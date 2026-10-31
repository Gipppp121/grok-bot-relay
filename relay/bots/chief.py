"""Chief. Updates the launch board. The brief is printed by the engine."""

from __future__ import annotations

from relay.board import publish_board
from relay.bots.base import Bot
from relay.demo_data import READ_COST
from relay.models import BotResult


class Chief(Bot):
    name = "chief"

    def run(self, idea, ctx) -> BotResult:
        del idea
        ok, reason = ctx.budget.try_charge(
            self.name, READ_COST[self.name], ctx.clock.now()
        )
        if not ok:
            return BotResult("STOP", f"read cap {reason}")
        publish_board(ctx.root)
        return BotResult("DONE", "board updated")
