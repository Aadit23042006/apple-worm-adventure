from pathlib import Path

p = Path(".env")
if not p.exists():
    raise SystemExit("STOP: .env file not found. No changes made.")

lines = p.read_text(encoding="utf-8-sig").splitlines()

updates = {
    "SECURE_HSTS_INCLUDE_SUBDOMAINS": "True",
    "SECURE_HSTS_PRELOAD": "True",
}

for key, value in updates.items():
    lines = [line for line in lines if not line.startswith(key + "=")]
    lines.append(f"{key}={value}")

p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("PASS: Production HSTS variables configured.")
