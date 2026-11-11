# Phase 5 — Leaderboard & Achievements Empty States

## Implementation
- Leaderboard and achievements pages now own their request state instead of depending on stale parent arrays.
- UI states are explicit: `loading`, `success`, `empty`, and `error`.
- Empty leaderboard response shows a useful next step: complete a level to earn a score.
- Empty achievement catalogue has a clear empty message; a new account with a catalogue receives the achievements as locked rather than being misrepresented as having unlocked achievements.
- Failed requests expose the API error and a Retry action.
- Requests are aborted after a 15-second deadline, so the page cannot remain in a permanent loading state.
- Invalid response shapes are treated as errors, not as empty success.
- Backend integration tests cover new-account and existing-account response behavior.

## Verification
Run from the project root:

```powershell
python scripts/verify_phase5_6.py
cd frontend
npm ci
npm run build
cd ..\backend
python manage.py test core.tests_phase3_achievements --verbosity=2
```

Run backend tests only against an isolated test database. Do not point test settings at the recovered production database.
