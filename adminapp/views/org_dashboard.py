"""
Org-user farms & satellite dashboard (SUPER_ADMIN + ORG_USER).

The same dashboard the FPO web app shows (state → district → farmer → farm
tree, overview, farm boundaries map, farm satellite map layers), covering
every farm under the FPOs linked to the caller's hierarchy node and the nodes
below it — e.g. an HO account at the top of an organization sees every farm
of the organization.

Each view is the FPO view with OrgFarmerScopeMixin in front, so the request
params and response shapes are identical to the /fpo/... endpoints; only the
set of farmers differs. Farm insights / charts are served by the existing
/farmer/farms/<id>/satellite-insights|charts/ endpoints, which scope ORG_USER
the same way.
"""

from fpoapp.api.views import (
    FPOFarmBoundariesAPIView,
    FPOFarmerDistrictListView,
    FPOFarmerFarmsListView,
    FPOFarmerFilterStateView,
    FPOFarmerListByDistrictView,
    FPOOverviewAPIView,
    FPOSingleFarmSatelliteMapLayersView,
)
from fpoapp.api.views.scope import OrgFarmerScopeMixin


class OrgDashboardFilterStateView(OrgFarmerScopeMixin, FPOFarmerFilterStateView):
    """GET /super-admin/org-data/dashboard/farmers/filter-states/"""


class OrgDashboardDistrictListView(OrgFarmerScopeMixin, FPOFarmerDistrictListView):
    """GET /super-admin/org-data/dashboard/farmers/states/<state>/districts/"""


class OrgDashboardFarmerListByDistrictView(OrgFarmerScopeMixin, FPOFarmerListByDistrictView):
    """GET /super-admin/org-data/dashboard/farmers/states/<state>/districts/<district>/farmers/"""


class OrgDashboardFarmerFarmsListView(OrgFarmerScopeMixin, FPOFarmerFarmsListView):
    """GET /super-admin/org-data/dashboard/farmers/<farmer_id>/farms/"""


class OrgDashboardOverviewView(OrgFarmerScopeMixin, FPOOverviewAPIView):
    """GET /super-admin/org-data/dashboard/overview/"""


class OrgDashboardFarmBoundariesView(OrgFarmerScopeMixin, FPOFarmBoundariesAPIView):
    """GET /super-admin/org-data/dashboard/farms/geojson/"""


class OrgDashboardFarmMapLayersView(OrgFarmerScopeMixin, FPOSingleFarmSatelliteMapLayersView):
    """GET /super-admin/org-data/dashboard/farms/<farm_id>/satellite-map-layers/"""
