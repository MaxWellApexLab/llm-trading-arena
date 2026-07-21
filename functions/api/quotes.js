// GET /api/quotes?s=BTC-USD,ETH-USD,AAPL
// Free, no-key quotes: crypto spot via Coinbase, stocks (delayed) via Yahoo.
// Edge-cached 90s via Cache API. Educational purposes only. Not investment advice.

const MAX_SYMBOLS = 40;
const CACHE_TTL_SECONDS = 90;
const UA = "Mozilla/5.0 (compatible; llm-trading-arena; +https://github.com/MaxWellApexLab/llm-trading-arena)";

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "public, max-age=60",
    "Content-Type": "application/json",
  };
}

function jsonResponse(body, status, extraHeaders) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders(), ...(extraHeaders || {}) },
  });
}

function parseSymbols(raw) {
  const symbols = (raw || "")
    .split(",")
    .map(s => s.trim().toUpperCase())
    .filter(s => /^[A-Z0-9.\-]{1,15}$/.test(s));
  return Array.from(new Set(symbols)).sort();
}

async function fetchOne(sym) {
  try {
    if (sym.endsWith("-USD")) {
      // crypto spot, real-time
      const res = await fetch(`https://api.coinbase.com/v2/prices/${sym}/spot`, { headers: { "User-Agent": UA } });
      if (!res.ok) return null;
      const j = await res.json();
      const px = Number(j?.data?.amount);
      return Number.isFinite(px) ? px : null;
    }
    // stock, ~15min delayed
    const res = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?interval=1d&range=1d`,
      { headers: { "User-Agent": UA } }
    );
    if (!res.ok) return null;
    const j = await res.json();
    const px = Number(j?.chart?.result?.[0]?.meta?.regularMarketPrice);
    return Number.isFinite(px) ? px : null;
  } catch {
    return null;
  }
}

export async function onRequestGet(context) {
  const { request } = context;
  const url = new URL(request.url);
  const symbols = parseSymbols(url.searchParams.get("s"));

  if (!symbols.length) {
    return jsonResponse({ error: "missing symbols, e.g. ?s=BTC-USD,AAPL" }, 400);
  }
  if (symbols.length > MAX_SYMBOLS) {
    return jsonResponse({ error: `too many symbols (max ${MAX_SYMBOLS})` }, 400);
  }

  const normalizedKey = symbols.join(",");
  const cacheKeyUrl = new URL(request.url);
  cacheKeyUrl.search = `?s=${normalizedKey}`;
  const cacheKey = new Request(cacheKeyUrl.toString(), { method: "GET" });

  // Separate long-lived entry so we can serve stale data if upstreams are down.
  const staleKeyUrl = new URL(request.url);
  staleKeyUrl.search = `?s=${normalizedKey}&bucket=stale`;
  const staleKey = new Request(staleKeyUrl.toString(), { method: "GET" });

  const cache = caches.default;

  const cached = await cache.match(cacheKey);
  if (cached) {
    return cached;
  }

  const prices = await Promise.all(symbols.map(fetchOne));
  const quotes = {};
  symbols.forEach((sym, i) => {
    if (prices[i] !== null) quotes[sym] = prices[i];
  });

  if (!Object.keys(quotes).length) {
    const staleCached = await cache.match(staleKey);
    if (staleCached) {
      return staleCached;
    }
    return jsonResponse({ error: "quotes unavailable" }, 503);
  }

  const freshBody = { quotes, asof: new Date().toISOString(), stale: false };
  const freshResponse = jsonResponse(freshBody, 200, { "CDN-Cache-Control": `max-age=${CACHE_TTL_SECONDS}` });
  context.waitUntil(cache.put(cacheKey, freshResponse.clone()));

  // Fallback copy kept for a day in case the next fetch fails.
  const staleBody = { quotes, asof: freshBody.asof, stale: true };
  const staleResponse = jsonResponse(staleBody, 200, { "CDN-Cache-Control": "max-age=86400" });
  context.waitUntil(cache.put(staleKey, staleResponse));

  return freshResponse;
}

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: corsHeaders() });
}
