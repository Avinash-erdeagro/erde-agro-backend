from rest_framework import generics, viewsets

from .models import FarmerProfile, FpoProfile
from .api.serializers import UserRegistrationSerializer, FpoProfileSerializer, FarmerProfileSerializer


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer


class FPOProfileViewSet(viewsets.ModelViewSet):
    queryset = FpoProfile.objects.select_related("app_user", "locality")
    serializer_class = FpoProfileSerializer


class FarmerProfileViewSet(viewsets.ModelViewSet):
    queryset = FarmerProfile.objects.select_related(
        "app_user", "locality", "registered_with_fpo"
    )
    serializer_class = FarmerProfileSerializer
