"""Returns a fixed-shape, always-legal decision instead of calling a real
API. Two jobs:

1. `--dry-run` smoke-tests the whole pipeline without burning a key.
2. Contributors can test a new persona's prompt renders sanely without
   needing any API key at all — lowers the bar for community PRs.

Not model intelligence, just deterministic plumbing: buy-and-hold the first
ticker in the universe, one line of flavor text.
"""

from .base import Adapter


class MockAdapter(Adapter):
    def __init__(self, display_name: str = "mock"):
        self.display_name = display_name

    def complete(self, prompt: str, *, temperature: float = 0.7) -> str:
        return (
            '{"orders": [{"action": "buy", "ticker": "AAPL", "weight_pct": 10}], '
            '"commentary": "(dry-run) buying a small starter position, no real model was called"}'
        )
