from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Achievement, PlayerProfile, UserAchievement

User = get_user_model()


class AchievementsApiIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="phase3-achievements-player",
            email="phase3-achievements@example.com",
            password="safe-password-123",
        )

        # Isolate tests from migration-seeded production achievements.
        Achievement.objects.all().delete()

    def test_achievements_endpoint_requires_authentication(self):
        response = self.client.get("/api/achievements/")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_player_receives_achievement_data_and_unlock_state(self):
        unlocked = Achievement.objects.create(
            code="phase3-first-win",
            title="First Win",
            description="Complete your first level.",
            icon="🏆",
        )
        locked = Achievement.objects.create(
            code="phase3-master",
            title="Master",
            description="Complete many levels.",
            icon="⭐",
        )
        UserAchievement.objects.create(user=self.user, achievement=unlocked)
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/achievements/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data.keys()), {"achievements"})
        records = {item["code"]: item for item in response.data["achievements"]}
        self.assertIn("phase3-first-win", records)
        self.assertIn("phase3-master", records)
        self.assertTrue(records["phase3-first-win"]["unlocked"])
        self.assertFalse(records["phase3-master"]["unlocked"])
        self.assertEqual(records["phase3-first-win"]["title"], "First Win")

    def test_new_account_receives_catalog_with_locked_state(self):
        Achievement.objects.create(
            code="phase5-new-player",
            title="First Steps",
            description="Start your adventure.",
            icon="🏆",
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/achievements/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["achievements"]), 1)
        self.assertFalse(response.data["achievements"][0]["unlocked"])

    def test_empty_achievement_catalog_returns_empty_array(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/achievements/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["achievements"], [])

    def test_empty_leaderboard_returns_empty_array_for_new_account(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/leaderboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["leaderboard"], [])

    def test_existing_player_appears_in_leaderboard_with_server_score(self):
        PlayerProfile.objects.create(user=self.user, total_score=125, coins=10)
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/leaderboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["leaderboard"]), 1)
        self.assertEqual(response.data["leaderboard"][0]["username"], self.user.username)
        self.assertEqual(response.data["leaderboard"][0]["score"], 125)
