$ErrorActionPreference = 'Stop'
if (-not (Test-Path '.env')) { throw 'Root .env file not found. Create it from .env.example first.' }
$envText = Get-Content '.env' -Raw
$domainMatch = [regex]::Match($envText, '(?m)^AWA_DOMAIN=(.+)$')
$emailMatch = [regex]::Match($envText, '(?m)^ACME_EMAIL=(.+)$')
if (-not $domainMatch.Success -or $domainMatch.Groups[1].Value.Trim() -match 'your-real-domain|example\.com|localhost') {
  throw 'Set AWA_DOMAIN to a real domain you control in .env.'
}
if (-not $emailMatch.Success -or $emailMatch.Groups[1].Value.Trim() -notmatch '@') {
  throw 'Set ACME_EMAIL to a valid contact email in .env.'
}
$domain = $domainMatch.Groups[1].Value.Trim()
Write-Host "Checking DNS for $domain ..."
Resolve-DnsName $domain -ErrorAction Stop | Format-Table Name,Type,IPAddress -AutoSize
Write-Host 'Checking local TCP ports 80 and 443 ...'
foreach ($port in 80,443) {
  $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
  if ($listener) { Write-Host "Port $port is already occupied:"; $listener | Format-Table -AutoSize }
  else { Write-Host "Port $port has no local listener (available for Caddy)." }
}
Write-Host 'Preflight done. Verify DNS points to this host and firewall/router allows inbound TCP 80/443 before deployment.'
