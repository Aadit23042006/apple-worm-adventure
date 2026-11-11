"""
Regression tests for the cross-device logout cause of
"Checkpoint save failed: Invalid token."

The backend keeps ONE shared DRF Token per user. Logging out used to delete
it AND revoke every refresh session, so a logout in another tab/device/test
run left every other live session with a dead token and nothing to refresh
with. Logout now revokes only the caller's own refresh session when the
caller identifies it; other devices recover through /auth/refresh/.

Legacy behaviour (no refresh_token supplied) is unchanged: revoke all.
"""

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import GameSession, RefreshSession

User = get_user_model()
PASSWORD = "safe-password-123"


def _login(username):
    r = APIClient().post(
        "/api/auth/login/",
        {"username": username, "password": PASSWORD},
        format="json",
    )
    assert r.status_code == 200, r.content
    return r.data["token"], r.data["refresh_token"]


def _client(token):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return c


class MultiDeviceLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="md_a", email="md_a@example.com", password=PASSWORD
        )
        self.token_a, self.refresh_a = _login("md_a")  # device A
        self.token_b, self.refresh_b = _login("md_a")  # device B (same user)

        started = _client(self.token_a).post(
            "/api/games/start/", {"level": 1}, format="json"
        )
        self.assertEqual(started.status_code, 200, started.content)
        self.session_id = started.data["sessionId"]
        self.initial = deepcopy(started.data["state"])

    def _move(self):
        s = deepcopy(self.initial)
        s["worm"] = [{"r": 1, "c": 2}, *s["worm"]]
        s["worm"].pop()
        s["moves"] = 1
        return s

    def _checkpoint(self, client):
        return client.post(
            f"/api/games/{self.session_id}/checkpoint/",
            {"state": self._move()},
            format="json",
        )

    def test_logout_with_own_refresh_revokes_only_that_session(self):
        out = _client(self.token_a).post(
            "/api/auth/logout/", {"refresh_token": self.refresh_a}, format="json"
        )
        self.assertEqual(out.status_code, 200)

        dead = APIClient().post(
            "/api/auth/refresh/", {"refresh_token": self.refresh_a}, format="json"
        )
        alive = APIClient().post(
            "/api/auth/refresh/", {"refresh_token": self.refresh_b}, format="json"
        )
        self.assertEqual(dead.status_code, 401)
        self.assertEqual(alive.status_code, 200)

    def test_other_device_recovers_and_checkpoint_succeeds_after_logout(self):
        _client(self.token_a).post(
            "/api/auth/logout/", {"refresh_token": self.refresh_a}, format="json"
        )

        # The shared access token is gone: the stale token is rejected ...
        stale = self._checkpoint(_client(self.token_b))
        self.assertEqual(stale.status_code, 401)
        self.assertEqual(stale.data["detail"], "Invalid token.")

        # ... but device B can refresh and then save the checkpoint.
        refreshed = APIClient().post(
            "/api/auth/refresh/", {"refresh_token": self.refresh_b}, format="json"
        )
        self.assertEqual(refreshed.status_code, 200)
        ok = self._checkpoint(_client(refreshed.data["token"]))
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(
            GameSession.objects.get(id=self.session_id).moves, 1
        )

    def test_logged_out_device_access_token_is_dead(self):
        _client(self.token_a).post(
            "/api/auth/logout/", {"refresh_token": self.refresh_a}, format="json"
        )
        self.assertEqual(
            _client(self.token_a).get("/api/auth/me/").status_code, 401
        )

    def test_logout_without_refresh_token_still_revokes_everything(self):
        _client(self.token_a).post("/api/auth/logout/")
        for raw in (self.refresh_a, self.refresh_b):
            r = APIClient().post(
                "/api/auth/refresh/", {"refresh_token": raw}, format="json"
            )
            self.assertEqual(r.status_code, 401)

    def test_logout_with_unknown_refresh_token_revokes_everything(self):
        _client(self.token_a).post(
            "/api/auth/logout/", {"refresh_token": "nope" * 12}, format="json"
        )
        self.assertFalse(
            RefreshSession.objects.filter(
                user=self.user, revoked_at__isnull=True
            ).exists()
        )

    def test_logout_cannot_revoke_another_users_refresh_session(self):
        User.objects.create_user(
            username="md_b", email="md_b@example.com", password=PASSWORD
        )
        _, refresh_other = _login("md_b")

        _client(self.token_a).post(
            "/api/auth/logout/", {"refresh_token": refresh_other}, format="json"
        )

        still = APIClient().post(
            "/api/auth/refresh/", {"refresh_token": refresh_other}, format="json"
        )
        self.assertEqual(still.status_code, 200)
