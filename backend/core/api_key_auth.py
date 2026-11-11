from functools import wraps

from django.utils import timezone
from rest_framework.response import Response

from .models import ApiKey
from .views import digest


def get_api_key(request):
    """
    Read an API key only from the X-API-Key header.

    API keys are deliberately not accepted through query parameters because
    query strings can appear in logs, browser history, proxies, etc.
    """
    return (
        request.headers.get("X-API-Key")
        or request.META.get("HTTP_X_API_KEY")
        or ""
    ).strip()


def authenticate_api_key(request):
    """
    Authenticate a request using a stored API-key hash.

    The raw API key is never stored in the database.
    """
    raw = get_api_key(request)

    if not raw:
        return None

    key = (
        ApiKey.objects
        .select_related("user")
        .filter(
            key_hash=digest(raw),
            revoked_at__isnull=True,
            user__is_active=True,
        )
        .first()
    )

    if key is None:
        return None

    # Record successful API-key usage.
    key.last_used_at = timezone.now()
    key.save(update_fields=["last_used_at"])

    return key.user


def api_key_auth_required(view_func):
    """
    Decorator for endpoints that require a valid X-API-Key header.
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = authenticate_api_key(request)

        if user is None:
            return Response(
                {"detail": "Invalid or revoked API key."},
                status=401,
            )

        request.user = user
        request.auth_method = "api_key"

        return view_func(request, *args, **kwargs)

    return wrapped