from django.db import migrations


def build_objectives(number, size, apple_count):
    difficulty = min(10, 1 + (number - 1) // 6)
    max_moves = max(
        40,
        (size * size) + (apple_count * 12) + (difficulty * 4),
    )

    objectives = [
        {
            "id": "collect_apples",
            "type": "collect_apples",
            "title": "Collect all apples",
            "required": True,
            "target": apple_count,
        },
        {
            "id": "reach_portal",
            "type": "reach_portal",
            "title": "Reach the portal",
            "required": True,
        },
    ]

    if difficulty >= 4:
        objectives.append(
            {
                "id": "move_limit",
                "type": "move_limit",
                "title": "Finish within the move limit",
                "required": True,
                "target": max_moves,
            }
        )

    if difficulty >= 7:
        objectives.append(
            {
                "id": "no_revive",
                "type": "no_revive",
                "title": "Finish without using a revive",
                "required": True,
                "target": 0,
            }
        )

    return objectives


def populate_objectives(apps, schema_editor):
    Level = apps.get_model("core", "Level")

    for level in Level.objects.filter(is_active=True).order_by("number"):
        size = 7 + min(3, level.number // 12)
        apple_count = min(5, 2 + (level.number - 1) // 12)

        config = dict(level.config or {})
        config["rows"] = size
        config["cols"] = size
        config["difficulty"] = min(10, 1 + (level.number - 1) // 6)
        config["seed"] = level.number
        config["objectives"] = build_objectives(
            level.number,
            size,
            apple_count,
        )
        level.config = config
        level.save(update_fields=["config"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_fix_production_achievements"),
    ]

    operations = [
        migrations.RunPython(
            populate_objectives,
            migrations.RunPython.noop,
        ),
    ]
