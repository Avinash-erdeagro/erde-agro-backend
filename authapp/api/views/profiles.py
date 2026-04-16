from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authapp.api.responses import api_response
from authapp.models import FpoProfile, FarmerProfile, AppUser
from ..serializers import (
    FarmerMyProfileSerializer,
    FarmerProfileSerializer,
    FPOListSerializer,
    FPOMyProfileSerializer,
    FpoProfileSerializer,
)
from .base import BaseAPIView, BaseModelViewSet


class FPOProfileViewSet(BaseModelViewSet):
    queryset = FpoProfile.objects.select_related("app_user", "locality")
    serializer_class = FpoProfileSerializer
    action_success_messages = {
        "list": "FPO profiles fetched successfully.",
        "retrieve": "FPO profile fetched successfully.",
        "create": "FPO profile created successfully.",
        "update": "FPO profile updated successfully.",
        "partial_update": "FPO profile updated successfully.",
        "destroy": "FPO profile deleted successfully.",
    }


class FarmerProfileViewSet(BaseModelViewSet):
    queryset = FarmerProfile.objects.select_related(
        "app_user", "locality", "registered_with_fpo"
    )
    serializer_class = FarmerProfileSerializer
    action_success_messages = {
        "list": "Farmer profiles fetched successfully.",
        "retrieve": "Farmer profile fetched successfully.",
        "create": "Farmer profile created successfully.",
        "update": "Farmer profile updated successfully.",
        "partial_update": "Farmer profile updated successfully.",
        "destroy": "Farmer profile deleted successfully.",
    }


class FarmerMyProfileView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get_profile(self, request):
        app_user = request.user.appuser
        if app_user.role != AppUser.Role.FARMER:
            return None, api_response(
                success=False,
                message="This API is available only for farmer users.",
                result=None,
                status_code=status.HTTP_403_FORBIDDEN,
            )
        profile = FarmerProfile.objects.select_related(
            "locality", "registered_with_fpo"
        ).filter(app_user=app_user).first()
        if not profile:
            return None, api_response(
                success=False,
                message="Farmer profile not found.",
                result=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return profile, None

    def get(self, request):
        profile, error = self.get_profile(request)
        if error:
            return error
        serializer = FarmerMyProfileSerializer(profile)
        return api_response(
            success=True,
            message="Farmer profile fetched successfully.",
            result=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    def patch(self, request):
        profile, error = self.get_profile(request)
        if error:
            return error
        serializer = FarmerMyProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(
            success=True,
            message="Farmer profile updated successfully.",
            result=serializer.data,
            status_code=status.HTTP_200_OK,
        )


class FPOMyProfileView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get_profile(self, request):
        app_user = request.user.appuser
        if app_user.role != AppUser.Role.FPO:
            return None, api_response(
                success=False,
                message="This API is available only for FPO users.",
                result=None,
                status_code=status.HTTP_403_FORBIDDEN,
            )
        profile = FpoProfile.objects.select_related("locality").filter(
            app_user=app_user
        ).first()
        if not profile:
            return None, api_response(
                success=False,
                message="FPO profile not found.",
                result=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return profile, None

    def get(self, request):
        profile, error = self.get_profile(request)
        if error:
            return error
        serializer = FPOMyProfileSerializer(profile)
        return api_response(
            success=True,
            message="FPO profile fetched successfully.",
            result=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    def patch(self, request):
        profile, error = self.get_profile(request)
        if error:
            return error
        serializer = FPOMyProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(
            success=True,
            message="FPO profile updated successfully.",
            result=serializer.data,
            status_code=status.HTTP_200_OK,
        )


class FPOListView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        fpos = FpoProfile.objects.only("id", "fpo_name").order_by("fpo_name")
        serializer = FPOListSerializer(fpos, many=True)
        return api_response(
            success=True,
            message="FPO list fetched successfully.",
            result={"fpos": serializer.data},
            status_code=status.HTTP_200_OK,
        )
