from farmerapp.models import Farm


def filter_fpo_farms(fpo_profile, state=None, district=None, farmer_id=None):
    """Farms of an FPO narrowed to the sidebar selection.

    Shared by the overview and the farm-boundaries map so both always cover
    exactly the same set of farms.
    """
    farms = Farm.objects.filter(farmer__farmer_profile__registered_with_fpo=fpo_profile)
    if state:
        farms = farms.filter(farmer__farmer_profile__locality__state__iexact=state)
    if district:
        farms = farms.filter(farmer__farmer_profile__locality__district__iexact=district)
    if farmer_id:
        farms = farms.filter(farmer__farmer_profile__id=farmer_id)
    return farms
