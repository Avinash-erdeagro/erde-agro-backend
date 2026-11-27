from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authapp.api.responses import api_response
from authapp.api.response_codes import ResponseCode
from authapp.api.views.base import BaseAPIView
from authapp.models import AppUser, OrgUnitFPO
from orgapp.services import get_org_farmers, get_org_farms, get_org_fpos, get_org_units


class OrgAccessDenied(Exception):
    """Raised when the caller is logged in but is not an org user with a unit."""


class OrgScopedAPIView(BaseAPIView):
    """
    Base for every org-dashboard endpoint (/org/...).

    - Only authenticated ORG_USER accounts with an OrgMembership get in;
      everyone else gets 403 ORG_USER_ONLY. The check runs before the
      view's get(), so a subclass cannot forget it.
    - Views must read data only through get_org_units() / get_fpos() /
      get_farmers() / get_farms(), which apply the caller's hierarchy scope.
    """

    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        # Authentication + IsAuthenticated run here first (401 if not logged in).
        super().initial(request, *args, **kwargs)
        self.app_user, self.org_unit = self._resolve_org_user(request)
        if self.org_unit is None:
            raise OrgAccessDenied()

    def handle_exception(self, exc):
        if isinstance(exc, OrgAccessDenied):
            return api_response(
                success=False,
                message="This API is available only for organization users.",
                code=ResponseCode.ORG_USER_ONLY,
                result=None,
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return super().handle_exception(exc)

    @staticmethod
    def _resolve_org_user(request):
        app_user = getattr(request.user, "appuser", None)
        if app_user is None or app_user.role != AppUser.Role.ORG_USER:
            return app_user, None
        membership = getattr(app_user, "org_membership", None)
        if membership is None:
            return app_user, None
        return app_user, membership.org_unit

    def get_org_units(self):
        """The caller's unit and every unit below it."""
        return get_org_units(self.app_user)

    def get_fpos(self):
        """FPOs linked to units in the caller's subtree."""
        return get_org_fpos(self.app_user)

    def get_farmers(self):
        """Farmers of in-scope FPOs."""
        return get_org_farmers(self.app_user)

    def get_farms(self):
        """Farms of in-scope farmers."""
        return get_org_farms(self.app_user)

    def get_observation_date(self):
        """
        Required ?observation_date=YYYY-MM-DD.

        Same rule as the FPO dashboard: data is looked up for the day
        BEFORE the given date. Returns (date, None) or (None, error_response).
        """
        raw = self.request.query_params.get("observation_date")
        if not raw:
            return None, api_response(
                success=False,
                message="observation_date is required (YYYY-MM-DD)",
                code=ResponseCode.OBSERVATION_DATE_REQUIRED,
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return None, api_response(
                success=False,
                message="Invalid observation_date format. Use YYYY-MM-DD",
                code=ResponseCode.OBSERVATION_DATE_INVALID,
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return parsed - timedelta(days=1), None

    def filter_farms_by_selection(self, farms):
        """
        Narrow a scoped farms queryset to the sidebar selection:
        ?org_unit=<id> (that unit's whole subtree), ?fpo=<id>, ?farmer=<id>
        (FarmerProfile id). Several may be given; they combine with AND.
        An id outside the caller's scope just gives no farms.

        Returns (farms, None) or (None, error_response) for a non-numeric id.
        """
        params = {}
        for name in ("org_unit", "fpo", "farmer"):
            raw = self.request.query_params.get(name)
            if not raw:
                continue
            if not raw.isdigit():
                return None, api_response(
                    success=False,
                    message=f"{name} must be a numeric id.",
                    code=ResponseCode.INVALID_DATA,
                    result=None,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            params[name] = int(raw)

        if "org_unit" in params:
            unit = self.get_org_units().filter(pk=params["org_unit"]).first()
            if unit is None:
                return farms.none(), None
            subtree_fpo_ids = OrgUnitFPO.objects.filter(
                org_unit__organization_id=unit.organization_id,
                org_unit__path__startswith=unit.path,
            ).values("fpo_profile_id")
            farms = farms.filter(
                farmer__farmer_profile__registered_with_fpo_id__in=subtree_fpo_ids
            )
        if "fpo" in params:
            farms = farms.filter(farmer__farmer_profile__registered_with_fpo_id=params["fpo"])
        if "farmer" in params:
            farms = farms.filter(farmer__farmer_profile__id=params["farmer"])
        return farms, None
