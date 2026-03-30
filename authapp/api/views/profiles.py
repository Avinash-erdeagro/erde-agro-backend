from authapp.models import FpoProfile, FarmerProfile
from ..serializers import FarmerProfileSerializer, FpoProfileSerializer
from .base import BaseModelViewSet


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
