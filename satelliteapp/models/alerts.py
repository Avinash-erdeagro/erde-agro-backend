from django.db import models

from .provider import OrderFarm


class AlertType(models.TextChoices):
    CRITICAL_WATER_STRESS      = "CRITICAL_WATER_STRESS"
    OVERWATERING_DETECTED      = "OVERWATERING_DETECTED"
    CROP_HEALTH_DROPPING       = "CROP_HEALTH_DROPPING"
    RAIN_ALERT_SKIP_IRRIGATION = "RAIN_ALERT_SKIP_IRRIGATION"


class SatelliteFarmAlert(models.Model):
    order_farm = models.ForeignKey(
        OrderFarm,
        on_delete=models.CASCADE,
        related_name="farm_alerts",
    )
    alert_type = models.CharField(max_length=100, choices=AlertType.choices)
    details_json = models.JSONField(default=dict, blank=True)
    observation_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order_farm", "observation_date", "alert_type"],
                name="uniq_satellite_alert_per_field_date_type",
            )
        ]