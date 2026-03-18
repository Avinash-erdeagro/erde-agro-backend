from rest_framework import generics, viewsets

from .models import FarmerProfile, FpoProfile
from .serializers import (
	FarmerProfileSerializer,
	FpoProfileSerializer,
	UserRegistrationSerializer,
)


class UserRegistrationView(generics.CreateAPIView):
	serializer_class = UserRegistrationSerializer


class FPOProfileViewSet(viewsets.ModelViewSet):
	queryset = FpoProfile.objects.select_related("app_user", "address")
	serializer_class = FpoProfileSerializer


class FarmerProfileViewSet(viewsets.ModelViewSet):
	queryset = FarmerProfile.objects.select_related(
		"app_user", "address", "registered_with_fpo"
	)
	serializer_class = FarmerProfileSerializer
