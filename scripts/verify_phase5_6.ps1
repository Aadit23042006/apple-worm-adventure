$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========== PHASE 5 + 6 STATIC VALIDATION =========="
python (Join-Path $ProjectRoot 'scripts\verify_phase5_6.py')
if ($LASTEXITCODE -ne 0) { throw 'Phase 5/6 static validation failed.' }

Write-Host "========== FRONTEND PRODUCTION BUILD =========="
Push-Location (Join-Path $ProjectRoot 'frontend')
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend production build failed.' }
}
finally { Pop-Location }

Write-Host "========== BACKEND API INTEGRATION TESTS =========="
Write-Host 'Run against an isolated test database only.'
Push-Location (Join-Path $ProjectRoot 'backend')
try {
    python manage.py test core.tests_phase3_achievements --verbosity=2
    if ($LASTEXITCODE -ne 0) { throw 'Phase 5/6 backend API tests failed.' }
}
finally { Pop-Location }
