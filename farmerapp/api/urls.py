from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    SoilTypeViewSet,
    IrrigationTypeViewSet,
    CropTypeViewSet,
    FarmViewSet,
    FarmCropViewSet,
    FarmSatelliteChartsView,
    FarmSatelliteEventsView,
    FarmSatelliteInsightsView,
    FarmSatelliteResultsView,
    FarmerSatelliteMapLayersView,
    FarmerSatelliteOverviewView,
)

router = DefaultRouter()
router.register("soil-types", SoilTypeViewSet, basename="soil-type")
router.register("irrigation-types", IrrigationTypeViewSet, basename="irrigation-type")
router.register("crop-types", CropTypeViewSet, basename="crop-type")
router.register("farms", FarmViewSet, basename="farm")
router.register("farm-crops", FarmCropViewSet, basename="farm-crop")

urlpatterns = [
    path(
        "farm-events/",
        FarmSatelliteEventsView.as_view(),
        name="farm-satellite-events",
    ),
    path(
        "satellite-overview/",
        FarmerSatelliteOverviewView.as_view(),
        name="farmer-satellite-overview",
    ),
    path(
        "satellite-map-layers/",
        FarmerSatelliteMapLayersView.as_view(),
        name="farmer-satellite-map-layers",
    ),
    path(
        "farms/<int:farm_id>/satellite-results/",
        FarmSatelliteResultsView.as_view(),
        name="farm-satellite-results",
    ),
    path(
        "farms/<int:farm_id>/satellite-insights/",
        FarmSatelliteInsightsView.as_view(),
        name="farm-satellite-insights",
    ),
    path(
        "farms/<int:farm_id>/satellite-charts/",
        FarmSatelliteChartsView.as_view(),
        name="farm-satellite-charts",
    ),
    path("", include(router.urls)),
]
