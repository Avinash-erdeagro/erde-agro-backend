from rest_framework import viewsets
from authapp.models import FpoProfile, FarmerProfile
from ..serializers import FarmerProfileSerializer, FpoProfileSerializer

class FPOProfileViewSet(viewsets.ModelViewSet):
    queryset = FpoProfile.objects.select_related("app_user", "locality")
    serializer_class = FpoProfileSerializer


class FarmerProfileViewSet(viewsets.ModelViewSet):
    queryset = FarmerProfile.objects.select_related(
        "app_user", "locality", "registered_with_fpo"
    )
    serializer_class = FarmerProfileSerializer