from collections import Counter

from django.db.models import Count
from rest_framework import status

from authapp.api.responses import api_response
from authapp.api.response_codes import ResponseCode
from authapp.models import OrgUnitFPO
from orgapp.api.views.base import OrgScopedAPIView
from satelliteapp.models import SatelliteFarmAlert, SatelliteFarmNotification


class _OrgTreeMixin:
    """
    Builds the sidebar nodes of the hierarchy tree.

    A unit's farmers_count / has_alert / has_notification cover its whole
    subtree (the unit itself and every unit below it). An FPO's cover that
    FPO's farmers. Computed in a few grouped queries for the caller's scope,
    then summed per node in Python (the trees are small).
    """

    def load_scope_stats(self, observation_date):
        """Per-FPO stats for every FPO in the caller's scope."""
        # (unit path, fpo id) for every FPO link inside the caller's subtree.
        self._links = list(
            OrgUnitFPO.objects.filter(org_unit__in=self.get_org_units())
            .values_list("org_unit__path", "fpo_profile_id")
        )
        fpo_ids = [fpo_id for _, fpo_id in self._links]

        self._farmers_by_fpo = Counter(
            dict(
                self.get_farmers()
                .values("registered_with_fpo_id")
                .annotate(n=Count("id"))
                .values_list("registered_with_fpo_id", "n")
            )
        )
        self._fpos_with_alert = set(
            SatelliteFarmAlert.objects.filter(
                order_farm__farm__farmer__farmer_profile__registered_with_fpo_id__in=fpo_ids,
                observation_date=observation_date,
            ).values_list("order_farm__farm__farmer__farmer_profile__registered_with_fpo_id", flat=True)
        )
        self._fpos_with_notification = set(
            SatelliteFarmNotification.objects.filter(
                order_farm__farm__farmer__farmer_profile__registered_with_fpo_id__in=fpo_ids,
                observation_date=observation_date,
            ).values_list("order_farm__farm__farmer__farmer_profile__registered_with_fpo_id", flat=True)
        )

    def _stats(self, fpo_ids):
        fpo_ids = set(fpo_ids)
        return {
            "farmers_count": sum(self._farmers_by_fpo.get(i, 0) for i in fpo_ids),
            "has_alert": bool(fpo_ids & self._fpos_with_alert),
            "has_notification": bool(fpo_ids & self._fpos_with_notification),
        }

    def unit_node(self, unit, has_children):
        subtree_fpo_ids = [
            fpo_id for path, fpo_id in self._links if path.startswith(unit.path)
        ]
        return {
            "type": "unit",
            "id": unit.id,
            "name": unit.name,
            "level": unit.hierarchy_level.level,
            "level_name": unit.hierarchy_level.name,
            "has_children": has_children,
            **self._stats(subtree_fpo_ids),
        }

    def fpo_node(self, fpo):
        return {
            "type": "fpo",
            "id": fpo.id,
            "name": fpo.fpo_name,
            **self._stats([fpo.id]),
        }

    def unit_has_children(self, unit):
        return unit.children.exists() or unit.fpo_links.exists()


class OrgTreeRootView(_OrgTreeMixin, OrgScopedAPIView):
    """
    GET /org/tree/?observation_date=YYYY-MM-DD

    The root of the sidebar tree: the caller's own org unit, with farmer
    count and alert/notification flags for its whole subtree.
    """

    def get(self, request):
        observation_date, error = self.get_observation_date()
        if error:
            return error

        self.load_scope_stats(observation_date)
        unit = self.org_unit
        return api_response(
            success=True,
            message="Organization tree root fetched successfully.",
            code=ResponseCode.ORG_TREE_FETCHED,
            result={"root": self.unit_node(unit, self.unit_has_children(unit))},
            status_code=status.HTTP_200_OK,
        )


class OrgUnitChildrenView(_OrgTreeMixin, OrgScopedAPIView):
    """
    GET /org/units/<unit_id>/children/?observation_date=YYYY-MM-DD

    What is directly under one unit in the tree: its child units and the
    FPOs linked to it. The unit must be in the caller's subtree, else 404.
    """

    def get(self, request, unit_id):
        observation_date, error = self.get_observation_date()
        if error:
            return error

        unit = (
            self.get_org_units()
            .select_related("hierarchy_level")
            .filter(pk=unit_id)
            .first()
        )
        if unit is None:
            return api_response(
                success=False,
                message="Org unit not found.",
                code=ResponseCode.ORG_UNIT_NOT_FOUND,
                result=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.load_scope_stats(observation_date)

        child_units = unit.children.select_related("hierarchy_level").order_by("name")
        fpos = self.get_fpos().filter(org_unit_link__org_unit=unit).order_by("fpo_name")

        return api_response(
            success=True,
            message=f"Children of org unit '{unit.name}'.",
            code=ResponseCode.ORG_UNIT_CHILDREN_FETCHED,
            result={
                "units": [
                    self.unit_node(child, self.unit_has_children(child))
                    for child in child_units
                ],
                "fpos": [self.fpo_node(fpo) for fpo in fpos],
            },
            status_code=status.HTTP_200_OK,
        )
