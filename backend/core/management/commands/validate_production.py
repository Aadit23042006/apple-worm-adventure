import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models import Achievement, EconomyConfig, Level
from core.ad_providers import get_ad_provider
from core.views import level_objectives, level_static_config


class Command(BaseCommand):
    help = "Validate production configuration and company-required seeded game data."

    def handle(self, *args, **options):
        errors = []

        if settings.DEBUG:
            errors.append("DJANGO_DEBUG must be false in production.")
        if len(settings.SECRET_KEY) < 50 or "change" in settings.SECRET_KEY.lower():
            errors.append("DJANGO_SECRET_KEY must be a long non-placeholder secret.")
        domain = os.getenv("AWA_DOMAIN", "").strip().lower()
        if not settings.ALLOWED_HOSTS:
            errors.append("DJANGO_ALLOWED_HOSTS must not be empty.")
        if not domain or domain not in {host.lower() for host in settings.ALLOWED_HOSTS}:
            errors.append("DJANGO_ALLOWED_HOSTS must include the configured AWA_DOMAIN.")
        expected_origin = f"https://{domain}" if domain else ""
        if expected_origin and expected_origin not in settings.CORS_ALLOWED_ORIGINS:
            errors.append("CORS_ALLOWED_ORIGINS must include the configured HTTPS AWA_DOMAIN origin.")
        if expected_origin and expected_origin not in settings.CSRF_TRUSTED_ORIGINS:
            errors.append("CSRF_TRUSTED_ORIGINS must include the configured HTTPS AWA_DOMAIN origin.")
        if not settings.SECURE_SSL_REDIRECT:
            errors.append("SECURE_SSL_REDIRECT must be enabled in production.")
        if not settings.SESSION_COOKIE_HTTPONLY:
            errors.append("SESSION_COOKIE_HTTPONLY must be enabled in production.")
        if settings.SESSION_COOKIE_SAMESITE not in {"Lax", "Strict", "None"}:
            errors.append("SESSION_COOKIE_SAMESITE must be Lax, Strict, or None.")
        if settings.CSRF_COOKIE_SAMESITE not in {"Lax", "Strict", "None"}:
            errors.append("CSRF_COOKIE_SAMESITE must be Lax, Strict, or None.")
        if not settings.SECURE_PROXY_SSL_HEADER:
            errors.append("SECURE_PROXY_SSL_HEADER must trust the HTTPS reverse-proxy header.")
        if settings.SECURE_HSTS_INCLUDE_SUBDOMAINS or settings.SECURE_HSTS_PRELOAD:
            errors.append("HSTS subdomains/preload must remain disabled until all hostnames meet the policy.")
        if not settings.SESSION_COOKIE_SECURE or not settings.CSRF_COOKIE_SECURE:
            errors.append("Secure session and CSRF cookies must be enabled.")
        if settings.SECURE_HSTS_SECONDS < 31536000:
            errors.append("SECURE_HSTS_SECONDS must be at least 31536000.")
        if not settings.AD_PROVIDER_WEBHOOK_SECRET or "change_me" in settings.AD_PROVIDER_WEBHOOK_SECRET.lower():
            errors.append("AD_PROVIDER_WEBHOOK_SECRET must be configured with the provider's signing secret.")
        if settings.AD_PROVIDER in {"", "mock", "none", "disabled", "provider_free_demo"}:
            errors.append("A real rewarded-ad provider is required for production.")
        if not settings.AD_PROVIDER_ADAPTER or "change_me" in settings.AD_PROVIDER_ADAPTER.lower():
            errors.append("AD_PROVIDER_ADAPTER must point to a configured real provider adapter.")
        if not settings.EMAIL_HOST or "change_me" in settings.EMAIL_HOST.lower():
            errors.append("A real SMTP EMAIL_HOST is required for production email verification.")
        if settings.ALLOW_PROVIDER_FREE_DEMO_ADS:
            errors.append("ALLOW_PROVIDER_FREE_DEMO_ADS must be false in production.")
        try:
            get_ad_provider()
        except Exception:
            errors.append("The configured real rewarded-ad provider adapter could not be loaded.")
        if not settings.CORS_ALLOWED_ORIGINS or any(not origin.startswith("https://") for origin in settings.CORS_ALLOWED_ORIGINS):
            errors.append("CORS_ALLOWED_ORIGINS must contain the deployed HTTPS frontend origin(s).")
        if not settings.CSRF_TRUSTED_ORIGINS or any(not origin.startswith("https://") for origin in settings.CSRF_TRUSTED_ORIGINS):
            errors.append("CSRF_TRUSTED_ORIGINS must contain the deployed HTTPS frontend origin(s).")

        active_levels = list(Level.objects.filter(is_active=True).order_by("number"))
        level_count = len(active_levels)
        if level_count < 50:
            errors.append(f"At least 50 active levels are required; found {level_count}.")

        for level in active_levels:
            cfg = level_static_config(level.number)
            expected = level_objectives(
                level.number,
                size=cfg["size"],
                apple_count=len(cfg["apples"]),
            )
            if level.config.get("objectives") != expected:
                errors.append(
                    f"Level {level.number} objective configuration is missing or invalid."
                )

        economy = EconomyConfig.objects.filter(key="default").first()
        if not economy or not isinstance(economy.config, dict):
            errors.append("Default economy configuration is missing.")

        if Achievement.objects.count() < 10:
            errors.append("At least 10 achievements are required.")

        if errors:
            raise CommandError("\n".join(f"- {error}" for error in errors))

        self.stdout.write(self.style.SUCCESS(
            f"Production validation passed: {level_count} active levels, "
            f"{Achievement.objects.count()} achievements, economy configuration present."
        ))
