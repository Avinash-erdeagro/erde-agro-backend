from rest_framework import status

from authapp.api.serializers import PincodeLookupResultSerializer
from authapp.services import PincodeLookupError, fetch_localities_by_pincode
from ..responses import api_response
from ..response_codes import ResponseCode
from .base import BaseAPIView


class PincodeLookupView(BaseAPIView):
    authentication_classes = []
    permission_classes = []
    success_message = "Pincode details fetched successfully."

    def get(self, request, pin_code):
        try:
            results = fetch_localities_by_pincode(pin_code)
        except PincodeLookupError as exc:
            return api_response(
                success=False,
                message=str(exc), code=getattr(exc, "code", ResponseCode.ERROR),
                result=None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PincodeLookupResultSerializer(results)
        return api_response(
            success=True,
            message=self.success_message, code=getattr(self, "success_code", ResponseCode.SUCCESS),
            result=serializer.data,
            status_code=status.HTTP_200_OK,
        )
