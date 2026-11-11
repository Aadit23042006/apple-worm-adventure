$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root '.env.production'
if (-not (Test-Path $envFile)) { throw 'Missing .env.production. Run .\scripts\PREPARE-PRODUCTION.ps1 first.' }
$raw = Get-Content -Raw -LiteralPath $envFile
if ($raw -match '(?im)^\s*[^#\r\n]+=.*CHANGE_ME') { throw 'Production environment still contains CHANGE_ME placeholders. No secrets were displayed.' }
$required = @('DJANGO_SECRET_KEY','DJANGO_DEBUG','DJANGO_ALLOWED_HOSTS','POSTGRES_DB','POSTGRES_USER','POSTGRES_PASSWORD','AWA_DOMAIN','ACME_EMAIL','AD_PROVIDER','AD_PROVIDER_ADAPTER','AD_PROVIDER_WEBHOOK_SECRET','EMAIL_HOST','EMAIL_HOST_USER','EMAIL_HOST_PASSWORD','CORS_ALLOWED_ORIGINS','CSRF_TRUSTED_ORIGINS','SECURE_SSL_REDIRECT','SESSION_COOKIE_SECURE','SESSION_COOKIE_HTTPONLY','CSRF_COOKIE_SECURE','SECURE_HSTS_SECONDS','SECURE_HSTS_INCLUDE_SUBDOMAINS','SECURE_HSTS_PRELOAD','SECURE_PROXY_SSL_HEADER_ENABLED','ALLOW_PROVIDER_FREE_DEMO_ADS')
$map = @{}
foreach ($line in ($raw -split "`r?`n")) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $map[$Matches[1]] = $Matches[2].Trim() }
}
$missing = @($required | Where-Object { -not $map.ContainsKey($_) -or [string]::IsNullOrWhiteSpace($map[$_]) })
if ($missing.Count) { throw ('Missing required variables: ' + ($missing -join ', ')) }
if ($map.DJANGO_DEBUG.ToLower() -ne 'false') { throw 'DJANGO_DEBUG must be false.' }
foreach ($key in @('SECURE_SSL_REDIRECT','SESSION_COOKIE_SECURE','SESSION_COOKIE_HTTPONLY','CSRF_COOKIE_SECURE','SECURE_PROXY_SSL_HEADER_ENABLED')) { if ($map[$key].ToLower() -ne 'true') { throw "$key must be true in production." } }
if ($map.ALLOW_PROVIDER_FREE_DEMO_ADS.ToLower() -ne 'false') { throw 'ALLOW_PROVIDER_FREE_DEMO_ADS must be false.' }
if ([int]$map.SECURE_HSTS_SECONDS -lt 31536000) { throw 'SECURE_HSTS_SECONDS must be at least 31536000.' }
if ($map.SECURE_HSTS_INCLUDE_SUBDOMAINS.ToLower() -ne 'false' -or $map.SECURE_HSTS_PRELOAD.ToLower() -ne 'false') { throw 'HSTS subdomain and preload flags must remain false until separately approved.' }
if ($map.DJANGO_SECRET_KEY.Length -lt 50) { throw 'DJANGO_SECRET_KEY must contain at least 50 characters.' }
if ($map.POSTGRES_PASSWORD.Length -lt 24) { throw 'POSTGRES_PASSWORD must contain at least 24 characters.' }
if (($map.DJANGO_ALLOWED_HOSTS -split ',') -notcontains $map.AWA_DOMAIN) { throw 'DJANGO_ALLOWED_HOSTS must include AWA_DOMAIN.' }
$origin = 'https://' + $map.AWA_DOMAIN
if (($map.CORS_ALLOWED_ORIGINS -split ',') -notcontains $origin) { throw 'CORS_ALLOWED_ORIGINS must include https://AWA_DOMAIN.' }
if (($map.CSRF_TRUSTED_ORIGINS -split ',') -notcontains $origin) { throw 'CSRF_TRUSTED_ORIGINS must include https://AWA_DOMAIN.' }
if ($map.FRONTEND_BASE_URL -ne $origin) { throw 'FRONTEND_BASE_URL must equal https://AWA_DOMAIN.' }
if ($map.AWA_DOMAIN -notmatch '^[A-Za-z0-9.-]+$' -or $map.AWA_DOMAIN -match 'CHANGE_ME|example\.com$') { throw 'AWA_DOMAIN must be a real assigned hostname, not an example or placeholder.' }
if ($map.AD_PROVIDER -in @('mock','none','disabled','provider_free_demo')) { throw 'A real ad provider must be selected for production.' }
if ($map.AD_PROVIDER_ADAPTER -match 'CHANGE_ME' -or $map.AD_PROVIDER_WEBHOOK_SECRET -match 'CHANGE_ME') { throw 'Configure a real ad provider adapter and matching webhook signing secret.' }
if ($map.EMAIL_HOST -match 'CHANGE_ME' -or $map.EMAIL_HOST_PASSWORD -match 'CHANGE_ME') { throw 'Configure a real SMTP provider.' }
if ($map.CORS_ALLOWED_ORIGINS -notmatch '^https://') { throw 'CORS_ALLOWED_ORIGINS must be an HTTPS origin.' }
if ($map.CSRF_TRUSTED_ORIGINS -notmatch '^https://') { throw 'CSRF_TRUSTED_ORIGINS must be an HTTPS origin.' }
Push-Location $root
try {
    docker compose -f docker-compose.production.yml --env-file .env.production config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose configuration validation failed.' }
} finally { Pop-Location }
Write-Host 'Production environment and Compose syntax validation passed. Values were not printed.'
Write-Host 'This does not prove DNS, certificates, provider callbacks, SMTP delivery, or public deployment.'
