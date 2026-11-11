from django.db import migrations


ACHIEVEMENTS = [
    {
        "code": "LEVEL_5",
        "title": "Getting Started",
        "description": "Complete 5 levels",
        "icon": "🐛",
    },
    {
        "code": "LEVEL_10",
        "title": "Worm Explorer",
        "description": "Complete 10 levels",
        "icon": "🗺️",
    },
    {
        "code": "LEVEL_20",
        "title": "Puzzle Solver",
        "description": "Complete 20 levels",
        "icon": "🧩",
    },
    {
        "code": "LEVEL_30",
        "title": "Worm Master",
        "description": "Complete 30 levels",
        "icon": "⭐",
    },
    {
        "code": "LEVEL_40",
        "title": "Puzzle Expert",
        "description": "Complete 40 levels",
        "icon": "🏅",
    },
    {
        "code": "LEVEL_50",
        "title": "Apple Worm Champion",
        "description": "Complete 50 levels",
        "icon": "🏆",
    },
    {
        "code": "SCORE_1000",
        "title": "Score Starter",
        "description": "Reach 1,000 total score",
        "icon": "🎯",
    },
    {
        "code": "SCORE_5000",
        "title": "Score Chaser",
        "description": "Reach 5,000 total score",
        "icon": "🔥",
    },
    {
        "code": "SCORE_10000",
        "title": "Score Master",
        "description": "Reach 10,000 total score",
        "icon": "💎",
    },
    {
        "code": "SCORE_25000",
        "title": "High Scorer",
        "description": "Reach 25,000 total score",
        "icon": "👑",
    },
]


def seed_achievements(apps, schema_editor):
    Achievement = apps.get_model("core", "Achievement")

    for item in ACHIEVEMENTS:
        Achievement.objects.update_or_create(
            code=item["code"],
            defaults={
                "title": item["title"],
                "description": item["description"],
                "icon": item["icon"],
            },
        )


def unseed_achievements(apps, schema_editor):
    Achievement = apps.get_model("core", "Achievement")
    Achievement.objects.filter(
        code__in=[item["code"] for item in ACHIEVEMENTS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_level_completion_reward_ledger"),
    ]

    operations = [
        migrations.RunPython(
            seed_achievements,
            reverse_code=unseed_achievements,
        ),
    ]
