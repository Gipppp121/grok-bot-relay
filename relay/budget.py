"""X read budget. 1000 a day and 30 a minute, split per bot.

A charge that would pass a slice is refused. The caller writes STOP and
sleeps until that window resets. Nothing is recorded for a refused charge.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from relay.config import Config
from relay.util import atomic_write, parse_ts


class Budget:
    def __init__(self, path: Path, config: Config):
        self.path = path
        self.config = config
        self.events: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self.events = []
            return
        data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        self.events = list(data.get("events", []))

    def save(self) -> None:
        atomic_write(
            self.path,
            json.dumps({"events": self.events}, indent=2) + "\n",
        )

    def try_charge(self, bot: str, reads: int, now: datetime) -> tuple[bool, str]:
        if reads < 0:
            raise ValueError("reads must be >= 0")
        if reads == 0:
            return True, "ok"
        window = self.block_window(bot, reads, now)
        if window != "ok":
            return False, window
        self.events.append({"bot": bot, "reads": int(reads), "ts": now.isoformat()})
        self.save()
        return True, "ok"

    def block_window(self, bot: str, reads: int, now: datetime) -> str:
        day_bot, minute_bot = self.used(bot, now)
        day_all, minute_all = self.used_all(now)
        if day_bot + reads > self.config.bot_daily[bot]:
            return "day"
        if day_all + reads > self.config.daily_reads:
            return "day"
        if minute_bot + reads > self.config.bot_minute[bot]:
            return "minute"
        if minute_all + reads > self.config.minute_reads:
            return "minute"
        return "ok"

    def used(self, bot: str, now: datetime) -> tuple[int, int]:
        return self._sum(now, bot=bot)

    def used_all(self, now: datetime) -> tuple[int, int]:
        return self._sum(now, bot=None)

    def _sum(self, now: datetime, bot: str | None) -> tuple[int, int]:
        day = 0
        minute = 0
        for event in self.events:
            if bot is not None and event["bot"] != bot:
                continue
            ts = _align(parse_ts(event["ts"]), now)
            if ts.date() != now.date():
                continue
            day += int(event["reads"])
            if ts.hour == now.hour and ts.minute == now.minute:
                minute += int(event["reads"])
        return day, minute

    def next_reset(self, window: str, now: datetime) -> datetime:
        if window == "day":
            tomorrow = now.date() + timedelta(days=1)
            return datetime(
                tomorrow.year,
                tomorrow.month,
                tomorrow.day,
                tzinfo=now.tzinfo,
            )
        base = now.replace(second=0, microsecond=0)
        return base + timedelta(minutes=1)

    def day_with_events(self) -> datetime | None:
        if not self.events:
            return None
        return max(parse_ts(event["ts"]) for event in self.events)


def _align(ts: datetime, now: datetime) -> datetime:
    if ts.tzinfo is None or now.tzinfo is None:
        return ts
    return ts.astimezone(now.tzinfo)
