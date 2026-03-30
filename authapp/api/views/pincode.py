from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from authapp.api.serializers import PincodeLookupResultSerializer
from authapp.services import PincodeLookupError, fetch_localities_by_pincode


class PincodeLookupView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pin_code):
        try:
            results = fetch_localities_by_pincode(pin_code)
        except PincodeLookupError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PincodeLookupResultSerializer(results)
        return Response(serializer.data, status=status.HTTP_200_OK)
