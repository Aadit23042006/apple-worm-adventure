$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ProjectRoot
try {
    & docker compose -p 'awa-apple-worm' stop
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop the AWA Compose services.' }
    Write-Host 'AWA services stopped. Persistent database volume awa_fresh_install_data_v1 was preserved.' -ForegroundColor Green
} finally { Pop-Location }
