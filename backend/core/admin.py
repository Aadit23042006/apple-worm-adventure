from django.contrib import admin
from .models import *
for model in [PlayerProfile,Level,PlayerProgress,GameSession,WalletTransaction,AdOpportunity,RewardTransaction,Achievement,UserAchievement,EconomyConfig,DailyChallenge]: admin.site.register(model)
