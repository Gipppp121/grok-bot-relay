"""Buyer is the only spender. $40 cap. A yes on every buy."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from relay.bots.buyer import decide
from relay.ledger import Ledger
from relay.models import CHAIN, Entry
from tests.support import TUESDAY, engine_with, workspace, write_idea


def _seed_through_pitch(root: Path, idea_id: str) -> None:
    ledger = Ledger(root / "ledger.jsonl")
    for bot in CHAIN[:5]:
        ledger.append(Entry("2026-10-27T10:00:00+00:00", bot, idea_id, "DONE", "seed"))


class BuyerTests(unittest.TestCase):
    def test_decide(self) -> None:
        self.assertEqual(decide(False, 100, 0, 4000), "WAIT")
        self.assertEqual(decide(True, 100, 0, 4000), "DONE")
        self.assertEqual(decide(True, 4000, 0, 4000), "DONE")
        self.assertEqual(decide(True, 100, 4000, 4000), "STOP")
        self.assertEqual(decide(True, 200, 3900, 4000), "STOP")
        self.assertEqual(decide(False, 5000, 0, 4000), "WAIT")

    def test_no_yes_means_no_spend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(Path(tmp))
            write_idea(root, "idea-12", price_cents=1000)
            _seed_through_pitch(root, "idea-12")
            engine = engine_with(root, TUESDAY)
            before = engine.wakes.total()
            tick = engine.tick()
            assert tick is not None
            self.assertEqual(tick.bot, "buyer")
            self.assertEqual(tick.status, "WAIT")
            self.assertEqual(engine.spend.total(), 0)
            for _ in range(5):
                self.assertIsNone(engine.tick())
            self.assertEqual(engine.wakes.total(), before + 1)
            bots = [entry.bot for entry in engine.ledger.read() if entry.idea_id == "idea-12"]
            self.assertNotIn("chief", bots)

    def test_yes_then_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(Path(tmp))
            write_idea(root, "idea-01", price_cents=3000)
            write_idea(root, "idea-02", price_cents=2000)
            _seed_through_pitch(root, "idea-01")
            _seed_through_pitch(root, "idea-02")
            engine = engine_with(root, TUESDAY)
            engine.approvals.grant("idea-01", engine.clock.now())
            engine.approvals.grant("idea-02", engine.clock.now())
            first = engine.tick()
            assert first is not None
            self.assertEqual((first.bot, first.status), ("buyer", "DONE"))
            self.assertEqual(engine.spend.total(), 3000)
            chief = engine.tick()
            assert chief is not None
            self.assertEqual(chief.bot, "chief")
            second = engine.tick()
            assert second is not None
            self.assertEqual((second.bot, second.idea_id, second.status), ("buyer", "idea-02", "STOP"))
            self.assertTrue(second.note.startswith("spend cap"))
            self.assertEqual(engine.spend.total(), 3000)
            self.assertIsNone(engine.peek())
            self.assertEqual([item["idea_id"] for item in engine.spend.items], ["idea-01"])


if __name__ == "__main__":
    unittest.main()
