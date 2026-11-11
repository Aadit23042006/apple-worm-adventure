# VELoop Economy Documentation

## Reward placements
REVIVE, DOUBLE_SCORE, DOUBLE_COINS, EXTRA_MOVES, HINT, BOOSTER and DAILY_REWARD.

## Server-authoritative flow
1. Authenticated player creates an ad opportunity.
2. Provider completes the ad.
3. Provider callback is verified with the configured webhook secret.
4. The reward claim is accepted only for a verified opportunity.
5. The player profile row is locked while cooldown and daily-limit checks run.
6. A unique reward transaction is written using the ad event id.
7. The configured reward is applied to the wallet/game session.
8. Duplicate event ids return an idempotent response and do not grant twice.

## Safety controls
- Server-side reward calculation.
- Per-player reward cooldown.
- Calendar-day rewarded-ad limit using the application timezone.
- Per-level limits for revive, Double Score and Double Coins.
- Levels with the required `no_revive` objective persist `maxRevivesPerLevel: 0`; both ad-opportunity creation and reward claims reject Revive server-side.
- Wallet ledger with balance-after snapshots.
- Reward transaction ledger.
- Provider signature verification.
- No reward is granted for an unverified ad opportunity.

## Economy configuration
The default configuration is stored in the database and can be inspected/managed through the existing economy API/admin controls. Production values must be reviewed before launch.

## Unified reward ledger

Level-completion coins are recorded in both the wallet ledger (`WalletTransaction`, reason `LEVEL_REWARD`) and the unified reward ledger (`RewardTransaction`, placement `LEVEL_COMPLETION`, reward type `COINS`). The session-bound reward event is idempotent. Rewarded-ad cooldown and daily limits explicitly count only rewarded-ad placements, so level-completion rewards do not consume ad opportunities.
