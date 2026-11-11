# Checkpoint "Invalid token." — root cause and fix

## Where the message comes from
`Invalid token.` is DRF `TokenAuthentication` saying the access-token key is not in the
database. The checkpoint view itself (ownership, ACTIVE status, move validation) is correct
and was not changed. The defect is in how the frontend handled token loss/rotation.

## Root-cause defects (all in the frontend token lifecycle)
1. **Stale captured token.** `saveCheckpoint(session, token, ...)` sent the token captured when
   the move was made, not the latest stored token.
2. **Refresh failure left a dead session on screen.** On failed refresh, `request()` wiped
   localStorage but React state (`token`, `player`) stayed set, so every later move kept
   posting a dead token and showed "Checkpoint save failed: Invalid token."
3. **Refresh wiped credentials on transient errors.** Any non-OK refresh response (429
   throttle, 5xx, proxy hiccup) deleted both tokens, turning a temporary glitch into a logout.
4. **No cross-tab sync.** Logout/login/refresh in another tab changed localStorage but not
   this tab's state.

Backend design facts that make (1)–(4) bite: access tokens are one DRF `Token` per user
(non-expiring), `/auth/refresh/` returns that same key, and logout / password reset delete it
and revoke all refresh sessions (logout is effectively "all devices"). Logout in any tab,
device or test run therefore invalidates every other live session's token.

## Fix
- New `frontend/src/authClient.ts` (request + refresh logic moved out of `App.tsx`, same API).
  - 401 -> check for a newer stored token -> otherwise ONE shared refresh -> ONE retry. No loops.
  - Refresh rejected (400/401/403) or retry still 401 -> clear storage, emit
    `veloop:session-expired`, throw `AuthExpiredError`.
  - Refresh unreachable / 429 / 5xx -> tokens kept, retryable error.
  - Successful refresh emits `veloop:token-updated`.
- `App.tsx`: listens for those events and the `storage` event (login screen + clear message on
  expiry; token state follows refresh and other tabs). `saveCheckpoint` uses
  `getStoredToken() || checkpointToken`.
- Backend: **no behaviour change** (no auth weakened, no checkpoint checks removed).

## Tests
- Backend `core/tests_checkpoint_auth.py`: 14 tests (acceptance items 1-5, 10-14, logout,
  refresh failure, account switching).
- Frontend `src/authClient.test.ts` (vitest): 12 tests (item 6, stale-token handling,
  refresh failure vs transient failure, no retry loop, concurrent refresh sharing, item 15 at
  client level). Run: `cd frontend && npm test`.
- Full backend suite after change: 105/105 (91 existing + 14 new). Evidence: `EVIDENCE/runtime/`.

## NOT covered by automated tests yet (needs a real browser)
Acceptance items 7, 8 (rapid keyboard/touch ordering), 9 (reload restore), and the UI side of
15 / 14. The checkpoint serialisation chain lives inside `App.tsx` and must be exercised with
Playwright or manually.

## Known limitation / recommended follow-up
Single shared token per user means logout is global. Moving to per-session access tokens
(new model + migration) would remove that, but changes login/logout semantics, so it was not
done silently. Also note the user throttle is 240/min: very rapid play with one checkpoint per
move can reach it (that surfaces as HTTP 429, not "Invalid token").

## Addendum 2026-11-10 — cross-device logout (actual recurring trigger)
Logout revoked every refresh session, so any logout elsewhere permanently killed other live sessions. Logout now
revokes only the caller's own refresh session when it is supplied (legacy revoke-all otherwise). 6 new backend tests
(fail on old code), real-browser evidence in EVIDENCE/FINAL_REGRESSION/. See FINAL_REGRESSION_REPORT.md.
