"""One prompt template, shared by every model, every day — fairness by
construction: nobody gets a better-tuned prompt than anyone else.
"""

import json

TEMPLATE = """You are managing a ${cash_display} paper portfolio of US stocks (S&P 100 only).

{persona}

Current portfolio positions (ticker: shares): {positions_json}
Cash available: ${cash:,.2f}
Market data, last {lookback_days} trading days (ticker -> OHLCV rows, oldest first): {ohlcv_json}
Today's notable moves (ticker -> % change): {movers_json}

Rules: long-only, max {max_position_pct:.0f}% of portfolio value in one stock, \
orders execute at tomorrow's open, {fee_pct:.2%} fee per trade.

Decide your orders for tomorrow. Respond in JSON only, no markdown fences, no prose outside the JSON:
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
) -> str:
    return TEMPLATE.format(
        cash_display=f"{cash:,.0f}",
        persona=persona_text.strip(),
        positions_json=json.dumps({k: round(v, 4) for k, v in positions.items()}),
        cash=cash,
        lookback_days=lookback_days,
        ohlcv_json=json.dumps(ohlcv, separators=(",", ":")),
        movers_json=json.dumps({k: round(v, 2) for k, v in top_movers.items()}),
        max_position_pct=max_position_pct * 100,
        fee_pct=fee_pct,
    )
