import requests


PINCODE_API_URL = "https://api.postalpincode.in/pincode/{pin_code}"


class PincodeLookupError(Exception):
    pass


def fetch_localities_by_pincode(pin_code: str):
    pin_code = pin_code.strip()

    if not pin_code.isdigit() or len(pin_code) != 6:
        raise PincodeLookupError("PIN code must contain exactly 6 digits.")

    try:
        response = requests.get(
            PINCODE_API_URL.format(pin_code=pin_code),
            timeout=(5, 10),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
            verify=False,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise PincodeLookupError(f"Failed to connect to pincode service: {exc}") from exc

    data = response.json()
    if not isinstance(data, list) or not data:
        raise PincodeLookupError("Invalid response from pincode service.")

    first_item = data[0]
    if first_item.get("Status") != "Success":
        message = first_item.get("Message") or "No locality found for this PIN code."
        raise PincodeLookupError(message)

    post_offices = first_item.get("PostOffice") or []
    if not post_offices:
        raise PincodeLookupError("No locality found for this PIN code.")

    district = (post_offices[0].get("District") or "").strip()
    state = (post_offices[0].get("State") or "").strip()

    localities = []
    seen = set()

    for office in post_offices:
        village = (office.get("Name") or "").strip()
        taluka = (office.get("Block") or "").strip()

        key = (village, taluka)
        if key in seen:
            continue
        seen.add(key)

        localities.append(
            {
                "village": village,
                "taluka": taluka,
            }
        )

    return {
        "pin_code": pin_code,
        "district": district,
        "state": state,
        "localities": localities,
    }

