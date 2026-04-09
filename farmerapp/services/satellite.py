from datetime import timedelta

import jwt
import requests
from django.conf import settings
from django.utils import timezone


class SatelliteServiceError(Exception):
    pass


def _validate_satellite_settings():
    required_settings = {
        "SATELLITE_SERVICE_BASE_URL": settings.SATELLITE_SERVICE_BASE_URL,
        "SATELLITE_INTERNAL_AUTH_ISSUER": settings.SATELLITE_INTERNAL_AUTH_ISSUER,
        "SATELLITE_INTERNAL_AUTH_AUDIENCE": settings.SATELLITE_INTERNAL_AUTH_AUDIENCE,
        "SATELLITE_INTERNAL_AUTH_SHARED_SECRET": settings.SATELLITE_INTERNAL_AUTH_SHARED_SECRET,
        "SATELLITE_INTERNAL_AUTH_ALGORITHM": settings.SATELLITE_INTERNAL_AUTH_ALGORITHM,
    }

    missing_settings = [name for name, value in required_settings.items() if not value]
    if missing_settings:
        missing = ", ".join(missing_settings)
        raise SatelliteServiceError(
            f"Satellite service configuration is missing: {missing}."
        )


def _build_internal_auth_token():
    _validate_satellite_settings()

    now = timezone.now()
    payload = {
        "iss": settings.SATELLITE_INTERNAL_AUTH_ISSUER,
        "aud": settings.SATELLITE_INTERNAL_AUTH_AUDIENCE,
        "sub": "drf-service",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "scope": "satellite:read",
    }

    token = jwt.encode(
        payload,
        settings.SATELLITE_INTERNAL_AUTH_SHARED_SECRET,
        algorithm=settings.SATELLITE_INTERNAL_AUTH_ALGORITHM,
    )
    print(f"Generated internal auth token: {token}")
    if isinstance(token, bytes):
        return token.decode("utf-8")
    return token


def fetch_satellite_results_by_external_id(external_id: int):
    token = _build_internal_auth_token()
    url = (
        f"{settings.SATELLITE_SERVICE_BASE_URL}"
        "/internal/satellite-results/by-external-id"
    )

    try:
        response = requests.get(
            url,
            params={"external_id": external_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=settings.SATELLITE_SERVICE_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise SatelliteServiceError(
            "Failed to connect to satellite service."
        ) from exc

    try:
        data = response.json()
    except ValueError:
        data = None

    if response.status_code == 404:
        raise SatelliteServiceError("Satellite data not found for this farm.")

    if response.status_code >= 400:
        message = None
        if isinstance(data, dict):
            message = data.get("detail") or data.get("message") or data.get("error")
        raise SatelliteServiceError(message or "Failed to fetch satellite data.")

    if data is None:
        raise SatelliteServiceError("Invalid response from satellite service.")

    return data
