from django.contrib.gis.db import models as gis_models
from django.db import models
from authapp.models import AppUser


class Farm(models.Model):
    # instead lets have the foreign key to app_user
    # what happends when a soil_type is deleted - we should not allow deletion if there are farms using it, so PROTECT is a good option

    farmer = models.ForeignKey(
        AppUser,
        on_delete=models.CASCADE,
        related_name="farms",
    )
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
    farm_document = models.FileField(
        upload_to="documents/farmer/farm/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Farm {self.land_record_number} – {self.farmer}"