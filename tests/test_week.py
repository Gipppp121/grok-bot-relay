"""The demo week: hourly 1176 wakes, relay 60."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from relay.demo import format_report, simulate_week
from relay.demo_data import DEMO_YES, IDEAS
from relay.models import HOURLY_WAKES_PER_WEEK
from relay.workspace import init_workspace, open_engine
from relay.clock import FrozenClock

REPO = Path(__file__).resolve().parents[1]
EXPECTED_BY_BOT = {
    "scout": 1,
    "pain_miner": 13,
    "judge": 13,
    "builder": 9,
    "pitch": 9,
    "buyer": 9,
    "chief": 6,
}


class WeekTests(unittest.TestCase):
    def test_wake_count(self) -> None:
        self.assertEqual(HOURLY_WAKES_PER_WEEK, 1176)
        self.assertEqual(len(IDEAS), 13)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ws"
            init_workspace(root)
            report = simulate_week(root)
            text = format_report(report)
            self.assertEqual(report.relay_wakes, 60)
            self.assertEqual(report.hourly, 1176)
            self.assertEqual(report.avoided, 1116)
            self.assertEqual(sum(report.by_bot.values()), 60)
            self.assertEqual(report.by_bot, EXPECTED_BY_BOT)
            self.assertEqual(report.spent_cents, 3900)
            self.assertEqual(report.cap_cents, 4000)
            self.assertEqual(
                report.bought,
                ["idea-01", "idea-02", "idea-04", "idea-06", "idea-07", "idea-09"],
            )
            self.assertEqual(report.killed, ["idea-03", "idea-05", "idea-08", "idea-11"])
            self.assertEqual(report.waiting, ["idea-12", "idea-13"])
            self.assertEqual(report.stopped, ["idea-10"])
            self.assertIn("hourly 1176 vs relay 60", text)
            self.assertTrue(text.strip().endswith("hourly 1176 vs relay 60"))
            for idea_id in report.bought:
                self.assertIn(idea_id, DEMO_YES)
                self.assertTrue((root / "plans" / f"{idea_id}.md").exists())
                plan = (root / "plans" / f"{idea_id}.md").read_text(encoding="utf-8")
                self.assertIn("dry run only", plan)
                self.assertIn("merge is off", plan)
                self.assertTrue((root / "drafts" / f"{idea_id}.md").exists())
            for idea_id in report.killed:
                self.assertFalse((root / "plans" / f"{idea_id}.md").exists())
                self.assertFalse((root / "drafts" / f"{idea_id}.md").exists())
            ledger_lines = [
                line
                for line in (root / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            # Scout writes one line per idea plus the clock line, in a single wake.
            self.assertEqual(len(ledger_lines), 73)
            self.assertNotEqual(len(ledger_lines), report.relay_wakes)
            board = (root / "board.md").read_text(encoding="utf-8")
            self.assertIn("| idea | stage | owner bot | waiting on me | last update |", board)
            self.assertIn("| idea-12 Paid ads blast | Buyer WAIT | Buyer | yes |", board)
            self.assertIn("| idea-03 AI for everything | Judge KILL | Judge | no |", board)
            # A later yes still cannot cross the cap.
            engine = open_engine(
                root,
                clock=FrozenClock(datetime(2026, 10, 26, 15, 0, tzinfo=timezone.utc)),
            )
            self.assertEqual(engine.wakes.total(), 60)
            self.assertIsNone(engine.tick())
            engine.approvals.grant("idea-13", engine.clock.now())
            over = engine.tick()
            assert over is not None
            self.assertEqual((over.bot, over.idea_id, over.status), ("buyer", "idea-13", "STOP"))
            self.assertTrue(over.note.startswith("spend cap"))
            self.assertEqual(engine.spend.total(), 3900)
            self.assertIsNone(engine.peek())

    def test_cli_demo_prints_the_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ws"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO)
            init = subprocess.run(
                [sys.executable, "-m", "relay", "init", "--root", str(root)],
                cwd=REPO,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            demo = subprocess.run(
                [sys.executable, "-m", "relay", "run", "--demo", "--root", str(root)],
                cwd=REPO,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(demo.returncode, 0, demo.stderr)
            self.assertIn("hourly 1176 vs relay 60", demo.stdout)
            missing = subprocess.run(
                [sys.executable, "-m", "relay", "run", "--demo", "--root", str(Path(tmp) / "empty")],
                cwd=REPO,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(missing.returncode, 2)


if __name__ == "__main__":
    unittest.main()
