"""OPTIONAL NETWORK ADAPTER.

The demo does not import this module and does not open a socket.
A host that already has X search can pass a client. Until then, search
fails closed.
"""

from __future__ import annotations

from relay.demo_data import READ_COST


class XSearchHook:
    """Host hook for X search. Offline unless a client is supplied."""

    scout_reads = READ_COST["scout"]

    def __init__(self, client=None):
        self.client = client

    def search(self, query: str, limit: int) -> list:
        if self.client is None:
            raise RuntimeError(
                "X search hook is optional and has no client. "
                "The demo uses SeededSearch."
            )
        return self.client.search(query, limit)
