"""
Client data scope.

Every client-facing view must get its data through these functions and
never query Farm / FarmerProfile directly. That keeps "what can this
client see" defined in exactly one place.

Rule: a client with no scope row, an inactive profile, or an empty
scope sees nothing (never "everything").
"""

from __future__ import annotations

import logging

from django.db.models import Q

from authapp.models import ClientProfile, FarmerProfile, OrgUnitFPO
from farmerapp.models import Farm, FarmCrop

logger = logging.getLogger(__name__)


def get_client_fpo_ids(client: ClientProfile) -> set[int]:
    """FPO ids the client can see: scope.fpos + FPOs under scope.org_units."""
    if client is None or not client.is_active:
        return set()

    scope = getattr(client, "scope", None)
    if scope is None:
        return set()

    fpo_ids = set(scope.fpos.values_list("pk", flat=True))

    unit_q = Q()
    for unit in scope.org_units.values("pk", "organization_id", "path"):
        if not unit["path"]:
            # An empty path would match every unit in the organization.
            # Skip it rather than widen the client's access.
            logger.warning(
                "Client %s scope skips OrgUnit %s: path is not set.",
                client.pk, unit["pk"],
            )
            continue
        unit_q |= Q(
            org_unit__organization_id=unit["organization_id"],
            org_unit__path__startswith=unit["path"],
        )

    if unit_q:
        fpo_ids |= set(
            OrgUnitFPO.objects.filter(unit_q).values_list("fpo_profile_id", flat=True)
        )

    return fpo_ids


def get_client_farms(client: ClientProfile):
    """
    Farms the client can see:
      source  - farms of farmers registered with any in-scope FPO
      filter  - if scope.crop_types is set, only farms whose active
                primary crop is one of them
    """
    fpo_ids = get_client_fpo_ids(client)
    if not fpo_ids:
        return Farm.objects.none()

    farms = Farm.objects.filter(
        farmer__farmer_profile__registered_with_fpo_id__in=fpo_ids
    )

    # Non-empty fpo_ids implies client.scope exists.
    crop_type_ids = list(client.scope.crop_types.values_list("pk", flat=True))
    if crop_type_ids:
        farms = farms.filter(
            pk__in=FarmCrop.objects.filter(
                is_active=True,
                primary_crop_id__in=crop_type_ids,
            ).values("farm_id")
        )

    return farms


def get_client_farmers(client: ClientProfile):
    """
    Farmers the client can see:
      - no filters set: every farmer registered with an in-scope FPO
        (including farmers who have not mapped a farm yet)
      - filters set:    only farmers with at least one in-scope farm
    """
    fpo_ids = get_client_fpo_ids(client)
    if not fpo_ids:
        return FarmerProfile.objects.none()

    farmers = FarmerProfile.objects.filter(registered_with_fpo_id__in=fpo_ids)

    if client.scope.crop_types.exists():
        farmers = farmers.filter(
            app_user_id__in=get_client_farms(client).values("farmer_id")
        )

    return farmers