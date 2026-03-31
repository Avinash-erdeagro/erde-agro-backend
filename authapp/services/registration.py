from django.contrib.auth import get_user_model
from django.db import transaction

from authapp.models import AppUser, FarmerProfile, FpoProfile
from authapp.services.locality import get_or_create_locality

User = get_user_model()

@transaction.atomic
def register_user(validated_data):
    role = validated_data["role"]
    locality_data = validated_data.pop("locality")
    password = validated_data.pop("password")
    username = validated_data.pop("username")

    user = User.objects.create_user(username=username, password=password)
    app_user = AppUser.objects.create(user=user, role=role)
    locality = get_or_create_locality(locality_data)

    if role == AppUser.Role.FARMER:
        FarmerProfile.objects.create(
            app_user=app_user,
            locality=locality,
            farmer_name=validated_data.get("farmer_name"),
            contact_number=validated_data.get("contact_number"),
            registered_with_fpo=validated_data.get("registered_with_fpo"),
            aadhaar_number=validated_data.get("aadhaar_number"),
            aadhaar_file=validated_data.get("aadhaar_file"),
        )
        return app_user

    FpoProfile.objects.create(
        app_user=app_user,
        locality=locality,
        fpo_name=validated_data.get("fpo_name"),
        contact_person_name=validated_data.get("contact_person_name"),
        email=validated_data.get("email"),
        mobile=validated_data.get("mobile"),
        gst_number=validated_data.get("gst_number"),
        pan_number=validated_data.get("pan_number"),
        cin_number=validated_data.get("cin_number"),
        pan_file=validated_data.get("pan_file"),
        cin_file=validated_data.get("cin_file"),
        gst_file=validated_data.get("gst_file"),
    )

    return app_user
