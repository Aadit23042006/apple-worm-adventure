import uuid
from django.conf import settings
from django.db import models

class PlayerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='player_profile')
    coins=models.PositiveIntegerField(default=0); total_score=models.PositiveIntegerField(default=0)
    # Server-side timestamp for the last successfully granted rewarded-ad claim.
    # This is the authoritative cooldown anchor; it cannot be supplied by the client.
    last_reward_claim_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)

class Level(models.Model):
    number=models.PositiveIntegerField(unique=True); config=models.JSONField(default=dict); is_active=models.BooleanField(default=True)
    class Meta: ordering=['number']

class PlayerProgress(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='progress'); level=models.ForeignKey(Level,on_delete=models.CASCADE)
    unlocked=models.BooleanField(default=False); completed=models.BooleanField(default=False); stars=models.PositiveSmallIntegerField(default=0)
    best_score=models.PositiveIntegerField(default=0); best_moves=models.PositiveIntegerField(null=True,blank=True); best_time_ms=models.PositiveIntegerField(null=True,blank=True); attempts=models.PositiveIntegerField(default=0); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','level'],name='unique_user_level_progress')]; ordering=['level__number']

class GameSession(models.Model):
    STATUS=[('ACTIVE','Active'),('COMPLETED','Completed'),('FAILED','Failed'),('ABANDONED','Abandoned')]
    id=models.UUIDField(default=uuid.uuid4,primary_key=True,editable=False); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='game_sessions'); level=models.ForeignKey(Level,on_delete=models.PROTECT)
    initial_state=models.JSONField(default=dict); checkpoint_state=models.JSONField(default=dict); checkpoint_history=models.JSONField(default=list); score=models.PositiveIntegerField(default=0); moves=models.PositiveIntegerField(default=0); status=models.CharField(max_length=16,choices=STATUS,default='ACTIVE'); revives_used=models.PositiveSmallIntegerField(default=0)
    started_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True); completed_at=models.DateTimeField(null=True,blank=True)

class WalletTransaction(models.Model):
    KIND=[('CREDIT','Credit'),('DEBIT','Debit'),('REVERSAL','Reversal'),('BONUS','Bonus')]
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='wallet_transactions'); amount=models.IntegerField(); balance_after=models.IntegerField(); kind=models.CharField(max_length=16,choices=KIND); reason=models.CharField(max_length=64); reference=models.CharField(max_length=128,unique=True); created_at=models.DateTimeField(auto_now_add=True)

class AdOpportunity(models.Model):
    PLACEMENTS=[('REVIVE','Revive'),('HINT','Hint'),('DOUBLE_SCORE','Double Score'),('DOUBLE_COINS','Double Coins'),('EXTRA_MOVES','Extra Moves'),('BOOSTER','Booster'),('DAILY_REWARD','Daily Reward')]
    STATUS=[('OFFERED','Offered'),('REQUESTED','Requested'),('AD_STARTED','Ad started'),('AD_COMPLETED','Ad completed'),('VERIFYING','Verifying'),('VERIFIED','Verified'),('GRANTED','Granted'),('REJECTED','Rejected'),('EXPIRED','Expired')]
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='ad_opportunities'); placement=models.CharField(max_length=24,choices=PLACEMENTS); event_id=models.CharField(max_length=128,unique=True); status=models.CharField(max_length=16,choices=STATUS,default='OFFERED'); metadata=models.JSONField(default=dict); provider_reference=models.CharField(max_length=128,blank=True); created_at=models.DateTimeField(auto_now_add=True); completed_at=models.DateTimeField(null=True,blank=True)

class RewardTransaction(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='reward_transactions'); placement=models.CharField(max_length=24); reward_type=models.CharField(max_length=32); amount=models.IntegerField(default=0); event_id=models.CharField(max_length=128,unique=True); status=models.CharField(max_length=16,default='GRANTED'); metadata=models.JSONField(default=dict); created_at=models.DateTimeField(auto_now_add=True)

class Achievement(models.Model):
    code=models.CharField(max_length=64,unique=True); title=models.CharField(max_length=120); description=models.CharField(max_length=255); icon=models.CharField(max_length=16,default='\U0001F3C6')

class UserAchievement(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='achievements'); achievement=models.ForeignKey(Achievement,on_delete=models.CASCADE); unlocked_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['user','achievement'],name='unique_user_achievement')]

class EconomyConfig(models.Model):
    key=models.CharField(max_length=64,unique=True,default='default'); config=models.JSONField(default=dict); updated_at=models.DateTimeField(auto_now=True)

class DailyChallenge(models.Model):
    date=models.DateField(unique=True); config=models.JSONField(default=dict)

class RefreshSession(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='refresh_sessions'); token_hash=models.CharField(max_length=64,unique=True); expires_at=models.DateTimeField(); revoked_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)

class EmailVerification(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='email_verification'); token_hash=models.CharField(max_length=64,unique=True); expires_at=models.DateTimeField(); verified_at=models.DateTimeField(null=True,blank=True)

class PasswordResetToken(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='password_resets'); token_hash=models.CharField(max_length=64,unique=True); expires_at=models.DateTimeField(); used_at=models.DateTimeField(null=True,blank=True)

class ApiKey(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='api_keys'); name=models.CharField(max_length=80); key_prefix=models.CharField(max_length=12); key_hash=models.CharField(max_length=64,unique=True); last_used_at=models.DateTimeField(null=True,blank=True); revoked_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)


