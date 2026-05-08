"""
Hierarchy management views — SUPER_ADMIN only.

Covers Organization, HierarchyLevel, OrgUnit, OrgMembership, OrgUnitFPO,
and privileged user creation (ORG_USER / SUPER_ADMIN).
"""

from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView

from authapp.api.permissions import IsSuperAdmin
from authapp.api.responses import api_response
from authapp.models import AppUser
from authapp.models.hierarchy import (
    HierarchyLevel,
    OrgMembership,
    OrgUnit,
    OrgUnitFPO,
    Organization,
)
from authapp.services.hierarchy import move_org_unit, set_org_unit_path
from authapp.services.registration import create_org_user, create_super_admin

from authapp.api.serializers.hierarchy import (
    AdminUserCreateSerializer,
    HierarchyLevelSerializer,
    OrgMembershipSerializer,
    OrgUnitFPOSerializer,
    OrgUnitSerializer,
    OrganizationSerializer,
)


class OrganizationListCreateView(ListCreateAPIView):
    """
    GET  /super-admin/organizations/   — list all organizations
    POST /super-admin/organizations/   — create a new organization
    """
    permission_classes = [IsSuperAdmin]
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()


class OrganizationDetailView(RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /super-admin/organizations/<id>/"""
    permission_classes = [IsSuperAdmin]
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()


class HierarchyLevelListCreateView(ListCreateAPIView):
    """
    GET  /super-admin/hierarchy-levels/?organization=<id>   — list levels
    POST /super-admin/hierarchy-levels/                     — add a new level
    """
    permission_classes = [IsSuperAdmin]
    serializer_class = HierarchyLevelSerializer

    def get_queryset(self):
        org_id = self.request.query_params.get("organization")
        qs = HierarchyLevel.objects.all()
        if org_id:
            qs = qs.filter(organization_id=org_id)
        return qs


class HierarchyLevelDetailView(RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /super-admin/hierarchy-levels/<id>/"""
    permission_classes = [IsSuperAdmin]
    serializer_class = HierarchyLevelSerializer
    queryset = HierarchyLevel.objects.all()


class OrgUnitListCreateView(ListCreateAPIView):
    """
    GET  /super-admin/org-units/?organization=<id>   — list all org units
    POST /super-admin/org-units/                     — create a new org unit

    Materialized path is computed automatically on creation.
    """
    permission_classes = [IsSuperAdmin]
    serializer_class = OrgUnitSerializer

    def get_queryset(self):
        org_id = self.request.query_params.get("organization")
        qs = OrgUnit.objects.select_related("hierarchy_level", "organization")
        if org_id:
            qs = qs.filter(organization_id=org_id)
        return qs

    def perform_create(self, serializer):
        org_unit = serializer.save()
        set_org_unit_path(org_unit)


class OrgUnitDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /super-admin/org-units/<id>/

    PATCHing `parent` re-parents the node and updates all descendant paths.
    """
    permission_classes = [IsSuperAdmin]
    serializer_class = OrgUnitSerializer
    queryset = OrgUnit.objects.select_related("hierarchy_level", "organization")

    def perform_update(self, serializer):
        old_parent_id = serializer.instance.parent_id
        org_unit = serializer.save()
        new_parent_id = org_unit.parent_id
        if new_parent_id != old_parent_id:
            new_parent = OrgUnit.objects.get(pk=new_parent_id) if new_parent_id else None
            move_org_unit(org_unit, new_parent)
        else:
            set_org_unit_path(org_unit)


class OrgMembershipListCreateView(ListCreateAPIView):
    """
    GET  /super-admin/memberships/?org_unit=<id>   — list memberships
    POST /super-admin/memberships/                 — assign an ORG_USER to an OrgUnit
    """
    permission_classes = [IsSuperAdmin]
    serializer_class = OrgMembershipSerializer

    def get_queryset(self):
        org_unit_id = self.request.query_params.get("org_unit")
        qs = OrgMembership.objects.select_related("app_user", "org_unit")
        if org_unit_id:
            qs = qs.filter(org_unit_id=org_unit_id)
        return qs


class OrgMembershipDetailView(RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /super-admin/memberships/<id>/"""
    permission_classes = [IsSuperAdmin]
    serializer_class = OrgMembershipSerializer
    queryset = OrgMembership.objects.select_related("app_user", "org_unit")


class OrgUnitFPOListCreateView(ListCreateAPIView):
    """
    GET  /super-admin/fpo-links/?org_unit=<id>   — list FPO ↔ OrgUnit links
    POST /super-admin/fpo-links/                 — link an FPO to an OrgUnit
    """
    permission_classes = [IsSuperAdmin]
    serializer_class = OrgUnitFPOSerializer

    def get_queryset(self):
        org_unit_id = self.request.query_params.get("org_unit")
        qs = OrgUnitFPO.objects.select_related("fpo_profile", "org_unit")
        if org_unit_id:
            qs = qs.filter(org_unit_id=org_unit_id)
        return qs


class OrgUnitFPODetailView(RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /super-admin/fpo-links/<id>/"""
    permission_classes = [IsSuperAdmin]
    serializer_class = OrgUnitFPOSerializer
    queryset = OrgUnitFPO.objects.select_related("fpo_profile", "org_unit")


class AdminUserCreateView(APIView):
    """
    POST /super-admin/users/

    Create an ORG_USER or SUPER_ADMIN account.
    The public /register/ endpoint only accepts FPO and FARMER.

    Body:
      { "username": "...", "password": "...", "role": "ORG_USER", "org_unit": 5 }
      { "username": "...", "password": "...", "role": "SUPER_ADMIN" }
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        serializer = AdminUserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message="Invalid data.",
                result=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        role = data["role"]

        if role == AppUser.Role.ORG_USER:
            app_user = create_org_user(
                username=data["username"],
                password=data["password"],
                org_unit=data["org_unit"],
            )
        else:
            app_user = create_super_admin(
                username=data["username"],
                password=data["password"],
            )

        response_serializer = AdminUserCreateSerializer(app_user)
        return api_response(
            success=True,
            message=f"{role} account created successfully.",
            result=response_serializer.data,
            status_code=status.HTTP_201_CREATED,
        )
