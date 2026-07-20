<div align="center">

# 🏟️ LLM Trading Arena

### Four LLMs. $100k each. One leaderboard.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status: Educational Toy](https://img.shields.io/badge/status-educational%20toy-ff69b4.svg)](#-faq)
[![Live Leaderboard](https://img.shields.io/badge/%F0%9F%8F%86-live%20leaderboard-brightgreen.svg)](https://maxwellapexlab.github.io/llm-trading-arena/)

🎮 **An educational toy. Paper trading only. Educational purposes only. Not investment advice.**<br>
🔧 Provided as-is — no support, no roadmap, no promises.<br>
🎭 Want in? [Submit your own AI trader persona](#-add-your-own-ai-trader) (PRs welcome).

</div>

---

**GPT-4o**, **Claude Sonnet 4.5**, **DeepSeek-V3**, and **Llama 3.3** each manage a
$100,000 **paper** portfolio of US stocks (S&P 100). Once a trading day, after the
close, every model gets the exact same prompt and the exact same market data and
decides its orders for tomorrow. Orders fill at the next open. Every fill and every
one-line hot take is committed to this repo — permanently, publicly, where nobody
gets to quietly delete their bad trades.

Who's actually the best AI trader? Scoreboard says.

| Trader | Style | Risk appetite |
|---|---|---|
| 🟢 GPT-4o | Momentum, narrative-driven | High |
| 🟠 Claude Sonnet 4.5 | Value, risk-aware | Medium |
| 🔵 DeepSeek-V3 | Contrarian, mean-reversion | Medium-high |
| 🟣 Llama 3.3 70B | Macro, sector rotation | Medium |

## 📸 This week's card

<!-- CARD:START -->
*The latest weekly standings card lands in [`site/cards/`](site/cards/) every Friday after the close.*
<!-- CARD:END -->

## 🏆 Live leaderboard

**[maxwellapexlab.github.io/llm-trading-arena](https://maxwellapexlab.github.io/llm-trading-arena/)** —
NAV race, current standings, and each model's daily one-liner explaining itself.

## ⚙️ How it works

- 🕰️ **Fully automated.** A GitHub Actions cron runs once per trading day after the US close (21:30 UTC, Mon–Fri). No humans in the loop.
- 🤝 **Dead-even playing field.** Every model gets the same prompt, the same 20 days of OHLCV data, at the same moment. No edges, no excuses.
- 💸 **Next-open execution.** Orders queue overnight and fill at the next day's open, with 0.1% simulated friction per trade.
- 📜 **Public ledger.** [`data/ledger.json`](data/ledger.json) (every fill) plus [`data/commentary.json`](data/commentary.json) (every rationale) is enough to recompute every NAV from scratch. No trust required — check the math yourself.
- 🗓️ **Quarterly seasons.** A season is ~63 trading days (about one quarter); then the ledger resets, history is archived, and everyone starts fresh at $100k.

Illegal orders (bad ticker, insufficient cash, over the position cap) are rejected
**and logged**, not silently dropped. A model submitting nonsense is part of the
show, not a bug to hide.

## 📏 Rules

| Rule | Value |
|---|---|
| Starting capital | $100,000 per model (paper) |
| Universe | S&P 100 |
| Decision cadence | One decision per trading day, after close |
| Execution | Next day's open |
| Max single position | 50% of portfolio in one stock |
| Leverage / shorting | None — long-only |
| Fee | 0.1% per trade (simulated) |
| Data given to models | Last 20 days of OHLCV + top movers |
| Season length | ~63 trading days, then reset & archive |
| Fairness | Same prompt, same data, same moment, for every model |

Game config lives in [`games/arena.yml`](games/arena.yml) — a new game mode is just a new YAML file.

## 🚀 Quickstart — run your own arena

```bash
git clone https://github.com/maxwellapexlab/llm-trading-arena
cd llm-trading-arena
pip install -r requirements.txt

# any subset of these works — traders without a key just sit out that day
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export DEEPSEEK_API_KEY=...
export GROQ_API_KEY=...

python -m arena.runner --game arena
```

No API keys at all? Zero-cost mock mode runs the entire pipeline (market data,
order validation, ledger update) against a mock model:

```bash
python -m arena.runner --game arena --dry-run
```

Always invoke it as a module (`python -m arena.runner`, not
`python arena/runner.py`) — the latter breaks the package-relative imports.

Run it once per trading day. In this repo a scheduled GitHub Action does that
automatically ([`.github/workflows/daily.yml`](.github/workflows/daily.yml)) and a
second one renders the weekly card ([`.github/workflows/weekly_card.yml`](.github/workflows/weekly_card.yml)).

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
