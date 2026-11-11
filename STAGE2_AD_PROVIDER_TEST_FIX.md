# Stage 2 rewarded-ad test configuration fix

## Root cause
The mock-provider regression test depended on the process environment. The isolated Compose backend loads the project `.env`, which may explicitly enable `AD_PROVIDER=provider_free_demo` and `ALLOW_PROVIDER_FREE_DEMO_ADS=true`. In that configuration, the request endpoint correctly returns HTTP 200 with a provider-free demo session, while the test was asserting the mock-provider HTTP 503 contract.

## Permanent test correction
The test `RewardedAdVerificationFlowTests.test_mock_provider_never_marks_ad_completed` now uses Django `override_settings` to pin `AD_PROVIDER=mock`, clear `AD_PROVIDER_ADAPTER`, and disable provider-free demo mode for that test only. This makes the test deterministic and verifies the intended unconfigured-mock behavior regardless of local `.env` values.

No production provider logic, ad lifecycle, reward granting, gameplay, authentication, or database configuration was changed. Provider-free demo mode remains available when explicitly enabled for local/staging.

## Verification
Run the isolated backend suite:

```powershell
docker compose -p awa_candidate_isolated -f .\docker-compose.yml -f .\docker-compose.isolated.yml exec -T backend python manage.py test core -v 1
```

Expected: all 111 tests pass. The Level 23 move-limit boundary regression tests remain in `tests_phase5_6.py`.
