from django.urls import path

from .views import (
    FPOFarmerContactListView,
    FPOFarmerListCreateView,
)

urlpatterns = [
    path(
        "farmers/contact-list/",
        FPOFarmerContactListView.as_view(),
        name="fpo-farmer-contact-list",
    ),
    path("farmers/", FPOFarmerListCreateView.as_view(), name="fpo-farmers"),
]
