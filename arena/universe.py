"""Ticker universes. Only `sp100` today; `sp500` can be added later without
touching runner.py or broker.py.
"""

# S&P 100 constituents (as of 2026-07). Not survivorship-bias-free across
# history, but the arena only ever trades the *current* list going forward.
SP100 = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN",
    "AVGO", "AXP", "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK-B", "C",
    "CAT", "CHTR", "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS",
    "CVX", "DHR", "DIS", "DOW", "DUK", "EMR", "F", "FDX", "GD", "GE",
    "GILD", "GM", "GOOG", "GOOGL", "GS", "HD", "HON", "IBM", "INTC", "JNJ",
    "JPM", "KHC", "KO", "LIN", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ",
    "MDT", "MET", "META", "MMM", "MO", "MRK", "MS", "MSFT", "NEE", "NFLX",
    "NKE", "NVDA", "ORCL", "PEP", "PFE", "PG", "PM", "PYPL", "QCOM", "RTX",
    "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO", "TMUS", "TSLA", "TXN",
    "UNH", "UNP", "UPS", "USB", "V", "VZ", "WFC", "WMT", "XOM",
]

# Top-5 by market cap, in yfinance's "<TICKER>-USD" format (same free,
# no-key data pipeline as the stock arena — see market_data.py). PEPE was
# considered and dropped: yfinance's ticker for it is the disambiguated
# "PEPE24478-USD", and its sub-cent price gets flattened to $0.00 by 2dp
# rounding — DOGE covers the "meme coin" slot well enough on its own.
CRYPTO5 = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD"]

UNIVERSES = {"sp100": SP100, "crypto5": CRYPTO5}


def resolve(name: str) -> list[str]:
    if name not in UNIVERSES:
        raise ValueError(f"unknown universe: {name!r} (known: {sorted(UNIVERSES)})")
    return list(UNIVERSES[name])
