"""Pitch. Writes a launch post draft. Does not post it."""

from __future__ import annotations

from relay.bots.base import Bot
from relay.demo_data import READ_COST
from relay.models import BotResult


class Pitch(Bot):
    name = "pitch"

    def run(self, idea, ctx) -> BotResult:
        ok, reason = ctx.budget.try_charge(
            self.name, READ_COST[self.name], ctx.clock.now()
        )
        if not ok:
            return BotResult("STOP", f"read cap {reason}")
        text = (
            f"# {idea.title}\n"
            "\n"
            f"{idea.pitch}\n"
            "\n"
            "A draft only. Nothing here is posted without a yes.\n"
        )
        path = ctx.root / "drafts" / f"{idea.id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return BotResult("DONE", "draft written")
