from django.core.management.base import BaseCommand

from satelliteapp.services import ingest, seed
from satelliteapp.tasks import run_satellite_sync


class Command(BaseCommand):
    help = "Run the IrriWatch satellite sync (seed = discover orders, ingest = pull results)."

    def add_arguments(self, parser):
        parser.add_argument(
            "job",
            choices=["seed", "ingest", "all"],
            help="Which job to run.",
        )
        parser.add_argument(
            "--async",
            action="store_true",
            dest="run_async",
            help="Dispatch to Celery instead of running inline.",
        )

    def handle(self, *args, **options):
        job = options["job"]

        if options["run_async"]:
            result = run_satellite_sync.delay(job)
            self.stdout.write(self.style.SUCCESS(f"Dispatched satellite sync job={job} task id={result.id}"))
            return

        self.stdout.write(f"Running satellite sync job={job} inline...")
        if job in ("seed", "all"):
            seed.run()
        if job in ("ingest", "all"):
            ingest.run()
        self.stdout.write(self.style.SUCCESS(f"Satellite sync finished job={job}"))