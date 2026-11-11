# Final regression report — checkpoint "Invalid token" (session of 2026-11-10)

Environment: Linux sandbox, Python 3.13, Node 22, PostgreSQL 16 (throwaway local instance, NOT your data),
headless Chromium (Playwright). Docker was NOT available here -> all Docker items are NOT TESTED in this session.

## Results actually executed
| Check | Command | Result |
|---|---|---|
| Baseline backend suite (ZIP as received) | `manage.py test core` | 105/105 OK |
| Django system check | `manage.py check` | no issues |
| Migration drift | `makemigrations --check --dry-run` | No changes detected |
| New regression tests vs ORIGINAL code | `manage.py test core.tests_multi_device_logout` | **2 FAIL / 6** (defect reproduced) |
| New regression tests vs FIXED code | same | 6/6 OK |
| Full backend suite after fix | `manage.py test core` | **111/111 OK** (105 + 6 new) |
| Frontend unit tests | `npm test` | 12/12 OK |
| Frontend production build | `npm run build` (tsc app config + vite) | exit 0 |
| Real-browser scenario, fixed backend | `e2e/checkpoint_cross_device_logout.e2e.js per-device` | 4 saves 200 -> other device logs out -> checkpoint 401 -> /auth/refresh 200 -> 4 more saves 200; no error banner; still logged in; HUD Moves 8, Score 170 |
| Real-browser control (old revoke-all behaviour) | same script, `legacy` | checkpoint 401 -> refresh 401 -> "session has expired" + login screen |

## Root cause (established, reproduced)
One shared DRF Token per user. `/auth/logout/` deleted it and revoked ALL refresh sessions, so a logout in any other
tab/device/test run left every other live session with a dead token and nothing to refresh with.
Evidence: tests fail on original code; browser control run shows the end state.
Note: the previous fix (authClient.ts) made the failure graceful but could not prevent it.

## Fix (minimal, backward compatible)
- backend/core/views.py `logout`: optional `refresh_token` in body revokes only that user's matching refresh session;
  absent/unknown token keeps the original revoke-all behaviour. Access token of the logging-out device is still deleted.
  Password reset still revokes everything. No auth check weakened.
- frontend/src/App.tsx `signout`: sends the device's refresh token, `skipRefresh: true`.
- New tests: backend/core/tests_multi_device_logout.py (6).

## Known limitations / NOT verified (do not treat as PASS)
- Logout is still not truly per-device for the *access* token: other devices take one extra 401->refresh round trip.
  Fully removing that needs per-session access tokens (new model + migration) — a design change not made here.
- Throttle 240/min per user can yield HTTP 429 under extremely rapid play (not "Invalid token").
- Console shows one `ERR_TUNNEL_CONNECTION_FAILED`: an external resource blocked by the sandbox proxy; not an app defect,
  but unverified on a normal network.
- `tsc -b` on the root tsconfig reports TS2591 (`process` in vite.config.ts, @types/node absent). Not used by
  `npm run build`, so build is unaffected; left unchanged.
- NOT TESTED this session: Docker/Compose, fresh-install scripts (PowerShell), RUN-ALL-VERIFICATION.ps1, physical
  mobile devices, multi-viewport screenshots (Sections 11), touch controls, level-complete/rewards/game-over browser
  flows, real ad-provider integration (BLOCKED: no credentials), full 127-clause PDF re-traceability, Phase 7/8
  runtime re-verification, security review beyond the logout change.
- Therefore this release is NOT declared RELEASE READY by Section 19 criteria; it is a verified fix for the checkpoint defect.
