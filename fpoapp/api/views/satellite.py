from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authapp.api.responses import api_response
from authapp.api.views.base import BaseAPIView
from authapp.models import AppUser
from farmerapp.api.serializers import FarmerSatelliteOverviewQuerySerializer
from farmerapp.models import Farm, SatelliteSubscriptionStatus
from farmerapp.services import (
    SatelliteServiceError,
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
