[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$NetworkName = 'awa-app-network'
$DbContainer = 'awa-app-db'
$BackendContainer = 'awa-app-backend'
$FrontendContainer = 'awa-app-frontend'
$DbVolume = 'awa_recovered_app_data_v1'
$BackendImage = 'awa-backend-safe:latest'
$FrontendImage = 'awa-frontend-safe:latest'
$DumpPath = Join-Path $PSScriptRoot 'database-safety-backup\awa_verified_recovery_2026-11-06.dump'
$EnvPath = Join-Path $PSScriptRoot '.env'

function Invoke-Docker {
    param([Parameter(Mandatory=$true)][string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed (exit $LASTEXITCODE): docker $($DockerArgs -join ' ')"
    }
}

function Get-EnvValue {
    param([string]$Name, [string]$Default = '')
    $line = Get-Content -LiteralPath $EnvPath | Where-Object { $_ -match ('^\s*' + [regex]::Escape($Name) + '\s*=') } | Select-Object -First 1
    if (-not $line) { return $Default }
    return (($line -split '=', 2)[1]).Trim()
}

function Set-EnvValue {
    param([string]$Name, [string]$Value)
    $lines = @(Get-Content -LiteralPath $EnvPath)
    $pattern = '^\s*' + [regex]::Escape($Name) + '\s*='
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = "$Name=$Value"
            $found = $true
        }
    }
    if (-not $found) { $lines += "$Name=$Value" }
    Set-Content -LiteralPath $EnvPath -Value $lines -Encoding UTF8
}

Write-Host "`n=== APPLE WORM ADVENTURE STARTUP ===" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI was not found. Install/start Docker Desktop, then retry.' }
& docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop is not running. Start Docker Desktop and retry.' }

if (-not (Test-Path -LiteralPath $EnvPath)) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot '.env.example') -Destination $EnvPath
    Write-Host 'Created local .env from .env.example.' -ForegroundColor Yellow
}

# Replace example-only secrets automatically on first setup. Existing user values are preserved.
$secret = Get-EnvValue 'DJANGO_SECRET_KEY'
if (-not $secret -or $secret -match '^change-this') {
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 48
    $rng.GetBytes($bytes)
    $rng.Dispose()
    Set-EnvValue 'DJANGO_SECRET_KEY' ([Convert]::ToBase64String($bytes))
}
$dbPassword = Get-EnvValue 'POSTGRES_PASSWORD'
if (-not $dbPassword -or $dbPassword -match '^change-this') {
    Set-EnvValue 'POSTGRES_PASSWORD' ([Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N'))
}
$adSecret = Get-EnvValue 'AD_PROVIDER_WEBHOOK_SECRET'
if (-not $adSecret -or $adSecret -match '^change-this') {
    Set-EnvValue 'AD_PROVIDER_WEBHOOK_SECRET' ([Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N'))
}
Set-EnvValue 'POSTGRES_HOST' 'db'
Set-EnvValue 'POSTGRES_PORT' '5432'
Set-EnvValue 'VITE_API_BASE_URL' '/api'

$dbName = Get-EnvValue 'POSTGRES_DB' 'veloop'
$dbUser = Get-EnvValue 'POSTGRES_USER' 'veloop_user'
if (-not $dbName -or -not $dbUser -or -not (Get-EnvValue 'POSTGRES_PASSWORD')) {
    throw 'POSTGRES_DB, POSTGRES_USER and POSTGRES_PASSWORD must be configured in .env.'
}
if (-not (Test-Path -LiteralPath $DumpPath)) {
    throw "Verified recovery dump is missing: $DumpPath. Refusing to create an empty game database."
}

# This is a NEW isolated volume. The original corrupted volume is never referenced or modified.
$networkExists = docker network ls --format '{{.Name}}' | Where-Object { $_ -eq $NetworkName }
if (-not $networkExists) { Invoke-Docker @('network','create',$NetworkName) | Out-Null }
Invoke-Docker @('volume','create',$DbVolume) | Out-Null

$dbExists = docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $DbContainer }
if ($dbExists) {
    $dbRunning = docker inspect $DbContainer --format '{{.State.Running}}'
    if ($dbRunning -ne 'true') { Invoke-Docker @('start',$DbContainer) | Out-Null }
} else {
    Invoke-Docker @('run','-d','--name',$DbContainer,'--network',$NetworkName,'--network-alias','db','--restart','unless-stopped','--env-file',$EnvPath,'-v',"${DbVolume}:/var/lib/postgresql/data",'postgres:16-alpine') | Out-Null
}

Write-Host 'Waiting for PostgreSQL...' -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    & docker exec $DbContainer pg_isready -U $dbUser -d $dbName *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) { & docker logs --tail 80 $DbContainer; throw 'PostgreSQL did not become ready. See database logs above.' }

$tableCountRaw = & docker exec $DbContainer psql -U $dbUser -d $dbName -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the selected application database.' }
$tableCount = 0
[int]::TryParse(($tableCountRaw | Out-String).Trim(), [ref]$tableCount) | Out-Null
if ($tableCount -eq 0) {
    Write-Host 'Restoring the verified database backup into the isolated application volume...' -ForegroundColor Yellow
    Invoke-Docker @('cp',$DumpPath,"${DbContainer}:/tmp/awa_verified_recovery.dump")
    Invoke-Docker @('exec',$DbContainer,'pg_restore','--exit-on-error','--single-transaction','--no-owner','--role',$dbUser,'-U',$dbUser,'-d',$dbName,'/tmp/awa_verified_recovery.dump')
    $tableCountRaw = & docker exec $DbContainer psql -U $dbUser -d $dbName -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
    if ($LASTEXITCODE -ne 0) { throw 'Database restore completed but table verification failed.' }
    [int]::TryParse(($tableCountRaw | Out-String).Trim(), [ref]$tableCount) | Out-Null
}
if ($tableCount -lt 20) { throw "Database validation failed: expected at least 20 public tables, found $tableCount. Backend will not be started." }
Write-Host "Database ready: $dbName ($tableCount public tables)." -ForegroundColor Green

Write-Host 'Building backend image...' -ForegroundColor Cyan
Invoke-Docker @('build','-t',$BackendImage,'.\backend')
Write-Host 'Building frontend image...' -ForegroundColor Cyan
$gameName = Get-EnvValue 'VITE_GAME_NAME' 'APPLE WORM ADVENTURE'
Invoke-Docker @('build','-t',$FrontendImage,'--build-arg',"VITE_GAME_NAME=$gameName",'--build-arg','VITE_API_BASE_URL=/api','.\frontend')

# Only remove containers created by this startup script; never remove any volume.
foreach ($name in @($FrontendContainer,$BackendContainer)) {
    $exists = docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $name }
    if ($exists) { Invoke-Docker @('rm','-f',$name) | Out-Null }
}

Write-Host 'Starting Django backend (database migrations are applied to the isolated restored copy only)...' -ForegroundColor Cyan
$backendCommand = 'python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --graceful-timeout 30'
Invoke-Docker @('run','-d','--name',$BackendContainer,'--network',$NetworkName,'--network-alias','backend','--restart','unless-stopped','--env-file',$EnvPath,'-e','POSTGRES_HOST=db','-e','POSTGRES_PORT=5432','-p','8002:8000',$BackendImage,'sh','-c',$backendCommand) | Out-Null

$backendReady = $false
for ($i = 0; $i -lt 60; $i++) {
    $state = docker inspect $BackendContainer --format '{{.State.Status}}' 2>$null
    if ($state -eq 'exited') { & docker logs --tail 120 $BackendContainer; throw 'Backend exited during migration or startup. Review the logs above; frontend was not started.' }
    try {
        $response = Invoke-WebRequest -Uri 'http://localhost:8002/api/health/' -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) { $backendReady = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}
if (-not $backendReady) { & docker logs --tail 120 $BackendContainer; throw 'Backend health check timed out. Review the logs above.' }
Write-Host 'Backend health: PASS (http://localhost:8002/api/health/).' -ForegroundColor Green

Write-Host 'Starting frontend...' -ForegroundColor Cyan
Invoke-Docker @('run','-d','--name',$FrontendContainer,'--network',$NetworkName,'--restart','unless-stopped','-p','5174:5173',$FrontendImage) | Out-Null
$frontendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $page = Invoke-WebRequest -Uri 'http://localhost:5174/' -UseBasicParsing -TimeoutSec 3
        $api = Invoke-WebRequest -Uri 'http://localhost:5174/api/health/' -UseBasicParsing -TimeoutSec 3
        if ($page.StatusCode -eq 200 -and $api.StatusCode -eq 200) { $frontendReady = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}
if (-not $frontendReady) { & docker logs --tail 100 $FrontendContainer; throw 'Frontend or proxied API health check failed. Review the logs above.' }

Write-Host "`n=== STARTUP SUCCESS ===" -ForegroundColor Green
Write-Host 'Game:     http://localhost:5174' -ForegroundColor Green
Write-Host 'API:      http://localhost:8002/api/health/' -ForegroundColor Green
Write-Host 'API via UI: http://localhost:5174/api/health/' -ForegroundColor Green
Write-Host "Database: $dbName on isolated volume $DbVolume" -ForegroundColor Green
Write-Host 'Original database volume was not used or modified.' -ForegroundColor Green
Write-Host "`nTo stop the app: .\STOP-AWA.ps1" -ForegroundColor Cyan
