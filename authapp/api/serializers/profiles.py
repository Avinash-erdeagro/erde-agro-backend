from rest_framework import serializers
from .locality import LocalitySerializer
from authapp.models import FarmerProfile, FpoProfile
from authapp.services import get_or_create_locality, normalize_indian_phone_number

class FpoProfileSerializer(serializers.ModelSerializer):
    locality = LocalitySerializer(required=False, allow_null=True)

    def validate_mobile(self, value):
        try:
            return normalize_indian_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

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

    def validate_contact_number(self, value):
        try:
            return normalize_indian_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

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
            "registered_with_fpo",
            "aadhaar_number",
            "aadhaar_file",
            "locality",
            "app_user",
        ]
        read_only_fields = ["app_user"]


class FarmerMyProfileSerializer(serializers.ModelSerializer):
    locality = LocalitySerializer(required=False, allow_null=True)
    registered_with_fpo = serializers.PrimaryKeyRelatedField(
        queryset=FpoProfile.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = FarmerProfile
        fields = [
            "id",
            "farmer_name",
            "contact_number",
            "registered_with_fpo",
            "aadhaar_number",
            "aadhaar_file",
            "locality",
        ]
        read_only_fields = ["id", "contact_number"]

    def update(self, instance, validated_data):
        locality_data = validated_data.pop("locality", None)
        if locality_data is not None:
            instance.locality = get_or_create_locality(locality_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.registered_with_fpo:
            rep["registered_with_fpo"] = {
                "id": instance.registered_with_fpo.id,
                "fpo_name": instance.registered_with_fpo.fpo_name,
            }
        return rep


class FPOMyProfileSerializer(serializers.ModelSerializer):
    locality = LocalitySerializer(required=False, allow_null=True)

    def validate_mobile(self, value):
        try:
            return normalize_indian_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

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
        ]
        read_only_fields = ["id", "email"]

    def update(self, instance, validated_data):
        locality_data = validated_data.pop("locality", None)
        if locality_data is not None:
            instance.locality = get_or_create_locality(locality_data)
        return super().update(instance, validated_data)


class FPOListSerializer(serializers.ModelSerializer):
    class Meta:
        model = FpoProfile
        fields = ["id", "fpo_name"]
