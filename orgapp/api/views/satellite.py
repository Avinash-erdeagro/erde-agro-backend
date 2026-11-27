import json

from django.contrib.gis.db.models.functions import Centroid
from django.db.models import Prefetch
from rest_framework import status

from authapp.api.responses import api_response
from authapp.api.response_codes import ResponseCode
from farmerapp.models import FarmCrop
from fpoapp.utils import localized_lookup_name
from orgapp.api.views.base import OrgScopedAPIView


class OrgFarmBoundariesView(OrgScopedAPIView):
    """
    GET /org/farms/geojson/[?org_unit=][&fpo=][&farmer=]

    The caller's scoped farms in the sidebar selection, as a GeoJSON
    FeatureCollection. Same shape as /fpo/farms/geojson/. Boundaries don't
    change with the date, so no observation_date is taken.
    """

    def get(self, request):
        farms, error = self.filter_farms_by_selection(self.get_farms())
        if error:
            return error

        farms = (
            farms.filter(boundary__isnull=False)
            .select_related("farmer__farmer_profile", "soil_type", "irrigation_type")
            .annotate(centroid=Centroid("boundary"))
            .prefetch_related(
                Prefetch(
                    "crops",
                    queryset=FarmCrop.objects.filter(is_active=True).select_related("primary_crop"),
                    to_attr="active_crops",
                )
            )
            .order_by("id")
        )

        language_code = getattr(request, "language_code", None)
        features = []
        for farm in farms:
            farmer_profile = farm.farmer.farmer_profile
            crop = next(iter(farm.active_crops), None)
            features.append(
                {
                    "type": "Feature",
                    "id": farm.id,
                    "geometry": json.loads(farm.boundary.geojson),
                    "properties": {
                        "farm_id": farm.id,
                        "farm_name": farm.farm_name,
                        "farmer_id": farmer_profile.id,
                        "farmer_name": farmer_profile.farmer_name,
                        "area": farm.area,
                        "crop_name": crop.primary_crop_localized_name(language_code) if crop else None,
                        "plantation_date": crop.plantation_date.isoformat() if crop and crop.plantation_date else None,
                        "irrigation_type": localized_lookup_name(farm.irrigation_type, language_code),
                        "soil_type": localized_lookup_name(farm.soil_type, language_code),
                        # [lng, lat] — GeoJSON order, ready for a pin layer.
                        "centroid": [farm.centroid.x, farm.centroid.y] if farm.centroid else None,
                    },
                }
            )

        return api_response(
            success=True,
            message="Organization farm boundaries fetched successfully.",
            code=ResponseCode.ORG_FARM_BOUNDARIES_FETCHED,
            result={"type": "FeatureCollection", "features": features},
            status_code=status.HTTP_200_OK,
        )
