from rest_framework import serializers


class FarmerFirebaseLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class FPOLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
