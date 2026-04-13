from django.contrib.auth import get_user_model
from django.db import transaction

from authapp.models import AppUser, FarmerProfile, FpoProfile
from authapp.services.locality import get_or_create_locality

User = get_user_model()


class FPOAppError(Exception):
    pass


@transaction.atomic
def create_farmer_under_fpo(*, fpo_profile: FpoProfile, validated_data: dict):
    locality_data = validated_data.pop("locality", None)

    user = User(username=validated_data["contact_number"])
    user.set_unusable_password()
    user.save()

    app_user = AppUser.objects.create(user=user, role=AppUser.Role.FARMER)

    locality = None
    if locality_data:
        locality = get_or_create_locality(locality_data)

    farmer_profile = FarmerProfile.objects.create(
        app_user=app_user,
        locality=locality,
        farmer_name=validated_data["farmer_name"],
        contact_number=validated_data["contact_number"],
        registered_with_fpo=fpo_profile,
        aadhaar_number=validated_data["aadhaar_number"],
        aadhaar_file=validated_data.get("aadhaar_file"),
    )

    return farmer_profile
