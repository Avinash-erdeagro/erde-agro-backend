import math

from django.contrib.gis.db import models as gis_models
from django.db import models
from authapp.models import AppUser


class Farm(models.Model):
    farmer = models.ForeignKey(
        AppUser,
        on_delete=models.CASCADE,
        related_name="farms",
    )
    farm_name = models.CharField(max_length=100, default="")
    land_record_number = models.CharField(max_length=50)
    soil_type = models.ForeignKey(
        "farmerapp.SoilType",
        on_delete=models.PROTECT,
        related_name="farms",
    )
    irrigation_type = models.ForeignKey(
        "farmerapp.IrrigationType",
        on_delete=models.PROTECT,
        related_name="farms",
    )
    boundary = gis_models.PolygonField(srid=4326)  # GeoJSON polygon from React Native
    area = models.FloatField(
        help_text="Area in acres, calculated from boundary polygon.",
        default=0,
    )
    farm_document = models.FileField(
        upload_to="documents/farmer/farm/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Farm {self.land_record_number} – {self.farmer}"

    def save(self, *args, **kwargs):
        if self.boundary:
            R = 6378137

            def to_radians(degree):
                return degree * (math.pi / 180)

            coords = list(self.boundary.coords[0])
            area = 0
            num_points = len(coords)

            for i in range(num_points):
                x1 = coords[i][0]
                y1 = coords[i][1]
                x2 = coords[(i + 1) % num_points][0]
                y2 = coords[(i + 1) % num_points][1]

                area += to_radians(x1) * math.sin(to_radians(y2)) - to_radians(
                    x2
                ) * math.sin(to_radians(y1))

            area = abs((area * R * R) / 2.0)
            area_in_acres = area / 4046.8564224
            self.area = round(area_in_acres, 2)

        super().save(*args, **kwargs)