import logging

from celery import shared_task
from django.utils import timezone

from notificationapp.services import send_pending_satellite_notifications
from satelliteapp.models import (
    SatelliteEventReceipt,
    SatelliteEventReceiptStatus,
    SatelliteFarmNotification,
    SatelliteFarmNotificationPushStatus,
)
from satelliteapp.services.processor import process_receipt

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_satellite_receipt(self, receipt_id: int):
    try:
        receipt = SatelliteEventReceipt.objects.get(id=receipt_id)
    except SatelliteEventReceipt.DoesNotExist:
        logger.error("Receipt %s not found", receipt_id)
        return

    if receipt.status != SatelliteEventReceiptStatus.RECEIVED:
        logger.info("Receipt %s already in status %s, skipping", receipt_id, receipt.status)
        return

    receipt.status = SatelliteEventReceiptStatus.PROCESSING
    receipt.save(update_fields=["status"])

    try:
        process_receipt(receipt)
    except Exception as exc:
        receipt.status = SatelliteEventReceiptStatus.FAILED
        receipt.failure_reason = str(exc)
        receipt.processed_at = timezone.now()
        receipt.save(update_fields=["status", "failure_reason", "processed_at"])
        logger.exception("Receipt %s: processing failed – %s", receipt_id, exc)
        raise self.retry(exc=exc)

    pending_qs = SatelliteFarmNotification.objects.filter(
        receipt=receipt,
        push_status=SatelliteFarmNotificationPushStatus.PENDING,
    )
    if pending_qs.exists():
        sent, failed, no_devices = send_pending_satellite_notifications(pending_qs)
        logger.info(
            "Receipt %s: %s sent, %s failed, %s no-device",
            receipt_id,
            sent,
            failed,
            no_devices,
        )
