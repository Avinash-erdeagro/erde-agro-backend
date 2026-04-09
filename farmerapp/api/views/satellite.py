from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authapp.api.responses import api_response
from authapp.api.views.base import BaseAPIView
from farmerapp.models import Farm, SatelliteSubscriptionStatus
from farmerapp.services import SatelliteServiceError, fetch_satellite_results_by_external_id


class FarmSatelliteResultsView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        app_user = user.appuser
        queryset = Farm.objects.select_related(
            "farmer", "soil_type", "irrigation_type"
        ).prefetch_related("crops", "crops__crop_type")

        if app_user.role == "FARMER":
            queryset = queryset.filter(farmer=app_user)
        elif app_user.role == "FPO":
            queryset = queryset.filter(
                farmer__farmer_profile__registered_with_fpo=app_user.fpo_profile
            )

        return queryset

    def get(self, request, farm_id):
        farm = get_object_or_404(self.get_queryset(), pk=farm_id)
        subscription = farm.satellite_subscriptions.order_by("-created_at").first()

        if not subscription:
            return api_response(
                success=False,
                message="You are not subscribed to satellite services for this farm",
                result=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if subscription.status == SatelliteSubscriptionStatus.PAID:
            return api_response(
                success=False,
                message="You will receive satellite data within 7 working days. Please check back later",
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            satellite_data = fetch_satellite_results_by_external_id(farm.id)
        except SatelliteServiceError as exc:
            return api_response(
                success=False,
                message=str(exc),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            success=True,
            message="Satellite data fetched successfully.",
            result={
                "farm_id": farm.id,
                "subscription": {
                    "id": subscription.id,
                    "status": subscription.status,
                    "subscription_start": subscription.subscription_start,
                    "subscription_end": subscription.subscription_end,
                    "irriwatch_order_uuid": subscription.irriwatch_order_uuid,
                    "irriwatch_field_uuid": subscription.irriwatch_field_uuid,
                },
                "satellite_data": satellite_data,
            },
            status_code=status.HTTP_200_OK,
        )
