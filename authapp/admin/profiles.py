from django.contrib import admin

from ..models import FarmerProfile, FpoProfile


@admin.register(FpoProfile)
class FpoProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "fpo_name", "app_user", "email", "mobile", "locality")
    search_fields = (
        "fpo_name",
        "contact_person_name",
        "email",
        "mobile",
        "gst_number",
        "pan_number",
        "cin_number",
    )


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "farmer_name", "app_user", "contact_number", "locality")
    search_fields = ("farmer_name", "contact_number", "aadhaar_number")
