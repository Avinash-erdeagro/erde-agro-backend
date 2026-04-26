from django.contrib import admin

from satelliteapp.models import SatelliteEventReceipt, SatelliteFarmAlert, SatelliteFarmNotification

@admin.register(SatelliteEventReceipt)
class SatelliteEventReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "event_type",
        "received_at",
    )
    search_fields = ("event_id", "event_type")
    ordering = ("-received_at",)    


@admin.register(SatelliteFarmAlert)
class SatelliteFarmAlertAdmin(admin.ModelAdmin):
    list_display = (
        "receipt",
        "farm",
        "alert_type",
        "observation_date",
        "created_at",
    )
    search_fields = ("receipt__event_id", "farm__name", "alert_type")
    ordering = ("-created_at",)

@admin.register(SatelliteFarmNotification)
class SatelliteFarmNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "receipt",
        "farm",
        "notification_type",
        "observation_date",
        "is_read",
        "created_at",
    )
    search_fields = ("receipt__event_id", "farm__name", "notification_type")
    ordering = ("-created_at",)