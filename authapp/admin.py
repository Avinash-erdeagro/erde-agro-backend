from django.contrib import admin

from .models import Address, AppUser, FarmerProfile, FpoProfile


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
	list_display = ("id", "pin_code", "village", "taluka", "district", "state")
	search_fields = ("pin_code", "village", "taluka", "district", "state")


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "role")
	list_filter = ("role",)
	search_fields = ("user__username",)


@admin.register(FpoProfile)
class FpoProfileAdmin(admin.ModelAdmin):
	list_display = ("id", "fpo_name", "app_user", "email", "mobile", "address")
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
	list_display = ("id", "farmer_name", "app_user", "contact_number", "address")
	search_fields = ("farmer_name", "contact_number", "aadhaar_number", "email")
