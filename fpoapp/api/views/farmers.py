from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authapp.api.responses import api_response
from authapp.api.views.base import BaseAPIView
from authapp.models import AppUser, FarmerProfile, FpoProfile
from fpoapp.api.serializers import (
    FPOFarmerContactListSerializer,
    FPOFarmerCreateSerializer,
    FPOFarmerListSerializer,
)
from fpoapp.services import create_farmer_under_fpo
from farmerapp.models import FarmCrop
from django.db.models import Count, Prefetch, OuterRef, Exists
from satelliteapp.models import SatelliteFarmAlert, SatelliteFarmNotification
from datetime import datetime, timedelta

class FPOBaseAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get_fpo_profile(self):
        app_user = self.request.user.appuser
        if app_user.role != AppUser.Role.FPO:
            return None
        return getattr(app_user, "fpo_profile", None)

    def ensure_fpo_profile(self):
        fpo_profile = self.get_fpo_profile()
        if not fpo_profile:
            return api_response(
                success=False,
                message="This API is available only for FPO users.",
                result=None,
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return fpo_profile


class FPOFarmerListCreateView(FPOBaseAPIView):
    def get(self, request):
        fpo_profile = self.ensure_fpo_profile()
        if not isinstance(fpo_profile, FpoProfile):
            return fpo_profile

        farmers = FarmerProfile.objects.filter(
            registered_with_fpo=fpo_profile
        ).select_related(
            "app_user",
            "app_user__user",
            "locality",
        ).prefetch_related(
            Prefetch(
                "app_user__farms",
                queryset=AppUser.farms.rel.related_model.objects.prefetch_related("crops")
            )
        )

        serializer = FPOFarmerListSerializer(farmers, many=True)
        return api_response(
            success=True,
            message="FPO farmers fetched successfully.",
            result={"farmers": serializer.data},
            status_code=status.HTTP_200_OK,
        )

    def post(self, request):
        fpo_profile = self.ensure_fpo_profile()
        if not isinstance(fpo_profile, FpoProfile):
            return fpo_profile

        serializer = FPOFarmerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = create_farmer_under_fpo(
            fpo_profile=fpo_profile,
            validated_data=dict(serializer.validated_data),
        )
        response_serializer = FPOFarmerCreateSerializer(result)

        return api_response(
            success=True,
            message="Farmer created successfully under the FPO.",
            result=response_serializer.data,
            status_code=status.HTTP_201_CREATED,
        )


class FPOFarmerContactListView(FPOBaseAPIView):
    def get(self, request):
        fpo_profile = self.ensure_fpo_profile()
        if not isinstance(fpo_profile, FpoProfile):
            return fpo_profile

        farmers = FarmerProfile.objects.filter(
            registered_with_fpo=fpo_profile
        ).only("farmer_name", "contact_number")

        serializer = FPOFarmerContactListSerializer(farmers, many=True)
        return api_response(
            success=True,
            message="FPO farmer contacts fetched successfully.",
            result={"farmers": serializer.data},
            status_code=status.HTTP_200_OK,
        )

# Filter States endpoint for farmers registered under the FPO
class FPOFarmerFilterStateView(FPOBaseAPIView):
    def get(self, request):
        fpo_profile = self.ensure_fpo_profile()
        if not isinstance(fpo_profile, FpoProfile):
            return fpo_profile

        # Get & validate observation_date
        observation_date = request.query_params.get("observation_date")

        if not observation_date:
            return api_response(
                success=False,
                message="observation_date is required (YYYY-MM-DD)",
                result=None,
                status_code=400,
            )

        try:
            # Parse the date and subtract one day
            parsed_date = datetime.strptime(observation_date, "%Y-%m-%d").date()
            observation_date = parsed_date - timedelta(days=1)

        except ValueError:
            return api_response(
                success=False,
                message="Invalid observation_date format. Use YYYY-MM-DD",
                result=None,
                status_code=400,
            )

        # Subquery alerts
        alerts_subquery = SatelliteFarmAlert.objects.filter(
            farm__farmer__farmer_profile__registered_with_fpo=fpo_profile,
            farm__farmer__farmer_profile__locality__state=OuterRef("locality__state"),
            observation_date=observation_date
        )

        # Subquery notifications
        notifications_subquery = SatelliteFarmNotification.objects.filter(
            farm__farmer__farmer_profile__registered_with_fpo=fpo_profile,
            farm__farmer__farmer_profile__locality__state=OuterRef("locality__state"),
            observation_date=observation_date
        )

        # Main query
        states = (
            FarmerProfile.objects
            .filter(
                registered_with_fpo=fpo_profile,
                locality__state__isnull=False
            )
            .exclude(locality__state="")
            .values("locality__state")
            .annotate(
                farmers_count=Count("id"),
                has_alert=Exists(alerts_subquery),
                has_notification=Exists(notifications_subquery)
            )
            .order_by("locality__state")
        )

        return api_response(
            success=True,
            message="States with farmer counts and alerts.",
            result={"states": list(states)},
            status_code=200,
        )

# Filter Districts for a given state for farmers registered under the FPO
class FPOFarmerDistrictListView(FPOBaseAPIView):
    def get(self, request, state):
        fpo_profile = self.ensure_fpo_profile()
        if not isinstance(fpo_profile, FpoProfile):
            return fpo_profile

        # Get & validate observation_date
        observation_date = request.query_params.get("observation_date")

        if not observation_date:
            return api_response(
                success=False,
                message="observation_date is required (YYYY-MM-DD)",
                result=None,
                status_code=400,
            )

        try:
            # Parse the date and subtract one day
            parsed_date = datetime.strptime(observation_date, "%Y-%m-%d").date()
            from datetime import timedelta
            observation_date = parsed_date - timedelta(days=1)

        except ValueError:
            return api_response(False, "Invalid date format", None, 400)

        # 🔹 Alerts subquery
        alerts_subquery = SatelliteFarmAlert.objects.filter(
            farm__farmer__farmer_profile__registered_with_fpo=fpo_profile,
            farm__farmer__farmer_profile__locality__district=OuterRef("locality__district"),
            farm__farmer__farmer_profile__locality__state__iexact=state,
            observation_date=observation_date
        )

        # 🔹 Notifications subquery
        notifications_subquery = SatelliteFarmNotification.objects.filter(
            farm__farmer__farmer_profile__registered_with_fpo=fpo_profile,
            farm__farmer__farmer_profile__locality__district=OuterRef("locality__district"),
            farm__farmer__farmer_profile__locality__state__iexact=state,
            observation_date=observation_date
        )

        districts = (
            FarmerProfile.objects
            .filter(
                registered_with_fpo=fpo_profile,
                locality__state__iexact=state,
                locality__district__isnull=False
            )
            .exclude(locality__district="")
            .values("locality__district")
            .annotate(
                farmers_count=Count("id"),
                has_alert=Exists(alerts_subquery),
                has_notification=Exists(notifications_subquery)
            )
            .order_by("locality__district")
        )

        return api_response(
            success=True,
            message=f"Districts in state '{state}'.",
            result={"districts": list(districts)},
            status_code=200,
        )

# List farmers for a given state and district for farmers registered under the FPO, along with alert/notification status
class FPOFarmerListByDistrictView(FPOBaseAPIView):
    def get(self, request, state, district):
        fpo_profile = self.ensure_fpo_profile()
        if not isinstance(fpo_profile, FpoProfile):
            return fpo_profile

        # ✅ Get & validate observation_date
        observation_date = request.query_params.get("observation_date")

        if not observation_date:
            return api_response(
                success=False,
                message="observation_date is required (YYYY-MM-DD)",
                result=None,
                status_code=400,
            )

        try:
            parsed_date = datetime.strptime(observation_date, "%Y-%m-%d").date()
            observation_date = parsed_date - timedelta(days=1)
        except ValueError:
            return api_response(
                success=False,
                message="Invalid observation_date format",
                result=None,
                status_code=400,
            )

        # ✅ Subqueries (fast)
        alerts_subquery = SatelliteFarmAlert.objects.filter(
            farm__farmer=OuterRef("app_user"),
            observation_date=observation_date
        )

        notifications_subquery = SatelliteFarmNotification.objects.filter(
            farm__farmer=OuterRef("app_user"),
            observation_date=observation_date
        )

        farmers = (
            FarmerProfile.objects
            .filter(
                registered_with_fpo=fpo_profile,
                locality__state__iexact=state,
                locality__district__iexact=district,
            )
            .annotate(
                farms_count=Count("app_user__farms"),
                has_alert=Exists(alerts_subquery),
                has_notification=Exists(notifications_subquery)
            )
            .values(
                "id",
                "farmer_name",
                "farms_count",
                "has_alert",
                "has_notification"
            )
            .order_by("farmer_name")
        )

        return api_response(
            success=True,
            message=f"Farmers in '{district}', '{state}'",
            result={"farmers": list(farmers)},
            status_code=200,
        )
    
# Farms for a given farmer_id for farmers registered under the FPO, along with alert/notification status for the given observation_date
class FPOFarmerFarmsListView(FPOBaseAPIView):
    def get(self, request, farmer_id):
        fpo_profile = self.ensure_fpo_profile()
        if not isinstance(fpo_profile, FpoProfile):
            return fpo_profile

        # ✅ Get & validate observation_date
        observation_date = request.query_params.get("observation_date")

        if not observation_date:
            return api_response(
                success=False,
                message="observation_date is required (YYYY-MM-DD)",
                result=None,
                status_code=400,
            )

        try:
            parsed_date = datetime.strptime(observation_date, "%Y-%m-%d").date()
            observation_date = parsed_date - timedelta(days=1)
        except ValueError:
            return api_response(
                success=False,
                message="Invalid observation_date format",
                result=None,
                status_code=400,
            )

        try:
            farmer = FarmerProfile.objects.select_related("app_user").get(
                id=farmer_id,
                registered_with_fpo=fpo_profile
            )
        except FarmerProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Farmer not found or not registered under this FPO.",
                result=None,
                status_code=404,
            )

        farms = (
            farmer.app_user.farms
            .all()
            .prefetch_related(
                # crops
                Prefetch(
                    "crops",
                    queryset=FarmCrop.objects.filter(is_active=True).order_by("-plantation_date"),
                    to_attr="active_crops"
                ),
                # alerts
                Prefetch(
                    "satellite_alerts",
                    queryset=SatelliteFarmAlert.objects.filter(
                        observation_date=observation_date
                    ),
                    to_attr="alerts_for_date"
                ),
                # notifications
                Prefetch(
                    "satellite_notifications",
                    queryset=SatelliteFarmNotification.objects.filter(
                        observation_date=observation_date
                    ),
                    to_attr="notifications_for_date"
                ),
            )
        )

        farm_list = []

        for farm in farms:
            active_crop = None
            plantation_date = None

            if getattr(farm, "active_crops", []):
                active = farm.active_crops[0]
                active_crop = active.primary_crop_name
                plantation_date = active.plantation_date

            farm_list.append({
                "id": farm.id,
                "name": farm.farm_name,
                "area": farm.area,
                "active_crop": active_crop,
                "plantation_date": plantation_date,
                "has_alert": bool(getattr(farm, "alerts_for_date", [])),
                "has_notification": bool(getattr(farm, "notifications_for_date", [])),
            })

        return api_response(
            success=True,
            message=f"Farms for farmer id {farmer_id}.",
            result={"farms": farm_list},
            status_code=200,
        )