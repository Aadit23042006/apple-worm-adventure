# Apple Worm Adventure — Retest Audit (2026-11-09)

## Decision
NOT APPROVED as a 100% tested, production-ready, fresh-machine one-click release.

This ZIP is an audited source candidate. It is not a certified final build. No source-code changes were made during this retest.

## Retests executed from this archive
- Phase 1 static source audit: 11/11 PASS
- Phase 4 static feature audit: 15/15 PASS
- Phase 5–6 static audit: 14/14 PASS
- Phase 7–8 static audit: 27/27 PASS
- Backend Python syntax compilation (`compileall`): PASS
- ZIP extraction/readability: PASS

Total: 67/67 static assertions passed, plus Python syntax compilation.

Important: these are static/source checks, not end-to-end runtime acceptance.

## Not verified
- Frontend `npm ci` and production build
- Django system checks, migrations, and full backend test suite
- PostgreSQL integration
- Docker Compose runtime startup
- Auth/API/gameplay end-to-end tests
- Runtime anti-cheat and reward-ledger regression
- Desktop/mobile browser tests
- Live ad-provider SDK/account/callback integration
- Production deployment, demo video, reference-game study evidence, and reviewer sign-off

## Traceability
The supplied audit evidence reports:
- 127/127 requirements mapped
- 127 exact traceability rows still `NOT YET VERIFIED`
- 127 review rows still `PARTIAL`

Mapping is not proof of passing.

## Fresh-machine startup limitation
The project startup script expects `database-safety-backup/awa_verified_recovery_2026-11-06.dump`, which is not packaged. The primary Compose file also expects an existing external PostgreSQL volume named `veloop_apple_worm_postgres_v2`. Therefore this archive cannot honestly be represented as a self-contained fresh-machine one-click package.

Do not create an empty replacement database or delete/reset the existing volume to bypass this. Preserve the user's existing database and backup.

## Safe local verification
The included `scripts/VERIFY-PHASE1.ps1` uses a dedicated Compose project and dedicated `phase1_test_pgdata` volume, and its cleanup targets that isolated test stack. Review it before running. It performs:
1. `npm ci`
2. `npm run build`
3. isolated Compose config validation
4. isolated PostgreSQL + Django checks, migrations, and test suite

Do not run `docker compose down -v` against the working project.
