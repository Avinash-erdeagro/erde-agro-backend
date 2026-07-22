from rest_framework import serializers

from authapp.models import AppUser


class PreferredLanguageSerializer(serializers.ModelSerializer):
    preferred_language_display = serializers.CharField(
        source="get_preferred_language_display", read_only=True
    )

    class Meta:
        model = AppUser
        fields = ["preferred_language", "preferred_language_display"]
