import json

from django.contrib.gis.geos import Polygon
from rest_framework import serializers

from farmerapp.models import Farm, FarmCrop


class FarmCropSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmCrop
        fields = ["id", "farm", "crop_type", "plantation_date", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["crop_type"] = instance.crop_type.name
        return rep


class FarmSerializer(serializers.ModelSerializer):
    crops = FarmCropSerializer(many=True, read_only=True)
    boundary = serializers.JSONField()
    farmer = serializers.PrimaryKeyRelatedField(queryset=Farm.farmer.field.related_model.objects.all(), required=False)

    class Meta:
        model = Farm
        fields = [
            "id", "farmer", "farm_name", "land_record_number", "soil_type", "irrigation_type",
            "boundary", "area", "farm_document", "crops", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

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

    @staticmethod
    # TODO: CHECK if this can be optimized by caching the area for known polygons, or by using a more efficient library for 
    # geodesic area calculation in Python instead of hitting the database every time.
    def _calc_area_acres(polygon):
        """Return geodesic area of the polygon in acres using PostGIS ST_Area(geography)."""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT ST_Area(%s::geography)", [polygon.ewkt])
            area_sq_m = cursor.fetchone()[0]
        return round(area_sq_m / 4046.8564224, 2)

    def create(self, validated_data):
        backend_area = self._calc_area_acres(validated_data["boundary"])
        frontend_area = round(validated_data.pop("area", 0) or 0, 2)
        print(f"Backend area: {backend_area} acres, Frontend area: {frontend_area} acres")
        validated_data["area"] = max(backend_area, frontend_area)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "boundary" in validated_data:
            backend_area = self._calc_area_acres(validated_data["boundary"])
            frontend_area = round(validated_data.pop("area", 0) or 0, 2)
            validated_data["area"] = max(backend_area, frontend_area)
        else:
            validated_data.pop("area", None)
        return super().update(instance, validated_data)