from rest_framework import serializers
from farmerapp.models import SoilType, IrrigationType, CropType


class LocalizedNameMixin:
    """Collapse the per-language name columns into a single localized ``name``.

    English (the default) keeps the base ``name``; other languages read the
    matching ``name_<lang>`` column, falling back to English when that column is
    empty. The raw ``name_xx`` columns are never sent to the client.

    Reads the language from ``request.language_code`` (set by
    PreferredLanguageMiddleware). When there is no request in context the base
    English ``name`` is returned.
    """

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get("request")
        language_code = getattr(request, "language_code", None)
        if language_code and language_code != "en":
            translated = getattr(instance, f"name_{language_code}", "")
            if translated:
                rep["name"] = translated
        return rep


class SoilTypeSerializer(LocalizedNameMixin, serializers.ModelSerializer):
    class Meta:
        model = SoilType
        fields = ["id", "name"]


class IrrigationTypeSerializer(LocalizedNameMixin, serializers.ModelSerializer):
    class Meta:
        model = IrrigationType
        fields = ["id", "name"]


class CropTypeSerializer(LocalizedNameMixin, serializers.ModelSerializer):
    class Meta:
        model = CropType
        fields = ["id", "name"]
