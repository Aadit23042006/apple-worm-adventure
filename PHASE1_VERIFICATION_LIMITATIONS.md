# Phase 1 Verification Limitations

This file distinguishes checks executed during the current archive review from historical records.

## Executed now
- Uploaded ZIP CRC integrity: PASS.
- 49 active Python source files: AST parse PASS.
- 6 JSON files: parse PASS.
- 4/5 Compose files: standard PyYAML parse PASS.
- Static source assertions: 11/11 PASS.
- Safe package inspection: no `.env` or `.env.production` file was found in the uploaded archive; safe `.env.example` templates were present.
- Security packaging: private TLS keys, local PKI state, database backups, node_modules, Python caches and historical backup files omitted from the release copy.

## Not executed now
- Django `manage.py check`, migrations, PostgreSQL integration, and full Django tests: Django/DRF/psycopg are unavailable in this sandbox.
- Docker Compose validation and container integration: Docker CLI unavailable.
- Frontend production build: `npm ci` timed out; `npm run build` then failed because `vite/client` was not installed. This is an incomplete dependency-install environment, not proof of a source-code defect.
- Browser/mobile end-to-end tests.
- Real advertising vendor SDK/webhook integration: no vendor adapter or credentials were supplied; default mock is intentionally unavailable.

## Historical project evidence
The included dated evidence folder records 84/84 backend tests, frontend build and TypeScript checks, isolated DB test setup, and backup archive readability. Those reports state that they are written records rather than raw terminal logs. Backup archive readability does not prove a full database restore.

## Sign-off rule
Do not mark a requirement PASS solely because a file or feature marker exists. Runtime behavior, exact PDF clause, and evidence must be checked before final company sign-off.
