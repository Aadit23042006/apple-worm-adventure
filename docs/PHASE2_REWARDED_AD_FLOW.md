# Phase 2 — Rewarded Advertisement Flow

## Security boundary

The browser can request an opportunity and request an ad session. It cannot mark an ad completed, verified, or granted. Only the backend provider callback can move an opportunity to `VERIFIED`, and the authenticated owner can then claim it. The callback requires an HMAC-SHA256 signature made with `AD_PROVIDER_WEBHOOK_SECRET`, the exact event ID, provider reference, and `COMPLETED` status. A callback is accepted only for an existing opportunity whose state is `AD_STARTED` and whose provider reference matches.

## Lifecycle

The audit trail in `AdOpportunity.metadata.adLifecycle` records:

`OFFERED → REQUESTED → AD_STARTED → AD_COMPLETED → VERIFYING → VERIFIED → GRANTED`

The model's `status` field stores the current durable state. When a provider is not configured, the request attempt is recorded, the opportunity remains `OFFERED`, the API responds `AD_UNAVAILABLE`, and no completion timestamp, reward transaction, wallet credit, or gameplay reward is created. This leaves the offer safe to retry after a real provider is configured.

## Provider adapter contract

Configure `AD_PROVIDER` to a provider name and `AD_PROVIDER_ADAPTER` to a dotted Python class path. The adapter must implement:

```python
class MyProvider:
    name = "my-provider"
    available = True

    def create_ad_session(self, opportunity):
        # Create a provider-side rewarded ad session.
        # Return a unique providerReference and client-safe launch data.
        return {
            "providerReference": "provider-session-id",
            "launch": {"url": "https://provider.example/ad/session"},
        }
```

The launch URL, when present, must be HTTPS. The provider's server must call the configured callback endpoint after its own verification and sign the canonical message:

`{eventId}:{providerReference}:COMPLETED`

using HMAC-SHA256 and the shared webhook secret. Never put `AD_PROVIDER_WEBHOOK_SECRET` in frontend variables or expose it to the browser.

## Local development

The default `AD_PROVIDER=mock` is intentionally unavailable. It does not simulate playback or completion. This is the correct local behavior when a real provider cannot be used; it is not evidence of a live ad-network integration.

## Preserved economy controls

The existing server-side placement/session eligibility, cooldown, daily cap, placement-specific limits, reward calculations, transaction atomicity, unique event IDs, reward ledger, and wallet ledger remain authoritative. The frontend only updates its display after the backend reports `VERIFIED` and the claim endpoint returns the persisted result.

## API sequence

1. `POST /api/economy/ad-opportunity/` — create `OFFERED`.
2. `POST /api/economy/ad-opportunity/{eventId}/request/` — ask the adapter to create an ad session; returns `AD_STARTED` or `AD_UNAVAILABLE`.
3. Provider calls `POST /api/economy/ad-provider-callback/` — signed provider completion.
4. `GET /api/economy/ad-opportunity/{eventId}/status/` — authenticated owner polls current state and lifecycle.
5. `POST /api/economy/claim-reward/` — claim only after `VERIFIED`; duplicate claims are idempotent.

## Important limitation

No vendor SDK, provider account, or provider credentials are bundled with this source archive. A vendor-specific adapter and provider-side webhook configuration are required for live ads. The included mock deliberately refuses to fabricate completion.
