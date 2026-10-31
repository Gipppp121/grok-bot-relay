"""OPTIONAL NETWORK ADAPTER.

The demo does not import this module. Builder writes a plan file and does
not call GitHub. merge() always fails: nothing in this package merges.
"""

from __future__ import annotations


class GitHubHook:
    """Host hook for GitHub. Plan fails closed. Merge stays off."""

    def __init__(self, client=None):
        self.client = client

    def plan(self, idea) -> dict:
        if self.client is None:
            raise RuntimeError(
                "GitHub hook is optional and has no client. "
                "The demo uses SeededRepo."
            )
        return self.client.plan(idea)

    def merge(self, pr: int) -> None:
        raise RuntimeError("merge is disabled")
