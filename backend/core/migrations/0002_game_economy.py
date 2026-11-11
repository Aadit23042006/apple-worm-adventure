from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def seed_levels(apps, schema_editor):
    Level = apps.get_model('core','Level')
    EconomyConfig = apps.get_model('core','EconomyConfig')
    Achievement = apps.get_model('core','Achievement')
    for n in range(1, 61):
        size = 7 + min(n // 12, 3)
        config = {'rows': size, 'cols': size, 'difficulty': min(10, 1 + (n-1)//6), 'seed': n}
        Level.objects.get_or_create(number=n, defaults={'config': config})
    EconomyConfig.objects.get_or_create(key='default', defaults={'config': {
        'levelCompletionCoins':25,'doubleCoinsMultiplier':2,'doubleScoreMultiplier':2,'extraMoves':5,
        'maxRewardedAdsPerDay':10,'maxRevivesPerLevel':1,'maxDoubleScorePerLevel':1,'maxDoubleCoinsPerLevel':1,
        'adCooldownSeconds':30,'hintEnabled':True,'boosterEnabled':True,'levelCompletionScore':100,
    }})
    achievements = [
        ('FIRST_APPLE','First Bite','Collect your first apple','🍎'),('LEVEL_10','Puzzle Rookie','Complete 10 levels','🌱'),
        ('LEVEL_25','Puzzle Pro','Complete 25 levels','⭐'),('LEVEL_50','Worm Master','Complete 50 levels','👑'),
        ('THREE_STARS','Perfect Run','Earn three stars on a level','💎'),('SCORE_10000','Score Hunter','Reach 10,000 total score','🎯'),
    ]
    for code,title,desc,icon in achievements: Achievement.objects.get_or_create(code=code, defaults={'title':title,'description':desc,'icon':icon})

class Migration(migrations.Migration):
    dependencies=[('core','0001_initial')]
    operations=[
        migrations.CreateModel(name='Level',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('number',models.PositiveIntegerField(unique=True)),('config',models.JSONField(default=dict)),('is_active',models.BooleanField(default=True))]),
        migrations.CreateModel(name='EconomyConfig',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('key',models.CharField(default='default',max_length=64,unique=True)),('config',models.JSONField(default=dict)),('updated_at',models.DateTimeField(auto_now=True))]),
        migrations.CreateModel(name='DailyChallenge',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('date',models.DateField(unique=True)),('config',models.JSONField(default=dict))]),
        migrations.CreateModel(name='Achievement',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('code',models.CharField(max_length=64,unique=True)),('title',models.CharField(max_length=120)),('description',models.CharField(max_length=255)),('icon',models.CharField(default='🏆',max_length=16))]),
        migrations.CreateModel(name='GameSession',fields=[('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),('initial_state',models.JSONField(default=dict)),('checkpoint_state',models.JSONField(default=dict)),('score',models.PositiveIntegerField(default=0)),('moves',models.PositiveIntegerField(default=0)),('status',models.CharField(choices=[('ACTIVE','Active'),('COMPLETED','Completed'),('FAILED','Failed'),('ABANDONED','Abandoned')],default='ACTIVE',max_length=16)),('revives_used',models.PositiveSmallIntegerField(default=0)),('started_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),('completed_at',models.DateTimeField(blank=True,null=True)),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='game_sessions',to=settings.AUTH_USER_MODEL)),('level',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='core.level'))]),
        migrations.CreateModel(name='PlayerProgress',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('unlocked',models.BooleanField(default=False)),('completed',models.BooleanField(default=False)),('stars',models.PositiveSmallIntegerField(default=0)),('best_score',models.PositiveIntegerField(default=0)),('best_moves',models.PositiveIntegerField(blank=True,null=True)),('best_time_ms',models.PositiveIntegerField(blank=True,null=True)),('attempts',models.PositiveIntegerField(default=0)),('updated_at',models.DateTimeField(auto_now=True)),('level',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='core.level')),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='progress',to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name='WalletTransaction',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('amount',models.IntegerField()),('balance_after',models.IntegerField()),('kind',models.CharField(choices=[('CREDIT','Credit'),('DEBIT','Debit'),('REVERSAL','Reversal'),('BONUS','Bonus')],max_length=16)),('reason',models.CharField(max_length=64)),('reference',models.CharField(max_length=128,unique=True)),('created_at',models.DateTimeField(auto_now_add=True)),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='wallet_transactions',to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name='AdOpportunity',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('placement',models.CharField(choices=[('REVIVE','Revive'),('HINT','Hint'),('DOUBLE_SCORE','Double Score'),('DOUBLE_COINS','Double Coins'),('EXTRA_MOVES','Extra Moves'),('BOOSTER','Booster'),('DAILY_REWARD','Daily Reward')],max_length=24)),('event_id',models.CharField(max_length=128,unique=True)),('status',models.CharField(choices=[('OFFERED','Offered'),('STARTED','Started'),('COMPLETED','Completed'),('REJECTED','Rejected'),('EXPIRED','Expired')],default='OFFERED',max_length=16)),('metadata',models.JSONField(default=dict)),('created_at',models.DateTimeField(auto_now_add=True)),('completed_at',models.DateTimeField(blank=True,null=True)),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='ad_opportunities',to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name='RewardTransaction',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('placement',models.CharField(max_length=24)),('reward_type',models.CharField(max_length=32)),('amount',models.IntegerField(default=0)),('event_id',models.CharField(max_length=128,unique=True)),('status',models.CharField(default='GRANTED',max_length=16)),('metadata',models.JSONField(default=dict)),('created_at',models.DateTimeField(auto_now_add=True)),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='reward_transactions',to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name='UserAchievement',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('unlocked_at',models.DateTimeField(auto_now_add=True)),('achievement',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='core.achievement')),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='achievements',to=settings.AUTH_USER_MODEL))]),
        migrations.AddConstraint(model_name='playerprogress',constraint=models.UniqueConstraint(fields=('user','level'),name='unique_user_level_progress')),
        migrations.AddConstraint(model_name='userachievement',constraint=models.UniqueConstraint(fields=('user','achievement'),name='unique_user_achievement')),
        migrations.RunPython(seed_levels, migrations.RunPython.noop),
    ]
