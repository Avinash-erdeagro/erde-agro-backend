from django.db import models


class Organization(models.Model):
    """Root tenant that owns a hierarchy configuration."""

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["name"]


class HierarchyLevel(models.Model):
    """
    Defines a named role type within one Organization's hierarchy.
    level=1 is the highest (e.g. Corporate Admin), increasing values are lower.
    Role names (State Head, Area Officer, etc.) live here — not hardcoded elsewhere.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hierarchy_levels",
    )
    name = models.CharField(max_length=100)
    level = models.PositiveIntegerField(
        help_text="1 = highest in hierarchy; larger numbers = lower levels."
    )

    class Meta:
        unique_together = [
            ("organization", "level"),
            ("organization", "name"),
        ]
        ordering = ["organization", "level"]

    def __str__(self) -> str:
        return f"{self.organization.name} › L{self.level}: {self.name}"


class OrgUnit(models.Model):
    """
    A concrete node instance in the hierarchy tree
    (e.g. "Maharashtra Division" at the Area Head level).

    parent / path implement an adjacency-list + materialized-path pattern.
    The `path` field is maintained by `authapp.services.hierarchy.set_org_unit_path`
    and must not be edited directly.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="org_units",
    )
    hierarchy_level = models.ForeignKey(
        HierarchyLevel,
        on_delete=models.PROTECT,
        related_name="org_units",
    )
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    # Materialized path: "/1/", "/1/3/", "/1/3/7/" — managed by service layer.
    path = models.CharField(max_length=1000, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["organization", "path"]

    def __str__(self) -> str:
        return f"{self.hierarchy_level.name}: {self.name}"


class OrgMembership(models.Model):
    """
    Binds an ORG_USER AppUser to exactly one OrgUnit.
    The effective role name is resolved via org_unit → hierarchy_level → name.
    """

    app_user = models.OneToOneField(
        "authapp.AppUser",
        on_delete=models.CASCADE,
        related_name="org_membership",
    )
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.CASCADE,
        related_name="members",
    )

    class Meta:
        ordering = ["org_unit"]

    def __str__(self) -> str:
        return f"{self.app_user} → {self.org_unit}"


class OrgUnitFPO(models.Model):
    """
    Association table linking an FpoProfile into the org-unit hierarchy.
    Using a separate table (rather than a FK on FpoProfile) keeps FpoProfile
    decoupled and allows future multi-membership without a schema change.
    """

    fpo_profile = models.OneToOneField(
        "authapp.FpoProfile",
        on_delete=models.CASCADE,
        related_name="org_unit_link",
    )
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.CASCADE,
        related_name="fpo_links",
    )

    class Meta:
        ordering = ["org_unit"]

    def __str__(self) -> str:
        return f"FPO {self.fpo_profile} → {self.org_unit}"
