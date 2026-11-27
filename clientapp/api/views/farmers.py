from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from rest_framework import status

from authapp.api.responses import api_response
from authapp.api.response_codes import ResponseCode
from clientapp.api.views.base import ClientScopedAPIView
from farmerapp.api.serializers.lookups import CropTypeSerializer
from farmerapp.models import FarmCrop
from satelliteapp.models import SatelliteFarmAlert, SatelliteFarmNotification


class ClientFarmerFilterStateView(ClientScopedAPIView):
    """
    GET /client/farmers/filter-states/?observation_date=YYYY-MM-DD

    Same response shape as /fpo/farmers/filter-states/, over the client's
    scoped farmers. Alert/notification flags consider scoped farms only.
    """

    def get(self, request):
        observation_date, error = self.get_observation_date()
        if error:
            return error

        scoped_farm_ids = self.get_farms().values("pk")
        same_state = OuterRef("locality__state")

        alerts_subquery = SatelliteFarmAlert.objects.filter(
            order_farm__farm_id__in=scoped_farm_ids,
            order_farm__farm__farmer__farmer_profile__locality__state=same_state,
            observation_date=observation_date,
        )
        notifications_subquery = SatelliteFarmNotification.objects.filter(
            order_farm__farm_id__in=scoped_farm_ids,
            order_farm__farm__farmer__farmer_profile__locality__state=same_state,
            observation_date=observation_date,
        )

        states = (
            self.get_farmers()
            .filter(locality__state__isnull=False)
            .exclude(locality__state="")
            .values("locality__state")
            .annotate(
                farmers_count=Count("id"),
                has_alert=Exists(alerts_subquery),
                has_notification=Exists(notifications_subquery),
            )
            .order_by("locality__state")
        )

        return api_response(
            success=True,
            message="States with farmer counts and alerts.",
            code=ResponseCode.FILTER_STATES,
            result={"states": list(states)},
            status_code=status.HTTP_200_OK,
        )

class ClientFarmerDistrictListView(ClientScopedAPIView):
    """
    GET /client/farmers/states/<state>/districts/?observation_date=YYYY-MM-DD

    Same response shape as the FPO districts endpoint, over the client's
    scoped farmers. Alert/notification flags consider scoped farms only.
    """

    def get(self, request, state):
        observation_date, error = self.get_observation_date()
        if error:
            return error

        scoped_farm_ids = self.get_farms().values("pk")
        same_district = OuterRef("locality__district")

        alerts_subquery = SatelliteFarmAlert.objects.filter(
            order_farm__farm_id__in=scoped_farm_ids,
            order_farm__farm__farmer__farmer_profile__locality__state__iexact=state,
            order_farm__farm__farmer__farmer_profile__locality__district=same_district,
            observation_date=observation_date,
        )
        notifications_subquery = SatelliteFarmNotification.objects.filter(
            order_farm__farm_id__in=scoped_farm_ids,
            order_farm__farm__farmer__farmer_profile__locality__state__iexact=state,
            order_farm__farm__farmer__farmer_profile__locality__district=same_district,
            observation_date=observation_date,
        )

        districts = (
            self.get_farmers()
            .filter(locality__state__iexact=state, locality__district__isnull=False)
            .exclude(locality__district="")
            .values("locality__district")
            .annotate(
                farmers_count=Count("id"),
                has_alert=Exists(alerts_subquery),
                has_notification=Exists(notifications_subquery),
            )
            .order_by("locality__district")
        )

        return api_response(
            success=True,
            message=f"Districts in state '{state}'.",
            code=ResponseCode.DISTRICTS_IN_STATE,
            result={"districts": list(districts)},
            status_code=status.HTTP_200_OK,
        )

class ClientFarmerListByDistrictView(ClientScopedAPIView):
    """
    GET /client/farmers/states/<state>/districts/<district>/farmers/?observation_date=YYYY-MM-DD

    Same response shape as the FPO endpoint, over the client's scoped
    farmers. farms_count and alert/notification flags use scoped farms only.
    """

    def get(self, request, state, district):
        observation_date, error = self.get_observation_date()
        if error:
            return error

        scoped_farm_ids = self.get_farms().values("pk")

        alerts_subquery = SatelliteFarmAlert.objects.filter(
            order_farm__farm_id__in=scoped_farm_ids,
            order_farm__farm__farmer=OuterRef("app_user"),
            observation_date=observation_date,
        )
        notifications_subquery = SatelliteFarmNotification.objects.filter(
            order_farm__farm_id__in=scoped_farm_ids,
            order_farm__farm__farmer=OuterRef("app_user"),
            observation_date=observation_date,
        )

        farmers = (
            self.get_farmers()
            .filter(
                locality__state__iexact=state,
                locality__district__iexact=district,
            )
            .annotate(
                farms_count=Count(
                    "app_user__farms",
                    filter=Q(app_user__farms__pk__in=scoped_farm_ids),
                ),
                has_alert=Exists(alerts_subquery),
                has_notification=Exists(notifications_subquery),
            )
            .values("id", "farmer_name", "farms_count", "has_alert", "has_notification")
            .order_by("farmer_name")
        )

        return api_response(
            success=True,
            message=f"Farmers in '{district}', '{state}'",
            code=ResponseCode.FARMERS_IN_DISTRICT,
            result={"farmers": list(farmers)},
            status_code=status.HTTP_200_OK,
        )


class ClientFarmerFarmsListView(ClientScopedAPIView):
    """
    GET /client/farmers/<farmer_id>/farms/?observation_date=YYYY-MM-DD

    farmer_id is the FarmerProfile id (as returned by the district farmers
    list). Same response shape as the FPO endpoint, but only the farmer's
    scoped farms are listed. Out-of-scope farmer -> 404 FARMER_NOT_FOUND.
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
