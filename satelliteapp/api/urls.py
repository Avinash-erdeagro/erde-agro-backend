from django.urls import path

from satelliteapp.api.views import SatelliteBatchReceiverView


urlpatterns = [
    path("event-batch-receiver/", SatelliteBatchReceiverView.as_view(), name="satellite-batch-receiver"),
]
