"""
Single-FPO views for the super-admin FPO detail page — SUPER_ADMIN only.

  GET /super-admin/fpos/<id>/          FPO info, org placement and summary stats
  GET /super-admin/fpos/<id>/farms/    every farm with crop details, satellite status,
                                       boundary and data-quality issues (overlaps etc.)
  GET /super-admin/fpos/<id>/farmers/  every farmer with farm count and total area
"""

import json
from collections import Counter

from django.db.models import Count, OuterRef, Prefetch, Subquery, Sum
from rest_framework.views import APIView

from authapp.api.permissions import IsSuperAdmin
from authapp.api.response_codes import ResponseCode
from authapp.api.responses import api_response
from authapp.models import FarmerProfile, FpoProfile
from farmerapp.models import Farm, FarmCrop, FarmSatelliteSubscription
from satelliteapp.models.provider import SatelliteResult
from satelliteapp.services.farm_checks import check_farms

# Status shown for farms that have never had a satellite subscription.
NOT_SENT = "NOT_SENT"


def _fpo_not_found():
    return api_response(
        success=False,
        message="FPO not found.",
        code=ResponseCode.FPO_NOT_FOUND,
        result=None,
        status_code=404,
    )


def _locality(locality):
    if not locality:
        return None
    return {
        "district": locality.district,
        "state": locality.state,
        "pin_code": getattr(locality, "pin_code", None),
    }


def _fpo_farms(fpo):
    """Farms of the FPO with what the detail page needs prefetched/annotated."""
    latest_observation = (
        SatelliteResult.objects.filter(order_farm__farm=OuterRef("pk"))
        .order_by("-observation_date")
        .values("observation_date")[:1]
    )
    return (
        Farm.objects.filter(farmer__farmer_profile__registered_with_fpo=fpo)
        .select_related("farmer__farmer_profile", "soil_type", "irrigation_type")
        .prefetch_related(
            Prefetch(
                "crops",
                queryset=FarmCrop.objects.filter(is_active=True).select_related(
                    "primary_crop", "intercrop"
                ),
                to_attr="active_crops",
            ),
            Prefetch(
                "satellite_subscriptions",
                queryset=FarmSatelliteSubscription.objects.order_by("-created_at"),
                to_attr="subscriptions_newest_first",
            ),
        )
        .annotate(latest_observation_date=Subquery(latest_observation))
        .order_by("id")
    )


def _crop_details(crop):
    """Active crop, with whether each name was chosen from the list or typed by hand."""
    if crop is None:
        return None
    return {
        "name": crop.primary_crop_name,
        "source": "LIST" if crop.primary_crop_id else "CUSTOM",
        "variety": crop.primary_crop_variety or None,
        "intercrop": crop.intercrop_name,
        "intercrop_source": (
            "LIST" if crop.intercrop_id else ("CUSTOM" if crop.custom_intercrop_name else None)
        ),
        "intercrop_variety": crop.intercrop_variety or None,
        "plantation_date": crop.plantation_date.isoformat() if crop.plantation_date else None,
    }


def _current_subscription(farm):
    return farm.subscriptions_newest_first[0] if farm.subscriptions_newest_first else None


def _satellite_status(farm):
    sub = _current_subscription(farm)
    return sub.status if sub else NOT_SENT


class SuperAdminFPODetailView(APIView):
    """GET /super-admin/fpos/<id>/ — FPO info, org placement and summary stats."""

    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        fpo = (
            FpoProfile.objects.select_related("locality")
            .prefetch_related("org_unit_link__org_unit__organization", "org_unit_link__org_unit__hierarchy_level")
            .filter(pk=pk)
            .first()
        )
        if fpo is None:
            return _fpo_not_found()

        farms = list(_fpo_farms(fpo))
        status_counts = Counter(_satellite_status(f) for f in farms)

        link = getattr(fpo, "org_unit_link", None)
        unit = link.org_unit if link else None

        return api_response(
            success=True,
            message="FPO details fetched.",
            code=ResponseCode.FPO_DETAILS_FETCHED,
            result={
                "id": fpo.pk,
                "fpo_name": fpo.fpo_name,
                "contact_person_name": fpo.contact_person_name,
                "mobile": fpo.mobile,
                "email": fpo.email,
                "locality": _locality(fpo.locality),
                "organization": (
                    {"id": unit.organization_id, "name": unit.organization.name} if unit else None
                ),
                "org_unit": (
                    {
                        "id": unit.id,
                        "name": unit.name,
                        "level_name": unit.hierarchy_level.name if unit.hierarchy_level else None,
                    }
                    if unit
                    else None
                ),
                "stats": {
                    "farmers": FarmerProfile.objects.filter(registered_with_fpo=fpo).count(),
                    "farms": len(farms),
                    "mapped_area_acres": round(sum(f.area or 0 for f in farms), 2),
                    "satellite_area_acres": round(
                        sum(f.area or 0 for f in farms if f.latest_observation_date), 2
                    ),
                    "satellite_status": dict(status_counts),
                },
            },
        )


class SuperAdminFPOFarmsView(APIView):
    """GET /super-admin/fpos/<id>/farms/ — farms with crop, satellite status, boundary and issues."""

    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        fpo = FpoProfile.objects.filter(pk=pk).first()
        if fpo is None:
            return _fpo_not_found()

        farms = list(_fpo_farms(fpo))
        issues_by_farm = check_farms(farms)

        result = []
        for farm in farms:
            farmer = farm.farmer.farmer_profile
            crop = farm.active_crops[0] if farm.active_crops else None
            sub = _current_subscription(farm)
            result.append(
                {
                    "id": farm.id,
                    "farm_name": farm.farm_name,
                    "farmer_id": farmer.id,
                    "farmer_name": farmer.farmer_name,
                    "area": round(farm.area or 0, 2),
                    "crop": _crop_details(crop),
                    "soil_type": farm.soil_type.name if farm.soil_type else None,
                    "irrigation_type": farm.irrigation_type.name if farm.irrigation_type else None,
                    "satellite_status": sub.status if sub else NOT_SENT,
                    "subscription_end": sub.subscription_end.isoformat() if sub else None,
                    "failure_reason": sub.failure_reason if sub else None,
                    "latest_observation_date": (
                        farm.latest_observation_date.isoformat()
                        if farm.latest_observation_date
                        else None
                    ),
                    "boundary": json.loads(farm.boundary.geojson) if farm.boundary else None,
                    "issues": issues_by_farm.get(farm.id, []),
                }
            )

        return api_response(
            success=True,
            message=f"{len(result)} farm(s) found.",
            code=ResponseCode.FPO_FARMS_FETCHED,
            result=result,
        )


class SuperAdminFPOFarmersView(APIView):
    """GET /super-admin/fpos/<id>/farmers/ — farmers with farm count and total area."""

    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        if not FpoProfile.objects.filter(pk=pk).exists():
            return _fpo_not_found()

        farmers = (
            FarmerProfile.objects.filter(registered_with_fpo_id=pk)
            .select_related("locality")
            .annotate(
                farm_count=Count("app_user__farms", distinct=True),
                total_area=Sum("app_user__farms__area"),
            )
            .order_by("farmer_name")
        )

        result = [
            {
                "id": f.id,
                "farmer_name": f.farmer_name,
                "contact_number": f.contact_number,
                "district": f.locality.district if f.locality else None,
                "state": f.locality.state if f.locality else None,
                "farm_count": f.farm_count,
                "total_area": round(f.total_area or 0, 2),
            }
            for f in farmers
        ]

        return api_response(
            success=True,
            message=f"{len(result)} farmer(s) found.",
            code=ResponseCode.FPO_FARMERS_FETCHED,
            result=result,
        )
