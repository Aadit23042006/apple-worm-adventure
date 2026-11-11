# Apple Worm Adventure — Phase 2 Runtime Fixes

This patch preserves the existing Phase 1 backend/authentication implementation and adds only Phase 2/runtime reliability fixes in the frontend.

## Fixed

- Local browser API routing is now resilient: when the app is opened on `localhost` or `127.0.0.1`, API calls use the local Django backend on port `8002`, with the `/api` Nginx proxy retained as a fallback.
- Login, session restore, level loading, game sessions and gameplay requests therefore do not depend on a stale HTTPS `/api` URL.
- Login stores both the access token and rotating refresh token before loading the level map.
- Level loading can explicitly use the newly issued access token immediately after login.
- Automatic access-token refresh remains concurrency-safe and preserves the existing Phase 1 refresh-token flow.
- Completed levels are locked against further movement after the completion state is reached.
- Undo history is recorded only after a valid move, so failed collision attempts do not create invalid undo states.
- Restart creates a fresh game state/session as before.
- Rewarded Hint now produces an actionable safe direction instead of only recording a reward.
- Background WebAudio music is available from the gameplay screen and starts after entering a level; it can be toggled on/off.
- Gameplay feedback animations were added for the worm head, worm body, apples and portal.
- Login/register password fields now use appropriate browser autocomplete attributes.

## Phase 1 preservation

No backend Phase 1 authentication, database, migration, refresh-token, email-verification, password-reset, rate-limit, API-key or production-security implementation was removed or rewritten in this patch.

The existing Docker/Nginx `/api` proxy remains in place for deployment compatibility.
