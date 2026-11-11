# Apple Worm Adventure — Release Candidate Audit Report

**Audit basis:** uploaded `A.zip` and supplied 55-page VELoop Full Stack Developer Internship Task PDF.  
**Audit date:** 2026-11-08.  
**Decision:** **NOT APPROVED as a 100% tested/final production release.** This package is a cleaned source/audit candidate, not a certified final build.

## Results actually executed in this environment

| Check | Result | Meaning |
|---|---:|---|
| Uploaded ZIP CRC integrity | PASS | Archive entries are readable; this is not a runtime test. |
| Phase 1 static source audit | 11/11 PASS | Static assertions only. |
| Phase 4 static audit | 15/15 PASS | Static assertions only. |
| Phase 5–6 static audit | 14/14 PASS | Static assertions only. |
| Phase 7–8 static audit | 27/27 PASS | Static assertions only. |
| Backend Python syntax compilation | PASS | Python files compile; Django behavior is not proven. |
| 127-section requirement map | 127/127 mapped | The exact traceability CSV still has 127 `NOT YET VERIFIED` rows. |
| Final traceability review | 127/127 PARTIAL | No row is justified as fully PASS by this audit. |
| Frontend production build | NOT RUN | `npm ci` did not complete within the available execution window; no build result. |
| Django checks / migrations / tests | NOT RUN | Django, DRF and psycopg are unavailable in this environment. |
| Docker Compose / PostgreSQL integration | NOT RUN | Docker CLI is unavailable in this environment. |
| Desktop/mobile browser E2E | NOT RUN | Requires browser/device runtime and target environment. |
| Live ad-provider integration | NOT RUN / external | No real provider adapter, account, SDK or provider webhook credentials are included. |
| Production deployment / demo video / reference-game study | EXTERNAL EVIDENCE REQUIRED | Cannot be proven from this source archive alone. |

## Material blockers before a 100% sign-off

1. **Runtime verification is incomplete.** The full frontend build, Django test suite, isolated PostgreSQL integration, Docker Compose startup, API integration, and browser/mobile acceptance remain unverified.
2. **The requirement traceability is not signed off.** `PHASE1_TRACEABILITY_127_EXACT.csv` contains 127 `NOT YET VERIFIED` statuses; the review CSV contains 127 `PARTIAL` statuses. Mapping is not the same as passing.
3. **Rewarded ads are intentionally fail-closed by default.** The project documents an unavailable/mock provider when no real vendor is configured. This is consistent with the PDF's provider-abstraction allowance for local environments, but live ad delivery and vendor-side callback verification still need staging evidence.
4. **Startup is not self-contained in this ZIP.** `START-AWA.ps1` requires `database-safety-backup\awa_verified_recovery_2026-11-06.dump`, which is intentionally excluded from the distributable for data/security safety. The main `docker-compose.yml` also declares an external PostgreSQL volume named `veloop_apple_worm_postgres_v2`; a fresh machine without that volume cannot simply start it. Do not create an empty replacement or reset an existing database without an explicit migration/restore plan.
5. **External company deliverables remain.** Reference-game study evidence, originality/IP review, deployed frontend/backend URLs, demo video, and authorized reviewer sign-off are not included.

## What this package preserves

- Backend, frontend source, migrations, tests, scripts, Docker/Caddy configuration, documentation, and the original requirements PDF.
- `.env.example` and `.env.production.example` templates only.
- No real `.env` files, database dumps, private TLS keys, `node_modules`, generated frontend `dist`, Python caches, or Git metadata.

## Safe next steps on the target Windows machine

1. Extract the archive to a new folder; do not overwrite the existing project or database.
2. Review `.env.example` and create a local `.env` with fresh secrets. Never share it.
3. Confirm the intended PostgreSQL volume exists and is the correct project database before running Compose.
4. Run the isolated test stack from PowerShell:
   `powershell -ExecutionPolicy Bypass -File .\scripts\VERIFY-PHASE1.ps1`
   Inspect the script/compose file first; it uses a dedicated test volume and cleans only that isolated test stack.
5. Run the documented Phase 2–8 verification scripts and the full Django suite against an isolated disposable test database.
6. Complete desktop/mobile browser acceptance, configure and test a real ad provider in staging, gather deployment/demo evidence, then update each of the 127 rows with evidence and obtain reviewer approval.

**Do not run `docker compose down -v` against the working project. Do not delete or overwrite the user's existing PostgreSQL volume or database backup.**
