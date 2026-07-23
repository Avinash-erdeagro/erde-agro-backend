from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authapp.api.responses import api_response
from authapp.models import AppUser
from ..serializers import PreferredLanguageSerializer
from .base import BaseAPIView


class PreferredLanguageView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get_app_user(self, request):
        app_user = AppUser.objects.filter(user=request.user).first()
        if not app_user:
            return None, api_response(
                success=False,
                message="App user not found.",
                result=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return app_user, None

    def patch(self, request):
        app_user, error = self.get_app_user(request)
        if error:
            return error
        serializer = PreferredLanguageSerializer(app_user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(
            success=True,
            message="Preferred language updated successfully.",
            result=serializer.data,
            status_code=status.HTTP_200_OK,
        )
