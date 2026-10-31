"""Shared fixtures for relay tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from relay.bots.base import Bot
from relay.clock import FrozenClock
from relay.config import Config
from relay.engine import Engine
from relay.models import CHAIN, BotResult, Idea
from relay.workspace import init_workspace, open_engine

UTC = timezone.utc
MONDAY = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)
MONDAY_EARLY = datetime(2026, 10, 26, 8, 59, tzinfo=UTC)
TUESDAY = datetime(2026, 10, 27, 10, 0, tzinfo=UTC)
SATURDAY = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
NEXT_MONDAY = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


def workspace(path: Path) -> Path:
    root = path / "ws"
    init_workspace(root)
    return root


def write_idea(
    root: Path,
    idea_id: str,
    price_cents: int = 100,
    scores: dict | None = None,
) -> Idea:
    idea = Idea(
        id=idea_id,
        title=idea_id,
        summary="a seeded idea",
        price_cents=price_cents,
        scores=scores
        or {
            "pain_sharp": 2,
            "buyer_reachable": 2,
            "build_small": 2,
            "channel_fit": 2,
        },
        pains=["one pain"],
        pitch="a draft line",
    )
    path = root / "ideas" / f"{idea_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(idea.to_dict()), encoding="utf-8")
    return idea


class ScriptBot(Bot):
    def __init__(self, name: str, result: BotResult | None = None):
        self.name = name
        self.result = result or BotResult("DONE", "ok")
        self.calls = 0

    def run(self, idea, ctx):
        self.calls += 1
        return self.result


def scripted_bots(result: BotResult | None = None) -> dict[str, ScriptBot]:
    return {name: ScriptBot(name, result) for name in CHAIN}


def engine_with(
    root: Path,
    when: datetime,
    bots=None,
    config: Config | None = None,
) -> Engine:
    clock = FrozenClock(when)
    if config is None:
        return open_engine(root, clock=clock, bots=bots)
    return Engine(root, config, clock=clock, bots=bots)
