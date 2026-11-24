from django.db.models import Count, Sum
from rest_framework import status

from authapp.api.responses import api_response
from authapp.api.response_codes import ResponseCode
from clientapp.api.views.base import ClientScopedAPIView
from farmerapp.models import FarmCrop
from satelliteapp.models import SatelliteFarmAlert

MOISTURE_ALERT_TYPES = [
    "CRITICAL_WATER_STRESS",
    "OVERWATERING_DETECTED",
    "RAIN_ALERT_SKIP_IRRIGATION",
]
CROP_GROWTH_ALERT_TYPES = ["CROP_HEALTH_DROPPING"]


class ClientOverviewView(ClientScopedAPIView):
    """
    GET /client/overview/?observation_date=YYYY-MM-DD[&state=][&district=][&farmer=]

    Same response shape as /fpo/overview/, computed over the client's
    scoped farms. Filters only narrow within the scope.
    """

    def get(self, request):
        observation_date, error = self.get_observation_date()
        if error:
            return error

        farms = self.get_farms()

        state = request.query_params.get("state")
        district = request.query_params.get("district")
        farmer_id = request.query_params.get("farmer")

        if state:
            farms = farms.filter(farmer__farmer_profile__locality__state__iexact=state)
        if district:
            farms = farms.filter(farmer__farmer_profile__locality__district__iexact=district)
        if farmer_id:
            if not farmer_id.isdigit():
                return api_response(
                    success=False,
                    message="farmer must be a numeric id.",
                    code=ResponseCode.INVALID_DATA,
                    result=None,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            farms = farms.filter(farmer__farmer_profile__id=int(farmer_id))

        total_area = farms.aggregate(total_area=Sum("area"))["total_area"] or 0.0

        # Crop-wise area (active crops only)
        language_code = getattr(request, "language_code", None)
        crop_name_field = (
            f"primary_crop__name_{language_code}"
            if language_code and language_code != "en"
            else "primary_crop__name"
        )
        crop_areas = (
            FarmCrop.objects.filter(farm__in=farms, is_active=True)
            .values(crop_name_field, "primary_crop__name", "custom_primary_crop_name")
            .annotate(total_area=Sum("farm__area"), farms_count=Count("farm", distinct=True))
            .order_by("primary_crop__name")
        )

        # Alert counts for the date
        alerts_qs = SatelliteFarmAlert.objects.filter(
            order_farm__farm__in=farms,
            observation_date=observation_date,
        )

        return api_response(
            success=True,
            message="Client overview fetched successfully.",
            code=ResponseCode.CLIENT_OVERVIEW_FETCHED,
            result={
                "observation_date": observation_date,
                "total_area": round(total_area, 2),
                "crops": [
                    {
                        "crop_name": c.get(crop_name_field) or c["primary_crop__name"] or c["custom_primary_crop_name"],
                        "total_area": round(c["total_area"] or 0, 2),
                        "farms_count": c["farms_count"],
                    }
                    for c in crop_areas
                ],
                "alerts": {
                    "total": alerts_qs.count(),
                    "moisture_status": alerts_qs.filter(alert_type__in=MOISTURE_ALERT_TYPES).count(),
                    "crop_growth": alerts_qs.filter(alert_type__in=CROP_GROWTH_ALERT_TYPES).count(),
                },
            },
            status_code=status.HTTP_200_OK,
        )