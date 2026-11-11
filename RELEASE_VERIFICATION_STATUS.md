# Apple Worm Adventure — Release Verification Status

**Package classification: RELEASE CANDIDATE — NOT CERTIFIED 100%**

Prepared from the supplied `AWA_RELEASE_CANDIDATE.zip` on 2026-11-11. This document records what was freshly checked in the available review environment. It does not claim that unavailable runtime, device, provider, or deployment tests passed.

## Fresh checks that passed

- Python backend source compilation: `python -m compileall -q backend` — PASS.
- `scripts/phase1_source_audit.py` — 11/11 checks passed.
- `PHASE2_STATIC_AUDIT.py` — 8/8 checks passed.
- `scripts/verify_phase4_features.py` — 15/15 checks passed.
- `scripts/verify_phase5_6.py` — 14/14 checks passed.
- `scripts/verify_phase7_8.py` — 27/27 checks passed.
- `scripts/verify_audio_preferences.py` — 14/14 checks passed.
- `scripts/verify_level_reachability.py` — 60/60 static reachability layouts passed.
- Six Docker Compose YAML files parsed successfully with a YAML loader that accepts Compose-specific `!reset` and `!override` tags. This is syntax parsing only, not `docker compose config` or container startup.

The six listed static audit scripts total 89/89 checks. The 60 reachability layouts and Python compilation are separate checks.

## Not freshly verified / blocked

- The 127 company requirements are not fully evidenced: the supplied exact traceability CSV marks all 127 implementation verification statuses `NOT YET VERIFIED`; the evidence review marks implementation/audit statuses `PARTIAL`.
- Backend Django/DRF runtime tests and PostgreSQL regression tests were not run because the review environment did not have the required Python packages, PostgreSQL service, or project virtual environment.
- Frontend dependency installation/build/unit tests were not completed. The environment had Node 22.16.0 while the project declares Node >=22.22.2; offline npm installation also lacked a required cached package (`xmlchars`).
- Docker Compose runtime/configuration and service health checks were not run because Docker CLI/Compose were unavailable.
- Full browser E2E, gameplay/device testing, deployment smoke tests, and production-like load/security checks were not run.
- A real rewarded-ad vendor integration was not verified. The repository contains an unconfigured fail-closed provider abstraction and a demo adapter; neither proves a real vendor account, SDK, signed webhook, or live reward completion.
- Existing historical test/build reports were not treated as fresh test results.

## Packaging security

This release ZIP intentionally excludes local `.env` and `.env.production` files, the local SQL database backup, and `.git` metadata. These are not application features. The corresponding `.env.example` and `.env.production.example` templates are retained. Keep the excluded local files private; rotate any credentials that may have been exposed outside a trusted environment.

## Final decision

**Not 100% verified and not approved for production certification.** The ZIP is a cleaned source/evidence package for the next verification stage. Do not represent the blocked checks or the 127 requirements as passed. Complete the blocked runtime, integration, provider, device, and requirement-by-requirement evidence checks in the target environment before production sign-off.
