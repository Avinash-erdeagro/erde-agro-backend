from django.db import transaction
from django.utils import timezone

from farmerapp.models import Farm, FarmSatelliteSubscription
from satelliteapp.models import (
    SatelliteEventReceipt,
    SatelliteEventReceiptStatus,
    SatelliteFarmAlert,
    SatelliteFarmNotification,
)


def resolve_farm_for_receipt(receipt: SatelliteEventReceipt):
    return Farm.objects.get(id=receipt.external_id)


def process_receipt(receipt: SatelliteEventReceipt):

    if receipt.external_id is None:
        receipt.status = SatelliteEventReceiptStatus.FAILED
        receipt.failure_reason = "external_id is null, cannot map event to farm"
        receipt.processed_at = timezone.now()
        receipt.save(update_fields=["status", "failure_reason", "processed_at"])
        return

    payload = receipt.payload_json or {}
    alerts = payload.get("alerts", [])
    notifications = payload.get("notifications", [])

    farm = resolve_farm_for_receipt(receipt)

    alert_rows = [
        SatelliteFarmAlert(
            receipt=receipt,
            farm=farm,
            source_index=index,
            alert_type=item.get("alert_type", ""),
            details_json=item.get("details_json") or {},
            event_created_at=item.get("created_at"),
            observation_date=receipt.observation_date,
        )
        for index, item in enumerate(alerts)
    ]

    notification_rows = [
        SatelliteFarmNotification(
            receipt=receipt,
            farm=farm,
            source_index=index,
            notification_type=item.get("notification_type", ""),
            details_json=item.get("details_json") or {},
            event_created_at=item.get("created_at"),
            observation_date=receipt.observation_date,
        )
        for index, item in enumerate(notifications)
    ]

    with transaction.atomic():
        SatelliteFarmAlert.objects.bulk_create(alert_rows, ignore_conflicts=True)
        SatelliteFarmNotification.objects.bulk_create(
            notification_rows,
            ignore_conflicts=True,
        )

        receipt.status = SatelliteEventReceiptStatus.PROCESSED
        receipt.processed_at = timezone.now()
        receipt.failure_reason = ""
        receipt.save(update_fields=["status", "processed_at", "failure_reason"])
