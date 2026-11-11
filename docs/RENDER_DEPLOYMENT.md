# Render Deployment — Apple Worm Adventure

This project can be deployed to Render using the included `render.yaml`.

## Important

The blueprint is deployment configuration, not proof of a completed live deployment. A live deployment is only verified after Render services start successfully and the smoke tests below pass.

## 1. Create the Render Blueprint

1. Push the complete project to GitHub.
2. In Render, create a new Blueprint from the repository.
3. Select the repository root containing `render.yaml`.
4. Create the services and PostgreSQL database.

## 2. Configure required secrets/values

In the `awa-backend` service set:

- `DJANGO_ALLOWED_HOSTS` — the actual backend hostname and any required frontend host.
- `FRONTEND_BASE_URL` — the actual HTTPS frontend URL.
- `CORS_ALLOWED_ORIGINS` — exact HTTPS frontend origin, without a trailing slash.
- `CSRF_TRUSTED_ORIGINS` — exact HTTPS frontend origin, without a trailing slash.
- `AD_PROVIDER` — a real supported provider.
- `AD_PROVIDER_ADAPTER` — the dotted Python adapter path.
- `AD_PROVIDER_WEBHOOK_SECRET` — provider signing secret.
- SMTP settings for email verification.
- `DEFAULT_FROM_EMAIL`.

Keep `ALLOW_PROVIDER_FREE_DEMO_ADS=false` in production.

In the `awa-frontend` service set:

- `VITE_GAME_NAME=APPLE WORM ADVENTURE`.
- `VITE_API_BASE_URL` to the deployed backend API origin, ending with `/api` only if the frontend API client expects that form.

## 3. Database

The blueprint creates a Render PostgreSQL database. Django migrations are not destructive; nevertheless, review migrations before applying them to any database containing existing user data.

The application must never be started with a command that deletes the database, tables, PostgreSQL volumes, users, progress or reward history.

## 4. Production smoke tests

After deployment verify:

```text
GET /api/health/
GET /api/auth/me/       (must require authentication)
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/refresh/
GET /api/levels/        (authenticated)
```

Then verify:

- Existing accounts can log in.
- Refresh works after an expired access token.
- Logout does not unexpectedly revoke unrelated refresh sessions.
- Level progress remains intact.
- Wallet and reward ledger remain intact.
- Production rewards remain blocked unless a real provider is configured and verified.
- HTTPS is active.
- Browser secure-cookie flags are present.
- Frontend can reach the backend API.

## 5. Rollback

If a deployment introduces a regression:

1. Stop promoting the new release.
2. Re-deploy the last known-good application image/commit.
3. Do not delete or recreate the PostgreSQL database.
4. Do not run destructive migrations.
5. Review the migration and application logs.
6. Restore the database only from a verified backup if an actual data-corruption event occurred.

## 6. Certification rule

Mark the project production-ready only after the deployment smoke tests and the missing runtime checks are actually executed. Static inspection alone is insufficient.
