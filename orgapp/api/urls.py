from django.urls import path

from orgapp.api.views.farmers import OrgFarmerFarmsListView, OrgFpoFarmersListView
from orgapp.api.views.overview import OrgOverviewView
from orgapp.api.views.satellite import (
    OrgFarmBoundariesView,
    OrgFarmSatelliteChartsView,
    OrgFarmSatelliteInsightsView,
    OrgFarmSatelliteMapLayersView,
)
from orgapp.api.views.tree import OrgTreeRootView, OrgUnitChildrenView

urlpatterns = [
    path("tree/", OrgTreeRootView.as_view(), name="org-tree-root"),
    path("units/<int:unit_id>/children/", OrgUnitChildrenView.as_view(), name="org-unit-children"),
    path("fpos/<int:fpo_id>/farmers/", OrgFpoFarmersListView.as_view(), name="org-fpo-farmers"),
    path("farmers/<int:farmer_id>/farms/", OrgFarmerFarmsListView.as_view(), name="org-farmer-farms"),
    path("overview/", OrgOverviewView.as_view(), name="org-overview"),
    path("farms/geojson/", OrgFarmBoundariesView.as_view(), name="org-farm-boundaries"),
    path(
        "farms/<int:farm_id>/satellite-map-layers/",
        OrgFarmSatelliteMapLayersView.as_view(),
        name="org-farm-satellite-map-layers",
    ),
    path(
        "farms/<int:farm_id>/satellite-insights/",
        OrgFarmSatelliteInsightsView.as_view(),
        name="org-farm-satellite-insights",
    ),
    path(
        "farms/<int:farm_id>/satellite-charts/",
        OrgFarmSatelliteChartsView.as_view(),
        name="org-farm-satellite-charts",
    ),
]
