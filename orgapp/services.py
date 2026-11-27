"""
What an org user (ORG_USER) can see on the org dashboard.

Scope = the user's OrgMembership unit and every unit below it
(materialized path), the FPOs linked to those units, and those FPOs'
farmers and farms. Built on authapp.services.hierarchy, which the existing
hierarchy endpoints already use.
"""

from authapp.models import FarmerProfile, FpoProfile, OrgUnitFPO
from authapp.services.hierarchy import get_accessible_org_units
from farmerapp.models import Farm


def get_org_units(app_user):
    """The caller's unit and all units below it."""
    return get_accessible_org_units(app_user)


def get_org_fpos(app_user):
    """FPOs linked to any unit in the caller's subtree."""
    return FpoProfile.objects.filter(
        pk__in=OrgUnitFPO.objects.filter(
            org_unit__in=get_org_units(app_user)
        ).values("fpo_profile_id")
    )


def get_org_farmers(app_user):
    """Farmers registered with an in-scope FPO."""
    return FarmerProfile.objects.filter(
        registered_with_fpo__in=get_org_fpos(app_user)
    )


def get_org_farms(app_user):
    """Farms of in-scope farmers."""
    return Farm.objects.filter(
        farmer__farmer_profile__registered_with_fpo__in=get_org_fpos(app_user)
    )
