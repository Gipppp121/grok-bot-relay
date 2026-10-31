"""Create a workspace and open an engine on it."""

from __future__ import annotations

from pathlib import Path

from relay.board import empty_board
from relay.clock import Clock
from relay.config import DEFAULT_TOML, find_config, load_config
from relay.util import atomic_write


def init_workspace(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    config_path = root / "relay.toml"
    if not config_path.exists() and not (root / "relay.json").exists():
        atomic_write(config_path, DEFAULT_TOML)
    ledger = root / "ledger.jsonl"
    if not ledger.exists():
        ledger.write_text("", encoding="utf-8")
    approvals = root / "approvals.json"
    if not approvals.exists():
        atomic_write(approvals, '{"yes": {}}\n')
    board = root / "board.md"
    if not board.exists():
        atomic_write(board, empty_board())
    for name in ("drafts", "plans", "ideas", "pains", "verdicts", ".relay"):
        (root / name).mkdir(parents=True, exist_ok=True)


def open_engine(root: Path, clock: Clock | None = None, bots=None, adapters=None):
    from relay.engine import Engine

    config = load_config(find_config(root))
    return Engine(root, config, clock=clock, bots=bots, adapters=adapters)
