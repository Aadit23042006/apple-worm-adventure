# Phase 6 Test 9 — Portal progression and responsive-input fix

## Changes in this candidate

1. **Portal objective feedback:** the game now explains that every required apple must be collected before the portal can complete the level. The supplied recording's Level 35 screen shows `Apples 4`; therefore, entering the portal with four apples still remaining must not trigger completion. This matches the VELoop specification's portal validation rule.
2. **Completion recovery after refresh:** if the final portal checkpoint was successfully saved but the browser refreshed before the completion API call finished, startup now retries the server-side completion endpoint using the server-stored checkpoint. The browser does not award score, coins, or level progression locally.
3. **Next-level continuation:** after server-confirmed completion, the dialog's Continue button starts the next sequential level instead of only returning to the level list.
4. **Completion retry affordance:** if all required objectives are complete and the worm is at the portal but the automatic completion request did not finish, a Complete Level action is shown so the user can retry server confirmation.
5. **Mobile swipe input:** the board now supports four-direction swipe gestures and captures touch gestures on the board without disabling normal page scrolling elsewhere.
6. **Regression coverage:** added a backend API regression test for Level 35 completion, Level 36 unlock, and closing the ACTIVE session.
7. **Test procedure:** documented the Test 9 viewport matrix (1920×1080, 1366×768, 768×1024, 390×844, 320×568), rotation, controls, refresh recovery, and evidence requirements.

## Company requirement alignment

- VELoop portal completion requires correct position, worm state, required apples, and objective completion.
- All apples must be collected before completion.
- Level progression is sequential: completing a level unlocks the next.
- Desktop keyboard controls and mobile swipe/direction controls are required.

## Verification status — important

- TSX syntax parse after the final edits: PASS.
- Backend Python `compileall`: PASS.
- Existing selected source audits: 67/67 static checks passed (Phase 1: 11/11; Phase 4: 15/15; Phase 5/6: 14/14; Phase 7/8: 27/27).
- New Test 9 source assertions: 8/8 passed (refresh recovery, next-level action, swipe input, portal guidance, regression-test presence, and viewport-matrix documentation).
- Frontend TypeScript check was run successfully before the final UI-feedback/retry additions; it could not be rerun after the uploaded `node_modules` were partially removed by a timed-out `npm ci`.
- Frontend production build: BLOCKED. The archive's installed dependencies are Windows-specific; Vite's native Rolldown binding for this Linux verification environment is missing. `npm ci` timed out while attempting dependency installation.
- Django checks/tests, PostgreSQL integration, Docker startup, and actual desktop/mobile browser tests were not run in this environment.
- Therefore this is an updated source candidate, **not a certified 100% company-compliance sign-off**. Complete the documented Test 9 browser matrix and full Phase 6 gates before declaring PASS.

## Safe packaging

The distributable excludes `.env`, node_modules, Python caches, database backups, and local secret/backup artifacts. Copy `.env.example` to `.env` and supply environment-specific values locally. Existing user database volumes are not modified by this source patch.
