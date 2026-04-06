from rest_framework.views import exception_handler


def _extract_error_message(data):
    if isinstance(data, dict):
        for value in data.values():
            message = _extract_error_message(value)
            if message:
                return message
        return None

    if isinstance(data, list):
        for item in data:
            message = _extract_error_message(item)
            if message:
                return message
        return None

    if isinstance(data, str):
        return data

    return None


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    message = "Request failed."
    if isinstance(response.data, dict) and isinstance(response.data.get("detail"), str):
        message = response.data["detail"]
    elif response.status_code == 400:
        message = _extract_error_message(response.data) or "Validation failed."
    elif response.status_code == 401:
        message = "Authentication failed."
    elif response.status_code == 403:
        message = "Permission denied."
    elif response.status_code == 404:
        message = "Resource not found."

    response.data = {
        "success": False,
        "message": message,
        "result": None,
    }
    return response
