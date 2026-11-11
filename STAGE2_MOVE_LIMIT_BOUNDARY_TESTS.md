# Stage 2 — Level 23 move-limit boundary regression

## Scope

This additive regression suite protects Level 23's server-authoritative move-limit boundary. It does not change gameplay logic, authentication, checkpoint ownership, rewards, or existing features.

## Expected contract

- Level 23's generated `move_limit` objective is exactly 116.
- At 116 moves, with all apples collected and the worm at the portal, objective evaluation succeeds and the completion API returns HTTP 200.
- At 117 moves, with the same otherwise-valid checkpoint, objective evaluation fails and the completion API returns HTTP 409. The session remains `ACTIVE`, its stored checkpoint and score remain unchanged, and level progression is not granted.

## Run in the isolated candidate environment

```powershell
docker compose -p awa_candidate_isolated -f .\docker-compose.yml -f .\docker-compose.isolated.yml exec -T backend python manage.py test core.tests_phase5_6.Level23MoveLimitBoundaryRegressionTests -v 2
```

Expected result: 3 tests pass. The Django test runner uses its own temporary test database; it does not mutate the isolated app database or production database.

## Important distinction

The move-limit objective is a completion requirement, not a hard movement lock. A player can continue moving after 116, but the server must reject level completion after the limit is exceeded. The 117-move regression test verifies that server-side rule.

## Verification status

Tests have been added to the candidate source. They must be executed in the user's isolated Docker environment before marking the boundary as runtime-tested or Stage 2 as fully signed off.
