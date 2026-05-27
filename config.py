"""
FinSage Configuration Module
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
100% FREE APIs — No paid keys required!
  • yfinance    → Stocks (Yahoo Finance) — completely free
  • CoinGecko   → Crypto/Meme coins — free public API

Optional upgrades (still free):
  • COINGECKO_API_KEY → CoinGecko Demo key (free signup) = higher rate limits
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()  # Load .env if present (local dev)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finsage.config")

# ── API Keys — ALL OPTIONAL (app works 100% without them) ────────────────────
COINGECKO_API_KEY: str | None = os.getenv("COINGECKO_API_KEY")  # Optional: free demo key
# NOTE: yfinance needs NO API key — it scrapes Yahoo Finance directly
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")  # Free: gemini-2.5-flash

# ── Performance Settings ──────────────────────────────────────────────────────
CACHE_TTL_SECONDS: int  = int(os.getenv("CACHE_TTL_SECONDS", "300"))   # 5 min cache
MAX_RETRIES: int        = int(os.getenv("MAX_RETRIES", "3"))            # 3 retry attempts
REQUEST_TIMEOUT: int    = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))  # 15s timeout
BACKOFF_BASE: float     = 1.0  # Exponential backoff: 1s → 2s → 4s

# ── CoinGecko Endpoints ───────────────────────────────────────────────────────
COINGECKO_FREE_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_DEMO_BASE = "https://api.coingecko.com/api/v3"   # Demo key uses same endpoint

def coingecko_base() -> str:
    return COINGECKO_FREE_BASE  # Always free tier

def coingecko_headers() -> dict:
    """Return auth header if demo key present, else empty (free public access)."""
    if COINGECKO_API_KEY:
        return {"x-cg-demo-api-key": COINGECKO_API_KEY}
    return {}  # No key = free public API (30 calls/min limit)

# ── Startup Info ──────────────────────────────────────────────────────────────
def print_api_status():
    logger.info("=" * 50)
    logger.info("FinSage API Status:")
    logger.info("  ✅ yfinance     → FREE (no key needed)")
    if COINGECKO_API_KEY:
        logger.info("  ✅ CoinGecko    → FREE Demo Key (higher limits)")
    else:
        logger.info("  ✅ CoinGecko    → FREE Public API (30 req/min)")
    if GEMINI_API_KEY:
        logger.info("  ✅ Gemini AI    → FREE (gemini-2.5-flash)")
    else:
        logger.info("  ⚠️  Gemini AI    → No key (set GEMINI_API_KEY for AI insights)")
    logger.info("=" * 50)

print_api_status()
