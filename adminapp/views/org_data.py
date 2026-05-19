"""
Hierarchy-scoped FPO and Farmer data views.

All views here are available to both SUPER_ADMIN and ORG_USER.
Querysets are automatically filtered to the caller's position in the hierarchy:
  - SUPER_ADMIN  → all FPOs / all farmers across every org
  - ORG_USER     → only FPOs linked to units in their subtree, and the
                   farmers registered under those FPOs
"""

from rest_framework.views import APIView

from authapp.api.permissions import IsSuperAdminOrOrgUser
from authapp.api.responses import api_response
from authapp.api.serializers.profiles import FarmerProfileSerializer, FpoProfileSerializer
from authapp.models.hierarchy import OrgUnitFPO
from authapp.services.hierarchy import (
    get_accessible_fpo_profiles,
    get_accessible_farmer_profiles,
    get_accessible_org_units,
)


class HierarchyFPOListView(APIView):
    """
    GET /super-admin/org-data/fpos/

    Returns all FPO profiles visible to the caller based on their hierarchy
    position. Includes which org unit each FPO is linked to.

    Query params:
      - org_unit=<id>   Filter to FPOs under a specific unit (must be in
                        the caller's accessible subtree).
    """
    permission_classes = [IsSuperAdminOrOrgUser]

    def get(self, request):
        app_user = request.user.appuser
        fpo_qs = get_accessible_fpo_profiles(app_user).select_related(
            "locality", "app_user", "app_user__user"
        ).prefetch_related("org_unit_link__org_unit")

        # Optional: narrow to a specific org unit within the accessible subtree
        org_unit_id = request.query_params.get("org_unit")
        if org_unit_id:
            accessible_unit_ids = get_accessible_org_units(app_user).values_list(
                "pk", flat=True
            )
            if int(org_unit_id) not in list(accessible_unit_ids):
                return api_response(
                    success=False,
                    message="Org unit not found or not accessible.",
                    result=None,
                    status_code=403,
                )
            fpo_ids_in_unit = OrgUnitFPO.objects.filter(
                org_unit_id=org_unit_id
            ).values_list("fpo_profile_id", flat=True)
            fpo_qs = fpo_qs.filter(pk__in=fpo_ids_in_unit)

        result = []
        for fpo in fpo_qs:
            # Get the org unit this FPO is linked to (if any)
            link = getattr(fpo, "org_unit_link", None)
            result.append({
                "id": fpo.pk,
                "fpo_name": fpo.fpo_name,
                "contact_person_name": fpo.contact_person_name,
                "email": fpo.email,
                "mobile": fpo.mobile,
                "locality": {
                    "district": fpo.locality.district if fpo.locality else None,
                    "state": fpo.locality.state if fpo.locality else None,
                } if fpo.locality else None,
                "org_unit_id": link.org_unit_id if link else None,
                "org_unit_name": link.org_unit.name if link else None,
                "farmer_count": fpo.registered_farmers.count(),
            })

        return api_response(
            success=True,
            message=f"{len(result)} FPO(s) found.",
            result=result,
        )


class HierarchyFarmerListView(APIView):
    """
    GET /super-admin/org-data/farmers/

    Returns all farmers visible to the caller based on their hierarchy position.

    Query params:
      - fpo=<id>        Filter to farmers under a specific FPO (must be
                        accessible to the caller).
      - org_unit=<id>   Filter to farmers under all FPOs in a specific org unit.
    """
    permission_classes = [IsSuperAdminOrOrgUser]

    def get(self, request):
        app_user = request.user.appuser
        farmer_qs = get_accessible_farmer_profiles(app_user).select_related(
            "app_user",
            "app_user__user",
            "locality",
            "registered_with_fpo",
        )

        # Optional: narrow to a specific FPO
        fpo_id = request.query_params.get("fpo")
        if fpo_id:
            accessible_fpo_ids = get_accessible_fpo_profiles(app_user).values_list(
                "pk", flat=True
            )
            if int(fpo_id) not in list(accessible_fpo_ids):
                return api_response(
                    success=False,
                    message="FPO not found or not accessible.",
                    result=None,
                    status_code=403,
                )
            farmer_qs = farmer_qs.filter(registered_with_fpo_id=fpo_id)

        # Optional: narrow to a specific org unit
        org_unit_id = request.query_params.get("org_unit")
        if org_unit_id:
            accessible_unit_ids = get_accessible_org_units(app_user).values_list(
                "pk", flat=True
            )
            if int(org_unit_id) not in list(accessible_unit_ids):
                return api_response(
                    success=False,
                    message="Org unit not found or not accessible.",
                    result=None,
                    status_code=403,
                )
            fpo_ids_in_unit = OrgUnitFPO.objects.filter(
                org_unit_id=org_unit_id
            ).values_list("fpo_profile_id", flat=True)
            farmer_qs = farmer_qs.filter(registered_with_fpo_id__in=fpo_ids_in_unit)

        result = []
        for farmer in farmer_qs:
            fpo = farmer.registered_with_fpo
            result.append({
                "id": farmer.pk,
                "farmer_name": farmer.farmer_name,
                "contact_number": farmer.contact_number,
                "locality": {
                    "district": farmer.locality.district if farmer.locality else None,
                    "state": farmer.locality.state if farmer.locality else None,
                } if farmer.locality else None,
                "fpo_id": fpo.pk if fpo else None,
                "fpo_name": fpo.fpo_name if fpo else None,
            })

        return api_response(
            success=True,
            message=f"{len(result)} farmer(s) found.",
            result=result,
        )


class HierarchyFarmerDetailView(APIView):
    """
    GET /super-admin/org-data/farmers/<id>/

    Returns full details of a single farmer, accessible only if the farmer
    is within the caller's hierarchy scope.
    """
    permission_classes = [IsSuperAdminOrOrgUser]

    def get(self, request, pk):
        app_user = request.user.appuser
        accessible_farmers = get_accessible_farmer_profiles(app_user)
        farmer = accessible_farmers.filter(pk=pk).select_related(
            "app_user", "app_user__user", "locality", "registered_with_fpo"
        ).first()

        if not farmer:
            return api_response(
                success=False,
                message="Farmer not found or not accessible.",
                result=None,
                status_code=404,
            )

        fpo = farmer.registered_with_fpo
        return api_response(
            success=True,
            message="Farmer details fetched.",
            result={
                "id": farmer.pk,
                "farmer_name": farmer.farmer_name,
                "contact_number": farmer.contact_number,
                "aadhaar_number": farmer.aadhaar_number,
                "locality": {
                    "district": farmer.locality.district if farmer.locality else None,
                    "state": farmer.locality.state if farmer.locality else None,
                    "pin_code": farmer.locality.pin_code if farmer.locality else None,
                } if farmer.locality else None,
                "fpo_id": fpo.pk if fpo else None,
                "fpo_name": fpo.fpo_name if fpo else None,
            },
        )


class HierarchyFPODetailView(APIView):
    """
    GET /super-admin/org-data/fpos/<id>/

    Returns full details of a single FPO, accessible only if it is within
    the caller's hierarchy scope.
    """
    permission_classes = [IsSuperAdminOrOrgUser]

    def get(self, request, pk):
        app_user = request.user.appuser
        accessible_fpos = get_accessible_fpo_profiles(app_user)
        fpo = accessible_fpos.filter(pk=pk).select_related(
            "locality", "app_user", "app_user__user"
        ).prefetch_related("org_unit_link__org_unit").first()

        if not fpo:
            return api_response(
                success=False,
                message="FPO not found or not accessible.",
                result=None,
                status_code=404,
            )

        link = getattr(fpo, "org_unit_link", None)
        return api_response(
            success=True,
            message="FPO details fetched.",
            result={
                "id": fpo.pk,
                "fpo_name": fpo.fpo_name,
                "contact_person_name": fpo.contact_person_name,
                "email": fpo.email,
                "mobile": fpo.mobile,
                "gst_number": fpo.gst_number,
                "pan_number": fpo.pan_number,
                "cin_number": fpo.cin_number,
                "locality": {
                    "district": fpo.locality.district if fpo.locality else None,
                    "state": fpo.locality.state if fpo.locality else None,
                    "pin_code": fpo.locality.pin_code if fpo.locality else None,
                } if fpo.locality else None,
                "org_unit_id": link.org_unit_id if link else None,
                "org_unit_name": link.org_unit.name if link else None,
                "farmer_count": fpo.registered_farmers.count(),
            },
        )
