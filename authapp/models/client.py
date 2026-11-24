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


class ClientScope(models.Model):
    """
    Defines which data a ClientProfile can see.

    Source (at least one required, otherwise the client sees nothing):
      - fpos:      these FPOs, as a fixed list.
      - org_units: every FPO linked to these units or any unit below them
                   (e.g. an HO unit covers all its District Heads' FPOs).
                   New FPOs linked under them are included automatically.

    Both lists are combined: an FPO is in scope if it matches either.
    """

    client = models.OneToOneField(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="scope",
    )
    fpos = models.ManyToManyField(
        "authapp.FpoProfile",
        related_name="client_scopes",
        blank=True,
    )
    org_units = models.ManyToManyField(
        "authapp.OrgUnit",
        related_name="client_scopes",
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Scope: {self.client}"