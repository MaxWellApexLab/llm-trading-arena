"""Daily recap: Grok isn't a trader, it's the arena's trash-talking color
commentator. Once a day, after both games have settled, it gets fed a
summary of the day's action (standings, NAV moves, best/worst trades,
rejected-order blunders) across both games and writes one mean paragraph.

    python -m arena.recap

Requires OPENROUTER_API_KEY. Never crashes a CI run: any failure just
means no recap.json update this run, logged to stderr.
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from core.adapters.openai_compat_adapter import OpenAICompatAdapter
from core.adapters.registry import OPENROUTER_REFERER, OPENROUTER_TITLE

ROOT = Path(__file__).resolve().parent.parent
RECAP_PATH = ROOT / "data" / "recap.json"
GAMES = ["crypto", "arena"]
RECAP_MODEL_ID = "x-ai/grok-build-0.1"

SYSTEM_PROMPT = """You are Grok, the trash-talking color commentator for the LLM Trading \
Arena — a toy paper-trading scoreboard where six AI models manage $100k each. You are \
not a trader here, just the mouthiest guy in the booth. Write one short, mean, funny \
paragraph (3-5 sentences) recapping today's action across both games below. Roast the \
worst performer, hype the leader, and make fun of anyone who submitted a rejected/illegal \
order. Never mention specific model version numbers — refer to traders by their camp name \
only (e.g. "the DeepSeek camp"). Plain text only, no markdown, no JSON."""


def _today_entries(commentary: list[dict], today: str) -> list[dict]:
    return [c for c in commentary if c.get("date") == today]


def _summarize_game(game_name: str, today: str) -> str | None:
    data_dir = ROOT / "data" / game_name
    ledger_path = data_dir / "ledger.json"
    commentary_path = data_dir / "commentary.json"
    events_path = data_dir / "events.json"
    if not ledger_path.exists() or not commentary_path.exists():
        return None

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    commentary = json.loads(commentary_path.read_text(encoding="utf-8"))
    events = json.loads(events_path.read_text(encoding="utf-8")) if events_path.exists() else []

    todays = _today_entries(commentary, today)
    if not todays:
        return None

    standings = sorted(
        ((tid, t["nav_history"][-1]["nav"] if t.get("nav_history") else 100000) for tid, t in ledger.items()),
        key=lambda kv: kv[1],
        reverse=True,
    )
    standings_line = ", ".join(f"#{i+1} {tid} (${nav:,.0f})" for i, (tid, nav) in enumerate(standings))

    best = max(todays, key=lambda c: c["nav"], default=None)
    worst = min(todays, key=lambda c: c["nav"], default=None)

    rejected_today = [
        f"{tid}: {r['reason']}"
        for tid, t in ledger.items()
        for r in t.get("rejected", [])
        if r.get("date") == today
    ]

    todays_events = [e for e in events if e.get("ts", "").startswith(today)]
    events_line = "; ".join(f"{e['overtaker']} overtook {e['overtaken']}" for e in todays_events)

    lines = [f"[{game_name.upper()}] Standings: {standings_line}."]
    if best:
        lines.append(f"Best line: {best['trader']} — \"{best['commentary']}\"")
    if worst:
        lines.append(f"Worst line: {worst['trader']} — \"{worst['commentary']}\"")
    if rejected_today:
        lines.append(f"Rejected orders: {'; '.join(rejected_today[:5])}")
    if events_line:
        lines.append(f"Overtakes: {events_line}")
    return "\n".join(lines)


def build_recap(today: str | None = None) -> str | None:
    today = today or date.today().isoformat()
    summaries = [s for g in GAMES if (s := _summarize_game(g, today))]
    if not summaries:
        return None

    adapter = OpenAICompatAdapter(
        model_id=RECAP_MODEL_ID,
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        display_name="a current model from the xAI family",
        extra_headers={"HTTP-Referer": OPENROUTER_REFERER, "X-Title": OPENROUTER_TITLE},
    )
    prompt = SYSTEM_PROMPT + "\n\n" + "\n\n".join(summaries)
    return adapter.complete(prompt, temperature=0.9).strip()


def write_recap(summary: str, today: str | None = None) -> None:
    today = today or date.today().isoformat()
    payload = {"date": today, "summary": summary, "generated_at": datetime.now(timezone.utc).isoformat()}
    RECAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECAP_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    try:
        summary = build_recap()
    except Exception as exc:  # noqa: BLE001 - a recap failure must never fail CI
        print(f"[recap] failed: {exc}", file=sys.stderr)
        return
    if summary is None:
        print("[recap] no rounds settled today yet, skipping")
        return
    write_recap(summary)
    print(f"[recap] wrote {RECAP_PATH}")


if __name__ == "__main__":
    main()
