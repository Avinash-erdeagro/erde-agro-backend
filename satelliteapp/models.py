from django.db import models

class SatelliteEventReceiptStatus(models.TextChoices):
    RECEIVED = "RECEIVED", "Received"
    PROCESSING = "PROCESSING", "Processing"
    PROCESSED = "PROCESSED", "Processed"
    FAILED = "FAILED", "Failed"

class SatelliteEventReceipt(models.Model):
    event_id = models.BigIntegerField(unique=True)
    batch_id = models.CharField(max_length=100, blank=True, default="")
    event_type = models.CharField(max_length=100)
    external_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    order_field_id = models.BigIntegerField(db_index=True)
    observation_date = models.DateField(db_index=True)
    generated_at = models.DateTimeField()
    payload_json = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=SatelliteEventReceiptStatus.choices,
        default=SatelliteEventReceiptStatus.RECEIVED,
    )
    failure_reason = models.TextField(blank=True, default="")
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
