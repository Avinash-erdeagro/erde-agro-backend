from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from authapp.api.views.base import FormattedResponseMixin
from farmerapp.models import Farm, FarmCrop
from farmerapp.api.serializers import FarmSerializer, FarmCropSerializer


class FarmViewSet(FormattedResponseMixin, ModelViewSet):
    serializer_class = FarmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        app_user = user.appuser
        qs = Farm.objects.select_related(
            "farmer", "soil_type", "irrigation_type"
        ).prefetch_related("crops", "crops__primary_crop", "crops__intercrop")
        if app_user.role == "FARMER":
            qs = qs.filter(farmer=app_user)
        elif app_user.role == "FPO":
            qs = qs.filter(farmer__farmer_profile__registered_with_fpo=app_user.fpo_profile)
        return qs


class FarmCropViewSet(FormattedResponseMixin, ModelViewSet):
    serializer_class = FarmCropSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        app_user = self.request.user.appuser
        qs = FarmCrop.objects.select_related("farm", "primary_crop", "intercrop")

        if app_user.role == "FARMER":
            qs = qs.filter(farm__farmer=app_user)
        elif app_user.role == "FPO":
            qs = qs.filter(
                farm__farmer__farmer_profile__registered_with_fpo=app_user.fpo_profile
            )

        farm_id = self.request.query_params.get("farm")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)

        return qs