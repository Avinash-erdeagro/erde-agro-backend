from django.db import models


class FarmCrop(models.Model):
    farm = models.ForeignKey(
        "farmerapp.Farm",
        on_delete=models.CASCADE,
        related_name="crops",
    )
    crop_type = models.ForeignKey(
        "farmerapp.CropType",
        on_delete=models.PROTECT,
        related_name="farm_crops",
    )
    plantation_date = models.DateField()
    is_active = models.BooleanField(default=True)  # current standing crop
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-plantation_date"]

    def __str__(self):
        return f"{self.crop_type.name} on Farm {self.farm.gat_number}"