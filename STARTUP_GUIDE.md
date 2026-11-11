# Apple Worm Adventure — safe fresh-install startup

## One-command startup (Windows PowerShell)

1. Install Docker Desktop with Linux containers enabled, then start it.
2. Extract the ZIP to a writable folder.
3. Open PowerShell in that folder and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\START-AWA.ps1
```

The included root `.env.example` supplies the documented local defaults. The script creates `.env` from `.env.example` if needed, replaces only known template secrets with random local values, validates Compose, builds the frontend/backend images, starts PostgreSQL, applies Django migrations, and polls the API and frontend health endpoints.

Open `http://localhost:5174` after `STARTUP SUCCESS`.

## Database safety and first-run behavior

- This distributable uses a dedicated persistent Docker volume named `awa_fresh_install_data_v1`.
- On a new machine, Docker Compose creates this volume automatically. Migrations seed the 60 levels, default economy configuration, and achievement definitions.
- Previously used volumes such as `veloop_apple_worm_postgres_v2` and `awa_recovered_app_data_v1` are not mounted, deleted, or modified.
- The ZIP intentionally does not contain a database dump. Therefore, existing player accounts/progress from another machine are not imported. If you need to migrate existing progress, provide a verified database backup and perform a separately rehearsed restore into a separate volume.
- `STOP-AWA.ps1` stops services but preserves the database volume. Never use `docker compose down -v` as routine troubleshooting.

## Verification (isolated from the application database)

Run:

```powershell
.\RUN-ALL-VERIFICATION.ps1
```

This runs the four static phase audits, clean frontend install/build, Compose config validation, and the full Django test suite against a dedicated temporary PostgreSQL test stack. It cleans only that isolated test stack. It does not delete or connect to the application database volume.

The script does not replace visual desktop/mobile acceptance, a real ad-provider staging test, production deployment, or the final human review of all 127 company clauses. Those require the target environment and/or external provider/demo evidence.

## Rewarded ads

The local default intentionally uses a fail-closed provider abstraction. No ad completion or reward is fabricated. The company specification explicitly permits a provider abstraction/mock integration when an actual provider cannot be used locally, provided the architecture routes through provider → verification → backend → economy ledger. For production ads, implement/configure the selected provider adapter and verify signed callbacks in its staging environment.

## Troubleshooting

- If Docker is unavailable, start Docker Desktop and rerun the script.
- If a build fails because npm/PyPI cannot be reached, restore network access and rerun; do not delete the database volume.
- If startup fails, inspect `docker compose -p awa-apple-worm logs --tail 150` and preserve the output.
- If ports 5174 or 8002 are occupied, stop the process using those ports before retrying.

The old dump-based workflow is preserved separately as `START-AWA-RECOVERY-RESTORE.ps1`. It is not the standard startup command and requires the exact verified database dump at its configured path. That dump is intentionally absent from this ZIP; do not run the recovery script unless you have separately verified and supplied the correct backup.
