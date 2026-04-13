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

# TODO this needs to be removed
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
