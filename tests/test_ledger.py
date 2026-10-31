"""Ledger lines stay intact under threads, and the tail command reads them."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from relay.ledger import Ledger
from relay.models import Entry
from relay.workspace import init_workspace
from tests.support import TUESDAY, engine_with, workspace

REPO = Path(__file__).resolve().parents[1]


class LedgerTests(unittest.TestCase):
    def test_threaded_appends_stay_valid_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            ledger = Ledger(path)
            errors: list[BaseException] = []

            def worker(index: int) -> None:
                try:
                    ledger.append(
                        Entry(
                            "2026-10-26T09:00:00+00:00",
                            "scout",
                            f"idea-{index:02d}",
                            "DONE",
                            f"note {index}",
                        )
                    )
                except BaseException as exc:  # pragma: no cover - surfaced below
                    errors.append(exc)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(errors, [])
            entries = ledger.read()
            self.assertEqual(len(entries), 20)
            ids = sorted(entry.idea_id for entry in entries)
            self.assertEqual(ids, [f"idea-{i:02d}" for i in range(20)])
            for line in path.read_text(encoding="utf-8").splitlines():
                data = json.loads(line)
                self.assertEqual(
                    set(data),
                    {"ts", "bot", "idea_id", "status", "note"},
                )

    def test_tail_and_approve_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ws"
            init_workspace(root)
            ledger = Ledger(root / "ledger.jsonl")
            ledger.append(Entry("2026-10-26T09:00:00+00:00", "scout", "idea-01", "DONE", "one"))
            ledger.append(Entry("2026-10-26T09:01:00+00:00", "pain_miner", "idea-01", "DONE", "two"))
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO)
            tail = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "relay",
                    "ledger",
                    "tail",
                    "--root",
                    str(root),
                    "-n",
                    "1",
                ],
                cwd=REPO,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(tail.returncode, 0, tail.stderr)
            self.assertIn("pain_miner", tail.stdout)
            self.assertNotIn("scout", tail.stdout)
            approved = subprocess.run(
                [sys.executable, "-m", "relay", "approve", "idea-01", "--root", str(root)],
                cwd=REPO,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(approved.returncode, 0, approved.stderr)
            self.assertIn("idea-01", (root / "approvals.json").read_text(encoding="utf-8"))
            board = subprocess.run(
                [sys.executable, "-m", "relay", "board", "--root", str(root)],
                cwd=REPO,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(board.returncode, 0, board.stderr)
            self.assertIn("waiting on me", board.stdout)
            stats = subprocess.run(
                [sys.executable, "-m", "relay", "stats", "--root", str(root)],
                cwd=REPO,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(stats.returncode, 0, stats.stderr)
            self.assertIn("hourly 1176 vs relay 0", stats.stdout)

    def test_brief_is_quiet_until_the_ledger_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(Path(tmp))
            engine = engine_with(root, TUESDAY)
            self.assertIsNone(engine.maybe_brief())
            self.assertIsNone(engine.maybe_brief())
            Ledger(root / "ledger.jsonl").append(
                Entry("2026-10-27T10:00:00+00:00", "scout", "idea-01", "DONE", "seed")
            )
            text = engine.maybe_brief()
            self.assertIsNotNone(text)
            assert text is not None
            self.assertIn("morning brief", text)
            self.assertIsNone(engine.maybe_brief())


if __name__ == "__main__":
    unittest.main()
