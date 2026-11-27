from django.urls import path

from clientapp.api.views.overview import ClientOverviewView
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
]
