"""Rewarded-ad provider abstraction. No provider is considered complete by default.

A concrete provider adapter must expose ``create_ad_session(opportunity)`` and
return a mapping containing a provider session/reference and client launch data.
Provider completion is accepted only through the signed server webhook.
"""
from importlib import import_module
from django.conf import settings


class AdProviderUnavailable(Exception):
    pass


class UnconfiguredAdProvider:
    name = "mock"
    available = False

    def create_ad_session(self, opportunity):
        raise AdProviderUnavailable(
            "Rewarded ads are unavailable: no real ad provider is configured. "
            "The local mock never simulates a completed ad."
        )


class ProviderFreeDemoAdapter:
    """Explicit local/staging rewarded-ad simulator.

    This adapter never claims an ad was viewed. It only creates a provider-like
    session. Completion is handled by a separate, authenticated demo endpoint
    that is disabled unless ALLOW_PROVIDER_FREE_DEMO_ADS=true. Production must
    use a real provider adapter and signed provider webhook.
    """

    name = "provider-free-demo"
    available = True

    def create_ad_session(self, opportunity):
        from django.conf import settings
        import uuid

        return {
            "providerReference": f"pf-demo-{uuid.uuid4().hex}",
            "launch": {
                "mode": "provider-free-demo",
                "durationSeconds": int(getattr(settings, "PROVIDER_FREE_DEMO_DURATION_SECONDS", 3)),
                "label": "Provider-free demo rewarded action",
            },
        }


def get_ad_provider():
    adapter_path = getattr(settings, "AD_PROVIDER_ADAPTER", "").strip()
    provider_name = str(getattr(settings, "AD_PROVIDER", "mock")).strip().lower()
    if provider_name == "provider_free_demo":
        if not getattr(settings, "ALLOW_PROVIDER_FREE_DEMO_ADS", False):
            raise AdProviderUnavailable(
                "Provider-free demo rewards are disabled. Set ALLOW_PROVIDER_FREE_DEMO_ADS=true for local/staging only."
            )
        return ProviderFreeDemoAdapter()
    if provider_name in {"", "mock", "none", "disabled"} or not adapter_path:
        return UnconfiguredAdProvider()
    module_path, separator, attribute = adapter_path.rpartition(".")
    if not separator:
        raise AdProviderUnavailable("AD_PROVIDER_ADAPTER must be a dotted Python path.")
    adapter = getattr(import_module(module_path), attribute)
    provider = adapter() if isinstance(adapter, type) else adapter
    if not callable(getattr(provider, "create_ad_session", None)):
        raise AdProviderUnavailable("Configured ad provider does not implement create_ad_session().")
    return provider
