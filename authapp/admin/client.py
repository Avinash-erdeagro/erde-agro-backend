from django.contrib import admin

from ..models import ClientProfile, ClientScope


class ClientScopeInline(admin.StackedInline):
    model = ClientScope
    can_delete = False
    extra = 1
    max_num = 1
    filter_horizontal = ("org_units", "fpos", "crop_types")
    verbose_name_plural = "Scope (what this client can see)"
    help_text = (
        "Source: pick org units (includes everything below them) and/or individual FPOs. "
        "Filter: pick crop types to limit to farms with that active primary crop (empty = all crops)."
    )


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "client_name", "app_user", "contact_person_name", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("client_name", "contact_person_name", "email", "app_user__user__username")
    inlines = [ClientScopeInline]