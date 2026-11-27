"""
GET /super-admin/farms/<id>/inspect/ — SUPER_ADMIN only.

Everything needed to investigate one farm's data problems: the farm itself,
its issues, and every farm it overlaps (from any FPO) with boundaries and the
shared area, so the admin can see on a map whether it's a duplicate entry,
a farm drawn inside another, or two farmers claiming the same land.
"""

import json

from rest_framework.views import APIView

from authapp.api.permissions import IsSuperAdmin
from authapp.api.response_codes import ResponseCode
from authapp.api.responses import api_response
from farmerapp.models import Farm
from satelliteapp.services.farm_checks import OVERLAP_CODES, check_farms, overlap_geometries

from .fpo_detail import NOT_SENT, crop_details, current_subscription, with_farm_details


def _farm_summary(farm):
    profile = getattr(farm.farmer, "farmer_profile", None)
    fpo = profile.registered_with_fpo if profile else None
    crop = farm.active_crops[0] if farm.active_crops else None
    sub = current_subscription(farm)
    return {
        "id": farm.id,
        "farm_name": farm.farm_name,
        "land_record_number": farm.land_record_number,
        "created_at": farm.created_at.isoformat(),
        "area": round(farm.area or 0, 2),
        "farmer": (
            {"id": profile.id, "name": profile.farmer_name, "contact_number": profile.contact_number}
            if profile
            else None
        ),
        "fpo": {"id": fpo.id, "name": fpo.fpo_name} if fpo else None,
        "crop": crop_details(crop),
        "soil_type": farm.soil_type.name if farm.soil_type else None,
        "irrigation_type": farm.irrigation_type.name if farm.irrigation_type else None,
        "satellite_status": sub.status if sub else NOT_SENT,
        "latest_observation_date": (
            farm.latest_observation_date.isoformat() if farm.latest_observation_date else None
        ),
        "boundary": json.loads(farm.boundary.geojson) if farm.boundary else None,
    }


class SuperAdminFarmInspectView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        farm = with_farm_details(Farm.objects.filter(pk=pk)).first()
        if farm is None:
            return api_response(
                success=False,
                message="Farm not found.",
                code=ResponseCode.FARM_NOT_FOUND,
                result=None,
                status_code=404,
            )

        issues = check_farms([farm]).get(farm.id, [])
        overlap_issues = [i for i in issues if i["code"] in OVERLAP_CODES]
        other_ids = [i["other_farm_id"] for i in overlap_issues]

        others = {f.id: f for f in with_farm_details(Farm.objects.filter(id__in=other_ids))}
        shared_areas = overlap_geometries(farm.id, other_ids)
        this_profile = getattr(farm.farmer, "farmer_profile", None)
        this_farmer_id = this_profile.id if this_profile else None
        this_fpo_id = this_profile.registered_with_fpo_id if this_profile else None

        overlaps = []
        for issue in overlap_issues:
            other = others.get(issue["other_farm_id"])
            if other is None:
                continue
            summary = _farm_summary(other)
            overlaps.append(
                {
                    "code": issue["code"],
                    "severity": issue["severity"],
                    "message": issue["message"],
                    "overlap_m2": issue["overlap_m2"],
                    "overlap_pct": issue["overlap_pct"],
                    "other_overlap_pct": issue["other_overlap_pct"],
                    "same_farmer": (summary["farmer"] or {}).get("id") == this_farmer_id,
                    "same_fpo": (summary["fpo"] or {}).get("id") == this_fpo_id,
                    "shared_area": shared_areas.get(other.id),
                    "farm": summary,
                }
            )

        return api_response(
            success=True,
            message="Farm inspection fetched.",
            code=ResponseCode.FARM_INSPECTION_FETCHED,
            result={
                "farm": _farm_summary(farm),
                "issues": [i for i in issues if i["code"] not in OVERLAP_CODES],
                "overlaps": overlaps,
            },
        )
