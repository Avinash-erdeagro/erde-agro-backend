from django.contrib import admin
from .models import SoilType, IrrigationType, CropType, Farm, FarmCrop, FarmSatelliteSubscription


@admin.register(SoilType)
class SoilTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "irriwatch_id")


@admin.register(IrrigationType)
class IrrigationTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "irriwatch_id")


@admin.register(CropType)
class CropTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "irriwatch_id")


class FarmCropInline(admin.TabularInline):
    model = FarmCrop
    extra = 0


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ("id", "farm_name", "land_record_number", "farmer", "soil_type", "irrigation_type", "area")
    inlines = [FarmCropInline]


@admin.register(FarmCrop)
class FarmCropAdmin(admin.ModelAdmin):
    list_display = ("id", "farm", "primary_crop", "intercrop", "plantation_date", "is_active")
    list_filter = ("is_active",)

@admin.register(FarmSatelliteSubscription)
class FarmSatelliteSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "farm", "irriwatch_order_uuid", "subscription_start", "subscription_end", "status", "created_at")