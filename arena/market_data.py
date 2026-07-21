"""Thin wrapper around yfinance — the only place that touches market data,
so swapping data providers later only touches this file.
"""

from math import floor, log10

import yfinance as yf


def _round_sig(value: float, sig: int = 4) -> float:
    """Round to `sig` significant figures — plain round(x, 2) flattens
    sub-cent prices (DOGE-USD, etc.) to 0.00.
    """
    if value == 0:
        return 0.0
    digits = sig - 1 - int(floor(log10(abs(value))))
    return round(value, max(digits, 0))


def fetch_ohlcv(tickers: list[str], lookback_days: int) -> "dict[str, object]":
    """Returns (ohlcv, latest_open, latest_close, movers_pct) for `tickers`.

    ohlcv: {ticker: [[date, open, high, low, close, volume], ...]} (oldest first)
    latest_open / latest_close: {ticker: float} for the most recent row
    movers_pct: {ticker: pct change vs previous close}, top 10 by abs magnitude
    """
    data = yf.download(
        tickers, period=f"{lookback_days + 5}d", group_by="ticker",
        auto_adjust=False, progress=False, threads=True,
    )

    ohlcv: dict[str, list] = {}
    latest_open: dict[str, float] = {}
    latest_close: dict[str, float] = {}
    movers_pct: dict[str, float] = {}

    for ticker in tickers:
        try:
            df = data[ticker].dropna().tail(lookback_days)
        except KeyError:
            continue
        if df.empty:
            continue

        rows = [
            [str(r.Index.date()), _round_sig(r.Open), _round_sig(r.High), _round_sig(r.Low), _round_sig(r.Close), int(r.Volume)]
            for r in df.itertuples(name="R")
        ]
        ohlcv[ticker] = rows
        latest_open[ticker] = float(df.iloc[-1]["Open"])
        latest_close[ticker] = float(df.iloc[-1]["Close"])
        if len(df) >= 2:
            prev_close = float(df.iloc[-2]["Close"])
            if prev_close:
                movers_pct[ticker] = (latest_close[ticker] / prev_close - 1) * 100

    top_movers = dict(sorted(movers_pct.items(), key=lambda kv: abs(kv[1]), reverse=True)[:10])
    return {"ohlcv": ohlcv, "open": latest_open, "close": latest_close, "movers": top_movers}
