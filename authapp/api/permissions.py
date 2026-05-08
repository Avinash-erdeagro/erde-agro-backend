from rest_framework.permissions import BasePermission

from authapp.models import AppUser


class IsSuperAdmin(BasePermission):
    """
    Grants access only to users whose AppUser role is SUPER_ADMIN.
    Use on views that control organization / hierarchy configuration.
    """

    message = "Only Super Admin accounts can perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        app_user = getattr(request.user, "appuser", None)
        if app_user is None:
            return False
        return app_user.role == AppUser.Role.SUPER_ADMIN


class IsSuperAdminOrOrgUser(BasePermission):
    """
    Grants access to SUPER_ADMIN or ORG_USER accounts.
    Used on read-only hierarchy views that both roles can access.
    """

    message = "Only Super Admin or Org User accounts can perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        app_user = getattr(request.user, "appuser", None)
        if app_user is None:
            return False
        return app_user.role in (AppUser.Role.SUPER_ADMIN, AppUser.Role.ORG_USER)
