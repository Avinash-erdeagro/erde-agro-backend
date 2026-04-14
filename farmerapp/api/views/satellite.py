from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authapp.api.responses import api_response
from authapp.api.views.base import BaseAPIView
from authapp.models import AppUser
from farmerapp.models import Farm, SatelliteSubscriptionStatus, FarmCrop, FarmSatelliteSubscription
from farmerapp.api.serializers import FarmerSatelliteOverviewQuerySerializer
from farmerapp.services import (
    SatelliteServiceError,
    fetch_farm_events_by_external_ids,
    fetch_farm_insights,
    fetch_satellite_metrics_by_external_ids,
    fetch_satellite_results_by_external_id,
)
from django.db.models import Prefetch, OuterRef, Subquery



class FarmSatelliteResultsView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        app_user = user.appuser
        queryset = Farm.objects.select_related(
            "farmer", "soil_type", "irrigation_type"
        ).prefetch_related("crops", "crops__crop_type")

        if app_user.role == "FARMER":
            queryset = queryset.filter(farmer=app_user)
        elif app_user.role == "FPO":
            queryset = queryset.filter(
                farmer__farmer_profile__registered_with_fpo=app_user.fpo_profile
            )

        return queryset

    def get(self, request, farm_id):
        farm = get_object_or_404(self.get_queryset(), pk=farm_id)
        subscription = farm.satellite_subscriptions.order_by("-created_at").first()

        if not subscription:
            return api_response(
                success=False,
                message="You are not subscribed to satellite services for this farm",
                result=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if subscription.status == SatelliteSubscriptionStatus.PAID:
            return api_response(
                success=False,
                message="You will receive satellite data within 7 working days. Please check back later",
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            satellite_data = fetch_satellite_results_by_external_id(farm.id)
        except SatelliteServiceError as exc:
            return api_response(
                success=False,
                message=str(exc),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            success=True,
            message="Satellite data fetched successfully.",
            result={
                "farm_id": farm.id,
                "subscription": {
                    "id": subscription.id,
                    "status": subscription.status,
                    "subscription_start": subscription.subscription_start,
                    "subscription_end": subscription.subscription_end,
                    "irriwatch_order_uuid": subscription.irriwatch_order_uuid,
                    "irriwatch_field_uuid": subscription.irriwatch_field_uuid,
                },
                "satellite_data": satellite_data,
            },
            status_code=status.HTTP_200_OK,
        )


class FarmSatelliteInsightsView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        app_user = user.appuser
        queryset = Farm.objects.select_related(
            "farmer", "soil_type", "irrigation_type"
        ).prefetch_related("crops", "crops__crop_type")

        if app_user.role == "FARMER":
            queryset = queryset.filter(farmer=app_user)
        elif app_user.role == "FPO":
            queryset = queryset.filter(
                farmer__farmer_profile__registered_with_fpo=app_user.fpo_profile
            )

        return queryset

    def get(self, request, farm_id):
        serializer = FarmerSatelliteOverviewQuerySerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        observation_date = serializer.validated_data["observation_date"]

        farm = get_object_or_404(self.get_queryset(), pk=farm_id)
        subscription = farm.satellite_subscriptions.order_by("-created_at").first()

        if not subscription:
            return api_response(
                success=False,
                message="You are not subscribed to satellite services for this farm",
                result=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if subscription.status == SatelliteSubscriptionStatus.PAID:
            return api_response(
                success=False,
                message="You will receive satellite data within 7 working days. Please check back later",
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            insights = fetch_farm_insights(
                external_id=farm.id,
                observation_date=observation_date.isoformat(),
            )
        except SatelliteServiceError as exc:
            return api_response(
                success=False,
                message=str(exc),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            success=True,
            message="Farm insights fetched successfully.",
            result={
                "farm_id": farm.id,
                "observation_date": observation_date.isoformat(),
                "subscription": {
                    "id": subscription.id,
                    "status": subscription.status,
                    "subscription_start": subscription.subscription_start,
                    "subscription_end": subscription.subscription_end,
                    "irriwatch_order_uuid": subscription.irriwatch_order_uuid,
                    "irriwatch_field_uuid": subscription.irriwatch_field_uuid,
                },
                "insights": insights,
            },
            status_code=status.HTTP_200_OK,
        )


class FarmerSatelliteOverviewView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_user = request.user.appuser
        if app_user.role != "FARMER":
            return api_response(
                success=False,
                message="This API is available only for farmer users.",
                result=None,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = FarmerSatelliteOverviewQuerySerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        observation_date = serializer.validated_data["observation_date"]

        farms = list(
            Farm.objects.filter(farmer=app_user)
            .select_related("soil_type", "irrigation_type")
            .prefetch_related("crops", "crops__crop_type", "satellite_subscriptions")
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

            crop_name = active_crop.crop_type.name if active_crop else None
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
            message="Farmer satellite overview fetched successfully.",
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

class FarmSatelliteEventsView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get_filtered_queryset(self, app_user):
        """
        Step 1:
        - Filter farms based on role
        - Only include farms whose latest subscription is SYNCING
        """

        queryset = Farm.objects.all()

        # 🔹 Role-based filtering
        if app_user.role == AppUser.Role.FARMER:
            queryset = queryset.filter(farmer=app_user)

        elif app_user.role == AppUser.Role.FPO:
            queryset = queryset.filter(
                farmer__farmer_profile__registered_with_fpo=app_user.fpo_profile
            )

        else:
            return Farm.objects.none()

        # 🔹 Subquery: latest subscription per farm
        latest_subscription_qs = FarmSatelliteSubscription.objects.filter(
            farm_id=OuterRef("pk")   # ✅ FIXED HERE
        ).order_by("-created_at")

        # 🔹 Annotate latest subscription status
        queryset = queryset.annotate(
            latest_subscription_status=Subquery(
                latest_subscription_qs.values("status")[:1]
            )
        )

        # 🔹 Filter only farms with SYNCING subscriptions
        queryset = queryset.filter(
            latest_subscription_status__isnull=False,
            latest_subscription_status=SatelliteSubscriptionStatus.SYNCING,
        )

        return queryset

    def get_optimized_queryset(self, queryset):
        """
        Step 2:
        - Fetch only required fields
        - Prefetch crops efficiently
        """

        crop_queryset = (
            FarmCrop.objects
            .select_related("crop_type")
            .order_by("-is_active")
        )

        return (
            queryset
            .only("id", "farm_name", "area")
            .prefetch_related(
                Prefetch("crops", queryset=crop_queryset)
            )
        )

    def build_farm_payload(self, farms):
        """
        Step 3:
        Build response payload efficiently
        """
        farm_items = []

        for farm in farms:
            crops = farm.crops.all()
            crop = crops[0] if crops else None  # ✅ cleaner than iter()

            farm_items.append(
                {
                    "farm_id": farm.id,
                    "farm_name": farm.farm_name,
                    "area": farm.area,
                    "crop_name": crop.crop_type.name if crop else None,
                }
            )

        return farm_items

    def get(self, request):
        app_user = request.user.appuser

        # 🚫 Role validation
        if app_user.role not in (AppUser.Role.FARMER, AppUser.Role.FPO):
            return api_response(
                success=False,
                message="This API is available only for farmer and FPO users.",
                result=None,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # ✅ Validate query params
        serializer = FarmerSatelliteOverviewQuerySerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        observation_date = serializer.validated_data["observation_date"]

        # ✅ Step 1: Filter (includes subscription logic)
        queryset = self.get_filtered_queryset(app_user)

        # ✅ Step 2: Optimize
        queryset = self.get_optimized_queryset(queryset)

        # ⚠️ Evaluate queryset once
        farms = list(queryset)

        # ✅ Build farm data
        farm_items = self.build_farm_payload(farms)

        # Extract external IDs
        external_ids = [farm["farm_id"] for farm in farm_items]

        # ✅ External satellite service call
        try:
            satellite_events = fetch_farm_events_by_external_ids(
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

        # ✅ Final response
        return api_response(
            success=True,
            message="Farm satellite events fetched successfully.",
            result={
                "observation_date": satellite_events.get(
                    "observation_date",
                    observation_date.isoformat(),
                ),
                "farms_count": len(farm_items),
                "farms": farm_items,
                "satellite_events": satellite_events,
            },
            status_code=status.HTTP_200_OK,
        )