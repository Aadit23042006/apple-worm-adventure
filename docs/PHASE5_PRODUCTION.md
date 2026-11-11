# Phase 5 — Production

This phase adds production-ready operational controls without removing the existing gameplay, Full Stack or VELoop features.

## Completed controls
- Environment-specific production example.
- HTTPS/security settings already supported by environment variables.
- Production Docker Compose deployment.
- Backend healthcheck and dependency ordering.
- Automated migrations and deployment checks.
- Django `check --deploy` before Gunicorn.
- Production configuration/data validation command.
- Deterministic level validation command.
- CI workflow retained.
- Architecture, economy and deployment documentation.
- Secrets remain outside source control.

## Commands
```bash
python manage.py check --deploy
python manage.py validate_production
python manage.py validate_game_levels
python manage.py test
```

Production deployment is intentionally separate from the existing local Docker Compose flow so the local setup is not removed or changed.

## Permanent Phase 5 game-session hardening

`POST /api/games/start/` is now server-authoritative:

- `level` is accepted as the canonical request field; `level_id` is also accepted for backward/manual compatibility.
- The client does not need to send an initial `state`.
- The backend generates the canonical worm, apples, obstacles, portal, counters and start timestamp from the level configuration.
- A client-supplied state is still strictly validated, so legacy clients cannot bypass anti-cheat validation.
- The response returns the exact authoritative `state` persisted in `GameSession`.
- The React client now renders the returned server state instead of reconstructing the board independently.

This permanently fixes the `Invalid worm state.` failure caused by calling the start endpoint without a state and removes the client from authority over the initial board.
