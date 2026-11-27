import json

from django.contrib.gis.db.models.functions import Centroid
from django.db.models import OuterRef, Prefetch, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import status

from authapp.api.responses import api_response
from authapp.api.response_codes import ResponseCode
from clientapp.api.views.base import ClientScopedAPIView
from farmerapp.api.serializers import FarmerSatelliteOverviewQuerySerializer
from farmerapp.models import FarmCrop, FarmSatelliteSubscription, SatelliteSubscriptionStatus
from farmerapp.services import (
    SatelliteServiceError,
    fetch_farm_charts,
    fetch_farm_insights,
    fetch_farm_map_layers_by_farm_ids,
)
from fpoapp.utils import localized_lookup_name


def _satellite_error_response(exc):
    return api_response(
        success=False,
        message=str(exc),
        code=getattr(exc, "code", ResponseCode.SATELLITE_ERROR),
        result=None,
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _subscription_payload(subscription):
    return {
        "id": subscription.id,
        "status": subscription.status,
        "subscription_start": subscription.subscription_start,
        "subscription_end": subscription.subscription_end,
        "irriwatch_order_uuid": subscription.irriwatch_order_uuid,
        "irriwatch_field_uuid": subscription.irriwatch_field_uuid,
    }


class ClientFarmBoundariesView(ClientScopedAPIView):
    """
    GET /client/farms/geojson/[?state=][&district=][&farmer=]

    The client's scoped farms in the sidebar selection, as a GeoJSON
    FeatureCollection. Same shape as /fpo/farms/geojson/. Boundaries don't
    change with the date, so no observation_date is taken.
    """

    def get(self, request):
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

        farms = (
            farms.filter(boundary__isnull=False)
            .select_related("farmer__farmer_profile", "soil_type", "irrigation_type")
            .annotate(centroid=Centroid("boundary"))
            .prefetch_related(
                Prefetch(
                    "crops",
                    queryset=FarmCrop.objects.filter(is_active=True).select_related("primary_crop"),
                    to_attr="active_crops",
                )
            )
            .order_by("id")
        )

        language_code = getattr(request, "language_code", None)
        features = []
        for farm in farms:
            farmer_profile = farm.farmer.farmer_profile
            crop = next(iter(farm.active_crops), None)
            features.append(
                {
                    "type": "Feature",
                    "id": farm.id,
                    "geometry": json.loads(farm.boundary.geojson),
                    "properties": {
                        "farm_id": farm.id,
                        "farm_name": farm.farm_name,
                        "farmer_id": farmer_profile.id,
                        "farmer_name": farmer_profile.farmer_name,
                        "area": farm.area,
                        "crop_name": crop.primary_crop_localized_name(language_code) if crop else None,
                        "plantation_date": crop.plantation_date.isoformat() if crop and crop.plantation_date else None,
                        "irrigation_type": localized_lookup_name(farm.irrigation_type, language_code),
                        "soil_type": localized_lookup_name(farm.soil_type, language_code),
                        # [lng, lat] — GeoJSON order, ready for a pin layer.
                        "centroid": [farm.centroid.x, farm.centroid.y] if farm.centroid else None,
                    },
                }
            )

        return api_response(
            success=True,
            message="Client farm boundaries fetched successfully.",
            code=ResponseCode.CLIENT_FARM_BOUNDARIES_FETCHED,
            result={"type": "FeatureCollection", "features": features},
            status_code=status.HTTP_200_OK,
        )


class ClientFarmSatelliteMapLayersView(ClientScopedAPIView):
    """
    GET /client/farms/<farm_id>/satellite-map-layers/?observation_date=YYYY-MM-DD

    Map layers for one scoped farm with an active (SYNCING) subscription.
    Same shape as /fpo/farms/<id>/satellite-map-layers/. Like the FPO
    endpoint, the date is used as given (no day shift).
    """

    def get(self, request, farm_id):
        serializer = FarmerSatelliteOverviewQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        observation_date = serializer.validated_data["observation_date"]

        latest_subscription_qs = FarmSatelliteSubscription.objects.filter(
            farm_id=OuterRef("pk")
        ).order_by("-created_at")

        farms = (
            self.get_farms()
            .annotate(
                latest_subscription_status=Subquery(latest_subscription_qs.values("status")[:1])
            )
            .filter(latest_subscription_status=SatelliteSubscriptionStatus.SYNCING)
            .prefetch_related(
                Prefetch(
                    "crops",
                    queryset=FarmCrop.objects.select_related("primary_crop").order_by("-is_active"),
                )
            )
        )
        farm = get_object_or_404(farms, pk=farm_id)

        language_code = getattr(request, "language_code", None)
        try:
            satellite_layers = fetch_farm_map_layers_by_farm_ids(
                observation_date=observation_date.isoformat(),
                farm_ids=[farm.id],
                language_code=language_code,
            )
        except SatelliteServiceError as exc:
            return _satellite_error_response(exc)

        layers_result = next(
            (
                item
                for item in satellite_layers.get("results", [])
                if isinstance(item, dict) and item.get("farm_id") == farm.id
            ),
            {},
        )
        crop = next(iter(farm.crops.all()), None)

        return api_response(
            success=True,
            message="Client farm map layers fetched successfully.",
            code=ResponseCode.SATELLITE_MAP_LAYERS_FETCHED,
            result={
                "farm_id": farm.id,
                "farm_name": farm.farm_name,
                "area": farm.area,
                "crop_name": crop.primary_crop_localized_name(language_code) if crop else None,
                "boundary": json.loads(farm.boundary.geojson) if farm.boundary else None,
                "observation_date": layers_result.get(
                    "observation_date",
                    satellite_layers.get("observation_date", observation_date.isoformat()),
                ),
                "layers": layers_result.get("layers", []),
            },
            status_code=status.HTTP_200_OK,
        )


class _ClientFarmSatelliteDetailView(ClientScopedAPIView):
    """
    Shared flow for the farm-details endpoints (insights / charts):
    scoped farm -> subscription checks -> fetch -> response.
    Same checks and response shape as the farmer/FPO endpoints.
    """

    def fetch(self, farm, observation_date, language_code):
        raise NotImplementedError

    def build_result(self, data):
        raise NotImplementedError

    success_message = ""
    success_code = None

    def get(self, request, farm_id):
        serializer = FarmerSatelliteOverviewQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        observation_date = serializer.validated_data["observation_date"]

        farm = get_object_or_404(self.get_farms(), pk=farm_id)
        subscription = farm.satellite_subscriptions.order_by("-created_at").first()

        if not subscription:
            return api_response(
                success=False,
                message="Satellite services are not active for this farm.",
                code=ResponseCode.SATELLITE_NOT_SUBSCRIBED,
                result=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if subscription.status == SatelliteSubscriptionStatus.PAID:
            return api_response(
                success=False,
                message="Satellite data for this farm will be available within 7 working days.",
                code=ResponseCode.SATELLITE_DATA_PENDING,
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = self.fetch(farm, observation_date, getattr(request, "language_code", None))
        except SatelliteServiceError as exc:
            return _satellite_error_response(exc)

        return api_response(
            success=True,
            message=self.success_message,
            code=self.success_code,
            result={
                "farm_id": farm.id,
                "observation_date": observation_date.isoformat(),
                "subscription": _subscription_payload(subscription),
                **self.build_result(data),
            },
            status_code=status.HTTP_200_OK,
        )


class ClientFarmSatelliteInsightsView(_ClientFarmSatelliteDetailView):
    """GET /client/farms/<farm_id>/satellite-insights/?observation_date=YYYY-MM-DD"""

    success_message = "Farm insights fetched successfully."
    success_code = ResponseCode.SATELLITE_INSIGHTS_FETCHED

    def fetch(self, farm, observation_date, language_code):
        return fetch_farm_insights(
            farm_id=farm.id,
            observation_date=observation_date.isoformat(),
            language_code=language_code,
        )

    def build_result(self, data):
        return {"insights": data}


class ClientFarmSatelliteChartsView(_ClientFarmSatelliteDetailView):
    """GET /client/farms/<farm_id>/satellite-charts/?observation_date=YYYY-MM-DD"""

    success_message = "Farm charts fetched successfully."
    success_code = ResponseCode.SATELLITE_CHARTS_FETCHED

    def fetch(self, farm, observation_date, language_code):
        return fetch_farm_charts(
            farm_id=farm.id,
            observation_date=observation_date.isoformat(),
            language_code=language_code,
        )

    def build_result(self, data):
        return {"charts": data.get("charts", [])}
