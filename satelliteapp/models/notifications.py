from django.db import models

from .provider import OrderFarm


class NotificationType(models.TextChoices):
    YOUR_FIELD_IS_DRYING                    = "YOUR_FIELD_IS_DRYING"
    MOISTURE_IS_IDEAL                       = "MOISTURE_IS_IDEAL"
    GROWTH_LOOKS_GREAT                      = "GROWTH_LOOKS_GREAT"
    MONITOR_FIELD_CLOSELY_CROP_HEALTH       = "MONITOR_FIELD_CLOSELY_CROP_HEALTH"
    MONITOR_FIELD_CLOSELY_FERTILIZER_LEVELS = "MONITOR_FIELD_CLOSELY_FERTILIZER_LEVELS"
    PLAN_IRRIGATION_THIS_WEEK               = "PLAN_IRRIGATION_THIS_WEEK"


class SatelliteFarmNotificationPushStatus(models.TextChoices):
    PENDING    = "PENDING"
    SENT       = "SENT"
    FAILED     = "FAILED"
    NO_DEVICES = "NO_DEVICES"


class SatelliteFarmNotification(models.Model):
    order_farm = models.ForeignKey(
        OrderFarm,
        on_delete=models.CASCADE,
        related_name="farm_notifications",
    )
    notification_type = models.CharField(max_length=100, choices=NotificationType.choices)
    details_json = models.JSONField(default=dict, blank=True)
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
                fields=["order_farm", "observation_date", "notification_type"],
                name="uniq_satellite_notification_per_field_date_type",
            )
        ]