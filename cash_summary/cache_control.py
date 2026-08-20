from django.utils.cache import patch_cache_control


class AuthenticatedNoCacheMiddleware:
    """Prevent browser/proxy caching of authenticated pages.

    This is intentionally applied after AuthenticationMiddleware so request.user
    is available. It makes browser Back after logout revalidate instead of showing
    a cached protected page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            patch_cache_control(
                response,
                no_cache=True,
                no_store=True,
                must_revalidate=True,
                max_age=0,
                private=True,
            )
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response
