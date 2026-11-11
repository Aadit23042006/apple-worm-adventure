[CmdletBinding()]
param(
    [switch]$KeepIsolatedTestVolume
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root 'frontend'
$ComposeFile = Join-Path $Root 'docker-compose.phase1-test.yml'
$Project = 'awa-phase1-verify'
$Results = [System.Collections.Generic.List[string]]::new()
function Record([string]$Name, [bool]$Passed, [string]$Detail) {
    $line = '{0} | {1} | {2}' -f $(if ($Passed) {'PASS'} else {'FAIL'}), $Name, $Detail
    $Results.Add($line)
    Write-Host $line -ForegroundColor $(if ($Passed) {'Green'} else {'Red'})
}
function Invoke-Step([string]$Name, [scriptblock]$Action) {
    Write-Host "`n===== $Name =====" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}
try {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js 22 is required.' }
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'npm is required.' }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI is required; start Docker Desktop.' }
    Invoke-Step 'Frontend clean dependency install' { Push-Location $Frontend; try { npm ci --no-audit --no-fund } finally { Pop-Location } }
    Record 'Frontend npm ci' $true 'Clean install from package-lock.json'
    Invoke-Step 'Frontend production build' { Push-Location $Frontend; try { npm run build } finally { Pop-Location } }
    if (-not (Test-Path (Join-Path $Frontend 'dist/index.html'))) { throw 'Frontend build did not create dist/index.html.' }
    Record 'Frontend production build' $true 'dist/index.html exists'
    Invoke-Step 'Isolated Docker Compose configuration' { docker compose -f $ComposeFile -p $Project config --quiet }
    Record 'Docker Compose config' $true 'Isolated test stack config valid'
    Invoke-Step 'Isolated PostgreSQL + Django tests' { docker compose -f $ComposeFile -p $Project up --build --abort-on-container-exit --exit-code-from backend-tests }
    Record 'Fresh Django/PostgreSQL tests' $true 'Django check, migrations and test suite exited 0 against isolated PostgreSQL 16'
}
catch {
    Record 'Verification run' $false $_.Exception.Message
    Write-Error $_
}
finally {
    if (-not $KeepIsolatedTestVolume -and (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "`nCleaning ONLY the isolated '$Project' test stack and its dedicated test volume..." -ForegroundColor Yellow
        docker compose -f $ComposeFile -p $Project down --volumes --remove-orphans
    }
    $report = Join-Path $Root 'PHASE1_LOCAL_VERIFICATION_RESULTS.txt'
    @('AWA Phase 1 local verification', (Get-Date -Format o), 'Production database/volumes are not referenced by this test stack.', '') + $Results | Set-Content -Encoding utf8 $report
    Write-Host "`nEvidence report: $report" -ForegroundColor Cyan
}
if ($Results.Count -eq 0 -or ($Results | Where-Object { $_ -like 'FAIL*' }).Count -gt 0) { exit 1 }
