from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from .models import (
    AdOpportunity,
    PlayerProfile,
    RewardTransaction,
    WalletTransaction,
)

User = get_user_model()


class RewardReplayAntiCheatTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="reward_owner",
            email="reward_owner@example.com",
            password="safe-password-123",
        )
        self.attacker = User.objects.create_user(
            username="reward_attacker",
            email="reward_attacker@example.com",
            password="safe-password-123",
        )

        self.owner_profile = PlayerProfile.objects.create(
            user=self.owner
        )
        PlayerProfile.objects.create(user=self.attacker)

        owner_token = Token.objects.create(user=self.owner)
        attacker_token = Token.objects.create(user=self.attacker)

        self.owner_client = APIClient()
        self.owner_client.credentials(
            HTTP_AUTHORIZATION=f"Token {owner_token.key}"
        )

        self.attacker_client = APIClient()
        self.attacker_client.credentials(
            HTTP_AUTHORIZATION=f"Token {attacker_token.key}"
        )

        self.event_id = "anticheat-step7-daily-reward"

        self.opportunity = AdOpportunity.objects.create(
            user=self.owner,
            placement="DAILY_REWARD",
            event_id=self.event_id,
            status="VERIFIED",
            provider_reference="verified-provider-reference",
            metadata={},
        )

    def test_replayed_claim_does_not_grant_coins_twice(self):
        endpoint = "/api/economy/claim-reward/"
        payload = {"eventId": self.event_id}

        first = self.owner_client.post(
            endpoint,
            payload,
            format="json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.data.get("granted"))
        self.assertEqual(first.data.get("amount"), 25)

        self.owner_profile.refresh_from_db()
        balance_after_first = self.owner_profile.coins

        wallet_count_after_first = WalletTransaction.objects.filter(
            user=self.owner
        ).count()

        reward_count_after_first = RewardTransaction.objects.filter(
            user=self.owner
        ).count()

        self.assertEqual(balance_after_first, 25)
        self.assertEqual(wallet_count_after_first, 1)
        self.assertEqual(reward_count_after_first, 1)

        second = self.owner_client.post(
            endpoint,
            payload,
            format="json",
        )

        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.data.get("granted"))
        self.assertTrue(second.data.get("duplicate"))
        self.assertEqual(second.data.get("amount"), 25)

        self.owner_profile.refresh_from_db()

        self.assertEqual(
            self.owner_profile.coins,
            balance_after_first,
        )
        self.assertEqual(
            WalletTransaction.objects.filter(user=self.owner).count(),
            wallet_count_after_first,
        )
        self.assertEqual(
            RewardTransaction.objects.filter(user=self.owner).count(),
            reward_count_after_first,
        )

    def test_another_user_cannot_claim_owners_event(self):
        response = self.attacker_client.post(
            "/api/economy/claim-reward/",
            {"eventId": self.event_id},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.owner_profile.refresh_from_db()
        self.assertEqual(self.owner_profile.coins, 0)

        self.assertFalse(
            RewardTransaction.objects.filter(
                user=self.attacker,
                event_id=self.event_id,
            ).exists()
        )

        self.assertFalse(
            WalletTransaction.objects.filter(
                user=self.attacker,
            ).exists()
        )
