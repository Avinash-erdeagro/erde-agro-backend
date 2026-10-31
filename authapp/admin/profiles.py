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
    list_display = ("id", "farmer_name", "app_user", "contact_number", "locality", "added_by_field_officer", "created_at")
    list_filter = ("added_by_field_officer__org_unit__organization", "added_by_field_officer")
    search_fields = ("farmer_name", "contact_number", "aadhaar_number")
