"""The seven bots, in chain order."""

from relay.bots.builder import Builder
from relay.bots.buyer import Buyer
from relay.bots.chief import Chief
from relay.bots.judge import Judge
from relay.bots.pain import PainMiner
from relay.bots.pitch import Pitch
from relay.bots.scout import Scout

__all__ = [
    "Builder",
    "Buyer",
    "Chief",
    "Judge",
    "PainMiner",
    "Pitch",
    "Scout",
    "default_bots",
]


def default_bots() -> dict:
    bots = (
        Scout(),
        PainMiner(),
        Judge(),
        Builder(),
        Pitch(),
        Buyer(),
        Chief(),
    )
    return {bot.name: bot for bot in bots}
