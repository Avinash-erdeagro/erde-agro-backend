
from rest_framework import serializers
from .locality import LocalitySerializer
from authapp.models import AppUser, FpoProfile
from django.contrib.auth import get_user_model
from authapp.services import normalize_indian_phone_number, register_user

User = get_user_model()

class UserRegistrationSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=AppUser.Role.choices)
    locality = LocalitySerializer(required=True, write_only=True)

    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    profile_id = serializers.SerializerMethodField(read_only=True)
    profile_type = serializers.SerializerMethodField(read_only=True)

    # Farmer fields
    farmer_name = serializers.CharField(required=False, allow_blank=False, write_only=True)
    contact_number = serializers.CharField(required=False, allow_blank=False, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True, write_only=True)
    registered_with_fpo = serializers.PrimaryKeyRelatedField(
        queryset=FpoProfile.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    aadhaar_number = serializers.CharField(required=False, allow_blank=False, write_only=True)
    aadhaar_file = serializers.FileField(required=False, allow_null=True, write_only=True)

    # FPO fields
    fpo_name = serializers.CharField(required=False, allow_blank=False, write_only=True)
    contact_person_name = serializers.CharField(required=False, allow_blank=False, write_only=True)
    mobile = serializers.CharField(required=False, allow_blank=False, write_only=True)
    gst_number = serializers.CharField(required=False, allow_blank=False, write_only=True)
    pan_number = serializers.CharField(required=False, allow_blank=False, write_only=True)
    cin_number = serializers.CharField(required=False, allow_blank=False, write_only=True)
    pan_file = serializers.FileField(required=False, allow_null=True, write_only=True)
    cin_file = serializers.FileField(required=False, allow_null=True, write_only=True)
    gst_file = serializers.FileField(required=False, allow_null=True, write_only=True)

    def validate_contact_number(self, value):
        try:
            return normalize_indian_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_mobile(self, value):
        try:
            return normalize_indian_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def get_profile_type(self, obj):
        if obj.role == AppUser.Role.FPO:
            return "fpo"
        if obj.role == AppUser.Role.FARMER:
            return "farmer"
        return None

    def get_profile_id(self, obj):
        if obj.role == AppUser.Role.FPO and hasattr(obj, "fpo_profile"):
            return obj.fpo_profile.id
        if obj.role == AppUser.Role.FARMER and hasattr(obj, "farmer_profile"):
            return obj.farmer_profile.id
        return None

    def validate(self, attrs):
        role = attrs.get("role")
        derived_username = self._derive_username(role, attrs)
        if User.objects.filter(username=derived_username).exists():
            raise serializers.ValidationError(
                {"username": "A user with this username already exists."}
            )

        attrs["username"] = derived_username

        if role == AppUser.Role.FARMER:
            self._validate_farmer_fields(attrs)
        elif role == AppUser.Role.FPO:
            self._validate_fpo_fields(attrs)
        else:
            raise serializers.ValidationError({"role": "Unsupported role"})

        return attrs

    def _validate_required_fields(self, attrs, field_names):
        errors = {}
        for field_name in field_names:
            value = attrs.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors[field_name] = "This field is required."
        if errors:
            raise serializers.ValidationError(errors)

    def _validate_farmer_fields(self, attrs):
        self._validate_required_fields(
            attrs,
            ["farmer_name", "contact_number", "aadhaar_number"],
        )

    def _validate_fpo_fields(self, attrs):
        self._validate_required_fields(
            attrs,
            [
                "fpo_name",
                "contact_person_name",
                "email",
                "mobile",
                "gst_number",
                "pan_number",
                "cin_number",
            ],
        )

    def _derive_username(self, role, attrs):
        if role == AppUser.Role.FARMER:
            value = attrs.get("contact_number") or ""
            if not value:
                raise serializers.ValidationError(
                    {"contact_number": "This field is required for role 'farmer'."}
                )
            return value

        if role == AppUser.Role.FPO:
            value = (attrs.get("email") or "").strip()
            if not value:
                raise serializers.ValidationError(
                    {"email": "This field is required for role 'fpo'."}
                )
            return value

        raise serializers.ValidationError({"role": "Unsupported role"})

    def create(self, validated_data):
        return register_user(validated_data)
