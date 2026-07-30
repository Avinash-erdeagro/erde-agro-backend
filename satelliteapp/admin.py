from django.contrib import admin

from satelliteapp.models import (
    Company,
    Order,
    OrderFarm,
    SatelliteResult,
    SatelliteFarmAlert,
    SatelliteFarmNotification,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("company_name", "company_uuid", "created_at")
    search_fields = ("company_name", "company_uuid")
    ordering = ("-created_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "irriwatch_order_uuid", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("irriwatch_order_uuid",)
    ordering = ("-created_at",)


@admin.register(OrderFarm)
class OrderFarmAdmin(admin.ModelAdmin):
    list_display = ("id", "farm", "irriwatch_field_uuid", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("irriwatch_field_uuid", "farm__farm_name")
    ordering = ("-created_at",)


@admin.register(SatelliteResult)
class SatelliteResultAdmin(admin.ModelAdmin):
    list_display = ("id", "order_farm", "observation_date", "created_at")
    search_fields = ("order_farm__irriwatch_field_uuid",)
    ordering = ("-observation_date",)


@admin.register(SatelliteFarmAlert)
class SatelliteFarmAlertAdmin(admin.ModelAdmin):
    list_display = ("order_farm", "alert_type", "observation_date", "created_at")
    list_filter = ("alert_type",)
    search_fields = ("order_farm__irriwatch_field_uuid", "alert_type")
    ordering = ("-created_at",)


@admin.register(SatelliteFarmNotification)
class SatelliteFarmNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "order_farm",
        "notification_type",
        "observation_date",
        "is_read",
        "push_status",
        "created_at",
    )
    list_filter = ("push_status", "notification_type")
    search_fields = ("order_farm__irriwatch_field_uuid", "notification_type")
    readonly_fields = ("push_failure_reason",)
    ordering = ("-created_at",)