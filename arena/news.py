"""RSS headline fetcher — titles + source + link only, never article bodies
(copyright line in the wind). Stdlib-only (urllib + xml.etree) so no new
dependency for something this small.

A dead/slow feed must never block a trading round: every network or parse
error is swallowed and logged to stderr, falling back to an empty list.
"""

import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = {
    "crypto_rss": [
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("Cointelegraph", "https://cointelegraph.com/rss"),
    ],
    "yahoo_finance": [
        ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ],
}

USER_AGENT = "Mozilla/5.0 (compatible; llm-trading-arena/1.0; +https://github.com/maxwellapexlab/llm-trading-arena)"
TIMEOUT_SECONDS = 8


def _fetch_one(source_name: str, url: str, limit: int) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    items = root.findall(".//item")[:limit]
    out = []
    for item in items:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title:
            out.append({"title": title, "source": source_name, "url": link})
    return out


def fetch_headlines(news_source: str, limit: int = 5) -> list[dict]:
    """Returns up to `limit` most-recent headlines across all feeds for
    `news_source` (see FEEDS). Never raises — a feed outage just means
    fewer (or zero) headlines this round.
    """
    feeds = FEEDS.get(news_source, [])
    collected: list[dict] = []
    for source_name, url in feeds:
        try:
            collected.extend(_fetch_one(source_name, url, limit))
        except Exception as exc:  # noqa: BLE001 - a dead feed must never block a round
            print(f"[news] {source_name} feed failed: {exc}", file=sys.stderr)
    return collected[:limit]


def write_news_json(path, headlines: list[dict]) -> None:
    import json

    fetched_at = datetime.now(timezone.utc).isoformat()
    payload = [{**h, "fetched_at": fetched_at} for h in headlines]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
