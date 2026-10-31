"""Workspace state besides the ledger: approvals, spend, wakes, resume."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from relay.util import atomic_write, parse_ts


class Approvals:
    """Human yeses. Buyer reads this file. Buyer never writes it."""

    def __init__(self, path: Path):
        self.path = path
        self.yes: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        if not self.path.exists():
            self.yes = {}
            return
        data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        raw = data.get("yes", {})
        if isinstance(raw, list):
            raw = {item: "" for item in raw}
        self.yes = {str(key): str(value) for key, value in raw.items()}

    def save(self) -> None:
        atomic_write(self.path, json.dumps({"yes": self.yes}, indent=2) + "\n")

    def grant(self, idea_id: str, when: datetime) -> None:
        self.reload()
        self.yes[idea_id] = when.isoformat()
        self.save()

    def is_approved(self, idea_id: str) -> bool:
        return idea_id in self.yes


class Spend:
    """Buyer is the only writer. Amounts are integer cents."""

    def __init__(self, path: Path, cap_cents: int):
        self.path = path
        self.cap_cents = cap_cents
        self.items: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self.items = []
            return
        data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        self.items = list(data.get("items", []))

    def save(self) -> None:
        atomic_write(self.path, json.dumps({"items": self.items}, indent=2) + "\n")

    def total(self) -> int:
        return sum(int(item["cents"]) for item in self.items)

    def has(self, idea_id: str) -> bool:
        return any(item["idea_id"] == idea_id for item in self.items)

    def record(self, idea_id: str, cents: int, when: datetime) -> None:
        if cents <= 0:
            raise ValueError("spend must be positive")
        if self.has(idea_id):
            raise RuntimeError(f"already spent on {idea_id}")
        if self.total() + cents > self.cap_cents:
            raise RuntimeError("spend cap")
        self.items.append(
            {"idea_id": idea_id, "cents": int(cents), "ts": when.isoformat()}
        )
        self.save()


class Wakes:
    """One line per Bot.run call. This is the relay wake count."""

    def __init__(self, path: Path):
        self.path = path
        self.items: list[dict] = []
        if path.exists():
            for raw in path.read_text(encoding="utf-8").splitlines():
                if raw.strip():
                    self.items.append(json.loads(raw))

    def record(self, bot: str, idea_id: str, when: datetime) -> None:
        item = {"ts": when.isoformat(), "bot": bot, "idea_id": idea_id}
        self.items.append(item)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, separators=(",", ":")) + "\n")

    def total(self) -> int:
        return len(self.items)

    def by_bot(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            counts[item["bot"]] = counts.get(item["bot"], 0) + 1
        return counts


class ResumeBook:
    """When a read-cap STOP may run again. Spend-cap STOPs are not stored."""

    def __init__(self, path: Path):
        self.path = path
        self.items: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self.items = {}
            return
        data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        self.items = {str(k): str(v) for k, v in data.items()}

    def save(self) -> None:
        atomic_write(self.path, json.dumps(self.items, indent=2) + "\n")

    def key(self, bot: str, idea_id: str) -> str:
        return f"{bot}/{idea_id}"

    def set(self, bot: str, idea_id: str, when: datetime) -> None:
        self.items[self.key(bot, idea_id)] = when.isoformat()
        self.save()

    def clear(self, bot: str, idea_id: str) -> None:
        if self.key(bot, idea_id) in self.items:
            del self.items[self.key(bot, idea_id)]
            self.save()

    def ready(self, bot: str, idea_id: str, now: datetime) -> bool:
        raw = self.items.get(self.key(bot, idea_id))
        if raw is None:
            return True
        return now >= parse_ts(raw)
