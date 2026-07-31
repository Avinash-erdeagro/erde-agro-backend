import logging

from celery import shared_task

from satelliteapp.services import ingest, seed

logger = logging.getLogger(__name__)


@shared_task(name="satelliteapp.run_satellite_sync")
def run_satellite_sync(job="all"):
    """Celery entrypoint for the IrriWatch sync. job = seed | ingest | all."""
    logger.info("Satellite sync task started job=%s", job)

    if job in ("seed", "all"):
        seed.run()
    if job in ("ingest", "all"):
        ingest.run()

    logger.info("Satellite sync task finished job=%s", job)
