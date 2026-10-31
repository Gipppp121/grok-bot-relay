"""Judge. Four checks, each 0, 1, or 2. Kill a total under 5 of 8."""

from __future__ import annotations

import json

from relay.bots.base import Bot
from relay.demo_data import READ_COST
from relay.models import BotResult

CHECKS = ("pain_sharp", "buyer_reachable", "build_small", "channel_fit")
MAX_SCORE = 8
KILL_UNDER = 5


def total_score(scores: dict) -> int:
    if set(scores) != set(CHECKS):
        raise ValueError("judge needs 4 checks")
    total = 0
    for name in CHECKS:
        value = scores[name]
        if value not in (0, 1, 2):
            raise ValueError(f"{name} must be 0, 1, or 2")
        total += value
    return total


def judge_status(scores: dict) -> str:
    return "KILL" if total_score(scores) < KILL_UNDER else "DONE"


class Judge(Bot):
    name = "judge"

    def run(self, idea, ctx) -> BotResult:
        ok, reason = ctx.budget.try_charge(
            self.name, READ_COST[self.name], ctx.clock.now()
        )
        if not ok:
            return BotResult("STOP", f"read cap {reason}")
        try:
            total = total_score(idea.scores)
        except ValueError as exc:
            return BotResult("KILL", str(exc))
        status = "KILL" if total < KILL_UNDER else "DONE"
        path = ctx.root / "verdicts" / f"{idea.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "idea_id": idea.id,
                    "scores": {name: idea.scores[name] for name in CHECKS},
                    "total": total,
                    "max": MAX_SCORE,
                    "status": status,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        verb = "killed" if status == "KILL" else "pass"
        return BotResult(status, f"score {total}/{MAX_SCORE} {verb}")
