# AWA HTTPS/TLS deployment

## What this patch provides
- Caddy reverse proxy publishes TCP 80 and 443 (plus UDP 443 for HTTP/3).
- Caddy automatically obtains and renews a publicly trusted certificate using ACME.
- HTTP requests for the configured hostname are automatically redirected to HTTPS.
- Django emits HSTS (`max-age=31536000`) only after the trusted proxy header identifies HTTPS; subdomains and preload remain disabled.
- Django is configured by the Compose overlay to trust Caddy's `X-Forwarded-Proto`,
  enforce HTTPS, and use secure session/CSRF cookies.
- Existing frontend/backend services and database volume are retained. The TLS
  overlay removes the frontend's public 5174 mapping so Caddy is the only entry.

## Required before deployment
This cannot be made publicly trusted on `localhost` alone. You must have a domain
you control, DNS A/AAAA records pointing to this host, public inbound TCP 80/443
allowed by the cloud firewall/router/ISP, and no other process occupying those
ports. If an AAAA record exists, IPv6 must route correctly; remove a stale AAAA
record rather than letting ACME validate a broken IPv6 route.

1. Back up the project and database using your established backup procedure.
   Do not run `docker compose down -v` and do not remove any volumes/rollback containers.
2. Add these values to the root `.env` (replace the examples):
   `AWA_DOMAIN=game.your-real-domain.com`
   `ACME_EMAIL=you@your-real-domain.com`
3. Ensure `DJANGO_ALLOWED_HOSTS` in `.env` includes the exact hostname, and
   `CSRF_TRUSTED_ORIGINS` includes `https://` plus that hostname. If
   `CORS_ALLOWED_ORIGINS` is used for browser requests, set it to the HTTPS origin.
4. Confirm DNS resolves to this host and TCP 80/443 are reachable from the public
   internet. Localhost-only checks cannot prove public ACME reachability.
5. From the project root, validate the merged Compose configuration:
   `docker compose -f docker-compose.yml -f docker-compose.tls.yml config`
6. Deploy without deleting volumes:
   `docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build`
7. Inspect certificate issuance:
   `docker compose -f docker-compose.yml -f docker-compose.tls.yml logs --tail 150 caddy`
   Caddy must report successful certificate issuance. Do not mark TLS PASS before this.

## Verification (run from a machine that can reach the public domain)
Replace `game.your-real-domain.com` below with the exact configured hostname.

- `curl.exe -sSI http://game.your-real-domain.com/` must return 301 or 308 and a
  `Location: https://game.your-real-domain.com/...` header.
- `curl.exe -sSI https://game.your-real-domain.com/` must return HTTP 200 and a
  valid publicly trusted certificate (do not use `-k`).
- `curl.exe -sSI https://game.your-real-domain.com/api/health/` must return HTTP 200.
- `curl.exe -sSI https://game.your-real-domain.com/` must include
  `Strict-Transport-Security: max-age=31536000`.
- `docker compose -f docker-compose.yml -f docker-compose.tls.yml ps` must show
  caddy, frontend, backend, and db healthy/running as applicable.

## Important
The patch adds a ready-to-configure TLS deployment; it does not claim the live
certificate is issued. Actual PASS depends on your domain, DNS, firewall and
host availability. HSTS is intentionally not configured with includeSubDomains
or preload until all subdomains are HTTPS-ready. Keep the current working
deployment and rollback containers until all external checks pass.
