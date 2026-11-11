# Phase 4 Step 5 — Permanent Reward Safety Fix

## Fixed server-side guarantees

1. Reward cooldown is enforced inside `claim_reward`, so a client cannot bypass it by creating a new ad opportunity.
2. Cooldown is anchored to the server's `PlayerProfile.last_reward_claim_at` timestamp.
3. Existing profiles are backward-compatible: if the timestamp is empty, the latest granted `RewardTransaction` is used as the fallback anchor.
4. The profile row is locked with `select_for_update()` during a claim, preventing two concurrent reward claims from both passing the cooldown check.
5. The timestamp update and `RewardTransaction` creation occur in the same atomic transaction.
6. The daily rewarded-ad limit counts only `RewardTransaction(status='GRANTED')`, not merely created opportunities.
7. The opportunity endpoint also blocks creation during cooldown and uses granted rewards for the daily limit.
8. Duplicate event claims remain idempotent and return the original reward amount without creating another ledger entry.
9. Client-supplied reward amounts/types cannot override the server-calculated reward.

## Migration

`core/migrations/0006_reward_claim_cooldown.py` adds the server-side cooldown anchor to `PlayerProfile`.

## Required runtime verification

After extracting this version:

```cmd
docker compose build --no-cache backend
docker compose up -d backend
docker compose ps
curl -i http://localhost:8002/api/health/
```

Then, while authenticated with the normal DRF header:

```js
Authorization: `Token ${localStorage.getItem('veloop_auth_token')}`
```

### Cooldown test

1. Create and claim one fresh rewarded-ad opportunity. It must grant once.
2. Immediately create another opportunity. It must return HTTP 429 with `Reward cooldown active.`.
3. If a second opportunity already exists from before this fix, claim it immediately. It must also return HTTP 429.
4. After the configured cooldown expires, a fresh opportunity may be created and claimed.

### Daily-limit test

Grant rewards until the configured daily limit is reached. Further opportunity creation and claim attempts must return HTTP 429. Creating unclaimed opportunities must not consume the daily reward allowance.

### Duplicate test

Repeat the exact same event after a successful claim. It must return `granted: false`, `duplicate: true`, and must not increase the wallet or create another reward transaction.
