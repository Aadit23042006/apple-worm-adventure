# Step 4 Authentication Fix — 11 November 2026

## Changes applied

1. **Registration → level selection request de-duplication**
   - Removed the second direct `loadLevels(accessToken)` call from the login/register handler.
   - The existing token-state effect now owns the single level-list request.
2. **Avoid redundant auth restore immediately after successful login/register**
   - The login/register response already contains the authenticated player object.
   - The exact newly-issued token is marked so the initial `/auth/me/` restore request is skipped for that token only.
   - Normal page reload and cross-tab token changes continue to use the normal restore path.
3. **Avoid an unnecessary active-game request for a newly registered account**
   - A new account cannot have an active game yet.
   - The initial registration transition skips `/games/active/` once; normal login and page reload still restore an existing active game.
4. **More diagnostic registration E2E test**
   - The test now captures any `/api/levels/` response, including 401/403/5xx, instead of waiting only for HTTP 200.
   - It reports the actual response status and response body when the endpoint fails.
5. **Backend integration regression tests added**
   - Registration token authenticates `/auth/me/`, `/levels/`, and `/games/active/`.
   - Registration refresh token returns a usable access token and can authenticate `/levels/`.
6. **Node engine metadata corrected**
   - `frontend/package.json` and `frontend/package-lock.json` now require Node `>=22.22.2`, matching the minimum declared by the locked jsdom dependency. The available verification runtime was Node 22.16.0.

## Verification performed in this environment

| Check | Result |
|---|---|
| Python syntax compilation for `backend/core/views.py` and `backend/core/tests_phase7_auth.py` | PASS |
| Source-level review of registration, token storage, level loading, session restore, and routes | PASS |
| Fresh Django/PostgreSQL authentication test run | NOT RUN — Docker is unavailable and Django/DRF/PostgreSQL dependencies are not installed; package download is blocked by unavailable network access |
| Frontend `npm ci` | BLOCKED — network timeout; offline retry reports uncached `xmlchars` package |
| Frontend TypeScript/Vite build | NOT RUN — dependencies are incomplete (`vite/client` type definitions unavailable) |
| Vitest authentication unit tests | NOT RUN — Vitest is not installed in the available runtime |
| Playwright browser E2E | NOT RUN — Playwright dependencies/browser and Docker runtime are unavailable |
| Windows Docker deployment / cross-tab real-browser verification | NOT RUN — this environment cannot access the user's Windows Docker/browser session |

## Important status

The source fixes and regression tests are included, but **Step 4 is not certified 100% yet**. The failing browser scenario cannot be truthfully marked PASS until the frontend/backend are run together and the new Django, Vitest, and Playwright checks execute successfully. No source-only inspection can guarantee a permanent fix across all deployments.

## Security handling

The uploaded `.env` file was intentionally excluded from the returned ZIP. Keep real secrets only in your local environment. If the uploaded `.env` contained real production credentials or secrets, rotate them because the original archive included that file.
