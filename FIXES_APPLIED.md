# Apple Worm Adventure — Runtime Fixes Applied

This build fixes the runtime issues found during Docker verification.

## Fixed

- Added the missing `core` migration `0004` for `PlayerProfile.coins` and `PlayerProfile.total_score`, plus the model-state metadata changes.
- Fixed local authentication behavior so development accounts can be used immediately while production can require email verification with `EMAIL_VERIFICATION_REQUIRED=true`.
- Added clearer inactive-user login handling.
- Fixed level loading error handling and retry UI.
- Added continuous backend health checking instead of a one-time offline check.
- Switched the containerized frontend to same-origin `/api` requests through Nginx, avoiding browser-to-container URL/CORS problems.
- Passed `VITE_GAME_NAME` into the Vite Docker build so the configured game name is available at build time.
- Fixed level completion requests so the complete game state is sent to server-side validation.
- Added real client-side undo state restoration.
- Restarting a level now creates a fresh game session.
- Added server-side reward cooldown/limit checks and session-aware reward handling.
- Added server-validated revive state restoration.
- Added double-score and double-coins reward flows after completion.

## Verification performed

- Python backend files pass `py_compile`.
- Docker Compose YAML parses successfully.
- The frontend source was syntax-checked with TypeScript using temporary module stubs; the remaining local check limitation is that the uploaded source archive does not contain installed npm dependencies.

## Local startup

Keep your existing local `.env` file. Do not replace it with secrets from this archive.

Then rebuild:

```cmd
docker compose up -d --build
```

Check:

```cmd
docker compose ps
docker compose exec backend python manage.py migrate
```

Open:

```text
http://localhost:5174
```

## Final integrity hardening

- Added server-persisted checkpoint history and a dedicated undo endpoint.
- Added exact one-move server transition validation for movement, growth, apple removal, and score progression.
- Added deterministic initial-state validation so clients cannot start a session from a fabricated board state.
- Completion now locks the session row, validates the final move from the trusted checkpoint, and returns HTTP 409 for an already-used session.
- Frontend undo now restores the server checkpoint instead of only changing React state.
- Frontend API calls use the same-origin `/api` proxy; direct browser calls to port 8002 are no longer required.
- Backend healthcheck and frontend dependency ordering were added to Docker Compose.
- The distributable archive excludes the local `.env` file and its secrets.

- **Phase 4 cooldown hardening:** `claim_reward()` now independently enforces the configured rewarded-ad cooldown and calendar-day granted-reward cap using `RewardTransaction.created_at`. This closes the bypass where a fresh ad opportunity could be claimed immediately. Exact duplicate event retries remain idempotent.


## Phase 5 permanent start-session fix

- Fixed `POST /api/games/start/` to generate the canonical initial state server-side when `state` is omitted.
- Added `level_id` compatibility so manual/API clients using the alternate field do not fail before validation.
- Kept strict validation for any client-supplied state to preserve anti-cheat protections.
- Returned the server-authoritative state in the start response.
- Updated the React client to submit only the level number and render the returned authoritative state.
- Added regression tests for canonical start, `level_id` compatibility, and tampered initial-state rejection.

## Permanent Phase 5 Step 8 economy-ledger fix

- Level-completion coin rewards are now recorded in the unified `RewardTransaction` ledger as `LEVEL_COMPLETION` / `COINS`.
- Existing `LEVEL_REWARD` wallet transactions are backfilled into the reward ledger by migration `0007_level_completion_reward_ledger`.
- Rewarded-ad cooldown and daily-ad quota count only rewarded-ad placements, so deterministic level-completion rewards cannot consume ad limits.
- `/api/economy/wallet/` exposes both verified ad rewards and level-completion rewards through the `rewards` ledger.
- Level-completion reward ledger creation is idempotent and tied to the session.
