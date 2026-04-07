from rest_framework import serializers
from farmerapp.models import SoilType, IrrigationType, CropType


class SoilTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoilType
        fields = ["id", "name"]


class IrrigationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IrrigationType
        fields = ["id", "name"]


class CropTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropType
        fields = ["id", "name"]