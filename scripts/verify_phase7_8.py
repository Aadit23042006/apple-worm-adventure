from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
checks = []

def check(name, ok):
    checks.append((name, bool(ok)))

views = (ROOT / 'backend/core/views.py').read_text(encoding='utf-8')
urls = (ROOT / 'backend/core/urls.py').read_text(encoding='utf-8')
models = (ROOT / 'backend/core/models.py').read_text(encoding='utf-8')
app = (ROOT / 'frontend/src/App.tsx').read_text(encoding='utf-8')
css = (ROOT / 'frontend/src/styles.css').read_text(encoding='utf-8')
pdf_audit = (ROOT / 'docs/PHASE7_8_AUTH_ACCESSIBILITY.md').read_text(encoding='utf-8')

for route in ('auth/register/', 'auth/login/', 'auth/refresh/', 'auth/logout/', 'auth/me/', 'auth/verify-email/', 'auth/password-reset/request/', 'auth/password-reset/confirm/'):
    check(f'Route exists: {route}', route in urls)

check('Refresh token stored as digest', 'token_hash=digest(raw)' in views)
check('Refresh token expiry checked', 'expires_at__gt=timezone.now()' in views)
check('Refresh token revocation on logout', 'revoked_at=timezone.now()' in views)
check('Email verification expiry checked', 'obj.expires_at <= timezone.now()' in views)
check('Password reset token is single-use', 'used_at__isnull=True' in views and 'obj.used_at = timezone.now()' in views)
check('Password reset expiry checked', 'obj.expires_at <= timezone.now()' in views)
check('Password reset invalidates API tokens', 'Token.objects.filter(\n            user=obj.user\n        ).delete()' in views)
check('Password reset revokes refresh sessions', 'user=obj.user,\n            revoked_at__isnull=True' in views)
check('Password reset frontend request flow', '/auth/password-reset/request/' in app)
check('Password reset frontend confirm flow', '/auth/password-reset/confirm/' in app)
check('Forgot password entry point', 'Forgot password?' in app)
check('Reset-password URL route', "pathName !== '/reset-password'" in app)
check('Reset link token removed from browser URL', "replaceState({}, document.title, '/reset-password/')" in app)
check('Skip-to-main-content link', 'Skip to main content' in app and 'id="main-content"' in app)
check('Visible keyboard focus style', ':focus-visible' in css and 'outline: 3px solid' in css)
check('Reduced-motion preference disables animation', '@media(prefers-reduced-motion:reduce)' in css and 'animation:none!important' in css)
check('Reduced-motion preference disables transitions', 'transition:none!important' in css)
check('Status messages announced accessibly', 'aria-live="polite"' in app and 'aria-live="assertive"' in app)
check('PDF audit documents password reset is not a mandatory listed endpoint', 'password reset as a mandatory endpoint' in pdf_audit)

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
print(f'\nRESULT: {len(checks)-len(failed)}/{len(checks)} static checks passed')
if failed:
    sys.exit(1)
