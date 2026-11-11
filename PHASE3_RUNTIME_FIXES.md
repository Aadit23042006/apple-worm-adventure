# Apple Worm Adventure — Phase 3 Permanent Runtime Fixes

## What was hardened

- Added `GET /api/games/active/` to restore the newest active game session after browser refresh/reopen.
- Active sessions are restored from the server checkpoint, not from untrusted browser-only state.
- Starting a new attempt for the same level safely marks an older active attempt as `ABANDONED`.
- Checkpoints are now saved after every valid move from the frontend.
- Checkpoint requests are serialized so rapid keyboard/touch input cannot arrive out of order.
- Checkpoints validate deterministic level geometry, portal, apples, obstacles, worm bounds, duplicate segments, and contiguous worm segments.
- Completion validation uses the server's deterministic level score and rejects client-invented scores.
- Completion requires an active session to advance beyond its last checkpoint and requires all apples to be collected with the worm at the portal.
- Achievement records are automatically unlocked when their documented thresholds are reached.
- Existing authentication, refresh-token, API-key, economy, leaderboard, wallet, reward, and Phase 1/2 functionality is retained.

## Important

The local `.env` file is intentionally not included in the fixed archive. Keep the existing local `.env` from your working project.

## Verification available in this archive

- Python backend source passes `py_compile`/`compileall`.
- Frontend application TypeScript (`tsconfig.app.json`) passes `tsc --noEmit`.
- Docker runtime verification must be performed on the target machine because Docker is not available in this build environment.
