from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FeaturedVideoViewSet, TutorialVideoViewSet, DashboardAllVideoView

router = DefaultRouter()
router.register("featured-videos", FeaturedVideoViewSet, basename="featured-video")
router.register("tutorial-videos", TutorialVideoViewSet, basename="tutorial-video")

urlpatterns = [
    path("videos/", DashboardAllVideoView.as_view(), name="dashboard-all-videos"),
    path("", include(router.urls)),
]