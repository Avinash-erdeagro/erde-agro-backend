from django.urls import path

from adminapp.views import (
    # Hierarchy management
    AdminUserCreateView,
    HierarchyLevelDetailView,
    HierarchyLevelListCreateView,
    OrgMembershipDetailView,
    OrgMembershipListCreateView,
    OrgUnitDetailView,
    OrgUnitFPODetailView,
    OrgUnitFPOListCreateView,
    OrgUnitListCreateView,
    OrganizationDetailView,
    OrganizationListCreateView,
    # Org data (hierarchy-scoped)
    HierarchyFPODetailView,
    HierarchyFPOListView,
    HierarchyFarmerDetailView,
    HierarchyFarmerListView,
    # Org-user farms & satellite dashboard
    OrgDashboardDistrictListView,
    OrgDashboardFarmBoundariesView,
    OrgDashboardFarmerFarmsListView,
    OrgDashboardFarmerListByDistrictView,
    OrgDashboardFarmMapLayersView,
    OrgDashboardFilterStateView,
    OrgDashboardOverviewView,
    # Stats
    FPOAreaStatsView,
    FPOStatsView,
    PlatformOverviewStatsView,
    # Notifications
    DeviceTokenStatsView,
    UserNotificationCoverageView,
    # Payments
    FPOSubscriptionDetailView,
    SatellitePlanListView,
    SubscriptionSummaryView,
)

app_name = "adminapp"

urlpatterns = [
    # ── Hierarchy management ──────────────────────────────────────────────────
    path("organizations/", OrganizationListCreateView.as_view(), name="org-list"),
    path("organizations/<int:pk>/", OrganizationDetailView.as_view(), name="org-detail"),
    path("hierarchy-levels/", HierarchyLevelListCreateView.as_view(), name="level-list"),
    path("hierarchy-levels/<int:pk>/", HierarchyLevelDetailView.as_view(), name="level-detail"),
    path("org-units/", OrgUnitListCreateView.as_view(), name="unit-list"),
    path("org-units/<int:pk>/", OrgUnitDetailView.as_view(), name="unit-detail"),
    path("memberships/", OrgMembershipListCreateView.as_view(), name="membership-list"),
    path("memberships/<int:pk>/", OrgMembershipDetailView.as_view(), name="membership-detail"),
    path("fpo-links/", OrgUnitFPOListCreateView.as_view(), name="fpo-link-list"),
    path("fpo-links/<int:pk>/", OrgUnitFPODetailView.as_view(), name="fpo-link-detail"),
    path("users/", AdminUserCreateView.as_view(), name="admin-user-create"),

    # ── Org data (hierarchy-scoped, SUPER_ADMIN + ORG_USER) ──────────────────
    path("org-data/fpos/", HierarchyFPOListView.as_view(), name="org-fpo-list"),
    path("org-data/fpos/<int:pk>/", HierarchyFPODetailView.as_view(), name="org-fpo-detail"),
    path("org-data/farmers/", HierarchyFarmerListView.as_view(), name="org-farmer-list"),
    path("org-data/farmers/<int:pk>/", HierarchyFarmerDetailView.as_view(), name="org-farmer-detail"),

    # ── Org-user farms & satellite dashboard (same shapes as /fpo/...) ───────
    path("org-data/dashboard/overview/", OrgDashboardOverviewView.as_view(), name="org-dash-overview"),
    path("org-data/dashboard/farmers/filter-states/", OrgDashboardFilterStateView.as_view(), name="org-dash-states"),
    path(
        "org-data/dashboard/farmers/states/<str:state>/districts/",
        OrgDashboardDistrictListView.as_view(),
        name="org-dash-districts",
    ),
    path(
        "org-data/dashboard/farmers/states/<str:state>/districts/<str:district>/farmers/",
        OrgDashboardFarmerListByDistrictView.as_view(),
        name="org-dash-farmers-in-district",
    ),
    path(
        "org-data/dashboard/farmers/<int:farmer_id>/farms/",
        OrgDashboardFarmerFarmsListView.as_view(),
        name="org-dash-farmer-farms",
    ),
    path("org-data/dashboard/farms/geojson/", OrgDashboardFarmBoundariesView.as_view(), name="org-dash-farm-boundaries"),
    path(
        "org-data/dashboard/farms/<int:farm_id>/satellite-map-layers/",
        OrgDashboardFarmMapLayersView.as_view(),
        name="org-dash-farm-map-layers",
    ),

    # ── Stats ─────────────────────────────────────────────────────────────────
    path("stats/overview/", PlatformOverviewStatsView.as_view(), name="stats-overview"),
    path("stats/fpos/", FPOStatsView.as_view(), name="stats-fpos"),
    path("stats/fpo-area/", FPOAreaStatsView.as_view(), name="stats-fpo-area"),

    # ── Notifications ─────────────────────────────────────────────────────────
    path("notifications/device-tokens/", DeviceTokenStatsView.as_view(), name="notif-tokens"),
    path("notifications/coverage/", UserNotificationCoverageView.as_view(), name="notif-coverage"),

    # ── Payments ──────────────────────────────────────────────────────────────
    path("payments/plans/", SatellitePlanListView.as_view(), name="payment-plans"),
    path("payments/subscriptions/summary/", SubscriptionSummaryView.as_view(), name="sub-summary"),
    path("payments/subscriptions/by-fpo/", FPOSubscriptionDetailView.as_view(), name="sub-by-fpo"),
]

