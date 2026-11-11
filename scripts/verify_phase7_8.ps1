$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $ProjectRoot 'frontend'

Write-Host "`n========== PHASE 7 + 8 STATIC AUDIT ==========" -ForegroundColor Cyan
python (Join-Path $PSScriptRoot 'verify_phase7_8.py')
if ($LASTEXITCODE -ne 0) { throw 'Phase 7/8 static audit failed.' }

Write-Host "`n========== FRONTEND DEPENDENCY INSTALL ==========" -ForegroundColor Cyan
Push-Location $Frontend
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }

    Write-Host "`n========== FRONTEND PRODUCTION BUILD ==========" -ForegroundColor Cyan
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'npm run build failed.' }
}
finally {
    Pop-Location
}

Write-Host "`nPASS: Static audit and frontend production build completed." -ForegroundColor Green
Write-Host 'Backend tests must be run against an isolated test database, not the recovered production database.'
Write-Host 'See docs/PHASE7_8_AUTH_ACCESSIBILITY.md for exact Django and anti-cheat regression commands.'
