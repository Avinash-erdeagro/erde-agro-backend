"""
Read-only hierarchy views.
Accessible to SUPER_ADMIN and ORG_USER.
"""

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView

from authapp.api.permissions import IsSuperAdminOrOrgUser
from authapp.api.responses import api_response
from authapp.models import AppUser
from authapp.models.hierarchy import HierarchyLevel, OrgUnit
from authapp.services.hierarchy import (
    generate_impersonation_token,
    get_accessible_org_units,
)

from ..serializers.hierarchy import (
    HierarchyLevelSerializer,
    OrgUnitTreeSerializer,
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
