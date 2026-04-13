from django.db import models


class SatellitePlan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    duration_days = models.PositiveIntegerField(unique=True)
    duration_months = models.PositiveIntegerField()
    base_price_per_acre = models.DecimalField(max_digits=10, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    total_price_per_acre = models.DecimalField(max_digits=10, decimal_places=2)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount_per_acre = models.DecimalField(max_digits=10, decimal_places=2)
    commission_gst_per_acre = models.DecimalField(max_digits=10, decimal_places=2)
    total_commission_per_acre = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["duration_days"]

    def __str__(self):
        return self.name
