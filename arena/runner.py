"""Round entrypoint: settle pending orders, get this round's decisions,
queue new orders, mark to market, persist. Run once per round.

    python -m arena.runner --game arena     # stocks, once per trading day
    python -m arena.runner --game crypto    # crypto, twice a day incl. weekends
    python -m arena.runner --game arena --dry-run   # no API keys needed

Always run as a module (`python -m arena.runner`), not `python arena/runner.py`
directly — the latter breaks the `arena.*` / `core.*` package-relative imports.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from arena import broker, market_data, news, prompts, universe
from core.adapters.registry import build_all

ROOT = Path(__file__).resolve().parent.parent
NEWS_HEADLINE_LIMIT = 5


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


def _nav_of(trader: dict, starting_cash: float) -> float:
    hist = trader.get("nav_history") or []
    return hist[-1]["nav"] if hist else starting_cash


def _current_ranking(ledger: dict, starting_cash: float) -> list[str]:
    """Trader ids ordered by NAV, richest first."""
    return sorted(ledger, key=lambda tid: _nav_of(ledger[tid], starting_cash), reverse=True)


def _detect_overtakes(prev_ranking: list[str], new_ranking: list[str], game_name: str, ts: str) -> list[dict]:
    """A trader "overtakes" another when its rank improves past someone who
    used to be ahead of it. One event per newly-passed rival.
    """
    prev_rank = {tid: i for i, tid in enumerate(prev_ranking)}
    new_rank = {tid: i for i, tid in enumerate(new_ranking)}
    events = []
    for tid, rank in new_rank.items():
        old_rank = prev_rank.get(tid)
        if old_rank is None or old_rank <= rank:
            continue  # new trader, or didn't improve
        for rival, rival_new_rank in new_rank.items():
            if rival == tid:
                continue
            rival_old_rank = prev_rank.get(rival)
            if rival_old_rank is None:
                continue
            # tid used to be behind rival, now sits ahead of it
            if rival_old_rank < old_rank and rival_new_rank > rank:
                events.append(
                    {"ts": ts, "game": game_name, "overtaker": tid, "overtaken": rival, "rank": rank + 1}
                )
    return events


def run(game_name: str, dry_run: bool = False) -> None:
    game_path = ROOT / "games" / f"{game_name}.yml"
    game = yaml.safe_load(game_path.read_text(encoding="utf-8"))
    tickers = universe.resolve(game["universe"])
    adapters = build_all(game["traders"], dry_run=dry_run, universe=tickers)
    starting_cash = game["starting_cash"]
    asset_label = game.get("asset_label", "US stocks (S&P 100 only)")
    execution_desc = game.get("execution_desc", "at tomorrow's open")

    data_dir = ROOT / "data" / game_name
    data_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = data_dir / "ledger.json"
    commentary_path = data_dir / "commentary.json"
    events_path = data_dir / "events.json"
    news_path = data_dir / "news.json"

    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    ts = now.isoformat()

    if ledger_path.exists():
        ledger = broker.load_ledger(ledger_path)
        # a trader added to the roster after the ledger was created (e.g. a
        # new camp joining an in-progress season) starts fresh at $100k
        new_ids = [t["id"] for t in game["traders"] if t["id"] not in ledger]
        if new_ids:
            ledger.update(broker.init_ledger(new_ids, starting_cash))
    else:
        ledger = broker.init_ledger([t["id"] for t in game["traders"]], starting_cash)

    prev_ranking = _current_ranking(ledger, starting_cash)

    md = market_data.fetch_ohlcv(tickers, game["lookback_days"])
    commentary_log = json.loads(commentary_path.read_text(encoding="utf-8")) if commentary_path.exists() else []

    headlines = news.fetch_headlines(game.get("news_source", ""), limit=NEWS_HEADLINE_LIMIT)
    news.write_news_json(news_path, headlines)

    for trader_cfg in game["traders"]:
        tid = trader_cfg["id"]
        trader = ledger[tid]
        lev = float(trader_cfg.get("max_leverage", game.get("max_leverage", 1.0)))

        # 1. settle previously queued orders at this round's open
        broker.settle_pending_orders(trader, md["open"], today, game["fee_pct"])

        # 2. ask the model for the next round's orders
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
            asset_label=asset_label,
            execution_desc=execution_desc,
            news_headlines=headlines,
            max_leverage=lev,
        )

        try:
            raw = adapters[tid].complete(prompt, temperature=0.7)
            decision = _parse_decision(raw)
        except Exception as exc:  # noqa: BLE001 - a bad model response must never crash the run
            trader["rejected"].append({"date": today, "reason": f"unparseable response: {exc}", "raw": None})
            decision = {"orders": [], "commentary": "(no valid response today)"}

        # 3. validate & queue for next-open execution
        broker.validate_and_queue_orders(
            trader, decision, tickers, game["max_position_pct"], game["long_only"], today,
            max_leverage=lev,
        )

        # 4. mark to market at this round's close
        nav = broker.mark_to_market(trader, md["close"], today, starting_cash=starting_cash)

        commentary_log.append(
            {
                "date": today,
                "trader": tid,
                "nav": nav,
                "commentary": decision.get("commentary", ""),
                "orders": decision.get("orders", []),
            }
        )
        print(f"[{today}] {game_name}/{tid}: NAV=${nav:,.2f}  {decision.get('commentary', '')!r}")

    new_ranking = _current_ranking(ledger, starting_cash)
    new_events = _detect_overtakes(prev_ranking, new_ranking, game_name, ts)
    if new_events:
        events_log = json.loads(events_path.read_text(encoding="utf-8")) if events_path.exists() else []
        events_log.extend(new_events)
        events_path.write_text(json.dumps(events_log, indent=2), encoding="utf-8")
        for e in new_events:
            print(f"[{today}] {game_name}: {e['overtaker']} overtook {e['overtaken']}, now rank #{e['rank']}")

    broker.save_ledger(ledger, ledger_path)
    commentary_path.write_text(json.dumps(commentary_log, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="arena", help="game name, i.e. games/<name>.yml")
    parser.add_argument("--dry-run", action="store_true", help="use MockAdapter, no API keys needed")
    args = parser.parse_args()
    run(args.game, dry_run=args.dry_run)
