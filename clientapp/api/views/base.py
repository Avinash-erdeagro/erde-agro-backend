from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authapp.api.responses import api_response
from authapp.api.response_codes import ResponseCode
from authapp.api.views.base import BaseAPIView
from authapp.models import AppUser
from clientapp.services import get_client_farmers, get_client_farms
from datetime import datetime, timedelta


class ClientAccessDenied(Exception):
    """Raised when the caller is logged in but is not an active client."""


class ClientScopedAPIView(BaseAPIView):
    """
    Base for every client-dashboard endpoint.

    - Only authenticated CLIENT users with an active ClientProfile get in;
      everyone else gets 403 CLIENT_ONLY. The check runs before the view's
      get(), so a subclass cannot forget it.
    - Views must read data only through get_farms() / get_farmers(), which
      apply the client's scope (source FPOs/org units + filters).
    """

    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        # Authentication + IsAuthenticated run here first (401 if not logged in).
        super().initial(request, *args, **kwargs)
        self.client_profile = self._resolve_client_profile(request)
        if self.client_profile is None:
            raise ClientAccessDenied()

    def handle_exception(self, exc):
        if isinstance(exc, ClientAccessDenied):
            return api_response(
                success=False,
                message="This API is available only for client users.",
                code=ResponseCode.CLIENT_ONLY,
                result=None,
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return super().handle_exception(exc)

    @staticmethod
    def _resolve_client_profile(request):
        app_user = getattr(request.user, "appuser", None)
        if app_user is None or app_user.role != AppUser.Role.CLIENT:
            return None
        client_profile = getattr(app_user, "client_profile", None)
        if client_profile is None or not client_profile.is_active:
            return None
        return client_profile

    def get_farms(self):
        """Farms this client can see (scope applied)."""
        return get_client_farms(self.client_profile)

    def get_farmers(self):
        """Farmers this client can see (scope applied)."""
        return get_client_farmers(self.client_profile)

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
