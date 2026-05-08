from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FarmerFirebaseLoginView,
    FarmerOTPCheckView,
    FarmerMyProfileView,
    FarmerProfileViewSet,
    FPOListView,
    FPOLoginView,
    FPOMyProfileView,
    FPOProfileViewSet,
    PincodeLookupView,
    UserRegistrationView,
    TokenRefreshApiView,
    WebAppLoginView,
    ImpersonateUserView,
    HierarchyLevelListView,
    AccessibleOrgUnitListView,
    OrgUnitSubtreeView,
    OrganizationListCreateView,
    OrganizationDetailView,
    HierarchyLevelListCreateView,
    HierarchyLevelDetailView,
    OrgUnitListCreateView,
    OrgUnitDetailView,
    OrgMembershipListCreateView,
    OrgMembershipDetailView,
    OrgUnitFPOListCreateView,
    OrgUnitFPODetailView,
    AdminUserCreateView,
)

router = DefaultRouter()
router.register("fpo-profiles", FPOProfileViewSet, basename="fpo-profile")
router.register("farmer-profiles", FarmerProfileViewSet, basename="farmer-profile")

hierarchy_urlpatterns = [
    path("impersonate/<int:user_id>/", ImpersonateUserView.as_view(), name="hierarchy-impersonate"),
    path("levels/", HierarchyLevelListView.as_view(), name="hierarchy-levels"),
    path("units/", AccessibleOrgUnitListView.as_view(), name="hierarchy-units"),
    path("units/<int:pk>/subtree/", OrgUnitSubtreeView.as_view(), name="hierarchy-unit-subtree"),
]

# SUPER_ADMIN management endpoints
admin_urlpatterns = [
    path("organizations/", OrganizationListCreateView.as_view(), name="admin-organizations"),
    path("organizations/<int:pk>/", OrganizationDetailView.as_view(), name="admin-organization-detail"),
    path("hierarchy-levels/", HierarchyLevelListCreateView.as_view(), name="admin-hierarchy-levels"),
    path("hierarchy-levels/<int:pk>/", HierarchyLevelDetailView.as_view(), name="admin-hierarchy-level-detail"),
    path("org-units/", OrgUnitListCreateView.as_view(), name="admin-org-units"),
    path("org-units/<int:pk>/", OrgUnitDetailView.as_view(), name="admin-org-unit-detail"),
    path("memberships/", OrgMembershipListCreateView.as_view(), name="admin-memberships"),
    path("memberships/<int:pk>/", OrgMembershipDetailView.as_view(), name="admin-membership-detail"),
    path("fpo-links/", OrgUnitFPOListCreateView.as_view(), name="admin-fpo-links"),
    path("fpo-links/<int:pk>/", OrgUnitFPODetailView.as_view(), name="admin-fpo-link-detail"),
    path("users/", AdminUserCreateView.as_view(), name="admin-user-create"),
]

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("pincode/<str:pin_code>/", PincodeLookupView.as_view(), name="pincode-lookup"),
    path("farmer/check-otp/", FarmerOTPCheckView.as_view(), name="farmer-check-otp"),
    path("firebase-login/", FarmerFirebaseLoginView.as_view(), name="farmer-firebase-login"),
    path("fpo/login/", FPOLoginView.as_view(), name="fpo-login"),
    path("webapp/login/", WebAppLoginView.as_view(), name="webapp-login"),
    path("token/refresh/", TokenRefreshApiView.as_view(), name="token-refresh"),
    path("farmer/my-profile/", FarmerMyProfileView.as_view(), name="farmer-my-profile"),
    path("fpo/my-profile/", FPOMyProfileView.as_view(), name="fpo-my-profile"),
    path("fpo-list/", FPOListView.as_view(), name="fpo-list"),
    path("hierarchy/", include(hierarchy_urlpatterns)),
    path("admin/", include(admin_urlpatterns)),
    path("", include(router.urls)),
]
