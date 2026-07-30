import time

import boto3
import requests
from django.conf import settings

# In-process token cache
_token = None
_token_expiry = 0.0


def get_token():
    """Fetch (and cache) an IrriWatch OAuth2 client_credentials token."""
    global _token, _token_expiry

    # Reuse the cached token while it is still valid (60s safety buffer).
    if _token and time.time() < (_token_expiry - 60):
        return _token

    response = requests.post(
        settings.IRRIWATCH_TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {settings.IRRIWATCH_BASIC_AUTH}",
        },
        data={"grant_type": "client_credentials"},
        timeout=settings.IRRIWATCH_HTTP_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    _token = data["access_token"]
    _token_expiry = time.time() + data["expires_in"]
    return _token


def _headers():
    return {
        "accept": "application/json",
        "authorization": f"Bearer {get_token()}",
    }


# --- S3 client (reuses the app's AWS credentials/region

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_S3_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_AC
        )
    return _s3_client


# --- IrriWatch API calls ----------------------------------------------------

def get_companies():
    response = requests.get(
        f"{settings.IRRIWATCH_BASE_URL}/company",
        headers=_headers(),
        timeout=settings.IRRIWATCH_HTTP_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_orders(company_uuid):
    response = requests.get(
        f"{settings.IRRIWATCH_BASE_URL}/company/{company_uuid}/order",
        headers=_headers(),
        timeout=settings.IRRIWATCH_HTTP_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_result_dates(company_uuid, order_uuid):
    response = requests.get(
        f"{settings.IRRIWATCH_BASE_URL}/company/{company_uuid}/order/{order_uuid}/result",
        headers=_headers(),
        timeout=settings.IRRIWATCH_HTTP_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def download_result_zip(company_uuid, order_uuid, result_uuid):
    response = requests.get(
        f"{settings.IRRIWATCH_BASE_URL}/company/{company_uuid}/order/{order_uuid}/result/{result_uuid}",
        headers=_headers(),
        timeout=settings.IRRIWATCH_DOWNLOAD_TIMEOUT,
    )
    response.raise_for_status()
    return response.content


# --- S3 upload --------------------------------------------------------------
def upload_tif_to_s3(tif_bytes, field_uuid, observation_date):
    """Upload a GeoTIFF to the dedicated satellite bucket, return its URL."""
    key = f"tiff/{observation_date}/{field_uuid}.tif"
    _get_s3_client().put_object(
        Bucket=settings.SATELLITE_DATA_S3_BUCKET,
        Key=key,
        Body=tif_bytes,
        ContentType="image/tiff",
    )
    return (
        f"https://{settings.SATELLITE_DATA_S3_BUCKET}.s3."
        f"{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"
    )