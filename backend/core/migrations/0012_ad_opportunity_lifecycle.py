from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0011_no_revive_level_policy")]

    operations = [
        migrations.AlterField(
            model_name="adopportunity",
            name="status",
            field=models.CharField(
                choices=[
                    ("OFFERED", "Offered"),
                    ("REQUESTED", "Requested"),
                    ("AD_STARTED", "Ad started"),
                    ("AD_COMPLETED", "Ad completed"),
                    ("VERIFYING", "Verifying"),
                    ("VERIFIED", "Verified"),
                    ("GRANTED", "Granted"),
                    ("REJECTED", "Rejected"),
                    ("EXPIRED", "Expired"),
                ],
                default="OFFERED",
                max_length=16,
            ),
        ),
    ]
