from django.db import models


TRANSLATION_FIELDS = [
    ("name_hi", "Hindi"),
    ("name_mr", "Marathi"),
    ("name_gu", "Gujarati"),
    ("name_pa", "Punjabi"),
    ("name_bn", "Bangla"),
    ("name_kn", "Kannada"),
    ("name_te", "Telugu"),
    ("name_ta", "Tamil"),
]


class SoilType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    irriwatch_id = models.IntegerField(unique=True, null=True, blank=True)
    name_hi = models.CharField(max_length=150, blank=True, default="")
    name_mr = models.CharField(max_length=150, blank=True, default="")
    name_gu = models.CharField(max_length=150, blank=True, default="")
    name_pa = models.CharField(max_length=150, blank=True, default="")
    name_bn = models.CharField(max_length=150, blank=True, default="")
    name_kn = models.CharField(max_length=150, blank=True, default="")
    name_te = models.CharField(max_length=150, blank=True, default="")
    name_ta = models.CharField(max_length=150, blank=True, default="")

    def __str__(self):
        return self.name


class IrrigationType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    irriwatch_id = models.IntegerField(unique=True, null=True, blank=True)
    name_hi = models.CharField(max_length=150, blank=True, default="")
    name_mr = models.CharField(max_length=150, blank=True, default="")
    name_gu = models.CharField(max_length=150, blank=True, default="")
    name_pa = models.CharField(max_length=150, blank=True, default="")
    name_bn = models.CharField(max_length=150, blank=True, default="")
    name_kn = models.CharField(max_length=150, blank=True, default="")
    name_te = models.CharField(max_length=150, blank=True, default="")
    name_ta = models.CharField(max_length=150, blank=True, default="")

    def __str__(self):
        return self.name


class CropType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    irriwatch_id = models.IntegerField(unique=True, null=True, blank=True)
    name_hi = models.CharField(max_length=150, blank=True, default="")
    name_mr = models.CharField(max_length=150, blank=True, default="")
    name_gu = models.CharField(max_length=150, blank=True, default="")
    name_pa = models.CharField(max_length=150, blank=True, default="")
    name_bn = models.CharField(max_length=150, blank=True, default="")
    name_kn = models.CharField(max_length=150, blank=True, default="")
    name_te = models.CharField(max_length=150, blank=True, default="")
    name_ta = models.CharField(max_length=150, blank=True, default="")

    def __str__(self):
        return self.name