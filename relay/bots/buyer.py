"""Buyer. The only bot that spends. Cap $40. A human yes on every buy."""

from __future__ import annotations

from relay.bots.base import Bot
from relay.models import BotResult
from relay.util import money

# 4000 cents. The config value is the one the engine enforces.
DEFAULT_CAP_CENTS = 4000


def decide(approved: bool, price_cents: int, spent_cents: int, cap_cents: int) -> str:
    if price_cents <= 0:
        raise ValueError("price must be positive")
    if not approved:
        return "WAIT"
    if spent_cents + price_cents > cap_cents:
        return "STOP"
    return "DONE"


class Buyer(Bot):
    name = "buyer"

    def run(self, idea, ctx) -> BotResult:
        # Buyer does not read X. A zero charge keeps the budget path honest.
        ok, reason = ctx.budget.try_charge(self.name, 0, ctx.clock.now())
        if not ok:
            return BotResult("STOP", f"read cap {reason}")
        approved = ctx.approvals.is_approved(idea.id)
        cap = ctx.config.buyer_cap_cents
        status = decide(approved, idea.price_cents, ctx.spend.total(), cap)
        if status == "WAIT":
            return BotResult("WAIT", "needs human yes")
        if status == "STOP":
            return BotResult(
                "STOP",
                f"spend cap {money(ctx.spend.total())} of {money(cap)}",
            )
        ctx.spend.record(idea.id, idea.price_cents, ctx.clock.now())
        return BotResult("DONE", f"bought {money(idea.price_cents)}")
