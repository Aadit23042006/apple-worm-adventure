from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from .models import GameSession, PlayerProfile


User = get_user_model()


class AppleScoreCheckpointAntiCheatTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="anticheat_step3",
            email="anticheat_step3@example.com",
            password="safe-password-123",
        )

        PlayerProfile.objects.get_or_create(user=self.user)

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

        self.initial_state = deepcopy(response.data["state"])

    def test_checkpoint_rejects_fake_apple_and_score_claims(self):
        original_state = deepcopy(self.session.checkpoint_state)

        # A legitimate move to (1, 2), which is not an apple.
        valid_move = deepcopy(self.initial_state)
        new_head = {"r": 1, "c": 2}

        valid_move["worm"] = [new_head, *valid_move["worm"]]
        valid_move["worm"].pop()
        valid_move["moves"] = 1

        cases = []

        fake_apple = deepcopy(valid_move)
        fake_apple["apples"] = fake_apple["apples"][1:]
        cases.append(("fake apple collection", fake_apple))

        fake_score = deepcopy(valid_move)
        fake_score["score"] = 999
        cases.append(("forged score", fake_score))

        for label, forged_state in cases:
            with self.subTest(attempt=label):
                response = self.client.post(
                    f"/api/games/{self.session.id}/checkpoint/",
                    {"state": forged_state},
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    400,
                    f"{label} was not rejected: {response.data}",
                )

                self.session.refresh_from_db()

                self.assertEqual(
                    self.session.checkpoint_state,
                    original_state,
                    f"{label} changed the stored checkpoint",
                )
                self.assertEqual(self.session.moves, 0)
                self.assertEqual(self.session.score, 0)
                self.assertEqual(self.session.status, "ACTIVE")
