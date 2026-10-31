"""Read budgets. At the cap the bot writes STOP and waits for the reset."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from relay.bots.base import Bot
from relay.budget import Budget
from relay.config import Config, DEFAULT_TOML, load_config
from relay.ledger import Ledger
from relay.models import CHAIN, BotResult, Entry
from tests.support import TUESDAY, engine_with, workspace, write_idea


def _json_config() -> dict:
    budget = {
        "daily_reads": 1000,
        "minute_reads": 30,
    }
    slices = {
        "scout": (300, 9),
        "pain_miner": (300, 8),
        "judge": (150, 4),
        "builder": (50, 2),
        "pitch": (150, 5),
        "buyer": (0, 0),
        "chief": (50, 2),
    }
    for name, (daily, minute) in slices.items():
        budget[name] = {"daily": daily, "minute": minute}
    return {
        "clock": {"weekday": "monday", "hour": 9, "minute": 0},
        "budget": budget,
        "buyer": {"cap_cents": 4000},
    }


def _slice_config(pain_daily: int, pain_minute: int) -> Config:
    daily = {name: 100 for name in CHAIN}
    minute = {name: 10 for name in CHAIN}
    daily["pain_miner"] = pain_daily
    minute["pain_miner"] = pain_minute
    # Keep the published totals consistent enough for a direct Config.
    # Engine does not re-check the sum. Budget uses the per-bot and global caps.
    return Config(
        weekday=0,
        hour=9,
        minute=0,
        daily_reads=1000,
        minute_reads=30,
        bot_daily=daily,
        bot_minute=minute,
        buyer_cap_cents=4000,
    )


class ChargingPain(Bot):
    name = "pain_miner"

    def __init__(self, reads: int):
        self.reads = reads

    def run(self, idea, ctx):
        ok, reason = ctx.budget.try_charge(self.name, self.reads, ctx.clock.now())
        if not ok:
            return BotResult("STOP", f"read cap {reason}")
        return BotResult("DONE", "ok")


class Pass(Bot):
    def __init__(self, name: str):
        self.name = name

    def run(self, idea, ctx):
        return BotResult("DONE", "ok")


class BudgetTests(unittest.TestCase):
    def test_config_slices_match_the_caps(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "relay.toml").read_text(encoding="utf-8")
        self.assertEqual(text, DEFAULT_TOML)
        cfg = load_config(root / "relay.toml")
        self.assertEqual(sum(cfg.bot_daily.values()), 1000)
        self.assertEqual(sum(cfg.bot_minute.values()), 30)
        self.assertEqual(cfg.daily_reads, 1000)
        self.assertEqual(cfg.minute_reads, 30)
        self.assertEqual(cfg.buyer_cap_cents, 4000)
        self.assertEqual(cfg.weekday, 0)
        self.assertEqual((cfg.hour, cfg.minute), (9, 0))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "relay.json"
            path.write_text(json.dumps(_json_config()), encoding="utf-8")
            loaded = load_config(path)
            self.assertEqual(loaded.bot_daily, cfg.bot_daily)
            self.assertEqual(loaded.bot_minute, cfg.bot_minute)
            self.assertEqual(loaded.buyer_cap_cents, 4000)

    def test_minute_and_day_windows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "budget.json"
            cfg = _slice_config(pain_daily=4, pain_minute=2)
            budget = Budget(path, cfg)
            now = TUESDAY
            self.assertEqual(budget.try_charge("pain_miner", 2, now), (True, "ok"))
            ok, reason = budget.try_charge("pain_miner", 1, now)
            self.assertFalse(ok)
            self.assertEqual(reason, "minute")
            self.assertEqual(budget.used("pain_miner", now), (2, 2))
            later = now + timedelta(minutes=1)
            self.assertEqual(budget.try_charge("pain_miner", 2, later), (True, "ok"))
            blocked, why = budget.try_charge("pain_miner", 1, later + timedelta(minutes=1))
            self.assertFalse(blocked)
            self.assertEqual(why, "day")
            tomorrow = budget.next_reset("day", later)
            self.assertEqual(
                budget.try_charge("pain_miner", 2, tomorrow),
                (True, "ok"),
            )

    def test_engine_writes_stop_and_sleeps_until_reset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(Path(tmp))
            write_idea(root, "idea-01")
            write_idea(root, "idea-02")
            Ledger(root / "ledger.jsonl").append(
                Entry("2026-10-27T10:00:00+00:00", "scout", "idea-01", "DONE", "seed")
            )
            Ledger(root / "ledger.jsonl").append(
                Entry("2026-10-27T10:00:00+00:00", "scout", "idea-02", "DONE", "seed")
            )
            bots = {name: Pass(name) for name in CHAIN}
            bots["pain_miner"] = ChargingPain(reads=2)
            engine = engine_with(
                root,
                TUESDAY,
                bots=bots,
                config=_slice_config(pain_daily=100, pain_minute=2),
            )
            first = engine.tick()
            assert first is not None
            self.assertEqual((first.bot, first.idea_id, first.status), ("pain_miner", "idea-01", "DONE"))
            # Finish idea-01 so the next pain run is idea-02, still inside this minute.
            for _ in range(5):
                step = engine.tick()
                assert step is not None
                self.assertEqual(step.idea_id, "idea-01")
            stopped = engine.tick()
            assert stopped is not None
            self.assertEqual(stopped.bot, "pain_miner")
            self.assertEqual(stopped.idea_id, "idea-02")
            self.assertEqual(stopped.status, "STOP")
            self.assertEqual(stopped.note, "read cap minute")
            self.assertIsNone(engine.peek())
            engine.clock.advance(minutes=1)
            resumed = engine.tick()
            assert resumed is not None
            self.assertEqual((resumed.bot, resumed.idea_id, resumed.status), ("pain_miner", "idea-02", "DONE"))


if __name__ == "__main__":
    unittest.main()
