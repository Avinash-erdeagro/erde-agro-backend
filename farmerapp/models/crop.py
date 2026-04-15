from django.db import models


class FarmCrop(models.Model):
    farm = models.ForeignKey(
        "farmerapp.Farm",
        on_delete=models.CASCADE,
        related_name="crops",
    )
    primary_crop = models.ForeignKey(
        "farmerapp.CropType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="farm_crops",
    )
    custom_primary_crop_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Custom crop name when not in the CropType list.",
    )
    primary_crop_variety = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )
    intercrop = models.ForeignKey(
        "farmerapp.CropType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intercrop_farm_crops",
        help_text="Optional second crop grown alongside the primary crop (intercropping).",
    )
    custom_intercrop_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Custom intercrop name when not in the CropType list.",
    )
    intercrop_variety = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )
    plantation_date = models.DateField()
    is_active = models.BooleanField(default=True)  # current standing crop
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-plantation_date"]

    @property
    def primary_crop_name(self):
        if self.primary_crop_id:
            return self.primary_crop.name
        return self.custom_primary_crop_name

    @property
    def intercrop_name(self):
        if self.intercrop_id:
            return self.intercrop.name
        return self.custom_intercrop_name or None

    def __str__(self):
        label = self.primary_crop_name
        intercrop = self.intercrop_name
        if intercrop:
            label = f"{label} + {intercrop}"
        return f"{label} on Farm {self.farm.land_record_number}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.is_active:
            # Deactivate all other crops on the same farm.
            FarmCrop.objects.filter(farm=self.farm).exclude(pk=self.pk).update(
                is_active=False
            )