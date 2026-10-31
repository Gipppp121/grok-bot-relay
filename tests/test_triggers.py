"""A bot runs only after the previous bot wrote DONE."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from relay.ledger import Ledger
from relay.models import CHAIN, Entry
from tests.support import (
    MONDAY,
    MONDAY_EARLY,
    NEXT_MONDAY,
    SATURDAY,
    TUESDAY,
    engine_with,
    scripted_bots,
    workspace,
    write_idea,
)


def _stamp(root: Path, bot: str, idea_id: str, status: str, note: str = "seed") -> None:
    Ledger(root / "ledger.jsonl").append(
        Entry("2026-10-26T09:00:00+00:00", bot, idea_id, status, note)
    )


class TriggerTests(unittest.TestCase):
    def test_scout_is_the_only_clock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(Path(tmp))
            saturday = engine_with(root, SATURDAY)
            self.assertIsNone(saturday.peek())
            early = engine_with(root, MONDAY_EARLY)
            self.assertIsNone(early.peek())
            monday = engine_with(root, MONDAY)
            self.assertEqual(monday.peek(), ("scout", None))
            tick = monday.tick()
            self.assertIsNotNone(tick)
            assert tick is not None
            self.assertEqual(tick.bot, "scout")
            self.assertEqual(tick.status, "DONE")
            self.assertEqual(len(list((root / "ideas").glob("*.json"))), 13)
            # Same week, same morning: the clock does not fire again.
            nxt = monday.peek()
            self.assertIsNotNone(nxt)
            assert nxt is not None
            self.assertNotEqual(nxt[0], "scout")
            later = engine_with(root, NEXT_MONDAY)
            self.assertEqual(later.peek()[0], "scout")

    def test_next_bot_waits_for_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(Path(tmp))
            write_idea(root, "idea-01")
            write_idea(root, "idea-02")
            engine = engine_with(root, TUESDAY)
            self.assertIsNone(engine.peek())
            _stamp(root, "pain_miner", "idea-01", "DONE")
            self.assertIsNone(engine.peek())
            _stamp(root, "scout", "idea-02", "WIP", "not yet")
            self.assertIsNone(engine.peek())
            _stamp(root, "scout", "idea-02", "DONE", "ready")
            self.assertEqual(engine.peek(), ("pain_miner", "idea-02"))

    def test_chain_order_and_kill_stops_the_idea(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(Path(tmp))
            write_idea(root, "idea-01")
            write_idea(root, "idea-02")
            bots = scripted_bots()
            engine = engine_with(root, TUESDAY, bots=bots)
            _stamp(root, "scout", "idea-01", "DONE")
            _stamp(root, "scout", "idea-02", "DONE")
            seen = []
            for _ in range(12):
                tick = engine.tick()
                self.assertIsNotNone(tick)
                assert tick is not None
                seen.append((tick.bot, tick.idea_id))
            self.assertEqual(
                seen,
                [(bot, "idea-01") for bot in CHAIN[1:]]
                + [(bot, "idea-02") for bot in CHAIN[1:]],
            )

    def test_kill_does_not_wake_builder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(Path(tmp))
            write_idea(
                root,
                "idea-03",
                scores={
                    "pain_sharp": 1,
                    "buyer_reachable": 1,
                    "build_small": 1,
                    "channel_fit": 1,
                },
            )
            engine = engine_with(root, TUESDAY)
            _stamp(root, "scout", "idea-03", "DONE")
            _stamp(root, "pain_miner", "idea-03", "DONE")
            tick = engine.tick()
            assert tick is not None
            self.assertEqual(tick.bot, "judge")
            self.assertEqual(tick.status, "KILL")
            self.assertIsNone(engine.peek())
            bots = [entry.bot for entry in engine.ledger.read()]
            self.assertNotIn("builder", bots)

    def test_wip_does_not_advance_or_spin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(Path(tmp))
            write_idea(root, "idea-01")
            engine = engine_with(root, TUESDAY)
            _stamp(root, "scout", "idea-01", "DONE")
            _stamp(root, "pain_miner", "idea-01", "WIP", "partial")
            self.assertIsNone(engine.tick())
            self.assertIsNone(engine.tick())
            self.assertEqual(engine.wakes.total(), 0)


if __name__ == "__main__":
    unittest.main()
