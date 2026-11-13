import json
import logging

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from authapp.models import FpoProfile
from farmerapp.models import (
    Farm,
    FarmCrop,
    FarmSatelliteSubscription,
    SatelliteSubscriptionStatus,
)
from satelliteapp.services.irriwatch import create_order

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = [
    SatelliteSubscriptionStatus.PAID,
    SatelliteSubscriptionStatus.SUBMITTED,
    SatelliteSubscriptionStatus.SYNCING,
]

MIN_FARM_AREA_ACRES = 0.3


class SkipFarm(Exception):
    """Raised when a farm can't be sent to IrriWatch; message is the reason."""


def field_name(farm):
    # Stable key used to map IrriWatch field uuids back to our farms.
    return f"farm-{farm.id}"


def get_fpo_farms(fpo):
    active_crops = FarmCrop.objects.filter(is_active=True).select_related("primary_crop")
    return (
        Farm.objects.filter(farmer__farmer_profile__registered_with_fpo=fpo)
        .select_related("soil_type", "irrigation_type")
        .prefetch_related(Prefetch("crops", queryset=active_crops, to_attr="active_crops"))
        .order_by("id")
    )


def build_feature(farm):
    if not farm.boundary:
        raise SkipFarm("no boundary")
    if not farm.boundary.valid:
        raise SkipFarm(f"invalid boundary: {farm.boundary.valid_reason}")
    if farm.area < MIN_FARM_AREA_ACRES:
        raise SkipFarm(f"area {farm.area} acres is below {MIN_FARM_AREA_ACRES} acres")

    crop = farm.active_crops[0] if farm.active_crops else None
    if crop is None:
        raise SkipFarm("no active crop")
    if crop.primary_crop is None or crop.primary_crop.irriwatch_id is None:
        raise SkipFarm(f"crop '{crop.primary_crop_name}' has no irriwatch_id")
    if farm.soil_type.irriwatch_id is None:
        raise SkipFarm(f"soil '{farm.soil_type.name}' has no irriwatch_id")
    if farm.irrigation_type.irriwatch_id is None:
        raise SkipFarm(f"irrigation '{farm.irrigation_type.name}' has no irriwatch_id")

    return {
        "type": "Feature",
        "properties": {
            "name": field_name(farm),
            "crop": crop.primary_crop.irriwatch_id,
            "irrigation": farm.irrigation_type.irriwatch_id,
            "soil": farm.soil_type.irriwatch_id,
        },
        "geometry": json.loads(farm.boundary.geojson),
    }


def get_reusable_subscription(farm):
    """Return an unsubmitted PAID subscription (or None); raise SkipFarm if already ordered."""
    existing = FarmSatelliteSubscription.objects.filter(
        farm=farm, status__in=ACTIVE_STATUSES
    ).first()
    if existing and (
        existing.status != SatelliteSubscriptionStatus.PAID or existing.irriwatch_order_uuid
    ):
        raise SkipFarm(f"already has {existing.status} subscription #{existing.id}")
    return existing


def get_or_create_subscription(farm, fpo, months):
    existing = get_reusable_subscription(farm)
    if existing:
        return existing

    return FarmSatelliteSubscription.objects.create(
        farm=farm,
        subscription_start=timezone.now().date(),
        subscription_duration_months=months,
        payment_reference=f"FPO-BULK-{fpo.id}",
        status=SatelliteSubscriptionStatus.PAID,
    )


def _field_uuids_by_name(order_response):
    mapping = {}
    for feature in order_response.get("fields", {}).get("features", []):
        props = feature.get("properties", {})
        if props.get("name") and props.get("uuid"):
            mapping[props["name"]] = props["uuid"]
    return mapping


def _submit_batch(company_uuid, batch, report):
    """batch = list of (farm, feature, subscription)."""
    feature_collection = {
        "type": "FeatureCollection",
        "features": [feature for _, feature, _ in batch],
    }

    try:
        response = create_order(company_uuid, feature_collection)
    except Exception as exc:
        reason = f"IrriWatch order failed: {exc}"
        body = getattr(getattr(exc, "response", None), "text", "")
        if body:
            reason = f"{reason} | {body[:1000]}"
        logger.exception("IrriWatch order failed for farms %s", [f.id for f, _, _ in batch])
        for farm, _, sub in batch:
            sub.failure_reason = reason
            sub.save(update_fields=["failure_reason", "updated_at"])
            report["failed"].append((farm.id, reason))
        return

    logger.info("IrriWatch order response: %s", json.dumps(response)[:5000])

    order_uuid = response.get("uuid")
    uuids = _field_uuids_by_name(response)
    now = timezone.now()

    # Order exists on IrriWatch now, so always mark SUBMITTED (re-running must
    # not re-order these farms), even if a field uuid couldn't be mapped.
    with transaction.atomic():
        for farm, _, sub in batch:
            field_uuid = uuids.get(field_name(farm))
            sub.irriwatch_order_uuid = order_uuid
            sub.irriwatch_field_uuid = field_uuid
            sub.status = SatelliteSubscriptionStatus.SUBMITTED
            sub.submitted_at = now
            sub.failure_reason = None if field_uuid else "field uuid not found in order response"
            sub.save()
            if field_uuid:
                report["submitted"].append(farm.id)
            else:
                report["unmapped"].append(farm.id)

    report["orders"].append(order_uuid)


def submit_fpo(fpo, company_uuid, months, batch_size=50, dry_run=False):
    """Send all eligible farms of one FPO to IrriWatch, in batches of `batch_size`."""
    report = {
        "fpo": str(fpo),
        "submitted": [],
        "unmapped": [],
        "skipped": [],
        "failed": [],
        "orders": [],
        "payloads": [],
    }

    eligible = []
    for farm in get_fpo_farms(fpo):
        try:
            feature = build_feature(farm)
            get_reusable_subscription(farm)
        except SkipFarm as exc:
            report["skipped"].append((farm.id, str(exc)))
            continue
        eligible.append((farm, feature))

    for start in range(0, len(eligible), batch_size):
        chunk = eligible[start:start + batch_size]

        if dry_run:
            report["payloads"].append(
                {"type": "FeatureCollection", "features": [f for _, f in chunk]}
            )
            continue

        batch = [
            (farm, feature, get_or_create_subscription(farm, fpo, months))
            for farm, feature in chunk
        ]
        _submit_batch(company_uuid, batch, report)

    return report


def submit_fpos(fpo_ids, company_uuid, months, batch_size=50, dry_run=False):
    fpos = FpoProfile.objects.filter(id__in=fpo_ids).order_by("id")
    missing = set(fpo_ids) - {f.id for f in fpos}
    if missing:
        raise ValueError(f"FpoProfile not found: {sorted(missing)}")

    return [
        submit_fpo(fpo, company_uuid, months, batch_size=batch_size, dry_run=dry_run)
        for fpo in fpos
    ]
