from datetime import timedelta

from satelliteapp.models import (
    OrderFarm,
    SatelliteFarmAlert,
    SatelliteFarmNotification,
    SatelliteResult,
    SatelliteMapLayer
)
from satelliteapp.services.metrics import (
    build_irrigation_advisory,
    calculate_average_temperature,
    calculate_crop_growth,
    calculate_soil_moisture,
)
from satelliteapp.services.utils import to_float
from farmerapp.utils import previous_day


class SatelliteServiceError(Exception):
    pass


def _serialize_result(result):
    data_json = result.data_json or {}
    return {
        "id": result.id,
        "order_farm_id": result.order_farm_id,
        "observation_date": result.observation_date.isoformat(),
        "ndvi": to_float(data_json.get("ndvi")),
        "actual_evapotranspiration": to_float(data_json.get("actual_evapotranspiration")),
        "soil_moisture_root_zone": to_float(data_json.get("soil_moisture_root_zone")),
        "leaf_nitrogen": to_float(data_json.get("leaf_nitrogen")),
        "data_json": data_json,
        "tiff_url": result.tiff_url,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


def _serialize_alert(alert):
    return {
        "alert_type": alert.alert_type,
        "details_json": alert.details_json,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


def _serialize_notification(notification):
    return {
        "notification_type": notification.notification_type,
        "details_json": notification.details_json,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


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


def fetch_satellite_results_by_farm_id(farm_id: int):
    results = (
        SatelliteResult.objects
        .filter(order_farm__farm_id=farm_id)
        .order_by("-observation_date")
    )
    return [_serialize_result(result) for result in results]


def fetch_farm_insights(*, farm_id: int, observation_date: str):
    obs_date = previous_day(observation_date)

    result = (
        SatelliteResult.objects
        .filter(order_farm__farm_id=farm_id, observation_date=obs_date)
        .order_by("-created_at")
        .first()
    )

    if result is None:
        raise SatelliteServiceError("Farm insights not found for this farm and date.")

    data_json = result.data_json or {}
    soil_moisture = calculate_soil_moisture(data_json)
    crop_growth = calculate_crop_growth(data_json)
    temperature = calculate_average_temperature(data_json)

    alerts = (
        SatelliteFarmAlert.objects
        .filter(order_farm_id=result.order_farm_id, observation_date=obs_date)
        .order_by("created_at", "id")
    )
    notifications = (
        SatelliteFarmNotification.objects
        .filter(order_farm_id=result.order_farm_id, observation_date=obs_date)
        .order_by("created_at", "id")
    )

    irrigation_advisory = build_irrigation_advisory(
        observation_date=obs_date,
        data_json=data_json,
    )

    return {
        "farm_id": farm_id,
        "observation_date": obs_date.isoformat(),
        "soil_moisture": round(soil_moisture) if soil_moisture is not None else None,
        "crop_growth": round(crop_growth) if crop_growth is not None else None,
        "temperature": round(temperature) if temperature is not None else None,
        "data_json": data_json,
        "alerts": [_serialize_alert(alert) for alert in alerts],
        "notifications": [_serialize_notification(notification) for notification in notifications],
        "irrigation_advisory": (
            {
                "date": irrigation_advisory["date"].isoformat(),
                "amount": irrigation_advisory["amount"],
            }
            if irrigation_advisory is not None
            else None
        ),
    }


def fetch_farm_events_by_farm_ids(*, observation_date: str, farm_ids: list[int]):
    if not farm_ids:
        return {"observation_date": observation_date, "results": []}

    obs_date = previous_day(observation_date)
    unique_ids = list(dict.fromkeys(farm_ids))

    linked_farm_ids = set(
        OrderFarm.objects
        .filter(farm_id__in=unique_ids)
        .values_list("farm_id", flat=True)
    )

    results = []
    for farm_id in unique_ids:
        if farm_id not in linked_farm_ids:
            continue

        alerts = (
            SatelliteFarmAlert.objects
            .filter(order_farm__farm_id=farm_id, observation_date=obs_date)
            .order_by("created_at", "id")
        )
        notifications = (
            SatelliteFarmNotification.objects
            .filter(order_farm__farm_id=farm_id, observation_date=obs_date)
            .order_by("created_at", "id")
        )

        results.append({
            "farm_id": farm_id,
            "observation_date": obs_date.isoformat(),
            "alerts": [_serialize_alert(alert) for alert in alerts],
            "notifications": [_serialize_notification(notification) for notification in notifications],
        })

    return {"observation_date": obs_date.isoformat(), "results": results}


CHART_DEFINITIONS = [
    {
        "chart_name": "Crop Growth",
        "lines": [
            ("attainable_biomass_production_cumulative", "Attainable Crop Growth", "attainable_crop_production_cumulative"),
            ("water_unlimited_crop_production_cumulative", "Water Unlimited Crop Growth", "water_unlimited_crop_production_cumulative"),
            ("crop_production_cumulative", "Cumulative Crop Growth", "crop_production_cumulative"),
        ],
    },
    {
        "chart_name": "Percent Vegetation Cover",
        "lines": [
            ("vegetation_cover", "Vegetation Cover", "vegetation_cover"),
        ],
    },
    {
        "chart_name": "Leaf Nitrogen",
        "lines": [
            ("leaf_nitrogen", "Leaf Nitrogen", "leaf_nitrogen"),
        ],
    },
    {
        "chart_name": "Virtual Soil Moisture Probe",
        "lines": [
            ("theta_sat_sub", "Saturated Soil Moisture Root Zone", "theta_sat_sub"),
            ("theta_fc_sub", "Field Capacity Soil Moisture Root Zone", "theta_fc_sub"),
            ("soil_moisture_percentile95", "Soil Moisture Percentile 95", "soil_moisture_percentile95"),
            ("soil_moisture_root_zone", "Soil Moisture Root Zone", "soil_moisture_root_zone"),
            ("soil_moisture_percentile5", "Soil Moisture Percentile 5", "soil_moisture_percentile5"),
            ("theta_wp_sub", "Wilting Point", "theta_wp_sub"),
            ("critical_soil_moisture_root_zone", "Critical Soil Moisture Root Zone", "critical_soil_moisture_root_zone"),
        ],
    },
    {
        "chart_name": "Actual Evapotranspiration and Transpiration",
        "lines": [
            ("actual_evapotranspiration", "Actual Evapotranspiration", "actual_evapotranspiration"),
            ("actual_transpiration", "Actual Transpiration", "actual_transpiration"),
        ],
    },
    {
        "chart_name": "Cumulative Evapotranspiration, Irrigation, and Precipitation",
        "lines": [
            ("actual_evapotranspiration_cumulative", "Actual Evapotranspiration Cumulative (mm)", "actual_evapotranspiration_cumulative"),
            ("precipitation_cumulative", "Precipitation Cumulative (mm)", "precipitation_cumulative"),
            ("irrigation_amount_cumulative", "Irrigation Amount Cumulative (mm)", "irrigation_amount_cumulative"),
        ],
    },
    {
        "chart_name": "Virtual Tensiometer",
        "lines": [
            ("soil_water_potential_fc", "Soil Water Potential Field Capacity", "soil_water_potential_fc"),
            ("soil_water_potential_critical", "Soil Water Potential Critical", "soil_water_potential_critical"),
            ("soil_water_potential_percentile5", "Soil Water Potential Percentile 5", "soil_water_potential_percentile5"),
            ("soil_water_potential_percentile95", "Soil Water Potential Percentile 95", "soil_water_potential_percentile95"),
            ("soil_water_potential_root_zone", "Soil Water Potential Root Zone", "soil_water_potential_root_zone"),
        ],
    },
]


def fetch_farm_charts(*, farm_id: int, observation_date: str):
    obs_date = previous_day(observation_date)
    start_date = obs_date - timedelta(days=29)

    rows = list(
        SatelliteResult.objects
        .filter(
            order_farm__farm_id=farm_id,
            observation_date__gte=start_date,
            observation_date__lte=obs_date,
        )
        .order_by("observation_date")
    )

    if not rows:
        raise SatelliteServiceError("Farm charts not found for this farm and date.")

    charts = []
    for chart_def in CHART_DEFINITIONS:
        lines = []
        for key, label, json_field in chart_def["lines"]:
            data_points = [
                {
                    "date": row.observation_date.isoformat(),
                    "value": to_float((row.data_json or {}).get(json_field)),
                }
                for row in rows
            ]
            lines.append({"key": key, "label": label, "data": data_points})
        charts.append({"chart_name": chart_def["chart_name"], "lines": lines})

    return {
        "farm_id": farm_id,
        "observation_date": obs_date.isoformat(),
        "charts": charts,
    }


def fetch_farm_map_layers_by_farm_ids(*, observation_date: str, farm_ids: list[int]):
    if not farm_ids:
        return {"observation_date": observation_date, "results": []}

    obs_date = previous_day(observation_date)

    rows = (
        SatelliteMapLayer.objects
        .filter(order_farm__farm_id__in=farm_ids, observation_date=obs_date)
        .order_by("order_farm__farm_id", "band_number")
        .values(
            "order_farm__farm_id", "band_number", "layer_name", "unit",
            "png_url", "bounds", "legend", "is_categorical",
        )
    )

    layers_by_farm: dict[int, list] = {}
    for row in rows:
        farm_id = row["order_farm__farm_id"]
        layers_by_farm.setdefault(farm_id, []).append({
            "band_number": row["band_number"],
            "layer_name": row["layer_name"],
            "unit": row["unit"],
            "png_url": row["png_url"],
            "bounds": row["bounds"],
            "legend": row["legend"],
            "is_categorical": row["is_categorical"],
        })

    results = [
        {"farm_id": farm_id, "observation_date": obs_date.isoformat(), "layers": layers}
        for farm_id, layers in layers_by_farm.items()
    ]
    return {"observation_date": obs_date.isoformat(), "results": results}