[CmdletBinding()]
param([switch]$KeepIsolatedTestVolume)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Results = [System.Collections.Generic.List[string]]::new()
function Add-Result([string]$Name,[bool]$Pass,[string]$Detail) {
    $line = '{0} | {1} | {2}' -f $(if($Pass){'PASS'}else{'FAIL'}),$Name,$Detail
    $Results.Add($line); Write-Host $line -ForegroundColor $(if($Pass){'Green'}else{'Red'})
}
function Invoke-Checked([string]$Name,[scriptblock]$Action) {
    Write-Host "`n===== $Name =====" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}
$ComposeFile = Join-Path $Root 'docker-compose.phase1-test.yml'
$Project = 'awa-full-verification-isolated'
try {
    foreach ($tool in @('python','node','npm','docker')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Required tool missing: $tool" }
    }
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop/Engine is not running.' }

    Invoke-Checked 'Static audit: PHASE2_STATIC_AUDIT.py' { python (Join-Path $Root 'PHASE2_STATIC_AUDIT.py') }
    Add-Result 'PHASE2_STATIC_AUDIT.py' $true 'All 8 rewarded-ad assertions passed'

    foreach ($audit in @('phase1_source_audit.py','verify_phase4_features.py','verify_phase5_6.py','verify_phase7_8.py')) {
        $path = Join-Path $Root (Join-Path 'scripts' $audit)
        Invoke-Checked "Static audit: $audit" { python $path }
        Add-Result $audit $true 'All assertions in this audit passed'
    }

    $frontend = Join-Path $Root 'frontend'
    Push-Location $frontend
    try {
        Invoke-Checked 'Frontend clean install' { npm ci --no-audit --no-fund }
        Add-Result 'Frontend npm ci' $true 'Clean dependency install from pinned lockfile'
        Invoke-Checked 'Frontend production build' { npm run build }
        if (-not (Test-Path (Join-Path $frontend 'dist/index.html'))) { throw 'dist/index.html was not generated.' }
        Add-Result 'Frontend production build' $true 'TypeScript and Vite build completed'
    } finally { Pop-Location }

    Invoke-Checked 'Isolated Compose config' { docker compose -f $ComposeFile -p $Project config --quiet }
    Add-Result 'Isolated Compose config' $true 'Configuration validated'
    Invoke-Checked 'Django + PostgreSQL isolated full test suite' { docker compose -f $ComposeFile -p $Project up --build --abort-on-container-exit --exit-code-from backend-tests }
    Add-Result 'Django/PostgreSQL suite' $true 'Django check, migrations and full backend tests passed on isolated PostgreSQL'
} catch {
    Add-Result 'Verification run' $false $_.Exception.Message
    Write-Error $_
} finally {
    if (-not $KeepIsolatedTestVolume -and (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "Cleaning only isolated test project '$Project'..." -ForegroundColor Yellow
        docker compose -f $ComposeFile -p $Project down --volumes --remove-orphans
    }
    $report = Join-Path $Root 'ALL_VERIFICATION_RESULTS.txt'
    @('AWA automated verification results',(Get-Date -Format o),'Production application volume is not referenced by this test stack.','') + $Results | Set-Content -Encoding utf8 $report
    Write-Host "Results saved to $report" -ForegroundColor Cyan
}
if ($Results.Count -eq 0 -or ($Results | Where-Object { $_ -like 'FAIL*' }).Count -gt 0) { exit 1 }
