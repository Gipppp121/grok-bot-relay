"""relay.toml (or relay.json) loader.

The parser covers the subset this project writes: comments, dotted tables,
strings, integers, and bare words. Python 3.10 has no tomllib, and the
package stays on the standard library.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from relay.models import CHAIN

DEFAULT_TOML = """\
# Launch relay config. Times are local time for the scheduler.
# X reads: 1000 a day and 30 a minute, split across the 7 bots.

[clock]
weekday = "monday"
hour = 9
minute = 0

[budget]
daily_reads = 1000
minute_reads = 30

[budget.scout]
daily = 300
minute = 9

[budget.pain_miner]
daily = 300
minute = 8

[budget.judge]
daily = 150
minute = 4

[budget.builder]
daily = 50
minute = 2

[budget.pitch]
daily = 150
minute = 5

[budget.buyer]
daily = 0
minute = 0

[budget.chief]
daily = 50
minute = 2

[buyer]
cap_cents = 4000
"""

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass
class Config:
    weekday: int = 0
    hour: int = 9
    minute: int = 0
    daily_reads: int = 1000
    minute_reads: int = 30
    bot_daily: dict[str, int] = field(default_factory=dict)
    bot_minute: dict[str, int] = field(default_factory=dict)
    buyer_cap_cents: int = 4000

    def __post_init__(self) -> None:
        if not self.bot_daily:
            self.bot_daily = _default_daily()
        if not self.bot_minute:
            self.bot_minute = _default_minute()


def _default_daily() -> dict[str, int]:
    return {
        "scout": 300,
        "pain_miner": 300,
        "judge": 150,
        "builder": 50,
        "pitch": 150,
        "buyer": 0,
        "chief": 50,
    }


def _default_minute() -> dict[str, int]:
    return {
        "scout": 9,
        "pain_miner": 8,
        "judge": 4,
        "builder": 2,
        "pitch": 5,
        "buyer": 0,
        "chief": 2,
    }


def strip_comment(line: str) -> str:
    in_string = False
    for index, char in enumerate(line):
        if char == '"':
            in_string = not in_string
        elif char == "#" and not in_string:
            return line[:index]
    return line


def parse_value(raw: str):
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        return raw[1:-1]
    if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
        return int(raw)
    if raw == "true":
        return True
    if raw == "false":
        return False
    return raw


def parse_simple_toml(text: str) -> dict:
    root: dict = {}
    section = root
    for raw in text.splitlines():
        line = strip_comment(raw).strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            keys = [part.strip() for part in line[1:-1].split(".")]
            section = root
            for key in keys:
                current = section.get(key)
                if not isinstance(current, dict):
                    current = {}
                    section[key] = current
                section = current
            continue
        if "=" not in line:
            raise ValueError(f"bad config line: {raw}")
        key, value = line.split("=", 1)
        section[key.strip()] = parse_value(value.strip())
    return root


def config_from_dict(data: dict) -> Config:
    clock = data.get("clock", {})
    budget = data.get("budget", {})
    buyer = data.get("buyer", {})
    weekday_raw = str(clock.get("weekday", "monday")).lower()
    if weekday_raw not in WEEKDAYS:
        raise ValueError(f"unknown weekday {weekday_raw}")
    bot_daily: dict[str, int] = {}
    bot_minute: dict[str, int] = {}
    for name in CHAIN:
        block = budget.get(name)
        if not isinstance(block, dict):
            raise ValueError(f"missing [budget.{name}]")
        bot_daily[name] = int(block["daily"])
        bot_minute[name] = int(block["minute"])
    daily_reads = int(budget.get("daily_reads", 1000))
    minute_reads = int(budget.get("minute_reads", 30))
    if sum(bot_daily.values()) != daily_reads:
        raise ValueError("daily bot slices must add up to daily_reads")
    if sum(bot_minute.values()) != minute_reads:
        raise ValueError("minute bot slices must add up to minute_reads")
    return Config(
        weekday=WEEKDAYS[weekday_raw],
        hour=int(clock.get("hour", 9)),
        minute=int(clock.get("minute", 0)),
        daily_reads=daily_reads,
        minute_reads=minute_reads,
        bot_daily=bot_daily,
        bot_minute=bot_minute,
        buyer_cap_cents=int(buyer.get("cap_cents", 4000)),
    )


def load_config(path: Path) -> Config:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(text)
    else:
        data = parse_simple_toml(text)
    return config_from_dict(data)


def find_config(root: Path) -> Path:
    toml_path = root / "relay.toml"
    json_path = root / "relay.json"
    if toml_path.exists():
        return toml_path
    if json_path.exists():
        return json_path
    raise FileNotFoundError(
        f"no relay.toml in {root}. Run: python -m relay init"
    )
