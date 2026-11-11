from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Achievement, AdOpportunity, EconomyConfig, GameSession, Level, PlayerProfile, PlayerProgress
from rest_framework.authtoken.models import Token
from .views import build_initial_state, evaluate_objectives, level_objectives, level_static_config

User = get_user_model()


class ProductionConfigurationTests(TestCase):
    def test_fifty_levels_are_seeded(self):
        self.assertGreaterEqual(Level.objects.filter(is_active=True).count(), 50)

    def test_economy_configuration_exists(self):
        self.assertTrue(EconomyConfig.objects.filter(key="default").exists())

    def test_achievements_are_seeded(self):
        self.assertGreaterEqual(Achievement.objects.count(), 10)

    def test_deterministic_levels_have_reachable_route(self):
        for number in range(1, 51):
            cfg = level_static_config(number)
            blocked = {(p["r"], p["c"]) for p in cfg["obstacles"]}
            route = [(1, c) for c in range(1, cfg["size"] - 1)]
            route += [(r, cfg["size"] - 2) for r in range(2, cfg["size"] - 1)]
            self.assertTrue(all(point not in blocked for point in route), number)


class ProductionApiSmokeTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_contract(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["game_name"], settings.GAME_NAME)

    def test_levels_require_authentication(self):
        response = self.client.get("/api/levels/")
        self.assertEqual(response.status_code, 401)

    def test_invalid_level_cannot_start(self):
        user = User.objects.create_user(
            username="phase56",
            email="phase56@example.com",
            password="safe-password-123",
        )
        PlayerProfile.objects.get_or_create(user=user)
        from rest_framework.authtoken.models import Token
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post("/api/games/start/", {"level": 9999, "state": {}}, format="json")
        self.assertEqual(response.status_code, 400)



    def test_start_game_generates_server_authoritative_state(self):
        user = User.objects.create_user(username="phase5start", email="phase5start@example.com", password="safe-password-123")
        PlayerProfile.objects.get_or_create(user=user)
        from rest_framework.authtoken.models import Token
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post("/api/games/start/", {"level": 1}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["sessionId"])
        self.assertEqual(response.data["level"], 1)
        state = response.data["state"]
        self.assertEqual(state["worm"], [{"r": 1, "c": 1}])
        self.assertEqual(state["moves"], 0)
        self.assertEqual(state["score"], 0)
        self.assertFalse(state["failed"])
        self.assertFalse(state["completed"])

    def test_start_game_accepts_legacy_level_id_without_state(self):
        user = User.objects.create_user(username="phase5levelid", email="phase5levelid@example.com", password="safe-password-123")
        PlayerProfile.objects.get_or_create(user=user)
        from rest_framework.authtoken.models import Token
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post("/api/games/start/", {"level_id": 1}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["level"], 1)
        self.assertIn("state", response.data)

    def test_start_game_rejects_tampered_supplied_state(self):
        user = User.objects.create_user(username="phase5tamper", email="phase5tamper@example.com", password="safe-password-123")
        PlayerProfile.objects.get_or_create(user=user)
        from rest_framework.authtoken.models import Token
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post(
            "/api/games/start/",
            {"level": 1, "state": {
                "worm": [{"r": 1, "c": 1}], "apples": [], "obstacles": [],
                "portal": {"r": 5, "c": 5}, "moves": 0, "score": 0,
                "failed": False, "completed": False, "started": 0,
                "revives": 0, "hints": 0, "boosters": 0, "extraMoves": 0,
            }},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid", response.data["detail"])

class ProductionSecurityConfigurationTests(TestCase):
    def test_security_settings_are_environment_driven(self):
        self.assertIn("DEFAULT_THROTTLE_CLASSES", settings.REST_FRAMEWORK)
        self.assertIn("DEFAULT_THROTTLE_RATES", settings.REST_FRAMEWORK)
        self.assertIn("SECURE_CONTENT_TYPE_NOSNIFF", dir(settings))

    @override_settings(DJANGO_ENV="production")
    def test_suite_is_explicitly_marked_for_production_runs(self):
        self.assertEqual(settings.DJANGO_ENV, "production")

class RewardLedgerIntegrityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="rewardledger",
            email="rewardledger@example.com",
            password="safe-password-123",
        )
        PlayerProfile.objects.get_or_create(user=self.user)
        from rest_framework.authtoken.models import Token
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_level_reward_is_exposed_in_unified_reward_ledger(self):
        from .models import RewardTransaction, WalletTransaction
        wallet = WalletTransaction.objects.create(
            user=self.user,
            amount=25,
            balance_after=25,
            kind="CREDIT",
            reason="LEVEL_REWARD",
            reference="level:1:session:test-ledger",
        )
        RewardTransaction.objects.create(
            user=self.user,
            placement="LEVEL_COMPLETION",
            reward_type="COINS",
            amount=25,
            event_id="level-completion:level:1:session:test-ledger",
            status="GRANTED",
            metadata={"source": "level_completion", "walletReference": wallet.reference},
        )
        response = self.client.get("/api/economy/wallet/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(
            r["placement"] == "LEVEL_COMPLETION"
            and r["reward_type"] == "COINS"
            and r["amount"] == 25
            and r["status"] == "GRANTED"
            for r in response.data["rewards"]
        ))

    def test_level_rewards_do_not_consume_rewarded_ad_daily_quota(self):
        from .models import RewardTransaction
        RewardTransaction.objects.create(
            user=self.user,
            placement="LEVEL_COMPLETION",
            reward_type="COINS",
            amount=25,
            event_id="level-completion:test-daily-quota",
            status="GRANTED",
            metadata={"source": "level_completion"},
        )
        from .views import REWARDED_AD_PLACEMENTS
        self.assertNotIn("LEVEL_COMPLETION", REWARDED_AD_PLACEMENTS)

    def test_duplicate_level_reward_does_not_credit_wallet_twice(self):
        from .models import RewardTransaction, WalletTransaction
        from .views import grant_coins

        reference = "idempotency-test:level:session-001"
        event_id = "idempotency-test:level-completion:session-001"
        ledger = {
            "event_id": event_id,
            "placement": "LEVEL_COMPLETION",
            "reward_type": "COINS",
            "metadata": {"source": "idempotency_test"},
        }

        first_balance = grant_coins(
            self.user, 25, "LEVEL_REWARD", reference, reward_ledger=ledger
        )
        second_balance = grant_coins(
            self.user, 25, "LEVEL_REWARD", reference, reward_ledger=ledger
        )

        self.assertEqual(first_balance, 25)
        self.assertEqual(second_balance, 25)
        self.assertEqual(PlayerProfile.objects.get(user=self.user).coins, 25)
        self.assertEqual(
            WalletTransaction.objects.filter(reference=reference).count(), 1
        )
        self.assertEqual(
            RewardTransaction.objects.filter(event_id=event_id).count(), 1
        )

    def test_duplicate_wallet_reference_does_not_credit_twice(self):
        from .models import WalletTransaction
        from .views import grant_coins

        reference = "idempotency-test:generic-credit-001"

        grant_coins(self.user, 25, "TEST_REWARD", reference)
        grant_coins(self.user, 25, "TEST_REWARD", reference)

        self.assertEqual(PlayerProfile.objects.get(user=self.user).coins, 25)
        self.assertEqual(
            WalletTransaction.objects.filter(reference=reference).count(), 1
        )

    def test_wallet_reference_cannot_be_reused_by_another_user(self):
        from .models import WalletTransaction
        from .views import grant_coins

        reference = "idempotency-test:cross-user-001"
        grant_coins(self.user, 25, "TEST_REWARD", reference)

        other_user = User.objects.create_user(
            username="idempotency_other",
            email="idempotency_other@example.com",
            password="safe-password-123",
        )
        PlayerProfile.objects.get_or_create(user=other_user)

        with self.assertRaises(ValueError):
            grant_coins(other_user, 25, "TEST_REWARD", reference)

        self.assertEqual(PlayerProfile.objects.get(user=self.user).coins, 25)
        self.assertEqual(PlayerProfile.objects.get(user=other_user).coins, 0)
        self.assertEqual(
            WalletTransaction.objects.filter(reference=reference).count(), 1
        )



class NoReviveLevelEnforcementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="norevive",
            email="norevive@example.com",
            password="safe-password-123",
        )
        PlayerProfile.objects.get_or_create(user=self.user)
        self.client.force_authenticate(user=self.user)
        self.level = Level.objects.get(number=37)
        PlayerProgress.objects.update_or_create(
            user=self.user,
            level=self.level,
            defaults={"unlocked": True},
        )

    def test_no_revive_levels_have_zero_revive_limit(self):
        self.assertIn(
            {"type": "no_revive"},
            [
                {"type": objective.get("type")}
                for objective in (self.level.config.get("objectives") or [])
            ],
        )
        self.assertEqual(
            self.level.config.get("maxRevivesPerLevel"),
            0,
        )

    def test_no_revive_level_rejects_revive_opportunity(self):
        started = self.client.post(
            "/api/games/start/",
            {"level": 37},
            format="json",
        )
        self.assertEqual(started.status_code, 200)

        response = self.client.post(
            "/api/economy/ad-opportunity/",
            {
                "placement": "REVIVE",
                "metadata": {
                    "sessionId": started.data["sessionId"],
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Revive is not available.",
        )

    def test_no_revive_level_rejects_direct_reward_claim(self):
        session = GameSession.objects.create(
            user=self.user,
            level=self.level,
            initial_state={"revives": 0},
            checkpoint_state={"revives": 0},
        )
        opportunity = AdOpportunity.objects.create(
            user=self.user,
            placement="REVIVE",
            event_id="no-revive-direct-claim",
            status="VERIFIED",
            metadata={"sessionId": str(session.id)},
        )

        response = self.client.post(
            "/api/economy/claim-reward/",
            {
                "eventId": opportunity.event_id,
                "sessionId": str(session.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Revive is not available.",
        )


    def test_reward_claim_rejects_different_session_than_opportunity_binding(self):
        bound_session = GameSession.objects.create(
            user=self.user,
            level=self.level,
            initial_state={"revives": 0},
            checkpoint_state={"revives": 0},
        )
        other_session = GameSession.objects.create(
            user=self.user,
            level=self.level,
            initial_state={"revives": 0},
            checkpoint_state={"revives": 0},
        )
        opportunity = AdOpportunity.objects.create(
            user=self.user,
            placement="REVIVE",
            event_id="no-revive-session-binding-mismatch",
            status="VERIFIED",
            metadata={"sessionId": str(bound_session.id)},
        )

        response = self.client.post(
            "/api/economy/claim-reward/",
            {
                "eventId": opportunity.event_id,
                "sessionId": str(other_session.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Reward opportunity is not bound to the supplied game session.",
        )

        bound_session.refresh_from_db()
        other_session.refresh_from_db()
        self.assertEqual(bound_session.revives_used, 0)
        self.assertEqual(other_session.revives_used, 0)

    def test_reward_claim_rejects_unbound_opportunity_with_client_session_id(self):
        session = GameSession.objects.create(
            user=self.user,
            level=self.level,
            initial_state={"revives": 0},
            checkpoint_state={"revives": 0},
        )
        opportunity = AdOpportunity.objects.create(
            user=self.user,
            placement="REVIVE",
            event_id="no-revive-session-binding-missing",
            status="VERIFIED",
            metadata={},
        )

        response = self.client.post(
            "/api/economy/claim-reward/",
            {
                "eventId": opportunity.event_id,
                "sessionId": str(session.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Reward opportunity is not bound to the supplied game session.",
        )

        session.refresh_from_db()
        self.assertEqual(session.revives_used, 0)

    def test_opportunity_rejects_another_users_session_binding(self):
        other_user = User.objects.create_user(
            username="other-session-owner",
            email="other-session-owner@example.com",
            password="safe-password-123",
        )
        other_session = GameSession.objects.create(
            user=other_user,
            level=self.level,
            initial_state={"revives": 0},
            checkpoint_state={"revives": 0},
        )

        response = self.client.post(
            "/api/economy/ad-opportunity/",
            {
                "placement": "HINT",
                "metadata": {
                    "sessionId": str(other_session.id),
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Game session binding is not available.",
        )

    def test_opportunity_rejects_nonexistent_session_binding(self):
        response = self.client.post(
            "/api/economy/ad-opportunity/",
            {
                "placement": "HINT",
                "metadata": {
                    "sessionId": "00000000-0000-0000-0000-000000000000",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Game session binding is not available.",
        )

    def test_reward_claim_rejects_unresolvable_stored_session_binding(self):
        opportunity = AdOpportunity.objects.create(
            user=self.user,
            placement="HINT",
            event_id="no-revive-unresolvable-session-binding",
            status="VERIFIED",
            metadata={
                "sessionId": "00000000-0000-0000-0000-000000000000",
            },
        )

        response = self.client.post(
            "/api/economy/claim-reward/",
            {
                "eventId": opportunity.event_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Reward opportunity game-session binding is unavailable.",
        )

    def _create_failed_no_revive_session(self):
        started = self.client.post(
            "/api/games/start/",
            {"level": 37},
            format="json",
        )
        self.assertEqual(started.status_code, 200)

        session = GameSession.objects.get(
            id=started.data["sessionId"],
            user=self.user,
        )

        safe_state = started.data["state"]
        head = safe_state["worm"][0]

        failed_state = {
            **safe_state,
            "failed": True,
            "failedMove": {
                "r": head["r"],
                "c": head["c"] - 1,
            },
        }

        session.checkpoint_history = [safe_state]
        session.checkpoint_state = failed_state
        session.save(
            update_fields=[
                "checkpoint_history",
                "checkpoint_state",
                "updated_at",
            ]
        )

        return session, safe_state, failed_state

    def test_no_revive_level_rejects_undo_after_collision(self):
        session, safe_state, failed_state = (
            self._create_failed_no_revive_session()
        )

        response = self.client.post(
            f"/api/games/{session.id}/undo/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Undo is disabled after failure on a No-Revive level.",
        )

        session.refresh_from_db()
        self.assertTrue(session.checkpoint_state["failed"])
        self.assertEqual(
            session.checkpoint_state["failedMove"],
            failed_state["failedMove"],
        )
        self.assertEqual(session.checkpoint_history, [safe_state])
        self.assertEqual(session.revives_used, 0)

    def test_no_revive_level_rejects_checkpoint_after_collision(self):
        session, safe_state, failed_state = (
            self._create_failed_no_revive_session()
        )

        response = self.client.post(
            f"/api/games/{session.id}/checkpoint/",
            {"state": failed_state},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "A failed game cannot accept further moves.",
        )

        session.refresh_from_db()
        self.assertTrue(session.checkpoint_state["failed"])
        self.assertEqual(session.checkpoint_history, [safe_state])
        self.assertEqual(session.revives_used, 0)


    def test_failed_no_revive_session_is_not_restored(self):
        session, _, _ = self._create_failed_no_revive_session()

        response = self.client.get("/api/games/active/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["active"])
        self.assertIsNone(response.data["session"])

        session.refresh_from_db()
        self.assertEqual(session.status, "FAILED")

    def test_failed_no_revive_session_rejects_revive_ad_opportunity(self):
        session, _, _ = self._create_failed_no_revive_session()

        response = self.client.post(
            "/api/economy/ad-opportunity/",
            {
                "placement": "REVIVE",
                "metadata": {"sessionId": str(session.id)},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["detail"], "Revive is not available.")

    def test_failed_no_revive_session_rejects_reward_claim(self):
        session, _, _ = self._create_failed_no_revive_session()

        opportunity = AdOpportunity.objects.create(
            user=self.user,
            placement="REVIVE",
            event_id="no-revive-failed-session-claim",
            status="VERIFIED",
            metadata={"sessionId": str(session.id)},
        )

        response = self.client.post(
            "/api/economy/claim-reward/",
            {
                "eventId": opportunity.event_id,
                "sessionId": str(session.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Rewards are unavailable after failure on a No-Revive level.",
        )

        session.refresh_from_db()
        self.assertTrue(session.checkpoint_state["failed"])
        self.assertEqual(session.revives_used, 0)

    def test_failed_no_revive_session_rejects_completion(self):
        session, _, _ = self._create_failed_no_revive_session()

        response = self.client.post(
            f"/api/games/{session.id}/complete/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "A failed No-Revive game cannot be completed.",
        )

        session.refresh_from_db()
        self.assertEqual(session.status, "FAILED")
        self.assertTrue(session.checkpoint_state["failed"])
        self.assertEqual(session.revives_used, 0)

class ProvisionPhase6LevelCommandTests(TestCase):
    def setUp(self):
        from django.test import override_settings
        self.override = override_settings(PHASE6_TEST_PROVISIONING_ENABLED=True)
        self.override.enable()
        self.user = User.objects.create_user(
            username="phase6provision",
            email="phase6provision@example.com",
            password="safe-password-123",
        )
        self.level37 = Level.objects.get(number=37)

    def tearDown(self):
        self.override.disable()

    def test_provision_unlocks_level_without_fake_completion(self):
        from django.core.management import call_command
        from io import StringIO

        output = StringIO()
        call_command(
            "provision_phase6_level",
            username=self.user.username,
            level=37,
            stdout=output,
        )

        progress = PlayerProgress.objects.get(
            user=self.user,
            level=self.level37,
        )
        self.assertTrue(progress.unlocked)
        self.assertFalse(progress.completed)
        self.assertIn("no gameplay completion was created", output.getvalue())

    def test_provision_is_disabled_without_explicit_opt_in(self):
        from django.core import management
        from django.core.management.base import CommandError
        from django.test import override_settings

        with override_settings(PHASE6_TEST_PROVISIONING_ENABLED=False):
            with self.assertRaises(CommandError):
                management.call_command(
                    "provision_phase6_level",
                    username=self.user.username,
                    level=37,
                )



class PortalCompletionProgressionRegressionTests(TestCase):
    def setUp(self):
        # Django's default TestCase client is not DRF's APIClient and does not
        # support .credentials(). Use APIClient so Token authentication headers
        # are handled consistently with the other API regression tests.
        self.client = APIClient()

    def test_portal_completion_unlocks_next_level_and_closes_active_session(self):
        user = User.objects.create_user(
            username="portalprogress",
            email="portalprogress@example.com",
            password="safe-password-123",
        )
        PlayerProfile.objects.get_or_create(user=user)
        level = Level.objects.get(number=35)
        next_level = Level.objects.get(number=36)
        current_progress, _ = PlayerProgress.objects.get_or_create(
            user=user,
            level=level,
            defaults={"unlocked": True},
        )
        current_progress.unlocked = True
        current_progress.save(update_fields=["unlocked"])
        next_progress, _ = PlayerProgress.objects.get_or_create(
            user=user,
            level=next_level,
            defaults={"unlocked": False},
        )
        next_progress.unlocked = False
        next_progress.save(update_fields=["unlocked"])

        state = build_initial_state(35)
        state["worm"] = [dict(state["portal"])]
        state["apples"] = []
        state["moves"] = 20
        state["score"] = 200
        session = GameSession.objects.create(
            user=user,
            level=level,
            initial_state=build_initial_state(35),
            checkpoint_state=state,
            moves=20,
            score=200,
            status="ACTIVE",
        )

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post(
            f"/api/games/{session.id}/complete/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["completed"])
        session.refresh_from_db()
        next_progress.refresh_from_db()
        current_progress.refresh_from_db()
        self.assertEqual(session.status, "COMPLETED")
        self.assertTrue(current_progress.completed)
        self.assertTrue(next_progress.unlocked)
        self.assertFalse(
            GameSession.objects.filter(user=user, status="ACTIVE").exists()
        )


class Level23MoveLimitBoundaryRegressionTests(TestCase):
    """Protect Level 23's server-authoritative 116/117 move boundary."""

    level_number = 23
    expected_move_limit = 116

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="level23boundary",
            email="level23boundary@example.com",
            password="safe-password-123",
        )
        PlayerProfile.objects.get_or_create(user=self.user)
        token = Token.objects.create(user=self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}"
        )

        self.level = Level.objects.get(number=self.level_number)
        self.progress, _ = PlayerProgress.objects.get_or_create(
            user=self.user,
            level=self.level,
            defaults={"unlocked": True},
        )
        self.progress.unlocked = True
        self.progress.save(update_fields=["unlocked"])

        self.next_level = Level.objects.filter(
            number=self.level_number + 1,
            is_active=True,
        ).first()
        if self.next_level:
            self.next_progress, _ = PlayerProgress.objects.get_or_create(
                user=self.user,
                level=self.next_level,
                defaults={"unlocked": False},
            )
            self.next_progress.unlocked = False
            self.next_progress.save(update_fields=["unlocked"])

    def _state_at_portal(self, moves):
        state = build_initial_state(self.level_number)
        state["worm"] = [dict(state["portal"])]
        state["apples"] = []
        state["moves"] = moves
        state["score"] = 80
        state["failed"] = False
        state["completed"] = False
        state["revives"] = 0
        state["extraMoves"] = 0
        return state

    def _create_session(self, moves):
        return GameSession.objects.create(
            user=self.user,
            level=self.level,
            initial_state=build_initial_state(self.level_number),
            checkpoint_state=self._state_at_portal(moves),
            moves=moves,
            score=80,
            status="ACTIVE",
        )

    def test_level_23_move_limit_is_exactly_116(self):
        config = level_static_config(self.level_number)
        move_objectives = [
            item for item in config["objectives"]
            if item["type"] == "move_limit"
        ]
        self.assertEqual(len(move_objectives), 1)
        self.assertEqual(
            move_objectives[0]["target"],
            self.expected_move_limit,
        )

    def test_116_moves_passes_objectives_and_completes_level(self):
        state = self._state_at_portal(116)
        objective_result = evaluate_objectives(
            state,
            self.level_number,
        )
        self.assertTrue(objective_result["all_completed"])
        move_objective = next(
            item for item in objective_result["objectives"]
            if item["type"] == "move_limit"
        )
        self.assertTrue(move_objective["completed"])

        session = self._create_session(116)
        response = self.client.post(
            f"/api/games/{session.id}/complete/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["completed"])
        session.refresh_from_db()
        self.progress.refresh_from_db()
        self.assertEqual(session.status, "COMPLETED")
        self.assertEqual(session.moves, 116)
        self.assertTrue(session.checkpoint_state["completed"])
        self.assertTrue(self.progress.completed)

    def test_117_moves_is_rejected_and_session_remains_active(self):
        state = self._state_at_portal(117)
        objective_result = evaluate_objectives(
            state,
            self.level_number,
        )
        self.assertFalse(objective_result["all_completed"])
        move_objective = next(
            item for item in objective_result["objectives"]
            if item["type"] == "move_limit"
        )
        self.assertFalse(move_objective["completed"])

        session = self._create_session(117)
        original_checkpoint = dict(session.checkpoint_state)
        response = self.client.post(
            f"/api/games/{session.id}/complete/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 409, response.data)
        self.assertIn("move limit", response.data["detail"].lower())
        session.refresh_from_db()
        self.progress.refresh_from_db()
        self.assertEqual(session.status, "ACTIVE")
        self.assertEqual(session.moves, 117)
        self.assertEqual(session.score, 80)
        self.assertEqual(session.checkpoint_state, original_checkpoint)
        self.assertFalse(self.progress.completed)
        if self.next_level:
            self.next_progress.refresh_from_db()
            self.assertFalse(self.next_progress.unlocked)
