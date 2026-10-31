"""Builder. Writes a branch and PR plan. Dry run. Never merges."""

from __future__ import annotations

from relay.bots.base import Bot
from relay.demo_data import READ_COST
from relay.models import BotResult


class Builder(Bot):
    name = "builder"

    def run(self, idea, ctx) -> BotResult:
        ok, reason = ctx.budget.try_charge(
            self.name, READ_COST[self.name], ctx.clock.now()
        )
        if not ok:
            return BotResult("STOP", f"read cap {reason}")
        # SeededRepo.plan is local. The optional GitHub hook is not called.
        plan = ctx.adapters.github.plan(idea)
        if plan.get("merge"):
            raise RuntimeError("merge is disabled")
        text = _render(plan, idea.summary)
        path = ctx.root / "plans" / f"{idea.id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return BotResult("DONE", "dry run pr plan")


def _render(plan: dict, summary: str) -> str:
    commits = "\n".join(
        f"{index}. {line}" for index, line in enumerate(plan["commits"], start=1)
    )
    checks = ", ".join(plan["checks"])
    return (
        f"# PR plan {plan['idea_id']}\n"
        "\n"
        "dry run only. merge is off.\n"
        "\n"
        f"branch: {plan['branch']}\n"
        f"base: {plan['base']}\n"
        "\n"
        "## commits\n"
        "\n"
        f"{commits}\n"
        "\n"
        "## checks\n"
        "\n"
        f"{checks}\n"
        "\n"
        "## pull request\n"
        "\n"
        f"title: {plan['title']}\n"
        f"body: {summary} Builder stops after this plan.\n"
    )
