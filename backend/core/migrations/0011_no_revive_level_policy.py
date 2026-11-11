from django.db import migrations


def apply_no_revive_policy(apps, schema_editor):
    Level = apps.get_model("core", "Level")

    for level in Level.objects.filter(is_active=True).order_by("number"):
        config = dict(level.config or {})
        objectives = config.get("objectives") or []
        has_no_revive = any(
            objective.get("type") == "no_revive"
            and objective.get("required", True)
            for objective in objectives
        )

        if has_no_revive:
            config["maxRevivesPerLevel"] = 0
            level.config = config
            level.save(update_fields=["config"])


def reverse_no_revive_policy(apps, schema_editor):
    Level = apps.get_model("core", "Level")

    for level in Level.objects.filter(is_active=True).order_by("number"):
        config = dict(level.config or {})
        if "maxRevivesPerLevel" in config:
            config.pop("maxRevivesPerLevel", None)
            level.config = config
            level.save(update_fields=["config"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_level_objectives"),
    ]

    operations = [
        migrations.RunPython(
            apply_no_revive_policy,
            reverse_no_revive_policy,
        ),
    ]
