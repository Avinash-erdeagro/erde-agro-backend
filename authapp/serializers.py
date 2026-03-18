from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Address, AppUser, FarmerProfile, FpoProfile

User = get_user_model()


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "pin_code", "village", "taluka", "district", "state"]


class FpoProfileSerializer(serializers.ModelSerializer):
    address = AddressSerializer(required=False, allow_null=True)

    def create(self, validated_data):
        address_data = validated_data.pop("address", None)
        app_user = self.context.get("app_user")
        if app_user is None:
            raise serializers.ValidationError("app_user is required in serializer context")
        address = Address.objects.create(**address_data) if address_data else None
        return self.Meta.model.objects.create(
            app_user=app_user,
            address=address,
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
            "address",
            "app_user",
        ]
        read_only_fields = ["app_user"]


class FarmerProfileSerializer(serializers.ModelSerializer):
    address = AddressSerializer(required=False, allow_null=True)
    registered_with_fpo = serializers.PrimaryKeyRelatedField(
        queryset=FpoProfile.objects.all(), required=False, allow_null=True
    )

    def create(self, validated_data):
        address_data = validated_data.pop("address", None)
        app_user = self.context.get("app_user")
        if app_user is None:
            raise serializers.ValidationError("app_user is required in serializer context")
        address = Address.objects.create(**address_data) if address_data else None
        return self.Meta.model.objects.create(
            app_user=app_user,
            address=address,
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
            "address",
            "app_user",
        ]
        read_only_fields = ["app_user"]


class UserRegistrationSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=AppUser.Role.choices)
    address = AddressSerializer(required=True, write_only=True)

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
            raise serializers.ValidationError({"username": "A user with this username already exists."})

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
            value = (attrs.get("contact_number") or "").strip()
            if not value:
                raise serializers.ValidationError({"contact_number": "This field is required for role 'farmer'."})
            return value

        if role == AppUser.Role.FPO:
            value = (attrs.get("email") or "").strip()
            if not value:
                raise serializers.ValidationError({"email": "This field is required for role 'fpo'."})
            return value

        raise serializers.ValidationError({"role": "Unsupported role"})

    @transaction.atomic
    def create(self, validated_data):
        role = validated_data["role"]
        address_data = validated_data.pop("address")
        password = validated_data.pop("password")
        username = validated_data.pop("username")
        user = User.objects.create_user(username=username, password=password)
        app_user = AppUser.objects.create(user=user, role=role)

        address = Address.objects.create(**address_data)

        if role == AppUser.Role.FARMER:
            FarmerProfile.objects.create(
                app_user=app_user,
                address=address,
                farmer_name=validated_data.get("farmer_name"),
                contact_number=validated_data.get("contact_number"),
                email=validated_data.get("email"),
                registered_with_fpo=validated_data.get("registered_with_fpo"),
                aadhaar_number=validated_data.get("aadhaar_number"),
                aadhaar_file=validated_data.get("aadhaar_file"),
            )
            return app_user

        FpoProfile.objects.create(
            app_user=app_user,
            address=address,
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
