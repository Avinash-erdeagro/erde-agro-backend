from rest_framework.response import Response

from authapp.api.response_codes import ResponseCode


def api_response(*, success, message, result=None, status_code=200, code=None):
    """Standard envelope for API responses.

    ``code`` is a stable, machine-readable key the frontend maps to localized
    UI copy. ``message`` stays English (developer-facing / fallback). When a
    caller doesn't pass a ``code`` it falls back to ``SUCCESS``/``ERROR``.
    """
    if code is None:
        code = ResponseCode.SUCCESS if success else ResponseCode.ERROR
    return Response(
        {
            "success": success,
            "code": code,
            "message": message,
            "result": result,
        },
        status=status_code,
    )
