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


def fetch_satellite_metrics_by_external_ids(*, observation_date: str, external_ids: list[int]):
    if not external_ids:
        return {
            "observation_date": observation_date,
            "results": [],
        }

    token = _build_internal_auth_token()
    url = (
        f"{settings.SATELLITE_SERVICE_BASE_URL}"
        "/internal/satellite-metrics/by-external-ids"
    )

    try:
        response = requests.post(
            url,
            json={
                "observation_date": observation_date,
                "external_ids": external_ids,
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
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

    if response.status_code >= 400:
        message = None
        if isinstance(data, dict):
            message = data.get("detail") or data.get("message") or data.get("error")
        raise SatelliteServiceError(message or "Failed to fetch satellite metrics.")

    if data is None:
        raise SatelliteServiceError("Invalid response from satellite service.")

    return data


def fetch_farm_insights(*, external_id: int, observation_date: str):
    token = _build_internal_auth_token()
    url = f"{settings.SATELLITE_SERVICE_BASE_URL}/internal/farm-insights"

    try:
        response = requests.get(
            url,
            params={
                "external_id": external_id,
                "observation_date": observation_date,
            },
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
        raise SatelliteServiceError("Farm insights not found for this farm and date.")

    if response.status_code >= 400:
        message = None
        if isinstance(data, dict):
            message = data.get("detail") or data.get("message") or data.get("error")
        raise SatelliteServiceError(message or "Failed to fetch farm insights.")

    if data is None:
        raise SatelliteServiceError("Invalid response from satellite service.")

    return data


def fetch_farm_events_by_external_ids(*, observation_date: str, external_ids: list[int]):
    if not external_ids:
        return {
            "observation_date": observation_date,
            "results": [],
        }

    token = _build_internal_auth_token()
    url = f"{settings.SATELLITE_SERVICE_BASE_URL}/internal/farm-events/by-external-ids"

    try:
        response = requests.post(
            url,
            json={
                "observation_date": observation_date,
                "external_ids": external_ids,
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
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

    if response.status_code >= 400:
        message = None
        if isinstance(data, dict):
            message = data.get("detail") or data.get("message") or data.get("error")
        raise SatelliteServiceError(message or "Failed to fetch farm events.")

    if data is None:
        raise SatelliteServiceError("Invalid response from satellite service.")

    return data
