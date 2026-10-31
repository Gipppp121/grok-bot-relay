"""Offline adapters. Deterministic. No sockets."""

from __future__ import annotations

from relay.demo_data import IDEAS, READ_COST
from relay.models import Idea
from relay.util import slugify


class SeededSearch:
    """Stand-in for X search. Returns the fixed idea list."""

    scout_reads = READ_COST["scout"]

    def search(self, query: str, limit: int) -> list[Idea]:
        del query  # The demo ignores the query so the week stays fixed.
        if limit < 0:
            raise ValueError("limit")
        return list(IDEAS[:limit])


class SeededRepo:
    """Stand-in for GitHub. Plans a branch and a PR. Never merges."""

    def plan(self, idea: Idea) -> dict:
        slug = slugify(idea.title)
        return {
            "idea_id": idea.id,
            "branch": f"relay/{idea.id}-{slug}",
            "base": "main",
            "title": idea.title,
            "merge": False,
            "commits": [
                f"add {idea.title}",
                "record the ledger handoff",
            ],
            "checks": ["lint", "unit", "e2e", "types"],
        }

    def merge(self, pr: int) -> None:
        raise RuntimeError("merge is disabled")
