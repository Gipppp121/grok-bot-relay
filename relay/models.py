"""Shared records for the relay.

A wake is one call to Bot.run. Scout's Monday clock is one wake even though
it appends one ledger line per idea. Do not count ledger lines as wakes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

# 7 bots * 24 hours * 7 days. The hourly baseline the relay replaces.
HOURLY_WAKES_PER_WEEK = 7 * 24 * 7

CHAIN: tuple[str, ...] = (
    "scout",
    "pain_miner",
    "judge",
    "builder",
    "pitch",
    "buyer",
    "chief",
)

STATUSES = frozenset({"WIP", "DONE", "STOP", "WAIT", "KILL"})

DISPLAY = {
    "scout": "Scout",
    "pain_miner": "Pain Miner",
    "judge": "Judge",
    "builder": "Builder",
    "pitch": "Pitch",
    "buyer": "Buyer",
    "chief": "Chief",
}


def previous_bot(name: str) -> str | None:
    index = CHAIN.index(name)
    if index == 0:
        return None
    return CHAIN[index - 1]


@dataclass
class Entry:
    ts: str
    bot: str
    idea_id: str
    status: str
    note: str

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"unknown status {self.status}")
        self.note = self.note.replace("\n", " ").strip()

    def to_dict(self) -> dict[str, str]:
        return {
            "ts": self.ts,
            "bot": self.bot,
            "idea_id": self.idea_id,
            "status": self.status,
            "note": self.note,
        }


@dataclass
class Idea:
    id: str
    title: str
    summary: str
    price_cents: int
    scores: dict[str, int]
    pains: list[str] = field(default_factory=list)
    pitch: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Idea":
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            summary=str(data["summary"]),
            price_cents=int(data["price_cents"]),
            scores={str(k): int(v) for k, v in dict(data["scores"]).items()},
            pains=[str(item) for item in data.get("pains", [])],
            pitch=str(data.get("pitch", "")),
        )


@dataclass
class BotResult:
    """Returned by Bot.run. The engine is the only ledger writer."""

    status: str
    note: str
    idea_id: str | None = None
    # Further lines written in the same wake: (idea_id, status, note).
    extra: list[tuple[str, str, str]] = field(default_factory=list)


@dataclass
class Tick:
    bot: str
    idea_id: str
    status: str
    note: str
    brief: str | None = None
