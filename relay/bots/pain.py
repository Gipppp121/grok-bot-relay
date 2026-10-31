"""Pain Miner. Writes the pain note for one idea."""

from __future__ import annotations

from relay.bots.base import Bot
from relay.demo_data import READ_COST
from relay.models import BotResult


class PainMiner(Bot):
    name = "pain_miner"

    def run(self, idea, ctx) -> BotResult:
        ok, reason = ctx.budget.try_charge(
            self.name, READ_COST[self.name], ctx.clock.now()
        )
        if not ok:
            return BotResult("STOP", f"read cap {reason}")
        lines = [f"# {idea.title}", "", idea.summary, "", "## pains"]
        for pain in idea.pains:
            lines.append(f"- {pain}")
        lines.append("")
        path = ctx.root / "pains" / f"{idea.id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return BotResult("DONE", f"pains {len(idea.pains)}")
