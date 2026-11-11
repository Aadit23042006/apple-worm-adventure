# AWA production-readiness work — 11 November 2026

## Outcome

Production code/configuration hardening has been prepared in this working copy. This is **PREPARED**, not a claim that the application is publicly deployed or 100% production accepted. The original uploaded ZIP was left untouched as the pre-change backup.

## Implemented

- Reworked `docker-compose.production.yml` into a production topology with Caddy as the only public entry point on 80/443, private Django/PostgreSQL services, persistent database and ACME state volumes, health checks, and no host-published database/backend/frontend ports.
- Corrected `frontend/nginx.conf` to route `/api/` to the Compose service name `backend` rather than a container-instance name.
- Hardened Django cookie defaults (`HttpOnly`, `SameSite`) and retained environment-controlled HTTPS/security settings so local HTTP remains possible.
- Expanded `validate_production` to reject insecure cookie/proxy/HSTS policy, non-HTTPS CORS/CSRF origins, missing hostname alignment, provider-free demo mode, unconfigured provider adapters, and missing SMTP configuration.
- Updated the production environment template with explicit domain, ACME, Django, database, provider, SMTP, CORS/CSRF and transport settings. HSTS subdomain enforcement and preload remain disabled.
- Added `scripts/PREPARE-PRODUCTION.ps1` to create a private production env file with fresh Django and database secrets without printing them.
- Added `scripts/VALIDATE-PRODUCTION.ps1` to reject placeholders and validate production configuration before Compose deployment.
- Updated deployment documentation and README with DNS, firewall, certificate renewal, secret rotation, verification, backup and rollback procedures.
- Made the backend container run as a non-root application user where feasible.
- Corrected local `.env.example` to keep HTTP development free of forced HTTPS/HSTS, and corrected `START-AWA.ps1` to replace the current local secret placeholders with random local secrets.
- Expanded `.gitignore` for production env files, credentials, private key/certificate material, database dumps, logs and runtime artifacts.

## Validation performed in this execution environment

| Check | Result | Notes |
|---|---|---|
| Python syntax compilation | PASS | `settings.py` and `validate_production.py` compile. |
| Production Compose YAML parse/topology | PASS | YAML parsed; expected four services and only Caddy has published ports. |
| Django `check` / `check --deploy` | PENDING | Django is not installed in this execution environment; package installation was blocked by unavailable network access. |
| Backend automated tests | PENDING | Same dependency limitation; not claimed as rerun. |
| Frontend tests/build | PENDING | The packaged Windows `node_modules` could not run on this Linux host; clean install timed out and available Node was below the package engine requirement (`>=22.22.2`). |
| Docker Compose validation/build/health | PENDING | Docker CLI is not installed in this execution environment. |
| DNS / public TLS / cookies / browser flows | BLOCKED | Requires the actual assigned hostname, DNS, reachable deployment host and browser verification. |
| Live ad-provider signed callback | BLOCKED | Requires a real provider adapter and matching provider dashboard signing secret. |
| SMTP delivery | BLOCKED | Requires real SMTP credentials and a delivery test. |

The archive contains prior project evidence, but historical test results have not been re-labelled as fresh verification in this pass.

## Modified files

- `.env.example`
- `.env.production.example`
- `.gitignore`
- `README.md`
- `START-AWA.ps1`
- `TLS_DEPLOYMENT_GUIDE.md`
- `backend/Dockerfile`
- `backend/config/settings.py`
- `backend/core/management/commands/validate_production.py`
- `caddy/Caddyfile`
- `docker-compose.production.yml`
- `docs/DEPLOYMENT.md`
- `frontend/nginx.conf`
- `scripts/PREPARE-PRODUCTION.ps1` (new)
- `scripts/VALIDATE-PRODUCTION.ps1` (new)

## Remaining external actions

1. Run the preparation script on the deployment workstation and complete every remaining `CHANGE_ME` value in `.env.production`.
2. Supply the real assigned public hostname, DNS A/AAAA configuration (only valid IPv6), and inbound TCP 80/443 access.
3. Configure a real ad provider adapter and matching signed webhook secret; run end-to-end signature and duplicate-event tests. The existing local provider-free demo is not a production ad integration.
4. Configure SMTP and verify registration/password-reset email delivery.
5. Run production Compose validation/build on a Docker host, verify Django deploy checks and database migrations, and confirm all services are healthy.
6. Verify public TLS chain, hostname and expiry, HTTP-to-HTTPS redirect, secure cookie attributes, registration/login/gameplay/progress/logout and reward callbacks from a browser/external network.
7. Rotate any credentials that may have been exposed in earlier environment or Compose output. Rotation is not performed by this package patch.
8. Perform secret scanning and review the staged Git diff before any public GitHub push. No repository push was performed.

## Exact Windows commands

```powershell
.\scripts\PREPARE-PRODUCTION.ps1
notepad .env.production
.\scripts\VALIDATE-PRODUCTION.ps1
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
docker compose -f docker-compose.production.yml --env-file .env.production ps
docker compose -f docker-compose.production.yml --env-file .env.production logs --tail=100 backend
docker compose -f docker-compose.production.yml --env-file .env.production logs --tail=100 caddy
```

Do not run production Compose until placeholders are replaced and validation passes. Do not run `docker compose down -v` against a volume containing player progress.
