# Phase 1 — Target Windows/Docker Verification Runbook

Run from PowerShell in the extracted project root. These commands are intended for a dedicated test environment. Do not point the test settings at production credentials or production database. Do not run `docker compose down -v`.

## 1. Frontend clean install and build

```powershell
Set-Location .\frontend
npm ci
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
Set-Location ..
```

## 2. Backend static and Django checks

```powershell
Set-Location .\backend
python -m pip install -r requirements.txt
python manage.py check
python manage.py makemigrations --check --dry-run
```

## 3. Backend tests

```powershell
python manage.py test core --verbosity 2
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
Set-Location ..
```

Use an isolated disposable PostgreSQL test database configured through a dedicated test `.env` or CI secret store. Never paste secrets into logs or this chat. Confirm the database host/name before running tests.

## 4. Compose configuration validation

```powershell
docker compose -f .\docker-compose.yml config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration invalid' }
```

## 5. Integration test environment

Use only the dedicated test Compose file if it is configured for isolated test services:

```powershell
docker compose -f .\test-compose.yml config --quiet
docker compose -f .\test-compose.yml up -d --build
```

Then capture container status, backend health, migrations, API smoke tests, and frontend browser tests. Do not substitute production services or production database volumes. Tear down only the test stack, without deleting any production volumes.

## 6. Evidence capture

Save raw command output with timestamps, commit/source SHA-256 manifest, test summary, migration plan, Compose config result, browser desktop/mobile results, and DB isolation proof under a new dated evidence directory. Redact credentials, tokens, private keys and personal data.

## 7. PDF traceability

The original `requirements/Apple-G_VELoop_Full_Stack.pdf` is bundled, and `PHASE1_TRACEABILITY_127_EXACT.csv` now contains exact extracted clause text and PDF page ranges for all 127 numbered sections. For each row, inspect the listed source paths and add the exact symbol, test/evidence identifier, result (`PASS`, `FAIL`, `PARTIAL`, `NOT VERIFIED`), and defect/fix reference. Do not mark a row PASS based on a filename or static text match alone.
