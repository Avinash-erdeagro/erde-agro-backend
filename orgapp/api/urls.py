from django.urls import path

from orgapp.api.views.farmers import OrgFarmerFarmsListView, OrgFpoFarmersListView
from orgapp.api.views.overview import OrgOverviewView
from orgapp.api.views.satellite import OrgFarmBoundariesView
from orgapp.api.views.tree import OrgTreeRootView, OrgUnitChildrenView

urlpatterns = [
    path("tree/", OrgTreeRootView.as_view(), name="org-tree-root"),
    path("units/<int:unit_id>/children/", OrgUnitChildrenView.as_view(), name="org-unit-children"),
    path("fpos/<int:fpo_id>/farmers/", OrgFpoFarmersListView.as_view(), name="org-fpo-farmers"),
    path("farmers/<int:farmer_id>/farms/", OrgFarmerFarmsListView.as_view(), name="org-farmer-farms"),
    path("overview/", OrgOverviewView.as_view(), name="org-overview"),
    path("farms/geojson/", OrgFarmBoundariesView.as_view(), name="org-farm-boundaries"),
]
