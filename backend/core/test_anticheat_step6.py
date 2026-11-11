from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from .models import GameSession, PlayerProfile

User = get_user_model()


class SessionOwnershipAntiCheatTests(TestCase):
    def test_other_user_cannot_checkpoint_undo_or_complete_session(self):
        owner = User.objects.create_user(
            username="anticheat_owner",
            email="anticheat_owner@example.com",
            password="safe-password-123",
        )
        attacker = User.objects.create_user(
            username="anticheat_attacker",
            email="anticheat_attacker@example.com",
            password="safe-password-123",
        )

        PlayerProfile.objects.get_or_create(user=owner)
        PlayerProfile.objects.get_or_create(user=attacker)

        owner_token = Token.objects.create(user=owner)
        attacker_token = Token.objects.create(user=attacker)

        owner_client = APIClient()
        owner_client.credentials(
            HTTP_AUTHORIZATION=f"Token {owner_token.key}"
        )

        start_response = owner_client.post(
            "/api/games/start/",
            {"level": 1},
            format="json",
        )
        self.assertEqual(start_response.status_code, 200)

        session_id = start_response.data["sessionId"]
        session = GameSession.objects.get(
            id=session_id,
            user=owner,
        )
        original_checkpoint = session.checkpoint_state

        attacker_client = APIClient()
        attacker_client.credentials(
            HTTP_AUTHORIZATION=f"Token {attacker_token.key}"
        )

        endpoints = [
            (
                f"/api/games/{session_id}/checkpoint/",
                {"state": {}},
            ),
            (
                f"/api/games/{session_id}/undo/",
                {},
            ),
            (
                f"/api/games/{session_id}/complete/",
                {},
            ),
        ]

        for endpoint, payload in endpoints:
            with self.subTest(endpoint=endpoint):
                response = attacker_client.post(
                    endpoint,
                    payload,
                    format="json",
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(
                    response.data.get("detail"),
                    "Invalid session.",
                )

        session.refresh_from_db()

        self.assertEqual(session.user_id, owner.id)
        self.assertEqual(session.status, "ACTIVE")
        self.assertEqual(session.moves, 0)
        self.assertEqual(session.score, 0)
        self.assertEqual(
            session.checkpoint_state,
            original_checkpoint,
        )
