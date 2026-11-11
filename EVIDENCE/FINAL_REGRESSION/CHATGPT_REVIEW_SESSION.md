# Review and targeted correction report — AWA release candidate

Review date: 2026-11-10
Input archive: `AWA_RELEASE_CANDIDATE_CHECKPOINT_LOGOUT_FIX.zip`
Company specification: `requirements/Apple-G_VELoop_Full_Stack.pdf` (55 pages; numbered sections 1–127)

## Scope and integrity

- Original uploaded ZIP was left unchanged.
- Input ZIP archive integrity check: PASS.
- Extracted project files: 193.
- Company traceability CSVs contain 127 rows, matching the 127 numbered sections.
- `PHASE1_TRACEABILITY_127_EXACT.csv`: all 127 are `NOT YET VERIFIED`.
- `PHASE1_TRACEABILITY_127_EVIDENCE_REVIEW.csv` and `PHASE1_FINAL_TRACEABILITY_REVIEW.csv`: all 127 are `PARTIAL`.
- No clause-by-clause PASS claim is made.

## Checkpoint authentication review

The submitted source contains:
- `frontend/src/authClient.ts` with DRF `Token` header handling, one shared refresh promise, one retry, stale-token comparison, definitive-expiry handling, and transient refresh failure handling.
- `backend/core/views.py` login and refresh endpoints using `token` and `refresh_token`, consistent with the frontend contract.
- A checkpoint endpoint retaining authenticated-user and ACTIVE-session ownership filtering.
- `backend/core/tests_checkpoint_auth.py` with 14 checkpoint/authentication tests.
- `backend/core/tests_multi_device_logout.py` with 6 cross-device logout regression tests.
- A per-device refresh-session logout change which retains legacy revoke-all behavior when no matching refresh token is supplied.

The included `EVIDENCE/FINAL_REGRESSION/FINAL_REGRESSION_REPORT.md` documents a reproduced cross-device logout defect and a real-browser recovery scenario. This review inspected the source and report but did not independently rerun that browser scenario.

### Additional defect corrected in this review

`frontend/src/App.tsx` session restoration previously caught every `/auth/me/` request error by clearing both stored tokens and forcing the login screen. That contradicted `authClient.ts`, which intentionally preserves credentials for network failures, HTTP 429, and server 5xx responses.

The catch handler now reports the error without deleting credentials or forcing logout. Definitive credential rejection is still handled by `authClient` through `SESSION_EXPIRED_EVENT`. Authentication, permission checks, and checkpoint ownership were not weakened.

## Tests executed in this review environment

| Check | Result |
|---|---|
| ZIP integrity | PASS |
| Python `compileall` for backend | PASS |
| Phase 2 static audit | 8/8 PASS |
| Phase 1 source audit | 11/11 PASS |
| Phase 4 static feature audit | 15/15 PASS |
| Phase 5–6 static audit | 14/14 PASS |
| Phase 7–8 static audit | 27/27 PASS |
| Combined static assertions | 75/75 PASS |

## Tests not executed in this review environment

- `npm ci` did not complete before the command timeout. The available Node version here is v22.16.0, while the uploaded lockfile's `jsdom` dependency warns that it requires Node 22.22.2 or 24.15.0+. The user's previously reported Node 24.19.0 is compatible with that dependency requirement.
- Consequently, frontend Vitest and production build were not rerun after the additional session-restore correction.
- Docker is not installed in this execution environment.
- Django is not installed in this execution environment; PostgreSQL-backed Django tests were not rerun here.
- Physical mobile device testing, full gameplay acceptance, multi-viewport browser checks, live ad-provider verification, deployment checks, and fresh-install PowerShell verification were not performed here.

## Evidence reconciliation issue

Correction from the final archive inventory (2026-11-11): the raw historical 111-test console output is present at `EVIDENCE/STAGE2_FINAL_20261110/backend_111_tests.txt`. It records 111 tests and `OK`. This is historical evidence, not a fresh run in the current audit environment. The current environment cannot reproduce Django/PostgreSQL tests because Docker, PostgreSQL and backend dependencies are unavailable.

## Company requirement status

The PDF's numbered sections 1–127 were confirmed against the existing 127-row traceability file. The existing traceability reports classify every row as PARTIAL or NOT YET VERIFIED. The project is therefore not eligible for a RELEASE READY or 100% company-compliant claim at this point.

## Change log

- `frontend/src/App.tsx` — changed session-restore error handling so transient API/network failures do not clear persisted credentials or force logout. Definitive auth failures remain handled by `authClient` events.
- `SESSION_RESTORE_TRANSIENT_ERROR_FIX.md` — added this focused correction record.
- `EVIDENCE/FINAL_REGRESSION/CHATGPT_REVIEW_SESSION.md` — added this review's verification and limitation record.
