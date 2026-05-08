"""
Hierarchy service layer.

All subtree queries use the materialized `path` field on OrgUnit for O(1) depth
lookups instead of recursive SQL. Path management (set_org_unit_path,
move_org_unit) must be called explicitly — it is NOT wired into model.save().
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from authapp.models import AppUser, FarmerProfile, FpoProfile
from authapp.models.hierarchy import OrgMembership, OrgUnit, OrgUnitFPO

User = get_user_model()


# ---------------------------------------------------------------------------
# Path management
# ---------------------------------------------------------------------------


def set_org_unit_path(org_unit: OrgUnit) -> None:
    """
    Compute and persist the materialized path for `org_unit`.
    Call this after creating or re-parenting a node.
    """
    if org_unit.parent_id is None:
        org_unit.path = f"/{org_unit.pk}/"
    else:
        parent = OrgUnit.objects.get(pk=org_unit.parent_id)
        org_unit.path = f"{parent.path}{org_unit.pk}/"
    org_unit.save(update_fields=["path"])


@transaction.atomic
def move_org_unit(org_unit: OrgUnit, new_parent: OrgUnit | None) -> None:
    """
    Re-parent `org_unit` to `new_parent` (or make it a root if None) and
    update the paths of all descendant nodes in a single pass.
    """
    old_path = org_unit.path
    org_unit.parent = new_parent
    set_org_unit_path(org_unit)
    new_path = org_unit.path

    # Update all descendants: replace the old path prefix with the new one.
    descendants = OrgUnit.objects.filter(path__startswith=old_path).exclude(
        pk=org_unit.pk
    )
    for descendant in descendants:
        descendant.path = new_path + descendant.path[len(old_path):]
        descendant.save(update_fields=["path"])


# ---------------------------------------------------------------------------
# Subtree access helpers
# ---------------------------------------------------------------------------


def _get_caller_org_unit(app_user: AppUser) -> OrgUnit | None:
    """Return the OrgUnit the caller is assigned to, or None."""
    try:
        return app_user.org_membership.org_unit
    except OrgMembership.DoesNotExist:
        return None


def get_accessible_org_units(app_user: AppUser):
    """
    Return a queryset of all OrgUnit nodes at or below the caller's node.
    SUPER_ADMIN receives all OrgUnits across every organization.
    Returns an empty queryset if the caller has no OrgMembership.
    """
    if app_user.role == AppUser.Role.SUPER_ADMIN:
        return OrgUnit.objects.all()
    org_unit = _get_caller_org_unit(app_user)
    if org_unit is None:
        return OrgUnit.objects.none()
    return OrgUnit.objects.filter(
        organization=org_unit.organization,
        path__startswith=org_unit.path,
    )


def get_accessible_fpo_profiles(app_user: AppUser):
    """
    Return a queryset of FpoProfile instances visible to `app_user` based on
    their position in the org hierarchy.
    SUPER_ADMIN receives all FpoProfiles regardless of org linkage.
    """
    if app_user.role == AppUser.Role.SUPER_ADMIN:
        return FpoProfile.objects.all()
    accessible_units = get_accessible_org_units(app_user)
    fpo_profile_ids = OrgUnitFPO.objects.filter(
        org_unit__in=accessible_units
    ).values_list("fpo_profile_id", flat=True)
    return FpoProfile.objects.filter(pk__in=fpo_profile_ids)


def get_accessible_farmer_profiles(app_user: AppUser):
    """
    Return a queryset of FarmerProfile instances visible to `app_user`.
    Farmers are reachable via FpoProfile → FarmerProfile.registered_with_fpo.
    SUPER_ADMIN receives all FarmerProfiles.
    """
    if app_user.role == AppUser.Role.SUPER_ADMIN:
        return FarmerProfile.objects.all()
    accessible_fpos = get_accessible_fpo_profiles(app_user)
    return FarmerProfile.objects.filter(registered_with_fpo__in=accessible_fpos)


# ---------------------------------------------------------------------------
# Impersonation
# ---------------------------------------------------------------------------


def can_impersonate(requester: AppUser, target: AppUser) -> tuple[bool, str]:
    """
    Return (True, "") if `requester` may impersonate `target`, else
    (False, <reason>) explaining why not.

    Rules:
    - Requester must be SUPER_ADMIN or ORG_USER.
    - Target must be ORG_USER (FPO and FARMER are explicitly excluded).
    - SUPER_ADMIN may impersonate any ORG_USER in any organization.
    - ORG_USER may only impersonate ORG_USER nodes strictly below them
      in the same organization.
    - A user cannot impersonate themselves.
    """
    if requester.role not in (AppUser.Role.SUPER_ADMIN, AppUser.Role.ORG_USER):
        return False, "Only Super Admin or Org User accounts can impersonate others."

    if target.role != AppUser.Role.ORG_USER:
        return (
            False,
            "Impersonation is restricted to ORG_USER accounts. "
            "FPO and Farmer accounts cannot be impersonated.",
        )

    if requester.pk == target.pk:
        return False, "Cannot impersonate yourself."

    # SUPER_ADMIN: no further hierarchy checks needed.
    if requester.role == AppUser.Role.SUPER_ADMIN:
        return True, ""

    # ORG_USER: must be in the same org and strictly above the target.
    requester_unit = _get_caller_org_unit(requester)
    target_unit = _get_caller_org_unit(target)

    if requester_unit is None or target_unit is None:
        return False, "Both requester and target must have an OrgMembership."

    if requester_unit.organization_id != target_unit.organization_id:
        return False, "Cannot impersonate users outside your organization."

    # Target must be in a subtree strictly below requester.
    if not target_unit.path.startswith(requester_unit.path) or target_unit.path == requester_unit.path:
        return False, "You can only impersonate users below you in the hierarchy."

    return True, ""


def generate_impersonation_token(requester: AppUser, target: AppUser) -> dict:
    """
    Mint a standard JWT token pair for `target` with an extra claim
    `impersonated_by` carrying the requester's user_id for traceability.

    Returns a dict with `access` and `refresh` keys.
    Raises PermissionError if impersonation is not allowed.
    """
    allowed, reason = can_impersonate(requester, target)
    if not allowed:
        raise PermissionError(reason)

    refresh = RefreshToken.for_user(target.user)
    refresh["impersonated_by"] = requester.user_id

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "impersonated_user_id": target.pk,
        "impersonated_username": target.user.username,
    }
