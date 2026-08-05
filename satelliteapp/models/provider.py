from django.db import models


class Company(models.Model):
    company_uuid = models.CharField(max_length=100, unique=True)
    company_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class OrderStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"


class Order(models.Model):
    company = models.ForeignKey(
        "satelliteapp.Company",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    irriwatch_order_uuid = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)


class OrderFarmStatus(models.TextChoices):
    PENDING = "PENDING", "Pending" 
    CREATED = "CREATED", "Created"
    SYNCING = "SYNCING", "Syncing"
    COMPLETED = "COMPLETED", "Completed"


class OrderFarm(models.Model):
    order = models.ForeignKey(
        "satelliteapp.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_farms",
    )
    farm = models.ForeignKey(
        "farmerapp.Farm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_farms",
    )
    irriwatch_field_uuid = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=OrderFarmStatus.choices,
        default=OrderFarmStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)


class SatelliteResult(models.Model):
    order_farm = models.ForeignKey(
        "satelliteapp.OrderFarm",
        on_delete=models.CASCADE,
        related_name="results",
    )
    observation_date = models.DateField()
    data_json = models.JSONField(null=True, blank=True)
    tiff_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["order_farm", "observation_date"]),
        ]

