from firebase_admin import messaging
from authapp.services.firebase import get_firebase_app
from .models import DeviceToken
from satelliteapp.services.event_text import resolve_event_text



def send_push_notification(*, user, title: str, body: str, data: dict = None):
    """
    Send an FCM push notification to all registered devices of a user.
    Returns a list of (token, success, error) tuples.
    """
    get_firebase_app()

    tokens = list(DeviceToken.objects.filter(user=user).values_list("token", "id"))
    if not tokens:
        return []

    payload_data = {k: str(v) for k, v in (data or {}).items()}
    payload_data.setdefault("title", title)
    payload_data.setdefault("body", body)

    results = []
    stale_ids = []

    for token, device_id in tokens:
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=payload_data,
            android=messaging.AndroidConfig(
                priority="high",
                ttl=3600,  # 1 hour
                notification=messaging.AndroidNotification(
                    channel_id="general",  # must match app channel id
                    sound="default",
                ),
            ),
            apns=messaging.APNSConfig(
                headers={"apns-priority": "10"},
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", content_available=True)
                ),
            ),
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


def _format_satellite_notification(notification_type: str, details_json: dict, language_code=None):
    """
    Return (title, body) strings for a given satellite notification_type,
    localized to ``language_code`` (falls back to English). The copy lives in
    ``satelliteapp.services.event_text`` so push and the events API share it.
    """

    return resolve_event_text(notification_type, details_json, language_code)


def send_pending_satellite_notifications(notification_qs):
    """
    Given a queryset of SatelliteFarmNotification objects (typically those
    created this run with push_status=PENDING), attempt to send an FCM push
    to each farm's owner and update push_status accordingly.

    Returns (sent_count, failed_count, no_device_count).
    """
    from satelliteapp.models import SatelliteFarmNotificationPushStatus

    sent = failed = no_devices = 0

    # Prefetch to avoid N+1 queries:
    # order_farm → farm → farmer (AppUser) → user (Django User)
    notifications = notification_qs.select_related(
        "order_farm__farm__farmer__user"
    )

    for notif in notifications:
        farmer = notif.order_farm.farm.farmer
        django_user = farmer.user
        title, body = _format_satellite_notification(
            notif.notification_type, notif.details_json, farmer.preferred_language
        )
        data = {
            "notification_id": str(notif.id),
            "notification_type": notif.notification_type,
             "farm_id": str(notif.order_farm.farm_id),
            "observation_date": str(notif.observation_date),
        }

        results = send_push_notification(
            user=django_user, title=title, body=body, data=data
        )

        if not results:
            notif.push_status = SatelliteFarmNotificationPushStatus.NO_DEVICES
            notif.push_failure_reason = "No registered device tokens"
            no_devices += 1
        elif any(success for _, success, _ in results):
            notif.push_status = SatelliteFarmNotificationPushStatus.SENT
            notif.push_failure_reason = ""
            sent += 1
        else:
            errors = "; ".join(err for _, _, err in results if err)
            notif.push_status = SatelliteFarmNotificationPushStatus.FAILED
            notif.push_failure_reason = errors
            failed += 1

        notif.save(update_fields=["push_status", "push_failure_reason"])

    return sent, failed, no_devices

