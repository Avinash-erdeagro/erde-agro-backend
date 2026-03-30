from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics, viewsets


class FormattedResponseMixin:
    success_message = "Request successful."
    action_success_messages = {
        "list": "Data fetched successfully.",
        "retrieve": "Data fetched successfully.",
        "create": "Created successfully.",
        "update": "Updated successfully.",
        "partial_update": "Updated successfully.",
        "destroy": "Deleted successfully.",
    }

    def get_success_message(self):
        action = getattr(self, "action", None)
        if action:
            return self.action_success_messages.get(action, self.success_message)
        return self.success_message

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
