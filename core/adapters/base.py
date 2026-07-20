"""Base interface every model adapter must implement.

Adding a new LLM provider = add one file here that implements `Adapter`
and register it in `registry.py`. Nothing in arena/ needs to change.
"""

from abc import ABC, abstractmethod


class Adapter(ABC):
    """One adapter instance = one API call target (a specific model)."""

    #: human-readable id shown on the leaderboard, e.g. "gpt-4o"
    display_name: str = "unnamed-model"

    @abstractmethod
    def complete(self, prompt: str, *, temperature: float = 0.7) -> str:
        """Send `prompt`, return the raw text response (expected to be JSON)."""
        raise NotImplementedError
