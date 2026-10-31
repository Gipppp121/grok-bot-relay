"""Trigger engine.

Scout runs once a week, at Monday 9am local time (or whenever the clock says
that moment has arrived). Every other bot runs only when the previous bot
wrote DONE for that idea. One tick runs one bot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from relay.adapters import default_adapters
from relay.board import publish_board, render_brief
from relay.bots import default_bots
from relay.budget import Budget
from relay.clock import Clock, SystemClock
from relay.config import Config
from relay.ledger import Ledger
from relay.models import CHAIN, BotResult, Entry, Idea, Tick, previous_bot
from relay.state import Approvals, ResumeBook, Spend, Wakes
from relay.util import atomic_write, parse_ts


@dataclass
class Context:
    root: Path
    config: Config
    clock: Clock
    ledger: Ledger
    budget: Budget
    spend: Spend
    approvals: Approvals
    wakes: Wakes
    resume: ResumeBook
    adapters: object


class Engine:
    def __init__(
        self,
        root: Path,
        config: Config,
        clock: Clock | None = None,
        bots: dict | None = None,
        adapters=None,
    ):
        self.root = root
        self.config = config
        self.clock = clock or SystemClock()
        self.bots = bots or default_bots()
        self.adapters = adapters or default_adapters()
        relay_dir = root / ".relay"
        relay_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(root / "ledger.jsonl")
        self.budget = Budget(relay_dir / "budget.json", config)
        self.spend = Spend(relay_dir / "spend.json", config.buyer_cap_cents)
        self.approvals = Approvals(root / "approvals.json")
        self.wakes = Wakes(relay_dir / "wakes.jsonl")
        self.resume = ResumeBook(relay_dir / "resume.json")
        self.ctx = Context(
            root=root,
            config=config,
            clock=self.clock,
            ledger=self.ledger,
            budget=self.budget,
            spend=self.spend,
            approvals=self.approvals,
            wakes=self.wakes,
            resume=self.resume,
            adapters=self.adapters,
        )
        self._watermark = relay_dir / "brief.watermark"

    def peek(self) -> tuple[str, str | None] | None:
        self.approvals.reload()
        return self._select(self._index())

    def tick(self) -> Tick | None:
        self.approvals.reload()
        chosen = self._select(self._index())
        if chosen is None:
            return None
        bot_name, idea_id = chosen
        return self._run(bot_name, idea_id)

    def maybe_brief(self) -> str | None:
        size = self.ledger.size()
        previous = None
        if self._watermark.exists():
            raw = self._watermark.read_text(encoding="utf-8").strip()
            if raw.isdigit():
                previous = int(raw)
        if previous is not None and previous == size:
            return None
        if size == 0:
            atomic_write(self._watermark, "0\n")
            return None
        entries = self.ledger.read()
        text = render_brief(
            entries,
            self.wakes.total(),
            self.spend.total(),
            self.config.buyer_cap_cents,
        )
        atomic_write(self._watermark, f"{size}\n")
        atomic_write(self.root / ".relay" / "brief-latest.txt", text + "\n")
        return text

    def _index(self) -> tuple[list[str], dict[tuple[str, str], Entry]]:
        order: list[str] = []
        latest: dict[tuple[str, str], Entry] = {}
        for entry in self.ledger.read():
            if not entry.idea_id.startswith("_") and entry.idea_id not in order:
                order.append(entry.idea_id)
            latest[(entry.idea_id, entry.bot)] = entry
        return order, latest

    def _select(self, index) -> tuple[str, str | None] | None:
        order, latest = index
        now = self.clock.now()
        if self._scout_due(latest, now):
            return ("scout", None)
        for idea_id in order:
            for bot in CHAIN[1:]:
                prev = previous_bot(bot)
                prev_entry = latest.get((idea_id, prev))
                if prev_entry is None or prev_entry.status != "DONE":
                    break
                current = latest.get((idea_id, bot))
                if current is None:
                    return (bot, idea_id)
                if current.status == "DONE":
                    continue
                if current.status == "WAIT" and self.approvals.is_approved(idea_id):
                    return (bot, idea_id)
                if current.status == "STOP" and self._read_cap(current):
                    if self.resume.ready(bot, idea_id, now):
                        return (bot, idea_id)
                    break
                break
        return None

    def _scout_due(self, latest, now) -> bool:
        last = latest.get(("_clock", "scout"))
        if last is not None and last.status == "DONE":
            then = parse_ts(last.ts)
            if then.isocalendar()[:2] == now.isocalendar()[:2]:
                return False
        if last is not None and last.status == "STOP" and self._read_cap(last):
            if not self.resume.ready("scout", "_clock", now):
                return False
        if now.weekday() != self.config.weekday:
            return False
        if (now.hour, now.minute) < (self.config.hour, self.config.minute):
            return False
        return True

    def _read_cap(self, entry: Entry) -> bool:
        return entry.note.startswith("read cap")

    def _run(self, bot_name: str, idea_id: str | None) -> Tick:
        bot = self.bots[bot_name]
        idea = self._load_idea(idea_id) if idea_id else None
        now = self.clock.now()
        self.wakes.record(bot_name, idea_id or "_clock", now)
        result: BotResult = bot.run(idea, self.ctx)
        ts = now.isoformat()
        primary_id = result.idea_id or idea_id or "_clock"
        rows: list[tuple[str, str, str]] = list(result.extra)
        rows.append((primary_id, result.status, result.note))
        for row_id, status, note in rows:
            entry = Entry(ts=ts, bot=bot_name, idea_id=row_id, status=status, note=note)
            self.ledger.append(entry)
            if status == "STOP" and note.startswith("read cap"):
                window = "day" if note.endswith("day") else "minute"
                self.resume.set(bot_name, row_id, self.budget.next_reset(window, now))
            elif status == "DONE":
                self.resume.clear(bot_name, row_id)
        publish_board(self.root)
        brief = None
        if bot_name == "scout" and result.status == "DONE":
            brief = self.maybe_brief()
        return Tick(
            bot=bot_name,
            idea_id=primary_id,
            status=result.status,
            note=result.note,
            brief=brief,
        )

    def _load_idea(self, idea_id: str) -> Idea:
        path = self.root / "ideas" / f"{idea_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return Idea.from_dict(data)
