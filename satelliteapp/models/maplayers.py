from django.db import models


class SatelliteMapLayer(models.Model):
    order_farm = models.ForeignKey(
        "satelliteapp.OrderFarm",
        on_delete=models.CASCADE,
        related_name="map_layers",
    )
    observation_date = models.DateField()
    band_number = models.PositiveSmallIntegerField()
    layer_name = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, blank=True)
    png_url = models.TextField()
    bounds = models.JSONField(default=dict)          # {"north", "south", "east", "west"}
    legend = models.JSONField(default=list)          # [{"value": ..., "color": "#RRGGBB"}, ...]
    is_categorical = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order_farm", "observation_date", "band_number"],
                name="uniq_map_layer_per_field_date_band",
            )
        ]
        indexes = [
            models.Index(fields=["order_farm", "observation_date"]),
        ]