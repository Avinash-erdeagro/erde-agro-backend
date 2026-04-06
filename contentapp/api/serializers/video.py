from rest_framework import serializers

from contentapp.models import FeaturedVideo, TutorialVideo


class FeaturedVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturedVideo
        fields = [
            "id",
            "youtube_url",
            "thumbnail",
            "created_at",
        ]


class TutorialVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorialVideo
        fields = [
            "id",
            "title",
            "description",
            "youtube_url",
            "thumbnail",
            "created_at",
        ]