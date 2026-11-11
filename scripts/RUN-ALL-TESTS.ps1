[CmdletBinding()]
param(
    [switch]$SkipDockerBackend,
    [switch]$SkipFrontendInstall
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root 'frontend'
$Results = [System.Collections.Generic.List[string]]::new()

function Run-Check([string]$Name, [scriptblock]$Action) {
    Write-Host "`n========== $Name ==========" -ForegroundColor Cyan
    try {
        & $Action
        if ($LASTEXITCODE -ne 0) { throw "Exit code $LASTEXITCODE" }
        $Results.Add("PASS | $Name")
        Write-Host "PASS | $Name" -ForegroundColor Green
    } catch {
        $Results.Add("FAIL | $Name | $($_.Exception.Message)")
        Write-Host "FAIL | $Name | $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python is required.' }
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Node.js/npm is required.' }

    # Static source audits for the project's phase verifiers.
    $staticChecks = @(
        @{ Name = 'Phase 1 source audit'; File = 'scripts/phase1_source_audit.py' },
        @{ Name = 'Phase 4 feature audit'; File = 'scripts/verify_phase4_features.py' },
        @{ Name = 'Phase 5/6 source audit'; File = 'scripts/verify_phase5_6.py' },
        @{ Name = 'Phase 7/8 source audit'; File = 'scripts/verify_phase7_8.py' },
        @{ Name = 'Level reachability audit'; File = 'scripts/verify_level_reachability.py' },
        @{ Name = 'Audio preferences audit'; File = 'scripts/verify_audio_preferences.py' }
    )
    foreach ($check in $staticChecks) {
        $scriptPath = Join-Path $Root $check.File
        if (-not (Test-Path $scriptPath)) { throw "Missing verifier: $($check.File)" }
        Run-Check $check.Name { python $scriptPath }
    }

    # Frontend tests and production bundle.
    Push-Location $Frontend
    try {
        if (-not $SkipFrontendInstall) {
            Run-Check 'Frontend clean dependency install' { npm ci --no-audit --no-fund }
        }
        Run-Check 'Frontend unit/component tests' { npm test -- --reporter=default }
        Run-Check 'Frontend TypeScript + production build' { npm run build }
        if (-not (Test-Path (Join-Path $Frontend 'dist/index.html'))) { throw 'dist/index.html was not generated.' }
    } finally { Pop-Location }

    # Isolated PostgreSQL + complete Django suite. This stack has its own test DB/volume.
    if (-not $SkipDockerBackend) {
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI not found. Start Docker Desktop or use -SkipDockerBackend.' }
        Run-Check 'Docker engine available' { docker info --format '{{.ServerVersion}}' }
        Run-Check 'Isolated PostgreSQL + complete Django tests' {
            powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'VERIFY-PHASE1.ps1')
        }
    } else {
        $Results.Add('SKIP | Isolated PostgreSQL + complete Django tests | -SkipDockerBackend supplied')
    }

    # Production environment/config validation is conditional; never deploy or touch production data.
    $prodEnv = Join-Path $Root '.env.production'
    if (Test-Path $prodEnv) {
        Run-Check 'Production environment validation' { & (Join-Path $PSScriptRoot 'VALIDATE-PRODUCTION.ps1') }
        Run-Check 'Production Compose syntax validation' {
            docker compose -f (Join-Path $Root 'docker-compose.production.yml') --env-file $prodEnv config --quiet
        }
    } else {
        $Results.Add('SKIP | Production env/Compose validation | .env.production not present; copy/configure .env.production.example first')
        Write-Host 'SKIP | Production env/Compose validation: .env.production not present.' -ForegroundColor Yellow
    }

    $Results.Add('LIMIT | Live DNS/TLS/SMTP/ad-provider/browser/mobile acceptance | Requires real external services and manual end-to-end checks')
    Write-Host "`nALL AUTOMATED CHECKS COMPLETED. Review SKIP/LIMIT rows; this is not a production sign-off." -ForegroundColor Green
} catch {
    Write-Host "`nTEST RUN STOPPED: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    $report = Join-Path $Root 'ALL_TESTS_RESULTS.txt'
    @('AWA all-in-one verification', (Get-Date -Format o), '') + $Results | Set-Content -Path $report -Encoding utf8
    Write-Host "`nReport: $report" -ForegroundColor Cyan
}
if (($Results | Where-Object { $_ -like 'FAIL*' }).Count -gt 0 -or $Results.Count -eq 0) { exit 1 }
if (($Results | Where-Object { $_ -like 'SKIP*' -or $_ -like 'LIMIT*' }).Count -gt 0) { exit 2 }
exit 0
