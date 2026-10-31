"""Fast week. One wake per simulated minute, fixed Monday clock.

The spacing keeps the 30 reads a minute cap honest. Buyer still refuses a
buy with no yes. The yeses below are recorded through the approvals file
before Buyer runs. Two ideas are left waiting on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from relay.demo_data import DEMO_YES
from relay.clock import FrozenClock
from relay.models import HOURLY_WAKES_PER_WEEK
from relay.util import money
from relay.workspace import open_engine

# Monday 26 Oct 2026, 09:00 UTC. Reproducible on any weekday.
DEMO_START = datetime(2026, 10, 26, 9, 0, 0, tzinfo=timezone.utc)
MAX_STEPS = 500


@dataclass
class DemoReport:
    hourly: int
    relay_wakes: int
    by_bot: dict[str, int]
    spent_cents: int
    cap_cents: int
    killed: list[str] = field(default_factory=list)
    waiting: list[str] = field(default_factory=list)
    stopped: list[str] = field(default_factory=list)
    bought: list[str] = field(default_factory=list)
    transcript: list[str] = field(default_factory=list)

    @property
    def avoided(self) -> int:
        return self.hourly - self.relay_wakes


def simulate_week(root: Path) -> DemoReport:
    clock = FrozenClock(DEMO_START)
    engine = open_engine(root, clock=clock)
    transcript = [f"demo clock {DEMO_START.isoformat()}"]
    steps = 0
    while steps < MAX_STEPS:
        nxt = engine.peek()
        if nxt is None:
            break
        bot_name, idea_id = nxt
        if (
            bot_name == "buyer"
            and idea_id in DEMO_YES
            and not engine.approvals.is_approved(idea_id)
        ):
            engine.approvals.grant(idea_id, clock.now())
            transcript.append(f"demo yes {idea_id}")
        tick = engine.tick()
        steps += 1
        if tick is None:
            break
        transcript.append(f"wake {tick.bot} {tick.idea_id} {tick.status} {tick.note}")
        if tick.brief:
            transcript.append(tick.brief)
        clock.advance(minutes=1)
    else:
        raise RuntimeError("demo did not finish")
    final = engine.maybe_brief()
    if final:
        transcript.append(final)
    killed, waiting, stopped, bought = _outcomes(engine)
    return DemoReport(
        hourly=HOURLY_WAKES_PER_WEEK,
        relay_wakes=engine.wakes.total(),
        by_bot=engine.wakes.by_bot(),
        spent_cents=engine.spend.total(),
        cap_cents=engine.config.buyer_cap_cents,
        killed=killed,
        waiting=waiting,
        stopped=stopped,
        bought=bought,
        transcript=transcript,
    )


def _outcomes(engine):
    latest = {}
    for entry in engine.ledger.read():
        if entry.idea_id.startswith("_"):
            continue
        latest[entry.idea_id] = entry
    killed, waiting, stopped = [], [], []
    for idea_id, entry in latest.items():
        if entry.status == "KILL":
            killed.append(idea_id)
        elif entry.status == "WAIT":
            waiting.append(idea_id)
        elif entry.status == "STOP":
            stopped.append(idea_id)
    bought = [item["idea_id"] for item in engine.spend.items]
    return killed, waiting, stopped, bought


def format_report(report: DemoReport) -> str:
    parts = list(report.transcript)
    parts.append(f"spent {money(report.spent_cents)} of {money(report.cap_cents)}")
    parts.append(f"avoided {report.avoided}")
    parts.append(f"hourly {report.hourly} vs relay {report.relay_wakes}")
    return "\n".join(parts) + "\n"
