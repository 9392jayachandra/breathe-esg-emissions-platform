from django.contrib import admin
from .models import Tenant, DataSource, EmissionRecord, AuditLog

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['source_type', 'tenant', 'status', 'row_count', 'uploaded_at']

@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['category', 'scope', 'normalized_quantity', 'normalized_unit', 'co2e_kg', 'review_status', 'activity_date']
    list_filter = ['review_status', 'scope', 'category']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['emission_record', 'action', 'changed_by', 'changed_at']
