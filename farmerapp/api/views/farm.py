from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from authapp.api.views.base import FormattedResponseMixin
from farmerapp.models import Farm, FarmCrop
from farmerapp.api.serializers import FarmSerializer, FarmCropSerializer


class FarmViewSet(FormattedResponseMixin, ModelViewSet):
    serializer_class = FarmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        app_user = user.appuser
        qs = Farm.objects.select_related(
            "farmer", "soil_type", "irrigation_type"
        ).prefetch_related("crops")
        if app_user.role == "FARMER":
            qs = qs.filter(farmer=app_user)
        return qs


class FarmCropViewSet(FormattedResponseMixin, ModelViewSet):
    serializer_class = FarmCropSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FarmCrop.objects.select_related("farm", "crop_type")