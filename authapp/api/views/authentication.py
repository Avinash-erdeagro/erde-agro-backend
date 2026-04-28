from rest_framework import status

from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from authapp.api.serializers import (
    FarmerFirebaseLoginSerializer,
    FarmerOTPCheckSerializer,
    FPOLoginSerializer,
    WebAppLoginSerializer,
)
from authapp.services import (
    AuthenticationError,
    check_farmer_otp_eligibility,
    login_farmer_with_firebase,
    login_fpo,
    login_webapp,
)

from ..responses import api_response
from .base import BaseAPIView


class FarmerFirebaseLoginView(BaseAPIView):
    authentication_classes = []
    permission_classes = []
    success_message = "Farmer login successful."

    def post(self, request):
        serializer = FarmerFirebaseLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = login_farmer_with_firebase(
                serializer.validated_data["id_token"]
            )
        except AuthenticationError as exc:
            return api_response(
                success=False,
                message=str(exc),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            success=True,
            message=self.success_message,
            result=result,
            status_code=status.HTTP_200_OK,
        )


class FPOLoginView(BaseAPIView):
    authentication_classes = []
    permission_classes = []
    success_message = "FPO login successful."

    def post(self, request):
        serializer = FPOLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = login_fpo(
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
            )
        except AuthenticationError as exc:
            return api_response(
                success=False,
                message=str(exc),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            success=True,
            message=self.success_message,
            result=result,
            status_code=status.HTTP_200_OK,
        )


class FarmerOTPCheckView(BaseAPIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = FarmerOTPCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = check_farmer_otp_eligibility(
                serializer.validated_data["phone_number"]
            )
        except AuthenticationError as exc:
            return api_response(
                success=False,
                message=str(exc),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if result["should_send_otp"]:
            message = "Farmer found. OTP can be sent."
        else:
            message = "Farmer account not found for this phone number."

        return api_response(
            success=True,
            message=message,
            result=result,
            status_code=status.HTTP_200_OK,
        )


class TokenRefreshApiView(BaseAPIView):
    authentication_classes = []
    permission_classes = []
    success_message = "Token refreshed successfully."

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)

        if not serializer.is_valid():
            return api_response(
                success=False,
                message="Invalid or expired refresh token.",
                result=None,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        result = {
            "access_token": serializer.validated_data["access"],
        }

        if "refresh" in serializer.validated_data:
            result["refresh_token"] = serializer.validated_data["refresh"]

        return api_response(
            success=True,
            message=self.success_message,
            result=result,
            status_code=status.HTTP_200_OK,
        )


# WebApp Login API
class WebAppLoginView(BaseAPIView):
    authentication_classes = []
    permission_classes = []
    success_message = "WebApp login successful."

    def post(self, request):
        serializer = WebAppLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = login_webapp(
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
            )
        except AuthenticationError as exc:
            return api_response(
                success=False,
                message=str(exc),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            success=True,
            message=self.success_message,
            result=result,
            status_code=status.HTTP_200_OK,
        )