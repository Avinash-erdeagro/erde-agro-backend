from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from authapp.api.permissions import IsSuperAdmin, IsSuperAdminOrOrgUser
from authapp.api.responses import api_response
from authapp.models import AppUser
from authapp.models.hierarchy import HierarchyLevel, OrgUnit, Organization, OrgMembership, OrgUnitFPO
from authapp.services.hierarchy import (
    generate_impersonation_token,
    get_accessible_org_units,
    move_org_unit,
    set_org_unit_path,
)
from authapp.services.registration import create_org_user, create_super_admin

from ..serializers.hierarchy import (
    AdminUserCreateSerializer,
    HierarchyLevelSerializer,
    OrgMembershipSerializer,
    OrgUnitFPOSerializer,
    OrgUnitSerializer,
    OrgUnitTreeSerializer,
    OrganizationSerializer,
)


class ImpersonateUserView(APIView):
    """
    POST /hierarchy/impersonate/<user_id>/

    Mint a JWT token pair scoped to `user_id`.
    SUPER_ADMIN may impersonate any ORG_USER across all orgs.
    ORG_USER may only impersonate ORG_USER nodes strictly below them.
    FPO and FARMER targets are always blocked.
    """

    permission_classes = [IsSuperAdminOrOrgUser]

    def post(self, request, user_id: int):
        requester_app_user = getattr(request.user, "appuser", None)
        if requester_app_user is None:
            return api_response(
                success=False,
                message="Requester has no AppUser profile.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        target_app_user = (
            AppUser.objects.select_related("user", "org_membership__org_unit")
            .filter(pk=user_id)
            .first()
        )
        if target_app_user is None:
            return api_response(
                success=False,
                message="Target user not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            token_data = generate_impersonation_token(requester_app_user, target_app_user)
        except PermissionError as exc:
            return api_response(
                success=False,
                message=str(exc),
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return api_response(
            success=True,
            message="Impersonation token issued.",
            result=token_data,
            status_code=status.HTTP_200_OK,
        )


class HierarchyLevelListView(ListAPIView):
    """
    GET /hierarchy/levels/?organization=<id>

    List all HierarchyLevel rows for the caller's organization.
    SUPER_ADMIN may pass ?organization=<id> to filter, or omit it to see all.
    """

    permission_classes = [IsSuperAdminOrOrgUser]
    serializer_class = HierarchyLevelSerializer

    def get_queryset(self):
        app_user = getattr(self.request.user, "appuser", None)
        if app_user is None:
            return HierarchyLevel.objects.none()

        if app_user.role == AppUser.Role.SUPER_ADMIN:
            org_id = self.request.query_params.get("organization")
            if org_id:
                return HierarchyLevel.objects.filter(organization_id=org_id)
            return HierarchyLevel.objects.all()

        try:
            org = app_user.org_membership.org_unit.organization
        except Exception:
            return HierarchyLevel.objects.none()

        return HierarchyLevel.objects.filter(organization=org)


class AccessibleOrgUnitListView(ListAPIView):
    """
    GET /hierarchy/units/

    List all OrgUnit nodes at or below the authenticated user's position.
    SUPER_ADMIN receives all units across all organizations.
    """

    permission_classes = [IsSuperAdminOrOrgUser]
    serializer_class = OrgUnitTreeSerializer

    def get_queryset(self):
        app_user = getattr(self.request.user, "appuser", None)
        if app_user is None:
            return OrgUnit.objects.none()
        return get_accessible_org_units(app_user).select_related("hierarchy_level")


class OrgUnitSubtreeView(RetrieveAPIView):
    """
    GET /hierarchy/units/<id>/subtree/

    Return all OrgUnit nodes in the subtree rooted at `id`, provided the
    authenticated user has access to that node.
    """

    permission_classes = [IsSuperAdminOrOrgUser]
    serializer_class = OrgUnitTreeSerializer

    def get(self, request, pk: int):
        app_user = getattr(request.user, "appuser", None)
        if app_user is None:
            return api_response(
                success=False,
                message="No AppUser profile found.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        accessible = get_accessible_org_units(app_user)
        root = accessible.filter(pk=pk).first()
        if root is None:
            return api_response(
                success=False,
                message="OrgUnit not found or not accessible.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        subtree = OrgUnit.objects.filter(
            path__startswith=root.path,
            organization=root.organization,
        ).select_related("hierarchy_level")

        serializer = OrgUnitTreeSerializer(subtree, many=True)
        return api_response(
            success=True,
            message="Subtree retrieved.",
            result=serializer.data,
            status_code=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# SUPER_ADMIN management views
# ---------------------------------------------------------------------------


class OrganizationListCreateView(ListCreateAPIView):
    """
    GET  /admin/organizations/     — list all organizations
    POST /admin/organizations/     — create a new organization
    SUPER_ADMIN only.
    """

    permission_classes = [IsSuperAdmin]
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()


class OrganizationDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /admin/organizations/<id>/
    SUPER_ADMIN only.
    """

    permission_classes = [IsSuperAdmin]
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()


class HierarchyLevelListCreateView(ListCreateAPIView):
    """
    GET  /admin/hierarchy-levels/?organization=<id>  — list levels
    POST /admin/hierarchy-levels/                    — add a new level
    SUPER_ADMIN only.
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
    """
    GET/PATCH/DELETE /admin/hierarchy-levels/<id>/
    SUPER_ADMIN only.
    """

    permission_classes = [IsSuperAdmin]
    serializer_class = HierarchyLevelSerializer
    queryset = HierarchyLevel.objects.all()


class OrgUnitListCreateView(ListCreateAPIView):
    """
    GET  /admin/org-units/?organization=<id>  — list all org units
    POST /admin/org-units/                    — create a new org unit

    On creation the materialized path is computed automatically.
    SUPER_ADMIN only.
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
    GET/PATCH/DELETE /admin/org-units/<id>/

    PATCH with a new `parent` value will re-parent the node and update all
    descendant paths via `move_org_unit`.
    SUPER_ADMIN only.
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
    GET  /admin/memberships/?org_unit=<id>  — list memberships
    POST /admin/memberships/               — assign an ORG_USER to an OrgUnit
    SUPER_ADMIN only.
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
    """
    GET/PATCH/DELETE /admin/memberships/<id>/
    SUPER_ADMIN only.
    """

    permission_classes = [IsSuperAdmin]
    serializer_class = OrgMembershipSerializer
    queryset = OrgMembership.objects.select_related("app_user", "org_unit")


class OrgUnitFPOListCreateView(ListCreateAPIView):
    """
    GET  /admin/fpo-links/?org_unit=<id>  — list FPO ↔ OrgUnit links
    POST /admin/fpo-links/               — link an FPO to an OrgUnit
    SUPER_ADMIN only.
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
    """
    GET/PATCH/DELETE /admin/fpo-links/<id>/
    SUPER_ADMIN only.
    """

    permission_classes = [IsSuperAdmin]
    serializer_class = OrgUnitFPOSerializer
    queryset = OrgUnitFPO.objects.select_related("fpo_profile", "org_unit")


class AdminUserCreateView(APIView):
    """
    POST /admin/users/

    Create an ORG_USER or SUPER_ADMIN account.
    This is the ONLY way to create these privileged accounts — they are
    intentionally excluded from the public /register/ endpoint.

    Request body:
      {
        "username": "state_head_pune",
        "password": "...",
        "role": "ORG_USER",          // or "SUPER_ADMIN"
        "org_unit": 5                // required for ORG_USER, ignored for SUPER_ADMIN
      }

    SUPER_ADMIN only.
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
