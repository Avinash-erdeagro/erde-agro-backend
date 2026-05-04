from rest_framework import serializers
from .models import DeviceToken


class DeviceTokenRegisterSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)
    platform = serializers.ChoiceField(choices=DeviceToken.Platform.choices)


class DeviceTokenUnregisterSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)
