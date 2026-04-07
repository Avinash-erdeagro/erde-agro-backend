from rest_framework import serializers
from farmerapp.models import SoilType, IrrigationType, CropType


class SoilTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoilType
        fields = ["id", "name", "irriwatch_id"]


class IrrigationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IrrigationType
        fields = ["id", "name", "irriwatch_id"]


class CropTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropType
        fields = ["id", "name", "irriwatch_id"]