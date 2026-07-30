from datetime import date
from typing import Any

from satelliteapp.models import AlertType, SatelliteFarmAlert, SatelliteResult
from satelliteapp.services.metrics import calculate_soil_moisture
from satelliteapp.services.utils import to_float

def _build_rain_alert_details(data_json: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data_json:
        return None

    precipitation_fcdp0 = to_float(data_json.get("precipitation_fcdp0"))
    precipitation_fcdp1 = to_float(data_json.get("precipitation_fcdp1"))
    precipitation_fcdp2 = to_float(data_json.get("precipitation_fcdp2"))

    values = [precipitation_fcdp0, precipitation_fcdp1, precipitation_fcdp2]
    if any(value is not None and value > 20 for value in values):
        return {
            "precipitation_fcdp0": precipitation_fcdp0,
            "precipitation_fcdp1": precipitation_fcdp1,
            "precipitation_fcdp2": precipitation_fcdp2,
        }

    return None


def _get_recent_actual_crop_production_points(
    order_farm_id: int,
    observation_date: date,
) -> list[tuple[date, float]]:
    rows = list(
        SatelliteResult.objects.filter(
            order_farm_id=order_farm_id,
            observation_date__lte=observation_date,
        )
        .order_by("-observation_date")[:10]
    )

    rows = list(reversed(rows))
    points: list[tuple[date, float]] = []

    for row in rows:
        data_json = row.data_json or {}
        actual_crop_production = to_float(data_json.get("actual_crop_production"))
        if actual_crop_production is None:
            return []

        points.append((row.observation_date, actual_crop_production))

    return points


def _build_crop_health_dropping_details(
    order_farm_id: int,
    observation_date: date,
) -> dict[str, Any] | None:
    points = _get_recent_actual_crop_production_points(order_farm_id, observation_date)
    if len(points) < 10:
        return None

    first_value = points[0][1]
    last_value = points[-1][1]

    if first_value == 0:
        return None

    downward_moves = 0
    upward_moves = 0

    for index in range(1, len(points)):
        previous_value = points[index - 1][1]
        current_value = points[index][1]

        if previous_value == 0:
            return None

        change_pct = ((current_value - previous_value) / previous_value) * 100

        if change_pct < -5:
            downward_moves += 1
        elif change_pct > 5:
            upward_moves += 1

    overall_change_pct = ((last_value - first_value) / first_value) * 100

    if overall_change_pct >= -5:
        return None

    if downward_moves == 0:
        return None

    if upward_moves > 0:
        return None

    return {
        "first_actual_crop_production": first_value,
        "last_actual_crop_production": last_value,
        "overall_change_pct": overall_change_pct,
        "days_considered": len(points),
    }


def build_alert_payloads_for_result(
    satellite_result: SatelliteResult,
) -> dict[str, dict[str, Any]]:
    data_json = satellite_result.data_json or {}
    alerts: dict[str, dict[str, Any]] = {}

    soil_moisture = calculate_soil_moisture(data_json)

    if soil_moisture is not None and soil_moisture < 20:
        alerts[AlertType.CRITICAL_WATER_STRESS] = {
            "soil_moisture": soil_moisture,
        }

    if soil_moisture is not None and soil_moisture > 95:
        alerts[AlertType.OVERWATERING_DETECTED] = {
            "soil_moisture": soil_moisture,
        }

    crop_health_details = _build_crop_health_dropping_details(
        order_farm_id=satellite_result.order_farm_id,
        observation_date=satellite_result.observation_date,
    )
    if crop_health_details is not None:
        alerts[AlertType.CROP_HEALTH_DROPPING] = crop_health_details

    rain_alert_details = _build_rain_alert_details(data_json)
    if rain_alert_details is not None:
        alerts[AlertType.RAIN_ALERT_SKIP_IRRIGATION] = rain_alert_details

    return alerts


def sync_alerts_for_result(satellite_result: SatelliteResult) -> None:
    desired_alerts = build_alert_payloads_for_result(satellite_result)

    existing_alerts = SatelliteFarmAlert.objects.filter(
        order_farm_id=satellite_result.order_farm_id,
        observation_date=satellite_result.observation_date,
    )
    existing_by_type = {alert.alert_type: alert for alert in existing_alerts}

    for alert_type, details_json in desired_alerts.items():
        existing_alert = existing_by_type.get(alert_type)

        if existing_alert:
            existing_alert.details_json = details_json
            existing_alert.save(update_fields=["details_json"])
            continue

        SatelliteFarmAlert.objects.create(
            order_farm_id=satellite_result.order_farm_id,
            observation_date=satellite_result.observation_date,
            alert_type=alert_type,
            details_json=details_json,
        )

    for alert_type, existing_alert in existing_by_type.items():
        if alert_type not in desired_alerts:
            existing_alert.delete()