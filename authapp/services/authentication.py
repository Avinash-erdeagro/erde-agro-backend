from rest_framework.authtoken.models import Token

from authapp.models import AppUser, FarmerProfile
from authapp.services.firebase import verify_firebase_id_token
from authapp.services.phone import normalize_indian_phone_number


class AuthenticationError(Exception):
    pass


def login_farmer_with_firebase(id_token: str):
    decoded_token = verify_firebase_id_token(id_token)

    phone_number = decoded_token.get("phone_number")
    firebase_data = decoded_token.get("firebase", {})
    sign_in_provider = firebase_data.get("sign_in_provider")

    if not phone_number:
        raise AuthenticationError("Phone number not found in Firebase token.")

    if sign_in_provider != "phone":
        raise AuthenticationError("Invalid sign-in provider.")

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

    token, _ = Token.objects.get_or_create(user=farmer.app_user.user)

    return {
        "token": token.key,
        "user_id": farmer.app_user.user.id,
        "role": farmer.app_user.role,
        "profile_id": farmer.id,
        "profile_type": "farmer",
        "contact_number": farmer.contact_number,
    }
