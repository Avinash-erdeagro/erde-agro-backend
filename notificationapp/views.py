from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from authapp.api.responses import api_response
from .models import DeviceToken
from .serializers import DeviceTokenRegisterSerializer, DeviceTokenUnregisterSerializer


class DeviceTokenRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        platform = serializer.validated_data["platform"]

        DeviceToken.objects.update_or_create(
            token=token,
            defaults={"user": request.user, "platform": platform},
        )

        return api_response(
            success=True,
            message="Device token registered successfully.",
            status_code=status.HTTP_200_OK,
        )


class DeviceTokenUnregisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenUnregisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]

        deleted_count, _ = DeviceToken.objects.filter(
            token=token, user=request.user
        ).delete()

        if deleted_count == 0:
            return api_response(
                success=False,
                message="Device token not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return api_response(
            success=True,
            message="Device token unregistered successfully.",
            status_code=status.HTTP_200_OK,
        )
