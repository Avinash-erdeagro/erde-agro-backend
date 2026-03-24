from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api.views import FarmerProfileViewSet, FPOProfileViewSet, UserRegistrationView

router = DefaultRouter()
router.register("fpo-profiles", FPOProfileViewSet, basename="fpo-profile")
router.register("farmer-profiles", FarmerProfileViewSet, basename="farmer-profile")

urlpatterns = [
	path("register/", UserRegistrationView.as_view(), name="register"),
	path("", include(router.urls)),
]
