from django.urls import path

from .views import (
    FPOFarmerContactListView,
    FPOFarmerListCreateView,
    FPOSatelliteMapLayersView,
    FPOSatelliteOverviewView,
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
        "farmers/contact-list/",
        FPOFarmerContactListView.as_view(),
        name="fpo-farmer-contact-list",
    ),
    path("farmers/", FPOFarmerListCreateView.as_view(), name="fpo-farmers"),
]
