from django.core.management.base import BaseCommand

from notificationapp.services import send_pending_satellite_notifications
from satelliteapp.models import SatelliteFarmNotification, SatelliteFarmNotificationPushStatus


class Command(BaseCommand):
    help = "Send FCM push notifications for all pending SatelliteFarmNotification rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Max number of notifications to process in one run (default: 500)",
        )
        parser.add_argument(
            "--farm-id",
            type=int,
            help="Restrict to a single farm (useful for targeted testing)",
        )

    def handle(self, *args, **options):
        qs = SatelliteFarmNotification.objects.filter(
            push_status=SatelliteFarmNotificationPushStatus.PENDING
        ).order_by("created_at")

        if options["farm_id"]:
            qs = qs.filter(farm_id=options["farm_id"])

        qs = qs[: options["limit"]]
        total = qs.count()

        if total == 0:
            self.stdout.write("No pending notifications found.")
            return

        self.stdout.write(f"Sending {total} pending notification(s)...")
        sent, failed, no_devices = send_pending_satellite_notifications(qs)
        self.stdout.write(
            self.style.SUCCESS(f"Done – sent: {sent}, failed: {failed}, no devices: {no_devices}")
        )
