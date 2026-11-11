from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from .models import ApiKey, EmailVerification, PasswordResetToken, RefreshSession
from .views import digest, issue_refresh

User = get_user_model()


@override_settings(
    DEBUG=True,
    EMAIL_VERIFICATION_REQUIRED=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AuthenticationLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="auth-audit-player",
            email="auth-audit@example.com",
            password="Initial-Strong-Password-2026!",
        )

    def test_login_me_refresh_and_logout_revoke_session(self):
        login = self.client.post(
            "/api/auth/login/",
            {"username": self.user.username, "password": "Initial-Strong-Password-2026!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.data.get("token"))
        refresh_token = login.data["refresh_token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

        refreshed = self.client.post(
            "/api/auth/refresh/", {"refresh_token": refresh_token}, format="json"
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.data["refresh_token"], refresh_token)

        logout = self.client.post("/api/auth/logout/")
        self.assertEqual(logout.status_code, 200)
        self.assertFalse(
            RefreshSession.objects.filter(
                user=self.user, revoked_at__isnull=True
            ).exists()
        )
        denied = self.client.post(
            "/api/auth/refresh/", {"refresh_token": refresh_token}, format="json"
        )
        self.assertEqual(denied.status_code, 401)

    def test_refresh_rejects_expired_session(self):
        raw = issue_refresh(self.user)
        RefreshSession.objects.filter(user=self.user).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        response = self.client.post(
            "/api/auth/refresh/", {"refresh_token": raw}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_password_reset_request_is_generic_for_unknown_email(self):
        response = self.client.post(
            "/api/auth/password-reset/request/",
            {"email": "nobody@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["accepted"])
        self.assertNotIn("reset_token", response.data)

    def test_password_reset_valid_token_changes_password_and_revokes_sessions(self):
        login_token = Token.objects.create(user=self.user)
        raw_refresh = issue_refresh(self.user)
        request = self.client.post(
            "/api/auth/password-reset/request/",
            {"email": self.user.email},
            format="json",
        )
        self.assertEqual(request.status_code, 200)
        raw_reset = request.data["reset_token"]

        confirm = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": raw_reset, "password": "New-Strong-Password-2026!"},
            format="json",
        )
        self.assertEqual(confirm.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-Strong-Password-2026!"))
        self.assertFalse(Token.objects.filter(pk=login_token.pk).exists())
        self.assertFalse(
            RefreshSession.objects.filter(
                user=self.user, revoked_at__isnull=True
            ).exists()
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/refresh/", {"refresh_token": raw_refresh}, format="json"
            ).status_code,
            401,
        )

        reused = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": raw_reset, "password": "Another-Strong-Password-2026!"},
            format="json",
        )
        self.assertEqual(reused.status_code, 400)

    def test_password_reset_rejects_invalid_token(self):
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": "not-a-real-token", "password": "New-Strong-Password-2026!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_password_reset_rejects_expired_token(self):
        raw = "expired-reset-token"
        PasswordResetToken.objects.create(
            user=self.user,
            token_hash=digest(raw),
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": raw, "password": "New-Strong-Password-2026!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("expired", response.data["detail"].lower())


@override_settings(
    DEBUG=True,
    EMAIL_VERIFICATION_REQUIRED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class EmailVerificationLifecycleTests(TestCase):
    def test_registration_requires_verification_and_valid_token_activates_account(self):
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            {
                "username": "verify-player",
                "email": "verify-player@example.com",
                "password": "Registration-Strong-2026!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["verification_required"])
        self.assertTrue(response.data["email_sent"])
        self.assertEqual(len(mail.outbox), 1)

        user = User.objects.get(username="verify-player")
        self.assertFalse(user.is_active)
        blocked_login = client.post(
            "/api/auth/login/",
            {"username": "verify-player", "password": "Registration-Strong-2026!"},
            format="json",
        )
        self.assertEqual(blocked_login.status_code, 403)
        verify = client.post(
            "/api/auth/verify-email/",
            {"token": response.data["verification_token"]},
            format="json",
        )
        self.assertEqual(verify.status_code, 200)
        self.assertTrue(verify.data["verified"])
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        allowed_login = client.post(
            "/api/auth/login/",
            {"username": "verify-player", "password": "Registration-Strong-2026!"},
            format="json",
        )
        self.assertEqual(allowed_login.status_code, 200)

    def test_expired_email_verification_token_is_rejected(self):
        user = User.objects.create_user(
            username="expired-verify",
            email="expired-verify@example.com",
            password="Registration-Strong-2026!",
            is_active=False,
        )
        raw = "expired-email-verification"
        EmailVerification.objects.create(
            user=user,
            token_hash=digest(raw),
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        response = APIClient().post(
            "/api/auth/verify-email/", {"token": raw}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertFalse(user.is_active)



class ApiKeySecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="api-key-player",
            email="api-key-player@example.com",
            password="Strong-API-Key-Password-2026!",
        )
        self.other_user = User.objects.create_user(
            username="api-key-other",
            email="api-key-other@example.com",
            password="Strong-Other-Password-2026!",
        )

    def create_api_key(self, user=None, raw=None, name="Test key"):
        user = user or self.user
        raw = raw or "aw_test_key_" + user.username
        key = ApiKey.objects.create(
            user=user,
            name=name,
            key_prefix=raw[:12],
            key_hash=digest(raw),
        )
        return key, raw

    def authenticate_with_token(self, user=None):
        token = Token.objects.create(user=user or self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}"
        )
        return token

    def test_valid_api_key_authenticates(self):
        key, raw = self.create_api_key()
        response = self.client.get(
            "/api/levels/",
            HTTP_X_API_KEY=raw,
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_api_key_is_rejected(self):
        response = self.client.get(
            "/api/levels/",
            HTTP_X_API_KEY="aw_invalid_key",
        )
        self.assertEqual(response.status_code, 401)

    def test_revoked_api_key_is_rejected(self):
        key, raw = self.create_api_key()
        key.revoked_at = timezone.now()
        key.save(update_fields=["revoked_at"])

        response = self.client.get(
            "/api/levels/",
            HTTP_X_API_KEY=raw,
        )
        self.assertEqual(response.status_code, 401)

    def test_inactive_user_api_key_is_rejected(self):
        key, raw = self.create_api_key()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.get(
            "/api/levels/",
            HTTP_X_API_KEY=raw,
        )
        self.assertEqual(response.status_code, 401)

    def test_successful_authentication_updates_last_used(self):
        key, raw = self.create_api_key()
        self.assertIsNone(key.last_used_at)

        response = self.client.get(
            "/api/levels/",
            HTTP_X_API_KEY=raw,
        )

        self.assertEqual(response.status_code, 200)
        key.refresh_from_db()
        self.assertIsNotNone(key.last_used_at)

    def test_api_key_creation_returns_raw_key_once_and_stores_hash(self):
        self.authenticate_with_token()

        response = self.client.post(
            "/api/api-keys/",
            {"name": "Automated test key"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        raw = response.data["key"]
        self.assertTrue(raw.startswith("aw_"))

        key = ApiKey.objects.get(user=self.user)
        self.assertEqual(key.key_hash, digest(raw))
        self.assertNotEqual(key.key_hash, raw)
        self.assertEqual(response.data["name"], "Automated test key")

    def test_api_key_listing_only_returns_owners_active_keys(self):
        own_key, _ = self.create_api_key(name="Own key")
        self.create_api_key(
            user=self.other_user,
            name="Other user's key",
            raw="aw_other_user_secret",
        )

        revoked_key, _ = self.create_api_key(
            name="Revoked key",
            raw="aw_revoked_key_secret",
        )
        revoked_key.revoked_at = timezone.now()
        revoked_key.save(update_fields=["revoked_at"])

        self.authenticate_with_token()
        response = self.client.get("/api/api-keys/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["keys"]), 1)
        self.assertEqual(response.data["keys"][0]["id"], own_key.id)

    def test_api_key_revocation_blocks_future_authentication(self):
        key, raw = self.create_api_key()
        self.authenticate_with_token()

        response = self.client.post(
            f"/api/api-keys/{key.id}/revoke/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["revoked"])

        key.refresh_from_db()
        self.assertIsNotNone(key.revoked_at)

        self.client.credentials()
        denied = self.client.get(
            "/api/levels/",
            HTTP_X_API_KEY=raw,
        )
        self.assertEqual(denied.status_code, 401)

    def test_user_cannot_revoke_another_users_api_key(self):
        other_key, _ = self.create_api_key(
            user=self.other_user,
            raw="aw_foreign_user_key",
        )
        self.authenticate_with_token()

        response = self.client.post(
            f"/api/api-keys/{other_key.id}/revoke/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["revoked"])

        other_key.refresh_from_db()
        self.assertIsNone(other_key.revoked_at)

    def test_maximum_of_ten_active_api_keys_is_enforced(self):
        for number in range(10):
            self.create_api_key(
                name=f"Key {number}",
                raw=f"aw_limit_test_key_{number}",
            )

        self.authenticate_with_token()
        response = self.client.post(
            "/api/api-keys/",
            {"name": "Eleventh key"},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            ApiKey.objects.filter(
                user=self.user,
                revoked_at__isnull=True,
            ).count(),
            10,
        )

    def test_normal_drf_token_authentication_still_works(self):
        self.authenticate_with_token()

        response = self.client.get("/api/levels/")

        self.assertEqual(response.status_code, 200)


@override_settings(
    DEBUG=False,
    EMAIL_VERIFICATION_REQUIRED=False,
)
class RegistrationToLevelSelectionIntegrationTests(TestCase):
    """Regression coverage for the exact browser E2E registration flow."""

    def test_registered_access_token_authenticates_me_levels_and_active_game(self):
        client = APIClient(REMOTE_ADDR="198.51.100.101")
        registration = client.post(
            "/api/auth/register/",
            {
                "username": "register-level-flow",
                "email": "register-level-flow@example.com",
                "password": "Registration-Flow-Password-2026!",
            },
            format="json",
        )

        self.assertEqual(registration.status_code, 201)
        self.assertTrue(registration.data["token"])
        self.assertTrue(registration.data["refresh_token"])
        self.assertTrue(registration.data["user"]["email_verified"])

        client.credentials(
            HTTP_AUTHORIZATION=f"Token {registration.data['token']}"
        )

        me = client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["user"]["username"], "register-level-flow")

        levels = client.get("/api/levels/")
        self.assertEqual(levels.status_code, 200)
        self.assertGreater(len(levels.data["levels"]), 0)
        self.assertTrue(
            any(
                item["number"] == 1 and item["unlocked"] is True
                for item in levels.data["levels"]
            )
        )

        active_game = client.get("/api/games/active/")
        self.assertEqual(active_game.status_code, 200)
        self.assertFalse(active_game.data["active"])

    def test_registered_refresh_token_recovers_authenticated_access(self):
        client = APIClient(REMOTE_ADDR="198.51.100.102")
        registration = client.post(
            "/api/auth/register/",
            {
                "username": "register-refresh-flow",
                "email": "register-refresh-flow@example.com",
                "password": "Registration-Flow-Password-2026!",
            },
            format="json",
        )
        self.assertEqual(registration.status_code, 201)

        refreshed = client.post(
            "/api/auth/refresh/",
            {"refresh_token": registration.data["refresh_token"]},
            format="json",
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertTrue(refreshed.data["token"])
        self.assertEqual(
            refreshed.data["refresh_token"], registration.data["refresh_token"]
        )

        client.credentials(
            HTTP_AUTHORIZATION=f"Token {refreshed.data['token']}"
        )
        self.assertEqual(client.get("/api/levels/").status_code, 200)
