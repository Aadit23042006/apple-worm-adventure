# Apple Worm Adventure — retest and release status

**Date:** 9 November 2026  
**Input:** `AWA_FINAL_CANDIDATE_NOT_CERTIFIED_2026-11-09.zip`  
**Company specification:** `requirements/Apple-G_VELoop_Full_Stack.pdf`  
**Decision:** **NOT CERTIFIED as 100% tested or 100% company-compliant.**

## Corrections applied during this retest

1. Added the missing root `.env.example` required by `START-AWA.ps1`. It includes the VELoop game-name settings, actual frontend API variable (`VITE_API_BASE_URL`), documented `VITE_API_URL`, Django/PostgreSQL settings, and the three exact template-secret placeholders that the startup script replaces with random values. No real secrets are included.
2. Changed the browser `<title>` and description to use Vite's `%VITE_GAME_NAME%` build-time substitution rather than a hardcoded game name.
3. Aligned the default game name in backend settings, frontend Docker build argument, and default Compose interpolation with `APPLE WORM ADVENTURE`.
4. Added the Phase 2 rewarded-ad static audit to `RUN-ALL-VERIFICATION.ps1`; previously that full verification script omitted the standalone Phase 2 audit.
5. Updated startup documentation to identify the included `.env.example`.

These are source/configuration corrections. They have not yet been exercised through Windows PowerShell or a live container startup.

## Checks executed in this retest

| Check | Result |
|---|---:|
| Phase 2 rewarded-ad static audit | 8/8 PASS |
| Phase 1 static audit | 11/11 PASS |
| Phase 4 static audit | 15/15 PASS |
| Phase 5–6 static audit | 14/14 PASS |
| Phase 7–8 static audit | 27/27 PASS |
| **Selected static assertions** | **75/75 PASS** |
| Python backend `compileall` | PASS |
| Five Compose YAML files parsed | PASS |
| Frontend package/lock root versions | PASS |
| `.env.example` required settings and secret placeholders | PASS |
| Browser title/meta build-time name substitution | PASS |
| Canonical game-name defaults | PASS |
| ZIP extraction/readability | PASS |

Static assertions do not establish functional runtime acceptance.

## Runtime checks and blockers

| Test | Result | Reason / evidence |
|---|---|---|
| `npm ci` | BLOCKED | Attempt timed out in this environment; no complete dependency installation. |
| Frontend production build | BLOCKED/FAIL | `npm run build` cannot find `vite/client` because dependencies are unavailable. |
| Django system check | NOT RUN | Django is not installed in this environment. |
| Django migrations/full tests | NOT RUN | Django and PostgreSQL service unavailable. |
| PostgreSQL integration | NOT RUN | No PostgreSQL service/client available. |
| Docker Compose config/startup | NOT RUN | Docker CLI/daemon unavailable; YAML parsing is not equivalent. |
| API/auth/gameplay E2E | NOT RUN | Requires running backend and database. |
| Runtime anti-cheat/reward regression | NOT RUN | Requires running backend and isolated PostgreSQL. |
| Windows PowerShell startup/verification scripts | NOT RUN | PowerShell is not installed in this environment. |
| Desktop/mobile browser acceptance | NOT RUN | No running frontend build/application. |
| Real ad-provider staging | NOT RUN | Requires an actual provider account, adapter, credentials and signed callback setup. |
| Production deployment/demo/reviewer evidence | NOT RUN | No deployment URLs or demo artifact supplied. |

## VELoop compliance status

The supplied PDF's Section 111 expressly permits an ad-provider abstraction/mock integration in a local environment when an actual provider cannot be used, but prohibits fabricating ad completion. The project uses a fail-closed unconfigured provider; that is a valid local architecture choice, not proof of a live provider integration.

The PDF's mandatory feature set (Section 118) includes gameplay, 50+ levels, authentication, database persistence, sessions, progress, history, leaderboard, achievements, anti-cheat, wallet/ledgers, ad opportunity tracking, verified/idempotent rewards, revive, double score, double coins, extra moves, hint, booster, caps, cooldowns, daily limits, economy configuration, and deployment/documentation/demo deliverables. Sections 113–117 and 125–127 also require documentation, actual deployment, and demo/reviewer evidence.

The supplied 127-row traceability artifacts still mark the clauses as `PARTIAL` / `NOT YET VERIFIED`. The retest has not produced clause-by-clause runtime evidence to change those statuses. In particular, external URLs, demo video, reference-game study evidence and company sign-off cannot be inferred or invented.

## Release decision

- Selected static assertions: **75/75 PASS**.
- Additional configuration/source checks: **10 PASS**.
- Runtime phases certified in this environment: **0/8**.
- Company requirements fully evidenced: **not established; 127 rows remain PARTIAL / NOT YET VERIFIED**.
- Fresh-install configuration: **corrected in source; Windows/Docker runtime still pending**.
- Production-ready / error-free guarantee: **not established**.

This archive is a **repaired retest candidate**, not a 100% certified release. Run `RUN-ALL-VERIFICATION.ps1` on the target Windows machine with Docker Desktop and network access, then complete browser, provider, deployment, demo and clause-level acceptance before representing it as fully compliant.
