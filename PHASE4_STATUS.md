# Apple Worm Adventure — Phase 4 / Final Product Status

Implemented through the final phase against the VELoop Full Stack requirements.

## Gameplay
- 60 deterministic grid levels
- worm movement: arrows/WASD/touch controls
- apples, growth, body/wall/obstacle collision
- portal validation after all apples
- score, moves, stars, restart, undo affordance, hints
- level unlock/progress persistence
- responsive UI, animation-ready feedback, WebAudio effects

## Full stack
- authentication and persistent player profile
- game sessions, checkpoints, completion validation
- player progress, game history/session records
- leaderboard and achievements
- PostgreSQL-backed wallet and ledgers
- server-side completion/reward validation

## VELoop economy
- named ad placements
- ad opportunity -> completion -> verified/idempotent reward ledger flow
- revive, hint, extra moves, booster, double coins, double score placement support
- configurable reward values/caps/cooldown
- wallet transactions and reward history
- admin economy metrics endpoint

## Bonus product features
- 60 levels (exceeds 50+ requirement)
- daily/economy configuration foundation
- admin economy metrics
- achievements and leaderboard
- provider-neutral rewarded-ad abstraction at API contract level

## Verification
- Python compileall and JSON/TypeScript source sanity checks performed.
- Docker/browser/PostgreSQL runtime execution depends on the user's machine/CI environment because Docker and npm dependency installation were unavailable in the execution environment.

- Cooldown hardening: claim-time cooldown and calendar-day granted-reward limit are enforced server-side.

## Phase 4 Step 5 permanent hardening
- Added `PlayerProfile.last_reward_claim_at` as the authoritative server-side cooldown anchor.
- Added migration `0006_reward_claim_cooldown`.
- Claim-time cooldown now survives fresh opportunities and concurrent requests.
- Daily limit counts only granted reward transactions.
- Exact duplicate claims remain idempotent.
- Client reward values remain server-calculated.
