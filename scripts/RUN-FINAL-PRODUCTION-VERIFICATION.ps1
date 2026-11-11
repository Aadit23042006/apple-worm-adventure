[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Compose = Join-Path $Root 'docker-compose.production.yml'
$EnvFile = Join-Path $Root '.env.production'
$Results = [System.Collections.Generic.List[string]]::new()
$script:Domain = $null

function Add-Result([string]$Status, [string]$Name, [string]$Detail) {
    $line = "$Status | $Name | $Detail"
    $Results.Add($line)
    $color = switch ($Status) { 'PASS' {'Green'} 'FAIL' {'Red'} default {'Yellow'} }
    Write-Host $line -ForegroundColor $color
}
function Read-EnvFile([string]$Path) {
    $values = @{}
    foreach ($line in (Get-Content -LiteralPath $Path)) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $values[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'") }
    }
    return $values
}

Write-Host 'AWA FINAL PRODUCTION VERIFICATION - ONLY THE FIVE TRACKER ITEMS' -ForegroundColor Cyan
Write-Host "Project: $Root`n"

# 1. Django production security check (runs against production env inside backend image).
try {
    if (-not (Test-Path $EnvFile)) { throw '.env.production is missing; create/configure it before this check.' }
    $envValues = Read-EnvFile $EnvFile
    if (-not $envValues.ContainsKey('AWA_DOMAIN') -or [string]::IsNullOrWhiteSpace($envValues.AWA_DOMAIN) -or $envValues.AWA_DOMAIN -match 'CHANGE_ME|example\.com') {
        throw 'AWA_DOMAIN is not configured to an assigned public hostname.'
    }
    $script:Domain = $envValues.AWA_DOMAIN
    docker compose -f $Compose --env-file $EnvFile config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Production Compose configuration is invalid.' }
    docker compose -f $Compose --env-file $EnvFile build backend
    if ($LASTEXITCODE -ne 0) { throw 'Backend image build failed.' }
    docker compose -f $Compose --env-file $EnvFile run --rm --no-deps backend python manage.py check --deploy
    if ($LASTEXITCODE -ne 0) { throw 'Django check --deploy reported errors.' }
    Add-Result 'PASS' 'Django production security check' 'Environment validation and manage.py check --deploy passed.'
} catch { Add-Result 'FAIL' 'Django production security check' $_.Exception.Message }

# 2. Public DNS + HTTPS certificate.
if ($script:Domain) {
    try {
        $dns = Resolve-DnsName -Name $script:Domain -Type A -ErrorAction Stop | Where-Object { $_.IPAddress }
        if (-not $dns) { throw 'No public A record was returned.' }
        Add-Result 'PASS' 'Public domain DNS' (($dns | ForEach-Object { $_.IPAddress }) -join ', ')
    } catch { Add-Result 'SKIP' 'Public domain DNS' $_.Exception.Message }
    try {
        $response = Invoke-WebRequest -Uri ("https://{0}/" -f $script:Domain) -Method Get -UseBasicParsing -TimeoutSec 25
        Add-Result 'PASS' 'Real HTTPS certificate' ("HTTPS request succeeded; HTTP {0}. Windows certificate validation accepted the TLS chain." -f [int]$response.StatusCode)
        # Secure-cookie browser validation cannot be inferred from the homepage response.
        Add-Result 'SKIP' 'Secure cookies in browser' 'Verify an authenticated login response in browser DevTools; confirm sessionid and csrftoken have Secure, and sessionid has HttpOnly.'
    } catch {
        Add-Result 'SKIP' 'Real HTTPS certificate' ("HTTPS endpoint/certificate not verified: {0}" -f $_.Exception.Message)
        Add-Result 'SKIP' 'Secure cookies in browser' 'Requires a reachable HTTPS login flow and browser DevTools.'
    }
} else {
    Add-Result 'SKIP' 'Public domain DNS' 'No assigned AWA_DOMAIN in .env.production.'
    Add-Result 'SKIP' 'Real HTTPS certificate' 'Requires public DNS and reachable Caddy deployment.'
    Add-Result 'SKIP' 'Secure cookies in browser' 'Requires a reachable HTTPS login flow and browser DevTools.'
}

# 3. Production deployment state (read-only; this script does not deploy or modify production).
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI is unavailable.' }
    docker info --format '{{.ServerVersion}}' *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Docker engine is not running.' }
    $psOutput = docker compose -f $Compose --env-file $EnvFile ps --format json 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Could not query production Compose services (check .env.production and Compose configuration).' }
    $services = @()
    foreach ($row in ($psOutput -split "`r?`n" | Where-Object { $_.Trim() })) { try { $services += ($row | ConvertFrom-Json) } catch {} }
    if ($services.Count -eq 0) { Add-Result 'SKIP' 'Production deployment' 'No production Compose containers are currently present; deployment has not been verified.' }
    else {
        $notRunning = @($services | Where-Object { $_.State -ne 'running' })
        if ($notRunning.Count -eq 0) { Add-Result 'PASS' 'Production deployment' ("All reported Compose containers are running: " + (($services | ForEach-Object { $_.Service }) -join ', ')) }
        else { Add-Result 'FAIL' 'Production deployment' (($notRunning | ForEach-Object { "$($_.Service)=$($_.State)" }) -join ', ') }
    }
} catch { Add-Result 'SKIP' 'Production deployment' $_.Exception.Message }

$report = Join-Path $Root 'FINAL_PRODUCTION_VERIFICATION.txt'
@('AWA final production verification', (Get-Date -Format o), 'Scope: only final production tracker items', '') + $Results | Set-Content -LiteralPath $report -Encoding UTF8
Write-Host "`nReport saved to: $report" -ForegroundColor Cyan
if (@($Results | Where-Object { $_ -like 'FAIL*' }).Count -gt 0) { exit 1 }
if (@($Results | Where-Object { $_ -like 'SKIP*' }).Count -gt 0) { exit 2 }
exit 0
