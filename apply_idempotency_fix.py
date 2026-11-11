from pathlib import Path
import re
import shutil

views_path = Path("backend/core/views.py")
tests_path = Path("backend/core/tests_phase5_6.py")

views = views_path.read_text(encoding="utf-8")
tests = tests_path.read_text(encoding="utf-8")

# Backups
shutil.copy2(views_path, Path("backend/core/views.py.idempotency-backup"))
shutil.copy2(tests_path, Path("backend/core/tests_phase5_6.py.idempotency-backup"))

new_helper = '''def grant_coins(
    user,
    amount,
    reason,
    reference=None,
    reward_ledger=None,
):
    amount = int(amount)
    reference = reference or f"{reason}:{uuid.uuid4()}"

    with transaction.atomic():
        profile = (
            PlayerProfile.objects
            .select_for_update()
            .get(user=user)
        )

        # A wallet reference can be credited only once.
        existing_wallet = WalletTransaction.objects.filter(
            reference=reference
        ).first()

        if existing_wallet:
            if existing_wallet.user_id != user.id:
                raise ValueError("Wallet reference belongs to another user.")

            if reward_ledger:
                existing_reward = RewardTransaction.objects.filter(
                    event_id=reward_ledger["event_id"]
                ).first()

                if (
                    not existing_reward
                    or existing_reward.user_id != user.id
                ):
                    raise ValueError(
                        "Wallet and reward ledgers are inconsistent."
                    )

            return profile.coins

        # A reward event can also be granted only once.
        if reward_ledger:
            existing_reward = RewardTransaction.objects.filter(
                event_id=reward_ledger["event_id"]
            ).first()

            if existing_reward:
                if existing_reward.user_id != user.id:
                    raise ValueError(
                        "Reward event belongs to another user."
                    )

                # Do not silently repair a partial ledger by crediting again.
                raise ValueError(
                    "Reward event exists without its wallet transaction."
                )

        profile.coins = max(0, profile.coins + amount)
        profile.save(update_fields=["coins", "updated_at"])

        WalletTransaction.objects.create(
            user=user,
            amount=amount,
            balance_after=profile.coins,
            kind="CREDIT" if amount >= 0 else "DEBIT",
            reason=reason,
            reference=reference,
        )

        if reward_ledger:
            RewardTransaction.objects.create(
                user=user,
                placement=reward_ledger["placement"],
                reward_type=reward_ledger["reward_type"],
                amount=amount,
                event_id=reward_ledger["event_id"],
                status="GRANTED",
                metadata=reward_ledger.get("metadata", {}),
            )

        return profile.coins
'''

pattern = r"def grant_coins\([\s\S]*?\r?\n\r?\n# ============================================================\r?\n# REFRESH TOKENS"
replacement = new_helper + "\\n\\n# ============================================================\\n# REFRESH TOKENS"

views_new, count = re.subn(pattern, replacement, views, count=1)
if count != 1:
    raise SystemExit("STOP: Could not safely locate grant_coins(). No source change made.")

# Prevent an existing event belonging to another user from being accepted.
old_claim = '''    if existing:
        if opportunity.status != "GRANTED":'''
new_claim = '''    if existing:
        if existing.user_id != request.user.id:
            return Response(
                {"detail": "Reward event belongs to another user."},
                status=409,
            )

        if opportunity.status != "GRANTED":'''

if old_claim not in views_new:
    raise SystemExit("STOP: Could not safely locate claim_reward duplicate block.")

views_new = views_new.replace(old_claim, new_claim, 1)

# Add isolated regression tests to the existing reward test class.
test_addition = '''
    def test_duplicate_level_reward_does_not_credit_wallet_twice(self):
        from .models import RewardTransaction, WalletTransaction
        from .views import grant_coins

        reference = "idempotency-test:level:session-001"
        event_id = "idempotency-test:level-completion:session-001"
        ledger = {
            "event_id": event_id,
            "placement": "LEVEL_COMPLETION",
            "reward_type": "COINS",
            "metadata": {"source": "idempotency_test"},
        }

        first_balance = grant_coins(
            self.user, 25, "LEVEL_REWARD", reference, reward_ledger=ledger
        )
        second_balance = grant_coins(
            self.user, 25, "LEVEL_REWARD", reference, reward_ledger=ledger
        )

        self.assertEqual(first_balance, 25)
        self.assertEqual(second_balance, 25)
        self.assertEqual(PlayerProfile.objects.get(user=self.user).coins, 25)
        self.assertEqual(
            WalletTransaction.objects.filter(reference=reference).count(), 1
        )
        self.assertEqual(
            RewardTransaction.objects.filter(event_id=event_id).count(), 1
        )

    def test_duplicate_wallet_reference_does_not_credit_twice(self):
        from .models import WalletTransaction
        from .views import grant_coins

        reference = "idempotency-test:generic-credit-001"

        grant_coins(self.user, 25, "TEST_REWARD", reference)
        grant_coins(self.user, 25, "TEST_REWARD", reference)

        self.assertEqual(PlayerProfile.objects.get(user=self.user).coins, 25)
        self.assertEqual(
            WalletTransaction.objects.filter(reference=reference).count(), 1
        )

    def test_wallet_reference_cannot_be_reused_by_another_user(self):
        from .models import WalletTransaction
        from .views import grant_coins

        reference = "idempotency-test:cross-user-001"
        grant_coins(self.user, 25, "TEST_REWARD", reference)

        other_user = User.objects.create_user(
            username="idempotency_other",
            email="idempotency_other@example.com",
            password="safe-password-123",
        )
        PlayerProfile.objects.get_or_create(user=other_user)

        with self.assertRaises(ValueError):
            grant_coins(other_user, 25, "TEST_REWARD", reference)

        self.assertEqual(PlayerProfile.objects.get(user=self.user).coins, 25)
        self.assertEqual(PlayerProfile.objects.get(user=other_user).coins, 0)
        self.assertEqual(
            WalletTransaction.objects.filter(reference=reference).count(), 1
        )

'''

marker = "\n\nclass NoReviveLevelEnforcementTests"
if marker not in tests:
    raise SystemExit("STOP: Could not find test insertion point.")

if "test_duplicate_level_reward_does_not_credit_wallet_twice" in tests:
    raise SystemExit("STOP: Idempotency tests already appear to exist.")

tests_new = tests.replace(marker, "\\n" + test_addition + marker, 1)

# Write only after every safety check has passed.
views_path.write_text(views_new, encoding="utf-8")
tests_path.write_text(tests_new, encoding="utf-8")

print("PATCH APPLIED")
print("Updated: backend/core/views.py")
print("Updated: backend/core/tests_phase5_6.py")
print("Backups created for both original files.")


