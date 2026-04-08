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