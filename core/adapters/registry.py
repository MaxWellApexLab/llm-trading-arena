"""Reads games/*.yml `traders:` list and builds one Adapter instance per trader.

To add a new provider: add a branch here (or, for anything OpenAI-compatible,
just add a `games/*.yml` entry with kind: openai_compat — no code change needed).
"""

from .anthropic_adapter import AnthropicAdapter
from .mock_adapter import MockAdapter
from .openai_adapter import OpenAIAdapter
from .openai_compat_adapter import OpenAICompatAdapter

_BUILDERS = {
    "openai": lambda cfg: OpenAIAdapter(model_id=cfg["model_id"], display_name=cfg.get("display_name")),
    "anthropic": lambda cfg: AnthropicAdapter(model_id=cfg["model_id"], display_name=cfg.get("display_name")),
    "openai_compat": lambda cfg: OpenAICompatAdapter(
        model_id=cfg["model_id"],
        base_url=cfg["base_url"],
        api_key_env=cfg["api_key_env"],
        display_name=cfg.get("display_name"),
    ),
}


def build_adapter(trader_cfg: dict):
    kind = trader_cfg["kind"]
    if kind not in _BUILDERS:
        raise ValueError(f"unknown adapter kind: {kind!r} (known: {sorted(_BUILDERS)})")
    return _BUILDERS[kind](trader_cfg)


def build_all(traders_cfg: list[dict], dry_run: bool = False) -> dict[str, object]:
    """Returns {trader_id: Adapter}. With dry_run=True, every trader gets a
    MockAdapter instead — no API keys required, e.g. for persona PR testing.
    """
    if dry_run:
        return {t["id"]: MockAdapter(display_name=t.get("display_name", t["id"])) for t in traders_cfg}
    return {t["id"]: build_adapter(t) for t in traders_cfg}
