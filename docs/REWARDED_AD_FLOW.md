# Rewarded-ad provider flow (Phase 2)

## Honest local behavior

The default `AD_PROVIDER=mock` is an **unavailable development adapter**. It never reports an ad as started, completed, verified, or rewarded. A user click only creates an `OFFERED` opportunity; the request endpoint returns `AD_UNAVAILABLE` (HTTP 503) until a real provider adapter is configured. No reward is granted in this mode.

## Lifecycle

`OFFERED → REQUESTED → AD_STARTED → AD_COMPLETED → VERIFYING → VERIFIED → GRANTED`

The backend persists the lifecycle events in `AdOpportunity.metadata.adLifecycle`. The `status` column stores the current durable state. `AD_COMPLETED`, `VERIFYING`, and `VERIFIED` are recorded only after a signed provider webhook is accepted. The player client cannot set these states. `GRANTED` is set transactionally with creation of the unique `RewardTransaction`.

## Provider adapter contract

Configure `AD_PROVIDER` to a descriptive provider name and `AD_PROVIDER_ADAPTER` to a dotted Python class/object path. The adapter must implement `create_ad_session(opportunity)` and return:

```python
{
    "providerReference": "provider-issued-session-id",
    "launch": {"url": "https://provider.example/ad-session/..."},
}
```

The provider must call `POST /api/economy/ad-provider-callback/` from its server after a genuinely completed rewarded ad. Callback payload fields are `eventId`, `providerReference`, `eventStatus=COMPLETED`, and `signature`; signature is HMAC-SHA256 over `eventId:providerReference:COMPLETED` using `AD_PROVIDER_WEBHOOK_SECRET`. The provider adapter must use the same secret and send the exact provider reference issued for that opportunity. Do not expose the webhook secret to the browser.

The browser polls the authenticated opportunity status endpoint and calls claim only after the backend reports `VERIFIED`. The claim endpoint independently checks ownership, session binding, reward limits, cooldown, and unique reward event id. Duplicate claims return the existing ledger result and do not create another reward.

## Endpoints

- `POST /api/economy/ad-opportunity/` — create `OFFERED` opportunity.
- `POST /api/economy/ad-opportunity/{eventId}/request/` — request provider session; unavailable provider returns 503.
- `GET /api/economy/ad-opportunity/{eventId}/status/` — owner-only status.
- `POST /api/economy/ad-provider-callback/` — signed provider-to-server completion callback.
- `POST /api/economy/claim-reward/` — grant only a `VERIFIED` opportunity.

## Current limitation

No real advertising vendor SDK/account credentials are included in this project archive. Therefore the local default is intentionally unavailable and no live ad inventory can be shown until a vendor-specific adapter and its provider-side webhook are configured and independently tested. This is not represented as a real ad integration.


## Provider-free demo mode

When an external advertising provider is unavailable, local/staging environments may use `AD_PROVIDER=provider_free_demo` with `ALLOW_PROVIDER_FREE_DEMO_ADS=true`. The adapter creates a provider-like session and the authenticated demo completion endpoint verifies it as `MOCKED_PROVIDER_FREE_DEMO` before the normal reward claim/ledger flow runs. This is intentionally not a real advertisement and must not be presented as live monetization. Production deployments must disable the demo flag and configure a real provider adapter plus signed webhook.
