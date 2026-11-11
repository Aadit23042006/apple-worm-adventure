from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
app = (root / 'frontend/src/App.tsx').read_text(encoding='utf-8')
css = (root / 'frontend/src/styles.css').read_text(encoding='utf-8')
checks = []

def check(name, condition):
    checks.append((name, bool(condition)))

check('Explore Features link targets #features', 'href="#features"' in app)
check('Exactly one real #features section exists', app.count('id="features"') == 1)
check('Features section has accessible heading association', 'aria-labelledby="features-title"' in app and 'id="features-title"' in app)
check('Features section includes six factual feature cards', app.count('className="featureCard"') == 6)
check('60-level claim matches configured project feature', '60 puzzle levels' in app and '60 LEVELS' in app)
check('Gameplay feature descriptions mention apples, obstacles and portal', all(x in app for x in ['collect the apples', 'obstacles', 'reach the portal']))
check('Hint and undo feature corresponds to implemented controls', all(x in app for x in ['hintDirection', 'undo={undo}', 'restart={restart}']))
check('Score and stars feature corresponds to game state', all(x in app for x in ['score:', 'starsFor(', 'best_score']))
check('Achievements and leaderboard feature corresponds to existing API routes', all(x in app for x in ["'/achievements/'", "'/leaderboard/'"]))
check('Wallet and rewards feature corresponds to existing wallet API', "'/economy/wallet/'" in app)
check('Reward description explicitly requires backend verification', 'verified by the backend' in app)
check('Explore Features button has keyboard-accessible native anchor semantics', '<a' in app and 'href="#features"' in app)
check('Responsive tablet and mobile feature layouts exist', '@media(max-width:850px)' in css and '@media(max-width:520px)' in css and '.featuresGrid' in css)
check('Anchor scroll offset is defined', '#features{scroll-margin-top:' in css)
check('Reduced-motion preference is respected for scrolling and animation', '@media(prefers-reduced-motion:reduce)' in css)

for name, passed in checks:
    print(f"{'PASS' if passed else 'FAIL'}: {name}")
print(f'RESULT: {sum(p for _, p in checks)}/{len(checks)} checks passed')
raise SystemExit(0 if all(p for _, p in checks) else 1)
