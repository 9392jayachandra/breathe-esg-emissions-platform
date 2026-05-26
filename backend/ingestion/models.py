from django.db import models
import uuid


class Tenant(models.Model):
    """Represents a client company (multi-tenancy support)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DataSource(models.Model):
    """
    Tracks every ingestion event (file upload).
    One upload can produce many EmissionRecords.
    This is our source-of-truth tracking layer.
    """
    SOURCE_TYPES = [
        ('SAP', 'SAP Fuel & Procurement'),
        ('UTILITY', 'Utility Electricity'),
        ('TRAVEL', 'Corporate Travel'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('DONE', 'Done'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='data_sources')
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    uploaded_file = models.FileField(upload_to='uploads/', null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    row_count = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.source_type} | {self.tenant.name} | {self.uploaded_at:%Y-%m-%d}"


class EmissionRecord(models.Model):
    """
    A single normalized emission event.
    Scope 1 = direct (fuel combustion)
    Scope 2 = indirect electricity
    Scope 3 = value chain (travel, procurement)
    """
    SCOPE_CHOICES = [
        (1, 'Scope 1 – Direct Emissions'),
        (2, 'Scope 2 – Indirect Electricity'),
        (3, 'Scope 3 – Value Chain'),
    ]
    REVIEW_STATUS = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('FLAGGED', 'Flagged / Suspicious'),
    ]
    CATEGORY_CHOICES = [
        # Scope 1
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('natural_gas', 'Natural Gas'),
        ('lpg', 'LPG'),
        # Scope 2
        ('electricity', 'Electricity'),
        # Scope 3
        ('flight', 'Flight'),
        ('hotel', 'Hotel Stay'),
        ('ground_transport', 'Ground Transport'),
        ('procurement', 'Procurement'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='emission_records')
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='records')

    # Activity details
    activity_date = models.DateField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)

    # Raw values — exactly as they came in, never modified
    raw_quantity = models.FloatField()
    raw_unit = models.CharField(max_length=50)

    # Normalized values — converted to standard units
    normalized_quantity = models.FloatField()
    normalized_unit = models.CharField(max_length=50)

    # Emissions
    co2e_kg = models.FloatField(null=True, blank=True)

    # Scope classification
    scope = models.IntegerField(choices=SCOPE_CHOICES)

    # Review workflow
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='PENDING')
    reviewed_by = models.CharField(max_length=255, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(null=True, blank=True)

    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)  # locked after auditor sign-off

    # Auto-flag reasons
    flag_reason = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-activity_date']

    def __str__(self):
        return f"{self.category} | {self.normalized_quantity} {self.normalized_unit} | {self.review_status}"


class AuditLog(models.Model):
    """Immutable record of every change to an EmissionRecord."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emission_record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_logs')
    changed_by = models.CharField(max_length=255)
    changed_at = models.DateTimeField(auto_now_add=True)
    field_changed = models.CharField(max_length=100)
    old_value = models.TextField()
    new_value = models.TextField()
    action = models.CharField(max_length=50, default='UPDATE')  # UPDATE, APPROVE, REJECT, FLAG

    def __str__(self):
        return f"{self.action} on {self.emission_record_id} by {self.changed_by}"
