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
    # Stats
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

    # ── Stats ─────────────────────────────────────────────────────────────────
    path("stats/overview/", PlatformOverviewStatsView.as_view(), name="stats-overview"),
    path("stats/fpos/", FPOStatsView.as_view(), name="stats-fpos"),

    # ── Notifications ─────────────────────────────────────────────────────────
    path("notifications/device-tokens/", DeviceTokenStatsView.as_view(), name="notif-tokens"),
    path("notifications/coverage/", UserNotificationCoverageView.as_view(), name="notif-coverage"),

    # ── Payments ──────────────────────────────────────────────────────────────
    path("payments/plans/", SatellitePlanListView.as_view(), name="payment-plans"),
    path("payments/subscriptions/summary/", SubscriptionSummaryView.as_view(), name="sub-summary"),
    path("payments/subscriptions/by-fpo/", FPOSubscriptionDetailView.as_view(), name="sub-by-fpo"),
]

