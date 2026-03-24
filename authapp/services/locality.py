from authapp.models import Locality

def _normalize_whitespace(value):
    return " ".join(value.strip().split())

def normalize_locality_data(locality_data):
    return {
        "pin_code": _normalize_whitespace(locality_data["pin_code"]),
        "village": _normalize_whitespace(locality_data["village"]).title(),
        "taluka": _normalize_whitespace(locality_data["taluka"]).title(),
        "district": _normalize_whitespace(locality_data["district"]).title(),
        "state": _normalize_whitespace(locality_data["state"]).title(),
    }

def get_or_create_locality(locality_data):
    normalized_data = normalize_locality_data(locality_data)
    locality, _ = Locality.objects.get_or_create(**normalized_data)
    return locality