"""Launch board and the morning brief.

Chief owns this format. The engine republishes the file after every wake so
a WAIT row shows up even when Chief has not run for that idea.
"""

from __future__ import annotations

from pathlib import Path

from relay.ledger import Ledger
from relay.models import DISPLAY, Entry
from relay.util import atomic_write, money, parse_ts


HEADER = (
    "# Launch Board\n"
    "\n"
    "| idea | stage | owner bot | waiting on me | last update |\n"
    "| --- | --- | --- | --- | --- |\n"
)


def empty_board() -> str:
    return HEADER


def _title(root: Path, idea_id: str) -> str:
    path = root / "ideas" / f"{idea_id}.json"
    if not path.exists():
        return idea_id
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        title = str(data.get("title", "")).replace("|", " ").strip()
        return title or idea_id
    except (OSError, ValueError):
        return idea_id


def _stamp(ts: str) -> str:
    try:
        parsed = parse_ts(ts)
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts.replace("T", " ")[:19]


def render_board(root: Path, entries: list[Entry]) -> str:
    order: list[str] = []
    latest: dict[str, Entry] = {}
    for entry in entries:
        if entry.idea_id.startswith("_"):
            continue
        if entry.idea_id not in latest:
            order.append(entry.idea_id)
        latest[entry.idea_id] = entry
    lines = [HEADER.rstrip("\n")]
    for idea_id in order:
        entry = latest[idea_id]
        title = _title(root, idea_id)
        label = idea_id if title == idea_id else f"{idea_id} {title}"
        owner = DISPLAY.get(entry.bot, entry.bot)
        stage = f"{owner} {entry.status}"
        waiting = "yes" if entry.status == "WAIT" else "no"
        lines.append(
            f"| {label} | {stage} | {owner} | {waiting} | {_stamp(entry.ts)} |"
        )
    return "\n".join(lines) + "\n"


def publish_board(root: Path) -> str:
    entries = Ledger(root / "ledger.jsonl").read()
    text = render_board(root, entries)
    atomic_write(root / "board.md", text)
    return text


def render_brief(
    entries: list[Entry],
    wakes: int,
    spent_cents: int,
    cap_cents: int,
) -> str:
    killed: list[str] = []
    waiting: list[str] = []
    latest: dict[str, Entry] = {}
    for entry in entries:
        if entry.idea_id.startswith("_"):
            continue
        latest[entry.idea_id] = entry
    for idea_id, entry in latest.items():
        if entry.status == "KILL":
            killed.append(idea_id)
        elif entry.status == "WAIT":
            waiting.append(idea_id)
    waiting_text = ", ".join(waiting) if waiting else "none"
    killed_text = ", ".join(killed) if killed else "none"
    return "\n".join(
        [
            "morning brief",
            f"ledger lines {len(entries)}",
            f"wakes {wakes}",
            f"spent {money(spent_cents)} of {money(cap_cents)}",
            f"waiting on you: {waiting_text}",
            f"killed: {killed_text}",
        ]
    )
