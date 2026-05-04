from django.urls import path
from .views import DeviceTokenRegisterView, DeviceTokenUnregisterView

urlpatterns = [
    path("device-token/", DeviceTokenRegisterView.as_view(), name="device-token-register"),
    path("device-token/unregister/", DeviceTokenUnregisterView.as_view(), name="device-token-unregister"),
]
