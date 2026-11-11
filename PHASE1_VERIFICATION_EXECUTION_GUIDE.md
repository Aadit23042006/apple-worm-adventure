# Phase 1 verification execution guide

This package now includes a reproducible verification harness for the four checks that were previously blocked/not run.

## Safe scope

- Frontend dependencies are installed from `frontend/package-lock.json`; production build is run with `npm run build`.
- Django and PostgreSQL tests run in a dedicated Compose project named `awa-phase1-verify`.
- The test stack uses PostgreSQL 16 with a dedicated `phase1_test_pgdata` volume. It does not load `.env`, does not reference the production Compose file's `veloop_apple_worm_postgres_v2` volume, and does not publish a database port.
- The script cleans up only the isolated test project's containers and test volume. Do not manually change the project name or compose file to point at production resources.

## Run on Windows PowerShell

From the extracted project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\VERIFY-PHASE1.ps1
```

Requirements: Node.js 22, npm, Docker Desktop running, and internet access for clean package/image downloads.

The script runs `npm ci`, `npm run build`, `docker compose config`, then a fresh PostgreSQL-backed `python manage.py check`, `migrate`, and `test`. It writes `PHASE1_LOCAL_VERIFICATION_RESULTS.txt`.

To preserve the isolated test volume for diagnosis only:

```powershell
.\scripts\VERIFY-PHASE1.ps1 -KeepIsolatedTestVolume
```

The test volume is disposable. Never substitute the production Compose file or production database credentials.

## Formal sign-off rule

Phase 1 is eligible for sign-off only after all 127 traceability rows have implementation evidence/status reviewed, frontend production build passes, Django checks/tests pass against PostgreSQL, and Docker Compose verification passes. A generated script or a source-code scan is not a substitute for running it. Attach the complete PowerShell output and resulting text report to the evidence folder before changing the sign-off status.
