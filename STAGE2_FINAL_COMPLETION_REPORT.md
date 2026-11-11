# Stage 2 — Final Verification Report

Date: 2026-11-10
Project: APPLE WORM ADVENTURE (VELOOP)
Environment: Isolated Docker backend and local frontend build

## 1. Automated verification

| Verification | Result |
|---|---|
| Full Django backend suite | PASS — 111/111 |
| Level 23 move-limit boundary tests | PASS — 3/3 |
| Django system checks | PASS |
| Frontend TypeScript check | PASS |
| Frontend Vite production build | PASS |

## 2. Evidence files

- EVIDENCE/STAGE2_FINAL_20261110/backend_111_tests.txt
- EVIDENCE/STAGE2_FINAL_20261110/level23_boundary_3_tests.txt
- EVIDENCE/STAGE2_FINAL_20261110/frontend_production_build.txt

## 3. Gameplay verification

The following eight functional areas were reported as passing during
the Stage 2 verification process:

1. Worm movement and direction changes.
2. Apple collection and worm growth.
3. Wall and obstacle collision.
4. Self-collision.
5. Move-limit failure and completion boundary.
6. Portal completion.
7. Checkpoint save and restore.
8. Level progression.

Evidence quality varies: some checks have automated/backend evidence,
while others rely on user-reported browser runtime verification.
They must not all be represented as independently automated tests.

## 4. Limitations and outstanding verification

- Real rewarded-ad provider integration is not verified.
- The local mock does not simulate a completed real advertisement.
- Full clause-by-clause verification of all 127 company requirements
  is not complete.
- Mobile device and cross-browser acceptance still require evidence.
- Final release and deployment verification remain outstanding.

## 5. Conclusion

The listed Stage 2 automated regression checks passed.
Stage 2 evidence is substantially complete, but final sign-off must
account for the evidence qualifications and outstanding items above.

This report does not certify 100% completion of the 127 company
requirements or final production release readiness.
