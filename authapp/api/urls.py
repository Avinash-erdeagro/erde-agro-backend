from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FarmerProfileViewSet, FPOProfileViewSet, UserRegistrationView, PincodeLookupView, FarmerFirebaseLoginView

router = DefaultRouter()
router.register("fpo-profiles", FPOProfileViewSet, basename="fpo-profile")
router.register("farmer-profiles", FarmerProfileViewSet, basename="farmer-profile")

urlpatterns = [
	path("register/", UserRegistrationView.as_view(), name="register"),
    path("pincode/<str:pin_code>/", PincodeLookupView.as_view(), name="pincode-lookup"),
    path("farmer/login/", FarmerFirebaseLoginView.as_view(), name="farmer-firebase-login"),
	path("", include(router.urls)),
]
