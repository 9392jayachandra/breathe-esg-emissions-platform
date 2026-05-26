from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Count, Sum, Q

from .models import Tenant, DataSource, EmissionRecord, AuditLog
from .serializers import (
    TenantSerializer, DataSourceSerializer,
    EmissionRecordSerializer, AuditLogSerializer
)
from .parsers import parse_sap, parse_utility, parse_travel


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------

class TenantListView(APIView):
    def get(self, request):
        tenants = Tenant.objects.all()
        return Response(TenantSerializer(tenants, many=True).data)

    def post(self, request):
        s = TenantSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return Response(s.data, status=status.HTTP_201_CREATED)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Upload + Ingest
# ---------------------------------------------------------------------------

PARSERS = {
    'SAP': parse_sap,
    'UTILITY': parse_utility,
    'TRAVEL': parse_travel,
}


class UploadView(APIView):
    """
    POST multipart/form-data with:
      - file: the CSV file
      - source_type: SAP | UTILITY | TRAVEL
      - tenant_id: UUID
    """
    def post(self, request):
        file = request.FILES.get('file')
        source_type = request.data.get('source_type', '').upper()
        tenant_id = request.data.get('tenant_id')

        if not file:
            return Response({'error': 'No file provided'}, status=400)
        if source_type not in PARSERS:
            return Response({'error': f'source_type must be one of {list(PARSERS.keys())}'}, status=400)

        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found'}, status=404)

        ds = DataSource.objects.create(
            tenant=tenant,
            source_type=source_type,
            uploaded_file=file,
            original_filename=file.name,
            status='PROCESSING',
        )

        try:
            file_bytes = file.read()
            parser = PARSERS[source_type]
            records, errors = parser(file_bytes)

            created = []
            for rec in records:
                er = EmissionRecord.objects.create(
                    tenant=tenant,
                    source=ds,
                    review_status='FLAGGED' if rec.get('flag_reason') else 'PENDING',
                    **rec
                )
                created.append(er)

            ds.status = 'DONE'
            ds.row_count = len(created)
            ds.error_message = '\n'.join(errors) if errors else None
            ds.save()

            return Response({
                'source_id': str(ds.id),
                'rows_created': len(created),
                'rows_with_errors': len(errors),
                'errors': errors[:10],  # return first 10 errors max
            }, status=201)

        except Exception as e:
            ds.status = 'FAILED'
            ds.error_message = str(e)
            ds.save()
            return Response({'error': str(e)}, status=500)


# ---------------------------------------------------------------------------
# Emission Records
# ---------------------------------------------------------------------------

class EmissionRecordListView(APIView):
    def get(self, request):
        qs = EmissionRecord.objects.select_related('source', 'tenant').all()

        # Filters
        tenant_id = request.query_params.get('tenant_id')
        review_status = request.query_params.get('review_status')
        scope = request.query_params.get('scope')
        source_type = request.query_params.get('source_type')

        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        if review_status:
            qs = qs.filter(review_status=review_status)
        if scope:
            qs = qs.filter(scope=scope)
        if source_type:
            qs = qs.filter(source__source_type=source_type)

        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(EmissionRecordSerializer(page, many=True).data)


class EmissionRecordDetailView(APIView):
    def get_object(self, pk):
        try:
            return EmissionRecord.objects.get(pk=pk)
        except EmissionRecord.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        return Response(EmissionRecordSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        if obj.is_locked:
            return Response({'error': 'Record is locked for audit'}, status=403)

        analyst = request.data.get('reviewed_by', 'analyst')
        allowed_fields = {'review_notes', 'normalized_quantity', 'co2e_kg', 'flag_reason'}

        for field in allowed_fields:
            if field in request.data:
                old_val = str(getattr(obj, field))
                new_val = str(request.data[field])
                if old_val != new_val:
                    AuditLog.objects.create(
                        emission_record=obj,
                        changed_by=analyst,
                        field_changed=field,
                        old_value=old_val,
                        new_value=new_val,
                        action='UPDATE',
                    )
                    setattr(obj, field, request.data[field])
                    obj.is_edited = True

        obj.save()
        return Response(EmissionRecordSerializer(obj).data)


# ---------------------------------------------------------------------------
# Review actions: approve / reject / flag
# ---------------------------------------------------------------------------

class ReviewActionView(APIView):
    """
    POST /api/records/<pk>/review/
    Body: { "action": "approve"|"reject"|"flag", "reviewed_by": "name", "notes": "..." }
    """
    def post(self, request, pk):
        try:
            obj = EmissionRecord.objects.get(pk=pk)
        except EmissionRecord.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

        if obj.is_locked:
            return Response({'error': 'Record is locked for audit'}, status=403)

        action = request.data.get('action', '').upper()
        reviewer = request.data.get('reviewed_by', 'analyst')
        notes = request.data.get('notes', '')

        action_map = {
            'APPROVE': 'APPROVED',
            'REJECT': 'REJECTED',
            'FLAG': 'FLAGGED',
        }
        if action not in action_map:
            return Response({'error': 'action must be approve, reject, or flag'}, status=400)

        old_status = obj.review_status
        obj.review_status = action_map[action]
        obj.reviewed_by = reviewer
        obj.reviewed_at = timezone.now()
        obj.review_notes = notes
        if action == 'APPROVE':
            obj.is_locked = True  # lock on approval

        obj.save()

        AuditLog.objects.create(
            emission_record=obj,
            changed_by=reviewer,
            field_changed='review_status',
            old_value=old_status,
            new_value=obj.review_status,
            action=action,
        )

        return Response(EmissionRecordSerializer(obj).data)


# ---------------------------------------------------------------------------
# Bulk review
# ---------------------------------------------------------------------------

class BulkReviewView(APIView):
    """
    POST /api/records/bulk-review/
    Body: { "ids": [...], "action": "approve"|"reject", "reviewed_by": "..." }
    """
    def post(self, request):
        ids = request.data.get('ids', [])
        action = request.data.get('action', '').upper()
        reviewer = request.data.get('reviewed_by', 'analyst')

        action_map = {'APPROVE': 'APPROVED', 'REJECT': 'REJECTED', 'FLAG': 'FLAGGED'}
        if action not in action_map:
            return Response({'error': 'Invalid action'}, status=400)

        updated = 0
        for pk in ids:
            try:
                obj = EmissionRecord.objects.get(pk=pk, is_locked=False)
                old = obj.review_status
                obj.review_status = action_map[action]
                obj.reviewed_by = reviewer
                obj.reviewed_at = timezone.now()
                if action == 'APPROVE':
                    obj.is_locked = True
                obj.save()
                AuditLog.objects.create(
                    emission_record=obj,
                    changed_by=reviewer,
                    field_changed='review_status',
                    old_value=old,
                    new_value=obj.review_status,
                    action=action,
                )
                updated += 1
            except EmissionRecord.DoesNotExist:
                pass

        return Response({'updated': updated})


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

class DashboardStatsView(APIView):
    def get(self, request):
        tenant_id = request.query_params.get('tenant_id')
        qs = EmissionRecord.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        stats = {
            'total_records': qs.count(),
            'pending': qs.filter(review_status='PENDING').count(),
            'approved': qs.filter(review_status='APPROVED').count(),
            'rejected': qs.filter(review_status='REJECTED').count(),
            'flagged': qs.filter(review_status='FLAGGED').count(),
            'total_co2e_kg': qs.filter(review_status='APPROVED').aggregate(
                t=Sum('co2e_kg'))['t'] or 0,
            'by_scope': {
                'scope1': qs.filter(scope=1).aggregate(t=Sum('co2e_kg'))['t'] or 0,
                'scope2': qs.filter(scope=2).aggregate(t=Sum('co2e_kg'))['t'] or 0,
                'scope3': qs.filter(scope=3).aggregate(t=Sum('co2e_kg'))['t'] or 0,
            },
            'by_source': list(
                qs.values('source__source_type').annotate(
                    count=Count('id'), co2e=Sum('co2e_kg')
                )
            ),
        }
        return Response(stats)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class AuditLogView(APIView):
    def get(self, request, pk):
        logs = AuditLog.objects.filter(emission_record_id=pk).order_by('-changed_at')
        return Response(AuditLogSerializer(logs, many=True).data)


# ---------------------------------------------------------------------------
# Data sources list
# ---------------------------------------------------------------------------

class DataSourceListView(APIView):
    def get(self, request):
        tenant_id = request.query_params.get('tenant_id')
        qs = DataSource.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return Response(DataSourceSerializer(qs, many=True).data)
