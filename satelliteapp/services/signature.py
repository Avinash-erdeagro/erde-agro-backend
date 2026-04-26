import hashlib
import hmac
from django.conf import settings

def verify_satellite_signature(raw_body: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.SATELLITE_EVENTS_SECRET.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
