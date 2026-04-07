from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    SoilTypeViewSet,
    IrrigationTypeViewSet,
    CropTypeViewSet,
    FarmViewSet,
    FarmCropViewSet,
)

router = DefaultRouter()
router.register("soil-types", SoilTypeViewSet, basename="soil-type")
router.register("irrigation-types", IrrigationTypeViewSet, basename="irrigation-type")
router.register("crop-types", CropTypeViewSet, basename="crop-type")
router.register("farms", FarmViewSet, basename="farm")
router.register("farm-crops", FarmCropViewSet, basename="farm-crop")

urlpatterns = [
    path("", include(router.urls)),
]