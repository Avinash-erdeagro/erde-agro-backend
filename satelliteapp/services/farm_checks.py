"""
Data-quality checks for farms: boundary problems, overlaps with other farms,
suspicious areas, and crop / lookup data that would stop a farm from being
sent for satellite data.

Used by the super-admin FPO detail page; meant to be reused when selecting
farms for satellite submission.

Each issue is a dict:
    {"code": str, "severity": "error" | "warning" | "info", "message": str, ...extra}
"""

import json
import logging
from collections import defaultdict

from django.db import connection

from farmerapp.models import Farm
from satelliteapp.services.order_submit import MIN_FARM_AREA_ACRES

logger = logging.getLogger(__name__)

ERROR, WARNING, INFO = "error", "warning", "info"

# Issue codes that describe an overlap with another farm (they carry other_farm_* fields).
OVERLAP_CODES = frozenset({"DUPLICATE", "INSIDE_OTHER", "CONTAINS_OTHER", "OVERLAP"})

# Overlap thresholds, as % of a farm's own area covered by another farm.
# Below MIN_OVERLAP_PCT it's treated as GPS noise along a shared edge.
MIN_OVERLAP_PCT = 5
# Both farms covered at least this much -> the same plot saved twice.
DUPLICATE_PCT = 95
# This farm covered at least this much (but not the other way) -> drawn inside another farm.
INSIDE_PCT = 80

# Farms bigger than this are almost always a wrongly drawn boundary.
MAX_PLAUSIBLE_AREA_ACRES = 50

_OVERLAP_SQL = f"""
    SELECT a.id, b.id,
           ST_Area(ST_Intersection(a.boundary, b.boundary)::geography),
           ST_Area(a.boundary::geography),
           ST_Area(b.boundary::geography)
    FROM {Farm._meta.db_table} a
    JOIN {Farm._meta.db_table} b
      ON b.id <> a.id AND ST_Intersects(a.boundary, b.boundary)
    WHERE a.id = ANY(%s)
      AND ST_IsValid(a.boundary) AND ST_IsValid(b.boundary)
"""

_INVALID_SQL = f"""
    SELECT id, ST_IsValidReason(boundary)
    FROM {Farm._meta.db_table}
    WHERE id = ANY(%s) AND NOT ST_IsValid(boundary)
"""


def _pct(part, whole):
    return round(part / whole * 100, 1) if whole else 0.0


def _find_overlaps(farm_ids):
    """{farm_id: [(other_id, pct_of_this, pct_of_other, overlap_m2)]} for real overlaps."""
    with connection.cursor() as cursor:
        cursor.execute(_OVERLAP_SQL, [farm_ids])
        rows = cursor.fetchall()

    overlaps = defaultdict(list)
    for farm_id, other_id, inter_m2, farm_m2, other_m2 in rows:
        pct_this, pct_other = _pct(inter_m2, farm_m2), _pct(inter_m2, other_m2)
        if max(pct_this, pct_other) >= MIN_OVERLAP_PCT:
            overlaps[farm_id].append((other_id, pct_this, pct_other, round(inter_m2)))
    return overlaps


def _find_invalid(farm_ids):
    with connection.cursor() as cursor:
        cursor.execute(_INVALID_SQL, [farm_ids])
        return dict(cursor.fetchall())


def _other_farm_info(other_ids):
    """Name, farmer and FPO of the farms we overlap with (they may be in another FPO)."""
    farms = Farm.objects.filter(id__in=other_ids).select_related(
        "farmer__farmer_profile__registered_with_fpo"
    )
    info = {}
    for farm in farms:
        profile = getattr(farm.farmer, "farmer_profile", None)
        fpo = profile.registered_with_fpo if profile else None
        info[farm.id] = {
            "other_farm_id": farm.id,
            "other_farm_name": farm.farm_name,
            "other_farmer_name": profile.farmer_name if profile else None,
            "other_fpo_id": fpo.id if fpo else None,
            "other_fpo_name": fpo.fpo_name if fpo else None,
        }
    return info


def _overlap_issue(other, pct_this, pct_other, overlap_m2):
    ref = f"farm #{other['other_farm_id']}"
    extra = {**other, "overlap_pct": pct_this, "other_overlap_pct": pct_other, "overlap_m2": overlap_m2}
    if pct_this >= DUPLICATE_PCT and pct_other >= DUPLICATE_PCT:
        return {"code": "DUPLICATE", "severity": ERROR, "message": f"Same boundary as {ref}", **extra}
    if pct_this >= INSIDE_PCT:
        return {
            "code": "INSIDE_OTHER",
            "severity": ERROR,
            "message": f"{pct_this:g}% of this farm lies inside {ref}",
            **extra,
        }
    if pct_other >= INSIDE_PCT:
        return {
            "code": "CONTAINS_OTHER",
            "severity": ERROR,
            "message": f"Covers {pct_other:g}% of {ref}",
            **extra,
        }
    return {
        "code": "OVERLAP",
        "severity": WARNING,
        "message": f"Overlaps {ref} ({pct_this:g}% of this farm)",
        **extra,
    }


def _farm_issues(farm, invalid_reason):
    """Checks that only need the farm itself (expects `active_crops` prefetched)."""
    issues = []
    if invalid_reason:
        issues.append({
            "code": "INVALID_BOUNDARY",
            "severity": ERROR,
            "message": f"Invalid boundary: {invalid_reason}",
        })

    area = farm.area or 0
    if area < MIN_FARM_AREA_ACRES:
        issues.append({
            "code": "TOO_SMALL",
            "severity": WARNING,
            "message": f"{area:g} ac is below the {MIN_FARM_AREA_ACRES} ac satellite minimum",
        })
    elif area > MAX_PLAUSIBLE_AREA_ACRES:
        issues.append({
            "code": "TOO_LARGE",
            "severity": WARNING,
            "message": f"{area:,.1f} ac is unusually large — boundary may be wrong",
        })

    crop = farm.active_crops[0] if farm.active_crops else None
    if crop is None:
        issues.append({"code": "NO_CROP", "severity": WARNING, "message": "No active crop"})
    elif crop.primary_crop_id is None:
        issues.append({
            "code": "CUSTOM_CROP",
            "severity": INFO,
            "message": f"Crop '{crop.custom_primary_crop_name}' was typed by hand, not chosen from the list",
        })
    elif crop.primary_crop.irriwatch_id is None:
        issues.append({
            "code": "NOT_MAPPED",
            "severity": INFO,
            "message": f"Crop '{crop.primary_crop.name}' has no IrriWatch mapping",
        })

    for label, lookup in (("Soil", farm.soil_type), ("Irrigation", farm.irrigation_type)):
        if lookup is not None and lookup.irriwatch_id is None:
            issues.append({
                "code": "NOT_MAPPED",
                "severity": INFO,
                "message": f"{label} '{lookup.name}' has no IrriWatch mapping",
            })
    return issues


def check_farms(farms):
    """
    Run every check for the given farms (with `active_crops`, soil_type and
    irrigation_type loaded). Returns {farm_id: [issue, ...]}.

    Overlaps are checked against ALL farms, not just the ones passed in, so
    duplicates registered under another FPO are caught too.
    """
    farm_ids = [f.id for f in farms]
    if not farm_ids:
        return {}

    invalid = _find_invalid(farm_ids)
    try:
        overlaps = _find_overlaps(farm_ids)
    except Exception:  # a geometry PostGIS can't intersect shouldn't break the page
        logger.exception("Overlap check failed for farms %s", farm_ids)
        overlaps = {}

    other_ids = {other_id for rows in overlaps.values() for other_id, *_ in rows}
    other_info = _other_farm_info(other_ids)

    result = {}
    for farm in farms:
        issues = _farm_issues(farm, invalid.get(farm.id))
        for other_id, pct_this, pct_other, overlap_m2 in sorted(
            overlaps.get(farm.id, []), key=lambda row: -row[1]
        ):
            issues.append(_overlap_issue(other_info[other_id], pct_this, pct_other, overlap_m2))
        result[farm.id] = issues
    return result


_INTERSECTION_SQL = f"""
    SELECT b.id, ST_AsGeoJSON(ST_Intersection(a.boundary, b.boundary))
    FROM {Farm._meta.db_table} a
    JOIN {Farm._meta.db_table} b ON b.id = ANY(%s)
    WHERE a.id = %s AND ST_IsValid(a.boundary) AND ST_IsValid(b.boundary)
"""


def overlap_geometries(farm_id, other_ids):
    """{other_id: GeoJSON geometry of the area shared with farm_id} (for drawing)."""
    if not other_ids:
        return {}
    try:
        with connection.cursor() as cursor:
            cursor.execute(_INTERSECTION_SQL, [list(other_ids), farm_id])
            return {other_id: json.loads(geojson) for other_id, geojson in cursor.fetchall() if geojson}
    except Exception:
        logger.exception("Intersection geometry failed for farm %s", farm_id)
        return {}
