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


class SatelliteFarmAlert(models.Model):
    receipt = models.ForeignKey(
        "satelliteapp.SatelliteEventReceipt",
        on_delete=models.CASCADE,
        related_name="alert_rows",
    )
    farm = models.ForeignKey(
        "farmerapp.Farm",
        on_delete=models.CASCADE,
        related_name="satellite_alerts",
    )
    source_index = models.PositiveIntegerField()
    alert_type = models.CharField(max_length=100)
    details_json = models.JSONField(default=dict, blank=True)
    event_created_at = models.DateTimeField(null=True, blank=True)
    observation_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["receipt", "source_index"],
                name="uniq_satellite_alert_per_receipt_index",
            )
        ]


class SatelliteFarmNotificationPushStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    NO_DEVICES = "NO_DEVICES", "No Devices"


class SatelliteFarmNotification(models.Model):
    receipt = models.ForeignKey(
        "satelliteapp.SatelliteEventReceipt",
        on_delete=models.CASCADE,
        related_name="notification_rows",
    )
    farm = models.ForeignKey(
        "farmerapp.Farm",
        on_delete=models.CASCADE,
        related_name="satellite_notifications",
    )
    source_index = models.PositiveIntegerField()
    notification_type = models.CharField(max_length=100)
    details_json = models.JSONField(default=dict, blank=True)
    event_created_at = models.DateTimeField(null=True, blank=True)
    observation_date = models.DateField()
    is_read = models.BooleanField(default=False)
    push_status = models.CharField(
        max_length=20,
        choices=SatelliteFarmNotificationPushStatus.choices,
        default=SatelliteFarmNotificationPushStatus.PENDING,
        db_index=True,
    )
    push_failure_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["receipt", "source_index"],
                name="uniq_satellite_notification_per_receipt_index",
            )
        ]
