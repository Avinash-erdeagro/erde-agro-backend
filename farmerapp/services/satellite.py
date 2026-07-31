from satelliteapp.models import SatelliteResult
from satelliteapp.services.metrics import calculate_crop_growth, calculate_soil_moisture
from farmerapp.utils import previous_day


class SatelliteServiceError(Exception):
    pass


def fetch_satellite_metrics_by_farm_ids(*, observation_date: str, farm_ids: list[int]) -> dict[int, dict]:
    """Return {farm_id: {"soil_moisture": int|None, "crop_growth": int|None}} for the given farms."""
    if not farm_ids:
        return {}

    obs_date = previous_day(observation_date)

    rows = (
        SatelliteResult.objects
        .filter(order_farm__farm_id__in=farm_ids, observation_date=obs_date)
        .order_by("-created_at")
        .values("order_farm__farm_id", "data_json")
    )

    metrics_by_farm_id: dict[int, dict] = {}
    for row in rows:
        farm_id = row["order_farm__farm_id"]
        if farm_id is None or farm_id in metrics_by_farm_id:
            continue
        data_json = row["data_json"] or {}
        soil_moisture = calculate_soil_moisture(data_json)
        crop_growth = calculate_crop_growth(data_json)
        metrics_by_farm_id[farm_id] = {
            "soil_moisture": round(soil_moisture) if soil_moisture is not None else None,
            "crop_growth": round(crop_growth) if crop_growth is not None else None,
        }

    return metrics_by_farm_id


# --- not yet migrated (ported one API at a time) ---

def fetch_satellite_results_by_external_id(external_id: int):
    raise SatelliteServiceError("satellite results reader not migrated yet")


def fetch_farm_insights(*, external_id: int, observation_date: str):
    raise SatelliteServiceError("farm insights reader not migrated yet")


def fetch_farm_events_by_external_ids(*, observation_date: str, external_ids: list[int]):
    raise SatelliteServiceError("farm events reader not migrated yet")


def fetch_farm_charts(*, external_id: int, observation_date: str):
    raise SatelliteServiceError("farm charts reader not migrated yet")


def fetch_farm_map_layers_by_external_ids(*, observation_date: str, external_ids: list[int]):
    raise SatelliteServiceError("farm map layers reader not migrated yet")