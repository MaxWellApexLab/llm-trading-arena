"""Renders this week's leaderboard + best/worst commentary line as a PNG
card, for posting to X / Reddit. No headless-browser dependency — pure
matplotlib so it runs cheaply in CI.
"""

import json
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
STARTING_CASH = 100000


def make_card(out_dir: Path = ROOT / "site" / "cards") -> Path:
    ledger = json.loads((ROOT / "data" / "ledger.json").read_text(encoding="utf-8"))
    commentary = json.loads((ROOT / "data" / "commentary.json").read_text(encoding="utf-8"))

    ranked = sorted(
        (
            (tid, t["nav_history"][-1]["nav"] if t["nav_history"] else STARTING_CASH)
            for tid, t in ledger.items()
        ),
        key=lambda kv: kv[1],
        reverse=True,
    )

    week_ago = [c for c in commentary if c["commentary"]]
    best = max(week_ago, key=lambda c: c["nav"], default=None)
    worst = min(week_ago, key=lambda c: c["nav"], default=None)

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    ax.axis("off")
    ax.set_title("LLM Trading Arena — Weekly Standings", fontsize=16, fontweight="bold", pad=20)

    y = 0.85
    for i, (tid, nav) in enumerate(ranked):
        pct = (nav / STARTING_CASH - 1) * 100
        ax.text(0.05, y, f"#{i+1}  {tid}", fontsize=13, fontweight="bold", transform=ax.transAxes)
        ax.text(0.65, y, f"${nav:,.0f}  ({pct:+.2f}%)", fontsize=13, transform=ax.transAxes)
        y -= 0.12

    y -= 0.05
    if best:
        ax.text(0.05, y, f"Best call: {best['trader']} — \"{best['commentary']}\"", fontsize=10,
                 style="italic", wrap=True, transform=ax.transAxes)
        y -= 0.1
    if worst:
        ax.text(0.05, y, f"Worst call: {worst['trader']} — \"{worst['commentary']}\"", fontsize=10,
                 style="italic", wrap=True, transform=ax.transAxes)

    out_dir.mkdir(parents=True, exist_ok=True)
    iso = date.today().isocalendar()
    out_path = out_dir / f"{iso.year}-{iso.week:02d}.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    print(make_card())
