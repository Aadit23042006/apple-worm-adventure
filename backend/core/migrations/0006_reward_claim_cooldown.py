from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_gamesession_checkpoint_history'),
    ]

    operations = [
        migrations.AddField(
            model_name='playerprofile',
            name='last_reward_claim_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
