
$ErrorActionPreference = "Stop"

function Run-Check($Name, $Command) {
    Write-Host "`n========== $Name ==========" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name FAILED with exit code $LASTEXITCODE"
    }
    Write-Host "$Name : PASS" -ForegroundColor Green
}

Write-Host "AWA FULL AUTOMATED VERIFICATION" -ForegroundColor Yellow

# 1. Frontend clean install and production build
Push-Location .\frontend
try {
    Run-Check "Frontend dependency install" { npm ci }
    Run-Check "Frontend production build" { npm run build }
}
finally {
    Pop-Location
}

# 2. Backend tests and Django checks inside Docker
Run-Check "Docker Compose configuration" {
    docker compose config --quiet
}

Run-Check "Docker image build" {
    docker compose build
}

Run-Check "Start local services" {
    docker compose up -d
}

Run-Check "Django system check" {
    docker compose exec -T backend python manage.py check
}

Run-Check "Migration consistency" {
    docker compose exec -T backend python manage.py makemigrations --check --dry-run
}

Run-Check "Complete backend test suite" {
    docker compose exec -T backend python manage.py test
}

Run-Check "Backend Python compilation" {
    docker compose exec -T backend python -m compileall -q .
}

# 3. Existing project audit scripts
Run-Check "Phase 1 audit" {
    python .\scripts\phase1_source_audit.py
}

Run-Check "Phase 2 audit" {
    python .\PHASE2_STATIC_AUDIT.py
}

Run-Check "Phase 4 audit" {
    python .\scripts\verify_phase4_features.py
}

Run-Check "Phases 5 and 6 audit" {
    python .\scripts\verify_phase5_6.py
}

Run-Check "Phases 7 and 8 audit" {
    python .\scripts\verify_phase7_8.py
}

Write-Host "`nALL CONFIGURED CHECKS PASSED." -ForegroundColor Green
Write-Host "This does not certify external provider, device, or deployment acceptance." -ForegroundColor Yellow
