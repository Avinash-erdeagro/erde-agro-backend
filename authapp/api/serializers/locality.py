from rest_framework import serializers
from authapp.models import Locality
from authapp.services.locality import normalize_locality_data

class LocalitySerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        return normalize_locality_data(attrs)

    class Meta:
        model = Locality
        fields = ["id", "pin_code", "village", "taluka", "district", "state"]