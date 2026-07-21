// GET /api/quotes?s=AAPL,MSFT,NVDA
// Free, no-key delayed quotes proxied from Stooq, edge-cached 90s via Cache API.
// Educational purposes only. Not investment advice.

const MAX_SYMBOLS = 40;
const CACHE_TTL_SECONDS = 90;

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

// "BRK.B" -> "brk-b.us"; "AAPL" -> "aapl.us"
function toStooqTicker(sym) {
  return sym.toLowerCase().replace(/\./g, "-") + ".us";
}

function parseSymbols(raw) {
  const symbols = (raw || "")
    .split(",")
    .map(s => s.trim().toUpperCase())
    .filter(Boolean);
  return Array.from(new Set(symbols)).sort();
}

// Stooq CSV via f=sd2t2ohlcv: Symbol,Date,Time,Open,High,Low,Close,Volume
function parseStooqCsv(csv) {
  const lines = csv.trim().split("\n").map(l => l.trim()).filter(Boolean);
  const quotes = {};
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(",");
    const symbolCol = cols[0];
    const closeCol = cols[6];
    if (!symbolCol) continue;
    const symbol = symbolCol.replace(/\.US$/i, "").replace(/-/g, ".").toUpperCase();
    const close = Number(closeCol);
    if (closeCol && closeCol !== "N/D" && Number.isFinite(close)) {
      quotes[symbol] = close;
    }
  }
  return quotes;
}

export async function onRequestGet(context) {
  const { request } = context;
  const url = new URL(request.url);
  const symbols = parseSymbols(url.searchParams.get("s"));

  if (!symbols.length) {
    return jsonResponse({ error: "missing symbols, e.g. ?s=AAPL,MSFT" }, 400);
  }
  if (symbols.length > MAX_SYMBOLS) {
    return jsonResponse({ error: `too many symbols (max ${MAX_SYMBOLS})` }, 400);
  }

  const normalizedKey = symbols.join(",");
  const cacheKeyUrl = new URL(request.url);
  cacheKeyUrl.search = `?s=${normalizedKey}`;
  const cacheKey = new Request(cacheKeyUrl.toString(), { method: "GET" });

  // Separate long-lived entry so we still have something to serve stale if Stooq is down.
  const staleKeyUrl = new URL(request.url);
  staleKeyUrl.search = `?s=${normalizedKey}&bucket=stale`;
  const staleKey = new Request(staleKeyUrl.toString(), { method: "GET" });

  const cache = caches.default;

  const cached = await cache.match(cacheKey);
  if (cached) {
    return cached;
  }

  const stooqSymbols = symbols.map(toStooqTicker).join(",");
  const upstreamUrl = `https://stooq.com/q/l/?s=${encodeURIComponent(stooqSymbols)}&f=sd2t2ohlcv&h&e=csv`;

  try {
    const upstreamRes = await fetch(upstreamUrl);
    if (!upstreamRes.ok) throw new Error(`upstream ${upstreamRes.status}`);
    const csv = await upstreamRes.text();
    const quotes = parseStooqCsv(csv);

    const freshBody = { quotes, asof: new Date().toISOString(), stale: false };
    const freshResponse = jsonResponse(freshBody, 200, { "CDN-Cache-Control": `max-age=${CACHE_TTL_SECONDS}` });
    context.waitUntil(cache.put(cacheKey, freshResponse.clone()));

    // Fallback copy kept around for a day in case the next fetch fails.
    const staleBody = { quotes, asof: freshBody.asof, stale: true };
    const staleResponse = jsonResponse(staleBody, 200, { "CDN-Cache-Control": "max-age=86400" });
    context.waitUntil(cache.put(staleKey, staleResponse));

    return freshResponse;
  } catch (err) {
    const staleCached = await cache.match(staleKey);
    if (staleCached) {
      return staleCached;
    }
    return jsonResponse({ error: "quotes unavailable" }, 503);
  }
}

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: corsHeaders() });
}
