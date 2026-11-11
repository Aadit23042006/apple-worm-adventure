# Apple Worm Adventure — Phase 2 Rewarded Advertisement Flow

## Implementation status

The Phase 2 code changes are implemented in this isolated working copy. The original uploaded archive and live Docker/PostgreSQL environment were not modified.

### Requirement mapping

| Task | Implementation | Status |
|---|---|---|
| 1. Provider abstraction | Added `core/ad_providers.py`; provider adapter is pluggable; default mock is explicitly unavailable and never completes an ad | Implemented |
| 2. Placement flow | Existing reward placements use one authenticated opportunity/request/status/claim flow; existing session binding is preserved | Implemented |
| 3. Lifecycle states | `OFFERED → REQUESTED → AD_STARTED → AD_COMPLETED → VERIFYING → VERIFIED → GRANTED` recorded in lifecycle metadata; durable current state stored in `AdOpportunity.status` | Implemented |
| 4. No reward on click | Frontend no longer calls claim immediately after creating an opportunity; claim waits for backend `VERIFIED` status | Implemented |
| 5. Backend verification | Provider callback requires `eventStatus=COMPLETED`, HMAC-SHA256 signature, matching provider reference, and an opportunity already in `AD_STARTED` | Implemented |
| 6. Economy protections | Existing ownership/session checks, cooldown, daily quota, per-level caps, unique event IDs, row locks, reward ledger and wallet transaction remain in place; opportunity becomes `GRANTED` transactionally with reward ledger creation | Implemented |
| 7. UI states | Explicit `AD UNAVAILABLE`, `COOLDOWN`, `LIMIT REACHED`, pending-verification and successful-grant notices | Implemented |

## Critical provider limitation

The archive does not contain a real advertising vendor SDK, vendor account credentials, or provider-side webhook configuration. The default `AD_PROVIDER=mock` is therefore intentionally unavailable. It does not synthesize ad completion, call the completion callback, or grant a reward. A real vendor adapter must be configured before live ad inventory can be shown. The code does not claim that a real ad provider is integrated.

## Added/changed files

- `backend/core/ad_providers.py` (new provider abstraction)
- `backend/core/models.py` (expanded opportunity lifecycle choices)
- `backend/core/migrations/0012_ad_opportunity_lifecycle.py` (migration)
- `backend/core/views.py` (provider request, signed callback verification, status endpoint, verified-only claim, grant state)
- `backend/core/urls.py` (request/status routes)
- `backend/config/settings.py` (adapter configuration)
- `backend/core/tests_phase2_ads.py` (new security/idempotency regression tests)
- `backend/core/test_anticheat_step7.py` (fixture updated to use the new verified state)
- `backend/core/tests_phase5_6.py` (verified fixture states)
- `frontend/src/App.tsx` (no immediate claim; provider status polling and UI feedback)
- `.env.example` (provider adapter configuration)
- `docs/REWARDED_AD_FLOW.md` (provider contract and deployment instructions)

## Verification performed in this environment

- Python syntax compilation for all changed backend Python files: PASS.
- Static assertions for mock non-completion, signed callback gate, verified-only claims, unique reward event ledger: PASS (see separate audit script/result).
- Django `manage.py check` and Django test execution: NOT RUN — Django is not installed in this isolated runtime and Docker is not available here.
- Frontend production build: NOT RUN — archived `node_modules` contains platform-specific dependencies; `npm run build` fails with `vite: Permission denied`, and direct TypeScript invocation reports missing `@typescript/typescript-linux-x64`.

## Sign-off decision

**Implementation work: complete in the patch. Phase 2 final sign-off: PENDING runtime verification.** Run the migration, new Phase 2 tests, Phase 5/6 regression tests, full backend suite, and frontend production build in the user's Windows/Docker environment. Then configure and test a real provider adapter/webhook before describing ads as live. Do not mark Phase 2 100% verified until those checks pass.
