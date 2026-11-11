from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from .models import (
    GameSession,
    PlayerProfile,
    PlayerProgress,
    RewardTransaction,
)

User = get_user_model()


class CompletionAntiCheatTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="anticheat_step4",
            email="anticheat_step4@example.com",
            password="safe-password-123",
        )

        self.profile, _ = PlayerProfile.objects.get_or_create(
            user=self.user
        )

        token = Token.objects.create(user=self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}"
        )

        response = self.client.post(
            "/api/games/start/",
            {"level": 1},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.session = GameSession.objects.get(
            id=response.data["sessionId"],
            user=self.user,
        )

        self.initial_checkpoint = deepcopy(
            self.session.checkpoint_state
        )

        self.progress, _ = PlayerProgress.objects.get_or_create(
            user=self.user,
            level=self.session.level,
        )

    def assert_no_completion_mutation(self):
        self.session.refresh_from_db()
        self.profile.refresh_from_db()
        self.progress.refresh_from_db()

        self.assertEqual(self.session.status, "ACTIVE")
        self.assertEqual(self.session.moves, 0)
        self.assertEqual(self.session.score, 0)
        self.assertEqual(
            self.session.checkpoint_state,
            self.initial_checkpoint,
        )

        self.assertFalse(self.progress.completed)
        self.assertEqual(self.profile.total_score, 0)

        self.assertEqual(
            RewardTransaction.objects.filter(
                user=self.user,
                placement="LEVEL_COMPLETION",
            ).count(),
            0,
        )

    def test_completion_rejects_fabricated_finished_state(self):
        forged = deepcopy(self.initial_checkpoint)

        forged["apples"] = []
        forged["worm"] = [deepcopy(forged["portal"])]
        forged["moves"] = 999
        forged["score"] = 999999
        forged["completed"] = True
        forged["failed"] = False

        response = self.client.post(
            f"/api/games/{self.session.id}/complete/",
            {"state": forged},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
            f"Fabricated completion was not rejected: {response.data}",
        )

        self.assert_no_completion_mutation()

    def test_completion_rejects_incomplete_server_checkpoint(self):
        response = self.client.post(
            f"/api/games/{self.session.id}/complete/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
            f"Incomplete game was not rejected: {response.data}",
        )

        self.assert_no_completion_mutation()
