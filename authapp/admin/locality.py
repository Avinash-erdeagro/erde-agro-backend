from django.contrib import admin

from ..models import Locality


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("id", "pin_code", "village", "taluka", "district", "state")
    search_fields = ("pin_code", "village", "taluka", "district", "state")
