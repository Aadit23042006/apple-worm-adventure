# Phase 2 + Phase 3 final verification

## Phase 2 — Rewarded Advertisement Flow

The project contains the provider adapter boundary, fail-closed mock provider, signed provider callback, provider-reference matching, AD_STARTED precondition, verified-only claim guard, idempotent reward ledger, and the seven-state lifecycle audit history. The default mock is intentionally unavailable and cannot simulate playback or grant rewards.

Seven focused Django tests are present in `backend/core/tests_phase2_ads.py`:
- mock provider unavailable and no reward
- unverified claim rejected
- signed callback for started session
- full lifecycle and single grant
- invalid signature rejected
- callback before ad start rejected
- duplicate claim does not create a second reward

**Important provider boundary:** a real ad network is not configured in this package. A production provider cannot be declared integrated until its adapter, webhook secret, provider dashboard configuration, and a staging callback have been exercised. The mock's unavailable response is the correct safe local behavior.

## Phase 3 — Achievements Navigation

- Authenticated navigation shows the Achievements button.
- It opens the existing Achievements `DataPage` and preserves the `/api/achievements/` request and response shape.
- The page has a visible Back to Game / Back to Dashboard control.
- Loading, empty, error, and retry states are rendered.
- Responsive navigation and back-button rules exist at 850px and 520px breakpoints.
- Added backend API integration tests in `backend/core/tests_phase3_achievements.py` for authentication, achievement payload, and unlocked/locked state.

## Verification run in this build environment

- Python `compileall` across backend: PASS.
- Source/static checks: PASS.
- ZIP archive integrity: PASS after packaging.
- `npm ci`: did not complete within the available execution window; install left incomplete dependencies.
- `npm run build`: BLOCKED because `vite/client` is not installed.
- Django tests: NOT RUN because Django/DRF/PostgreSQL dependencies and a Docker/PostgreSQL runtime are not available in this build environment.
- Desktop/mobile browser checks: NOT RUN; no browser runtime attached.

Do not mark either phase 100% runtime-verified until the commands and browser checklist below pass in the user's isolated test environment.

## Run on Windows PowerShell

Extract the ZIP to a NEW test folder, then open PowerShell in the extracted project root. Confirm that the backend container is mounted to this exact extracted copy and uses a disposable test database before running backend tests. The script refuses to continue until the mount and test database are confirmed:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\verify_phase2_phase3.ps1
```

Do not point the test container at the recovered/production database. Do not run `docker compose down -v`, remove volumes, or apply migrations to a persistent database as part of this verification.

## Browser acceptance checklist

Test at desktop width (e.g. 1366×768) and mobile width (e.g. 390×844):

1. Sign in; verify Achievements is visible in the authenticated header.
2. Open Achievements; verify the page title and loading indicator.
3. With API data, verify unlocked and locked records render correctly.
4. With an empty response, verify the empty-state message is shown (not an endless Loading state).
5. With the API offline/401/500, verify an error and Try again action appear.
6. Select Back to Game when a game is active; otherwise Back to Dashboard. Verify the destination.
7. At mobile width, verify the Achievements and Back buttons remain visible, tappable, and do not cause horizontal overflow.
8. Repeat navigation after refresh and verify there is no stale or duplicated page state.

## Final status

Implementation and test coverage have been updated. **100% completion is not certified yet** because the production build, Django runtime suite, desktop/mobile browser acceptance, and real-provider staging verification remain unexecuted in this environment.
