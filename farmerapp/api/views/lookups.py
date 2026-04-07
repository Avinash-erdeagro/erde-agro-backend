from rest_framework.viewsets import ReadOnlyModelViewSet
from authapp.api.views.base import FormattedResponseMixin
from farmerapp.models import SoilType, IrrigationType, CropType
from farmerapp.api.serializers import SoilTypeSerializer, IrrigationTypeSerializer, CropTypeSerializer


class SoilTypeViewSet(FormattedResponseMixin, ReadOnlyModelViewSet):
    queryset = SoilType.objects.all()
    serializer_class = SoilTypeSerializer


class IrrigationTypeViewSet(FormattedResponseMixin, ReadOnlyModelViewSet):
    queryset = IrrigationType.objects.all()
    serializer_class = IrrigationTypeSerializer


class CropTypeViewSet(FormattedResponseMixin, ReadOnlyModelViewSet):
    queryset = CropType.objects.all()
    serializer_class = CropTypeSerializer