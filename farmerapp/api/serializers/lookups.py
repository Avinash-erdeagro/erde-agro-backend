from rest_framework import serializers
from farmerapp.models import SoilType, IrrigationType, CropType

TRANSLATION_FIELDS = ["name_hi", "name_mr", "name_gu", "name_pa", "name_bn", "name_kn", "name_te", "name_ta"]


class SoilTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoilType
        fields = ["id", "name"] + TRANSLATION_FIELDS


class IrrigationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IrrigationType
        fields = ["id", "name"] + TRANSLATION_FIELDS


class CropTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropType
        fields = ["id", "name"] + TRANSLATION_FIELDS