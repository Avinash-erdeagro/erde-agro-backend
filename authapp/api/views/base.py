from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics, viewsets

from authapp.api.response_codes import ResponseCode


class FormattedResponseMixin:
    success_message = "Request successful."
    success_code = ResponseCode.SUCCESS
    action_success_messages = {
        "list": "Data fetched successfully.",
        "retrieve": "Data fetched successfully.",
        "create": "Created successfully.",
        "update": "Updated successfully.",
        "partial_update": "Updated successfully.",
        "destroy": "Deleted successfully.",
    }
    action_success_codes = {
        "list": ResponseCode.DATA_FETCHED,
        "retrieve": ResponseCode.DATA_FETCHED,
        "create": ResponseCode.CREATED,
        "update": ResponseCode.UPDATED,
        "partial_update": ResponseCode.UPDATED,
        "destroy": ResponseCode.DELETED,
    }

    def get_success_message(self):
        action = getattr(self, "action", None)
        if action:
            return self.action_success_messages.get(action, self.success_message)
        return self.success_message

    def get_success_code(self):
        action = getattr(self, "action", None)
        if action:
            return self.action_success_codes.get(action, self.success_code)
        return self.success_code

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if not isinstance(response, Response):
            return response

        if not (200 <= response.status_code < 300):
            return response

        if isinstance(response.data, dict) and {
            "success",
            "message",
            "result",
        }.issubset(response.data.keys()):
            return response

        response.data = {
            "success": True,
            "code": self.get_success_code(),
            "message": self.get_success_message(),
            "result": response.data,
        }
        return response


class BaseAPIView(FormattedResponseMixin, APIView):
    pass


class BaseCreateAPIView(FormattedResponseMixin, generics.CreateAPIView):
    pass


class BaseModelViewSet(FormattedResponseMixin, viewsets.ModelViewSet):
    pass
