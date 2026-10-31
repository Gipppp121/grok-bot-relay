"""Small helpers. Standard library only."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(int(cents))
    return f"{sign}${cents // 100}.{cents % 100:02d}"


def slugify(title: str) -> str:
    parts: list[str] = []
    buf: list[str] = []
    for char in title.lower():
        if char.isalnum():
            buf.append(char)
        elif buf:
            parts.append("".join(buf))
            buf = []
    if buf:
        parts.append("".join(buf))
    return "-".join(parts)
