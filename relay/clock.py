"""Clocks. The scheduler uses local time. The demo uses a fixed Monday."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class Clock:
    def now(self) -> datetime:
        raise NotImplementedError

    def advance(self, **kwargs: int) -> datetime:
        raise NotImplementedError


class SystemClock(Clock):
    """Local time. Monday 9am means 9am on this machine."""

    def now(self) -> datetime:
        return datetime.now().astimezone()

    def advance(self, **kwargs: int) -> datetime:
        raise RuntimeError("the system clock does not advance")


class FrozenClock(Clock):
    def __init__(self, when: datetime):
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        self._now = when

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: int) -> datetime:
        self._now = self._now + timedelta(**kwargs)
        return self._now
