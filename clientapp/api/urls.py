from django.urls import path

from clientapp.api.views.overview import ClientOverviewView
from clientapp.api.views.satellite import (
    ClientFarmBoundariesView,
    ClientFarmSatelliteChartsView,
    ClientFarmSatelliteInsightsView,
    ClientFarmSatelliteMapLayersView,
)
from clientapp.api.views.farmers import (
    ClientFarmerDistrictListView,
    ClientFarmerFarmsListView,
    ClientFarmerFilterStateView,
    ClientFarmerListByDistrictView,
)

urlpatterns = [
    path("overview/", ClientOverviewView.as_view(), name="client-overview"),
    path(
        "farmers/filter-states/",
        ClientFarmerFilterStateView.as_view(),
        name="client-farmer-filter-states",
    ),
    path(
        "farmers/states/<str:state>/districts/",
        ClientFarmerDistrictListView.as_view(),
        name="client-farmer-districts",
    ),
    path(
        "farmers/states/<str:state>/districts/<str:district>/farmers/",
        ClientFarmerListByDistrictView.as_view(),
        name="client-farmers-in-district",
    ),
    path(
        "farmers/<int:farmer_id>/farms/",
        ClientFarmerFarmsListView.as_view(),
        name="client-farmer-farms",
    ),
    path("farms/geojson/", ClientFarmBoundariesView.as_view(), name="client-farm-boundaries"),
    path(
        "farms/<int:farm_id>/satellite-map-layers/",
        ClientFarmSatelliteMapLayersView.as_view(),
        name="client-farm-satellite-map-layers",
    ),
    path(
        "farms/<int:farm_id>/satellite-insights/",
        ClientFarmSatelliteInsightsView.as_view(),
        name="client-farm-satellite-insights",
    ),
    path(
        "farms/<int:farm_id>/satellite-charts/",
        ClientFarmSatelliteChartsView.as_view(),
        name="client-farm-satellite-charts",
    ),
]
