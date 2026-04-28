from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from authapp.models import AppUser, FarmerProfile, FpoProfile
from authapp.services.firebase import verify_firebase_id_token
from authapp.services.phone import normalize_indian_phone_number


class AuthenticationError(Exception):
    pass


def login_farmer_with_firebase(id_token: str):
    try:
        decoded_token = verify_firebase_id_token(id_token)
    except Exception as exc:
        raise AuthenticationError("Invalid or expired Firebase token.") from exc

    phone_number = decoded_token.get("phone_number")
    firebase_data = decoded_token.get("firebase", {})
    sign_in_provider = firebase_data.get("sign_in_provider")

    if not phone_number:
        raise AuthenticationError("Something went wrong during authentication. Please try again.")

    if sign_in_provider != "phone":
        raise AuthenticationError("Something went wrong during authentication. Please try again.")

    try:
        normalized_phone = normalize_indian_phone_number(phone_number)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc

    farmer = FarmerProfile.objects.select_related(
        "app_user", "app_user__user"
    ).filter(contact_number=normalized_phone).first()

    if not farmer:
        raise AuthenticationError("Farmer account not found.")

    if farmer.app_user.role != AppUser.Role.FARMER:
        raise AuthenticationError("User is not registered as a farmer.")

    refresh = RefreshToken.for_user(farmer.app_user.user)

    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "user_name": farmer.farmer_name,
        "role": farmer.app_user.role,
    }


def login_fpo(username: str, password: str):
    user = authenticate(username=username.strip(), password=password)

    if not user:
        raise AuthenticationError("Invalid username or password.")

    app_user = AppUser.objects.select_related("fpo_profile").filter(user=user).first()
    if not app_user:
        raise AuthenticationError("User account not found.")

    if app_user.role != AppUser.Role.FPO:
        raise AuthenticationError("User is not registered as an FPO.")

    fpo_profile = getattr(app_user, "fpo_profile", None)
    if not fpo_profile:
        raise AuthenticationError("FPO profile not found.")

    refresh = RefreshToken.for_user(user)

    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "user_name": fpo_profile.fpo_name,
        "role": app_user.role,
    }


def check_farmer_otp_eligibility(phone_number: str):
    try:
        normalized_phone = normalize_indian_phone_number(phone_number)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc

    farmer = FarmerProfile.objects.select_related("app_user").filter(
        contact_number=normalized_phone,
        app_user__role=AppUser.Role.FARMER,
    ).first()

    should_send_otp = farmer is not None

    return {
        "phone_number": normalized_phone,
        "is_farmer_registered": should_send_otp,
        "should_send_otp": should_send_otp,
    }


def login_webapp(username: str, password: str):
    user = authenticate(username=username.strip(), password=password)

    if not user:
        raise AuthenticationError("Invalid username or password.")

    app_user = AppUser.objects.filter(user=user).first()
    if not app_user:
        raise AuthenticationError("User account not found.")

    # Determine display name based on role
    display_name = user.username
    if app_user.role == AppUser.Role.FARMER:
        farmer_profile = FarmerProfile.objects.filter(app_user=app_user).first()
        if farmer_profile:
            display_name = farmer_profile.farmer_name
    elif app_user.role == AppUser.Role.FPO:
        fpo_profile = FpoProfile.objects.filter(app_user=app_user).first()
        if fpo_profile:
            display_name = fpo_profile.fpo_name

    refresh = RefreshToken.for_user(user)

    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "user_name": display_name,
        "role": getattr(app_user, "role", None),
    }