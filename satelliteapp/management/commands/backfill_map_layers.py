import logging

from django.core.management.base import BaseCommand

from satelliteapp.models import SatelliteMapLayer, SatelliteResult
from satelliteapp.services.tiff_processor import process_result_map_layers

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill SatelliteMapLayer PNGs for existing results that have a tif but no layers."

    def add_arguments(self, parser):
        parser.add_argument("--since", help="Only results with observation_date >= YYYY-MM-DD")
        parser.add_argument("--limit", type=int, help="Process at most N results (for a trial run)")

    def handle(self, *args, **options):
        qs = (
            SatelliteResult.objects
            .exclude(tiff_url__isnull=True).exclude(tiff_url="")
            .order_by("observation_date")
        )
        if options.get("since"):
            qs = qs.filter(observation_date__gte=options["since"])

        processed = 0
        for result in qs.iterator():
            already = SatelliteMapLayer.objects.filter(
                order_farm_id=result.order_farm_id,
                observation_date=result.observation_date,
            ).exists()
            if already:
                continue

            try:
                n = process_result_map_layers(result)
            except Exception:
                logger.exception("Backfill failed for result %s", result.id)
                continue

            processed += 1
            self.stdout.write(f"[{processed}] result {result.id} ({result.observation_date}): {n} layers")

            if options.get("limit") and processed >= options["limit"]:
                break

        self.stdout.write(self.style.SUCCESS(f"Backfill done: {processed} results processed"))
