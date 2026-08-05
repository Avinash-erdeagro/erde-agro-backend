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
from satelliteapp.services.event_text import resolve_event_text
from satelliteapp.services.label_text import localize_label
from farmerapp.utils import previous_day
from authapp.api.response_codes import ResponseCode


class SatelliteServiceError(Exception):
    """Business error surfaced to the API. Carries a stable ``code`` so views
    can pass it through even though they only see ``str(exc)``."""

    def __init__(self, message, code=ResponseCode.SATELLITE_ERROR):
        super().__init__(message)
        self.code = code


# Band -> display name for the map-layers API. Only these bands are exposed;
# bands 2 (Vegetation Cover), 11 (Variable Rate Irrigation) and 13 (Leaf
# Temperature) are still rendered/stored but withheld from the API.
API_MAP_LAYER_NAMES = {
    3: "Soil Moisture",
    4: "Leaf N",
    5: "NDVI",
    6: "Actual ET",
    7: "Total Crop Growth",
    8: "Crop Growth",
    9: "Soil Water Potential",
    10: "Moisture Status",
    12: "Soil Temp Daily",
}

# Display units per layer, keyed by band. Universal scientific notation — sent
# as-is, never translated. Empty string = no unit (NDVI is dimensionless;
# Moisture Status is categorical and carries a legend instead).
API_MAP_LAYER_UNITS = {
    3: "m³/m³",       # Soil Moisture (volumetric)
    4: "%",           # Leaf N
    5: "",            # NDVI
    6: "mm/day",      # Actual ET
    7: "kg/ha",       # Total Crop Growth
    8: "kg/ha/day",   # Crop Growth
    9: "pF",          # Soil Water Potential
    10: "",           # Moisture Status (categorical)
    12: "°C",         # Soil Temp Daily
}


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


def _serialize_alert(alert, language_code=None):
    title, body = resolve_event_text(alert.alert_type, alert.details_json, language_code)
    return {
        "alert_type": alert.alert_type,
        "title": title,
        "body": body,
        "details_json": alert.details_json,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


def _serialize_notification(notification, language_code=None):
    title, body = resolve_event_text(
        notification.notification_type, notification.details_json, language_code
    )
    return {
        "notification_type": notification.notification_type,
        "title": title,
        "body": body,
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


def fetch_farm_insights(*, farm_id: int, observation_date: str, language_code=None):
    obs_date = previous_day(observation_date)

    result = (
        SatelliteResult.objects
        .filter(order_farm__farm_id=farm_id, observation_date=obs_date)
        .order_by("-created_at")
        .first()
    )

    if result is None:
        raise SatelliteServiceError(
            "Farm insights not found for this farm and date.",
            code=ResponseCode.SATELLITE_INSIGHTS_NOT_FOUND,
        )

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
        "alerts": [_serialize_alert(alert, language_code) for alert in alerts],
        "notifications": [_serialize_notification(notification, language_code) for notification in notifications],
        "irrigation_advisory": (
            {
                "date": irrigation_advisory["date"].isoformat(),
                "amount": irrigation_advisory["amount"],
            }
            if irrigation_advisory is not None
            else None
        ),
    }


def fetch_farm_events_by_farm_ids(*, observation_date: str, farm_ids: list[int], language_code=None):
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
            "alerts": [_serialize_alert(alert, language_code) for alert in alerts],
            "notifications": [_serialize_notification(notification, language_code) for notification in notifications],
        })

    return {"observation_date": obs_date.isoformat(), "results": results}


CHART_DEFINITIONS = [
    {
        "key": "CROP_GROWTH",
        "chart_name": "Crop Growth",
        "lines": [
            ("attainable_biomass_production_cumulative", "Attainable Crop Growth", "attainable_crop_production_cumulative"),
            ("water_unlimited_crop_production_cumulative", "Water Unlimited Crop Growth", "water_unlimited_crop_production_cumulative"),
            ("crop_production_cumulative", "Cumulative Crop Growth", "crop_production_cumulative"),
        ],
    },
    {
        "key": "PERCENT_VEGETATION_COVER",
        "chart_name": "Percent Vegetation Cover",
        "lines": [
            ("vegetation_cover", "Vegetation Cover", "vegetation_cover"),
        ],
    },
    {
        "key": "LEAF_NITROGEN",
        "chart_name": "Leaf Nitrogen",
        "lines": [
            ("leaf_nitrogen", "Leaf Nitrogen", "leaf_nitrogen"),
        ],
    },
    {
        "key": "SOIL_MOISTURE_PROBE",
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
        "key": "ACTUAL_ET",
        "chart_name": "Actual Evapotranspiration and Transpiration",
        "lines": [
            ("actual_evapotranspiration", "Actual Evapotranspiration", "actual_evapotranspiration"),
            ("actual_transpiration", "Actual Transpiration", "actual_transpiration"),
        ],
    },
    {
        "key": "CUMULATIVE_ET",
        "chart_name": "Cumulative Evapotranspiration, Irrigation, and Precipitation",
        "lines": [
            ("actual_evapotranspiration_cumulative", "Actual Evapotranspiration Cumulative (mm)", "actual_evapotranspiration_cumulative"),
            ("precipitation_cumulative", "Precipitation Cumulative (mm)", "precipitation_cumulative"),
            ("irrigation_amount_cumulative", "Irrigation Amount Cumulative (mm)", "irrigation_amount_cumulative"),
        ],
    },
    {
        "key": "TENSIOMETER",
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


def fetch_farm_charts(*, farm_id: int, observation_date: str, language_code=None):
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
        raise SatelliteServiceError(
            "Farm charts not found for this farm and date.",
            code=ResponseCode.SATELLITE_CHARTS_NOT_FOUND,
        )

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
            lines.append({"key": key, "label": localize_label(label, language_code), "data": data_points})
        charts.append({"key": chart_def["key"], "chart_name": localize_label(chart_def["chart_name"], language_code), "lines": lines})

    return {
        "farm_id": farm_id,
        "observation_date": obs_date.isoformat(),
        "charts": charts,
    }


def _localize_legend(legend, is_categorical, language_code):
    """Localize the text ``label`` of categorical legend entries (e.g. Moisture
    Status). Numeric legends carry only ``value``/``color`` and pass through."""
    if not is_categorical or not isinstance(legend, list):
        return legend
    return [
        {**entry, "label": localize_label(entry["label"], language_code)}
        if isinstance(entry, dict) and "label" in entry
        else entry
        for entry in legend
    ]


def fetch_farm_map_layers_by_farm_ids(*, observation_date: str, farm_ids: list[int], language_code=None):
    if not farm_ids:
        return {"observation_date": observation_date, "results": []}

    obs_date = previous_day(observation_date)

    rows = (
        SatelliteMapLayer.objects
        .filter(
            order_farm__farm_id__in=farm_ids,
            observation_date=obs_date,
            band_number__in=API_MAP_LAYER_NAMES,
        )
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
            "layer_name": localize_label(API_MAP_LAYER_NAMES[row["band_number"]], language_code),
            "unit": API_MAP_LAYER_UNITS.get(row["band_number"], ""),
            "png_url": row["png_url"],
            "bounds": row["bounds"],
            "legend": _localize_legend(row["legend"], row["is_categorical"], language_code),
            "is_categorical": row["is_categorical"],
        })

    results = [
        {"farm_id": farm_id, "observation_date": obs_date.isoformat(), "layers": layers}
        for farm_id, layers in layers_by_farm.items()
    ]
    return {"observation_date": obs_date.isoformat(), "results": results}