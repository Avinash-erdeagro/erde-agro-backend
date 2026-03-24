from rest_framework import serializers
from authapp.models import Locality

def _normalize_whitespace(value):
    return " ".join(value.strip().split())


def normalize_locality_data(locality_data):
    return {
        "pin_code": _normalize_whitespace(locality_data["pin_code"]).upper(),
        "village": _normalize_whitespace(locality_data["village"]).title(),
        "taluka": _normalize_whitespace(locality_data["taluka"]).title(),
        "district": _normalize_whitespace(locality_data["district"]).title(),
        "state": _normalize_whitespace(locality_data["state"]).title(),
    }


class LocalitySerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        return normalize_locality_data(attrs)

    class Meta:
        model = Locality
        fields = ["id", "pin_code", "village", "taluka", "district", "state"]