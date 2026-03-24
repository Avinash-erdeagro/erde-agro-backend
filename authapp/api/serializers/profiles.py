from rest_framework import serializers
from .locality import LocalitySerializer
from authapp.models import FarmerProfile, FpoProfile
from authapp.services import get_or_create_locality

class FpoProfileSerializer(serializers.ModelSerializer):
    locality = LocalitySerializer(required=False, allow_null=True)

    def create(self, validated_data):
        locality_data = validated_data.pop("locality", None)
        app_user = self.context.get("app_user")
        if app_user is None:
            raise serializers.ValidationError("app_user is required in serializer context")

        locality = None
        if locality_data:
            locality = get_or_create_locality(locality_data)

        return self.Meta.model.objects.create(
            app_user=app_user,
            locality=locality,
            **validated_data,
        )

    class Meta:
        model = FpoProfile
        fields = [
            "id",
            "fpo_name",
            "contact_person_name",
            "email",
            "mobile",
            "gst_number",
            "pan_number",
            "cin_number",
            "pan_file",
            "cin_file",
            "gst_file",
            "locality",
            "app_user",
        ]
        read_only_fields = ["app_user"]


class FarmerProfileSerializer(serializers.ModelSerializer):
    locality = LocalitySerializer(required=False, allow_null=True)
    registered_with_fpo = serializers.PrimaryKeyRelatedField(
        queryset=FpoProfile.objects.all(), required=False, allow_null=True
    )

    def create(self, validated_data):
        locality_data = validated_data.pop("locality", None)
        app_user = self.context.get("app_user")
        if app_user is None:
            raise serializers.ValidationError("app_user is required in serializer context")

        locality = None
        if locality_data:
            locality = get_or_create_locality(locality_data)

        return self.Meta.model.objects.create(
            app_user=app_user,
            locality=locality,
            **validated_data,
        )

    class Meta:
        model = FarmerProfile
        fields = [
            "id",
            "farmer_name",
            "contact_number",
            "email",
            "registered_with_fpo",
            "aadhaar_number",
            "aadhaar_file",
            "locality",
            "app_user",
        ]
        read_only_fields = ["app_user"]