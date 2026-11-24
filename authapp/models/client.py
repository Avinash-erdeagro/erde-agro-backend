from django.db import models

from .user import AppUser


class ClientProfile(models.Model):
    """
    An external client (e.g. a crop buyer) with a read-only view of
    farmers, farms and satellite data.

    Access scope is not defined yet; see the scope helper used by the
    client views.
    """

    app_user = models.OneToOneField(
        AppUser,
        on_delete=models.CASCADE,
        related_name="client_profile",
    )
    client_name = models.CharField(max_length=255)
    contact_person_name = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.client_name