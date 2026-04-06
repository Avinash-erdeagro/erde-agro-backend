from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from authapp.api.views.base import BaseAPIView
from contentapp.models import FeaturedVideo, TutorialVideo

from ..serializers import FeaturedVideoSerializer, TutorialVideoSerializer
from .base import BaseReadOnlyModelViewSet


class FeaturedVideoViewSet(BaseReadOnlyModelViewSet):
    queryset = FeaturedVideo.objects.all()
    serializer_class = FeaturedVideoSerializer
    permission_classes = [IsAuthenticated]
    action_success_messages = {
        "list": "Featured videos fetched successfully.",
        "retrieve": "Featured video fetched successfully.",
    }


class TutorialVideoViewSet(BaseReadOnlyModelViewSet):
    queryset = TutorialVideo.objects.all()
    serializer_class = TutorialVideoSerializer
    permission_classes = [IsAuthenticated]
    action_success_messages = {
        "list": "Tutorial videos fetched successfully.",
        "retrieve": "Tutorial video fetched successfully.",
    }

class DashboardAllVideoView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    success_message = "Videos fetched successfully."

    def get(self, request):
        featured = FeaturedVideo.objects.all()
        tutorials = TutorialVideo.objects.all()

        return Response({
            "featured": FeaturedVideoSerializer(featured, many=True, context={"request": request}).data,
            "tutorials": TutorialVideoSerializer(tutorials, many=True, context={"request": request}).data,
        })