from django.db import models


class FeaturedVideo(models.Model):
    youtube_url = models.URLField()
    thumbnail = models.ImageField(upload_to="featured-section/video/thumbnails/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.youtube_url


class TutorialVideo(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    youtube_url = models.URLField()
    thumbnail = models.ImageField(upload_to="tutorial-section/video/tutorials/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title