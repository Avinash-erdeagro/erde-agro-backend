"""
Notification status views — SUPER_ADMIN only.

Shows device token coverage and push-notification delivery stats.
New notification models (e.g., NotificationLog) can be added to notificationapp
and referenced here for per-user / per-org delivery reports.
"""

from django.db.models import Count
from rest_framework.views import APIView

from authapp.api.permissions import IsSuperAdmin
from authapp.api.responses import api_response
from authapp.models import AppUser
from authapp.models.hierarchy import OrgUnit, OrgUnitFPO
from notificationapp.models import DeviceToken


class DeviceTokenStatsView(APIView):
    """
    GET /mgmt/notifications/device-tokens/

    Summary of registered device tokens by platform and user role.
    Scoped to an org with ?organization=<id>.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        org_id = request.query_params.get("organization")

        qs = DeviceToken.objects.all()

        if org_id:
            # Collect all user IDs that belong to this org (via OrgMembership or FPO/farmer link)
            from authapp.models.hierarchy import OrgMembership

            member_user_ids = OrgMembership.objects.filter(
                org_unit__organization_id=org_id
            ).values_list("app_user__user_id", flat=True)

            fpo_profile_ids = OrgUnitFPO.objects.filter(
                org_unit__organization_id=org_id
            ).values_list("fpo_profile_id", flat=True)

            fpo_user_ids = AppUser.objects.filter(
                fpo_profile__pk__in=fpo_profile_ids
            ).values_list("user_id", flat=True)

            all_user_ids = list(member_user_ids) + list(fpo_user_ids)
            qs = qs.filter(user_id__in=all_user_ids)

        platform_counts = qs.values("platform").annotate(total=Count("id"))
        by_platform = {row["platform"]: row["total"] for row in platform_counts}

        return api_response(
            success=True,
            message="Device token stats.",
            result={
                "total_tokens": qs.count(),
                "by_platform": by_platform,
            },
        )


class UserNotificationCoverageView(APIView):
    """
    GET /mgmt/notifications/coverage/

    Lists users who do NOT have any registered device token (no push channel).
    Useful for diagnosing delivery gaps.
    Scoped to an org with ?organization=<id>.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        org_id = request.query_params.get("organization")

        users_with_tokens = DeviceToken.objects.values_list("user_id", flat=True).distinct()

        qs = AppUser.objects.exclude(user_id__in=users_with_tokens).exclude(
            role=AppUser.Role.SUPER_ADMIN
        )

        if org_id:
            from authapp.models.hierarchy import OrgMembership

            org_app_user_ids = OrgMembership.objects.filter(
                org_unit__organization_id=org_id
            ).values_list("app_user_id", flat=True)
            qs = qs.filter(pk__in=org_app_user_ids)

        result = [
            {"user_id": u.pk, "username": u.user.username, "role": u.role}
            for u in qs.select_related("user")
        ]

        return api_response(
            success=True,
            message="Users without a registered device token.",
            result={"count": len(result), "users": result},
        )
