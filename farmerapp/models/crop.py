from django.db import models


class FarmCrop(models.Model):
    farm = models.ForeignKey(
        "farmerapp.Farm",
        on_delete=models.CASCADE,
        related_name="crops",
    )
    primary_crop = models.ForeignKey(
        "farmerapp.CropType",
        on_delete=models.PROTECT,
        related_name="farm_crops",
    )
    intercrop = models.ForeignKey(
        "farmerapp.CropType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intercrop_farm_crops",
        help_text="Optional second crop grown alongside the primary crop (intercropping).",
    )
    plantation_date = models.DateField()
    is_active = models.BooleanField(default=True)  # current standing crop
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-plantation_date"]

    def __str__(self):
        label = self.primary_crop.name
        if self.intercrop_id:
            label = f"{label} + {self.intercrop.name}"
        return f"{label} on Farm {self.farm.land_record_number}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.is_active:
            # If this crop has the newest plantation date on the farm,
            # deactivate all other crops on the same farm.
            newest_date = (
                FarmCrop.objects.filter(farm=self.farm)
                .order_by("-plantation_date")
                .values_list("plantation_date", flat=True)
                .first()
            )
            if self.plantation_date >= newest_date:
                FarmCrop.objects.filter(farm=self.farm).exclude(pk=self.pk).update(
                    is_active=False
                )