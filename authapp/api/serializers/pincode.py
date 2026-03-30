from rest_framework import serializers


class LocalityOptionSerializer(serializers.Serializer):
    village = serializers.CharField()
    taluka = serializers.CharField(allow_blank=True)


class PincodeLookupResultSerializer(serializers.Serializer):
    pin_code = serializers.CharField()
    district = serializers.CharField()
    state = serializers.CharField()
    localities = LocalityOptionSerializer(many=True)
