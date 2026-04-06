from rest_framework import viewsets

from authapp.api.views.base import FormattedResponseMixin


class BaseReadOnlyModelViewSet(FormattedResponseMixin, viewsets.ReadOnlyModelViewSet):
    pass