AWA Test 3 regression patch
===========================

Files:
- frontend/src/App.tsx
- backend/core/tests.py

What changed:
1. Frontend completion now fails closed if the server omits required core objectives.
2. Both mandatory objectives (collect all apples and reach the portal) must be present and required.
3. Reaching the portal is not shown as completed until all apples are collected.
4. The completion dialog appears only after the local game state is marked completed following backend confirmation.
5. A backend completion rejection no longer leaves the frontend permanently frozen in a locally completed state.
6. Added backend regression tests proving that completion is rejected when apples remain or when the worm is not at the portal.

No backend production logic was weakened or bypassed. The backend already contains authoritative apples/portal checks.

Apply:
- Back up the current two files.
- Copy these two files into the matching paths in AWA_RELEASE_CANDIDATE.
- Rebuild and run:
    docker compose up -d --build backend frontend
    docker compose run --rm backend python manage.py test core.tests
    cd frontend
    npm run build

Important:
- Do not replace your .env.
- Do not delete Docker volumes or database data.
- This patch addresses the discovered frontend fail-open condition and adds backend regression coverage. Browser Test 3 must still be repeated before marking it PASS.
