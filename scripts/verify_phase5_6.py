from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "src"
APP = SRC / "App.tsx"
errors = []
checks = []

def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    if not ok:
        errors.append(name)

# All active and retained frontend source files must be readable as UTF-8.
files = [p for p in SRC.rglob("*") if p.is_file()]
utf8_ok = True
mojibake_hits = []
markers = ("ðŸ", "Ã", "Â", "â€", "ï¿½", "\ufffd")
for path in files:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        utf8_ok = False
        continue
    if any(marker in content for marker in markers):
        mojibake_hits.append(str(path.relative_to(ROOT)))
check("Frontend source files decode as UTF-8", utf8_ok, f"{len(files)} files inspected")
check("No common mojibake markers remain", not mojibake_hits, ", ".join(mojibake_hits))

app = APP.read_text(encoding="utf-8")
for label, fragment in [
    ("Explicit data states", "'loading' | 'success' | 'empty' | 'error'"),
    ("Bounded loading timeout", "15000"),
    ("Retry action", "Try again"),
    ("Leaderboard empty message", "No leaderboard scores yet"),
    ("Achievements empty message", "No achievements are available yet"),
    ("Abort in-flight request on timeout", "controller.abort()"),
    ("Leaderboard response validation", "response?.leaderboard"),
    ("Achievements response validation", "response?.achievements"),
]:
    check(label, fragment in app)

api_tests = (ROOT / "backend" / "core" / "tests_phase3_achievements.py").read_text(encoding="utf-8")
for label, fragment in [
    ("New account achievements test", "test_new_account_receives_catalog_with_locked_state"),
    ("Empty achievements API test", "test_empty_achievement_catalog_returns_empty_array"),
    ("New account empty leaderboard test", "test_empty_leaderboard_returns_empty_array_for_new_account"),
    ("Existing account leaderboard test", "test_existing_player_appears_in_leaderboard_with_server_score"),
]:
    check(label, fragment in api_tests)

for name, ok, detail in checks:
    print(f"{'PASS' if ok else 'FAIL'} | {name}" + (f" | {detail}" if detail else ""))
print(f"\nRESULT: {sum(ok for _, ok, _ in checks)}/{len(checks)} static checks passed")
sys.exit(1 if errors else 0)
