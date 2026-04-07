import requests
from django.core.management.base import BaseCommand, CommandError
from farmerapp.models import SoilType, IrrigationType, CropType


IRRIWATCH_BASE_URL = "https://api.irriwatch.hydrosat.com/api/v1/reference"

ENDPOINTS = [
    {"path": "/irrigation", "model": IrrigationType},
    {"path": "/soil", "model": SoilType},
    {"path": "/crop", "model": CropType},
]


class Command(BaseCommand):
    help = "Seed soil types, irrigation types, and crop types from IrriWatch API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--irriwatch-auth-token",
            type=str,
            required=True,
            help="IrriWatch API token",
        )

    def _fetch(self, path, token):
        url = f"{IRRIWATCH_BASE_URL}{path}"
        response = requests.get(
            url,
            headers={
                "accept": "application/json",
                "authorization": f"Bearer {token}",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def handle(self, *args, **options):
        token = options["irriwatch_auth_token"]
        
        for endpoint in ENDPOINTS:
            model = endpoint["model"]
            model_name = model.__name__

            try:
                data = self._fetch(endpoint["path"], token)
            except requests.RequestException as e:
                raise CommandError(f"Failed to fetch {model_name} data: {e}")

            created_count = 0
            updated_count = 0

            for irriwatch_id_str, name in data.items():
                irriwatch_id = int(irriwatch_id_str)
                _, created = model.objects.update_or_create(
                    irriwatch_id=irriwatch_id,
                    defaults={"name": name},
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            self.stdout.write(self.style.SUCCESS(
                f"{model_name}: {created_count} created, {updated_count} updated"
            ))

        self.stdout.write(self.style.SUCCESS("Seeding complete."))