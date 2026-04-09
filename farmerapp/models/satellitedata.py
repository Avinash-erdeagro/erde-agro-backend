from django.db import models
from django.utils import timezone
from .farm import Farm

class SatelliteSubscriptionStatus(models.TextChoices):
    PAID      = "PAID"       # Payment done, not yet sent to satellite-service
    SUBMITTED = "SUBMITTED"  # Sent to satellite-service, waiting for data
    SYNCING   = "SYNCING"    # Actively receiving satellite data
    COMPLETED = "COMPLETED"  # Subscription over
    FAILED    = "FAILED"     # Satellite-service submission failed after retries

class FarmSatelliteSubscription(models.Model):
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name="satellite_subscriptions",
    )

    # Filled after adding entry to satellite-service and irriwatch order is created
    irriwatch_order_uuid = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
    )
    irriwatch_field_uuid = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
    )

    subscription_start = models.DateField()
    subscription_duration_months = models.PositiveIntegerField()
    subscription_end = models.DateField()

    payment_reference = models.CharField(max_length=255)

    status = models.CharField(
        max_length=20,
        choices=SatelliteSubscriptionStatus.choices,
        default=SatelliteSubscriptionStatus.PAID,
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(subscription_end__gte=models.F("subscription_start")),
                name="satellite_subscription_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["farm"],
                condition=models.Q(
                    status__in=[
                        SatelliteSubscriptionStatus.PAID,
                        SatelliteSubscriptionStatus.SUBMITTED,
                        SatelliteSubscriptionStatus.SYNCING,
                    ]
                ),
                name="unique_active_subscription_per_farm",
            ),
        ]

    def __str__(self):
        return f"{self.farm} - {self.status}"

    @property
    def is_expiring_soon(self):
        return (self.subscription_end - timezone.now().date()).days <= 7
