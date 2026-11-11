# Phase 2 Implementation & Verification Report

## Source basis

The VELoop assignment permits a provider abstraction/mock when an actual provider cannot be used locally, but explicitly prohibits setting a fake `adFinished = true` and claiming it is an ad integration (PDF section 111). It requires backend verification, ledger-based reward granting, idempotency, failure handling, and clear reward button states (sections 39, 47–50, 59–70, 104–105, 108).

## Changes included

- Retained a provider adapter boundary (`backend/core/ad_providers.py`).
- Kept the default mock unavailable; it never reports ad completion.
- Hardened provider startup failure handling and required HTTPS for provider launch URLs.
- Recorded lifecycle events in the opportunity audit metadata, including `GRANTED`.
- Returned lifecycle history from the authenticated status endpoint.
- Persisted provider launch data so an idempotent retry can recover a provider launch response.
- Retained signed HMAC callback verification, exact provider-reference matching, `AD_STARTED` precondition, and callback idempotency.
- Retained claim-time verification requirement, user/session binding, server-calculated rewards, cooldowns, daily/placement caps, unique reward event IDs, and reward/wallet ledgers.
- Added tests for unavailable mock behavior, unverified claim rejection, signed completion, full lifecycle, invalid signatures, callbacks before start, and duplicate claims.
- Added `docs/PHASE2_REWARDED_AD_FLOW.md`.

## Static verification performed in this environment

- Python syntax compilation: **41/41 backend Python files PASS** before the final test additions; changed backend/test files were also compiled after edits.
- Static source checks: **PASS** (no client-side ad-completion flag; backend claim requires provider-verified status).
- ZIP integrity: verified after packaging.

## Runtime verification not performed

This sandbox does not have Django, Django REST Framework, or psycopg installed, and no live PostgreSQL/Docker runtime is connected. Therefore the Django test suite, database transaction behavior, and frontend production build have not been executed here. Run the project commands in the deployment environment before treating Phase 2 as fully runtime-verified.

## Provider status

The archive intentionally has no real ad network credentials or vendor SDK. With `AD_PROVIDER=mock`, ads are unavailable and no reward can be issued from an ad click. A live provider is not claimed as integrated. Configure a vendor adapter and webhook secret in staging to verify the live provider path.

## Windows/Docker verification commands

Run from the extracted project root after taking a file backup and confirming the intended backend container/database:

```powershell
docker exec awa-backend-norevive-v2 python manage.py check
docker exec awa-backend-norevive-v2 python manage.py test core.tests_phase2_ads --verbosity=2
docker exec awa-backend-norevive-v2 python manage.py test --verbosity=2
```

Then run the frontend production build from `frontend`:

```powershell
npm ci
npm run build
```

Before applying migrations to a persistent database, inspect the migration state first:

```powershell
docker exec awa-backend-norevive-v2 python manage.py showmigrations core
docker exec awa-backend-norevive-v2 python manage.py migrate --plan
```

Do not remove Docker volumes or reset/restore PostgreSQL as part of Phase 2 verification.
