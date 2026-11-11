from django.db import migrations


def backfill_level_completion_reward_ledger(apps, schema_editor):
    WalletTransaction = apps.get_model("core", "WalletTransaction")
    RewardTransaction = apps.get_model("core", "RewardTransaction")

    for tx in WalletTransaction.objects.filter(reason="LEVEL_REWARD"):
        event_id = f"level-completion:{tx.reference}"
        RewardTransaction.objects.get_or_create(
            event_id=event_id,
            defaults={
                "user_id": tx.user_id,
                "placement": "LEVEL_COMPLETION",
                "reward_type": "COINS",
                "amount": tx.amount,
                "status": "GRANTED",
                "metadata": {
                    "source": "level_completion",
                    "walletReference": tx.reference,
                    "backfilled": True,
                },
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_reward_claim_cooldown"),
    ]

    operations = [
        migrations.RunPython(
            backfill_level_completion_reward_ledger,
            migrations.RunPython.noop,
        ),
    ]
