"""One prompt template, shared by every model, every day — fairness by
construction: nobody gets a better-tuned prompt than anyone else.
"""

import json

TEMPLATE = """You are managing a ${cash_display} paper portfolio of {asset_label}.

{persona}

Current portfolio positions (ticker: shares): {positions_json}
Cash available: ${cash:,.2f}
Market data, last {lookback_days} rounds (ticker -> OHLCV rows, oldest first): {ohlcv_json}
Recent notable moves (ticker -> % change): {movers_json}

Rules: long-only, {position_rule}, \
orders execute {execution_desc}, {fee_pct:.2%} fee per trade.

{news_block}Decide your orders for this round. Respond in JSON only, no markdown fences, no prose outside the JSON:
{{"orders": [{{"action": "buy|sell", "ticker": "...", "weight_pct": N}}],
 "commentary": "<one punchy sentence explaining your thinking>"}}

If you want to make no changes, respond with an empty "orders" list.
"""


def build_prompt(
    *,
    persona_text: str,
    cash: float,
    positions: dict[str, float],
    ohlcv: dict[str, list],
    top_movers: dict[str, float],
    lookback_days: int,
    max_position_pct: float,
    fee_pct: float,
    asset_label: str = "US stocks (S&P 100 only)",
    execution_desc: str = "at tomorrow's open",
    news_headlines: list[dict] | None = None,
    max_leverage: float = 1.0,
) -> str:
    news_block = ""
    if news_headlines:
        lines = "\n".join(f'- "{h["title"]}" ({h["source"]})' for h in news_headlines)
        news_block = f"Recent headlines:\n{lines}\n\n"

    if max_leverage > 1.0:
        position_rule = (
            "leverage is allowed with no set cap — weight_pct may exceed 100 and buying beyond your cash "
            "is a margin loan; size positions as boldly or carefully as your style demands, but if your "
            "equity ever hits zero you are LIQUIDATED on the spot and reset to a fresh $100,000 (your "
            "liquidation count is public)"
        )
    else:
        position_rule = f"max {max_position_pct * 100:.0f}% of portfolio value in one position"

    return TEMPLATE.format(
        position_rule=position_rule,
        cash_display=f"{cash:,.0f}",
        asset_label=asset_label,
        persona=persona_text.strip(),
        positions_json=json.dumps({k: round(v, 4) for k, v in positions.items()}),
        cash=cash,
        lookback_days=lookback_days,
        ohlcv_json=json.dumps(ohlcv, separators=(",", ":")),
        movers_json=json.dumps({k: round(v, 2) for k, v in top_movers.items()}),
        max_position_pct=max_position_pct * 100,
        fee_pct=fee_pct,
        execution_desc=execution_desc,
        news_block=news_block,
    )
