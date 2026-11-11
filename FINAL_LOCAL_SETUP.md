# Apple Worm Adventure — final local setup (current instructions)

This file previously described a volume-specific manual setup. The supported fresh-install path is now the `START-AWA.ps1` script in the project root.

## Start

1. Install and start Docker Desktop in Linux-container mode.
2. Extract the project ZIP.
3. Open PowerShell in the extracted project directory.
4. Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\START-AWA.ps1
```

The script creates `.env` from `.env.example` if needed, replaces known placeholder secrets with random local values, validates Compose, builds the images, starts the services and checks the frontend/API health endpoints.

Open `http://localhost:5174` when startup reports success.

## Database behavior

- Fresh install uses persistent volume `awa_fresh_install_data_v1`.
- Django migrations create the schema and seed 60 levels, default economy configuration and achievement definitions.
- This distributable contains no database dump; it does not import existing player accounts or progress.
- Previously used volumes are not mounted, deleted or modified by this fresh-install path.
- `STOP-AWA.ps1` stops services without deleting the volume.
- Never use `docker compose down -v` as routine troubleshooting. It deletes persistent database data.

## Automated verification

Run `.\RUN-ALL-VERIFICATION.ps1` in PowerShell to execute static audits, frontend install/build and the full Django suite against an isolated temporary PostgreSQL test stack. This test stack is separate from the application database.

The automated script does not replace visual browser acceptance, external ad-provider staging, production deployment or final reviewer/demo evidence.
