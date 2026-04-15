import json

from django.contrib.gis.geos import Polygon
from rest_framework import serializers

from farmerapp.models import Farm, FarmCrop
from authapp.models import FarmerProfile


class FarmCropSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmCrop
        fields = [
            "id", "farm",
            "primary_crop", "custom_primary_crop_name", "primary_crop_variety",
            "intercrop", "custom_intercrop_name", "intercrop_variety",
            "plantation_date", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        primary_crop = attrs.get("primary_crop")
        custom_primary = attrs.get("custom_primary_crop_name", "")
        if not primary_crop and not custom_primary:
            raise serializers.ValidationError(
                {"primary_crop": "Provide either a crop type ID or a custom crop name."}
            )
        if primary_crop and custom_primary:
            raise serializers.ValidationError(
                {"custom_primary_crop_name": "Cannot specify both a crop type and a custom name."}
            )

        intercrop = attrs.get("intercrop")
        custom_intercrop = attrs.get("custom_intercrop_name", "")
        if intercrop and custom_intercrop:
            raise serializers.ValidationError(
                {"custom_intercrop_name": "Cannot specify both a crop type and a custom name for intercrop."}
            )

        return attrs

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["primary_crop"] = instance.primary_crop_name
        rep["primary_crop_variety"] = instance.primary_crop_variety or None
        rep["intercrop"] = instance.intercrop_name
        rep["intercrop_variety"] = instance.intercrop_variety or None
        # Remove internal custom fields from response
        rep.pop("custom_primary_crop_name", None)
        rep.pop("custom_intercrop_name", None)
        return rep


class FarmSerializer(serializers.ModelSerializer):
    crops = FarmCropSerializer(many=True, read_only=True)
    boundary = serializers.JSONField()
    farmer = serializers.PrimaryKeyRelatedField(queryset=Farm.farmer.field.related_model.objects.all(), required=False)
    farmer_id = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = Farm
        fields = [
            "id", "farmer", "farmer_id", "farm_name", "land_record_number", "soil_type", "irrigation_type",
            "boundary", "area", "farm_document", "crops", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "area", "created_at", "updated_at"]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.boundary:
            rep["boundary"] = json.loads(instance.boundary.geojson)
        rep["farmer"] = str(instance.farmer)
        rep["soil_type"] = instance.soil_type.name
        rep["irrigation_type"] = instance.irrigation_type.name
        return rep

    def validate(self, attrs):
        request = self.context.get("request")
        app_user = request.user.appuser
        role = app_user.role

        if role == "FARMER":
            if "farmer" in attrs or "farmer_id" in attrs:
                raise serializers.ValidationError(
                    {"farmer_id": "Farmers cannot specify a farmer ID. It is inferred from the access token."}
                )
            attrs["farmer"] = app_user
        elif role == "FPO":
            farmer_profile_id = attrs.pop("farmer_id", None)

            if farmer_profile_id is not None:
                farmer_profile = (
                    FarmerProfile.objects.select_related("app_user", "registered_with_fpo")
                    .filter(
                        id=farmer_profile_id,
                        registered_with_fpo=app_user.fpo_profile,
                    )
                    .first()
                )
                if not farmer_profile:
                    raise serializers.ValidationError(
                        {"farmer_id": "Invalid farmer ID for this FPO."}
                    )
                attrs["farmer"] = farmer_profile.app_user
            else:
                raise serializers.ValidationError(
                    {"farmer_id": "FPO users must provide a farmer ID."}
                )
        else:
            raise serializers.ValidationError("Unknown user role.")

        return attrs

    def validate_boundary(self, value):
        """Convert GeoJSON-style coordinate array or GeoJSON object to a Polygon."""
        try:
            if isinstance(value, dict):
                # Full GeoJSON: {"type": "Polygon", "coordinates": [[[lng, lat], ...]]}
                coords = value["coordinates"]
            elif isinstance(value, list):
                # Raw coordinate ring: [[lng, lat], [lng, lat], ...]
                coords = [value]
            else:
                raise serializers.ValidationError("Invalid boundary format.")
            return Polygon(coords[0], srid=4326)
        except (KeyError, IndexError, TypeError, Exception) as e:
            raise serializers.ValidationError(f"Invalid boundary data: {e}")
