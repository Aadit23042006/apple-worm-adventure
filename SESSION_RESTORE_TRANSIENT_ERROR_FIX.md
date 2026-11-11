# Session restore: preserve credentials on transient failures

`frontend/src/App.tsx` no longer clears the access token and refresh token for every failure from `/auth/me/`.

`frontend/src/authClient.ts` distinguishes definitive authentication rejection from temporary network/server failures. A definitive failure emits `SESSION_EXPIRED_EVENT`, which already resets the UI to the login screen. A network error, HTTP 429, or HTTP 5xx must not be converted into a logout by the session-restore catch handler.

The catch handler now displays the actual error and leaves token storage untouched. No backend authentication, checkpoint validation, or session-ownership rule was changed.

Validation in this review:
- Python compileall: PASS (backend unchanged by this correction).
- Static audits: 75/75 PASS.
- Frontend tests/build: NOT RUN after this correction because dependency installation timed out in the available environment. Re-run with the project's Node 24.19.0 environment before release.
