# Phase 4 — Explore Features Section

## Implemented

- Replaced the inert JavaScript-only Explore Features control with a native, keyboard-accessible `href="#features"` anchor.
- Added the matching, unique `id="features"` section directly below the home hero.
- Added six descriptions grounded in existing project functionality: 60 levels, worm/apple/obstacle/portal gameplay, hint/undo/restart tools, scores/stars/progress, achievements/leaderboard, and wallet/reward history.
- Reward copy explicitly states that rewarded-ad eligibility depends on provider completion and backend verification; it does not promise an ad or reward when the mock provider is unavailable.
- Added a Start Adventure call-to-action that uses the existing `start` handler.
- Added responsive 3-column, 2-column and 1-column layouts for desktop, tablet and mobile widths.
- Added anchor scroll offset and `prefers-reduced-motion` handling.

## Static verification

Run from the project root:

```powershell
python .\scripts\verify_phase4_features.py
```

The script checks anchor/target uniqueness, accessibility association, feature count and descriptions against existing app/API markers, responsive breakpoints, and reduced-motion support.

## Runtime acceptance still required

A successful source/static check does not prove browser behavior. Complete these checks on the target machine:

1. `cd frontend; npm ci; npm run build`.
2. Open the home page on desktop, activate Explore Features by mouse and keyboard, and confirm the viewport lands on the section.
3. Repeat at a mobile viewport (320px, 375px and 430px); confirm cards stack without horizontal overflow and the anchor lands correctly.
4. Activate Start Adventure from the feature section and confirm the existing start/register behavior is preserved.
5. Test with reduced motion enabled and confirm the page does not animate the scroll.

No backend, database, migrations, Docker volumes, game rules, or anti-cheat code were changed for Phase 4.
