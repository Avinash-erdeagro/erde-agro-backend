from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("authapp.api.urls")),
    path("content/", include("contentapp.api.urls")),
    path("farmer/", include("farmerapp.api.urls")),
]

