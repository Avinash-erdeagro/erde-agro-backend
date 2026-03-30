from rest_framework.response import Response


def api_response(*, success, message, result=None, status_code=200):
    return Response(
        {
            "success": success,
            "message": message,
            "result": result,
        },
        status=status_code,
    )
