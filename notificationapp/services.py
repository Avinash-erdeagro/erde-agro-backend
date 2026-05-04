from firebase_admin import messaging
from authapp.services.firebase import get_firebase_app
from .models import DeviceToken


def send_push_notification(*, user, title: str, body: str, data: dict = None):
    """
    Send an FCM push notification to all registered devices of a user.
    Returns a list of (token, success, error) tuples.
    """
    get_firebase_app()

    tokens = list(
        DeviceToken.objects.filter(user=user).values_list("token", "id")
    )
    if not tokens:
        return []

    results = []
    stale_ids = []

    for token, device_id in tokens:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        try:
            messaging.send(message)
            results.append((token, True, None))
        except messaging.UnregisteredError:
            stale_ids.append(device_id)
            results.append((token, False, "unregistered"))
        except Exception as exc:
            results.append((token, False, str(exc)))

    if stale_ids:
        DeviceToken.objects.filter(id__in=stale_ids).delete()

    return results
