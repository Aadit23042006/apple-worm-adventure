# AWA — Phase 7 + Phase 8 Implementation & Verification Report

**Release:** Phase 7 + Phase 8 update on the Phase 5/6 project baseline  
**Database/schema changes:** None  
**Original database and Docker volumes:** Not accessed or modified

## Phase 7 — Authentication & Password-Reset Audit

### Company requirement audit

The supplied VELoop PDF section **84. AUTHENTICATION** names registration, login, current-user (`/me`), logout, JWT, bcrypt, secure cookies where appropriate, and protected routes. Password reset is not named as a mandatory endpoint in that section. Therefore, a missing reset UI by itself is not a failure against the inspected company checklist.

The source project already had backend email verification, refresh sessions, password reset request/confirm endpoints, hashed reset tokens, expiry, single-use handling, and credential invalidation. However, the reset email linked to `/reset-password/` while the frontend did not provide that route or form. This release connects that existing flow rather than adding a new database design.

### Implemented

- Added visible **Forgot password?** entry point to the login form.
- Added generic password-reset request feedback (does not reveal whether an email exists).
- Added `/reset-password/?token=...` frontend route and new-password/confirmation form.
- Added frontend password match validation and backend password policy remains authoritative.
- Removes reset token from the address bar after reading it into component state.
- Preserved email verification UX and existing registration/login flow.
- Unverified registration no longer leaves access/refresh credentials in browser storage.
- Added `backend/core/tests_phase7_auth.py` for registration + email verification, pre-verification login rejection, post-verification login, valid/expired email tokens, login/me/refresh/logout, expired refresh sessions, generic unknown-email reset response, valid/invalid/expired/reused reset tokens, and revocation of old credentials after password reset.

### Existing server protections retained

- Refresh token is stored as a SHA-256 digest server-side, has an expiry, and is revocable.
- Email verification token is hashed and expires.
- Password reset token is hashed, expires after one hour, and is single-use.
- Successful password reset invalidates other reset tokens, deletes API auth tokens, and revokes refresh sessions.
- Password reset request response is generic to limit account enumeration.

## Phase 8 — Accessibility, Regression & Sign-Off

### Implemented

- Strengthened `prefers-reduced-motion: reduce` to disable animation and transitions and disable smooth scrolling.
- Added a skip-to-main-content link.
- Added visible keyboard `:focus-visible` outlines, including form inputs.
- Added polite/urgent live announcement semantics for global status and error messages.
- No database migration or schema change was introduced.
- Existing No-Revive and server-authoritative reward code was not edited in this phase.

### Verification evidence available in this packaging environment

| Check | Result |
|---|---:|
| Phase 7/8 static audit | **27/27 PASS** |
| Python backend syntax compilation (`compileall`) | **PASS** |
| Django `manage.py check` | Not run — Django/DRF/PostgreSQL dependencies unavailable here |
| New Phase 7 Django runtime tests | Added, not run — Django runtime unavailable |
| Full Django backend suite | Not run — Django runtime unavailable |
| Anti-cheat regression suite | Not run — Docker runtime unavailable here |
| Frontend production build | Not run — `npm ci` did not complete before environment timeout |
| Desktop/mobile browser acceptance | Pending — requires user's browser/runtime |
| Reduced-motion OS preference verification | Static CSS check passed; browser test pending |

**Do not interpret static checks or syntax compilation as a successful runtime test.** Phase 8 final sign-off remains pending until the commands below and browser acceptance checks pass.

## Run on Windows PowerShell

From the extracted project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\verify_phase7_8.ps1
```

This runs the 27 static checks, installs frontend dependencies, and runs the production build.

Then, with the extracted source connected to an **isolated disposable test database** (not the recovered production database):

```powershell
python backend\manage.py check
python backend\manage.py test core.tests_phase7_auth --verbosity=2
python backend\manage.py test --verbosity=2
python backend\manage.py test core.test_anticheat_step3 core.test_anticheat_step4 core.test_anticheat_step5 core.test_anticheat_step6 core.test_anticheat_step7 --verbosity=2
```

Do not run these commands through an old container until its bind mount is confirmed to point to this extracted release. Never use `docker compose down -v`, delete database volumes, or run migrations against the recovered database for this verification.

## Browser acceptance checklist

1. New account: registration, verification email, login blocked before verification, login allowed after verification.
2. Existing account: login, `/auth/me`, reload/session restore, logout.
3. Reset request: known and unknown email addresses show the same generic UI response.
4. Reset confirmation: valid link succeeds; invalid, expired, and reused links fail; old password fails and new password succeeds; previous sessions are revoked.
5. Keyboard: Tab and Shift+Tab reach controls in order, focus indicator is visible, skip link works.
6. Reduced motion: enable OS reduced-motion preference and confirm game animations/transitions stop and scrolling is not smooth.
7. Repeat at desktop and narrow mobile widths.
8. Regression: test rewarded ad lifecycle, duplicate-claim protection, No-Revive permanent failure, achievements, leaderboard empty/error states, Explore Features anchor, and UTF-8 rendering.

## Overall phase tracker (based on evidence currently available)

| Phase | Implementation status | Runtime/company verification |
|---|---|---|
| 1 — Audit & Safe Baseline | Audit/baseline work recorded | Not a full product-fix sign-off |
| 2 — Rewarded Advertisement Flow | Implemented in supplied release | Pending runtime/provider tests |
| 3 — Achievements Navigation | Implemented in supplied release | Pending build/browser/API tests |
| 4 — Explore Features | Implemented in supplied release | Pending build/browser tests |
| 5 — Leaderboard & Achievements Empty States | Implemented in supplied release | Pending Django/account/API tests |
| 6 — Emoji & Text Encoding | Implemented in supplied release | Pending build/browser rendering |
| 7 — Authentication Audit | Implementation + 27 static checks | Django runtime and browser tests pending |
| 8 — Accessibility & Final Regression | Accessibility fixes + regression plan | Full regression and browser sign-off pending |

**Overall verdict:** Phase 7 implementation is updated; Phase 8 accessibility implementation is updated. The project is **not yet fully company-verified / 100% signed off** because runtime tests, production build, anti-cheat regression, and desktop/mobile browser acceptance remain outstanding.
