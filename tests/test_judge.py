"""Judge kills a total under 5 of 8."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from relay.bots.judge import CHECKS, KILL_UNDER, MAX_SCORE, judge_status, total_score
from relay.ledger import Ledger
from relay.models import Entry
from tests.support import TUESDAY, engine_with, workspace, write_idea


def _scores(*values: int) -> dict[str, int]:
    return dict(zip(CHECKS, values))


class JudgeTests(unittest.TestCase):
    def test_threshold(self) -> None:
        self.assertEqual(CHECKS, ("pain_sharp", "buyer_reachable", "build_small", "channel_fit"))
        self.assertEqual(MAX_SCORE, 8)
        self.assertEqual(KILL_UNDER, 5)
        self.assertEqual(total_score(_scores(2, 2, 2, 2)), 8)
        self.assertEqual(judge_status(_scores(2, 2, 1, 0)), "DONE")  # 5 lives
        self.assertEqual(judge_status(_scores(2, 2, 0, 0)), "KILL")  # 4 dies
        self.assertEqual(judge_status(_scores(0, 0, 0, 0)), "KILL")
        self.assertEqual(judge_status(_scores(1, 1, 1, 1)), "KILL")
        with self.assertRaises(ValueError):
            total_score(_scores(3, 0, 0, 0))
        with self.assertRaises(ValueError):
            total_score({"pain_sharp": 2})

    def test_engine_kill_blocks_the_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(Path(tmp))
            write_idea(root, "idea-03", scores=_scores(1, 1, 1, 1))
            engine = engine_with(root, TUESDAY)
            ledger = Ledger(root / "ledger.jsonl")
            ledger.append(Entry("2026-10-27T10:00:00+00:00", "scout", "idea-03", "DONE", "seed"))
            ledger.append(
                Entry("2026-10-27T10:00:00+00:00", "pain_miner", "idea-03", "DONE", "seed")
            )
            tick = engine.tick()
            assert tick is not None
            self.assertEqual(tick.status, "KILL")
            self.assertIn("score 4/8", tick.note)
            verdict = json.loads((root / "verdicts" / "idea-03.json").read_text(encoding="utf-8"))
            self.assertEqual(verdict["total"], 4)
            self.assertEqual(verdict["status"], "KILL")
            self.assertIsNone(engine.peek())


if __name__ == "__main__":
    unittest.main()
