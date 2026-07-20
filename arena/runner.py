"""Daily entrypoint: settle yesterday's orders, get today's decisions, queue
new orders, mark to market, persist. Run once per trading day after close.

    python -m arena.runner --game arena
    python -m arena.runner --game arena --dry-run   # no API keys needed

Always run as a module (`python -m arena.runner`), not `python arena/runner.py`
directly — the latter breaks the `arena.*` / `core.*` package-relative imports.
"""

import argparse
import json
import re
from datetime import date
from pathlib import Path

import yaml

from arena import broker, market_data, prompts, universe
from core.adapters.registry import build_all

ROOT = Path(__file__).resolve().parent.parent
COMMENTARY_PATH = ROOT / "data" / "commentary.json"


def _load_persona(path: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    # strip the frontmatter block, keep the prompt body
    return re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)


def _parse_decision(raw: str) -> dict:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(json)?\s*|\s*```$", "", cleaned.strip())
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in model output")
    return json.loads(match.group(0))


def run(game_name: str, dry_run: bool = False) -> None:
    game_path = ROOT / "games" / f"{game_name}.yml"
    game = yaml.safe_load(game_path.read_text(encoding="utf-8"))
    tickers = universe.resolve(game["universe"])
    adapters = build_all(game["traders"], dry_run=dry_run)
    today = date.today().isoformat()

    ledger_path = ROOT / "data" / "ledger.json"
    if ledger_path.exists():
        ledger = broker.load_ledger(ledger_path)
    else:
        ledger = broker.init_ledger([t["id"] for t in game["traders"]], game["starting_cash"])

    md = market_data.fetch_ohlcv(tickers, game["lookback_days"])
    commentary_log = json.loads(COMMENTARY_PATH.read_text(encoding="utf-8")) if COMMENTARY_PATH.exists() else []

    for trader_cfg in game["traders"]:
        tid = trader_cfg["id"]
        trader = ledger[tid]

        # 1. settle yesterday's queued orders at today's open
        broker.settle_pending_orders(trader, md["open"], today, game["fee_pct"])

        # 2. ask the model for tomorrow's orders
        persona_text = _load_persona(trader_cfg["persona"])
        prompt = prompts.build_prompt(
            persona_text=persona_text,
            cash=trader["cash"],
            positions=trader["positions"],
            ohlcv=md["ohlcv"],
            top_movers=md["movers"],
            lookback_days=game["lookback_days"],
            max_position_pct=game["max_position_pct"],
            fee_pct=game["fee_pct"],
        )

        try:
            raw = adapters[tid].complete(prompt, temperature=0.7)
            decision = _parse_decision(raw)
        except Exception as exc:  # noqa: BLE001 - a bad model response must never crash the run
            trader["rejected"].append({"date": today, "reason": f"unparseable response: {exc}", "raw": None})
            decision = {"orders": [], "commentary": "(no valid response today)"}

        # 3. validate & queue for tomorrow's open
        broker.validate_and_queue_orders(
            trader, decision, tickers, game["max_position_pct"], game["long_only"], today
        )

        # 4. mark to market at today's close
        nav = broker.mark_to_market(trader, md["close"], today)

        commentary_log.append(
            {
                "date": today,
                "trader": tid,
                "nav": nav,
                "commentary": decision.get("commentary", ""),
                "orders": decision.get("orders", []),
            }
        )
        print(f"[{today}] {tid}: NAV=${nav:,.2f}  {decision.get('commentary', '')!r}")

    broker.save_ledger(ledger, ledger_path)
    COMMENTARY_PATH.write_text(json.dumps(commentary_log, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="arena", help="game name, i.e. games/<name>.yml")
    parser.add_argument("--dry-run", action="store_true", help="use MockAdapter, no API keys needed")
    args = parser.parse_args()
    run(args.game, dry_run=args.dry_run)
