import os
from pathlib import Path

from corsheaders.defaults import default_headers


BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# CORE SETTINGS
# ============================================================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "development-only-change-me",
)

DEBUG = (
    os.getenv(
        "DJANGO_DEBUG",
        "true",
    ).lower()
    in {"1", "true", "yes", "on"}
)


ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1,backend",
    ).split(",")
    if host.strip()
]


# ============================================================
# GAME CONFIGURATION
# ============================================================

GAME_NAME = (
    os.getenv(
        "GAME_NAME",
        "APPLE WORM ADVENTURE",
    ).strip()
    or "APPLE WORM ADVENTURE"
)


# ============================================================
# EMAIL VERIFICATION
# ============================================================

EMAIL_VERIFICATION_REQUIRED = (
    os.getenv(
        "EMAIL_VERIFICATION_REQUIRED",
        "true" if not DEBUG else "false",
    ).lower()
    in {"1", "true", "yes", "on"}
)


# ============================================================
# EMAIL CONFIGURATION
# ============================================================
#
# Local development:
#
#     EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
#
# Emails will appear in:
#
#     docker compose logs -f backend
#
# Production:
#
#     Configure a real SMTP/transactional email provider
#     through environment variables.
#
# Never hard-code SMTP passwords or API secrets here.
# ============================================================

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    "",
)

EMAIL_PORT = int(
    os.getenv(
        "EMAIL_PORT",
        "587",
    )
)

EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    "",
)

EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD",
    "",
)

EMAIL_USE_TLS = (
    os.getenv(
        "EMAIL_USE_TLS",
        "true",
    ).lower()
    in {"1", "true", "yes", "on"}
)

EMAIL_USE_SSL = (
    os.getenv(
        "EMAIL_USE_SSL",
        "false",
    ).lower()
    in {"1", "true", "yes", "on"}
)

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "Apple Worm Adventure <no-reply@example.com>",
)

SERVER_EMAIL = os.getenv(
    "SERVER_EMAIL",
    DEFAULT_FROM_EMAIL,
)


# Frontend URL used when generating email verification links.
FRONTEND_BASE_URL = (
    os.getenv(
        "FRONTEND_BASE_URL",
        "http://localhost:5174",
    ).strip().rstrip("/")
)


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",

    "core",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # CORS middleware must be placed before CommonMiddleware.
    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL / WSGI
# ============================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",

        "NAME": os.getenv(
            "POSTGRES_DB",
            "veloop",
        ),

        "USER": os.getenv(
            "POSTGRES_USER",
            "veloop_user",
        ),

        "PASSWORD": os.getenv(
            "POSTGRES_PASSWORD",
            "change-this-password",
        ),

        "HOST": os.getenv(
            "POSTGRES_HOST",
            "localhost",
        ),

        "PORT": os.getenv(
            "POSTGRES_PORT",
            "5432",
        ),
    }
}


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# CORS
# ============================================================

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        (
            "http://localhost:5174,"
            "http://127.0.0.1:5174,"
            "http://localhost:5173,"
            "http://127.0.0.1:5173"
        ),
    ).split(",")
    if origin.strip()
]


# Allow authenticated cross-origin API requests.
CORS_ALLOW_CREDENTIALS = True


# Preserve django-cors-headers default headers and explicitly
# allow Cache-Control because the browser's preflight request
# includes it.
CORS_ALLOW_HEADERS = list(default_headers) + [
    "cache-control",
]


# ============================================================
# CSRF TRUSTED ORIGINS
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        (
            "http://localhost:5174,"
            "http://127.0.0.1:5174,"
            "http://localhost:5173,"
            "http://127.0.0.1:5173"
        ),
    ).split(",")
    if origin.strip()
]


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],

    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "240/min",
    },

    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],

    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}


# ============================================================
# SECURITY / HTTPS
# ============================================================
#
# Local Docker:
#
#     SECURE_SSL_REDIRECT=False
#     SESSION_COOKIE_SECURE=False
#     CSRF_COOKIE_SECURE=False
#     SECURE_HSTS_SECONDS=0
#
# Production:
#
#     SECURE_SSL_REDIRECT=True
#     SESSION_COOKIE_SECURE=True
#     CSRF_COOKIE_SECURE=True
#     SECURE_HSTS_SECONDS=31536000
#
# DEBUG=False does NOT automatically force HTTPS.
# ============================================================

SECURE_SSL_REDIRECT = (
    os.getenv(
        "SECURE_SSL_REDIRECT",
        "False",
    ).lower()
    in {"1", "true", "yes", "on"}
)


SESSION_COOKIE_SECURE = (
    os.getenv(
        "SESSION_COOKIE_SECURE",
        "False",
    ).lower()
    in {"1", "true", "yes", "on"}
)


CSRF_COOKIE_SECURE = (
    os.getenv(
        "CSRF_COOKIE_SECURE",
        "False",
    ).lower()
    in {"1", "true", "yes", "on"}
)


SECURE_HSTS_SECONDS = int(
    os.getenv(
        "SECURE_HSTS_SECONDS",
        "0",
    )
)


SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.getenv(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS",
        "False",
    ).lower()
    in {"1", "true", "yes", "on"}
)


SECURE_HSTS_PRELOAD = (
    os.getenv(
        "SECURE_HSTS_PRELOAD",
        "False",
    ).lower()
    in {"1", "true", "yes", "on"}
)


# Session and CSRF cookie hardening. Secure is enabled only when explicitly
# configured for the HTTPS production deployment; local HTTP remains usable.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_HTTPONLY = os.getenv("CSRF_COOKIE_HTTPONLY", "False").lower() in {"1", "true", "yes", "on"}

SECURE_CONTENT_TYPE_NOSNIFF = (
    os.getenv(
        "SECURE_CONTENT_TYPE_NOSNIFF",
        "True",
    ).lower()
    in {"1", "true", "yes", "on"}
)


SECURE_REFERRER_POLICY = os.getenv(
    "SECURE_REFERRER_POLICY",
    "strict-origin-when-cross-origin",
)


X_FRAME_OPTIONS = os.getenv(
    "X_FRAME_OPTIONS",
    "DENY",
)


# ============================================================
# REVERSE PROXY HTTPS SUPPORT
# ============================================================

SECURE_PROXY_SSL_HEADER = None


if (
    os.getenv(
        "SECURE_PROXY_SSL_HEADER_ENABLED",
        "False",
    ).lower()
    in {"1", "true", "yes", "on"}
):
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )


# ============================================================
# ECONOMY / ADS
# ============================================================

AD_PROVIDER = os.getenv(
    "AD_PROVIDER",
    "mock",
)


AD_PROVIDER_WEBHOOK_SECRET = os.getenv(
    "AD_PROVIDER_WEBHOOK_SECRET",
    "",
)

# Optional dotted path to a real provider adapter implementing
# create_ad_session(opportunity). Never set this to a fake completion adapter.
AD_PROVIDER_ADAPTER = os.getenv("AD_PROVIDER_ADAPTER", "")

# Provider-free demo mode is an explicit local/staging simulation. It is
# never a real ad network and must remain disabled for production monetization.
ALLOW_PROVIDER_FREE_DEMO_ADS = os.getenv("ALLOW_PROVIDER_FREE_DEMO_ADS", "false").lower() == "true"
PROVIDER_FREE_DEMO_DURATION_SECONDS = max(1, int(os.getenv("PROVIDER_FREE_DEMO_DURATION_SECONDS", "3")))


# Explicitly opt-in local/evidence-only Phase 6 level provisioning.
PHASE6_TEST_PROVISIONING_ENABLED = os.getenv("PHASE6_TEST_PROVISIONING_ENABLED", "false").lower() == "true"
