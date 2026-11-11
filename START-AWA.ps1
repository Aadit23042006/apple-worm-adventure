[CmdletBinding()]
param(
    [switch]$Rebuild
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComposeProject = 'awa-apple-worm'
$EnvPath = Join-Path $ProjectRoot '.env'

function New-RandomHex([int]$ByteCount = 32) {
    $bytes = New-Object byte[] $ByteCount
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return ([System.BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}

function Set-EnvValue([string]$Key, [string]$Value) {
    $lines = [System.Collections.Generic.List[string]]::new()
    if (Test-Path -LiteralPath $EnvPath) {
        foreach ($line in [System.IO.File]::ReadAllLines($EnvPath)) { $lines.Add($line) }
    }
    $pattern = '^' + [regex]::Escape($Key) + '='
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = "$Key=$Value"
            $found = $true
            break
        }
    }
    if (-not $found) { $lines.Add("$Key=$Value") }
    [System.IO.File]::WriteAllLines($EnvPath, $lines, (New-Object System.Text.UTF8Encoding($false)))
}

Write-Host '=== Apple Worm Adventure: safe fresh-install startup ===' -ForegroundColor Cyan
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker CLI was not found. Install Docker Desktop, start it in Linux-container mode, then rerun this script.'
}
& docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop is not running. Start Docker Desktop and rerun this script.' }
& docker compose version *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose v2 is required. Update Docker Desktop.' }

if (-not (Test-Path -LiteralPath $EnvPath)) {
    Copy-Item (Join-Path $ProjectRoot '.env.example') $EnvPath
    Write-Host 'Created local .env from .env.example.' -ForegroundColor Yellow
}

# Ensure local/staging uses the explicit provider-free rewarded-demo adapter.
# This never represents a real ad network and is disabled in production by policy.
Set-EnvValue 'AD_PROVIDER' 'provider_free_demo'
Set-EnvValue 'ALLOW_PROVIDER_FREE_DEMO_ADS' 'true'
Set-EnvValue 'PROVIDER_FREE_DEMO_DURATION_SECONDS' '3'

# Replace only known template placeholders. Existing user-supplied secrets are preserved.
$envText = [System.IO.File]::ReadAllText($EnvPath)
if ($envText -match '(?im)^DJANGO_SECRET_KEY=(replace-with-|change-this).*') {
    Set-EnvValue 'DJANGO_SECRET_KEY' (New-RandomHex 48)
}
$envText = [System.IO.File]::ReadAllText($EnvPath)
if ($envText -match '(?im)^POSTGRES_PASSWORD=(replace-with-|change-this).*') {
    Set-EnvValue 'POSTGRES_PASSWORD' (New-RandomHex 32)
}
$envText = [System.IO.File]::ReadAllText($EnvPath)
if ($envText -match '(?im)^AD_PROVIDER_WEBHOOK_SECRET=(replace-with-|change-this).*') {
    Set-EnvValue 'AD_PROVIDER_WEBHOOK_SECRET' (New-RandomHex 32)
}

Push-Location $ProjectRoot
try {
    Write-Host 'Validating Docker Compose configuration...' -ForegroundColor Cyan
    & docker compose -p $ComposeProject config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose configuration is invalid. Check .env and compose logs.' }

    $buildArg = @('compose', '-p', $ComposeProject, 'up', '-d', '--build')
    if ($Rebuild) { $buildArg += '--force-recreate' }
    Write-Host 'Building and starting PostgreSQL, Django and frontend...' -ForegroundColor Cyan
    & docker @buildArg
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose build/start failed. Services were not reported as healthy.' }

    $healthy = $false
    for ($attempt = 1; $attempt -le 90; $attempt++) {
        try {
            $api = Invoke-WebRequest -Uri 'http://localhost:8002/api/health/' -UseBasicParsing -TimeoutSec 4
            $web = Invoke-WebRequest -Uri 'http://localhost:5174/' -UseBasicParsing -TimeoutSec 4
            if ($api.StatusCode -eq 200 -and $web.StatusCode -eq 200) { $healthy = $true; break }
        } catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $healthy) {
        Write-Host 'Startup did not reach healthy HTTP responses. Recent service logs:' -ForegroundColor Red
        & docker compose -p $ComposeProject logs --tail 100
        throw 'Startup health check failed. The database volume has been preserved; do not delete it.'
    }

    Write-Host ''
    Write-Host '=== STARTUP SUCCESS ===' -ForegroundColor Green
    Write-Host 'Game: http://localhost:5174' -ForegroundColor Green
    Write-Host 'API:  http://localhost:8002/api/health/' -ForegroundColor Green
    Write-Host 'Database volume: awa_fresh_install_data_v1 (persistent; not deleted by STOP-AWA.ps1)' -ForegroundColor Green
    Write-Host 'The previous database volumes were not mounted, deleted, or modified.' -ForegroundColor Green
    Write-Host 'Rewarded Demo: provider-free local/staging mode is enabled. Real provider integration remains production-only.' -ForegroundColor Yellow
} finally {
    Pop-Location
}
