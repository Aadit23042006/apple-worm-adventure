# AWA — current-session retest report

**Date:** 9 November 2026  
**Input:** `AWA_REPAIRED_CANDIDATE_NOT_CERTIFIED_2026-11-09.zip`  
**Specification:** `requirements/Apple-G_VELoop_Full_Stack.pdf`  
**Decision:** **NOT CERTIFIED as 100% company-compliant.**

## Tests executed in this session

| Test | Result | Evidence / limitation |
|---|---:|---|
| Phase 2 rewarded-ad static audit | 8/8 PASS | `PHASE2_STATIC_AUDIT.py` |
| Phase 1 static audit | 11/11 PASS | `scripts/phase1_source_audit.py` |
| Phase 4 static audit | 15/15 PASS | `scripts/verify_phase4_features.py` |
| Phase 5–6 static audit | 14/14 PASS | `scripts/verify_phase5_6.py` |
| Phase 7–8 static audit | 27/27 PASS | `scripts/verify_phase7_8.py` |
| **Selected static assertions** | **75/75 PASS** | These inspect source structure, not live runtime behavior. |
| Python backend source compilation | PASS | `python -m compileall -q backend` |
| Compose YAML syntax | 6/6 PASS | PyYAML with Compose `!reset`/`!override` tags registered; this is syntax parsing, not `docker compose config`. |
| Frontend package/lock JSON and root dependency consistency | PASS | `package.json` and `package-lock.json` parsed and matched. |
| `.env.example` required keys | PASS | Required local startup keys and placeholders present. |
| Release startup/verification files | PASS | Startup, stop, verification and Dockerfiles present. |
| 127-row traceability file | PASS (inventory only) | 127 rows exist; all 127 remain `PARTIAL`, not certified. |

## Runtime tests attempted in this session

| Test | Result | Reason |
|---|---|---|
| `npm ci` | BLOCKED | npm registry requests failed with `EAI_AGAIN` (DNS/network unavailable); dependency install could not finish. |
| Frontend production build | NOT RUN | Cannot build without installed Vite/TypeScript dependencies. |
| Django check and backend tests | NOT RUN | Django, Django REST Framework, django-cors-headers and psycopg are not installed; package installation cannot be assumed. |
| PostgreSQL integration | NOT RUN | No PostgreSQL service/client available. |
| Docker Compose validation/startup | NOT RUN | Docker CLI/daemon unavailable. |
| Windows PowerShell startup | NOT RUN | PowerShell is unavailable in this Linux test environment. |
| Browser/gameplay end-to-end tests | NOT RUN | No built frontend or running API/database stack. |
| Real ad-provider staging | NOT RUN | Requires a configured provider account/adapter and signed callback credentials. |

## Earlier target-Windows evidence included in this archive

`PHASE1_LOCAL_VERIFICATION_RESULTS.txt` records a Windows run dated 8 November 2026 with PASS for clean `npm ci`, frontend production build, isolated Compose configuration, and a Django/PostgreSQL test suite. The 127-row traceability review also refers to a reported 84-test backend run. These are retained as prior evidence, but this session could not independently reproduce them in the current environment. Aggregate test success does not automatically prove every individual PDF clause.

## Company requirement gaps still open

`PHASE1_TRACEABILITY_127_EVIDENCE_REVIEW.csv` currently has **127/127 rows marked PARTIAL** in both implementation and audit status. The review identifies three classes of missing evidence:

1. Clause-specific source references and functional/security test evidence for the exact PDF wording.
2. Reward-provider decision/configuration and evidence for signed callback verification, session binding, replay protection, idempotency, caps/cooldowns and ledger grants. The PDF permits a provider abstraction/mock when a real provider cannot be used locally, but a mock must not falsely claim an ad completed.
3. External evidence that cannot be generated from source code alone: reference-game review/originality review, deployed frontend/backend URLs, demo video, and final submission/reviewer evidence.

The PDF also evaluates gameplay, game engineering, full-stack behavior, VELoop economy, responsive UI, audio/feedback, documentation and code quality (Section 125), and requests deployment/demo/submission artifacts (Sections 113–117 and 126–127).

## Release decision

- Current-session selected static assertions: **75/75 PASS**.
- Current-session supplemental source/config checks: **all applicable checks PASS**.
- Current-session live runtime phases certified: **0/8** (runtime infrastructure was unavailable).
- Prior Windows smoke/build/backend evidence: present in archive, not independently reproduced here.
- Company traceability: **127/127 PARTIAL**; not 100% evidenced.
- This ZIP is a **retested candidate, NOT a 100% tested/certified final release**.

Do not represent this archive as fully compliant until the Windows Docker startup, frontend build, isolated PostgreSQL suite, gameplay/browser acceptance, provider behavior, deployments and demo/submission evidence are complete and recorded.
