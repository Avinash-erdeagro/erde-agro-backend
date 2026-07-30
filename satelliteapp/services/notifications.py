from datetime import date, timedelta
from typing import Any

from satelliteapp.models import (
    NotificationType,
    SatelliteFarmNotification,
    SatelliteResult,
)
from satelliteapp.services.metrics import calculate_crop_growth, calculate_soil_moisture
from satelliteapp.services.utils import to_float

def _frequency_window_days(notification_type: str) -> int:
    if notification_type in {
        NotificationType.GROWTH_LOOKS_GREAT,
        NotificationType.MONITOR_FIELD_CLOSELY_CROP_HEALTH,
    }:
        return 5

    if notification_type == NotificationType.MONITOR_FIELD_CLOSELY_FERTILIZER_LEVELS:
        return 7

    return 1


def _notification_allowed(
    order_farm_id: int,
    observation_date: date,
    notification_type: str,
) -> bool:
    window_days = _frequency_window_days(notification_type)

    if window_days <= 1:
        return True

    exists = SatelliteFarmNotification.objects.filter(
        order_farm_id=order_farm_id,
        notification_type=notification_type,
        observation_date__lt=observation_date,
        observation_date__gte=observation_date - timedelta(days=window_days - 1),
    ).exists()

    return not exists


def _build_plan_irrigation_details(
    observation_date: date,
    data_json: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not data_json:
        return None

    irrigation_yesno = to_float(data_json.get("irrigation_yesno"))
    if irrigation_yesno != 1:
        return None

    irrigation_schedule: list[dict[str, Any]] = []

    for day_offset in range(8):
        amount = to_float(data_json.get(f"applied_water_fcdp{day_offset}"))
        if amount is None or amount <= 0:
            continue

        irrigation_schedule.append(
            {
                "date": (observation_date + timedelta(days=day_offset + 1)).isoformat(),
                "amount": amount,
            }
        )

    if not irrigation_schedule:
        return None

    return {
        "irrigation_schedule": irrigation_schedule,
    }


def build_notification_payloads_for_result(
    satellite_result: SatelliteResult,
) -> dict[str, dict[str, Any]]:
    data_json = satellite_result.data_json or {}
    notifications: dict[str, dict[str, Any]] = {}
    order_farm_id = satellite_result.order_farm_id
    observation_date = satellite_result.observation_date

    soil_moisture = calculate_soil_moisture(data_json)
    crop_growth = calculate_crop_growth(data_json)
    leaf_nitrogen = to_float(data_json.get("leaf_nitrogen"))
    vegetation_cover = to_float(data_json.get("vegetation_cover"))

    if (
        soil_moisture is not None
        and soil_moisture < 35
        and _notification_allowed(
            order_farm_id, observation_date, NotificationType.YOUR_FIELD_IS_DRYING
        )
    ):
        notifications[NotificationType.YOUR_FIELD_IS_DRYING] = {
            "soil_moisture": soil_moisture,
        }

    if (
        soil_moisture is not None
        and 36 <= soil_moisture <= 80
        and _notification_allowed(
            order_farm_id, observation_date, NotificationType.MOISTURE_IS_IDEAL
        )
    ):
        notifications[NotificationType.MOISTURE_IS_IDEAL] = {
            "soil_moisture": soil_moisture,
        }

    if (
        crop_growth is not None
        and crop_growth > 70
        and _notification_allowed(
            order_farm_id, observation_date, NotificationType.GROWTH_LOOKS_GREAT
        )
    ):
        notifications[NotificationType.GROWTH_LOOKS_GREAT] = {
            "crop_growth": crop_growth,
            "actual_crop_production": to_float(data_json.get("actual_crop_production")),
            "attainable_crop_production": to_float(data_json.get("attainable_crop_production")),
        }

    if (
        crop_growth is not None
        and crop_growth < 70
        and _notification_allowed(
            order_farm_id,
            observation_date,
            NotificationType.MONITOR_FIELD_CLOSELY_CROP_HEALTH,
        )
    ):
        notifications[NotificationType.MONITOR_FIELD_CLOSELY_CROP_HEALTH] = {
            "crop_growth": crop_growth,
            "actual_crop_production": to_float(data_json.get("actual_crop_production")),
            "attainable_crop_production": to_float(data_json.get("attainable_crop_production")),
        }

    if (
        leaf_nitrogen is not None
        and leaf_nitrogen < 0.8
        and vegetation_cover is not None
        and vegetation_cover > 50
        and _notification_allowed(
            order_farm_id,
            observation_date,
            NotificationType.MONITOR_FIELD_CLOSELY_FERTILIZER_LEVELS,
        )
    ):
        notifications[NotificationType.MONITOR_FIELD_CLOSELY_FERTILIZER_LEVELS] = {
            "leaf_nitrogen": leaf_nitrogen,
            "vegetation_cover": vegetation_cover,
        }

    irrigation_details = _build_plan_irrigation_details(
        observation_date=observation_date,
        data_json=data_json,
    )
    if (
        irrigation_details is not None
        and _notification_allowed(
            order_farm_id,
            observation_date,
            NotificationType.PLAN_IRRIGATION_THIS_WEEK,
        )
    ):
        notifications[NotificationType.PLAN_IRRIGATION_THIS_WEEK] = irrigation_details

    return notifications


def sync_notifications_for_result(satellite_result: SatelliteResult) -> None:
    desired_notifications = build_notification_payloads_for_result(satellite_result)

    existing_notifications = SatelliteFarmNotification.objects.filter(
        order_farm_id=satellite_result.order_farm_id,
        observation_date=satellite_result.observation_date,
    )
    existing_by_type = {
        notification.notification_type: notification
        for notification in existing_notifications
    }

    for notification_type, details_json in desired_notifications.items():
        existing_notification = existing_by_type.get(notification_type)

        if existing_notification:
            existing_notification.details_json = details_json
            existing_notification.save(update_fields=["details_json"])
            continue

        SatelliteFarmNotification.objects.create(
            order_farm_id=satellite_result.order_farm_id,
            observation_date=satellite_result.observation_date,
            notification_type=notification_type,
            details_json=details_json,
        )

    for notification_type, existing_notification in existing_by_type.items():
        if notification_type not in desired_notifications:
            existing_notification.delete()
