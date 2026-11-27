from django.urls import path

from orgapp.api.views.tree import OrgTreeRootView, OrgUnitChildrenView

urlpatterns = [
    path("tree/", OrgTreeRootView.as_view(), name="org-tree-root"),
    path("units/<int:unit_id>/children/", OrgUnitChildrenView.as_view(), name="org-unit-children"),
]
