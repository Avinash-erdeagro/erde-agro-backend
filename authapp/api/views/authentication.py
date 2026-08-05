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
from ..response_codes import ResponseCode
from .base import BaseAPIView


class FarmerFirebaseLoginView(BaseAPIView):
    authentication_classes = []
    permission_classes = []
    success_message = "Farmer login successful."
    success_code = ResponseCode.LOGIN_SUCCESS

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
                message=str(exc), code=getattr(exc, "code", ResponseCode.AUTH_ERROR),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            success=True,
            message=self.success_message, code=self.success_code,
            result=result,
            status_code=status.HTTP_200_OK,
        )


class FPOLoginView(BaseAPIView):
    authentication_classes = []
    permission_classes = []
    success_message = "FPO login successful."
    success_code = ResponseCode.LOGIN_SUCCESS

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
                message=str(exc), code=getattr(exc, "code", ResponseCode.AUTH_ERROR),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            success=True,
            message=self.success_message, code=self.success_code,
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
                message=str(exc), code=getattr(exc, "code", ResponseCode.AUTH_ERROR),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if result["should_send_otp"]:
            message = "Farmer found. OTP can be sent."
            code = ResponseCode.OTP_ELIGIBLE
        else:
            message = "Farmer account not found for this phone number."
            code = ResponseCode.FARMER_NOT_FOUND_FOR_PHONE

        return api_response(
            success=True,
            message=message,
            code=code,
            result=result,
            status_code=status.HTTP_200_OK,
        )


class TokenRefreshApiView(BaseAPIView):
    authentication_classes = []
    permission_classes = []
    success_message = "Token refreshed successfully."
    success_code = ResponseCode.TOKEN_REFRESHED

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)

        if not serializer.is_valid():
            return api_response(
                success=False,
                message="Invalid or expired refresh token.", code=ResponseCode.INVALID_REFRESH_TOKEN,
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
            message=self.success_message, code=self.success_code,
            result=result,
            status_code=status.HTTP_200_OK,
        )


# WebApp Login API
class WebAppLoginView(BaseAPIView):
    authentication_classes = []
    permission_classes = []
    success_message = "WebApp login successful."
    success_code = ResponseCode.LOGIN_SUCCESS

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
                message=str(exc), code=getattr(exc, "code", ResponseCode.AUTH_ERROR),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            success=True,
            message=self.success_message, code=self.success_code,
            result=result,
            status_code=status.HTTP_200_OK,
        )