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
from django.db.models import Count, Prefetch

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
        ).prefetch_related("app_user__farms")

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

        states = (
            FarmerProfile.objects
            .filter(
                registered_with_fpo=fpo_profile,
                locality__state__isnull=False
            )
            .exclude(locality__state="")
            .values("locality__state")
            .annotate(farmers_count=Count("id"))
            .order_by("locality__state")
        )

        return api_response(
            success=True,
            message="List of states with farmer counts.",
            result={"states": list(states)},
            status_code=status.HTTP_200_OK,
        )

# Filter Districts for a given state for farmers registered under the FPO
class FPOFarmerDistrictListView(FPOBaseAPIView):
    def get(self, request, state):
        fpo_profile = self.ensure_fpo_profile()
        if not isinstance(fpo_profile, FpoProfile):
            return fpo_profile

        districts = (
            FarmerProfile.objects
            .filter(
                registered_with_fpo=fpo_profile,
                locality__state__iexact=state,  
                locality__district__isnull=False
            )
            .exclude(locality__district="")
            .values("locality__district")
            .annotate(farmers_count=Count("id"))
            .order_by("locality__district")
        )

        return api_response(
            success=True,
            message=f"List of districts in state '{state}'.",
            result={"districts": list(districts)},
            status_code=status.HTTP_200_OK,
        )


class FPOFarmerListByDistrictView(FPOBaseAPIView):
    def get(self, request, state, district):
        fpo_profile = self.ensure_fpo_profile()
        if not isinstance(fpo_profile, FpoProfile):
            return fpo_profile

        farmers = (
            FarmerProfile.objects
            .filter(
                registered_with_fpo=fpo_profile,
                locality__state__iexact=state,
                locality__district__iexact=district,
            )
            .annotate(farms_count=Count("app_user__farms"))
            .values(
                "id",
                "farmer_name",
                "farms_count"
            )
            .order_by("farmer_name")
        )

        farmer_list = [
            {
                "id": f["id"],
                "name": f["farmer_name"],
                "farms_count": f["farms_count"],
            }
            for f in farmers
        ]

        return api_response(
            success=True,
            message=f"Farmers in district '{district}', state '{state}'.",
            result={"farmers": farmer_list},
            status_code=status.HTTP_200_OK,
        )
    
# Farms for a given farmer_id
class FPOFarmerFarmsListView(FPOBaseAPIView):
    def get(self, request, farmer_id):
        fpo_profile = self.ensure_fpo_profile()
        if not isinstance(fpo_profile, FpoProfile):
            return fpo_profile

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
                status_code=status.HTTP_404_NOT_FOUND,
            )

        farms = (
            farmer.app_user.farms
            .all()
            .prefetch_related(
                Prefetch(
                    "crops",
                    queryset=FarmCrop.objects.filter(is_active=True).order_by("-plantation_date"),
                    to_attr="active_crops"
                )
            )
        )

        farm_list = []

        for farm in farms:
            active_crop = None
            plantation_date = None

            if hasattr(farm, "active_crops") and farm.active_crops:
                active = farm.active_crops[0]
                active_crop = active.primary_crop_name
                plantation_date = active.plantation_date

            farm_list.append({
                "id": farm.id,
                "name": farm.farm_name,
                "area": farm.area,
                "active_crop": active_crop,
                "plantation_date": plantation_date,
            })

        return api_response(
            success=True,
            message=f"Farms for farmer id {farmer_id}.",
            result={"farms": farm_list},
            status_code=status.HTTP_200_OK,
        )