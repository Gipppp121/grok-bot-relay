"""Pluggable bot. Implement run(idea, ctx) and set name."""

from __future__ import annotations


class Bot:
    name = ""

    def run(self, idea, ctx):
        raise NotImplementedError
