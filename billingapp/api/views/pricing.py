import math
from decimal import Decimal

from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authapp.api.responses import api_response
from authapp.api.views.base import BaseAPIView
from billingapp.api.serializers import SatellitePricingRequestSerializer
from billingapp.models import SatellitePlan
from farmerapp.models import Farm


class SatellitePricingView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def _get_accessible_farms(self, app_user):
        queryset = Farm.objects.select_related(
            "farmer", "soil_type", "irrigation_type"
        ).prefetch_related("crops", "crops__crop_type")

        if app_user.role == "FARMER":
            return queryset.filter(farmer=app_user)

        if app_user.role == "FPO":
            return queryset.filter(
                farmer__farmer_profile__registered_with_fpo=app_user.fpo_profile
            )

        return queryset.none()

    def post(self, request):
        app_user = request.user.appuser
        serializer = SatellitePricingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        farm_ids = serializer.validated_data["farm_ids"]

        if app_user.role == "FARMER" and len(farm_ids) != 1:
            return api_response(
                success=False,
                message="Farmers can request pricing for only one farm at a time.",
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        accessible_farms = {
            farm.id: farm
            for farm in self._get_accessible_farms(app_user).filter(id__in=farm_ids)
        }

        missing_farm_ids = [
            farm_id for farm_id in farm_ids if farm_id not in accessible_farms
        ]
        if missing_farm_ids:
            return api_response(
                success=False,
                message=f"Invalid or inaccessible farm IDs: {missing_farm_ids}",
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        plans = list(SatellitePlan.objects.filter(is_active=True))
        if not plans:
            return api_response(
                success=False,
                message="No active satellite plans are configured.",
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        farm_results = []

        plan_totals = {
            plan.id: {
                "plan_id": plan.id,
                "name": plan.name,
                "duration_days": plan.duration_days,
                "duration_months": plan.duration_months,
                "total_amount": Decimal("0.00"),
                "total_commission": Decimal("0.00"),
            }
            for plan in plans
        }

        for farm_id in farm_ids:
            farm = accessible_farms[farm_id]
            chargeable_area = math.ceil(farm.area or 0)
            active_crop = next(
                (crop for crop in farm.crops.all() if crop.is_active),
                None,
            )
            if active_crop is None:
                active_crop = next(iter(farm.crops.all()), None)

            farm_plans = []
            for plan in plans:
                total_amount = Decimal(chargeable_area) * plan.total_price_per_acre
                total_commission = (
                    Decimal(chargeable_area) * plan.total_commission_per_acre
                )

                farm_plans.append(
                    {
                        "plan_id": plan.id,
                        "name": plan.name,
                        "duration_days": plan.duration_days,
                        "duration_months": plan.duration_months,
                        "price_per_acre": float(plan.total_price_per_acre),
                        "total_amount": float(total_amount),
                    }
                )

                plan_totals[plan.id]["total_amount"] += total_amount
                plan_totals[plan.id]["total_commission"] += total_commission

            farm_results.append(
                {
                    "farm_id": farm.id,
                    "farm_name": farm.farm_name,
                    "area": farm.area,
                    "chargeable_area": chargeable_area,
                    "crop_name": active_crop.crop_type.name if active_crop else None,
                    "plans": farm_plans,
                }
            )

        total_amount = []
        for plan in plans:
            summary = plan_totals[plan.id]
            total_amount.append(
                {
                    "plan_id": summary["plan_id"],
                    "name": summary["name"],
                    "duration_days": summary["duration_days"],
                    "duration_months": summary["duration_months"],
                    "price_per_acre": float(plan.total_price_per_acre),
                    "total_amount": float(summary["total_amount"]),
                    "commission_percent": float(plan.commission_percent),
                    "commission_per_acre": float(plan.total_commission_per_acre),
                    "total_commission": float(summary["total_commission"]),
                }
            )

        if app_user.role == "FARMER":
            result = {
                "farms": farm_results,
            }
        else:
            result = {
                "total_amount": total_amount,
            }

        return api_response(
            success=True,
            message="Satellite plan pricing fetched successfully.",
            result=result,
            status_code=status.HTTP_200_OK,
        )
