from django.contrib.auth import get_user_model
from rest_framework import serializers

from authapp.models import AppUser
from authapp.models.hierarchy import HierarchyLevel, OrgMembership, OrgUnit, OrgUnitFPO, Organization

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class HierarchyLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = HierarchyLevel
        fields = ["id", "organization", "name", "level"]
        read_only_fields = ["id"]


class OrgUnitSerializer(serializers.ModelSerializer):
    hierarchy_level_name = serializers.CharField(
        source="hierarchy_level.name", read_only=True
    )
    level_number = serializers.IntegerField(
        source="hierarchy_level.level", read_only=True
    )

    class Meta:
        model = OrgUnit
        fields = [
            "id",
            "organization",
            "hierarchy_level",
            "hierarchy_level_name",
            "level_number",
            "name",
            "parent",
            "path",
            "created_at",
        ]
        read_only_fields = ["id", "path", "created_at", "hierarchy_level_name", "level_number"]


class OrgUnitTreeSerializer(serializers.ModelSerializer):
    """Lightweight serializer for subtree listings."""

    hierarchy_level_name = serializers.CharField(
        source="hierarchy_level.name", read_only=True
    )

    class Meta:
        model = OrgUnit
        fields = ["id", "name", "hierarchy_level_name", "parent", "path"]


class OrgMembershipSerializer(serializers.ModelSerializer):
    org_unit_name = serializers.CharField(source="org_unit.name", read_only=True)
    role_name = serializers.CharField(
        source="org_unit.hierarchy_level.name", read_only=True
    )
    organization_name = serializers.CharField(
        source="org_unit.organization.name", read_only=True
    )

    class Meta:
        model = OrgMembership
        fields = [
            "id",
            "app_user",
            "org_unit",
            "org_unit_name",
            "role_name",
            "organization_name",
        ]
        read_only_fields = ["id", "org_unit_name", "role_name", "organization_name"]


class OrgUnitFPOSerializer(serializers.ModelSerializer):
    fpo_name = serializers.CharField(
        source="fpo_profile.fpo_name", read_only=True
    )
    org_unit_name = serializers.CharField(source="org_unit.name", read_only=True)

    class Meta:
        model = OrgUnitFPO
        fields = ["id", "fpo_profile", "fpo_name", "org_unit", "org_unit_name"]
        read_only_fields = ["id", "fpo_name", "org_unit_name"]


class ImpersonationResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    impersonated_user_id = serializers.IntegerField()
    impersonated_username = serializers.CharField()


class AdminUserCreateSerializer(serializers.Serializer):
    """
    Used by POST /admin/users/ to create ORG_USER or SUPER_ADMIN accounts.
    Only accepted roles are ORG_USER and SUPER_ADMIN.
    `org_unit` is required when role is ORG_USER and ignored for SUPER_ADMIN.
    """

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=[AppUser.Role.ORG_USER, AppUser.Role.SUPER_ADMIN]
    )
    org_unit = serializers.PrimaryKeyRelatedField(
        queryset=OrgUnit.objects.all(),
        required=False,
        allow_null=True,
    )

    # Read-only response fields
    id = serializers.IntegerField(read_only=True)
    created_username = serializers.SerializerMethodField(read_only=True)
    org_unit_name = serializers.SerializerMethodField(read_only=True)

    def get_created_username(self, obj):
        return obj.user.username if obj else None

    def get_org_unit_name(self, obj):
        try:
            return obj.org_membership.org_unit.name
        except Exception:
            return None

    def validate(self, attrs):
        if User.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError(
                {"username": "A user with this username already exists."}
            )
        if attrs["role"] == AppUser.Role.ORG_USER and not attrs.get("org_unit"):
            raise serializers.ValidationError(
                {"org_unit": "org_unit is required when creating an ORG_USER."}
            )
        return attrs
