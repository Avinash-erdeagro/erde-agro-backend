from django.contrib.auth import get_user_model
from rest_framework import serializers

from farmerapp.api.serializers import FarmSerializer
from authapp.api.serializers.locality import LocalitySerializer
from authapp.models import AppUser, FarmerProfile
from authapp.services import normalize_indian_phone_number
User = get_user_model()


class FPOManagedFarmerFarmSummarySerializer(serializers.Serializer):
    farm_id = serializers.IntegerField(source="id")
    farm_name = serializers.CharField()
    land_record_number = serializers.CharField()
    area = serializers.FloatField()


class FPOFarmerContactListSerializer(serializers.ModelSerializer):
    farmer_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = FarmerProfile
        fields = [
            "farmer_id",
            "farmer_name",
            "contact_number",
        ]


class FPOFarmerListSerializer(serializers.ModelSerializer):
    farmer_id = serializers.IntegerField(source="id", read_only=True)
    user_id = serializers.IntegerField(source="app_user.user.id", read_only=True)
    locality = LocalitySerializer(read_only=True)
    farms_count = serializers.IntegerField(source="app_user.farms.count", read_only=True)
    farms = serializers.SerializerMethodField()

    class Meta:
        model = FarmerProfile
        fields = [
            "farmer_id",
            "user_id",
            "farmer_name",
            "contact_number",
            "aadhaar_number",
            "locality",
            "farms_count",
            "farms",
        ]

    def get_farms(self, obj):
        farms = obj.app_user.farms.all().prefetch_related('crops')
        farm_list = []
        from farmerapp.api.serializers.farm import FarmSerializer
        for farm in farms:
            # Serialize all farm fields
            farm_data = FarmSerializer(farm).data
            # Find the active crop for this farm
            active_crop = None
            plantation_date = None
            for crop in farm.crops.all():
                if getattr(crop, 'is_active', False):
                    active_crop = crop.primary_crop_name
                    plantation_date = crop.plantation_date
                    break
            farm_data['active_crop'] = active_crop
            farm_data['plantation_date'] = plantation_date
            farm_list.append(farm_data)
        return farm_list


class FPOFarmerCreateSerializer(serializers.Serializer):
    farmer_name = serializers.CharField()
    contact_number = serializers.CharField()
    aadhaar_number = serializers.CharField()
    aadhaar_file = serializers.FileField(required=False, allow_null=True)
    locality = LocalitySerializer(required=False, allow_null=True)

    farmer_id = serializers.IntegerField(source="id", read_only=True)
    user_id = serializers.IntegerField(source="app_user.user.id", read_only=True)
    username = serializers.CharField(source="app_user.user.username", read_only=True)
    profile_type = serializers.SerializerMethodField(read_only=True)

    def validate_contact_number(self, value):
        try:
            return normalize_indian_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        contact_number = attrs["contact_number"]
        if User.objects.filter(username=contact_number).exists():
            raise serializers.ValidationError(
                {"contact_number": "A farmer with this contact number already exists."}
            )
        return attrs

    def get_profile_type(self, obj):
        return AppUser.Role.FARMER
