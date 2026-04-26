from django.core.management.base import BaseCommand
from django.utils import timezone

from satelliteapp.models import SatelliteEventReceipt, SatelliteEventReceiptStatus
from satelliteapp.services.processor import process_receipt


class Command(BaseCommand):
    help = "Process received satellite event receipts"

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
