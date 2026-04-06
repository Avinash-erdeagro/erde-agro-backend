from django.contrib import admin

from content.models import FeaturedVideo, TutorialVideo


@admin.register(FeaturedVideo)
class FeaturedVideoAdmin(admin.ModelAdmin):
    list_display = ("youtube_url", "created_at")


@admin.register(TutorialVideo)
class TutorialVideoAdmin(admin.ModelAdmin):
    list_display = ("title", "youtube_url", "created_at")