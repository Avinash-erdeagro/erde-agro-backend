from datetime import timedelta
from typing import Any

from satelliteapp.services.utils import to_float


def calculate_soil_moisture(data_json: dict[str, Any] | None) -> float | None:
    if not data_json:
        return None

    soil_moisture_root_zone = to_float(data_json.get("soil_moisture_root_zone"))
    critical_soil_moisture_root_zone = to_float(
        data_json.get("critical_soil_moisture_root_zone")
    )
    theta_fc_sub = to_float(data_json.get("theta_fc_sub"))

    if (
        soil_moisture_root_zone is None
        or critical_soil_moisture_root_zone is None
        or theta_fc_sub is None
    ):
        return None

    denominator = theta_fc_sub - critical_soil_moisture_root_zone
    if denominator == 0:
        return None

    return min(
        max(
            ((soil_moisture_root_zone - critical_soil_moisture_root_zone) / denominator) * 100,
            0,
        ),
        100,
    )


def calculate_crop_growth(data_json: dict[str, Any] | None) -> float | None:
    if not data_json:
        return None

    actual_crop_production = to_float(data_json.get("actual_crop_production"))
    attainable_crop_production = to_float(data_json.get("attainable_crop_production"))

    if actual_crop_production is None or attainable_crop_production is None:
        return None

    if attainable_crop_production == 0:
        return None

    return (actual_crop_production / attainable_crop_production) * 100


def calculate_average_temperature(data_json: dict[str, Any] | None) -> float | None:
    if not data_json:
        return None

    air_temperature_min_24 = to_float(data_json.get("air_temperature_min_24"))
    air_temperature_max_24 = to_float(data_json.get("air_temperature_max_24"))
    air_temperature_24 = to_float(data_json.get("air_temperature_24"))

    if air_temperature_min_24 is None or air_temperature_max_24 is None:
        return air_temperature_24

    return (air_temperature_min_24 + air_temperature_max_24) / 2


def build_irrigation_advisory(
    observation_date,
    data_json: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not data_json:
        return None

    for day_offset in range(8):
        key = f"applied_water_fcdp{day_offset}"
        amount = to_float(data_json.get(key))

        if amount is None or amount <= 0:
            continue

        return {
            "date": observation_date + timedelta(days=day_offset) + timedelta(days=1),
            "amount": amount,
        }

    # No positive applied-water forecast in the 8-day window: still return an
    # advisory with a zero amount (dated to the first forecast day) instead of
    # omitting it, so consumers always receive a numeric amount.
    return {
        "date": observation_date + timedelta(days=1),
        "amount": 0.0,
    }