from django.contrib import admin
from django.db.models import Count

from authapp.models.hierarchy import (
    HierarchyLevel,
    OrgMembership,
    OrgUnit,
    OrgUnitFPO,
    Organization,
    FieldOfficer
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "created_at"]
    search_fields = ["name"]


@admin.register(HierarchyLevel)
class HierarchyLevelAdmin(admin.ModelAdmin):
    list_display = ["id", "organization", "level", "name"]
    list_filter = ["organization"]
    ordering = ["organization", "level"]


class OrgUnitChildInline(admin.TabularInline):
    model = OrgUnit
    fk_name = "parent"
    fields = ["name", "hierarchy_level", "path"]
    readonly_fields = ["path"]
    extra = 0
    show_change_link = True


@admin.register(OrgUnit)
class OrgUnitAdmin(admin.ModelAdmin):
    list_display = ["id", "organization", "hierarchy_level", "name", "parent", "path"]
    list_filter = ["organization", "hierarchy_level"]
    search_fields = ["name"]
    readonly_fields = ["path"]
    raw_id_fields = ["parent"]
    inlines = [OrgUnitChildInline]

    def save_model(self, request, obj, form, change):
        """Auto-compute the materialized path after saving via admin."""
        from authapp.services.hierarchy import set_org_unit_path

        super().save_model(request, obj, form, change)
        # Path requires the PK to exist, so compute after initial save.
        set_org_unit_path(obj)


@admin.register(OrgMembership)
class OrgMembershipAdmin(admin.ModelAdmin):
    list_display = ["id", "app_user", "org_unit"]
    list_filter = ["org_unit__organization"]
    search_fields = ["app_user__user__username", "org_unit__name"]
    raw_id_fields = ["app_user", "org_unit"]


@admin.register(OrgUnitFPO)
class OrgUnitFPOAdmin(admin.ModelAdmin):
    list_display = ["id", "fpo_profile", "org_unit"]
    list_filter = ["org_unit__organization"]
    search_fields = ["fpo_profile__fpo_name", "org_unit__name"]
    raw_id_fields = ["fpo_profile", "org_unit"]


@admin.register(FieldOfficer)
class FieldOfficerAdmin(admin.ModelAdmin):
    list_display = ["id", "officer_code", "name", "mobile", "org_unit", "is_active", "farmer_count", "created_at"]
    list_filter = ["org_unit__organization", "is_active"]
    search_fields = ["officer_code", "name", "mobile"]
    raw_id_fields = ["org_unit"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_farmer_count=Count("registered_farmers"))

    @admin.display(description="Farmers", ordering="_farmer_count")
    def farmer_count(self, obj):
        return obj._farmer_count