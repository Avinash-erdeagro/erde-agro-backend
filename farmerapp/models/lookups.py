from django.db import models

# lets remove the name_mr thing and add something called irriwatch_id as we are referencing from there

class SoilType(models.Model):
    name = models.CharField(max_length=100, unique=True)       
    irriwatch_id = models.IntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.name


class IrrigationType(models.Model):
    name = models.CharField(max_length=100, unique=True)      
    irriwatch_id = models.IntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.name


class CropType(models.Model):
    name = models.CharField(max_length=100, unique=True)       
    irriwatch_id = models.IntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.name