from django.db.models import Count, Exists, OuterRef, Prefetch
from rest_framework import status

from authapp.api.responses import api_response
from authapp.api.response_codes import ResponseCode
from farmerapp.api.serializers.lookups import CropTypeSerializer
from farmerapp.models import FarmCrop
from orgapp.api.views.base import OrgScopedAPIView
from satelliteapp.models import SatelliteFarmAlert, SatelliteFarmNotification


class OrgFpoFarmersListView(OrgScopedAPIView):
    """
    GET /org/fpos/<fpo_id>/farmers/?observation_date=YYYY-MM-DD

    Farmers of one in-scope FPO, with farms_count and alert/notification
    flags. Same farmer fields as the FPO dashboard's district farmers list.
    FPO outside the caller's subtree -> 404 FPO_NOT_FOUND.
    """

    def get(self, request, fpo_id):
        observation_date, error = self.get_observation_date()
        if error:
            return error

        fpo = self.get_fpos().filter(pk=fpo_id).first()
        if fpo is None:
            return api_response(
                success=False,
                message="FPO not found.",
                code=ResponseCode.FPO_NOT_FOUND,
                result=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        alerts_subquery = SatelliteFarmAlert.objects.filter(
            order_farm__farm__farmer=OuterRef("app_user"),
            observation_date=observation_date,
        )
        notifications_subquery = SatelliteFarmNotification.objects.filter(
            order_farm__farm__farmer=OuterRef("app_user"),
            observation_date=observation_date,
        )

        farmers = (
            self.get_farmers()
            .filter(registered_with_fpo=fpo)
            .annotate(
                farms_count=Count("app_user__farms"),
                has_alert=Exists(alerts_subquery),
                has_notification=Exists(notifications_subquery),
            )
            .values("id", "farmer_name", "farms_count", "has_alert", "has_notification")
            .order_by("farmer_name")
        )

        return api_response(
            success=True,
            message=f"Farmers of FPO '{fpo.fpo_name}'.",
            code=ResponseCode.FARMERS_FOUND,
            result={"farmers": list(farmers)},
            status_code=status.HTTP_200_OK,
        )


class OrgFarmerFarmsListView(OrgScopedAPIView):
    """
    GET /org/farmers/<farmer_id>/farms/?observation_date=YYYY-MM-DD

    farmer_id is the FarmerProfile id (as returned by the FPO farmers list).
    Same response shape as the FPO / client farms endpoints.
    Farmer outside the caller's subtree -> 404 FARMER_NOT_FOUND.
    """

    def get(self, request, farmer_id):
        observation_date, error = self.get_observation_date()
        if error:
            return error

        farmer = (
            self.get_farmers()
            .select_related("app_user")
            .filter(id=farmer_id)
            .first()
        )
        if farmer is None:
            return api_response(
                success=False,
                message="Farmer not found.",
                code=ResponseCode.FARMER_NOT_FOUND,
                result=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        farms = (
            self.get_farms()
            .filter(farmer=farmer.app_user)
            .prefetch_related(
                Prefetch(
                    "crops",
                    queryset=FarmCrop.objects.filter(is_active=True)
                    .select_related("primary_crop")
                    .order_by("-plantation_date"),
                    to_attr="active_crops",
                ),
            )
            .annotate(
                has_alert=Exists(
                    SatelliteFarmAlert.objects.filter(
                        order_farm__farm=OuterRef("pk"),
                        observation_date=observation_date,
                    )
                ),
                has_notification=Exists(
                    SatelliteFarmNotification.objects.filter(
                        order_farm__farm=OuterRef("pk"),
                        observation_date=observation_date,
                    )
                ),
            )
            .order_by("id")
        )

        farm_list = []
        for farm in farms:
            active_crop = None
            plantation_date = None
            if farm.active_crops:
                active = farm.active_crops[0]
                if active.primary_crop_id:
                    active_crop = CropTypeSerializer(
                        active.primary_crop, context={"request": request}
                    ).data
                else:
                    active_crop = {"id": None, "name": active.custom_primary_crop_name}
                plantation_date = active.plantation_date

            farm_list.append({
                "id": farm.id,
                "name": farm.farm_name,
                "area": farm.area,
                "active_crop": active_crop,
                "plantation_date": plantation_date,
                "has_alert": farm.has_alert,
                "has_notification": farm.has_notification,
            })

        return api_response(
            success=True,
            message=f"Farms for farmer id {farmer_id}.",
            code=ResponseCode.FARMS_FOR_FARMER,
            result={"farms": farm_list},
            status_code=status.HTTP_200_OK,
        )
