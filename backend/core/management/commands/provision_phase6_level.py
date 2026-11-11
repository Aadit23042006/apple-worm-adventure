from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings

from core.models import Level, PlayerProgress


class Command(BaseCommand):
    help = (
        "Provision a Phase 6 test account with a specific level unlocked "
        "without marking any level completed. This is disabled unless "
        "PHASE6_TEST_PROVISIONING_ENABLED=true is explicitly set."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--level", type=int, required=True)

    def handle(self, *args, **options):
        enabled = (
            str(getattr(settings, "PHASE6_TEST_PROVISIONING_ENABLED", False)).lower()
            == "true"
        )
        if not enabled:
            raise CommandError(
                "Phase 6 test provisioning is disabled. "
                "Set PHASE6_TEST_PROVISIONING_ENABLED=true explicitly "
                "for the local/evidence environment."
            )

        username = options["username"].strip()
        number = options["level"]

        if not username.startswith("phase6"):
            raise CommandError(
                "Refusing provisioning: test accounts must use the phase6* username prefix."
            )

        if number < 2:
            raise CommandError(
                "Only levels 2+ may be provisioned; Level 1 is unlocked normally."
            )

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"User '{username}' does not exist.") from exc

        level = (
            Level.objects
            .filter(number=number, is_active=True)
            .first()
        )
        if not level:
            raise CommandError(f"Active level {number} does not exist.")

        progress, _ = PlayerProgress.objects.get_or_create(
            user=user,
            level=level,
            defaults={"unlocked": False},
        )

        progress.unlocked = True
        progress.save(update_fields=["unlocked", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Provisioned {username}: Level {number} unlocked for Phase 6 testing. "
                f"completed={progress.completed}; no gameplay completion was created."
            )
        )
