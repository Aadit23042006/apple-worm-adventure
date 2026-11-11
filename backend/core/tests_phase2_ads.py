import hashlib
import hmac

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import AdOpportunity, PlayerProfile, RewardTransaction

User = get_user_model()


class RewardedAdVerificationFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="phase2-ad-player",
            email="phase2-ad@example.com",
            password="safe-password-123",
        )
        PlayerProfile.objects.get_or_create(user=self.user)
        self.client.force_authenticate(user=self.user)

    @override_settings(
        AD_PROVIDER="mock",
        AD_PROVIDER_ADAPTER="",
        ALLOW_PROVIDER_FREE_DEMO_ADS=False,
    )
    def test_mock_provider_never_marks_ad_completed(self):
        offered = self.client.post(
            "/api/economy/ad-opportunity/",
            {"placement": "BOOSTER", "eventId": "phase2-mock-offer"},
            format="json",
        )
        self.assertEqual(offered.status_code, 200)
        self.assertEqual(offered.data["status"], "OFFERED")

        start = self.client.post(
            "/api/economy/ad-opportunity/phase2-mock-offer/request/",
            {}, format="json",
        )
        self.assertEqual(start.status_code, 503)
        self.assertEqual(start.data["status"], "AD_UNAVAILABLE")

        opportunity = AdOpportunity.objects.get(event_id="phase2-mock-offer")
        self.assertEqual(opportunity.status, "OFFERED")
        self.assertFalse(opportunity.completed_at)
        self.assertIn("REQUESTED", [entry["state"] for entry in opportunity.metadata["adLifecycle"]])
        self.assertFalse(RewardTransaction.objects.filter(event_id=opportunity.event_id).exists())

    def test_unverified_opportunity_cannot_be_claimed(self):
        AdOpportunity.objects.create(
            user=self.user, placement="BOOSTER", event_id="phase2-unverified",
            status="OFFERED", metadata={},
        )
        response = self.client.post(
            "/api/economy/claim-reward/",
            {"eventId": "phase2-unverified"}, format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(RewardTransaction.objects.filter(event_id="phase2-unverified").exists())

    @override_settings(AD_PROVIDER_WEBHOOK_SECRET="phase2-test-webhook-secret")
    def test_only_signed_callback_for_started_session_verifies_ad(self):
        opportunity = AdOpportunity.objects.create(
            user=self.user, placement="BOOSTER", event_id="phase2-signed-callback",
            status="AD_STARTED", provider_reference="provider-session-123", metadata={},
        )
        signature = hmac.new(
            b"phase2-test-webhook-secret",
            b"phase2-signed-callback:provider-session-123:COMPLETED",
            hashlib.sha256,
        ).hexdigest()
        response = self.client.post(
            "/api/economy/ad-provider-callback/",
            {"eventId": opportunity.event_id, "providerReference": opportunity.provider_reference, "eventStatus": "COMPLETED", "signature": signature},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, "VERIFIED")
        states = [entry["state"] for entry in opportunity.metadata["adLifecycle"]]
        self.assertEqual(states[-3:], ["AD_COMPLETED", "VERIFYING", "VERIFIED"])

    @override_settings(AD_PROVIDER_WEBHOOK_SECRET="phase2-test-webhook-secret")
    @override_settings(AD_PROVIDER_WEBHOOK_SECRET="phase2-test-webhook-secret")
    def test_verified_callback_claim_grants_once_and_records_full_lifecycle(self):
        opportunity = AdOpportunity.objects.create(
            user=self.user, placement="BOOSTER", event_id="phase2-full-lifecycle",
            status="AD_STARTED", provider_reference="provider-full-flow", metadata={
                "adLifecycle": [
                    {"state": "OFFERED", "at": "2026-01-01T00:00:00+00:00"},
                    {"state": "REQUESTED", "at": "2026-01-01T00:00:01+00:00"},
                    {"state": "AD_STARTED", "at": "2026-01-01T00:00:02+00:00"},
                ],
            },
        )
        signature = hmac.new(
            b"phase2-test-webhook-secret",
            b"phase2-full-lifecycle:provider-full-flow:COMPLETED",
            hashlib.sha256,
        ).hexdigest()
        callback_payload = {
            "eventId": opportunity.event_id,
            "providerReference": opportunity.provider_reference,
            "eventStatus": "COMPLETED",
            "signature": signature,
        }
        callback = self.client.post(
            "/api/economy/ad-provider-callback/", callback_payload, format="json",
        )
        self.assertEqual(callback.status_code, 200)
        duplicate_callback = self.client.post(
            "/api/economy/ad-provider-callback/", callback_payload, format="json",
        )
        self.assertEqual(duplicate_callback.status_code, 200)
        self.assertTrue(duplicate_callback.data["idempotent"])

        claim = self.client.post(
            "/api/economy/claim-reward/",
            {"eventId": opportunity.event_id}, format="json",
        )
        self.assertEqual(claim.status_code, 200)
        self.assertTrue(claim.data["granted"])

        opportunity.refresh_from_db()
        states = [entry["state"] for entry in opportunity.metadata["adLifecycle"]]
        self.assertEqual(
            states,
            ["OFFERED", "REQUESTED", "AD_STARTED", "AD_COMPLETED", "VERIFYING", "VERIFIED", "GRANTED"],
        )
        self.assertEqual(
            RewardTransaction.objects.filter(event_id=opportunity.event_id).count(), 1,
        )

    @override_settings(AD_PROVIDER_WEBHOOK_SECRET="phase2-test-webhook-secret")
    def test_invalid_signature_never_verifies_or_grants(self):
        opportunity = AdOpportunity.objects.create(
            user=self.user, placement="BOOSTER", event_id="phase2-invalid-signature",
            status="AD_STARTED", provider_reference="provider-invalid", metadata={},
        )
        response = self.client.post(
            "/api/economy/ad-provider-callback/",
            {
                "eventId": opportunity.event_id,
                "providerReference": opportunity.provider_reference,
                "eventStatus": "COMPLETED",
                "signature": "0" * 64,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, "AD_STARTED")
        self.assertFalse(opportunity.completed_at)
        self.assertFalse(RewardTransaction.objects.filter(event_id=opportunity.event_id).exists())

    @override_settings(AD_PROVIDER_WEBHOOK_SECRET="phase2-test-webhook-secret")
    def test_callback_cannot_complete_offer_that_never_started(self):
        opportunity = AdOpportunity.objects.create(
            user=self.user, placement="BOOSTER", event_id="phase2-not-started",
            status="OFFERED", provider_reference="", metadata={},
        )
        reference = "forged-reference"
        signature = hmac.new(
            b"phase2-test-webhook-secret",
            f"{opportunity.event_id}:{reference}:COMPLETED".encode(), hashlib.sha256,
        ).hexdigest()
        response = self.client.post(
            "/api/economy/ad-provider-callback/",
            {"eventId": opportunity.event_id, "providerReference": reference, "eventStatus": "COMPLETED", "signature": signature},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, "OFFERED")

    def test_duplicate_claim_does_not_create_second_reward(self):
        AdOpportunity.objects.create(
            user=self.user, placement="BOOSTER", event_id="phase2-duplicate-claim",
            status="VERIFIED", provider_reference="provider-ref", metadata={},
        )
        first = self.client.post(
            "/api/economy/claim-reward/",
            {"eventId": "phase2-duplicate-claim"}, format="json",
        )
        second = self.client.post(
            "/api/economy/claim-reward/",
            {"eventId": "phase2-duplicate-claim"}, format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.data["granted"])
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["duplicate"])
        self.assertEqual(RewardTransaction.objects.filter(event_id="phase2-duplicate-claim").count(), 1)
