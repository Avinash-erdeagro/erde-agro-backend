import json

from rest_framework import serializers
from django.contrib.gis.geos import Polygon
from farmerapp.models import Farm, FarmCrop


class FarmCropSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmCrop
        fields = ["id", "farm", "crop_type", "plantation_date", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class FarmSerializer(serializers.ModelSerializer):
    crops = FarmCropSerializer(many=True, read_only=True)
    boundary = serializers.JSONField()
    farmer = serializers.PrimaryKeyRelatedField(queryset=Farm.farmer.field.related_model.objects.all(), required=False)

    class Meta:
        model = Farm
        fields = [
            "id", "farmer", "land_record_number", "soil_type", "irrigation_type",
            "boundary", "farm_document", "crops", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.boundary:
            rep["boundary"] = json.loads(instance.boundary.geojson)
        return rep

    def validate(self, attrs):
        request = self.context.get("request")
        app_user = request.user.appuser
        role = app_user.role

        if role == "FARMER":
            if "farmer" in attrs:
                raise serializers.ValidationError(
                    {"farmer": "Farmers cannot specify a farmer ID. It is inferred from the access token."}
                )
            attrs["farmer"] = app_user
        elif role == "FPO":
            if "farmer" not in attrs:
                raise serializers.ValidationError(
                    {"farmer": "FPO users must provide a farmer ID."}
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