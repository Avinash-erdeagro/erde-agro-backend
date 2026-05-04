from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from notificationapp.models import DeviceToken
from notificationapp.services import send_push_notification

User = get_user_model()


class Command(BaseCommand):
    help = "Send a test push notification to a user's registered devices."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Username of the target user")
        parser.add_argument("--title", default="Test Notification", help="Notification title")
        parser.add_argument("--body", default="This is a test notification from the backend.", help="Notification body")

    def handle(self, *args, **options):
        username = options["username"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found.")

        tokens = DeviceToken.objects.filter(user=user)
        if not tokens.exists():
            raise CommandError(
                f"No registered device tokens found for '{username}'. "
                "Make sure the app has logged in and sent a token to POST /notifications/device-token/"
            )

        self.stdout.write(f"Found {tokens.count()} device(s) for '{username}'. Sending...")

        results = send_push_notification(
            user=user,
            title=options["title"],
            body=options["body"],
        )

        for token, success, error in results:
            short_token = token[:20] + "..."
            if success:
                self.stdout.write(self.style.SUCCESS(f"  ✓ {short_token}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ {short_token}  ({error})"))
