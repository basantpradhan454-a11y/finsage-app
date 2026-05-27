"""
FinSage Data Fetcher
━━━━━━━━━━━━━━━━━━━
100% FREE data sources:
  • yfinance    — Yahoo Finance (stocks, ETFs, global exchanges)
  • CoinGecko   — Crypto & Meme coins (free public API)

Security features:
  • Input sanitization (regex validation)
  • Retry with exponential backoff
  • Request timeouts
  • In-memory TTL cache
  • Graceful error handling
"""

import time
import logging
import re
import hashlib

import yfinance as yf
import requests

from config import (
    MAX_RETRIES, REQUEST_TIMEOUT, BACKOFF_BASE,
    CACHE_TTL_SECONDS, coingecko_base, coingecko_headers
)

logger = logging.getLogger("finsage.fetcher")

# ── In-Memory Cache (TTL-based) ───────────────────────────────────────────────
_cache: dict = {}

def _cache_key(*args) -> str:
    return hashlib.md5("_".join(str(a) for a in args).encode()).hexdigest()

def _get_cached(key: str):
    if key in _cache:
        value, expires_at = _cache[key]
        if time.time() < expires_at:
            logger.debug(f"Cache HIT: {key}")
            return value
        del _cache[key]
    return None

def _set_cache(key: str, value):
    _cache[key] = (value, time.time() + CACHE_TTL_SECONDS)


# ── Input Sanitization ────────────────────────────────────────────────────────
def sanitize_ticker(ticker: str) -> str:
    """Only alphanumeric + dot, hyphen, slash, underscore. Max 20 chars."""
    cleaned = re.sub(r"[^\w.\-/]", "", ticker.strip().upper())
    if len(cleaned) > 20:
        raise ValueError("Ticker too long — possible injection attempt.")
    if not cleaned:
        raise ValueError("Invalid ticker symbol.")
    return cleaned

def sanitize_coin_id(coin_id: str) -> str:
    """CoinGecko IDs: lowercase alphanumeric + hyphens only."""
    cleaned = re.sub(r"[^a-z0-9\-]", "", coin_id.strip().lower())
    if len(cleaned) > 60:
        raise ValueError("Coin ID too long.")
    if not cleaned:
        raise ValueError("Invalid coin ID.")
    return cleaned


# ── Retry with Exponential Backoff ────────────────────────────────────────────
def _retry_request(fn, *args, **kwargs):
    """Retry fn() up to MAX_RETRIES times with exponential backoff."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            wait = BACKOFF_BASE * (2 ** attempt)
            logger.warning(f"Attempt {attempt+1}/{MAX_RETRIES} failed: {e}. Retrying in {wait:.0f}s…")
            time.sleep(wait)
    raise last_err


# ══════════════════════════════════════════════════════════════════════════════
# STOCK DATA — yfinance (100% FREE, No API Key)
# ══════════════════════════════════════════════════════════════════════════════
def fetch_stock_data(ticker: str) -> dict:
    """
    Fetch stock data via yfinance (Yahoo Finance).
    FREE — no API key needed.
    Supports: NSE (.NS), BSE (.BO), NASDAQ, NYSE, LSE (.L), F'furt (.DE), etc.
    """
    ticker = sanitize_ticker(ticker)
    cache_key = _cache_key("stock", ticker)
    cached = _get_cached(cache_key)
    if cached:
        return cached

    def _fetch():
        stock = yf.Ticker(ticker)
        info  = stock.info
        hist  = stock.history(period="5d")

        if not info or (not info.get("currentPrice") and not info.get("regularMarketPrice") and hist.empty):
            raise ValueError(
                f"No data found for '{ticker}'. "
                "Check the symbol — for NSE use .NS suffix (e.g. RELIANCE.NS), for BSE use .BO."
            )

        current_price = (
            info.get("currentPrice") or
            info.get("regularMarketPrice") or
            (float(hist["Close"].iloc[-1]) if not hist.empty else None)
        )
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        change_pct = ((current_price - prev_close) / prev_close * 100) if (current_price and prev_close) else None

        # 5-day realized volatility
        volatility_5d = None
        if len(hist) >= 2:
            daily_returns = hist["Close"].pct_change().dropna()
            volatility_5d = round(float(daily_returns.std() * 100), 2)

        return {
            "ticker":          ticker,
            "name":            info.get("longName") or info.get("shortName", ticker),
            "exchange":        info.get("exchange", "Unknown"),
            "sector":          info.get("sector", "N/A"),
            "industry":        info.get("industry", "N/A"),
            "currency":        info.get("currency", "USD"),
            "current_price":   round(current_price, 4) if current_price else None,
            "prev_close":      round(prev_close, 4) if prev_close else None,
            "change_pct":      round(change_pct, 2) if change_pct is not None else None,
            "volume":          info.get("volume") or info.get("regularMarketVolume"),
            "avg_volume":      info.get("averageVolume"),
            "market_cap":      info.get("marketCap"),
            "pe_ratio":        info.get("trailingPE"),
            "forward_pe":      info.get("forwardPE"),
            "pb_ratio":        info.get("priceToBook"),
            "eps":             info.get("trailingEps"),
            "revenue":         info.get("totalRevenue"),
            "profit_margin":   info.get("profitMargins"),
            "debt_to_equity":  info.get("debtToEquity"),
            "roe":             info.get("returnOnEquity"),
            "52w_high":        info.get("fiftyTwoWeekHigh"),
            "52w_low":         info.get("fiftyTwoWeekLow"),
            "beta":            info.get("beta"),
            "dividend_yield":  info.get("dividendYield"),
            "volatility_5d_pct": volatility_5d,
            "analyst_rating":  info.get("recommendationMean"),
            "analyst_key":     info.get("recommendationKey"),
            "target_price":    info.get("targetMeanPrice"),
            "hist_closes":     [float(x) for x in hist["Close"].tolist()[-5:]] if not hist.empty else [],
            "asset_type":      "stock",
            "data_source":     "yfinance (Yahoo Finance) — FREE",
        }

    result = _retry_request(_fetch)
    _set_cache(cache_key, result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# CRYPTO / MEME COIN DATA — CoinGecko (100% FREE, No API Key)
# ══════════════════════════════════════════════════════════════════════════════

# Ticker → CoinGecko ID map
SYMBOL_TO_ID = {
    # Major Crypto
    "BTC": "bitcoin",          "ETH": "ethereum",         "SOL": "solana",
    "BNB": "binancecoin",      "XRP": "ripple",            "ADA": "cardano",
    "AVAX": "avalanche-2",     "DOT": "polkadot",          "MATIC": "matic-network",
    "LINK": "chainlink",       "UNI": "uniswap",           "LTC": "litecoin",
    "ATOM": "cosmos",          "NEAR": "near",             "APT": "aptos",
    "OP": "optimism",          "ARB": "arbitrum",          "SUI": "sui",
    "TON": "the-open-network", "TRX": "tron",              "USDT": "tether",
    "USDC": "usd-coin",
    # Meme Coins
    "DOGE": "dogecoin",        "SHIB": "shiba-inu",        "PEPE": "pepe",
    "FLOKI": "floki",          "BONK": "bonk",             "WIF": "dogwifcoin",
    "TRUMP": "official-trump", "MEME": "memecoin",         "WOJAK": "wojak",
    "BABYDOGE": "baby-doge-coin",
}

def resolve_coin_id(symbol_or_id: str) -> str:
    """Map ticker symbol → CoinGecko coin ID."""
    # Strip /USD, /USDT suffixes
    symbol = symbol_or_id.upper().replace("/USD", "").replace("/USDT", "").strip()
    if symbol in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[symbol]
    # Try lowercase as direct CoinGecko ID (e.g. 'bitcoin')
    return sanitize_coin_id(symbol_or_id.lower().replace("/", "-"))


def fetch_crypto_data(symbol_or_id: str) -> dict:
    """
    Fetch crypto/meme coin data from CoinGecko.
    FREE — public API, no key required. (30 req/min limit)
    Optional: set COINGECKO_API_KEY for free demo key (higher limits).
    """
    coin_id   = resolve_coin_id(symbol_or_id)
    cache_key = _cache_key("crypto", coin_id)
    cached    = _get_cached(cache_key)
    if cached:
        return cached

    def _fetch():
        url = f"{coingecko_base()}/coins/{coin_id}"
        params = {
            "localization":    "false",
            "tickers":         "false",
            "market_data":     "true",
            "community_data":  "true",
            "developer_data":  "false",
            "sparkline":       "false",
        }
        resp = requests.get(
            url, params=params,
            headers=coingecko_headers(),  # Empty for free, or demo key header
            timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 429:
            raise Exception(
                "CoinGecko rate limit reached (30 req/min free tier). "
                "Wait 60 seconds and try again. Or get a FREE demo key at coingecko.com."
            )
        if resp.status_code == 404:
            raise ValueError(
                f"Coin '{coin_id}' not found on CoinGecko. "
                "Try the full name (e.g. 'dogecoin') or check https://coingecko.com"
            )
        resp.raise_for_status()
        return resp.json()

    raw  = _retry_request(_fetch)
    mkt  = raw.get("market_data", {})
    comm = raw.get("community_data", {})
    sent = float(raw.get("sentiment_votes_up_percentage") or 50)

    result = {
        "coin_id":               coin_id,
        "ticker":                raw.get("symbol", "").upper(),
        "name":                  raw.get("name", coin_id),
        "asset_type":            "crypto",
        "categories":            raw.get("categories", []),
        "current_price":         mkt.get("current_price", {}).get("usd"),
        "market_cap":            mkt.get("market_cap", {}).get("usd"),
        "market_cap_rank":       mkt.get("market_cap_rank"),
        "fully_diluted_val":     mkt.get("fully_diluted_valuation", {}).get("usd"),
        "total_volume":          mkt.get("total_volume", {}).get("usd"),
        "change_24h":            mkt.get("price_change_percentage_24h"),
        "change_7d":             mkt.get("price_change_percentage_7d"),
        "change_30d":            mkt.get("price_change_percentage_30d"),
        "ath":                   mkt.get("ath", {}).get("usd"),
        "ath_change_pct":        mkt.get("ath_change_percentage", {}).get("usd"),
        "atl":                   mkt.get("atl", {}).get("usd"),
        "circulating_supply":    mkt.get("circulating_supply"),
        "total_supply":          mkt.get("total_supply"),
        "max_supply":            mkt.get("max_supply"),
        "high_24h":              mkt.get("high_24h", {}).get("usd"),
        "low_24h":               mkt.get("low_24h", {}).get("usd"),
        "volatility_24h_pct":    abs(mkt.get("price_change_percentage_24h") or 0),
        # Community / Social
        "sentiment_up_pct":      sent,
        "sentiment_down_pct":    100 - sent,
        "twitter_followers":     comm.get("twitter_followers"),
        "reddit_subscribers":    comm.get("reddit_subscribers"),
        "reddit_active_48h":     comm.get("reddit_accounts_active_48h"),
        "description":           raw.get("description", {}).get("en", "")[:400],
        "genesis_date":          raw.get("genesis_date"),
        "last_updated":          raw.get("last_updated"),
        "data_source":           "CoinGecko API — FREE",
    }
    _set_cache(cache_key, result)
    return result


# ── Global Live Prices (for dashboard ticker bar) ─────────────────────────────
def fetch_live_prices() -> dict:
    """Fetch quick prices for top assets. Used for live ticker bar."""
    cache_key = _cache_key("live_prices")
    cached = _get_cached(cache_key)
    if cached:
        return cached

    def _fetch():
        ids = "bitcoin,ethereum,dogecoin,solana,shiba-inu,binancecoin"
        r = requests.get(
            f"{coingecko_base()}/simple/price",
            params={"ids": ids, "vs_currencies": "usd", "include_24hr_change": "true"},
            headers=coingecko_headers(),
            timeout=REQUEST_TIMEOUT
        )
        r.raise_for_status()
        return r.json()

    try:
        result = _retry_request(_fetch)
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        logger.warning(f"Live prices fetch failed: {e}")
        return {}
