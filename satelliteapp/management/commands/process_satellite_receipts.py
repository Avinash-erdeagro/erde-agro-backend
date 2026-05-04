from django.core.management.base import BaseCommand
from django.utils import timezone

from notificationapp.services import send_pending_satellite_notifications
from satelliteapp.models import (
    SatelliteEventReceipt,
    SatelliteEventReceiptStatus,
    SatelliteFarmNotification,
    SatelliteFarmNotificationPushStatus,
)
from satelliteapp.services.processor import process_receipt


class Command(BaseCommand):
    help = "Process received satellite event receipts and push notifications to farmers"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        receipts = SatelliteEventReceipt.objects.filter(
            status=SatelliteEventReceiptStatus.RECEIVED
        ).order_by("received_at")[: options["limit"]]

        for receipt in receipts:
            receipt.status = SatelliteEventReceiptStatus.PROCESSING
            receipt.save(update_fields=["status"])

            try:
                process_receipt(receipt)
            except Exception as exc:
                receipt.status = SatelliteEventReceiptStatus.FAILED
                receipt.failure_reason = str(exc)
                receipt.processed_at = timezone.now()
                receipt.save(
                    update_fields=["status", "failure_reason", "processed_at"]
                )
                self.stderr.write(
                    self.style.ERROR(f"Receipt {receipt.id}: processing failed – {exc}")
                )
                continue

            # Send FCM push notifications for the newly created notification rows
            pending_qs = SatelliteFarmNotification.objects.filter(
                receipt=receipt,
                push_status=SatelliteFarmNotificationPushStatus.PENDING,
            )
            if pending_qs.exists():
                sent, failed, no_devices = send_pending_satellite_notifications(pending_qs)
                self.stdout.write(
                    f"Receipt {receipt.id}: "
                    f"{sent} sent, {failed} failed, {no_devices} no-device"
                )
            else:
                self.stdout.write(f"Receipt {receipt.id}: no notifications to send")
