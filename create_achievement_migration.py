from pathlib import Path

migration = Path("backend/core/migrations/0008_seed_production_achievements.py")

migration.write_text(
"""from django.db import migrations


def seed_production_achievements(apps, schema_editor):
    Achievement = apps.get_model("core", "Achievement")

    achievements = [
        (
            "LEVEL_5",
            "Getting Started",
            "Complete 5 levels",
            "🐛",
        ),
        (
            "LEVEL_40",
            "Puzzle Expert",
            "Complete 40 levels",
            "🏅",
        ),
        (
            "SCORE_5000",
            "Score Chaser",
            "Reach 5,000 total score",
            "🔥",
        ),
        (
            "SCORE_25000",
            "High Scorer",
            "Reach 25,000 total score",
            "🏆",
        ),
    ]

    for code, title, description, icon in achievements:
        Achievement.objects.get_or_create(
            code=code,
            defaults={
                "title": title,
                "description": description,
                "icon": icon,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_level_completion_reward_ledger"),
    ]

    operations = [
        migrations.RunPython(
            seed_production_achievements,
            migrations.RunPython.noop,
        ),
    ]
""",
    encoding="utf-8",
)

print(f"Created {migration}")
