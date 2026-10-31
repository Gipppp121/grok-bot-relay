"""Append-only JSONL ledger.

Locking is for one writer process: a thread lock plus an advisory flock so
lines are not torn if two threads append, and a second process waits its turn.
"""

from __future__ import annotations

import fcntl
import json
import os
import threading
import time
from pathlib import Path

from relay.models import STATUSES, Entry


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self._thread_lock = threading.Lock()

    def append(self, entry: Entry) -> None:
        if entry.status not in STATUSES:
            raise ValueError(entry.status)
        line = json.dumps(entry.to_dict(), ensure_ascii=True, separators=(",", ":"))
        if "\n" in line:
            raise ValueError("ledger line contains a newline")
        payload = line + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._thread_lock:
            with self.path.open("a", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def read(self) -> list[Entry]:
        if not self.path.exists():
            return []
        with self._thread_lock:
            with self.path.open("r", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
                try:
                    text = handle.read()
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        entries: list[Entry] = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"bad ledger line {line_no}") from exc
            entries.append(
                Entry(
                    ts=str(data["ts"]),
                    bot=str(data["bot"]),
                    idea_id=str(data["idea_id"]),
                    status=str(data["status"]),
                    note=str(data["note"]),
                )
            )
        return entries

    def size(self) -> int:
        if not self.path.exists():
            return 0
        return self.path.stat().st_size


def tail_lines(path: Path, count: int, follow: bool, write) -> None:
    """Print the last `count` lines. With follow, keep printing new ones."""

    def snapshot() -> list[str]:
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
        return [line for line in text.splitlines() if line.strip()]

    lines = snapshot()
    for line in lines[-count:]:
        write(line)
    if not follow:
        return
    seen = len(lines)
    while True:
        try:
            current = snapshot()
        except OSError:
            time.sleep(0.2)
            continue
        if len(current) > seen:
            for line in current[seen:]:
                write(line)
            seen = len(current)
        time.sleep(0.2)
