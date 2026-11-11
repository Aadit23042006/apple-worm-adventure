from pathlib import Path

p = Path("docker-compose.yml")
s = p.read_text(encoding="utf-8")

old = '''      SECURE_HSTS_INCLUDE_SUBDOMAINS: "False"
      SECURE_HSTS_PRELOAD: "False"
      SECURE_PROXY_SSL_HEADER_ENABLED: "False"'''

new = '''      SECURE_HSTS_INCLUDE_SUBDOMAINS: ${SECURE_HSTS_INCLUDE_SUBDOMAINS:-False}
      SECURE_HSTS_PRELOAD: ${SECURE_HSTS_PRELOAD:-False}
      SECURE_PROXY_SSL_HEADER_ENABLED: ${SECURE_PROXY_SSL_HEADER_ENABLED:-False}'''

if old not in s:
    raise SystemExit("STOP: Expected configuration block not found. No file changed.")

p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("PASS: HSTS settings are now environment-configurable.")
