# Phase 6 — Final Testing

## Automated gates
1. `python manage.py check`
2. `python manage.py check --deploy` in production configuration
3. `python manage.py migrate --check`
4. `python manage.py validate_production`
5. `python manage.py validate_game_levels`
6. `python manage.py test`
7. `npm ci`
8. `npm run build`

## Manual acceptance
### Gameplay — 20%
- Landing/login/dashboard/level selection.
- Worm movement and touch controls.
- Apple collection and growth.
- Body/obstacle collision.
- Portal completion.
- Multiple objectives.
- 50+ levels and sequential unlocking.
- Stars, score and move tracking.
- Restart, undo and hint.
- Failure and revive.
- No-revive objective levels reject Revive at both opportunity creation and reward claim.
- Desktop and mobile layouts.

### Game Engineering — 15%
- Data-driven levels.
- Deterministic server validation.
- Checkpoint persistence.
- Completion idempotency.
- No client-authoritative score/reward mutation.

### Full Stack — 15%
- Register/login/logout.
- Email verification.
- Refresh session.
- Password reset.
- Dashboard persistence.
- Game history/progress.
- Leaderboard and achievements.
- Database persistence.
- API authentication and validation.

### VELoop Economy — 25%
- Wallet and wallet ledger.
- Reward ledger.
- Ad opportunity and provider verification.
- Idempotency.
- Cooldown and calendar-day limits.
- Revive.
- Double Score.
- Double Coins.
- Extra Moves.
- Hint and Booster.
- Reward history.
- Server-side calculation.

### UI/UX — 10%
- Responsive desktop/mobile UI.
- Clear game states.
- Level progress.
- Wallet/reward feedback.
- Error and success notices.

### Audio/Feedback — 5%
- Movement, apple, portal, failure, reward and completion feedback.
- Music/sound controls.

### Documentation — 5%
- README.
- Architecture.
- Economy.
- Deployment.
- Demo checklist.

### Code Quality — 5%
- No placeholder production secrets.
- No generated cache committed.
- CI passes.
- Tests pass.
- No destructive changes to existing features.

## Final evidence
Capture:
- CI green run;
- production validation output;
- level validation output;
- test output;
- frontend production build output;
- desktop demo;
- mobile demo;
- reward/ledger demo;
- deployment configuration.


## Test 9 — Final desktop and mobile verification

Run this after the backend migrations and frontend production build are available.
Do not mark this test PASS from source inspection alone.

### Required browser matrix
- Desktop: 1920×1080 and 1366×768.
- Tablet: 768×1024.
- Mobile: 390×844 and 320×568.
- Repeat gameplay after rotating the mobile device between portrait and landscape.

### Required gameplay checks
1. Desktop Arrow keys and WASD move the worm exactly one cell per valid input.
2. Mobile swipe in all four directions and the on-screen direction buttons move the worm exactly one cell.
3. The board captures swipe gestures without scrolling the page; the rest of the page remains scrollable.
4. Collect every required apple before the portal. A portal touch while apples remain must not complete the level, in accordance with the portal-validation requirement.
5. After the final apple is collected and the worm reaches the portal, the backend confirms completion, the completion dialog appears, and Continue starts the next unlocked level.
6. Refresh immediately after the final portal checkpoint. If the browser closed before the completion request finished, the app retries completion against the server-stored checkpoint and shows the completion dialog only after server confirmation.
7. Confirm the completed level is marked complete, the next level is unlocked, and no stale ACTIVE session reopens the previous level.
8. Confirm no clipped controls, horizontal page overflow, unreadable HUD, or overlapping dialogs at every viewport.
9. Check browser console/network for uncaught errors and failed gameplay/progress API requests.

### Evidence to attach
Record each viewport, browser/device, keyboard/swipe method, level completed, next level opened, refresh-recovery result, console result, and screenshot/video filename. A browser-run result is required before sign-off.
