"""Command line. python -m relay"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from relay import __version__
from relay.clock import SystemClock
from relay.demo import format_report, simulate_week
from relay.ledger import tail_lines
from relay.models import CHAIN, DISPLAY, HOURLY_WAKES_PER_WEEK
from relay.util import money
from relay.wall import serve
from relay.workspace import init_workspace, open_engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="relay",
        description="7 Grok Bots. 1 clock. Triggers on DONE.",
    )
    parser.add_argument("--version", action="version", version=f"relay {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--root",
        default=".",
        help="workspace directory (default: current directory)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", parents=[common], help="create a workspace")
    sub.add_parser("tick", parents=[common], help="run one scheduler step")

    run_parser = sub.add_parser("run", parents=[common], help="run until idle, or --demo")
    run_parser.add_argument(
        "--demo",
        action="store_true",
        help="simulate a fixed Monday week and print the wake comparison",
    )

    sub.add_parser("board", parents=[common], help="print the launch board")
    sub.add_parser("stats", parents=[common], help="print wakes, reads, and spend")

    approve_parser = sub.add_parser(
        "approve",
        parents=[common],
        help="record a human yes for one idea",
    )
    approve_parser.add_argument("idea_id")

    ledger_parser = sub.add_parser("ledger", parents=[common], help="ledger tools")
    ledger_sub = ledger_parser.add_subparsers(dest="ledger_cmd", required=True)
    tail_parser = ledger_sub.add_parser(
        "tail",
        parents=[common],
        help="print recent ledger lines",
    )
    tail_parser.add_argument("-f", "--follow", action="store_true")
    tail_parser.add_argument("-n", type=int, default=10)

    wall_parser = sub.add_parser("wall", parents=[common], help="serve the terminal wall")
    wall_parser.add_argument("--host", default="127.0.0.1")
    wall_parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.cmd == "init":
            return cmd_init(root)
        if args.cmd == "tick":
            return cmd_tick(root)
        if args.cmd == "run":
            return cmd_run(root, demo=args.demo)
        if args.cmd == "board":
            return cmd_board(root)
        if args.cmd == "stats":
            return cmd_stats(root)
        if args.cmd == "approve":
            return cmd_approve(root, args.idea_id)
        if args.cmd == "ledger":
            return cmd_tail(root, args.n, args.follow)
        if args.cmd == "wall":
            serve(args.host, args.port)
            return 0
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        return 0
    print(f"unknown command {args.cmd}", file=sys.stderr)
    return 2


def cmd_init(root: Path) -> int:
    init_workspace(root)
    print(f"initialized {root}")
    return 0


def cmd_tick(root: Path) -> int:
    _require(root)
    engine = open_engine(root)
    tick = engine.tick()
    if tick is None:
        print("idle")
        return 0
    print(f"wake {tick.bot} {tick.idea_id} {tick.status} {tick.note}")
    if tick.brief:
        print(tick.brief)
    return 0


def cmd_run(root: Path, demo: bool) -> int:
    _require(root)
    if demo:
        report = simulate_week(root)
        sys.stdout.write(format_report(report))
        return 0
    engine = open_engine(root)
    clock = SystemClock()
    while True:
        tick = engine.tick()
        if tick is None:
            delay = _seconds_until_scout(clock.now(), engine.config)
            time.sleep(min(delay, 30))
            continue
        print(f"wake {tick.bot} {tick.idea_id} {tick.status} {tick.note}")
        if tick.brief:
            print(tick.brief)


def cmd_board(root: Path) -> int:
    _require(root)
    from relay.board import publish_board

    sys.stdout.write(publish_board(root))
    return 0


def cmd_stats(root: Path) -> int:
    _require(root)
    engine = open_engine(root)
    day = engine.budget.day_with_events() or engine.clock.now()
    day_reads, _minute = engine.budget.used_all(day)
    by_bot = engine.wakes.by_bot()
    lines = [
        f"hourly {HOURLY_WAKES_PER_WEEK} vs relay {engine.wakes.total()}",
        f"spent {money(engine.spend.total())} of {money(engine.config.buyer_cap_cents)}",
        f"reads on {day.date().isoformat()} {day_reads} / {engine.config.daily_reads}",
        "",
        "bot          wakes  day reads",
    ]
    for name in CHAIN:
        used, _minute_used = engine.budget.used(name, day)
        label = DISPLAY[name]
        lines.append(
            f"{label:<12} {by_bot.get(name, 0):<6} {used}/{engine.config.bot_daily[name]}"
        )
    print("\n".join(lines))
    return 0


def cmd_approve(root: Path, idea_id: str) -> int:
    _require(root)
    engine = open_engine(root)
    when = engine.clock.now()
    engine.approvals.grant(idea_id, when)
    print(f"approved {idea_id}")
    return 0


def cmd_tail(root: Path, count: int, follow: bool) -> int:
    _require(root)
    path = root / "ledger.jsonl"

    def write(line: str) -> None:
        print(line, flush=True)

    try:
        tail_lines(path, count, follow, write)
    except KeyboardInterrupt:
        return 0
    return 0


def _require(root: Path) -> None:
    if not (root / "relay.toml").exists() and not (root / "relay.json").exists():
        raise FileNotFoundError(f"no relay.toml in {root}. Run: python -m relay init")


def _seconds_until_scout(now: datetime, config) -> float:
    """Sleep hint for the live loop. At least one second, at most a week."""
    target = now.replace(
        hour=config.hour,
        minute=config.minute,
        second=0,
        microsecond=0,
    )
    days_ahead = (config.weekday - now.weekday()) % 7
    target = target + timedelta(days=days_ahead)
    if target <= now:
        target = target + timedelta(days=7)
    return max((target - now).total_seconds(), 1.0)
