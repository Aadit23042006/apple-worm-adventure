# Apple Worm Adventure — Architecture

## Runtime
- React + TypeScript + Vite frontend.
- Nginx serves the built frontend and proxies `/api/` to Django.
- Django + Django REST Framework backend.
- PostgreSQL 16 persistent database.
- Gunicorn application server.

## Trust boundaries
The browser is an untrusted client. The backend is authoritative for:
- authenticated identity;
- level configuration;
- game-session ownership;
- checkpoint transitions;
- score and move progression;
- level completion;
- wallet balance and wallet ledger;
- rewarded-ad eligibility and verification;
- reward caps, cooldowns and daily limits;
- achievement persistence.

The frontend is responsible for presentation, input and local interaction only.

## Request flow
Browser → Nginx `/api/` proxy → Django API → PostgreSQL.

Reward flow:
Player action → ad opportunity → provider verification → server eligibility checks → reward transaction → wallet/game-state update.

## Persistence
Core tables include users/profiles, levels, player progress, game sessions, wallet transactions, ad opportunities, reward transactions, achievements, economy configuration, daily challenges, refresh sessions, email verification, password-reset tokens and API keys.

## Deployment
Local development uses `docker-compose.yml`.
Production uses `docker-compose.production.yml` with `.env.production`.
The production backend runs migrations, collects static assets, Django deployment checks and the production validation command before Gunicorn starts.
