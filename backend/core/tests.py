from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Level, PlayerProfile, PlayerProgress

User = get_user_model()


class PhaseOneApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_endpoint_is_public(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertIn("game_name", response.data)

    def test_register_creates_user_profile_and_token(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "puzzleplayer",
                "email": "player@example.com",
                "password": "safe-password-123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["token"])

        user = User.objects.get(username="puzzleplayer")
        self.assertTrue(user.check_password("safe-password-123"))
        self.assertTrue(
            PlayerProfile.objects.filter(user=user).exists()
        )

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(
            username="taken",
            email="old@example.com",
            password="safe-password-123",
        )

        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "taken",
                "email": "new@example.com",
                "password": "safe-password-123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_login_and_authenticated_profile(self):
        User.objects.create_user(
            username="puzzleplayer",
            email="player@example.com",
            password="safe-password-123",
        )

        login_response = self.client.post(
            "/api/auth/login/",
            {
                "username": "puzzleplayer",
                "password": "safe-password-123",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        token = login_response.data["token"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token}"
        )

        profile_response = self.client.get("/api/auth/me/")

        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(
            profile_response.data["user"]["username"],
            "puzzleplayer",
        )

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)

    def test_logout_revokes_token(self):
        user = User.objects.create_user(
            username="puzzleplayer",
            email="player@example.com",
            password="safe-password-123",
        )

        from rest_framework.authtoken.models import Token

        token = Token.objects.create(user=user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}"
        )

        response = self.client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Token.objects.filter(user=user).exists()
        )
        self.assertEqual(
            self.client.get("/api/auth/me/").status_code,
            401,
        )


class PhaseThreeGameIntegrityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="integrity-player",
            email="integrity@example.com",
            password="safe-password-123",
        )

        from rest_framework.authtoken.models import Token

        self.token = Token.objects.create(user=self.user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )

        # IMPORTANT:
        # Level 1 is already seeded by the project's canonical
        # level seed/migration. Do not create another Level 1.
        self.level = Level.objects.get(number=1)

        PlayerProgress.objects.create(
            user=self.user,
            level=self.level,
            unlocked=True,
        )

    def initial_state(self):
        from .views import level_static_config

        cfg = level_static_config(1)

        return {
            "worm": [
                {
                    "r": 1,
                    "c": 1,
                }
            ],
            "apples": cfg["apples"],
            "obstacles": cfg["obstacles"],
            "portal": cfg["portal"],
            "moves": 0,
            "score": 0,
            "failed": False,
            "completed": False,
            "started": 123456,
            "revives": 0,
            "hints": 0,
            "boosters": 0,
            "extraMoves": 0,
        }

    def test_restart_creates_fresh_zeroed_session(self):
        first = self.client.post(
            "/api/games/start/",
            {"level": 1},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        first_session_id = first.data["sessionId"]

        from .models import GameSession

        first_session = GameSession.objects.get(id=first_session_id)
        progressed = dict(first_session.checkpoint_state)
        progressed["moves"] = 11
        progressed["score"] = 90
        first_session.checkpoint_state = progressed
        first_session.save(update_fields=["checkpoint_state"])

        restarted = self.client.post(
            "/api/games/start/",
            {"level": 1},
            format="json",
        )
        self.assertEqual(restarted.status_code, 200)
        self.assertNotEqual(restarted.data["sessionId"], first_session_id)
        self.assertEqual(restarted.data["state"]["moves"], 0)
        self.assertEqual(restarted.data["state"]["score"], 0)
        self.assertFalse(restarted.data["state"]["completed"])
        self.assertFalse(restarted.data["state"]["failed"])

        first_session.refresh_from_db()
        self.assertEqual(first_session.status, "ABANDONED")

    def test_tampered_checkpoint_movement_is_rejected(self):
        start = self.initial_state()

        response = self.client.post(
            "/api/games/start/",
            {
                "level": 1,
                "state": start,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        session_id = response.data["sessionId"]

        tampered = {
            **start,
            "moves": 1,
            "score": 0,
            "worm": [
                {
                    "r": 3,
                    "c": 3,
                }
            ],
        }

        response = self.client.post(
            f"/api/games/{session_id}/checkpoint/",
            {
                "moves": 1,
                "score": 0,
                "state": tampered,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_undo_restores_server_checkpoint(self):
        start = self.initial_state()

        response = self.client.post(
            "/api/games/start/",
            {
                "level": 1,
                "state": start,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        session_id = response.data["sessionId"]

        moved = {
            **start,
            "worm": [
                {
                    "r": 1,
                    "c": 2,
                }
            ],
            "moves": 1,
        }

        response = self.client.post(
            f"/api/games/{session_id}/checkpoint/",
            {
                "moves": 1,
                "score": 0,
                "state": moved,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            f"/api/games/{session_id}/undo/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"]["moves"], 0)
        self.assertEqual(
            response.data["state"]["worm"],
            [
                {
                    "r": 1,
                    "c": 1,
                }
            ],
        )


class PhaseFiveCompletionRegressionTests(TestCase):
    """
    Completion must finalize the already-validated portal checkpoint.
    """

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="completion-player",
            email="completion@example.com",
            password="safe-password-123",
        )

        from rest_framework.authtoken.models import Token

        self.token = Token.objects.create(user=self.user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )

        from .views import level_static_config

        # IMPORTANT:
        # Level 1 is already seeded by the canonical level data.
        # Retrieve it instead of attempting to insert another Level 1.
        self.level = Level.objects.get(number=1)

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
                "worm": [
                    {
                        "r": 1,
                        "c": 1,
                    }
                ],
                "apples": [
                    {
                        "r": 1,
                        "c": 4,
                    },
                    {
                        "r": 2,
                        "c": 5,
                    },
                ],
                "obstacles": level_static_config(1)["obstacles"],
                "portal": {
                    "r": 5,
                    "c": 5,
                },
                "moves": 0,
                "score": 0,
                "failed": False,
                "completed": False,
                "started": 123456,
                "revives": 0,
                "hints": 0,
                "boosters": 0,
                "extraMoves": 0,
            },
            checkpoint_state={
                "worm": [
                    {
                        "r": 5,
                        "c": 5,
                    },
                    {
                        "r": 4,
                        "c": 5,
                    },
                    {
                        "r": 3,
                        "c": 5,
                    },
                ],
                "apples": [],
                "obstacles": level_static_config(1)["obstacles"],
                "portal": {
                    "r": 5,
                    "c": 5,
                },
                "moves": 8,
                "score": 70,
                "failed": False,
                "completed": False,
                "started": 123456,
                "revives": 0,
                "hints": 0,
                "boosters": 0,
                "extraMoves": 0,
            },
            moves=8,
            score=70,
            status="ACTIVE",
        )

    def test_completion_finalizes_existing_portal_checkpoint(self):
        state = self.session.checkpoint_state

        response = self.client.post(
            f"/api/games/{self.session.id}/complete/",
            {
                "moves": 8,
                "score": 70,
                "state": state,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["completed"])
        self.assertEqual(response.data["score"], 170)
        self.assertFalse(response.data["idempotent"])

        self.session.refresh_from_db()

        self.assertEqual(
            self.session.status,
            "COMPLETED",
        )
        self.assertEqual(
            self.session.moves,
            8,
        )
        self.assertEqual(
            self.session.score,
            170,
        )
        self.assertTrue(
            self.session.checkpoint_state["completed"]
        )
        self.assertEqual(
            self.session.checkpoint_state["score"],
            170,
        )

    def test_completion_rejects_tampered_checkpoint_state(self):
        state = dict(self.session.checkpoint_state)

        state["worm"] = [
            {
                "r": 5,
                "c": 4,
            },
            {
                "r": 5,
                "c": 5,
            },
            {
                "r": 4,
                "c": 5,
            },
        ]

        response = self.client.post(
            f"/api/games/{self.session.id}/complete/",
            {
                "moves": 8,
                "score": 70,
                "state": state,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "does not match",
            response.data["detail"],
        )

    def test_completion_rejects_portal_when_apples_remain(self):
        state = dict(self.session.checkpoint_state)
        state["apples"] = [{"r": 1, "c": 4}]
        self.session.checkpoint_state = state
        self.session.save(update_fields=["checkpoint_state"])

        response = self.client.post(
            f"/api/games/{self.session.id}/complete/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("apples", response.data["detail"].lower())
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "ACTIVE")

    def test_completion_rejects_collected_apples_without_portal(self):
        state = dict(self.session.checkpoint_state)
        state["worm"] = [
            {"r": 4, "c": 5},
            {"r": 4, "c": 4},
            {"r": 4, "c": 3},
        ]
        state["apples"] = []
        self.session.checkpoint_state = state
        self.session.save(update_fields=["checkpoint_state"])

        response = self.client.post(
            f"/api/games/{self.session.id}/complete/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("portal", response.data["detail"].lower())
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "ACTIVE")


class RewardedAdOpportunityCooldownTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="cooldown-player",
            email="cooldown@example.com",
            password="safe-password-123",
        )
        self.client.force_authenticate(user=self.user)

    def test_new_opportunity_starts_cooldown_immediately(self):
        first = self.client.post(
            "/api/economy/ad-opportunity/",
            {"placement": "BOOSTER"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/economy/ad-opportunity/",
            {"placement": "BOOSTER"},
            format="json",
        )
        self.assertEqual(second.status_code, 429)
        self.assertIn("cooldown", str(second.data["detail"]).lower())
        self.assertGreaterEqual(
            int(second.data["cooldownSeconds"]),
            1,
        )

    def test_same_event_id_is_idempotent_before_cooldown(self):
        event_id = "cooldown-idempotency-event"

        first = self.client.post(
            "/api/economy/ad-opportunity/",
            {"placement": "BOOSTER", "eventId": event_id},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.data["idempotent"])

        retry = self.client.post(
            "/api/economy/ad-opportunity/",
            {"placement": "BOOSTER", "eventId": event_id},
            format="json",
        )
        self.assertEqual(retry.status_code, 200)
        self.assertTrue(retry.data["idempotent"])
        self.assertEqual(retry.data["eventId"], event_id)

        conflicting_retry = self.client.post(
            "/api/economy/ad-opportunity/",
            {"placement": "HINT", "eventId": event_id},
            format="json",
        )
        self.assertEqual(conflicting_retry.status_code, 409)

    def test_opportunity_cooldown_expires(self):
        first = self.client.post(
            "/api/economy/ad-opportunity/",
            {"placement": "BOOSTER"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)

        from django.utils import timezone
        from datetime import timedelta
        from .models import AdOpportunity

        AdOpportunity.objects.filter(
            event_id=first.data["eventId"]
        ).update(
            created_at=timezone.now() - timedelta(seconds=31)
        )

        second = self.client.post(
            "/api/economy/ad-opportunity/",
            {"placement": "BOOSTER"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.data["idempotent"])
