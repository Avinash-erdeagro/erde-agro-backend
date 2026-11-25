"""
Which farmers a dashboard view covers.

The FPO dashboard views (state → district → farmer → farm tree, overview,
farm boundaries, farm map layers) work on a set of farmers — a FarmerProfile
queryset returned by `get_farmer_scope()`. The mixin a view is built with
decides that set:

  FPOFarmerScopeMixin  → farmers registered under the calling FPO
  OrgFarmerScopeMixin  → every farmer under the FPOs linked to the caller's
                         hierarchy node and the nodes below it (ORG_USER),
                         or every farmer (SUPER_ADMIN)

The org-user dashboard endpoints are the FPO views with OrgFarmerScopeMixin
in front (see adminapp/views/org_dashboard.py), so both dashboards always
return the same shapes.
"""

from rest_framework import status

from authapp.api.permissions import IsSuperAdminOrOrgUser
from authapp.api.response_codes import ResponseCode
from authapp.api.responses import api_response
from authapp.models import AppUser, FarmerProfile
from authapp.services.hierarchy import get_accessible_farmer_profiles


class FPOFarmerScopeMixin:
    def get_farmer_scope(self):
        """Farmers of the calling FPO, or None if the caller is not an FPO."""
        app_user = self.request.user.appuser
        if app_user.role != AppUser.Role.FPO:
            return None
        fpo_profile = getattr(app_user, "fpo_profile", None)
        if fpo_profile is None:
            return None
        return FarmerProfile.objects.filter(registered_with_fpo=fpo_profile)

    def scope_denied_response(self):
        return api_response(
            success=False,
            message="This API is available only for FPO users.", code=ResponseCode.FPO_ONLY,
            result=None,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class OrgFarmerScopeMixin:
    permission_classes = [IsSuperAdminOrOrgUser]

    def get_farmer_scope(self):
        """Farmers under the caller's hierarchy node (all farmers for SUPER_ADMIN)."""
        return get_accessible_farmer_profiles(self.request.user.appuser)

    def scope_denied_response(self):
        # Not reached: permission_classes already rejects other roles.
        return api_response(
            success=False,
            message="Only Super Admin or Org User accounts can perform this action.",
            code=ResponseCode.ERROR,
            result=None,
            status_code=status.HTTP_403_FORBIDDEN,
        )
