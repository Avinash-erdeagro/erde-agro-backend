from django.contrib import admin

from ..models import AppUser


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "preferred_language")
    list_filter = ("role", "preferred_language")
    search_fields = ("user__username",)
