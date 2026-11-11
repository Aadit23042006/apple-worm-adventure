param(
    [string]$BackendContainer = "awa-backend-norevive-v2",
    [switch]$SkipBackend,
    [switch]$SkipFrontendInstall
)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"

Write-Host "=== AWA Phase 2 + Phase 3 verification ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"

if (-not $SkipBackend) {
    $container = docker inspect $BackendContainer 2>$null | ConvertFrom-Json
    if (-not $container) {
        throw "Backend container '$BackendContainer' not found. Start an isolated test runtime or pass -SkipBackend."
    }
    $mounts = $container[0].Mounts
    $matchingMount = $mounts | Where-Object { $_.Destination -eq "/app" -or $_.Destination -eq "/app/backend" }
    if (-not $matchingMount) {
        throw "Cannot verify the container source mount. Refusing to test a potentially different project copy."
    }
    Write-Host "Backend source mount: $($matchingMount.Source) -> $($matchingMount.Destination)" -ForegroundColor Yellow
    Write-Host "IMPORTANT: Ensure the mount source above is this extracted project before continuing."
    $confirm = Read-Host "Type YES only if the container is using this extracted project and a disposable/test database"
    if ($confirm -cne "YES") { throw "Stopped: backend runtime/database was not confirmed." }

    docker exec $BackendContainer python manage.py check
    if ($LASTEXITCODE -ne 0) { throw "Django system check failed." }
    docker exec $BackendContainer python manage.py test core.tests_phase2_ads core.tests_phase3_achievements --verbosity=2
    if ($LASTEXITCODE -ne 0) { throw "Phase 2/3 focused backend tests failed." }
    docker exec $BackendContainer python manage.py test --verbosity=2
    if ($LASTEXITCODE -ne 0) { throw "Full backend regression suite failed." }
}

Push-Location $FrontendRoot
try {
    if (-not $SkipFrontendInstall) {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }
    }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
} finally {
    Pop-Location
}

Write-Host "PASS: backend and frontend commands completed." -ForegroundColor Green
Write-Host "Browser checks still required: desktop and mobile Achievements navigation, API loading/error/empty/unlocked states."
