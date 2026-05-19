"""
Platform stats views — SUPER_ADMIN only.

Aggregates counts and summaries across all apps. Add new stat endpoints here.
"""

from django.db.models import Count, Q
from rest_framework.views import APIView

from authapp.api.permissions import IsSuperAdmin
from authapp.api.responses import api_response
from authapp.models import AppUser, FarmerProfile, FpoProfile
from authapp.models.hierarchy import OrgMembership, OrgUnit, OrgUnitFPO, Organization
from billingapp.models import SatellitePlan
from farmerapp.models import Farm, FarmSatelliteSubscription, SatelliteSubscriptionStatus
from notificationapp.models import DeviceToken


class PlatformOverviewStatsView(APIView):
    """
    GET /mgmt/stats/overview/

    High-level platform counts. Use as a dashboard summary.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        org_id = request.query_params.get("organization")

        # --- User counts ---
        user_counts = AppUser.objects.values("role").annotate(total=Count("id"))
        users_by_role = {row["role"]: row["total"] for row in user_counts}

        # --- FPO counts ---
        fpo_qs = FpoProfile.objects.all()
        fpo_linked = OrgUnitFPO.objects.values_list("fpo_profile_id", flat=True)
        fpo_unlinked_count = fpo_qs.exclude(pk__in=fpo_linked).count()

        # --- Farmer counts ---
        farmer_qs = FarmerProfile.objects.all()

        # --- Farm counts ---
        farm_qs = Farm.objects.all()

        # --- Satellite subscription counts ---
        sub_counts = FarmSatelliteSubscription.objects.values("status").annotate(
            total=Count("id")
        )
        subs_by_status = {row["status"]: row["total"] for row in sub_counts}

        # --- Org structure counts ---
        org_count = Organization.objects.count()
        org_unit_count = OrgUnit.objects.count()
        org_user_count = OrgMembership.objects.count()

        # Scope to a single org if requested
        if org_id:
            org_unit_count = OrgUnit.objects.filter(organization_id=org_id).count()
            org_user_count = OrgMembership.objects.filter(
                org_unit__organization_id=org_id
            ).count()
            fpo_ids_in_org = OrgUnitFPO.objects.filter(
                org_unit__organization_id=org_id
            ).values_list("fpo_profile_id", flat=True)
            fpo_qs = fpo_qs.filter(pk__in=fpo_ids_in_org)
            farmer_qs = farmer_qs.filter(registered_with_fpo__in=fpo_qs)
            farm_qs = farm_qs.filter(farmer__farmer_profile__registered_with_fpo__in=fpo_qs)

        return api_response(
            success=True,
            message="Platform overview stats.",
            result={
                "users": {
                    "super_admin": users_by_role.get("SUPER_ADMIN", 0),
                    "org_users": users_by_role.get("ORG_USER", 0),
                    "fpo": users_by_role.get("FPO", 0),
                    "farmer": users_by_role.get("FARMER", 0),
                },
                "fpo": {
                    "total": fpo_qs.count(),
                    "linked_to_hierarchy": fpo_qs.filter(org_unit_link__isnull=False).count(),
                    "unlinked": fpo_unlinked_count if not org_id else None,
                },
                "farmers": {
                    "total": farmer_qs.count(),
                    "with_fpo": farmer_qs.filter(registered_with_fpo__isnull=False).count(),
                    "without_fpo": farmer_qs.filter(registered_with_fpo__isnull=True).count(),
                },
                "farms": {
                    "total": farm_qs.count(),
                },
                "satellite_subscriptions": subs_by_status,
                "hierarchy": {
                    "organizations": org_count,
                    "org_units": org_unit_count,
                    "org_users_assigned": org_user_count,
                },
            },
        )


class FPOStatsView(APIView):
    """
    GET /mgmt/stats/fpos/?organization=<id>

    Per-FPO breakdown: farmer count, farm count, active subscriptions.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        org_id = request.query_params.get("organization")

        fpo_qs = FpoProfile.objects.annotate(
            farmer_count=Count("registered_farmers", distinct=True),
            farm_count=Count("registered_farmers__app_user__farms", distinct=True),
            active_sub_count=Count(
                "registered_farmers__app_user__farms__satellite_subscriptions",
                filter=Q(
                    registered_farmers__app_user__farms__satellite_subscriptions__status=SatelliteSubscriptionStatus.COMPLETED
                ),
                distinct=True,
            ),
        )

        if org_id:
            fpo_ids = OrgUnitFPO.objects.filter(
                org_unit__organization_id=org_id
            ).values_list("fpo_profile_id", flat=True)
            fpo_qs = fpo_qs.filter(pk__in=fpo_ids)

        result = [
            {
                "fpo_id": fpo.pk,
                "fpo_name": fpo.fpo_name,
                "farmer_count": fpo.farmer_count,
                "farm_count": fpo.farm_count,
                "active_subscription_count": fpo.active_sub_count,
            }
            for fpo in fpo_qs
        ]

        return api_response(
            success=True,
            message="FPO stats.",
            result=result,
        )
