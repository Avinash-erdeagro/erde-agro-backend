from rest_framework import serializers

from authapp.services import normalize_indian_phone_number


class FarmerFirebaseLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class FPOLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)



class WebAppLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class FarmerOTPCheckSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        return normalize_indian_phone_number(value)
