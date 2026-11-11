from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "frontend/src/App.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend/src/styles.css").read_text(encoding="utf-8")
VIEWS = (ROOT / "backend/core/views.py").read_text(encoding="utf-8")
URLS = (ROOT / "backend/core/urls.py").read_text(encoding="utf-8")
PROVIDER = (ROOT / "backend/core/ad_providers.py").read_text(encoding="utf-8")

checks = {
    "reward provider fails closed by default":
        "class UnconfiguredAdProvider" in PROVIDER
        and "available = False" in PROVIDER
        and "never simulates a completed ad" in PROVIDER,
    "provider request cannot treat failure as completion":
        "def request_ad(" in VIEWS
        and "get_ad_provider()" in VIEWS
        and '"AD_UNAVAILABLE"' in VIEWS,
    "signed provider callback verification exists":
        "def ad_provider_callback(" in VIEWS
        and "hmac.new(" in VIEWS
        and "secrets.compare_digest(" in VIEWS,
    "reward claim requires verified state":
        'opportunity.status not in {"VERIFIED", "GRANTED"}' in VIEWS,
    "achievements screen is reachable from navigation":
        "setScreen('achievements')" in APP and "Achievements" in APP,
    "Explore Features target exists":
        'id="features"' in APP and 'href="#features"' in APP,
    "leaderboard/achievement pages have explicit loading/empty/error/retry states":
        all(x in APP for x in ["status === 'loading'", "status === 'empty'",
                               "status === 'error'", "Try again"]),
    "password reset UI and API flow exist":
        all(x in APP for x in ["forgot-password", "reset-password",
                               "password-reset/request/", "password-reset/confirm/"]),
    "visible mojibake markers absent from main UI source":
        not any(x in APP for x in ["ðŸ", "Ã", "â€"]),
    "reduced-motion preference is handled":
        "prefers-reduced-motion:reduce" in CSS,
    "backend password-reset routes are registered":
        "auth/password-reset/request/" in URLS and "auth/password-reset/confirm/" in URLS,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
print(f"RESULT: {len(checks)-len(failed)}/{len(checks)} static checks passed")
sys.exit(1 if failed else 0)
