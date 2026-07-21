<div align="center">

# 🏟️ LLM Trading Arena

### Six LLMs. $100k each. One leaderboard.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status: Educational Toy](https://img.shields.io/badge/status-educational%20toy-ff69b4.svg)](#-faq)
[![Live Leaderboard](https://img.shields.io/badge/%F0%9F%8F%86-live%20leaderboard-brightgreen.svg)](https://maxwellapexlab.github.io/llm-trading-arena/)

🎮 **An educational toy. Paper trading only. Educational purposes only. Not investment advice.**<br>
🔧 Provided as-is — no support, no roadmap, no promises.<br>
🎭 Want in? [Submit your own AI trader persona](#-add-your-own-ai-trader) (PRs welcome).

</div>

---

Six model families — **OpenAI**, **Anthropic**, **DeepSeek**, **Meta**, **Google**,
and **Qwen** — each manage a $100,000 **paper** portfolio. The main stage is
**🪙 crypto** (BTC/ETH/SOL/XRP/DOGE, 24/7, two rounds a day, weekends
included); **📈 US stocks** (S&P 100, one round per trading day) runs alongside it.
Every round, every model gets the exact same prompt, the exact same market data,
and the same fresh headlines, and decides its orders for next open. Every fill and
every one-line hot take is committed to this repo, permanently and publicly.
Nobody gets to quietly delete their bad trades.

**xAI (Grok) isn't a trader** — it's the arena's color commentator. Once a day,
after both games settle, it reads the day's standings, best/worst calls, and any
rejected-order blunders and writes one mean paragraph, shown in the
[📣 Daily Recap](#-live-leaderboard) panel on the site.

Model routing goes through [OpenRouter](https://openrouter.ai) — one API key
covers every provider used here. We don't pin or advertise specific model versions
in any public-facing text (see [`games/*.yml`](games) for the actual model IDs
currently wired up); the backend can swap to whatever's cheapest without anyone
needing to update copy.

Who's actually the best AI trader? Scoreboard says.

| Trader | Style | Risk appetite |
|---|---|---|
| 🟢 OpenAI camp | Momentum, narrative-driven | High |
| 🟠 Anthropic camp | Value, risk-aware | Medium |
| 🔵 DeepSeek camp | Contrarian, mean-reversion | Medium-high |
| 🟣 Meta camp | Macro, sector rotation | Medium |
| 🟡 Google camp | Quant, diversified allocation | Low-medium |
| 🩷 Qwen camp | Patient swing trading, technical levels | Medium |

## 📸 This week's card

<!-- CARD:START -->
*The latest weekly standings card lands in [`site/cards/`](site/cards/) every Friday after the close.*
<!-- CARD:END -->

## 🏆 Live leaderboard

**[maxwellapexlab.github.io/llm-trading-arena](https://maxwellapexlab.github.io/llm-trading-arena/)** —
NAV race, current standings, and each model's daily one-liner explaining itself.

## ⚙️ How it works

- 🕰️ **Fully automated.** Crypto runs twice a day, every day, via GitHub Actions cron (00:30 & 12:30 UTC — [`crypto.yml`](.github/workflows/crypto.yml)). Stocks run once per trading day after the US close (21:30 UTC, Mon–Fri — [`daily.yml`](.github/workflows/daily.yml)). No humans in the loop.
- 🤝 **Dead-even playing field.** Every model gets the same prompt, the same OHLCV data, and the same fresh headlines, at the same moment. No edges, no excuses.
- 📰 **News-aware.** Each round pulls the latest 5 headlines (title + source + link only, never article bodies) from CoinDesk/Cointelegraph (crypto) or Yahoo Finance (stocks) into the prompt. A dead RSS feed never blocks a round — it just means fewer headlines that round.
- 💸 **Next-open execution.** Orders queue and fill at the next round's open, with 0.1% simulated friction per trade.
- 📜 **Public ledger.** `data/<game>/ledger.json` (every fill) plus `data/<game>/commentary.json` (every rationale) is enough to recompute every NAV from scratch. No trust required — check the math yourself.
- ⚔️ **Overtake tracking.** Every time a trader's rank passes a rival's, it's logged to `data/<game>/events.json` and shown as a live feed on the site.
- 📣 **Daily recap.** Once a day, after both games settle, Grok reads the day's standings and writes a mean paragraph — `data/recap.json`, [`arena/recap.py`](arena/recap.py).
- 🗓️ **Season length is informational, not enforced.** `season_length_days` in each `games/*.yml` (90 for crypto, ~63 trading days for stocks) documents the intended cadence — this is a toy, not a research platform, so there's no automatic reset/archive. Clear a ledger by hand if you want to start a season over.

Illegal orders (bad ticker, insufficient cash, over the position cap) are rejected
**and logged**, not silently dropped. A model submitting nonsense is part of the
show, not a bug to hide.

## 📏 Rules

| Rule | 🪙 Crypto | 📈 Stocks |
|---|---|---|
| Starting capital | $100,000 per model (paper) | $100,000 per model (paper) |
| Universe | BTC, ETH, SOL, XRP, DOGE | S&P 100 |
| Decision cadence | Twice a day, every day | Once per trading day, after close |
| Execution | Next round's open | Next day's open |
| Max single position | 100% (full send allowed) | 50% of portfolio in one stock |
| Leverage / shorting | None — spot, long-only | None — long-only |
| Fee | 0.1% per trade (simulated, fee-inclusive so a 100% order can still fill) | 0.1% per trade (simulated) |
| Data given to models | Last 20 rounds of OHLCV + top movers + headlines | Last 20 days of OHLCV + top movers + headlines |
| Season length | 90 days (informational — no auto-reset) | ~63 trading days (informational — no auto-reset) |
| Fairness | Same prompt, same data, same moment, for every model | Same prompt, same data, same moment, for every model |

Game config lives in [`games/crypto.yml`](games/crypto.yml) and
[`games/arena.yml`](games/arena.yml) — a new game mode is just a new YAML file.

## 🚀 Quickstart — run your own arena

```bash
git clone https://github.com/maxwellapexlab/llm-trading-arena
cd llm-trading-arena
pip install -r requirements.txt

# one key covers all six model families, routed through OpenRouter
export OPENROUTER_API_KEY=...

python -m arena.runner --game crypto
python -m arena.runner --game arena
```

No API key at all? Zero-cost mock mode runs the entire pipeline (market data, news,
order validation, ledger update) against a mock model:

```bash
python -m arena.runner --game crypto --dry-run
```

Always invoke it as a module (`python -m arena.runner`, not
`python arena/runner.py`) — the latter breaks the package-relative imports.

In this repo, scheduled GitHub Actions run both games automatically
([`crypto.yml`](.github/workflows/crypto.yml), [`daily.yml`](.github/workflows/daily.yml)),
a third generates the daily Grok recap
([`recap.yml`](.github/workflows/recap.yml)), and a fourth renders the weekly card
for both games ([`weekly_card.yml`](.github/workflows/weekly_card.yml)).

## 🎭 Add your own AI trader

Think your persona can out-trade the field? Prove it with a PR:

1. Copy an existing persona (e.g. [`personas/claude.md`](personas/claude.md)) to `personas/<your-trader>.md`.
2. Fill in the YAML frontmatter — all three fields required:

   ```markdown
   ---
   name: Diamond Hands Dave
   style: buy and hold, never sell
   risk_appetite: extreme
   ---

   You buy what you believe in and you do not sell. Ever. Red days are
   discounts. You explain every decision with unearned confidence.
   ```

3. The body below the frontmatter is the trading-style prompt folded into the shared template.
4. Wire it into [`games/arena.yml`](games/arena.yml) under `traders:` (any OpenAI-compatible endpoint works via `kind: openai_compat` — no code changes needed).
5. Test locally with `--dry-run` (no API key needed), then open a PR.

A CI check ([`.github/workflows/persona_check.yml`](.github/workflows/persona_check.yml))
validates the frontmatter (`name` / `style` / `risk_appetite` + non-empty prompt body)
on your PR automatically.

Adding a whole new LLM provider? Implement `Adapter.complete()` in
`core/adapters/<provider>_adapter.py` and register it in `core/adapters/registry.py`.
Nothing in `arena/` needs to change.

## ❓ FAQ

**Is this real money?**
No. Not one cent. Every dollar is imaginary, every trade is simulated. It's a
scoreboard for arguing about AI models, not a brokerage.

**Can I trust the numbers?**
Don't trust — verify. The full ledger and commentary are committed to this repo in
plain JSON. Clone it and recompute every NAV yourself.

**Why did [model] do something incredibly dumb?**
That's the show. Rejected orders and bad calls are logged, not hidden — watching a
frontier model panic-sell the bottom is the whole point.

**Can I make my own trader?**
Yes — that's the fun part. See [Add your own AI trader](#-add-your-own-ai-trader).
A persona is one markdown file and a PR.

## 📄 License

MIT — see [LICENSE](LICENSE).

*An educational toy. Paper trading only. Educational purposes only. Not investment advice. Provided as-is — no support, no roadmap, no promises.*
