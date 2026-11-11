# Provider-free rewarded-ad fix

The release now supports an explicit provider-free demo path for local/staging environments.

- No external ad SDK/account is required for local testing.
- Reward buttons no longer fail solely because the environment has no external provider.
- Demo rewards still use the server-authoritative opportunity -> started -> verified -> claim -> ledger flow.
- Demo verification is authenticated, session-bound, capped and idempotent.
- Demo events are recorded as `MOCKED_PROVIDER_FREE_DEMO`; they are not real ad-network events.
- Production must set `ALLOW_PROVIDER_FREE_DEMO_ADS=false` and use a real provider adapter plus signed webhook for actual monetization.
