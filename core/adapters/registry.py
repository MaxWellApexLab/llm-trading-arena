"""Reads games/*.yml `traders:` list and builds one Adapter instance per trader.

To add a new provider: add a branch here (or, for anything OpenAI-compatible,
just add a `games/*.yml` entry with kind: openai_compat — no code change needed).
"""

from .anthropic_adapter import AnthropicAdapter
from .mock_adapter import MockAdapter
from .openai_adapter import OpenAIAdapter
from .openai_compat_adapter import OpenAICompatAdapter

OPENROUTER_REFERER = "https://github.com/maxwellapexlab/llm-trading-arena"
OPENROUTER_TITLE = "LLM Trading Arena"

_BUILDERS = {
    "openai": lambda cfg: OpenAIAdapter(model_id=cfg["model_id"], display_name=cfg.get("display_name")),
    "anthropic": lambda cfg: AnthropicAdapter(model_id=cfg["model_id"], display_name=cfg.get("display_name")),
    "openai_compat": lambda cfg: OpenAICompatAdapter(
        model_id=cfg["model_id"],
        base_url=cfg["base_url"],
        api_key_env=cfg["api_key_env"],
        display_name=cfg.get("display_name"),
        # OpenRouter convention headers: surfaces this repo on OpenRouter's
        # public app rankings, at no cost — see F5c construction doc §1.4.
        extra_headers=(
            {"HTTP-Referer": OPENROUTER_REFERER, "X-Title": OPENROUTER_TITLE}
            if "openrouter.ai" in cfg["base_url"]
            else None
        ),
    ),
}


def build_adapter(trader_cfg: dict):
    kind = trader_cfg["kind"]
    if kind not in _BUILDERS:
        raise ValueError(f"unknown adapter kind: {kind!r} (known: {sorted(_BUILDERS)})")
    return _BUILDERS[kind](trader_cfg)


def build_all(traders_cfg: list[dict], dry_run: bool = False, universe: list[str] | None = None) -> dict[str, object]:
    """Returns {trader_id: Adapter}. With dry_run=True, every trader gets a
    MockAdapter instead — no API keys required, e.g. for persona PR testing.
    `universe` lets the mock pick a ticker that's actually legal for this
    game (a hardcoded "AAPL" doesn't exist in the crypto game's universe).
    """
    if dry_run:
        return {
            t["id"]: MockAdapter(display_name=t.get("display_name", t["id"]), universe=universe)
            for t in traders_cfg
        }
    return {t["id"]: build_adapter(t) for t in traders_cfg}
