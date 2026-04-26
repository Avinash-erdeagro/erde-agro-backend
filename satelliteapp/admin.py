from django.contrib import admin

from satelliteapp.models import SatelliteEventReceipt

@admin.register(SatelliteEventReceipt)
class SatelliteEventReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "event_type",
        "received_at",
    )
    search_fields = ("event_id", "event_type")
    ordering = ("-received_at",)    


