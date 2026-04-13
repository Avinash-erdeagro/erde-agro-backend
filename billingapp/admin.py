from django.contrib import admin

from billingapp.models import SatellitePlan


@admin.register(SatellitePlan)
class SatellitePlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "duration_days",
        "duration_months",
        "total_price_per_acre",
        "commission_percent",
        "total_commission_per_acre",
        "is_active",
    )
    list_filter = ("is_active", "duration_months")
    search_fields = ("name",)
    ordering = ("duration_days",)
