from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from .models import GameSession

User = get_user_model()


class MoveScoreConsistencyAntiCheatTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="anticheat_step5",
            email="anticheat_step5@example.com",
            password="safe-password-123",
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

        self.initial_state = deepcopy(
            response.data["state"]
        )

    def make_valid_non_apple_move(self):
        state = deepcopy(self.initial_state)

        new_head = {"r": 1, "c": 2}

        state["worm"] = [
            new_head,
            *state["worm"],
        ]
        state["worm"].pop()
        state["moves"] = 1

        return state

    def assert_checkpoint_unchanged(self, original):
        self.session.refresh_from_db()

        self.assertEqual(
            self.session.checkpoint_state,
            original,
        )
        self.assertEqual(self.session.moves, 0)
        self.assertEqual(self.session.score, 0)
        self.assertEqual(self.session.status, "ACTIVE")

    def test_legitimate_one_cell_move_is_accepted(self):
        state = self.make_valid_non_apple_move()

        response = self.client.post(
            f"/api/games/{self.session.id}/checkpoint/",
            {"state": state},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
            f"Legitimate move rejected: {response.data}",
        )

        self.session.refresh_from_db()

        self.assertEqual(self.session.moves, 1)
        self.assertEqual(self.session.score, 0)
        self.assertEqual(
            self.session.checkpoint_state["worm"],
            state["worm"],
        )

    def test_checkpoint_rejects_forged_move_count(self):
        original = deepcopy(self.session.checkpoint_state)

        state = self.make_valid_non_apple_move()
        state["moves"] = 25

        response = self.client.post(
            f"/api/games/{self.session.id}/checkpoint/",
            {"state": state},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
            f"Forged move count accepted: {response.data}",
        )

        self.assert_checkpoint_unchanged(original)

    def test_checkpoint_rejects_forged_score(self):
        original = deepcopy(self.session.checkpoint_state)

        state = self.make_valid_non_apple_move()
        state["score"] = 999999

        response = self.client.post(
            f"/api/games/{self.session.id}/checkpoint/",
            {"state": state},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
            f"Forged score accepted: {response.data}",
        )

        self.assert_checkpoint_unchanged(original)
