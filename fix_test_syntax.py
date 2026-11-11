from pathlib import Path

p = Path("backend/core/tests_phase5_6.py")
s = p.read_text(encoding="utf-8")

bad = "\\n\n    def test_duplicate_level_reward_does_not_credit_wallet_twice"
good = "\n    def test_duplicate_level_reward_does_not_credit_wallet_twice"

if bad not in s:
    raise SystemExit("STOP: Exact syntax issue not found. No changes made.")

p.write_text(s.replace(bad, good, 1), encoding="utf-8")
print("FIXED: Removed literal backslash-n before first new test.")
