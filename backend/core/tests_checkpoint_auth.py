"""
Regression tests for the recurring "Checkpoint save failed: Invalid token." defect.

Deterministic: no sleeps, no wall-clock dependence. Every test uses the real
login / refresh / logout / checkpoint endpoints against the test database.

Mapping to the acceptance list (backend-verifiable items only; items 6-8, 9 and 15
are frontend behaviour and are covered by frontend/src/authClient.test.ts):

  1  test_01_authenticated_checkpoint_save_succeeds
  2  test_02_invalid_token_is_rejected
  3  test_03_revoked_access_token_is_rejected_and_state_unchanged
  4  test_04_valid_refresh_token_issues_working_access_token
  5  test_05_checkpoint_succeeds_after_token_refresh
  10 test_10_checkpoint_persists_in_database
  11 test_11_user_cannot_modify_another_users_checkpoint
  12 test_12_inactive_session_rejects_checkpoint
  13 test_13_stale_session_cannot_overwrite_newer_session
  14 test_14_completion_is_not_accepted_without_server_checkpoint_at_portal
  -  test_logout_*, test_refresh_failure_*, test_account_switching_*
"""

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import GameSession, RefreshSession

User = get_user_model()

PASSWORD = "safe-password-123"


def _login(username):
    client = APIClient()
    response = client.post(
        "/api/auth/login/",
        {"username": username, "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200, response.content
    return response.data["token"], response.data["refresh_token"]


def _client_with(token):
    client = APIClient()
    if token:
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


class CheckpointAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cp_auth_a",
            email="cp_auth_a@example.com",
            password=PASSWORD,
        )
        self.token, self.refresh = _login("cp_auth_a")
        self.client = _client_with(self.token)

        started = self.client.post(
            "/api/games/start/", {"level": 1}, format="json"
        )
        self.assertEqual(started.status_code, 200, started.content)
        self.session_id = started.data["sessionId"]
        self.initial_state = deepcopy(started.data["state"])

    # ------------------------------------------------------------------ helpers

    def _first_move_state(self):
        state = deepcopy(self.initial_state)
        state["worm"] = [{"r": 1, "c": 2}, *state["worm"]]
        state["worm"].pop()
        state["moves"] = 1
        return state

    def _post_checkpoint(self, client, state=None, session_id=None):
        return client.post(
            f"/api/games/{session_id or self.session_id}/checkpoint/",
            {"state": state if state is not None else self._first_move_state()},
            format="json",
        )

    def _session(self):
        return GameSession.objects.get(id=self.session_id)

    # -------------------------------------------------------------------- tests

    def test_01_authenticated_checkpoint_save_succeeds(self):
        response = self._post_checkpoint(self.client)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data["ok"])
        self.assertEqual(response.data["moves"], 1)

    def test_02_invalid_token_is_rejected(self):
        before = deepcopy(self._session().checkpoint_state)

        response = self._post_checkpoint(_client_with("not-a-real-token"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Invalid token.")
        self.assertEqual(self._session().checkpoint_state, before)

    def test_03_revoked_access_token_is_rejected_and_state_unchanged(self):
        # The backend uses non-expiring DRF tokens: "expired" means revoked/deleted.
        before = deepcopy(self._session().checkpoint_state)
        Token.objects.filter(user=self.user).delete()

        response = self._post_checkpoint(self.client)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self._session().checkpoint_state, before)

    def test_04_valid_refresh_token_issues_working_access_token(self):
        Token.objects.filter(user=self.user).delete()

        refreshed = APIClient().post(
            "/api/auth/refresh/",
            {"refresh_token": self.refresh},
            format="json",
        )

        self.assertEqual(refreshed.status_code, 200, refreshed.content)
        self.assertNotEqual(refreshed.data["token"], self.token)

        me = _client_with(refreshed.data["token"]).get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)

    def test_05_checkpoint_succeeds_after_token_refresh(self):
        Token.objects.filter(user=self.user).delete()

        # Old token fails ...
        self.assertEqual(self._post_checkpoint(self.client).status_code, 401)

        # ... refresh yields a new one ...
        refreshed = APIClient().post(
            "/api/auth/refresh/",
            {"refresh_token": self.refresh},
            format="json",
        )
        self.assertEqual(refreshed.status_code, 200)

        # ... and the very next protected request with it succeeds.
        response = self._post_checkpoint(_client_with(refreshed.data["token"]))
        self.assertEqual(response.status_code, 200, response.content)

    def test_10_checkpoint_persists_in_database(self):
        self._post_checkpoint(self.client)

        stored = GameSession.objects.get(id=self.session_id)
        self.assertEqual(stored.moves, 1)
        self.assertEqual(stored.checkpoint_state["moves"], 1)
        self.assertEqual(stored.checkpoint_state["worm"][0], {"r": 1, "c": 2})

    def test_11_user_cannot_modify_another_users_checkpoint(self):
        User.objects.create_user(
            username="cp_auth_b",
            email="cp_auth_b@example.com",
            password=PASSWORD,
        )
        token_b, _ = _login("cp_auth_b")
        before = deepcopy(self._session().checkpoint_state)

        response = self._post_checkpoint(_client_with(token_b))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self._session().checkpoint_state, before)

    def test_12_inactive_session_rejects_checkpoint(self):
        for status in ("COMPLETED", "FAILED"):
            GameSession.objects.filter(id=self.session_id).update(status=status)
            before = deepcopy(self._session().checkpoint_state)

            response = self._post_checkpoint(self.client)

            self.assertEqual(response.status_code, 404, status)
            self.assertEqual(self._session().checkpoint_state, before, status)

    def test_13_stale_session_cannot_overwrite_newer_session(self):
        newer = self.client.post(
            "/api/games/start/", {"level": 1}, format="json"
        )
        self.assertEqual(newer.status_code, 200, newer.content)
        newer_id = newer.data["sessionId"]

        newer_before = deepcopy(
            GameSession.objects.get(id=newer_id).checkpoint_state
        )

        # A late write addressed to the OLD session id ...
        self._post_checkpoint(self.client)

        # ... must never touch the newer session's stored state.
        self.assertEqual(
            GameSession.objects.get(id=newer_id).checkpoint_state,
            newer_before,
        )

    def test_14_completion_is_not_accepted_without_server_checkpoint_at_portal(self):
        response = self.client.post(
            f"/api/games/{self.session_id}/complete/",
            {"state": {"completed": True}, "score": 999999, "stars": 3},
            format="json",
        )

        self.assertNotEqual(response.status_code, 200, response.content)
        self.assertNotEqual(self._session().status, "COMPLETED")

    # ------------------------------------------------- logout / switching / refresh

    def test_logout_invalidates_access_and_refresh_tokens(self):
        out = self.client.post("/api/auth/logout/")
        self.assertEqual(out.status_code, 200)

        self.assertEqual(
            self._post_checkpoint(_client_with(self.token)).status_code, 401
        )
        again = APIClient().post(
            "/api/auth/refresh/", {"refresh_token": self.refresh}, format="json"
        )
        self.assertEqual(again.status_code, 401)

    def test_refresh_failure_with_revoked_refresh_token_is_401(self):
        RefreshSession.objects.filter(user=self.user).update(
            revoked_at="2000-01-01T00:00:00Z"
        )

        response = APIClient().post(
            "/api/auth/refresh/", {"refresh_token": self.refresh}, format="json"
        )

        self.assertEqual(response.status_code, 401)

    def test_refresh_with_garbage_refresh_token_is_401_not_500(self):
        response = APIClient().post(
            "/api/auth/refresh/", {"refresh_token": "x" * 10}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_account_switching_old_token_never_acts_as_new_user(self):
        User.objects.create_user(
            username="cp_auth_b",
            email="cp_auth_b@example.com",
            password=PASSWORD,
        )
        token_b, _ = _login("cp_auth_b")

        me_b = _client_with(token_b).get("/api/auth/me/")
        me_a = _client_with(self.token).get("/api/auth/me/")

        self.assertEqual(me_b.data["user"]["username"], "cp_auth_b")
        self.assertEqual(me_a.data["user"]["username"], "cp_auth_a")
        self.assertNotEqual(token_b, self.token)
