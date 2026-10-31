"""Scout. The only bot on a clock."""

from __future__ import annotations

import json

from relay.bots.base import Bot
from relay.demo_data import READ_COST
from relay.models import BotResult


class Scout(Bot):
    name = "scout"

    def run(self, idea, ctx) -> BotResult:
        del idea
        found = ctx.adapters.x.search("launch pains", limit=20)
        reads = int(getattr(ctx.adapters.x, "scout_reads", READ_COST["scout"]))
        ok, reason = ctx.budget.try_charge(self.name, reads, ctx.clock.now())
        if not ok:
            return BotResult("STOP", f"read cap {reason}", idea_id="_clock")
        ideas_dir = ctx.root / "ideas"
        ideas_dir.mkdir(parents=True, exist_ok=True)
        extra: list[tuple[str, str, str]] = []
        for item in found:
            path = ideas_dir / f"{item.id}.json"
            path.write_text(
                json.dumps(item.to_dict(), indent=2) + "\n",
                encoding="utf-8",
            )
            extra.append((item.id, "DONE", item.title))
        return BotResult(
            "DONE",
            f"monday clock {len(found)} ideas",
            idea_id="_clock",
            extra=extra,
        )
