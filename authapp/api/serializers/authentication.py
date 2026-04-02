from rest_framework import serializers


class FarmerFirebaseLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()
