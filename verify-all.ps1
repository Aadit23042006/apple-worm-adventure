$ErrorActionPreference = "Stop"

$Results = @()

function Run-Check {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "`n==================================================" -ForegroundColor Cyan
    Write-Host $Name -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan

    try {
        & $Action
        $script:Results += [PSCustomObject]@{
            Check  = $Name
            Status = "PASS"
        }
        Write-Host "PASS: $Name" -ForegroundColor Green
    }
    catch {
        $script:Results += [PSCustomObject]@{
            Check  = $Name
            Status = "FAIL"
        }
        Write-Host "FAIL: $Name" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
}

# --------------------------------------------------
# 1. Fresh Django/PostgreSQL suite
# --------------------------------------------------
Run-Check "Fresh Django/PostgreSQL suite" {

    if (Test-Path ".\backend") {
        Set-Location ".\backend"
    }

    if (-not (Test-Path ".\manage.py")) {
        throw "backend/manage.py not found."
    }

    python -m pip install -r requirements.txt
    python manage.py check
    python manage.py test

    Set-Location ..
}

# --------------------------------------------------
# 2. Fresh npm ci + production build
# --------------------------------------------------
Run-Check "Fresh npm ci + production build" {

    Set-Location ".\frontend"

    if (-not (Test-Path ".\package-lock.json")) {
        throw "frontend/package-lock.json not found."
    }

    npm ci
    npm run build

    if (-not (Test-Path ".\dist")) {
        throw "Production dist directory was not generated."
    }

    Set-Location ..
}

# --------------------------------------------------
# 3. Docker / Compose runtime
# --------------------------------------------------
Run-Check "Docker / Compose runtime" {

    docker --version
    docker compose version

    docker compose config

    docker compose build
    docker compose up -d

    Start-Sleep -Seconds 10

    docker compose ps

    $containers = docker compose ps --status running --format "{{.Name}}"

    if ([string]::IsNullOrWhiteSpace($containers)) {
        throw "No Docker Compose containers are running."
    }

    Write-Host "`nRunning containers:" -ForegroundColor Yellow
    docker compose ps

    docker compose exec backend python manage.py check
}

# --------------------------------------------------
# 4. Live Render deployment
# --------------------------------------------------
Run-Check "Live Render deployment" {

    $RenderUrl = $env:AWA_RENDER_URL

    if ([string]::IsNullOrWhiteSpace($RenderUrl)) {
        throw "AWA_RENDER_URL is not set. Example: https://your-backend.onrender.com"
    }

    $RenderUrl = $RenderUrl.TrimEnd("/")

    Write-Host "Checking: $RenderUrl" -ForegroundColor Yellow

    $health = Invoke-WebRequest `
        -Uri "$RenderUrl/api/health/" `
        -Method GET `
        -UseBasicParsing `
        -TimeoutSec 30

    if ($health.StatusCode -ne 200) {
        throw "Render health endpoint returned HTTP $($health.StatusCode)."
    }

    Write-Host "Render health endpoint returned HTTP 200." -ForegroundColor Green
}

# --------------------------------------------------
# 5. Real ad-provider integration
# --------------------------------------------------
Run-Check "Real ad-provider integration" {

    $Provider = $env:AWA_AD_PROVIDER
    $WebhookSecret = $env:AWA_AD_WEBHOOK_SECRET

    if ([string]::IsNullOrWhiteSpace($Provider)) {
        throw "AWA_AD_PROVIDER is not configured."
    }

    if ($Provider -eq "demo") {
        throw "Demo/provider-free ads are configured. Real ad provider required."
    }

    if ([string]::IsNullOrWhiteSpace($WebhookSecret)) {
        throw "AWA_AD_WEBHOOK_SECRET is not configured."
    }

    Write-Host "Configured provider: $Provider" -ForegroundColor Yellow
    Write-Host "Webhook secret: configured" -ForegroundColor Yellow

    if ([string]::IsNullOrWhiteSpace($env:AWA_RENDER_URL)) {
        throw "AWA_RENDER_URL is required for live ad-provider verification."
    }

    $RenderUrl = $env:AWA_RENDER_URL.TrimEnd("/")

    Write-Host "Checking production backend..." -ForegroundColor Yellow

    $health = Invoke-WebRequest `
        -Uri "$RenderUrl/api/health/" `
        -Method GET `
        -UseBasicParsing `
        -TimeoutSec 30

    if ($health.StatusCode -ne 200) {
        throw "Production backend is not healthy."
    }

    Write-Host "Backend is reachable." -ForegroundColor Green
    Write-Host "Provider credentials/configuration are present." -ForegroundColor Green
    Write-Host "A real ad impression/reward transaction must still be exercised with the provider test environment." -ForegroundColor Yellow
}

# --------------------------------------------------
# Final report
# --------------------------------------------------

Write-Host "`n`n==================================================" -ForegroundColor Magenta
Write-Host "AWA FINAL VERIFICATION REPORT" -ForegroundColor Magenta
Write-Host "==================================================" -ForegroundColor Magenta

$Results | Format-Table -AutoSize

$Passed = ($Results | Where-Object Status -eq "PASS").Count
$Failed = ($Results | Where-Object Status -eq "FAIL").Count
$Total  = $Results.Count

Write-Host "`nPassed: $Passed / $Total" -ForegroundColor Green
Write-Host "Failed: $Failed / $Total" -ForegroundColor Red

if ($Failed -gt 0) {
    Write-Host "`nAWA IS NOT FULLY VERIFIED." -ForegroundColor Red
    exit 1
}

Write-Host "`nALL AUTOMATED CHECKS PASSED." -ForegroundColor Green
Write-Host "Note: a real ad-provider transaction still requires provider-side test execution." -ForegroundColor Yellow

# Optional cleanup
Write-Host "`nStopping Docker Compose..." -ForegroundColor Yellow
docker compose down
