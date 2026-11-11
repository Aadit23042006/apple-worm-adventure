$ErrorActionPreference = 'Stop'

$root = Get-Location
$viewsPath = Join-Path $root 'backend/core/views.py'
$testsPath = Join-Path $root 'backend/core/tests.py'

if (-not (Test-Path $viewsPath)) { throw "backend/core/views.py not found. Run this from the Phase5 project root." }
if (-not (Test-Path $testsPath)) { throw "backend/core/tests.py not found. Run this from the Phase5 project root." }

$views = Get-Content -Raw -Encoding UTF8 $viewsPath
$old = @'
        incoming = (
            request.data.get(
                "state"
            )
            or {}
        )

        ok, state = (
            validate_next_move(
                session.checkpoint_state,
                incoming,
                session.level.number,
                require_completion=True,
            )
        )

        if not ok:
            return Response(
                {
                    "detail": state
                },
                status=400,
            )
'@
$new = @'
        incoming = (
            request.data.get(
                "state"
            )
            or {}
        )

        # ----------------------------------------------------
        # COMPLETE THE ALREADY-VALIDATED CHECKPOINT
        #
        # Completion is a terminal action on the current
        # server checkpoint. It is NOT another movement.
        # Calling validate_next_move() here would incorrectly
        # require incoming.moves == checkpoint.moves + 1,
        # even though the player has already reached the portal
        # in the last checkpoint (for example move 8).
        #
        # The checkpoint endpoint has already validated the
        # complete movement history. Here we verify that the
        # client is replaying the exact current checkpoint,
        # that it is at the portal with no apples, and then the
        # server alone applies the +100 completion bonus and
        # completion flag.
        # ----------------------------------------------------

        incoming_ok, incoming_checked = validate_state_shape(
            incoming,
            session.level.number,
        )

        if not incoming_ok:
            return Response(
                {
                    "detail": incoming_checked
                },
                status=400,
            )

        stored_ok, stored_checked = validate_state_shape(
            session.checkpoint_state or {},
            session.level.number,
        )

        if not stored_ok:
            return Response(
                {
                    "detail": "Stored checkpoint is invalid.",
                },
                status=400,
            )

        incoming_state = _normalise_state(
            incoming_checked
        )
        stored_state = _normalise_state(
            stored_checked
        )

        # The completion request must refer to the exact server
        # checkpoint. This prevents clients from changing moves,
        # worm position, apples, obstacles, timestamps, or reward
        # counters at completion time.
        if incoming_state != stored_state:
            return Response(
                {
                    "detail": (
                        "Invalid completion state: "
                        "state does not match the "
                        "server checkpoint."
                    )
                },
                status=400,
            )

        if stored_state["failed"]:
            return Response(
                {
                    "detail": "Cannot complete a failed session.",
                },
                status=400,
            )

        if stored_state["apples"]:
            return Response(
                {
                    "detail": (
                        "All apples must be collected "
                        "before completion."
                    )
                },
                status=400,
            )

        if not same_position(
            stored_state["worm"][0],
            stored_state["portal"],
        ):
            return Response(
                {
                    "detail": "Worm is not at the portal.",
                },
                status=400,
            )

        if stored_state["completed"]:
            return Response(
                {
                    "detail": "Session is already marked completed.",
                },
                status=400,
            )

        # The gameplay score is the score stored by the last
        # validated checkpoint. The completion bonus is always
        # calculated server-side and is never trusted from the
        # client payload.
        final_score = (
            int(stored_state["score"])
            + 100
        )

        state = dict(stored_state)
        state["score"] = final_score
        state["completed"] = True
'@

if (-not $views.Contains($old)) {
    throw "The expected old completion block was not found. No files were changed. This protects against patching a different source version."
}
$views = $views.Replace($old, $new)

$oldScore = @'
        if "score" in request.data:
            try:
                supplied_score = int(
                    request.data[
                        "score"
                    ]
                )
            except (
                TypeError,
                ValueError,
            ):
                return Response(
                    {
                        "detail": (
                            "Invalid score value."
                        )
                    },
                    status=400,
                )

            if (
                supplied_score
                != state["score"]
            ):
                return Response(
                    {
                        "detail": (
                            "Top-level score does "
                            "not match state."
                        )
                    },
                    status=400,
                )
'@
$newScore = @'
        if "score" in request.data:
            try:
                supplied_score = int(
                    request.data[
                        "score"
                    ]
                )
            except (
                TypeError,
                ValueError,
            ):
                return Response(
                    {
                        "detail": (
                            "Invalid score value."
                        )
                    },
                    status=400,
                )

            if (
                supplied_score
                != stored_state["score"]
            ):
                return Response(
                    {
                        "detail": (
                            "Top-level score does not "
                            "match the last validated "
                            "checkpoint score."
                        )
                    },
                    status=400,
                )
'@

if (-not $views.Contains($oldScore)) {
    throw "The expected completion score-consistency block was not found. No files were changed."
}
$views = $views.Replace($oldScore, $newScore)

$views | Set-Content -Encoding UTF8 $viewsPath

$testMarker = 'class PhaseFiveCompletionRegressionTests(TestCase):'
$tests = Get-Content -Raw -Encoding UTF8 $testsPath
if (-not $tests.Contains($testMarker)) {
@'


class PhaseFiveCompletionRegressionTests(TestCase):
    """Completion must finalize the already-validated portal checkpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='completion-player',
            email='completion@example.com',
            password='safe-password-123',
        )
        from rest_framework.authtoken.models import Token
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.token.key}'
        )

        from .views import level_static_config
        self.level = Level.objects.create(
            number=1,
            config=level_static_config(1),
        )
        PlayerProgress.objects.create(
            user=self.user,
            level=self.level,
            unlocked=True,
        )

        from .models import GameSession
        self.session = GameSession.objects.create(
            user=self.user,
            level=self.level,
            initial_state={
                'worm': [{'r': 1, 'c': 1}],
                'apples': [
                    {'r': 1, 'c': 4},
                    {'r': 2, 'c': 5},
                ],
                'obstacles': level_static_config(1)['obstacles'],
                'portal': {'r': 5, 'c': 5},
                'moves': 0,
                'score': 0,
                'failed': False,
                'completed': False,
                'started': 123456,
                'revives': 0,
                'hints': 0,
                'boosters': 0,
                'extraMoves': 0,
            },
            checkpoint_state={
                'worm': [
                    {'r': 5, 'c': 5},
                    {'r': 4, 'c': 5},
                    {'r': 3, 'c': 5},
                ],
                'apples': [],
                'obstacles': level_static_config(1)['obstacles'],
                'portal': {'r': 5, 'c': 5},
                'moves': 8,
                'score': 70,
                'failed': False,
                'completed': False,
                'started': 123456,
                'revives': 0,
                'hints': 0,
                'boosters': 0,
                'extraMoves': 0,
            },
            moves=8,
            score=70,
            status='ACTIVE',
        )

    def test_completion_finalizes_existing_portal_checkpoint(self):
        state = self.session.checkpoint_state
        response = self.client.post(
            f'/api/games/{self.session.id}/complete/',
            {'moves': 8, 'score': 70, 'state': state},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['completed'])
        self.assertEqual(response.data['score'], 170)
        self.assertFalse(response.data['idempotent'])

        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'COMPLETED')
        self.assertEqual(self.session.moves, 8)
        self.assertEqual(self.session.score, 170)
        self.assertTrue(self.session.checkpoint_state['completed'])
        self.assertEqual(self.session.checkpoint_state['score'], 170)

    def test_completion_rejects_tampered_checkpoint_state(self):
        state = dict(self.session.checkpoint_state)
        state['worm'] = [
            {'r': 5, 'c': 4},
            {'r': 5, 'c': 5},
            {'r': 4, 'c': 5},
        ]
        response = self.client.post(
            f'/api/games/{self.session.id}/complete/',
            {'moves': 8, 'score': 70, 'state': state},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not match', response.data['detail'])
'@ | Add-Content -Encoding UTF8 $testsPath
}

Write-Host "Permanent completion fix applied." -ForegroundColor Green
Write-Host "Checkpoint validation was not changed." -ForegroundColor Green
Write-Host "Completion now finalizes the existing portal checkpoint and calculates +100 server-side." -ForegroundColor Green
