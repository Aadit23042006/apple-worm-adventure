# AWA Release Status — 11 November 2026

## Current verdict

**NOT CERTIFIED FOR LIVE PRODUCTION YET.**

The supplied release candidate contains the previously repaired authentication checkpoint fix and the fresh static audits pass, but this package must not be represented as 100% production-certified.

## What is verified from the supplied candidate

- 11/11 Phase 1 source assertions pass.
- 8/8 rewarded-ad lifecycle static assertions pass.
- 15/15 Phase 4 feature assertions pass.
- 14/14 Phase 5–6 assertions pass.
- 27/27 Phase 7–8 assertions pass.
- 14/14 audio preference/source assertions pass.
- 60/60 static level reachability checks pass.
- Python backend source compilation passes.
- The documented authentication regression was reproduced and fixed in the supplied evidence.
- Historical full backend suite: 111/111 passed.
- Historical frontend unit tests: 12/12 passed.
- Historical frontend production build: passed.

## Not certified / not currently re-verified in this environment

- Fresh Django/PostgreSQL test execution: unavailable because the required Python packages are not installed and external package download is unavailable.
- Fresh frontend dependency installation/build: not re-run because `node_modules` is absent and the environment has no package-network access.
- Docker/Compose runtime: not available for fresh execution.
- Live Render deployment, DNS and HTTPS: not performed.
- Real rewarded-ad provider/account/callback: not configured; the provider-free demo remains disabled for production.
- Physical mobile/touch acceptance: not executed.
- Full gameplay E2E coverage of every obstacle type and all required audio events: not established.
- Complete 127-clause final sign-off: not established.

## Safety rule

Do not convert any historical PASS into a newly executed PASS. Historical evidence remains useful evidence, but it is labelled historical.

The production environment must be configured from `.env.production.example`, with real secrets stored only in the deployment provider.

## Render deployment

A `render.yaml` blueprint has been added as deployment configuration. It defines:

- Django backend web service.
- React/Vite frontend web service using the existing frontend Dockerfile.
- Render PostgreSQL database.
- Production HTTPS/security environment variables.
- Explicit production disabling of provider-free demo rewards.

The blueprint still requires operator-supplied values for domain/origin, email, and real ad-provider configuration.
