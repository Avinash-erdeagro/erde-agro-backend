from django.urls import path

from .views import (
    FPOFarmerContactListView,
    FPOFarmerListCreateView,
    FPOSatelliteMapLayersView,
    FPOSatelliteOverviewView,
    FPOSingleFarmSatelliteMapLayersView,
    FPOFarmerFilterStateView,
    FPOFarmerDistrictListView,
    FPOFarmerListByDistrictView,
    FPOFarmerFarmsListView,
    FPOOverviewAPIView,
)

urlpatterns = [
    path(
        "satellite-overview/",
        FPOSatelliteOverviewView.as_view(),
        name="fpo-satellite-overview",
    ),
    path(
        "satellite-map-layers/",
        FPOSatelliteMapLayersView.as_view(),
        name="fpo-satellite-map-layers",
    ),
    path(
        "farms/<int:farm_id>/satellite-map-layers/",
        FPOSingleFarmSatelliteMapLayersView.as_view(),
        name="fpo-single-farm-satellite-map-layers",
    ),
    path(
        "farmers/contact-list/",
        FPOFarmerContactListView.as_view(),
        name="fpo-farmer-contact-list",
    ),
    path("farmers/", FPOFarmerListCreateView.as_view(), name="fpo-farmers"),
    path(
        "farmers/filter-states/",
            FPOFarmerFilterStateView.as_view(),
        name="fpo-farmer-filter-states",
    ),
    path(
        "farmers/states/<str:state>/districts/",
        FPOFarmerDistrictListView.as_view(),
        name="fpo-farmer-districts",
    ),
    path(
        "farmers/states/<str:state>/districts/<str:district>/farmers/",
        FPOFarmerListByDistrictView.as_view(),
        name="fpo-farmer-list-by-district",
    ),
    path(
        "farmers/<int:farmer_id>/farms/",
        FPOFarmerFarmsListView.as_view(),
        name="fpo-farmer-farms-list",
    ),
    path(
        "overview/",
        FPOOverviewAPIView.as_view(),
        name="fpo-overview",
    ),
]
