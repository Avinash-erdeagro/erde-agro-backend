from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FarmerFirebaseLoginView,
    FarmerMyProfileView,
    FarmerProfileViewSet,
    FPOListView,
    FPOLoginView,
    FPOMyProfileView,
    FPOProfileViewSet,
    PincodeLookupView,
    UserRegistrationView,
    TokenRefreshApiView
)

router = DefaultRouter()
router.register("fpo-profiles", FPOProfileViewSet, basename="fpo-profile")
router.register("farmer-profiles", FarmerProfileViewSet, basename="farmer-profile")

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("pincode/<str:pin_code>/", PincodeLookupView.as_view(), name="pincode-lookup"),
    path("firebase-login/", FarmerFirebaseLoginView.as_view(), name="farmer-firebase-login"),
    path("fpo/login/", FPOLoginView.as_view(), name="fpo-login"),
    path("token/refresh/", TokenRefreshApiView.as_view(), name="token-refresh"),
    path("farmer/my-profile/", FarmerMyProfileView.as_view(), name="farmer-my-profile"),
    path("fpo/my-profile/", FPOMyProfileView.as_view(), name="fpo-my-profile"),
    path("fpo-list/", FPOListView.as_view(), name="fpo-list"),
    path("", include(router.urls)),
]
