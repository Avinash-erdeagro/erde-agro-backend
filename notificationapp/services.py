from firebase_admin import messaging
from authapp.services.firebase import get_firebase_app
from .models import DeviceToken


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


def _format_satellite_notification(notification_type: str, details_json: dict):
    """
    Return (title, body) strings for a given satellite notification_type.
    Falls back to generic text when the type is unrecognised.
    """
    title_map = {
        "crop_stress": "Crop Stress Detected",
        "water_stress": "Water Stress Alert",
        "pest_risk": "Pest Risk Warning",
        "growth_stage": "Crop Growth Update",
        "yield_estimate": "Yield Estimate Ready",
    }
    title = title_map.get(notification_type, "Farm Satellite Update")

    # Try to build a human body from well-known detail keys
    severity = details_json.get("severity") or details_json.get("level")
    description = details_json.get("description") or details_json.get("message")

    if description:
        body = str(description)
    elif severity:
        body = f"Severity: {severity}"
    else:
        body = f"New satellite event: {notification_type.replace('_', ' ').title()}"

    return title, body


def send_pending_satellite_notifications(notification_qs):
    """
    Given a queryset of SatelliteFarmNotification objects (typically those
    with push_status=PENDING for a single receipt), attempt to send an FCM
    push to each farm's owner and update push_status accordingly.

    Returns (sent_count, failed_count, no_device_count).
    """
    from satelliteapp.models import SatelliteFarmNotificationPushStatus

    sent = failed = no_devices = 0

    # Prefetch to avoid N+1 queries: farm → farmer (AppUser) → user (Django User)
    notifications = notification_qs.select_related(
        "farm__farmer__user"
    )

    for notif in notifications:
        django_user = notif.farm.farmer.user
        title, body = _format_satellite_notification(
            notif.notification_type, notif.details_json
        )
        data = {
            "notification_id": str(notif.id),
            "notification_type": notif.notification_type,
            "farm_id": str(notif.farm_id),
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

