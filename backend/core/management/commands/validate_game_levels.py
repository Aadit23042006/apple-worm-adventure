from collections import deque

from django.core.management.base import BaseCommand, CommandError

from core.models import Level
from core.views import level_objectives, level_static_config


class Command(BaseCommand):
    help = "Validate all active levels against the deterministic route and obstacle rules."

    def handle(self, *args, **options):
        levels = list(Level.objects.filter(is_active=True).order_by("number"))
        errors = []

        if len(levels) < 50:
            errors.append(f"Expected at least 50 active levels; found {len(levels)}.")

        for level in levels:
            cfg = level_static_config(level.number)
            size = cfg["size"]
            start = (1, 1)
            portal = (cfg["portal"]["r"], cfg["portal"]["c"])
            blocked = {(p["r"], p["c"]) for p in cfg["obstacles"]}

            # The authoritative route used by the game must remain traversable.
            route = {(1, c) for c in range(1, size - 1)}
            route.update((r, size - 2) for r in range(2, size - 1))
            if start in blocked or portal in blocked or not all(p not in blocked for p in route):
                errors.append(f"Level {level.number}: obstacle blocks the guaranteed route.")
                continue

            reachable = {start}
            queue = deque([start])
            while queue:
                r, c = queue.popleft()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nxt = (r + dr, c + dc)
                    if (
                        1 <= nxt[0] < size - 1
                        and 1 <= nxt[1] < size - 1
                        and nxt not in blocked
                        and nxt not in reachable
                    ):
                        reachable.add(nxt)
                        queue.append(nxt)

            if portal not in reachable:
                errors.append(f"Level {level.number}: portal is unreachable.")

            for apple in cfg["apples"]:
                if (apple["r"], apple["c"]) not in reachable:
                    errors.append(f"Level {level.number}: apple is unreachable.")

            objectives = level.config.get("objectives")
            expected_objectives = level_objectives(
                level.number,
                size=size,
                apple_count=len(cfg["apples"]),
            )
            if objectives != expected_objectives:
                errors.append(
                    f"Level {level.number}: objective configuration is missing or invalid."
                )
            if len(expected_objectives) < 2:
                errors.append(
                    f"Level {level.number}: expected multiple required objectives."
                )

        if errors:
            raise CommandError("\n".join(f"- {error}" for error in errors))

        self.stdout.write(self.style.SUCCESS(
            f"Level validation passed for {len(levels)} active levels."
        ))
