from django.urls import path

from clientapp.api.views.overview import ClientOverviewView

urlpatterns = [
    path("overview/", ClientOverviewView.as_view(), name="client-overview"),
]