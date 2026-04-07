from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from authapp.api.views.base import FormattedResponseMixin
from farmerapp.models import Farm, FarmCrop
from farmerapp.api.serializers import FarmSerializer, FarmCropSerializer


class FarmViewSet(FormattedResponseMixin, ModelViewSet):
    serializer_class = FarmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Farm.objects.select_related(
            "farmer", "soil_type", "irrigation_type"
        ).prefetch_related("crops")


class FarmCropViewSet(FormattedResponseMixin, ModelViewSet):
    serializer_class = FarmCropSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FarmCrop.objects.select_related("farm", "crop_type")