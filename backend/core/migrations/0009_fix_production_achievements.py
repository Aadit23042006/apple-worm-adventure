from django.db import migrations


REQUIRED_ACHIEVEMENTS = [
    ("LEVEL_5", "Getting Started", "Complete 5 levels", "🐛"),
    ("LEVEL_10", "Worm Explorer", "Complete 10 levels", "🗺️"),
    ("LEVEL_20", "Puzzle Solver", "Complete 20 levels", "🧩"),
    ("LEVEL_30", "Worm Master", "Complete 30 levels", "⭐"),
    ("LEVEL_40", "Puzzle Expert", "Complete 40 levels", "🏅"),
    ("LEVEL_50", "Apple Worm Champion", "Complete 50 levels", "🏆"),
    ("SCORE_1000", "Score Starter", "Reach 1,000 total score", "🎯"),
    ("SCORE_5000", "Score Chaser", "Reach 5,000 total score", "🔥"),
    ("SCORE_10000", "Score Master", "Reach 10,000 total score", "💎"),
    ("SCORE_25000", "High Scorer", "Reach 25,000 total score", "👑"),
]

OBSOLETE_CODES = {
    "FIRST_APPLE",
    "LEVEL_25",
    "THREE_STARS",
}


def seed_required_achievements(apps, schema_editor):
    Achievement = apps.get_model("core", "Achievement")
    UserAchievement = apps.get_model("core", "UserAchievement")
    PlayerProfile = apps.get_model("core", "PlayerProfile")
    PlayerProgress = apps.get_model("core", "PlayerProgress")

    # Remove obsolete achievement definitions.
    # Their unlocks are recomputed below from authoritative player data.
    Achievement.objects.filter(code__in=OBSOLETE_CODES).delete()

    # Create/update the exact production achievement definitions.
    for code, title, description, icon in REQUIRED_ACHIEVEMENTS:
        Achievement.objects.update_or_create(
            code=code,
            defaults={
                "title": title,
                "description": description,
                "icon": icon,
            },
        )

    # Recompute achievement unlocks from authoritative player data.
    #
    # This intentionally does not carry FIRST_APPLE / LEVEL_25 /
    # THREE_STARS forward because those rules are no longer part of
    # the production achievement set.
    #
    # Instead, every required achievement is evaluated against the
    # player's persisted completed-level count and total score.
    for profile in PlayerProfile.objects.all().iterator():
        user_id = profile.user_id

        completed_levels = PlayerProgress.objects.filter(
            user_id=user_id,
            completed=True,
        ).count()

        score = profile.total_score or 0

        level_requirements = {
            "LEVEL_5": 5,
            "LEVEL_10": 10,
            "LEVEL_20": 20,
            "LEVEL_30": 30,
            "LEVEL_40": 40,
            "LEVEL_50": 50,
        }

        score_requirements = {
            "SCORE_1000": 1000,
            "SCORE_5000": 5000,
            "SCORE_10000": 10000,
            "SCORE_25000": 25000,
        }

        unlocked_codes = set()

        for code, required in level_requirements.items():
            if completed_levels >= required:
                unlocked_codes.add(code)

        for code, required in score_requirements.items():
            if score >= required:
                unlocked_codes.add(code)

        achievements = {
            achievement.code: achievement
            for achievement in Achievement.objects.filter(
                code__in=unlocked_codes
            )
        }

        for code in unlocked_codes:
            achievement = achievements.get(code)
            if achievement is None:
                continue

            UserAchievement.objects.get_or_create(
                user_id=user_id,
                achievement_id=achievement.id,
            )


def reverse_seed(apps, schema_editor):
    Achievement = apps.get_model("core", "Achievement")
    Achievement.objects.filter(
        code__in={code for code, *_ in REQUIRED_ACHIEVEMENTS}
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_seed_production_achievements"),
    ]

    operations = [
        migrations.RunPython(
            seed_required_achievements,
            reverse_seed,
        ),
    ]
