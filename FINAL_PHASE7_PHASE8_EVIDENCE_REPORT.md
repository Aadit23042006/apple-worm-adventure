# AWA — Phase 7 & Phase 8 Final Verification Evidence

**Inspected archive:** `AWA FULL.zip`  
**Inspection date:** 6 November 2026  
**Scope:** Phase 7 authentication/password-reset and Phase 8 accessibility/regression/sign-off  
**Safety:** No database, Docker volume, live service, or production data was accessed or modified.

## Executive verdict

**NOT 100% company-verified yet.** The uploaded release contains the Phase 7 and Phase 8 implementation, and the static audit passes. Runtime checks could not all be completed in this execution environment. This report distinguishes checks actually executed from checks merely present as test cases.

## Results actually executed

| Check | Result | Evidence / reason |
|---|---|---|
| ZIP integrity | PASS | Original archive opened and `ZipFile.testzip()` returned no corrupt entry; 158 entries inspected |
| Phase 7/8 static audit | PASS | `scripts/verify_phase7_8.py`: 27/27 checks passed |
| Backend Python syntax | PASS | `python -m compileall -q backend` completed successfully |
| Django system check | BLOCKED | `backend/manage.py check` could not start: `ModuleNotFoundError: No module named 'django'` |
| Frontend dependency install | BLOCKED | `npm ci --no-audit --no-fund` did not complete within the available execution window |
| Frontend production build | FAIL/BLOCKED | `npm run build` stopped at TypeScript: `TS2688: Cannot find type definition file for 'vite/client'`; dependency install was incomplete |
| Full Django backend tests | NOT RUN | Django runtime/dependencies unavailable |
| Phase 7 auth tests | NOT RUN | Django runtime unavailable; 8 test methods are present in `core/tests_phase7_auth.py` |
| Reward-flow integration tests | NOT RUN | Django runtime unavailable; 7 test methods are present in `core/tests_phase2_ads.py` |
| Anti-cheat regression tests | NOT RUN | Docker is unavailable in this environment; 9 test methods are present across step 3–7 files |
| Desktop browser acceptance | NOT RUN | No running built application/API was available |
| Mobile browser acceptance | NOT RUN | No running built application/API was available |
| Final company sign-off | PENDING | Required runtime/browser evidence is outstanding |

## Phase 7 — implementation inspection

The uploaded source includes:
- Registration, login, refresh, logout, `/me`, email verification and password-reset API routes.
- Frontend forgot-password entry and reset-password route/form.
- Hashed, expiring, single-use reset token handling in the backend.
- Session/API-token invalidation after successful reset.
- `core/tests_phase7_auth.py` with 8 runtime test methods covering login/refresh/logout, expired refresh, generic reset request, valid/invalid/expired reset tokens, reused token handling via the valid-token test flow, and email verification.

**Phase 7 verdict:** Implementation and static audit present; runtime test execution and browser acceptance are still required.

## Phase 8 — implementation inspection

The uploaded source includes:
- `prefers-reduced-motion` CSS rules.
- Keyboard `:focus-visible` styles.
- Skip-to-main-content link.
- Accessible live announcements for status/error messaging.
- Existing test modules for rewarded ads and No-Revive/server-authority regression.

**Phase 8 verdict:** Accessibility implementation is present; production build, full regression, and desktop/mobile acceptance remain unverified.

## Required Windows verification sequence

Run from the extracted release root, with dependencies installed and the project configured to use an **isolated disposable test database**:

```powershell
# 1. Frontend clean install and production build
Push-Location .\frontend
npm ci
if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed" }
Pop-Location

# 2. Django system check
python .\backend\manage.py check
if ($LASTEXITCODE -ne 0) { throw "Django system check failed" }

# 3. Phase 7 authentication/password-reset tests
python .\backend\manage.py test core.tests_phase7_auth --verbosity=2
if ($LASTEXITCODE -ne 0) { throw "Phase 7 tests failed" }

# 4. Rewarded-ad lifecycle integration tests
python .\backend\manage.py test core.tests_phase2_ads --verbosity=2
if ($LASTEXITCODE -ne 0) { throw "Reward-flow tests failed" }

# 5. Full backend suite
python .\backend\manage.py test --verbosity=2
if ($LASTEXITCODE -ne 0) { throw "Full backend suite failed" }

# 6. Anti-cheat/server-authority regression
python .\backend\manage.py test `
  core.test_anticheat_step3 `
  core.test_anticheat_step4 `
  core.test_anticheat_step5 `
  core.test_anticheat_step6 `
  core.test_anticheat_step7 `
  --verbosity=2
if ($LASTEXITCODE -ne 0) { throw "Anti-cheat regression failed" }
```

Before running Django tests, verify `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_DB`, and test database permissions. Django's test runner creates a separate test database; do not point the project at the recovered production database for manual integration testing. Never use `docker compose down -v`, remove volumes, or apply migrations to the recovered database during this verification.

## Browser acceptance required

On desktop and a narrow mobile viewport, test:
1. Register a new account; verify email; ensure login is blocked before verification and succeeds afterward.
2. Existing account login, `/auth/me`, refresh/session restore and logout.
3. Password reset request with known and unknown email; responses should not disclose account existence.
4. Valid reset succeeds; invalid/expired/reused token fails; old password no longer works; previous sessions are revoked.
5. Tab/Shift+Tab order, visible focus, and skip link.
6. OS reduced-motion preference disables non-essential animation/transitions and smooth scrolling.
7. Reward flow never grants before signed provider verification; duplicate claim does not duplicate ledger/reward.
8. No-Revive failure remains permanent; achievements, leaderboard empty/error states, Explore Features anchor and UTF-8 text render correctly.

## Phase tracker

| Phase | Current evidence status |
|---|---|
| 1 — Audit & Safe Baseline | Audit/baseline recorded; not a full product-fix sign-off |
| 2 — Rewarded Advertisement Flow | Implementation present; runtime/provider tests pending |
| 3 — Achievements Navigation | Implementation present; build/browser/API tests pending |
| 4 — Explore Features | Implementation present; build/browser tests pending |
| 5 — Leaderboard & Achievements Empty States | Implementation present; Django/account/API tests pending |
| 6 — Emoji & Text Encoding | Static encoding checks recorded; browser rendering pending |
| 7 — Authentication & Password Reset | Implementation + 27/27 static checks; runtime/browser tests pending |
| 8 — Accessibility & Full Regression | Accessibility implementation present; build/full regression/browser tests pending |

**Final status: Phase 7/8 implementation is present, but overall Phase 1–8 company compliance is not yet 100% evidenced.**
