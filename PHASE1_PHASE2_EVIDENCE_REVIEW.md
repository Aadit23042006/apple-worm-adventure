# Apple Worm Adventure — Phase 1 & Phase 2 Evidence Review

**Audit date:** 2026-11-08  
**Specification:** `Apple-G_VELoop_Full_Stack.pdf` (55 pages)  
**Traceability scope:** 127 numbered requirements  
**Source package reviewed:** `AWA_PHASE1_REVIEWED_SOURCE.zip`  
**CSV reviewed:** `PHASE1_TRACEABILITY_127_EXACT.csv`

## Executive result

- The supplied original PDF is present in the reviewed source package.
- The supplied exact traceability CSV contains 127 rows.
- The ZIP archive integrity check passed.
- Fresh Windows/Docker verification evidence is now available: clean frontend install, TypeScript/Vite production build, isolated Docker Compose validation, Django system check, and PostgreSQL-backed Django tests. The user's console transcript reports **84/84 backend tests passing**.
- The earlier source static audit reports **11/11 checks passing**.
- The detailed evidence review still classifies **127/127 requirements as PARTIAL**. No row is marked PASS because the package does not provide clause-specific evidence for every compound requirement, and several requirements need human, browser, deployment, reference-game, or demo evidence.

**Phase 1: NOT SIGNED OFF.**  
**Phase 2: Backend rewarded-ad verification tests PASS; end-to-end/provider acceptance remains PARTIAL.**

## Fresh runtime evidence

`PHASE1_LOCAL_VERIFICATION_RESULTS.txt` inside the submitted ZIP records:
1. `npm ci` — PASS.
2. Frontend production build — PASS; `dist/index.html` created.
3. Isolated Docker Compose config — PASS.
4. Fresh Django/PostgreSQL test stack — Django check, migrations, and test suite exited 0 against isolated PostgreSQL 16.

The separately supplied Windows console transcript reports:
- Django `manage.py check`: no issues.
- 84 backend tests found and run; 84 passed.
- Test groups include authentication/password reset, game integrity/anti-cheat, economy, leaderboard/achievements, revive restrictions, and rewarded-ad verification.
- The test script removed only its dedicated isolated test stack/volume. No production database volume was targeted.

## Phase 2 — rewarded-ad findings

### Supported by source and test evidence
- Default `UnconfiguredAdProvider` has `available = False`.
- The local mock raises `AdProviderUnavailable`; it does not simulate ad completion.
- A reward claim is rejected unless the opportunity is verified.
- Signed callback verification is tested.
- Callback requires an ad session that has started.
- Invalid signature does not verify or grant a reward.
- Duplicate callback/claim behavior is tested for idempotency.
- Successful flow records the lifecycle through `OFFERED → REQUESTED → AD_STARTED → AD_COMPLETED → VERIFYING → VERIFIED → GRANTED`.
- Cooldown and same-event idempotency tests are present.

### Remaining Phase 2 acceptance evidence
- No real ad provider/vendor adapter or vendor credentials are included; live provider playback is not demonstrated.
- No captured browser E2E recording of the full user journey is included.
- No staging callback from a real provider is included.
- Production provider readiness must not be claimed. This is not automatically a specification failure: PDF section 111 permits a provider abstraction/mock where the actual provider cannot be used locally, but it forbids pretending a fake completion is a real integration.

## Phase 1 requirements needing additional evidence

Examples of evidence that cannot be inferred from source or a backend test run:
- Reference game actually installed/played and observations recorded (PDF sections 2 and 127).
- Originality/IP review for all artwork, layouts, sound, music, and branding (section 3).
- Dynamic `VITE_GAME_NAME` override shown across every required surface (sections 4–9).
- Browser/mobile gameplay and responsive controls, audio, animations, particles, and UI state behavior.
- Production deployment URLs and actual deployed application validation (section 116).
- Demo video covering the complete gameplay, economy, backend, and responsive scenarios (section 117).
- Final submission fields and reviewer sign-off (section 126).

## Status definitions used in the attached CSV

- **PASS** — requirement-specific implementation and acceptance evidence are both attached.
- **PARTIAL** — relevant source and/or aggregate test evidence exists, but at least one required acceptance proof is missing.
- **FAIL** — a reproducible defect or contradiction has been demonstrated.
- **NOT VERIFIED** — no adequate evidence is available yet.

The attached `PHASE1_TRACEABILITY_127_EVIDENCE_REVIEW.csv` preserves all original 127 rows and original PDF wording/page references, adds source-review findings and next-evidence requirements, and records the fresh runtime evidence. It marks all 127 as PARTIAL rather than converting aggregate test success into unsupported PASS claims.

## Safe next actions

1. Collect browser evidence for every visible feature and mobile/desktop controls.
2. Perform the game-name override test using at least two alternate values and verify all required UI/metadata surfaces.
3. Capture reference-game study notes and an originality review.
4. Run staging rewarded-ad E2E with a real provider if available; otherwise document the permitted unavailable/mock mode and its limitations.
5. Attach deployment URLs, demo video, README/documentation review, and completed submission fields.
6. Revisit every PARTIAL row, mark PASS only when the specific acceptance evidence is attached, and obtain reviewer sign-off.

## Safety note

The verification stack described by the evidence is isolated. Do not run destructive compose commands or remove production database volumes while completing the remaining checks.
