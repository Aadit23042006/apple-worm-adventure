$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$template = Join-Path $root '.env.production.example'
$target = Join-Path $root '.env.production'
if (-not (Test-Path $template)) { throw 'Missing .env.production.example.' }
if (Test-Path $target) { throw '.env.production already exists; refusing to overwrite it.' }
$content = Get-Content -Raw -LiteralPath $template
function New-Secret([int]$bytes) {
    $buffer = New-Object byte[] $bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($buffer).TrimEnd('=').Replace('+','-').Replace('/','_')
}
# Two different generated values are required for Django and PostgreSQL.
$lines = $content -split "`r?`n"
$django = New-Secret 64
$db = New-Secret 36
for ($i=0; $i -lt $lines.Length; $i++) {
    if ($lines[$i] -match '^DJANGO_SECRET_KEY=') { $lines[$i] = "DJANGO_SECRET_KEY=$django" }
    if ($lines[$i] -match '^POSTGRES_PASSWORD=') { $lines[$i] = "POSTGRES_PASSWORD=$db" }
}
[System.IO.File]::WriteAllText($target, ($lines -join "`n"), [System.Text.UTF8Encoding]::new($false))
if (Get-Command icacls.exe -ErrorAction SilentlyContinue) {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls.exe $target /inheritance:r /grant:r "$($identity):(R,W)" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not restrict .env.production file permissions.' }
}
Write-Host 'Created .env.production with unique Django and PostgreSQL secrets.'
Write-Host 'Provider, SMTP, public hostname, email, CORS and CSRF placeholders remain; edit them locally.'
Write-Host 'Secret values were not printed.'
