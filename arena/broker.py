"""Virtual broker: order validation, next-open execution, fees, ledger I/O.

Ledger shape (data/ledger.json)::

    {
      "<trader_id>": {
        "cash": 100000.0,
        "positions": {"NVDA": 12.5},
        "pending_orders": [{"action": "buy", "ticker": "NVDA", "weight_pct": 10}],
        "trades": [{"date": "...", "ticker": "...", "action": "...",
                     "shares": ..., "price": ..., "fee": ..., "status": "filled"}],
        "nav_history": [{"date": "...", "nav": 100000.0}],
        "rejected": [{"date": "...", "reason": "...", "raw": "..."}]
      }
    }

Every ledger mutation is a plain-dict operation so the whole history can be
replayed and audited from the JSON file alone — no hidden state.
"""

import json
from pathlib import Path

DEFAULT_LEDGER_PATH = Path(__file__).resolve().parent.parent / "data" / "ledger.json"


def init_ledger(trader_ids: list[str], starting_cash: float) -> dict:
    return {
        tid: {
            "cash": starting_cash,
            "positions": {},
            "pending_orders": [],
            "trades": [],
            "nav_history": [],
            "rejected": [],
        }
        for tid in trader_ids
    }


def load_ledger(path: Path = DEFAULT_LEDGER_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_ledger(ledger: dict, path: Path = DEFAULT_LEDGER_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8")


def _nav(trader: dict, prices: dict[str, float]) -> float:
    equity = sum(shares * prices[ticker] for ticker, shares in trader["positions"].items() if ticker in prices)
    return trader["cash"] + equity


def settle_pending_orders(trader: dict, open_prices: dict[str, float], date: str, fee_pct: float) -> None:
    """Fill yesterday's queued orders at today's open. Mutates `trader` in place.

    In leverage games a buy may exceed cash (cash goes negative = margin loan)
    with no buying-power cap; the only consequence is liquidation at zero equity.
    """
    orders, trader["pending_orders"] = trader["pending_orders"], []
    for order in orders:
        ticker = order["ticker"]
        price = open_prices.get(ticker)
        if price is None or price <= 0:
            trader["rejected"].append({"date": date, "reason": f"no open price for {ticker}", "raw": order})
            continue

        nav = _nav(trader, open_prices)
        if order["action"] == "buy":
            # Fee-inclusive: target_value is the total cash outlay (shares +
            # fee), not shares-only-then-plus-fee — otherwise a 100% weight
            # order always rejects on "insufficient cash" by exactly the fee.
            # No buying-power check: cash may go negative (margin loan), size
            # is whatever the model asked for. Zero equity = reset, that's all.
            target_value = nav * (order["weight_pct"] / 100.0)
            cost = target_value
            shares = target_value / (price * (1 + fee_pct))
            fee = target_value - shares * price
            trader["cash"] -= cost
            trader["positions"][ticker] = trader["positions"].get(ticker, 0.0) + shares
            trader["trades"].append(
                {"date": date, "ticker": ticker, "action": "buy", "shares": shares,
                 "price": price, "fee": fee, "status": "filled"}
            )
        elif order["action"] == "sell":
            held = trader["positions"].get(ticker, 0.0)
            if held <= 0:
                trader["rejected"].append({"date": date, "reason": f"no position in {ticker} to sell", "raw": order})
                continue
            sell_fraction = min(order["weight_pct"] / 100.0 * nav / (held * price), 1.0) if held * price > 0 else 0
            shares = held * sell_fraction if sell_fraction else held
            proceeds = shares * price
            fee = proceeds * fee_pct
            trader["cash"] += proceeds - fee
            remaining = held - shares
            if remaining <= 1e-9:
                trader["positions"].pop(ticker, None)
            else:
                trader["positions"][ticker] = remaining
            trader["trades"].append(
                {"date": date, "ticker": ticker, "action": "sell", "shares": shares,
                 "price": price, "fee": fee, "status": "filled"}
            )
        else:
            trader["rejected"].append({"date": date, "reason": f"unknown action {order['action']!r}", "raw": order})


def validate_and_queue_orders(
    trader: dict,
    decision: dict,
    universe: list[str],
    max_position_pct: float,
    long_only: bool,
    date: str,
    max_leverage: float = 1.0,
) -> None:
    """Validate a parsed model decision and queue legal orders for next-open
    execution. Illegal orders are dropped and logged; a bad order does not
    invalidate the rest of the batch.
    """
    orders = decision.get("orders", [])
    if not isinstance(orders, list):
        trader["rejected"].append({"date": date, "reason": "orders is not a list", "raw": decision})
        return

    held = set(trader["positions"])
    for order in orders:
        try:
            ticker = order["ticker"]
            action = order["action"]
            weight_pct = float(order["weight_pct"])
        except (KeyError, TypeError, ValueError):
            trader["rejected"].append({"date": date, "reason": "malformed order", "raw": order})
            continue

        if ticker not in universe:
            trader["rejected"].append({"date": date, "reason": f"{ticker} not in universe", "raw": order})
            continue
        if action not in ("buy", "sell"):
            trader["rejected"].append({"date": date, "reason": f"unknown action {action!r}", "raw": order})
            continue
        if long_only and action == "sell" and ticker not in held:
            trader["rejected"].append({"date": date, "reason": f"cannot short {ticker} (long_only)", "raw": order})
            continue
        buy_cap = max_position_pct * 100 if max_leverage <= 1.0 else 10000  # leverage game: sanity bound only
        if action == "buy" and not (0 < weight_pct <= buy_cap):
            trader["rejected"].append(
                {"date": date, "reason": f"weight_pct {weight_pct} out of range (0, {buy_cap:g}]", "raw": order}
            )
            continue
        if action == "sell" and not (0 < weight_pct <= 100):
            trader["rejected"].append({"date": date, "reason": f"invalid sell weight_pct {weight_pct}", "raw": order})
            continue

        trader["pending_orders"].append({"action": action, "ticker": ticker, "weight_pct": weight_pct})


def mark_to_market(trader: dict, close_prices: dict[str, float], date: str, starting_cash: float = 100000.0) -> float:
    nav = _nav(trader, close_prices)
    if nav <= 0 and trader["positions"]:
        # Equity wiped out: liquidated, then instantly respawned with fresh
        # starting cash. The death is recorded (0-NAV point + trade entry +
        # liquidation counter) — getting REKT repeatedly is part of the show.
        trader["positions"] = {}
        trader["pending_orders"] = []
        trader["cash"] = starting_cash
        trader["liquidations"] = trader.get("liquidations", 0) + 1
        trader["trades"].append(
            {"date": date, "ticker": "*", "action": "liquidated", "shares": 0.0,
             "price": 0.0, "fee": 0.0, "status": "rekt"}
        )
        trader["nav_history"].append({"date": date, "nav": 0.0})
        nav = starting_cash
    trader["nav_history"].append({"date": date, "nav": nav})
    return nav
