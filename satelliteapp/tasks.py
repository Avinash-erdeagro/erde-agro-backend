import logging

from celery import shared_task

from satelliteapp.services import ingest, seed
from satelliteapp.models import SatelliteResult
from satelliteapp.services.tiff_processor import process_result_map_layers

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

@shared_task(name="satelliteapp.render_result_map_layers")
def render_result_map_layers(result_id):
    """Render a SatelliteResult's GeoTIFF into map-overlay PNGs + legends (SatelliteMapLayer rows)."""

    result = SatelliteResult.objects.filter(id=result_id).first()
    if result is None:
        logger.warning("render_result_map_layers: result %s not found", result_id)
        return

    process_result_map_layers(result)