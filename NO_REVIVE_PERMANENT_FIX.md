# No-Revive Level Enforcement — Permanent Fix

## Root cause
The game already defines a required `no_revive` objective for difficulty 7+ levels (levels 37–60), and completion correctly checks `revives == 0`. However, the rewarded-ad `REVIVE` path previously used only the global `maxRevivesPerLevel=1` economy setting, so a player could still create/claim a Revive on a no-revive level.

## Permanent fix
- Added server-authoritative `level_revive_limit(level_number)`.
- Required `no_revive` objective forces the effective revive limit to `0`.
- `REVIVE` ad opportunities are rejected before creation on no-revive levels.
- Direct `REVIVE` reward claims are also rejected, providing defense-in-depth against bypassing the opportunity endpoint.
- Added migration `0011_no_revive_level_policy.py` to persist `maxRevivesPerLevel: 0` in the JSON config of every active level whose required objectives contain `no_revive`.
- Frontend no longer shows the “Watch Ad · Revive” button on no-revive levels and displays a clear disabled message instead.
- Added regression tests for configuration, opportunity rejection, and direct claim rejection.

## Scope
No change to the global economy value (`maxRevivesPerLevel=1`) for normal levels. Existing revive-enabled levels retain their current behavior.


## Phase 6 Level 37 evidence provisioning

Normal gameplay progression remains sequential: completing level N unlocks N+1.
Level 37 is not globally unlocked and the `/api/games/start/` endpoint still rejects locked levels.

For local Phase 6 evidence only, the repository includes `provision_phase6_level`. It is explicitly opt-in via `PHASE6_TEST_PROVISIONING_ENABLED=true`, requires a `phase6*` test-account username, and only changes that account's `PlayerProgress.unlocked` flag. It never marks a level completed and cannot be used unless the environment explicitly enables the feature.

Example inside the backend container:

`PHASE6_TEST_PROVISIONING_ENABLED=true python manage.py provision_phase6_level --username phase6unlock1987039018 --level 37`

After provisioning, use the normal `/api/games/start/` API and perform the Level 37 gameplay/no-revive evidence test.
