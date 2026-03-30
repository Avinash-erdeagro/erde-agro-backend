from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    message = "Request failed."
    if isinstance(response.data, dict) and isinstance(response.data.get("detail"), str):
        message = response.data["detail"]
    elif response.status_code == 400:
        message = "Validation failed."
    elif response.status_code == 401:
        message = "Authentication failed."
    elif response.status_code == 403:
        message = "Permission denied."
    elif response.status_code == 404:
        message = "Resource not found."

    response.data = {
        "success": False,
        "message": message,
        "result": response.data,
    }
    return response
