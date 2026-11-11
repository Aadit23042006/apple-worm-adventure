# Production Deployment (Django + PostgreSQL + Caddy TLS)

This guide prepares the existing application for deployment without changing its local HTTP workflow. Production uses Caddy as the only public entry point; PostgreSQL and Django are private to the Compose network.

## 1. Requirements and external prerequisites

- A Linux host or Docker-capable VM with Docker Engine and Compose v2.
- A public hostname assigned by your host or a registered domain. Do not use an invented hostname.
- DNS A (and AAAA only if IPv6 is correctly routed) records pointing to the host.
- Inbound TCP 80 and 443 open; UDP 443 is optional for HTTP/3.
- A valid operations email for ACME certificate notifications.
- A real SMTP account and a real rewarded-ad provider adapter plus its webhook signing secret. The repository intentionally fails closed without a real provider; mock/demo modes are not production ad integrations.

If the host, hostname, DNS or provider credentials are unavailable, public deployment is BLOCKED, not PASS.

## 2. Create the private production environment

From the repository root in PowerShell:

```powershell
.\scripts\PREPARE-PRODUCTION.ps1
notepad .env.production
```

The script creates unique Django and PostgreSQL secrets locally without printing them. Complete every remaining `CHANGE_ME` value, including:

- `AWA_DOMAIN`, `ACME_EMAIL`, `FRONTEND_BASE_URL`, `DJANGO_ALLOWED_HOSTS`;
- matching HTTPS `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`;
- the real ad provider adapter import path and the exact webhook signing secret configured with that provider;
- SMTP host, username, password and sender address.

Use the same hostname in `AWA_DOMAIN`, `FRONTEND_BASE_URL`, `DJANGO_ALLOWED_HOSTS`, CORS and CSRF settings. Do not paste secrets into chat, source control, tickets or logs.

## 3. Validate before deployment

```powershell
.\scripts\VALIDATE-PRODUCTION.ps1
```

This rejects placeholders, unsafe provider-free modes and invalid Compose configuration. It does not validate public DNS, a live TLS certificate, SMTP delivery or provider callback signatures.

## 4. DNS and firewall

Create an A record for the assigned hostname pointing to the host's public IPv4 address. Add an AAAA record only if the host is reachable over IPv6. Allow inbound TCP 80/443. Caddy uses HTTP-01/TLS-ALPN challenges and automatically obtains and renews certificates. Keep Caddy's `/data` volume persistent; it stores ACME state and private certificate material and must never be committed or shared.

## 5. Deploy

After DNS points to the host and all environment values are configured:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
```

The backend waits for PostgreSQL, runs migrations, `check --deploy`, and `validate_production`, then starts Gunicorn. Caddy publishes only ports 80/443. PostgreSQL and Django have no host-published ports. The backend container runs as a non-root user.

## 6. Verify actual production behavior

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production ps
docker compose -f docker-compose.production.yml --env-file .env.production logs --tail=100 backend
docker compose -f docker-compose.production.yml --env-file .env.production logs --tail=100 caddy
curl.exe -I "https://$env:AWA_DOMAIN/api/health/"
```

Verify from an external network: DNS resolution; trusted certificate chain and hostname; certificate expiry; HTTP redirects to HTTPS; health endpoint; registration, login, authenticated API calls, gameplay, progress persistence, logout; Secure/HttpOnly/SameSite cookie attributes; CORS and CSRF; and provider-signed callback verification plus duplicate-event rejection. Do not mark HTTPS PASS until a real public certificate is checked against the deployed hostname.

Django deployment checks are run during backend startup. Also run the application test suite in CI/staging before release. A green container health check alone does not prove browser workflows or ad-provider verification.

## 7. HSTS policy

The production template sets a one-year HSTS max-age while leaving `includeSubDomains` and `preload` disabled. Do not enable either until every relevant subdomain has permanent HTTPS and preload requirements are reviewed. Django SecurityMiddleware emits HSTS only after the trusted reverse-proxy header identifies an HTTPS request.

## 8. Secret rotation

If any prior environment or Compose output exposed credentials, treat them as compromised. Rotate Django `SECRET_KEY`, PostgreSQL password, ad webhook signing secret and SMTP/API credentials with a coordinated maintenance window. For PostgreSQL, update the database role password and `.env.production` together, then restart dependent services. Rotating Django's key invalidates existing signed sessions/tokens where applicable. Rotate the webhook secret in both the provider dashboard and app configuration; test signed callbacks before re-enabling rewards. Never claim rotation until each external system and running container is verified.

## 9. Backups and rollback

Use encrypted, access-controlled PostgreSQL backups and test restore procedures. Keep backups off-host and outside the repository. Back up the Caddy data volume securely if certificate continuity is required. Before an upgrade, record the image revision and database backup. Roll back application images first; only reverse migrations after explicit compatibility review. Never use `docker compose down -v` on a database containing user progress.

## 10. GitHub safety

```powershell
git status --short
git check-ignore .env .env.production
# Review staged files and scan them with a secret scanner before pushing.
git add .
git diff --cached --check
git status --short
```

Do not push until secret scanning and review are clean. Public push requires the repository owner's explicit authorization.

## 11. Local development remains HTTP

Continue using `START-AWA.ps1` and `docker-compose.yml` for local HTTP. Production HTTPS settings live in `.env.production` and `docker-compose.production.yml`; do not copy them into local `.env`.
