"""
Payment / billing views — SUPER_ADMIN only.

Shows satellite subscription plans and per-org/FPO subscription status.
Extend this file when payment gateway integration is added (e.g., Razorpay).
"""

from django.db.models import Count, Q, Sum
from rest_framework.views import APIView

from authapp.api.permissions import IsSuperAdmin
from authapp.api.responses import api_response
from authapp.models import FarmerProfile, FpoProfile
from authapp.models.hierarchy import OrgUnitFPO
from billingapp.models import SatellitePlan
from farmerapp.models import Farm, FarmSatelliteSubscription, SatelliteSubscriptionStatus


class SatellitePlanListView(APIView):
    """
    GET /mgmt/payments/plans/

    All active satellite subscription plans with pricing details.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        plans = SatellitePlan.objects.filter(is_active=True).values(
            "id",
            "name",
            "duration_days",
            "duration_months",
            "base_price_per_acre",
            "gst_percent",
            "total_price_per_acre",
            "commission_percent",
            "commission_amount_per_acre",
            "commission_gst_per_acre",
            "total_commission_per_acre",
        )
        return api_response(
            success=True,
            message="Active satellite plans.",
            result=list(plans),
        )


class SubscriptionSummaryView(APIView):
    """
    GET /mgmt/payments/subscriptions/summary/?organization=<id>

    Overall subscription status breakdown across the platform (or a single org).
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        org_id = request.query_params.get("organization")

        qs = FarmSatelliteSubscription.objects.all()

        if org_id:
            fpo_ids = OrgUnitFPO.objects.filter(
                org_unit__organization_id=org_id
            ).values_list("fpo_profile_id", flat=True)
            # FarmerProfile PKs under this org's FPOs
            farmer_profile_ids = FarmerProfile.objects.filter(
                registered_with_fpo_id__in=fpo_ids
            ).values_list("pk", flat=True)
            # Farm.farmer → AppUser; AppUser.farmer_profile → FarmerProfile
            qs = qs.filter(farm__farmer__farmer_profile__pk__in=farmer_profile_ids)

        counts = qs.values("status").annotate(total=Count("id"))
        by_status = {row["status"]: row["total"] for row in counts}

        revenue_qs = qs.filter(status=SatelliteSubscriptionStatus.COMPLETED)
        total_area = revenue_qs.aggregate(total=Sum("farm__area"))["total"] or 0

        return api_response(
            success=True,
            message="Subscription summary.",
            result={
                "by_status": by_status,
                "completed_total_farm_area_acres": float(total_area),
            },
        )


class FPOSubscriptionDetailView(APIView):
    """
    GET /mgmt/payments/subscriptions/by-fpo/?organization=<id>

    Per-FPO list showing how many subscriptions are active/pending/expired.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        org_id = request.query_params.get("organization")

        fpo_qs = FpoProfile.objects.annotate(
            active_subs=Count(
                "registered_farmers__app_user__farms__satellite_subscriptions",
                filter=Q(
                    registered_farmers__app_user__farms__satellite_subscriptions__status=SatelliteSubscriptionStatus.COMPLETED
                ),
                distinct=True,
            ),
            pending_subs=Count(
                "registered_farmers__app_user__farms__satellite_subscriptions",
                filter=Q(
                    registered_farmers__app_user__farms__satellite_subscriptions__status=SatelliteSubscriptionStatus.PAID
                ),
                distinct=True,
            ),
            expired_subs=Count(
                "registered_farmers__app_user__farms__satellite_subscriptions",
                filter=Q(
                    registered_farmers__app_user__farms__satellite_subscriptions__status__in=[
                        SatelliteSubscriptionStatus.FAILED
                    ]
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
                "active_subscriptions": fpo.active_subs,
                "pending_subscriptions": fpo.pending_subs,
                "expired_subscriptions": fpo.expired_subs,
            }
            for fpo in fpo_qs
        ]

        return api_response(
            success=True,
            message="Per-FPO subscription details.",
            result=result,
        )
