from django.urls import path

from .views import SatellitePricingView

urlpatterns = [
    path(
        "satellite-pricing/",
        SatellitePricingView.as_view(),
        name="satellite-pricing",
    ),
]
