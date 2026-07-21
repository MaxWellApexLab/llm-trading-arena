"""Returns a fixed-shape, always-legal decision instead of calling a real
API. Two jobs:

1. `--dry-run` smoke-tests the whole pipeline without burning a key.
2. Contributors can test a new persona's prompt renders sanely without
   needing any API key at all — lowers the bar for community PRs.

Not model intelligence, just deterministic plumbing: buy-and-hold a random
ticker from the game's own universe (not a hardcoded "AAPL" — that ticker
doesn't exist in the crypto game's universe, so every crypto dry-run order
used to get rejected and the settlement path never got exercised).
"""

import random

from .base import Adapter


class MockAdapter(Adapter):
    def __init__(self, display_name: str = "mock", universe: list[str] | None = None):
        self.display_name = display_name
        self.universe = universe or ["AAPL"]

    def complete(self, prompt: str, *, temperature: float = 0.7) -> str:
        ticker = random.choice(self.universe)
        return (
            '{"orders": [{"action": "buy", "ticker": "%s", "weight_pct": 10}], '
            '"commentary": "(dry-run) buying a small starter position, no real model was called"}' % ticker
        )
