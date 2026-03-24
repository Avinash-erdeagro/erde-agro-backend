from rest_framework import serializers
from authapp.models import Locality
from authapp.services.locality import normalize_locality_data

class LocalitySerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        return normalize_locality_data(attrs)
    
    def validate_pin_code(self, value):
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError("PIN code must contain only digits.")
        if len(value) != 6:
            raise serializers.ValidationError("PIN code must contain exactly 6 digits.")
        return value

    class Meta:
        model = Locality
        fields = ["id", "pin_code", "village", "taluka", "district", "state"]