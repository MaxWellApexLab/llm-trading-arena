"""Intraday mark-to-market sampler for the crypto game.

Every run appends one NAV point per trader to nav_history using live Coinbase
spot prices — no model calls, no orders, no fees. Cron'd every 30 minutes so
the NAV race chart shows an actual trend line instead of two dots a day.
Liquidation (equity <= 0 -> reset to fresh $100k) can trigger here too, so a
mid-day flash crash REKTs you in near-real time. Stdlib only.
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from arena import broker

ROOT = Path(__file__).resolve().parent.parent
GAME = "crypto"
STARTING_CASH = 100000.0  # keep in sync with games/crypto.yml
UA = "llm-trading-arena/1.0 (+https://github.com/MaxWellApexLab/llm-trading-arena)"


def spot(sym: str) -> float | None:
    try:
        req = urllib.request.Request(
            f"https://api.coinbase.com/v2/prices/{sym}/spot", headers={"User-Agent": UA}
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            px = float(json.load(res)["data"]["amount"])
            return px if px > 0 else None
    except Exception as exc:  # noqa: BLE001 - a dead feed must never crash the sampler
        print(f"[mark] {sym}: {exc}", file=sys.stderr)
        return None


def main() -> None:
    ledger_path = ROOT / "data" / GAME / "ledger.json"
    if not ledger_path.exists():
        print("[mark] no ledger yet, skipping")
        return
    ledger = broker.load_ledger(ledger_path)

    tickers = sorted({t for trader in ledger.values() for t in trader.get("positions", {})})
    prices = {}
    for t in tickers:
        px = spot(t)
        if px is not None:
            prices[t] = px
    if tickers and not prices:
        print("[mark] no prices available, skipping")
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    for trader in ledger.values():
        broker.mark_to_market(trader, prices, ts, starting_cash=STARTING_CASH)

    broker.save_ledger(ledger, ledger_path)
    site_copy = ROOT / "site" / "data" / GAME / "ledger.json"
    site_copy.parent.mkdir(parents=True, exist_ok=True)
    site_copy.write_text(ledger_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[mark] {len(ledger)} traders marked at {ts} ({len(prices)}/{len(tickers)} prices)")


if __name__ == "__main__":
    main()
