"""Adapters. The demo uses seeded ones. Network hooks are optional."""

from relay.adapters.seeded import SeededRepo, SeededSearch


class Adapters:
    def __init__(self, x, github):
        self.x = x
        self.github = github


def default_adapters() -> Adapters:
    return Adapters(x=SeededSearch(), github=SeededRepo())
