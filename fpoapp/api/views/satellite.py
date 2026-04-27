from django.db.models import Sum, Q, Count
from satelliteapp.models import SatelliteFarmAlert
from farmerapp.models import Farm, FarmCrop
from authapp.models import FpoProfile
from datetime import datetime, timedelta

from collections import defaultdict

from django.db.models import OuterRef, Prefetch, Subquery
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authapp.api.responses import api_response
from authapp.api.views.base import BaseAPIView
from authapp.models import AppUser
from farmerapp.api.serializers import FarmerSatelliteOverviewQuerySerializer
from farmerapp.models import Farm, FarmCrop, FarmSatelliteSubscription, SatelliteSubscriptionStatus
from farmerapp.services import (
    SatelliteServiceError,
    fetch_farm_map_layers_by_external_ids,
    fetch_satellite_metrics_by_external_ids,
)


class FPOSatelliteOverviewView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_user = request.user.appuser
        if app_user.role != AppUser.Role.FPO:
            return api_response(
                success=False,
                message="This API is available only for FPO users.",
                result=None,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = FarmerSatelliteOverviewQuerySerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        observation_date = serializer.validated_data["observation_date"]

        farms = list(
            Farm.objects.filter(
                farmer__farmer_profile__registered_with_fpo=app_user.fpo_profile
            )
            .select_related("soil_type", "irrigation_type")
            .prefetch_related("crops", "crops__primary_crop", "satellite_subscriptions")
        )

        syncing_farm_ids = []
        farms_by_id = {}
        crop_summary = {}
        farm_groups = {
            "not_paid": [],
            "awaiting_data": [],
            "active": [],
        }

        for farm in farms:
            active_crop = next(
                (crop for crop in farm.crops.all() if crop.is_active),
                None,
            )
            if active_crop is None:
                active_crop = next(iter(farm.crops.all()), None)

            crop_name = active_crop.primary_crop_name if active_crop else None
            subscription = next(iter(farm.satellite_subscriptions.all()), None)

            if crop_name:
                if crop_name not in crop_summary:
                    crop_summary[crop_name] = {
                        "crop_name": crop_name,
                        "farms_count": 0,
                        "total_area": 0.0,
                    }
                crop_summary[crop_name]["farms_count"] += 1
                crop_summary[crop_name]["total_area"] += float(farm.area or 0)

            farm_payload = {
                "farm_id": farm.id,
                "farm_name": farm.farm_name,
                "area": farm.area,
                "crop_name": crop_name,
                "subscription": None,
                "soil_moisture": None,
                "crop_growth": None,
                "message": None,
            }

            if subscription:
                farm_payload["subscription"] = {
                    "id": subscription.id,
                    "status": subscription.status,
                    "subscription_start": subscription.subscription_start,
                    "subscription_end": subscription.subscription_end,
                }

            if subscription is None:
                farm_payload["message"] = "Satellite data is not enabled for this farm."
                farm_groups["not_paid"].append(farm_payload)
                continue

            if subscription.status in (
                SatelliteSubscriptionStatus.PAID,
                SatelliteSubscriptionStatus.SUBMITTED,
            ):
                farm_payload["message"] = (
                    "Satellite data subscription is active, but data is not available yet."
                )
                farm_groups["awaiting_data"].append(farm_payload)
                continue

            if subscription.status == SatelliteSubscriptionStatus.SYNCING:
                syncing_farm_ids.append(farm.id)
                farms_by_id[farm.id] = farm_payload
                continue

            farm_payload["message"] = "Satellite data is not enabled for this farm."
            farm_groups["not_paid"].append(farm_payload)

        satellite_response = {
            "observation_date": observation_date.isoformat(),
            "results": [],
        }
        if syncing_farm_ids:
            try:
                satellite_response = fetch_satellite_metrics_by_external_ids(
                    observation_date=observation_date.isoformat(),
                    external_ids=syncing_farm_ids,
                )
            except SatelliteServiceError as exc:
                return api_response(
                    success=False,
                    message=str(exc),
                    result=None,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        metrics_by_farm_id = {
            item["external_id"]: item
            for item in satellite_response.get("results", [])
            if isinstance(item, dict) and item.get("external_id") is not None
        }

        for farm_id in syncing_farm_ids:
            farm_payload = farms_by_id[farm_id]
            metric = metrics_by_farm_id.get(farm_id)

            if metric:
                farm_payload["soil_moisture"] = metric.get("soil_moisture")
                farm_payload["crop_growth"] = metric.get("crop_growth")
                farm_payload["message"] = None
            else:
                farm_payload["message"] = (
                    "This date's data is not currently available. Please choose an earlier date."
                )

            farm_groups["active"].append(farm_payload)

        crop_overview = sorted(
            (
                {
                    **item,
                    "total_area": round(item["total_area"], 2),
                }
                for item in crop_summary.values()
            ),
            key=lambda item: item["crop_name"],
        )

        return api_response(
            success=True,
            message="FPO satellite overview fetched successfully.",
            result={
                "observation_date": satellite_response.get(
                    "observation_date", observation_date.isoformat()
                ),
                "crop_overview": crop_overview,
                "farms": {
                    "not_paid": {
                        "count": len(farm_groups["not_paid"]),
                        "items": farm_groups["not_paid"],
                    },
                    "awaiting_data": {
                        "count": len(farm_groups["awaiting_data"]),
                        "items": farm_groups["awaiting_data"],
                    },
                    "active": {
                        "count": len(farm_groups["active"]),
                        "items": farm_groups["active"],
                    },
                },
            },
            status_code=status.HTTP_200_OK,
        )


class FPOSatelliteMapLayersView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, fpo_profile):
        latest_subscription_qs = FarmSatelliteSubscription.objects.filter(
            farm_id=OuterRef("pk")
        ).order_by("-created_at")

        crop_queryset = FarmCrop.objects.select_related("primary_crop").order_by("-is_active")

        return (
            Farm.objects.filter(
                farmer__farmer_profile__registered_with_fpo=fpo_profile
            )
            .select_related("farmer", "farmer__farmer_profile")
            .annotate(
                latest_subscription_status=Subquery(
                    latest_subscription_qs.values("status")[:1]
                )
            )
            .filter(latest_subscription_status=SatelliteSubscriptionStatus.SYNCING)
            .only("id", "farm_name", "area", "farmer")
            .prefetch_related(Prefetch("crops", queryset=crop_queryset))
        )

    def build_response_grouped_by_farmer(self, farms, layers_by_farm_id):
        farmers_map = defaultdict(lambda: {"farmer_name": None, "farms": []})

        for farm in farms:
            farmer_profile = farm.farmer.farmer_profile
            farmer_key = farmer_profile.id
            farmers_map[farmer_key]["farmer_name"] = farmer_profile.farmer_name

            crop = next(iter(farm.crops.all()), None)
            layers_result = layers_by_farm_id.get(farm.id, {})

            farmers_map[farmer_key]["farms"].append(
                {
                    "farm_id": farm.id,
                    "farm_name": farm.farm_name,
                    "area": farm.area,
                    "crop_name": crop.primary_crop_name if crop else None,
                    "observation_date": layers_result.get("observation_date"),
                    "layers": layers_result.get("layers", []),
                }
            )

        return [
            {
                "farmer_name": data["farmer_name"],
                "farms_count": len(data["farms"]),
                "farms": data["farms"],
            }
            for data in farmers_map.values()
        ]

    def get(self, request):
        app_user = request.user.appuser

        if app_user.role != AppUser.Role.FPO:
            return api_response(
                success=False,
                message="This API is available only for FPO users.",
                result=None,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = FarmerSatelliteOverviewQuerySerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        observation_date = serializer.validated_data["observation_date"]

        farms = list(self.get_queryset(app_user.fpo_profile))
        external_ids = [farm.id for farm in farms]

        try:
            satellite_layers = fetch_farm_map_layers_by_external_ids(
                observation_date=observation_date.isoformat(),
                external_ids=external_ids,
            )
        except SatelliteServiceError as exc:
            return api_response(
                success=False,
                message=str(exc),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        layers_by_farm_id = {
            item["external_id"]: {
                key: value
                for key, value in item.items()
                if key != "external_id"
            }
            for item in satellite_layers.get("results", [])
            if isinstance(item, dict) and item.get("external_id") is not None
        }

        farmers = self.build_response_grouped_by_farmer(farms, layers_by_farm_id)

        return api_response(
            success=True,
            message="FPO farm map layers fetched successfully.",
            result={
                "observation_date": satellite_layers.get(
                    "observation_date",
                    observation_date.isoformat(),
                ),
                "farmers_count": len(farmers),
                "farmers": farmers,
            },
            status_code=status.HTTP_200_OK,
        )

# --- FPO Overview API ---
class FPOOverviewAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_user = request.user.appuser
        if app_user.role != AppUser.Role.FPO:
            return api_response(
                success=False,
                message="This API is available only for FPO users.",
                result=None,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        fpo_profile = getattr(app_user, "fpo_profile", None)
        if not fpo_profile:
            return api_response(False, "No FPO profile found.", None, 403)

        observation_date = request.query_params.get("observation_date")
        if not observation_date:
            return api_response(False, "observation_date is required (YYYY-MM-DD)", None, 400)
        try:
            parsed_date = datetime.strptime(observation_date, "%Y-%m-%d").date()
            observation_date = parsed_date - timedelta(days=1)
        except ValueError:
            return api_response(False, "Invalid observation_date format. Use YYYY-MM-DD", None, 400)

        # Get all farms under this FPO
        farms = Farm.objects.filter(farmer__farmer_profile__registered_with_fpo=fpo_profile)
        total_area = farms.aggregate(total_area=Sum("area"))['total_area'] or 0.0

        # Crop-wise area
        crop_areas = (
            FarmCrop.objects.filter(
                farm__in=farms,
                is_active=True
            )
            .values("primary_crop__name", "custom_primary_crop_name")
            .annotate(total_area=Sum("farm__area"), farms_count=Count("farm", distinct=True))
            .order_by("primary_crop__name")
        )

        # Alert counts
        moisture_alert_types = [
            "CRITICAL_WATER_STRESS",
            "OVERWATERING_DETECTED",
            "RAIN_ALERT_SKIP_IRRIGATION",
        ]
        crop_growth_alert_types = ["CROP_HEALTH_DROPPING"]

        alerts_qs = SatelliteFarmAlert.objects.filter(
            farm__in=farms,
            observation_date=observation_date
        )

        moisture_alerts_count = alerts_qs.filter(alert_type__in=moisture_alert_types).count()
        crop_growth_alerts_count = alerts_qs.filter(alert_type__in=crop_growth_alert_types).count()
        total_alerts_count = alerts_qs.count()

        return api_response(
            success=True,
            message="FPO Overview fetched successfully.",
            result={
                "observation_date": observation_date,
                "total_area": round(total_area, 2),
                "crops": [
                    {
                        "crop_name": c["primary_crop__name"] or c["custom_primary_crop_name"],
                        "total_area": round(c["total_area"] or 0, 2),
                        "farms_count": c["farms_count"]
                    }
                    for c in crop_areas
                ],
                "alerts": {
                    "total": total_alerts_count,
                    "moisture_status": moisture_alerts_count,
                    "crop_growth": crop_growth_alerts_count,
                },
            },
            status_code=200,
        )