# Phase 7 + Phase 8 — Authentication Audit, Accessibility and Regression

## Company-source interpretation

The VELoop assignment PDF, section **84. AUTHENTICATION**, explicitly lists:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- JWT, bcrypt, secure cookies where appropriate, and protected routes.

The inspected section does **not** list password reset as a mandatory endpoint or completion criterion. Therefore, the absence of a password-reset UI alone is not treated as a company requirement failure.

The project already contained password-reset request/confirm endpoints, a hashed token model, one-hour expiry, single-use enforcement, password validation, and session invalidation. The email helper generated `/reset-password/?token=...`, but the frontend had no route/form for that link. This patch connects the existing backend flow to a visible frontend Forgot Password and Reset Password experience. It does not change the company requirement interpretation.

## Phase 7 changes

- Audited registration, login, current-user, logout, email verification, refresh, and reset endpoints.
- Preserved the existing registration/login/token architecture and email verification requirement.
- Added a Forgot Password entry point on the login screen.
- Added generic reset-request messaging to avoid disclosing whether an email is registered.
- Added reset-link route handling and new-password/confirmation form.
- Removes the reset token from the browser address bar after reading it into component state.
- Existing backend reset logic hashes tokens, expires them after one hour, permits one successful use, validates the new password, invalidates other reset tokens, deletes API tokens, and revokes refresh sessions.
- Added `backend/core/tests_phase7_auth.py` for login/me/refresh/logout, expired refresh, generic unknown-email response, valid/invalid/expired/reused reset tokens, credential revocation, and valid/expired email verification.

## Phase 8 changes

- Existing `prefers-reduced-motion` support was retained and strengthened to disable animations and transitions and turn off smooth scrolling.
- Added a skip-to-main-content link.
- Added visible keyboard `:focus-visible` outlines, including form inputs that previously suppressed outlines.
- Added accessible live announcement semantics to global status/error messages.
- Preserved the existing gameplay, server-authoritative reward logic, No-Revive enforcement, and data/API behavior; no database schema or migration changes were introduced.

## Local verification

From the extracted project root on Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\verify_phase7_8.ps1
```

This runs static checks and the frontend dependency install/production build.

## Backend verification (isolated test database only)

Run these only where the container/source is confirmed to be this extracted release and Django is configured to create/use a disposable test database. Do not point test runs at the recovered production database or delete Docker volumes.

```powershell
python backend\manage.py check
python backend\manage.py test core.tests_phase7_auth --verbosity=2
python backend\manage.py test --verbosity=2
python backend\manage.py test core.test_anticheat_step3 core.test_anticheat_step4 core.test_anticheat_step5 core.test_anticheat_step6 core.test_anticheat_step7 --verbosity=2
```

If test modules/classes have changed in the selected branch, use the current test labels after inspecting `backend/core/`.

## Browser acceptance checks

Use a new test account and an existing test account:

1. Register with email verification enabled; confirm the email link verifies the account; try login before and after verification.
2. Log in, open dashboard/game, refresh the browser, and confirm session restoration. Test expired and revoked refresh tokens through API tests.
3. From Login, open Forgot Password. Submit both a registered and unregistered email; the UI should show the same generic response.
4. Open the email reset link. Submit a valid new password; confirm login with the new password and rejection of the old password. Repeat with invalid, expired, and reused links through backend tests.
5. Use Tab/Shift+Tab through the page; confirm focus remains visible and the skip link works.
6. Enable the operating system's reduced-motion preference; confirm animated game effects stop and anchor scrolling is not smooth.
7. Repeat at desktop and narrow mobile widths.
8. Re-test rewarded ads, No-Revive failure, achievements, leaderboard empty/error states, Explore Features anchor, and UTF-8 rendering.

## Verification status at package creation

- Source edits and static audit: to be run by `scripts/verify_phase7_8.py` (record its result separately).
- Python syntax compilation: recorded in the release report.
- Django runtime tests/system checks: not run in this packaging environment because Django/DRF/PostgreSQL Python dependencies and an isolated database are not available here.
- Frontend production build: not run here; dependency installation did not complete within the available environment timeout. Run the PowerShell verifier on the user's Windows machine.
- Browser acceptance tests: require the user's browser/runtime and remain pending.

Do not declare Phase 8 full sign-off until the runtime and browser evidence above passes.
