from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0004_alter_level_options_alter_playerprogress_options_and_more')]

    operations = [
        migrations.AddField(
            model_name='gamesession',
            name='checkpoint_history',
            field=models.JSONField(default=list),
        ),
    ]
