from rest_framework.viewsets import ReadOnlyModelViewSet
from authapp.api.views.base import FormattedResponseMixin
from farmerapp.models import SoilType, IrrigationType, CropType
from farmerapp.api.serializers import SoilTypeSerializer, IrrigationTypeSerializer, CropTypeSerializer
from rest_framework.permissions import IsAuthenticated


class SoilTypeViewSet(FormattedResponseMixin, ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = SoilType.objects.all()
    serializer_class = SoilTypeSerializer


class IrrigationTypeViewSet(FormattedResponseMixin, ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = IrrigationType.objects.all()
    serializer_class = IrrigationTypeSerializer


class CropTypeViewSet(FormattedResponseMixin, ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = CropType.objects.all()
    serializer_class = CropTypeSerializer