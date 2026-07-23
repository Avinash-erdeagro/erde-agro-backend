from django.utils.functional import SimpleLazyObject

from authapp.models import AppUser

DEFAULT_LANGUAGE = AppUser.PreferredLanguage.ENGLISH


def resolve_language(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        app_user = AppUser.objects.filter(user=user).only("preferred_language").first()
        if app_user:
            return app_user.preferred_language
    return DEFAULT_LANGUAGE


class PreferredLanguageMiddleware:
    """
    Attaches ``request.language_code``, the language the response should use.

    The value is lazy on purpose. JWT tokens are decoded by DRF inside the view,
    after every middleware has run, so ``request.user`` is still anonymous here.
    Resolving on first read means the user is known by then, and requests that
    never read the language cost no extra query.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.language_code = SimpleLazyObject(lambda: resolve_language(request))
        return self.get_response(request)
