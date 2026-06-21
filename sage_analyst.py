"""
SAGE Analyst — FinSage AI Chart Analyst
Real-time Analysis + TradingView Lightweight Charts + Voice Explanation
Uses GROW_API_KEY (Groq llama-3.3-70b) for AI brain
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import os
import re
import time
import requests
from ticker_resolver import resolve_ticker
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ══════════════════════════════════════════════════════
# 0. GROQ API
# ══════════════════════════════════════════════════════
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

def _groq_key():
    for name in ("GROW_API_KEY", "GROQ_API_KEY"):
        try:
            v = st.secrets.get(name, "")
            if v: return v
        except Exception: pass
        v = os.environ.get(name, "")
        if v: return v
    return ""

def _call_groq(messages, max_tokens=3000, temperature=0.5):
    k = _groq_key()
    if not k:
        return None
    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages,
                  "temperature": temperature, "max_tokens": max_tokens},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return None

# ══════════════════════════════════════════════════════
# 1. STOCK SYMBOL MAP
# ══════════════════════════════════════════════════════
SYMBOL_MAP = {
    # Indian stocks
    "reliance": ("NSE:RELIANCE", "RELIANCE.NS"),
    "tcs":      ("NSE:TCS",      "TCS.NS"),
    "infosys":  ("NSE:INFY",     "INFY.NS"),
    "infy":     ("NSE:INFY",     "INFY.NS"),
    "hdfc":     ("NSE:HDFCBANK", "HDFCBANK.NS"),
    "hdfc bank":("NSE:HDFCBANK", "HDFCBANK.NS"),
    "hdfcbank": ("NSE:HDFCBANK", "HDFCBANK.NS"),
    "sbi":      ("NSE:SBIN",     "SBIN.NS"),
    "adani":    ("NSE:ADANIENT", "ADANIENT.NS"),
    "adanient": ("NSE:ADANIENT", "ADANIENT.NS"),
    "wipro":    ("NSE:WIPRO",    "WIPRO.NS"),
    "icici":    ("NSE:ICICIBANK","ICICIBANK.NS"),
    "icici bank":("NSE:ICICIBANK","ICICIBANK.NS"),
    "bajaj":    ("NSE:BAJFINANCE","BAJFINANCE.NS"),
    "bajaj finance":("NSE:BAJFINANCE","BAJFINANCE.NS"),
    "titan":    ("NSE:TITAN",    "TITAN.NS"),
    "hul":      ("NSE:HINDUNILVR","HINDUNILVR.NS"),
    "hindustan unilever":("NSE:HINDUNILVR","HINDUNILVR.NS"),
    "asian paints":("NSE:ASIANPAINT","ASIANPAINT.NS"),
    "maruti":   ("NSE:MARUTI",   "MARUTI.NS"),
    "kotak":    ("NSE:KOTAKBANK","KOTAKBANK.NS"),
    "axis bank":("NSE:AXISBANK","AXISBANK.NS"),
    "itc":      ("NSE:ITC",      "ITC.NS"),
    "ongc":     ("NSE:ONGC",     "ONGC.NS"),
    "nifty":    ("NSE:NIFTY50",  "^NSEI"),
    "nifty 50": ("NSE:NIFTY50",  "^NSEI"),
    "nifty50":  ("NSE:NIFTY50",  "^NSEI"),
    "banknifty":("NSE:BANKNIFTY","^NSEBANK"),
    "bank nifty":("NSE:BANKNIFTY","^NSEBANK"),
    "sensex":   ("BSE:SENSEX",   "^BSESN"),
    # Crypto
    "bitcoin":  ("BINANCE:BTCUSDT","BTC-USD"),
    "btc":      ("BINANCE:BTCUSDT","BTC-USD"),
    "ethereum": ("BINANCE:ETHUSDT","ETH-USD"),
    "eth":      ("BINANCE:ETHUSDT","ETH-USD"),
    "solana":   ("BINANCE:SOLUSDT","SOL-USD"),
    "sol":      ("BINANCE:SOLUSDT","SOL-USD"),
    # US Stocks
    "apple":    ("NASDAQ:AAPL",  "AAPL"),
    "aapl":     ("NASDAQ:AAPL",  "AAPL"),
    "tesla":    ("NASDAQ:TSLA",  "TSLA"),
    "tsla":     ("NASDAQ:TSLA",  "TSLA"),
    "nvidia":   ("NASDAQ:NVDA",  "NVDA"),
    "nvda":     ("NASDAQ:NVDA",  "NVDA"),
}

TIMEFRAME_MAP = {
    "intraday": "15", "aaj": "15", "today": "15",
    "5 min": "5", "5min": "5", "5m": "5",
    "15 min": "15", "15m": "15",
    "1 hour": "60", "1h": "60", "hourly": "60",
    "4 hour": "240", "4h": "240",
    "daily": "D", "din": "D", "swing": "D",
    "weekly": "W", "hafte": "W", "week": "W",
    "monthly": "M", "month": "M", "long term": "W",
}

YF_PERIOD = {"5":"5d","15":"5d","60":"1mo","240":"3mo","D":"6mo","W":"2y","M":"5y"}
YF_INTERVAL = {"5":"5m","15":"15m","60":"1h","240":"4h","D":"1d","W":"1wk","M":"1mo"}

# ══════════════════════════════════════════════════════
# 2. PARSE USER INPUT
# ══════════════════════════════════════════════════════
def parse_user_input(text: str):
    t = text.lower().strip()

    # Detect symbol
    tv_sym, yf_sym, display_name = None, None, None
    for key, (tv, yf) in SYMBOL_MAP.items():
        if key in t:
            tv_sym, yf_sym, display_name = tv, yf, key.title()
            break

    # If not found, try to extract a ticker-like word or resolve company name
    if not tv_sym:
        # First try ticker resolver for company names (apple -> AAPL)
        _resolved = resolve_ticker(text)
        if _resolved and _resolved.upper() != text.upper().strip():
            # Check if resolved ticker is in SYMBOL_MAP
            for key, (tv, yf) in SYMBOL_MAP.items():
                if key.upper() == _resolved.upper() or yf.upper() == _resolved.upper():
                    tv_sym, yf_sym, display_name = tv, yf, key.title()
                    break
            if not tv_sym:
                sym = _resolved
                yf_sym = sym
                if ".NS" in sym:
                    tv_sym = f"NSE:{sym.replace('.NS','')}"
                elif sym in ("BTC","ETH","SOL","DOGE","ADA","XRP","BNB","AVAX","DOT","LINK","MATIC"):
                    tv_sym = f"BINANCE:{sym}USDT"
                else:
                    tv_sym = sym
                display_name = sym
        else:
            tokens = re.findall(r'\b[A-Z]{2,6}(?:\.NS|\.BO)?\b', text)
            if tokens:
                sym = tokens[0]
                yf_sym = sym
                tv_sym = f"NSE:{sym.replace('.NS','')}" if ".NS" in sym else sym
                display_name = sym

    # Detect timeframe
    tf = "D"
    for key, val in TIMEFRAME_MAP.items():
        if key in t:
            tf = val
            break

    # Detect mode
    if any(w in t for w in ["quick", "jaldi", "fast", "snapshot"]):
        mode = "QUICK"
    elif any(w in t for w in ["pattern", "chart pattern", "formation"]):
        mode = "PATTERN"
    elif any(w in t for w in ["rsi", "macd", "ema", "moving average", "indicator"]):
        mode = "INDICATOR"
    elif any(w in t for w in ["compare", "vs", "versus"]):
        mode = "COMPARE"
    else:
        mode = "FULL"

    return {
        "tv_sym": tv_sym,
        "yf_sym": yf_sym,
        "display_name": display_name or tv_sym or "Unknown",
        "timeframe": tf,
        "mode": mode,
        "raw": text,
    }

# ══════════════════════════════════════════════════════
# 3. FETCH REAL OHLCV DATA
# ══════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlcv(yf_sym: str, tf: str) -> pd.DataFrame:
    period   = YF_PERIOD.get(tf, "6mo")
    interval = YF_INTERVAL.get(tf, "1d")
    try:
        df = yf.Ticker(yf_sym).history(period=period, interval=interval)
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()

def compute_indicators(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 20:
        return {}
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    v = df["Volume"]

    # EMA
    ema20  = float(c.ewm(span=20).mean().iloc[-1])
    ema50  = float(c.ewm(span=50).mean().iloc[-1]) if len(c) >= 50 else None
    ema200 = float(c.ewm(span=200).mean().iloc[-1]) if len(c) >= 200 else None

    # RSI
    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = float((100 - 100 / (1 + rs)).iloc[-1])

    # MACD
    ema12  = c.ewm(span=12).mean()
    ema26  = c.ewm(span=26).mean()
    macd_l = ema12 - ema26
    sig_l  = macd_l.ewm(span=9).mean()
    macd_val  = float(macd_l.iloc[-1])
    signal_val = float(sig_l.iloc[-1])
    hist_val  = macd_val - signal_val

    # Volume
    avg_vol = float(v.rolling(20).mean().iloc[-1])
    cur_vol = float(v.iloc[-1])

    # Support / Resistance
    price  = float(c.iloc[-1])
    lows   = l.rolling(10).min()
    highs  = h.rolling(10).max()

    recent_lows  = sorted(set([round(float(x),2) for x in lows.dropna().tail(30)
                                if x < price * 0.98]), reverse=True)
    recent_highs = sorted(set([round(float(x),2) for x in highs.dropna().tail(30)
                                if x > price * 1.02]))

    # Filter to most distinct levels
    def _filter_levels(levels, min_gap_pct=0.015):
        filtered = []
        for lv in levels:
            if not filtered or abs(lv - filtered[-1]) / filtered[-1] > min_gap_pct:
                filtered.append(lv)
        return filtered[:3]

    supports    = _filter_levels(recent_lows[:8])
    resistances = _filter_levels(recent_highs[:8])

    # Trend detection
    sma20 = float(c.rolling(20).mean().iloc[-1])
    sma50 = float(c.rolling(50).mean().iloc[-1]) if len(c) >= 50 else sma20
    prev5 = float(c.iloc[-5]) if len(c) >= 5 else price

    if price > ema20 and price > sma50 and ema20 > sma50:
        trend = "BULLISH"
    elif price < ema20 and price < sma50 and ema20 < sma50:
        trend = "BEARISH"
    else:
        trend = "SIDEWAYS"

    # 5-day change
    chg5d = (price - prev5) / prev5 * 100 if prev5 else 0

    return {
        "price":       round(price, 2),
        "ema20":       round(ema20, 2),
        "ema50":       round(ema50, 2) if ema50 else None,
        "ema200":      round(ema200, 2) if ema200 else None,
        "rsi":         round(rsi, 1),
        "macd":        round(macd_val, 4),
        "macd_signal": round(signal_val, 4),
        "macd_hist":   round(hist_val, 4),
        "avg_vol":     int(avg_vol),
        "cur_vol":     int(cur_vol),
        "vol_ratio":   round(cur_vol / avg_vol, 2) if avg_vol else 1.0,
        "supports":    supports,
        "resistances": resistances,
        "trend":       trend,
        "chg5d":       round(chg5d, 2),
        "high52":      round(float(h.max()), 2),
        "low52":       round(float(l.min()), 2),
    }

# ══════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════
# 3b. CANDLESTICK PATTERN DETECTION
# ══════════════════════════════════════════════════════
def detect_candlestick_patterns(df: pd.DataFrame) -> list:
    """Detect common candlestick patterns from last N candles."""
    if df.empty or len(df) < 5:
        return []

    patterns = []
    # Look at last 10 candles for pattern detection
    recent = df.tail(10)

    for i in range(len(recent)):
        row = recent.iloc[i]
        o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
        body = abs(c - o)
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        total_range = h - l if h > l else 0.001
        body_pct = (body / total_range) * 100 if total_range > 0 else 0
        is_bull = c > o
        is_bear = c < o

        # Doji — open ≈ close, very small body
        if body_pct < 10:
            patterns.append({
                "name": "Doji",
                "type": "NEUTRAL",
                "candle_index": i,
                "description": "Market indecision — open and close nearly equal. Reversal possible.",
                "action": "Wait for confirmation candle",
                "color": "#f0c040",
            })

        # Hammer — small body, long lower shadow (>= 2x body), bullish
        if lower_shadow > 2 * body and body > 0 and upper_shadow < body * 0.5:
            patterns.append({
                "name": "Hammer",
                "type": "BULLISH",
                "candle_index": i,
                "description": "Long lower wick — buyers rejected lower prices. Reversal signal at support.",
                "action": "Watch for bullish confirmation",
                "color": "#10b981",
            })

        # Shooting Star — small body, long upper shadow, bearish
        if upper_shadow > 2 * body and body > 0 and lower_shadow < body * 0.5:
            patterns.append({
                "name": "Shooting Star",
                "type": "BEARISH",
                "candle_index": i,
                "description": "Long upper wick — sellers rejected higher prices. Reversal at resistance.",
                "action": "Watch for bearish confirmation",
                "color": "#ef4444",
            })

        # Bullish Engulfing — current green candle engulfs previous red
        if i > 0:
            prev = recent.iloc[i-1]
            p_o, p_c = float(prev["Open"]), float(prev["Close"])
            if p_c < p_o and c > o and c >= p_o and o <= p_c:
                patterns.append({
                    "name": "Bullish Engulfing",
                    "type": "BULLISH",
                    "candle_index": i,
                    "description": "Green candle fully engulfs previous red — strong bullish reversal.",
                    "action": "Potential buy signal with volume confirmation",
                    "color": "#10b981",
                })

        # Bearish Engulfing — current red engulfs previous green
        if i > 0:
            prev = recent.iloc[i-1]
            p_o, p_c = float(prev["Open"]), float(prev["Close"])
            if p_c > p_o and c < o and c <= p_o and o >= p_c:
                patterns.append({
                    "name": "Bearish Engulfing",
                    "type": "BEARISH",
                    "candle_index": i,
                    "description": "Red candle fully engulfs previous green — strong bearish reversal.",
                    "action": "Potential sell signal with volume confirmation",
                    "color": "#ef4444",
                })

        # Morning Star (3-candle pattern)
        if i >= 2:
            p1 = recent.iloc[i-2]
            p2 = recent.iloc[i-1]
            p1_bear = float(p1["Close"]) < float(p1["Open"])
            p2_small = abs(float(p2["Close"]) - float(p2["Open"])) < (float(p1["High"]) - float(p1["Low"])) * 0.3
            curr_bull = c > o and c > float(p1["Open"])
            if p1_bear and p2_small and curr_bull:
                patterns.append({
                    "name": "Morning Star",
                    "type": "BULLISH",
                    "candle_index": i,
                    "description": "3-candle bullish reversal: big red → small body → big green. Strong bottom signal.",
                    "action": "Bullish reversal — consider long with SL below the low",
                    "color": "#10b981",
                })

        # Evening Star (3-candle pattern)
        if i >= 2:
            p1 = recent.iloc[i-2]
            p2 = recent.iloc[i-1]
            p1_bull = float(p1["Close"]) > float(p1["Open"])
            p2_small = abs(float(p2["Close"]) - float(p2["Open"])) < (float(p1["High"]) - float(p1["Low"])) * 0.3
            curr_bear = c < o and c < float(p1["Open"])
            if p1_bull and p2_small and curr_bear:
                patterns.append({
                    "name": "Evening Star",
                    "type": "BEARISH",
                    "candle_index": i,
                    "description": "3-candle bearish reversal: big green → small body → big red. Strong top signal.",
                    "action": "Bearish reversal — consider short with SL above the high",
                    "color": "#ef4444",
                })

        # Marubozu — full body, no shadows
        if body_pct > 90:
            if is_bull:
                patterns.append({
                    "name": "Bullish Marubozu",
                    "type": "BULLISH",
                    "candle_index": i,
                    "description": "Full green body, no wicks — strong buying pressure throughout.",
                    "action": "Continuation of uptrend",
                    "color": "#10b981",
                })
            elif is_bear:
                patterns.append({
                    "name": "Bearish Marubozu",
                    "type": "BEARISH",
                    "candle_index": i,
                    "description": "Full red body, no wicks — strong selling pressure throughout.",
                    "action": "Continuation of downtrend",
                    "color": "#ef4444",
                })

        # Spinning Top — small body, long shadows both sides
        if body_pct < 30 and upper_shadow > body and lower_shadow > body:
            patterns.append({
                "name": "Spinning Top",
                "type": "NEUTRAL",
                "candle_index": i,
                "description": "Small body with long wicks both sides — indecision, trend may pause or reverse.",
                "action": "Wait for direction confirmation",
                "color": "#f0c040",
            })

    # Chart pattern detection (from last 30 candles)
    last30 = df.tail(30)
    if len(last30) >= 20:
        highs = last30["High"].values
        lows  = last30["Low"].values
        closes = last30["Close"].values

        # Double Top — two similar highs with a dip between
        max_idx = list(highs).index(max(highs))
        if max_idx > 5 and max_idx < len(highs) - 5:
            left_high = max(highs[:max_idx])
            right_high = max(highs[max_idx+1:])
            if abs(left_high - right_high) / left_high < 0.02 and left_high > highs[max_idx] * 0.98:
                patterns.append({
                    "name": "Double Top (Potential)",
                    "type": "BEARISH",
                    "candle_index": -1,
                    "description": "Two similar highs — bearish reversal pattern if confirmed.",
                    "action": "Watch for neckline break",
                    "color": "#ef4444",
                })

        # Double Bottom — two similar lows with a bump between
        min_idx = list(lows).index(min(lows))
        if min_idx > 5 and min_idx < len(lows) - 5:
            left_low = min(lows[:min_idx])
            right_low = min(lows[min_idx+1:])
            if abs(left_low - right_low) / left_low < 0.02 and left_low < lows[min_idx] * 1.02:
                patterns.append({
                    "name": "Double Bottom (Potential)",
                    "type": "BULLISH",
                    "candle_index": -1,
                    "description": "Two similar lows — bullish reversal pattern if confirmed.",
                    "action": "Watch for neckline break",
                    "color": "#10b981",
                })

        # Higher Highs + Higher Lows = Uptrend
        if len(closes) >= 10:
            hh = highs[-1] > highs[-5] and highs[-5] > highs[-10]
            hl = lows[-1] > lows[-5] and lows[-5] > lows[-10]
            if hh and hl:
                patterns.append({
                    "name": "Higher Highs + Higher Lows",
                    "type": "BULLISH",
                    "candle_index": -1,
                    "description": "Classic uptrend structure — each peak and trough higher than previous.",
                    "action": "Trend continuation — buy on dips",
                    "color": "#10b981",
                })

            lh = highs[-1] < highs[-5] and highs[-5] < highs[-10]
            ll = lows[-1] < lows[-5] and lows[-5] < lows[-10]
            if lh and ll:
                patterns.append({
                    "name": "Lower Highs + Lower Lows",
                    "type": "BEARISH",
                    "candle_index": -1,
                    "description": "Classic downtrend structure — each peak and trough lower than previous.",
                    "action": "Trend continuation — sell on rallies",
                    "color": "#ef4444",
                })

    # Deduplicate by name (keep latest)
    seen = {}
    for p in patterns:
        seen[p["name"]] = p
    return list(seen.values())[:8]


# ══════════════════════════════════════════════════════
# 3c. VWAP CALCULATION
# ══════════════════════════════════════════════════════
def compute_vwap(df: pd.DataFrame) -> float | None:
    """Calculate VWAP (Volume Weighted Average Price)."""
    if df.empty or "Volume" not in df.columns:
        return None
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    vol = df["Volume"].replace(0, np.nan)
    vwap = (typical_price * vol).sum() / vol.sum()
    return round(float(vwap), 2) if not np.isnan(vwap) else None


# ══════════════════════════════════════════════════════
# 3d. FUNDAMENTAL DATA FETCHER
# ══════════════════════════════════════════════════════
@st.cache_data(ttl=600, show_spinner=False)
def fetch_fundamentals(yf_sym: str) -> dict:
    """Fetch fundamental data: P&L, Balance Sheet, Cash Flow, Ratios, Management."""
    try:
        ticker = yf.Ticker(yf_sym)
        info = ticker.info or {}

        # Income Statement (P&L)
        income_stmt = {}
        try:
            inc = ticker.quarterly_income_stmt
            if inc is not None and not inc.empty:
                income_stmt = {
                    "revenue": _safe_float(inc.loc["Total Revenue"].iloc[0]) if "Total Revenue" in inc.index else None,
                    "net_income": _safe_float(inc.loc["Net Income"].iloc[0]) if "Net Income" in inc.index else None,
                    "gross_profit": _safe_float(inc.loc["Gross Profit"].iloc[0]) if "Gross Profit" in inc.index else None,
                    "operating_income": _safe_float(inc.loc["Operating Income"].iloc[0]) if "Operating Income" in inc.index else None,
                    "eps": _safe_float(inc.loc["Diluted EPS"].iloc[0]) if "Diluted EPS" in inc.index else None,
                }
        except Exception:
            pass

        # Balance Sheet
        balance_sheet = {}
        try:
            bs = ticker.quarterly_balance_sheet
            if bs is not None and not bs.empty:
                balance_sheet = {
                    "total_assets": _safe_float(bs.loc["Total Assets"].iloc[0]) if "Total Assets" in bs.index else None,
                    "total_liabilities": _safe_float(bs.loc["Total Liabilities Net Minority Interest"].iloc[0]) if "Total Liabilities Net Minority Interest" in bs.index else None,
                    "total_debt": _safe_float(bs.loc["Total Debt"].iloc[0]) if "Total Debt" in bs.index else None,
                    "total_equity": _safe_float(bs.loc["Stockholders Equity"].iloc[0]) if "Stockholders Equity" in bs.index else None,
                    "cash": _safe_float(bs.loc["Cash And Cash Equivalents"].iloc[0]) if "Cash And Cash Equivalents" in bs.index else None,
                }
        except Exception:
            pass

        # Cash Flow
        cash_flow = {}
        try:
            cf = ticker.quarterly_cashflow
            if cf is not None and not cf.empty:
                cash_flow = {
                    "operating_cf": _safe_float(cf.loc["Operating Cash Flow"].iloc[0]) if "Operating Cash Flow" in cf.index else None,
                    "free_cf": _safe_float(cf.loc["Free Cash Flow"].iloc[0]) if "Free Cash Flow" in cf.index else None,
                    "capex": _safe_float(cf.loc["Capital Expenditure"].iloc[0]) if "Capital Expenditure" in cf.index else None,
                    "dividends_paid": _safe_float(cf.loc["Cash Dividends Paid"].iloc[0]) if "Cash Dividends Paid" in cf.index else None,
                }
        except Exception:
            pass

        # Valuation Ratios
        ratios = {
            "pe_ratio": _safe_float(info.get("trailingPE")),
            "forward_pe": _safe_float(info.get("forwardPE")),
            "pb_ratio": _safe_float(info.get("priceToBook")),
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "roe": _safe_float(info.get("returnOnEquity")),
            "roa": _safe_float(info.get("returnOnAssets")),
            "debt_to_equity": _safe_float(info.get("debtToEquity")),
            "current_ratio": _safe_float(info.get("currentRatio")),
            "profit_margin": _safe_float(info.get("profitMargins")),
            "operating_margin": _safe_float(info.get("operatingMargins")),
            "revenue_growth": _safe_float(info.get("revenueGrowth")),
            "earnings_growth": _safe_float(info.get("earningsGrowth")),
            "peg_ratio": _safe_float(info.get("pegRatio")),
            "beta": _safe_float(info.get("beta")),
            "ev_to_ebitda": _safe_float(info.get("enterpriseToEbitda")),
            "market_cap": _safe_float(info.get("marketCap")),
            "enterprise_value": _safe_float(info.get("enterpriseValue")),
            "book_value": _safe_float(info.get("bookValue")),
            "eps_ttm": _safe_float(info.get("trailingEps")),
        }

        # Management & Company Info
        management = {
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "full_name": info.get("longName", info.get("shortName", "N/A")),
            "description": (info.get("longBusinessSummary", "")[:500] + "...") if info.get("longBusinessSummary") else "N/A",
            "website": info.get("website", "N/A"),
            "employees": _safe_float(info.get("fullTimeEmployees")),
            "country": info.get("country", "N/A"),
            "address": info.get("address1", "N/A"),
            "officers": info.get("companyOfficers", [])[:3],
        }

        return {
            "income_stmt": income_stmt,
            "balance_sheet": balance_sheet,
            "cash_flow": cash_flow,
            "ratios": ratios,
            "management": management,
            "available": True,
        }
    except Exception:
        return {"available": False}


def _safe_float(val) -> float | None:
    """Safely convert to float, return None if invalid."""
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _fmt_inr(val) -> str:
    """Format large numbers in Indian style (Cr/L) or $ style."""
    if val is None:
        return "N/A"
    if abs(val) >= 1e12:
        return f"{val/1e12:.2f}T"
    elif abs(val) >= 1e9:
        return f"{val/1e9:.2f}B"
    elif abs(val) >= 1e7:
        return f"{val/1e7:.2f}Cr"
    elif abs(val) >= 1e5:
        return f"{val/1e5:.2f}L"
    elif abs(val) >= 1e3:
        return f"{val/1e3:.2f}K"
    return f"{val:.2f}"



# 4. AI ANALYSIS GENERATION (SAGE SYSTEM PROMPT)
# ══════════════════════════════════════════════════════
SAGE_SYSTEM = """Tu hai "SAGE Analyst" — FinSage ka AI Chart Analyst.

Tu HAMESHA valid JSON return karega — koi extra text nahi, sirf JSON.

JSON mein yeh fields hongi:
- symbol, timeframe, analysis_type
- draw_commands: support_levels, resistance_levels, trendlines, indicators, zones, patterns, current_price_analysis
- candlestick_patterns: detected patterns with name, type, description, action
- fundamental_analysis: income_stmt, balance_sheet, cash_flow, valuation_ratios, management_quality, industry_analysis
- voice_script: segments array (each with segment number, duration_seconds, text, draw_action)
- chat_explanation: summary, bias, key_levels, indicators_summary, candlestick_summary, fundamental_summary, educational_insight, follow_up_prompts

Rules:
- Indian stocks: Rs currency (use "Rs" not the rupee symbol)
- Hinglish voice script (Hindi + English mix)
- Har level ka reason batao
- Candlestick patterns explain karo: kya dikh raha hai, kya matlab hai
- Fundamental analysis: P&L, Balance Sheet, Cash Flow, Valuation Ratios (P/E, P/B, ROE, D/E)
- Management quality: sector, industry growth, company description
- Economic factors: GDP, inflation, RBI rates ka asar
- Educational tone — koi direct buy/sell tip nahi
- Max 3 support + 3 resistance levels
- Voice total 60-90 seconds
- Disclaimer hamesha shamil karo"""

def generate_ai_analysis(parsed: dict, indicators: dict,
                             candlestick_patterns: list = None,
                             vwap: float = None,
                             fundamentals: dict = None) -> dict | None:
    """Call Groq to generate SAGE analysis JSON with full technical + fundamental data."""
    sym  = parsed["tv_sym"] or parsed["display_name"]
    tf   = parsed["timeframe"]
    mode = parsed["mode"]
    candlestick_patterns = candlestick_patterns or []
    fundamentals = fundamentals or {}

    is_indian = ".NS" in (parsed.get("yf_sym","") or "") or "NSE:" in sym
    curr      = "₹" if is_indian else "$"

    price  = indicators.get("price", 0)
    rsi    = indicators.get("rsi", 50)
    trend  = indicators.get("trend", "SIDEWAYS")
    ema20  = indicators.get("ema20")
    ema50  = indicators.get("ema50")
    ema200 = indicators.get("ema200")
    macd_h = indicators.get("macd_hist", 0)
    supp   = indicators.get("supports", [])
    res    = indicators.get("resistances", [])
    vol_r  = indicators.get("vol_ratio", 1.0)
    chg5   = indicators.get("chg5d", 0)

    tf_label = {"5":"5 min","15":"15 min","60":"1 hour","240":"4 hour",
                "D":"Daily","W":"Weekly","M":"Monthly"}.get(tf,"Daily")

    # Build candlestick patterns text
    cs_text = ""
    if candlestick_patterns:
        cs_text = "\nDETECTED CANDLESTICK PATTERNS:\n"
        for p in candlestick_patterns[:6]:
            cs_text += f"- {p['name']} ({p['type']}): {p.get('description','')}\n"
    else:
        cs_text = "\nDETECTED CANDLESTICK PATTERNS: None detected in recent candles\n"

    # Build fundamental data text
    fund_text = ""
    if fundamentals and fundamentals.get("available"):
        r = fundamentals.get("ratios", {})
        mg = fundamentals.get("management", {})
        inc = fundamentals.get("income_stmt", {})
        bs = fundamentals.get("balance_sheet", {})
        cf = fundamentals.get("cash_flow", {})
        fund_text = f"""
FUNDAMENTAL ANALYSIS DATA:
Sector: {mg.get('sector','N/A')}
Industry: {mg.get('industry','N/A')}
Company: {mg.get('full_name','N/A')}

VALUATION RATIOS:
P/E Ratio: {r.get('pe_ratio','N/A')}
Forward P/E: {r.get('forward_pe','N/A')}
P/B Ratio: {r.get('pb_ratio','N/A')}
Dividend Yield: {r.get('dividend_yield','N/A')}
ROE: {r.get('roe','N/A')}
ROA: {r.get('roa','N/A')}
Debt to Equity: {r.get('debt_to_equity','N/A')}
Profit Margin: {r.get('profit_margin','N/A')}
Revenue Growth: {r.get('revenue_growth','N/A')}
PEG Ratio: {r.get('peg_ratio','N/A')}
Beta: {r.get('beta','N/A')}
Market Cap: {r.get('market_cap','N/A')}

INCOME STATEMENT (Quarterly):
Revenue: {inc.get('revenue','N/A')}
Net Income: {inc.get('net_income','N/A')}
Gross Profit: {inc.get('gross_profit','N/A')}
EPS: {inc.get('eps','N/A')}

BALANCE SHEET:
Total Assets: {bs.get('total_assets','N/A')}
Total Debt: {bs.get('total_debt','N/A')}
Total Equity: {bs.get('total_equity','N/A')}
Cash: {bs.get('cash','N/A')}

CASH FLOW:
Operating CF: {cf.get('operating_cf','N/A')}
Free CF: {cf.get('free_cf','N/A')}
CapEx: {cf.get('capex','N/A')}

COMPANY DESCRIPTION: {mg.get('description','N/A')[:200]}
"""
    else:
        fund_text = "\nFUNDAMENTAL ANALYSIS: Data not available for this symbol\n"

    vwap_text = f"\nVWAP: {curr}{vwap}\n" if vwap else "\nVWAP: N/A\n"

    prompt = f"""Analyze this stock and return COMPLETE valid JSON for SAGE Analyst:

STOCK: {sym}
Display Name: {parsed['display_name']}
Currency: {curr}
Timeframe: {tf_label}
Analysis Mode: {mode}

REAL MARKET DATA:
Current Price: {curr}{price}
RSI (14): {rsi}
Trend: {trend}
EMA 20: {curr}{ema20}
EMA 50: {curr}{ema50 or 'N/A'}
EMA 200: {curr}{ema200 or 'N/A'}
MACD Histogram: {macd_h} ({'Bullish' if macd_h > 0 else 'Bearish'})
Volume Ratio: {vol_r}x average
5-day Change: {chg5}%
VWAP: {vwap_text.strip()}
Detected Supports: {supp}
Detected Resistances: {res}

{cs_text}
{fund_text}

Generate EXACT JSON with this structure (use real price data above):
{{
  "symbol": "{sym}",
  "timeframe": "{tf_label}",
  "analysis_type": "{mode}",
  "draw_commands": {{
    "support_levels": [
      {{"price": <number>, "strength": "STRONG|MODERATE|WEAK", "color": "#10b981", "style": "solid|dashed", "width": 2, "label": "S1 — Description", "reason": "Why this level matters"}}
    ],
    "resistance_levels": [
      {{"price": <number>, "strength": "STRONG|MODERATE|WEAK", "color": "#ef4444", "style": "solid|dashed", "width": 2, "label": "R1 — Description", "reason": "Why this level matters"}}
    ],
    "trendlines": [
      {{"type": "UPTREND|DOWNTREND|SIDEWAYS", "label": "Trendline name", "color": "#6366f1", "reason": "Why this trendline matters"}}
    ],
    "indicators": [
      {{"type": "EMA", "period": 20, "color": "#f59e0b", "current_value": {ema20}, "signal": "Signal description"}},
      {{"type": "RSI", "period": 14, "current_value": {rsi}, "signal": "RSI {rsi} meaning", "zone": "OVERBOUGHT|NEUTRAL|OVERSOLD"}},
      {{"type": "MACD", "current_signal": "MACD status", "histogram": "Histogram description"}},
      {{"type": "VOLUME", "vol_ratio": {vol_r}, "signal": "Volume analysis"}}
    ],
    "zones": [
      {{"type": "DEMAND_ZONE|SUPPLY_ZONE", "top": <number>, "bottom": <number>, "color": "#10b98120", "border_color": "#10b981", "label": "Zone name", "reason": "Why this zone"}}
    ],
    "patterns": [
      {{"type": "Pattern name", "status": "ACTIVE|FORMING|BROKEN", "label": "Pattern label", "color": "#6366f1"}}
    ],
    "current_price_analysis": {{
      "price": {price},
      "position": "Where price is relative to levels",
      "nearest_support": <number>,
      "nearest_resistance": <number>,
      "risk_reward_long": "1:X",
      "bias": "BULLISH|BEARISH|NEUTRAL"
    }}
  }},
  "voice_script": {{
    "language": "hinglish",
    "segments": [
      {{"segment": 1, "duration_seconds": 8, "text": "Hinglish text here", "draw_action": "chart_loads"}},
      {{"segment": 2, "duration_seconds": 12, "text": "Support levels explain in Hinglish", "draw_action": "draw_support", "highlight": "support"}},
      {{"segment": 3, "duration_seconds": 10, "text": "Resistance explain in Hinglish", "draw_action": "draw_resistance", "highlight": "resistance"}},
      {{"segment": 4, "duration_seconds": 12, "text": "Indicators explain in Hinglish", "draw_action": "show_indicators", "highlight": "indicators"}},
      {{"segment": 5, "duration_seconds": 10, "text": "Overall bias and disclaimer in Hinglish", "draw_action": "show_summary", "highlight": "summary"}}
    ]
  }},
  "chat_explanation": {{
    "summary": "One line summary",
    "bias": "BULLISH|BEARISH|NEUTRAL",
    "bias_color": "#10b981|#ef4444|#f59e0b",
    "key_levels": {{
      "strong_support": "₹X,XXX (reason)",
      "strong_resistance": "₹X,XXX (reason)"
    }},
    "indicators_summary": {{
      "trend": "Trend description",
      "ema_signal": "EMA signal",
      "rsi": "{rsi} — what it means",
      "macd": "MACD status",
      "volume": "Volume interpretation"
    }},
    "educational_insight": {{
      "why_these_levels": "Educational explanation",
      "what_to_watch": "What signals to monitor",
      "indicator_education": "How to use these indicators together"
    }},
    "risk_disclaimer": "⚠️ Yeh sirf educational technical analysis hai. Koi bhi investment decision lene se pehle apne SEBI-registered financial advisor se consult karein.",
    "follow_up_prompts": ["Question 1?", "Question 2?", "Question 3?"]
  }}
}}

Return ONLY valid JSON. No markdown, no explanations outside JSON."""

    msgs = [
        {"role": "system", "content": SAGE_SYSTEM},
        {"role": "user", "content": prompt}
    ]
    raw = _call_groq(msgs, max_tokens=3000, temperature=0.4)
    if not raw:
        return None

    # Extract JSON from response
    try:
        # Remove markdown code blocks if present
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*', '', raw)
        raw = raw.strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to find JSON block
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return None

# ══════════════════════════════════════════════════════
# 5. RULE-BASED FALLBACK (no API key)
# ══════════════════════════════════════════════════════
def _build_fund_summary(fund: dict, curr: str) -> str:
    """Build fundamental summary string from fund data."""
    if not fund or not fund.get("available"):
        return "Fundamental data not available for this symbol."
    r = fund.get("ratios", {})
    mg = fund.get("management", {})
    parts = []
    if r.get("pe_ratio"):
        parts.append(f"P/E: {r['pe_ratio']:.1f}")
    if r.get("pb_ratio"):
        parts.append(f"P/B: {r['pb_ratio']:.1f}")
    if r.get("roe"):
        parts.append(f"ROE: {r['roe']*100:.1f}%")
    if r.get("debt_to_equity"):
        parts.append(f"D/E: {r['debt_to_equity']:.2f}")
    if mg.get("sector"):
        parts.append(f"Sector: {mg['sector']}")
    return " | ".join(parts) if parts else "Fundamental data available but ratios not populated."

def generate_rule_based_analysis(parsed: dict, ind: dict,
                                 candlestick_patterns: list = None,
                                 vwap: float = None,
                                 fundamentals: dict = None) -> dict:
    """Generate analysis without AI when no API key — includes patterns + fundamentals."""
    candlestick_patterns = candlestick_patterns or []
    fundamentals = fundamentals or {}
    sym    = parsed.get("tv_sym") or parsed.get("display_name","Stock")
    name   = parsed.get("display_name","Stock")
    tf_lbl = {"5":"5 min","15":"15 min","60":"1 hour","240":"4 hour",
               "D":"Daily","W":"Weekly","M":"Monthly"}.get(parsed["timeframe"],"Daily")
    price  = ind.get("price", 0)
    rsi    = ind.get("rsi", 50)
    trend  = ind.get("trend","SIDEWAYS")
    ema20  = ind.get("ema20", price)
    ema50  = ind.get("ema50")
    ema200 = ind.get("ema200")
    macd_h = ind.get("macd_hist", 0)
    supp   = ind.get("supports",[])
    res    = ind.get("resistances",[])
    vol_r  = ind.get("vol_ratio",1.0)

    is_indian = ".NS" in (parsed.get("yf_sym","") or "")
    curr = "₹" if is_indian else "$"

    bias      = trend
    bias_color = {"BULLISH":"#10b981","BEARISH":"#ef4444","SIDEWAYS":"#f59e0b"}.get(bias,"#f59e0b")

    # Build support levels from detected
    sup_levels = []
    sup_colors = ["#10b981","#34d399","#6ee7b7"]
    for i, s in enumerate(supp[:3]):
        sup_levels.append({
            "price": s,
            "strength": "STRONG" if i==0 else "MODERATE",
            "color": sup_colors[i],
            "style": "solid" if i==0 else "dashed",
            "width": 2 if i==0 else 1,
            "label": f"S{i+1} — Support Level",
            "reason": f"Historical bounce level at {curr}{s}"
        })

    res_levels = []
    res_colors = ["#ef4444","#f87171","#fca5a5"]
    for i, r in enumerate(res[:3]):
        res_levels.append({
            "price": r,
            "strength": "STRONG" if i==0 else "MODERATE",
            "color": res_colors[i],
            "style": "solid" if i==0 else "dashed",
            "width": 2 if i==0 else 1,
            "label": f"R{i+1} — Resistance Level",
            "reason": f"Historical rejection at {curr}{r}"
        })

    rsi_zone = "OVERSOLD" if rsi < 30 else ("OVERBOUGHT" if rsi > 70 else "NEUTRAL")
    macd_sig  = "Bullish — MACD above signal line" if macd_h > 0 else "Bearish — MACD below signal line"

    ns   = supp[0] if supp else round(price*0.97,2)
    nr   = res[0]  if res  else round(price*1.03,2)

    voice_text_1 = f"Main ab {name} ka {tf_lbl} chart analyze kar raha hoon. Current price hai {curr}{price}. Chart par kuch important levels mark kar raha hoon."
    voice_text_2 = f"Pehle support dekho. Sabse strong support hai {curr}{ns} par. Yahan buyers historically active rahe hain."
    voice_text_3 = f"Ab resistance dekho. Nearest resistance hai {curr}{nr} par. Yahan sellers pressure create karte hain."
    voice_text_4 = f"Indicators mein RSI abhi {rsi} par hai — yeh {rsi_zone.lower()} zone hai. MACD {('bullish' if macd_h>0 else 'bearish')} signal de raha hai."
    voice_text_5 = f"Overall {name} ka structure {bias.lower()} dikh raha hai. Lekin yeh sirf educational analysis hai — apne financial advisor se consult zaroor karein."

    return {
        "symbol": sym,
        "timeframe": tf_lbl,
        "analysis_type": parsed["mode"],
        "draw_commands": {
            "support_levels": sup_levels,
            "resistance_levels": res_levels,
            "trendlines": [{"type": trend,"label": f"{trend} Trend","color":"#6366f1","reason":"Based on EMA alignment and price structure"}],
            "indicators": [
                {"type":"EMA","period":20,"color":"#f59e0b","current_value":ema20,"signal":f"Price {'above' if price>ema20 else 'below'} 20 EMA — {'Bullish' if price>ema20 else 'Bearish'}"},
                {"type":"EMA","period":50,"color":"#06b6d4","current_value":ema50,"signal":f"50 EMA at {curr}{ema50}" if ema50 else "50 EMA: insufficient data"},
                {"type":"EMA","period":200,"color":"#8b5cf6","current_value":ema200,"signal":f"200 EMA at {curr}{ema200}" if ema200 else "200 EMA: insufficient data"},
                {"type":"RSI","period":14,"current_value":rsi,"signal":f"RSI {rsi} — {rsi_zone}","zone":rsi_zone},
                {"type":"MACD","current_signal":macd_sig,"histogram":f"{'Positive' if macd_h>0 else 'Negative'} — {('Bullish' if macd_h>0 else 'Bearish')} momentum"},
                {"type":"VOLUME","vol_ratio":vol_r,"signal":f"Volume {vol_r}x average — {'High activity' if vol_r>1.5 else 'Normal'}"},
            ],
            "zones": [
                {"type":"DEMAND_ZONE","top":round(ns*1.01,2),"bottom":round(ns*0.99,2),"color":"#10b98120","border_color":"#10b981","label":"Demand Zone","reason":"Key support area"},
                {"type":"SUPPLY_ZONE","top":round(nr*1.01,2),"bottom":round(nr*0.99,2),"color":"#ef444420","border_color":"#ef4444","label":"Supply Zone","reason":"Key resistance area"},
            ],
            "patterns": [{"type":trend,"status":"ACTIVE","label":f"{trend.title()} Structure","color":"#6366f1"}],
            "current_price_analysis": {
                "price": price,
                "position": f"Between S1 ({curr}{ns}) and R1 ({curr}{nr})",
                "nearest_support": ns,
                "nearest_resistance": nr,
                "risk_reward_long": "1:2",
                "bias": bias
            }
        },
        "voice_script": {
            "language": "hinglish",
            "segments": [
                {"segment":1,"duration_seconds":8,"text":voice_text_1,"draw_action":"chart_loads"},
                {"segment":2,"duration_seconds":12,"text":voice_text_2,"draw_action":"draw_support","highlight":"support"},
                {"segment":3,"duration_seconds":10,"text":voice_text_3,"draw_action":"draw_resistance","highlight":"resistance"},
                {"segment":4,"duration_seconds":12,"text":voice_text_4,"draw_action":"show_indicators","highlight":"indicators"},
                {"segment":5,"duration_seconds":10,"text":voice_text_5,"draw_action":"show_summary","highlight":"summary"},
            ]
        },
        "chat_explanation": {
            "summary": f"{name} — {bias.title()} Structure",
            "bias": bias,
            "bias_color": bias_color,
            "key_levels": {
                "strong_support": f"{curr}{ns}",
                "strong_resistance": f"{curr}{nr}",
            },
            "indicators_summary": {
                "trend": f"{trend} — Based on EMA alignment",
                "ema_signal": f"Price {'above' if price>ema20 else 'below'} 20 EMA",
                "rsi": f"{rsi} — {rsi_zone}",
                "macd": macd_sig,
                "volume": f"{vol_r}x average volume",
            },
            "educational_insight": {
                "why_these_levels": "Support aur resistance levels wahan bante hain jahan hazaron traders ek saath buy ya sell karte hain. Yeh collective memory create karta hai.",
                "what_to_watch": f"Agar price {curr}{nr} strong volume se todta hai → Bullish breakout. {curr}{ns} ke neeche jaaye → Caution.",
                "indicator_education": "RSI + MACD ek saath dekhna best hai. Sirf ek indicator mat dekho — multiple confirmation lo.",
            },
            "risk_disclaimer": "⚠️ Yeh sirf educational technical analysis hai. Koi bhi investment decision lene se pehle apne SEBI-registered financial advisor se consult karein. Past performance future returns guarantee nahi karta.",
            "follow_up_prompts": [
                f"{name} ke candlestick patterns dikhao",
                "Is stock mein entry kaise dhundhein?",
                "Support level kyun important hai?",
                "MACD ko aur detail mein samjhao",
                "Fundamental analysis dikhao",
                "Industry aur sector analysis karo",
            ],
            "candlestick_summary": (
                f"{len(candlestick_patterns)} patterns detected. "
                + "; ".join(f"{p['name']} ({p['type']})" for p in candlestick_patterns[:3])
                if candlestick_patterns else "No significant candlestick patterns in recent candles."
            ),
            "fundamental_summary": _build_fund_summary(fundamentals, curr),
        }
    }

# ══════════════════════════════════════════════════════
# 6. TRADINGVIEW LIGHTWEIGHT CHART WITH DRAWINGS
# ══════════════════════════════════════════════════════
def build_chart_html(parsed: dict, analysis: dict, ohlcv: pd.DataFrame,
                         candlestick_patterns: list = None, vwap: float = None) -> str:
    tv_sym    = parsed.get("tv_sym","BINANCE:BTCUSDT")
    tf        = parsed.get("timeframe","D")
    tf_tv     = {"5":"5","15":"15","60":"60","240":"240","D":"D","W":"W","M":"M"}.get(tf,"D")
    draw_cmds = analysis.get("draw_commands",{})
    sup_lvls  = draw_cmds.get("support_levels",[])
    res_lvls  = draw_cmds.get("resistance_levels",[])
    zones     = draw_cmds.get("zones",[])
    cur_price = draw_cmds.get("current_price_analysis",{}).get("price",0)
    bias      = draw_cmds.get("current_price_analysis",{}).get("bias","NEUTRAL")
    bias_color = {"BULLISH":"#10b981","BEARISH":"#ef4444","NEUTRAL":"#f59e0b"}.get(bias,"#f59e0b")

    # OHLCV to JSON for lightweight chart
    candle_data = []
    if not ohlcv.empty:
        for idx, row in ohlcv.tail(200).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            candle_data.append({
                "time": ts,
                "open":  round(float(row["Open"]),4),
                "high":  round(float(row["High"]),4),
                "low":   round(float(row["Low"]),4),
                "close": round(float(row["Close"]),4),
            })
        # volume
        vol_data = []
        for idx, row in ohlcv.tail(200).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            is_up = float(row["Close"]) >= float(row["Open"])
            vol_data.append({"time":ts,"value":int(row["Volume"]),"color":"rgba(0,255,136,0.3)" if is_up else "rgba(255,68,102,0.3)"})
    else:
        candle_data = []
        vol_data = []

    candles_json = json.dumps(candle_data)
    vol_json     = json.dumps(vol_data)
    supp_json    = json.dumps(sup_lvls)
    res_json     = json.dumps(res_lvls)
    zones_json   = json.dumps(zones)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#020609; font-family:sans-serif; }}
#chart-container {{ position:relative; width:100%; height:500px; }}
#chart {{ width:100%; height:100%; }}
#legend {{ position:absolute; top:8px; left:8px; background:rgba(2,6,9,0.85);
  border:1px solid rgba(0,212,255,0.2); border-radius:8px; padding:8px 12px;
  font-size:11px; color:#e6edf3; z-index:10; min-width:160px; }}
#legend .bias-badge {{ display:inline-block; padding:2px 8px; border-radius:12px;
  font-size:10px; font-weight:700; background:{bias_color}22;
  color:{bias_color}; border:1px solid {bias_color}44; margin-top:4px; }}
#levels-panel {{ position:absolute; top:8px; right:8px; background:rgba(2,6,9,0.85);
  border:1px solid rgba(0,212,255,0.15); border-radius:8px; padding:8px 12px;
  font-size:10px; color:#8b949e; z-index:10; max-width:180px; }}
#levels-panel .lv-row {{ margin:3px 0; display:flex; justify-content:space-between; gap:8px; }}
.lv-s {{ color:#10b981; font-weight:600; }}
.lv-r {{ color:#ef4444; font-weight:600; }}
</style>
</head>
<body>
<div id="chart-container">
  <div id="legend">
    <div style="font-weight:700;color:#00d4ff;font-size:12px;">{parsed['display_name']}</div>
    <div style="color:#8b949e;font-size:10px;">{tf_tv} · SAGE Analysis</div>
    <div class="bias-badge">{bias}</div>
  </div>
  <div id="levels-panel">
    <div style="color:#00d4ff;font-weight:700;margin-bottom:4px;">Key Levels</div>
    {''.join(f'<div class="lv-row"><span class="lv-s">{s["label"][:12]}</span><span>{s["price"]}</span></div>' for s in sup_lvls[:3])}
    {''.join(f'<div class="lv-row"><span class="lv-r">{r["label"][:12]}</span><span>{r["price"]}</span></div>' for r in res_lvls[:3])}
  </div>
  <div id="chart"></div>
</div>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
const candleData = {candles_json};
const volData    = {vol_json};
const suppLvls   = {supp_json};
const resLvls    = {res_json};
const zones      = {zones_json};

const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
  width:  document.getElementById('chart-container').clientWidth,
  height: 500,
  layout: {{ background: {{ color:'#020609' }}, textColor:'#8b949e' }},
  grid: {{ vertLines:{{ color:'rgba(255,255,255,0.03)' }}, horzLines:{{ color:'rgba(255,255,255,0.03)' }} }},
  crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
  rightPriceScale: {{ borderColor:'rgba(0,212,255,0.15)' }},
  timeScale: {{ borderColor:'rgba(0,212,255,0.15)', timeVisible:true }},
}});

// Candlestick series
const candleSeries = chart.addCandlestickSeries({{
  upColor:'#00ff88', downColor:'#ff4466',
  borderUpColor:'#00ff88', borderDownColor:'#ff4466',
  wickUpColor:'#00ff88', wickDownColor:'#ff4466',
}});
if (candleData.length > 0) {{
  candleSeries.setData(candleData);
}}

// Volume
const volSeries = chart.addHistogramSeries({{
  priceFormat: {{ type:'volume' }},
  priceScaleId: 'volume',
  scaleMargins: {{ top:0.85, bottom:0 }},
}});
if (volData.length > 0) {{
  volSeries.setData(volData);
}}

// Draw support lines
suppLvls.forEach(function(s) {{
  const line = chart.addLineSeries({{
    color: s.color || '#10b981',
    lineWidth: s.width || 1,
    lineStyle: s.style === 'dashed' ? LightweightCharts.LineStyle.Dashed : LightweightCharts.LineStyle.Solid,
    priceLabel: {{ visible: true }},
    lastValueVisible: true,
  }});
  if (candleData.length > 0) {{
    line.setData([
      {{ time: candleData[0].time, value: s.price }},
      {{ time: candleData[candleData.length-1].time, value: s.price }},
    ]);
  }}
  candleSeries.createPriceLine({{
    price: s.price, color: s.color || '#10b981',
    lineWidth: s.width || 1,
    lineStyle: s.style === 'dashed' ? LightweightCharts.LineStyle.Dashed : LightweightCharts.LineStyle.Solid,
    axisLabelVisible: true, title: s.label || 'Support',
  }});
}});

// Draw resistance lines
resLvls.forEach(function(r) {{
  candleSeries.createPriceLine({{
    price: r.price, color: r.color || '#ef4444',
    lineWidth: r.width || 1,
    lineStyle: r.style === 'dashed' ? LightweightCharts.LineStyle.Dashed : LightweightCharts.LineStyle.Solid,
    axisLabelVisible: true, title: r.label || 'Resistance',
  }});
}});

// VWAP line
{f"candleSeries.createPriceLine({{ price: {vwap}, color: '#fbbf24', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: true, title: 'VWAP' }});" if vwap else ""}

// Current price line
candleSeries.createPriceLine({{
  price: {cur_price if cur_price else 0},
  color: '{bias_color}',
  lineWidth: 1,
  lineStyle: LightweightCharts.LineStyle.Dotted,
  axisLabelVisible: true,
  title: 'Current',
}});

chart.timeScale().fitContent();

// Resize
window.addEventListener('resize', function() {{
  chart.applyOptions({{ width: document.getElementById('chart-container').clientWidth }});
}});
</script>
</body>
</html>"""
    return html

# ══════════════════════════════════════════════════════
# 7. VOICE SCRIPT (Web Speech API)
# ══════════════════════════════════════════════════════
def build_voice_html(segments: list) -> str:
    full_text = " ".join(s.get("text","") for s in segments)
    full_text_json = json.dumps(full_text)

    return f"""
<div style="background:rgba(2,6,9,0.8);border:1px solid rgba(0,212,255,0.2);
border-radius:12px;padding:14px 16px;margin:10px 0;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
    <span style="font-size:1rem;font-weight:700;color:#00d4ff;">🎙️ Voice Analysis</span>
    <span style="font-size:0.72rem;color:#8b949e;">(Web Speech API — works in Chrome/Edge)</span>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <button onclick="speakAnalysis()" style="background:rgba(0,212,255,0.15);
    border:1px solid rgba(0,212,255,0.4);border-radius:8px;padding:8px 16px;
    color:#00d4ff;font-weight:700;cursor:pointer;font-size:13px;">
    ▶ Play Voice Analysis</button>
    <button onclick="stopSpeech()" style="background:rgba(255,68,102,0.1);
    border:1px solid rgba(255,68,102,0.3);border-radius:8px;padding:8px 14px;
    color:#ff4466;font-weight:700;cursor:pointer;font-size:13px;">
    ⏹ Stop</button>
  </div>
  <div id="voice-status" style="font-size:0.75rem;color:#8b949e;margin-top:8px;">
    Click Play to hear the analysis</div>
  <div id="voice-segments" style="margin-top:8px;"></div>
</div>

<script>
const segments = {json.dumps(segments)};
const fullText = {full_text_json};
let utterance = null;

function speakAnalysis() {{
  if (!window.speechSynthesis) {{
    document.getElementById('voice-status').textContent = 
      '❌ Web Speech API not supported. Use Chrome or Edge.';
    return;
  }}
  window.speechSynthesis.cancel();
  utterance = new SpeechSynthesisUtterance(fullText);
  utterance.lang = 'hi-IN';
  utterance.rate = 0.85;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;
  
  // Try Hindi voice first, then any voice
  const voices = window.speechSynthesis.getVoices();
  const hiVoice = voices.find(v => v.lang === 'hi-IN') || 
                  voices.find(v => v.lang.startsWith('hi')) ||
                  voices.find(v => v.lang.startsWith('en-IN')) ||
                  null;
  if (hiVoice) utterance.voice = hiVoice;
  
  utterance.onstart = function() {{
    document.getElementById('voice-status').innerHTML = 
      '<span style="color:#00ff88;">🎙️ Playing analysis...</span>';
  }};
  utterance.onend = function() {{
    document.getElementById('voice-status').innerHTML =
      '<span style="color:#8b949e;">✅ Analysis complete.</span>';
  }};
  utterance.onerror = function(e) {{
    document.getElementById('voice-status').innerHTML =
      '<span style="color:#ff4466;">❌ Voice error: ' + e.error + '</span>';
  }};
  
  window.speechSynthesis.speak(utterance);
}}

function stopSpeech() {{
  window.speechSynthesis.cancel();
  document.getElementById('voice-status').textContent = 'Stopped.';
}}

// Show segments
const segDiv = document.getElementById('voice-segments');
segments.forEach(function(s) {{
  const d = document.createElement('div');
  d.style.cssText = 'font-size:11px;color:#8b949e;margin:3px 0;padding:5px 8px;'+
    'background:rgba(255,255,255,0.03);border-radius:6px;border-left:2px solid rgba(0,212,255,0.2);';
  d.innerHTML = '<b style="color:#4a9eff;">Seg ' + s.segment + ':</b> ' + s.text;
  segDiv.appendChild(d);
}});

// Load voices async
window.speechSynthesis.onvoiceschanged = function() {{}};
</script>"""

# ══════════════════════════════════════════════════════
# 8. CSS
# ══════════════════════════════════════════════════════
# ── Finsage AI New Logo
_SAGE_LOGO = "https://base44.app/api/apps/6a34884cbcecdd779c9d0281/files/mp/public/6a34884cbcecdd779c9d0281/a07ce8a2c_finsage_new_logo.jpg"

SAGE_CSS = """<style>
/* ── SAGE Pro Dark Theme — Midnight Blue + Teal + Gold ─────────────── */
.sage-header {
  background:linear-gradient(135deg,#050d1f 0%,#091628 50%,#050d1f 100%);
  border:1px solid transparent;
  border-image:linear-gradient(90deg,rgba(0,212,255,0.5),rgba(0,180,200,0.3),rgba(0,212,255,0.5)) 1;
  border-radius:16px;padding:16px 20px;margin-bottom:14px;
  box-shadow:0 0 32px rgba(0,212,255,0.06),inset 0 1px 0 rgba(0,212,255,0.1);
  position:relative;overflow:hidden;
}
.sage-header::before {
  content:"";position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(0,212,255,0.7),rgba(0,212,255,0.3),transparent);
}
.sage-logo-img {
  height:38px;border-radius:8px;object-fit:contain;
  filter:drop-shadow(0 0 8px rgba(0,212,255,0.4));
}
.sage-title {
  font-size:1.2rem;font-weight:900;font-family:Orbitron,monospace;
  background:linear-gradient(90deg,#00d4ff,#00b8d9,#00d4ff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
}
.sage-badge {
  display:inline-block;font-size:9px;font-weight:800;padding:2px 8px;
  border-radius:10px;margin-left:6px;letter-spacing:0.05em;
  background:rgba(0,212,255,0.08);color:#00d4ff;
  border:1px solid rgba(0,212,255,0.3);
}
.sage-badge-gold {
  background:rgba(255,185,0,0.1);color:#ffd700;
  border:1px solid rgba(255,185,0,0.3);
}
.sage-input-bar {
  background:linear-gradient(135deg,#060f1e,#091628);
  border:1px solid rgba(0,212,255,0.18);
  border-radius:12px;padding:12px;margin-bottom:10px;
  box-shadow:inset 0 1px 0 rgba(0,212,255,0.05);
}
.sage-card {
  background:linear-gradient(145deg,#050d1f,#071a30);
  border:1px solid rgba(0,212,255,0.12);border-radius:12px;
  padding:14px;margin:8px 0;
  box-shadow:0 4px 16px rgba(0,0,0,0.3);
}
.sage-bias-box {
  display:inline-block;padding:5px 14px;border-radius:16px;
  font-size:0.9rem;font-weight:900;margin:4px 0;letter-spacing:0.05em;
}
.sage-level-row {
  display:flex;justify-content:space-between;align-items:center;
  padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);
  font-size:0.8rem;
}
.sage-indicator-chip {
  display:inline-block;padding:3px 9px;border-radius:6px;
  font-size:0.72rem;font-weight:600;margin:2px;
}
.sage-insight {
  background:linear-gradient(135deg,#060f1e,#071a30);
  border-left:2px solid #00d4ff;border-radius:0 8px 8px 0;
  padding:10px 14px;margin:6px 0;font-size:0.79rem;color:#b0cce0;line-height:1.7;
}
.sage-disclaimer {
  background:rgba(255,185,0,0.05);border:1px solid rgba(255,185,0,0.2);
  border-radius:8px;padding:9px 13px;margin:8px 0;
  font-size:0.74rem;color:#ffd700;
}
.sage-section-title {
  font-size:0.7rem;font-weight:800;color:#00d4ff;text-transform:uppercase;
  letter-spacing:0.1em;margin:12px 0 6px;
  display:flex;align-items:center;gap:6px;
}
.sage-section-title::after {
  content:"";flex:1;height:1px;background:rgba(0,212,255,0.12);
}
.sage-msg-user {
  background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.2);
  border-radius:12px 12px 4px 12px;padding:10px 14px;margin:5px 0;
  font-size:0.83rem;color:#e8f4fd;max-width:85%;margin-left:auto;
}
.sage-msg-ai {
  background:rgba(0,0,0,0.2);border:1px solid rgba(0,212,255,0.1);
  border-radius:4px 12px 12px 12px;padding:10px 14px;margin:5px 0;
  font-size:0.83rem;color:#b0cce0;max-width:90%;line-height:1.6;
}
.sage-quick-btn { transition:all 0.15s; }
.sage-quick-btn:hover { transform:translateY(-1px); }
</style>"""

# ══════════════════════════════════════════════════════
# 9. SAGE CHAT (follow-up Q&A)
# ══════════════════════════════════════════════════════
def sage_chat_response(question: str, analysis: dict, parsed: dict) -> str:
    """Answer follow-up questions about the analysis."""
    sym   = parsed.get("display_name","the stock")
    chat  = analysis.get("chat_explanation",{})
    bias  = chat.get("bias","NEUTRAL")
    ind   = chat.get("indicators_summary",{})
    levels= chat.get("key_levels",{})

    # Build context with candlestick + fundamental data
    cs_patterns = analysis.get("detected_candlestick_patterns", [])
    fund_data = analysis.get("fundamentals", {})
    cs_text = "; ".join(f"{p['name']} ({p['type']})" for p in cs_patterns[:5]) if cs_patterns else "None detected"
    fund_text = ""
    if fund_data and fund_data.get("available"):
        r = fund_data.get("ratios", {})
        mg = fund_data.get("management", {})
        fund_text = f"Sector: {mg.get('sector','N/A')}, P/E: {r.get('pe_ratio','N/A')}, ROE: {r.get('roe','N/A')}, D/E: {r.get('debt_to_equity','N/A')}"

    system = f"""Tu SAGE Analyst hai. User ne {sym} ka analysis dekha:
Bias: {bias}
Key Levels: {json.dumps(levels)}
Indicators: {json.dumps(ind)}
Candlestick Patterns: {cs_text}
Fundamental Data: {fund_text}
Educational Insight: {json.dumps(chat.get('educational_insight',{}))}

User ke follow-up questions ka jawab do:
- Hinglish mein (Hindi + English mix)
- Educational tone — koi direct buy/sell tip nahi
- 100-200 words
- Specific levels aur indicators reference karo
- Candlestick patterns explain karo agar sawaal ho
- Fundamental analysis (P/E, ROE, Balance Sheet) explain karo
- Industry/sector analysis karo
- Economic factors (GDP, inflation, RBI rates) ka asar batao
- Har jawab mein ek educational insight do
- Disclaimer add karo agar trading decision ki baat ho"""

    msgs = [
        {"role":"system","content":system},
        {"role":"user","content":question}
    ]
    reply = _call_groq(msgs, max_tokens=500, temperature=0.6)
    if reply:
        return reply

    # Rule-based fallback
    q = question.lower()
    if "fundamental" in q or "balance sheet" in q or "p/e" in q or "pe ratio" in q or "valuation" in q:
        fund_data = analysis.get("fundamentals", {})
        if fund_data and fund_data.get("available"):
            r = fund_data.get("ratios", {})
            mg = fund_data.get("management", {})
            return f"**Fundamental Analysis — {sym}**\n\n**Sector:** {mg.get('sector','N/A')}\n**Industry:** {mg.get('industry','N/A')}\n\n**Valuation Ratios:**\n- P/E: {r.get('pe_ratio','N/A')}\n- P/B: {r.get('pb_ratio','N/A')}\n- ROE: {r.get('roe','N/A')}\n- Debt/Equity: {r.get('debt_to_equity','N/A')}\n- Profit Margin: {r.get('profit_margin','N/A')}\n\nP/E ratio batata hai ki market company ki earnings ke liye kitna pay kar raha hai. Lower P/E = cheaper, but growth prospects bhi check karo.\n\n⚠️ Educational only. Apne advisor se consult karein."
        return f"**Fundamental Analysis**\n\n{sym} ka fundamental data abhi available nahi hai. Yahoo Finance se fetch nahi ho paaya.\n\n⚠️ Educational only."
    elif "candlestick" in q or "pattern" in q or "doji" in q or "hammer" in q or "engulfing" in q:
        cs = analysis.get("detected_candlestick_patterns", [])
        if cs:
            names = ", ".join(f"{p['name']} ({p['type']})" for p in cs[:5])
            return f"**Candlestick Patterns — {sym}**\n\nDetected patterns: {names}\n\nCandlestick patterns price action ki psychology dikhate hain. Har pattern ka apna matlab hai:\n- Doji = Indecision\n- Hammer = Bullish reversal at support\n- Engulfing = Strong reversal signal\n\nVolume ke saath confirm karo before acting.\n\n⚠️ Educational only."
        return f"**Candlestick Patterns**\n\n{sym} mein abhi koi significant candlestick pattern detect nahi hua. Recent candles mein clear pattern nahi ban raha.\n\n⚠️ Educational only."
    elif "industry" in q or "sector" in q:
        fund_data = analysis.get("fundamentals", {})
        mg = fund_data.get("management", {}) if fund_data else {}
        sector = mg.get("sector", "N/A")
        industry = mg.get("industry", "N/A")
        return f"**Industry Analysis — {sym}**\n\n**Sector:** {sector}\n**Industry:** {industry}\n\nSector analysis important hai kyunki:\n1. Growing sector mein company ko grow karna aasaan hai\n2. Government policies ka asar padta hai (PLI scheme, FDI rules)\n3. Competition aur market share matter karta hai\n4. India mein {sector} sector ki growth rate monitor karo\n\n⚠️ Educational only."
    elif "economic" in q or "gdp" in q or "inflation" in q or "rbi" in q or "interest rate" in q:
        return f"**Economic Factors — {sym}**\n\nEconomic factors stock prices ko directly affect karte hain:\n\n1. **GDP Growth:** India GDP 6-7% grow kar raha hai — positive for equity markets\n2. **Inflation:** High inflation se RBI interest rates badhata hai — negative for stocks\n3. **RBI Rates:** High rates se borrowing cost badhti hai, company profits par asar padta hai\n4. **Global Factors:** US Fed rates, crude oil prices, geo-political tensions\n\n⚠️ Educational only. Economic factors long-term investing mein important hain."
    elif "management" in q:
        fund_data = analysis.get("fundamentals", {})
        mg = fund_data.get("management", {}) if fund_data else {}
        return f"**Management Quality — {sym}**\n\n**Company:** {mg.get('full_name','N/A')}\n**Sector:** {mg.get('sector','N/A')}\n\nManagement quality check karne ke points:\n1. **Experience:** Promoter aur CEO ka track record\n2. **Honesty:** Corporate governance, auditor reports\n3. **Alignment:** Promoter shareholding (% stake)\n4. **Execution:** Past promises vs deliverables\n5. **Transparency:** Quarterly results, disclosures\n\n⚠️ Educational only."
    elif "support" in q or "support kyun" in q:
        ns = levels.get("strong_support","key level")
        return f"**Support level kyun important hai?**\n\nSupport {ns} par isliye important hai kyunki historically price yahan se bounce hua hai. Hazaron traders yeh level dekhte hain aur wahan buy orders lagate hain. Jab buyers ek saath active ho jaate hain, price support le leta hai.\n\n⚠️ Educational only. Apne advisor se consult karein."
    elif "entry" in q:
        return f"**Entry kaise dhundhen?**\n\nEntry ke liye support zone ke paas wait karo jab:\n1. Bullish reversal candle confirm ho (Hammer, Engulfing)\n2. Volume average se zyada ho\n3. RSI oversold zone se wapas aaye\n\nYeh confirmation milne ke baad consider karo. Risk always define karke chalo.\n\n⚠️ Educational only."
    elif "macd" in q:
        macd_s = ind.get("macd","MACD signal")
        return f"**MACD kya bata raha hai?**\n\n{sym} mein {macd_s}.\n\nMACD = 12 EMA - 26 EMA. Jab MACD line signal line ke upar jaaye → Bullish. Neeche jaaye → Bearish. Histogram momentum dikhata hai — growing histogram = momentum badh raha hai.\n\n⚠️ Educational only."
    elif "rsi" in q:
        rsi_s = ind.get("rsi","RSI")
        return f"**RSI ka matlab?**\n\n{sym} mein {rsi_s}.\n\nRSI 0-100 scale par hota hai:\n- Below 30 = Oversold (potential bounce)\n- Above 70 = Overbought (potential correction)\n- 30-70 = Neutral zone\n\nRSI sirf ek indicator hai — doosre indicators se confirm karo.\n\n⚠️ Educational only."
    else:
        ei = chat.get("educational_insight",{})
        return f"**{sym} Analysis:**\n\n{ei.get('what_to_watch','Monitor key levels for breakout or breakdown.')}\n\n{ei.get('indicator_education','Use multiple indicators for confirmation.')}\n\n⚠️ {chat.get('risk_disclaimer','Educational only. Not SEBI investment advice.')}"

# ══════════════════════════════════════════════════════
# 9b. TRADINGVIEW ADVANCED WIDGET BUILDER
# ══════════════════════════════════════════════════════
def _build_tv_advanced_widget(tv_sym: str, tf: str, height: int = 640,
                               studies: list = None) -> str:
    """Build a proper TradingView advanced chart widget HTML."""
    if studies is None:
        studies = ['"MAExp@tv-basicstudies"','"RSI@tv-basicstudies"',
                   '"MACD@tv-basicstudies"','"Volume@tv-basicstudies"']
    studies_json = "[" + ",".join(studies) + "]"
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:100%; height:100%; background:#131722; overflow:hidden; }}
.tv-wrap {{ width:100%; height:{height}px; }}
.tradingview-widget-container,
.tradingview-widget-container__widget {{
    width:100% !important;
    height:100% !important;
}}
</style>
</head>
<body>
<div class="tv-wrap">
  <div class="tradingview-widget-container" style="height:{height}px;width:100%;">
    <div class="tradingview-widget-container__widget"
         style="height:{height}px;width:100%;"></div>
    <script type="text/javascript"
      src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
    {{
      "autosize": true,
      "symbol": "{tv_sym}",
      "interval": "{tf}",
      "timezone": "Asia/Kolkata",
      "theme": "dark",
      "style": "1",
      "locale": "en",
      "toolbar_bg": "#131722",
      "backgroundColor": "rgba(19,23,34,1)",
      "gridColor": "rgba(255,255,255,0.03)",
      "enable_publishing": false,
      "allow_symbol_change": true,
      "save_image": true,
      "calendar": false,
      "hide_side_toolbar": false,
      "details": false,
      "hotlist": false,
      "withdateranges": true,
      "studies": {studies_json},
      "show_popup_button": false,
      "support_host": "https://www.tradingview.com"
    }}
    </script>
  </div>
</div>
<script>
function fixH() {{
  var w = document.querySelector('.tradingview-widget-container__widget');
  var c = document.querySelector('.tradingview-widget-container');
  var f = document.querySelector('iframe');
  if(w) w.style.height = '{height}px';
  if(c) c.style.height = '{height}px';
  if(f) f.style.height = '{height}px';
}}
fixH();
setTimeout(fixH,800);
setTimeout(fixH,2000);
window.addEventListener('resize', fixH);
</script>
</body>
</html>"""


def _render_sage_tv_integrated(parsed: dict, analysis: dict):
    """
    Full TradingView + SAGE AI integrated view.
    Shows TradingView advanced chart on the left,
    AI analysis + TradingView-style chat on the right.
    """
    import streamlit.components.v1 as components

    tv_sym = parsed.get("tv_sym","NSE:RELIANCE") if parsed else "NSE:RELIANCE"
    tf     = parsed.get("timeframe","D") if parsed else "D"
    tf_tv  = {"5":"5","15":"15","60":"60","240":"240","D":"D","W":"W","M":"M"}.get(tf,"D")
    draw_cmds = analysis.get("draw_commands",{}) if analysis else {}
    chat_exp  = analysis.get("chat_explanation",{}) if analysis else {}
    voice_seg = analysis.get("voice_script",{}).get("segments",[]) if analysis else []

    # Fullscreen CSS for integrated TV view
    st.markdown("""<style>
    /* Integrated TV mode — maximize space */
    .block-container { padding-left:0.3rem !important; padding-right:0.3rem !important; }
    </style>""", unsafe_allow_html=True)

    # Header bar
    bias       = draw_cmds.get("current_price_analysis",{}).get("bias","NEUTRAL")
    bias_color = {"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#f0c040"}.get(bias,"#f0c040")
    summary    = chat_exp.get("summary","SAGE Analysis")
    sup_lvls   = draw_cmds.get("support_levels",[])
    res_lvls   = draw_cmds.get("resistance_levels",[])
    cur_price  = draw_cmds.get("current_price_analysis",{}).get("price",0)

    st.markdown(f"""
    <div style="background:#131722;border:1px solid #2a2e39;border-radius:8px 8px 0 0;
    padding:8px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;
    margin-bottom:0;border-bottom:none;">
      <span style="color:#2962ff;font-size:18px;">⬡</span>
      <span style="color:#d1d4dc;font-weight:700;font-size:14px;">{parsed.get('display_name','') if parsed else ''}</span>
      <span style="background:#1e3a5f;color:#2962ff;font-size:10px;padding:2px 8px;
      border-radius:10px;border:1px solid #2962ff44;">{tf_tv} · SAGE</span>
      <span style="background:{bias_color}22;color:{bias_color};font-size:11px;
      padding:2px 10px;border-radius:10px;font-weight:700;border:1px solid {bias_color}44;
      margin-left:auto;">{bias}</span>
      <span style="color:#6a6e7a;font-size:11px;">{summary}</span>
    </div>
    """, unsafe_allow_html=True)

    # Two-column layout: chart left (2/3), panel right (1/3)
    chart_col, panel_col = st.columns([2, 1], gap="small")

    with chart_col:
        # TradingView Advanced Chart — full width, 700px height
        tv_html = _build_tv_advanced_widget(tv_sym, tf_tv, height=700)
        components.html(tv_html, height=714, scrolling=False)

        # SAGE analysis overlay as Pine-script-style caption below chart
        if sup_lvls or res_lvls:
            sup_str = " | ".join([f"🟢 {s['label'][:10]}: {s['price']}" for s in sup_lvls[:3]])
            res_str = " | ".join([f"🔴 {r['label'][:10]}: {r['price']}" for r in res_lvls[:3]])
            st.markdown(f"""
            <div style="background:#1e222d;border:1px solid #2a2e39;border-radius:0 0 8px 8px;
            padding:7px 14px;font-size:11.5px;font-family:monospace;
            display:flex;gap:16px;flex-wrap:wrap;">
              <span>{sup_str}</span>
              <span>{res_str}</span>
              {'<span style="color:#f0c040;">📍 Current: '+str(cur_price)+'</span>' if cur_price else ''}
            </div>
            """, unsafe_allow_html=True)

    with panel_col:
        # TradingView-style side panel
        st.markdown("""<style>
        .tv-panel { background:#131722; border:1px solid #2a2e39; border-radius:8px;
                    height:fit-content; overflow:hidden; }
        .tv-panel-tab { background:#1e222d; border-bottom:1px solid #2a2e39;
                        padding:8px 0; display:flex; }
        .tv-panel-tab-item { flex:1; text-align:center; color:#6a6e7a; font-size:11px;
                             font-weight:600; cursor:pointer; padding:4px 0; }
        .tv-panel-tab-item.active { color:#2962ff; border-bottom:2px solid #2962ff; }
        .tv-panel-body { padding:10px 12px; }
        .tv-level-row { display:flex; justify-content:space-between; align-items:center;
                        padding:5px 0; border-bottom:1px solid #1e222d; font-size:12px; }
        .tv-ind-row { display:flex; justify-content:space-between; padding:4px 0;
                      font-size:11.5px; border-bottom:1px solid #1a1e2d; }
        </style>""", unsafe_allow_html=True)

        panel_tab = st.session_state.get("sage_tv_panel_tab", "analysis")

        tab_btns = st.columns(3)
        with tab_btns[0]:
            if st.button("📊 Analysis", key="tvp_analysis",
                         type="primary" if panel_tab == "analysis" else "secondary",
                         use_container_width=True):
                st.session_state.sage_tv_panel_tab = "analysis"
                st.rerun()
        with tab_btns[1]:
            if st.button("📐 Levels", key="tvp_levels",
                         type="primary" if panel_tab == "levels" else "secondary",
                         use_container_width=True):
                st.session_state.sage_tv_panel_tab = "levels"
                st.rerun()
        with tab_btns[2]:
            if st.button("💬 Chat", key="tvp_chat",
                         type="primary" if panel_tab == "chat" else "secondary",
                         use_container_width=True):
                st.session_state.sage_tv_panel_tab = "chat"
                st.rerun()

        # ANALYSIS TAB
        if panel_tab == "analysis":
            ind_sum = chat_exp.get("indicators_summary",{})
            st.markdown('<div class="tv-panel">', unsafe_allow_html=True)

            # Bias card
            st.markdown(f"""
            <div style="background:{bias_color}11;border:1px solid {bias_color}33;
            border-radius:6px;padding:10px;margin-bottom:10px;text-align:center;">
              <div style="font-size:18px;font-weight:900;color:{bias_color};">{bias}</div>
              <div style="color:#6a6e7a;font-size:10px;margin-top:2px;">{summary[:40]}</div>
            </div>
            """, unsafe_allow_html=True)

            # Indicators
            if ind_sum:
                st.markdown('<div style="color:#d1d4dc;font-size:11px;font-weight:700;margin-bottom:6px;">INDICATORS</div>', unsafe_allow_html=True)
                for key, val in ind_sum.items():
                    ic = "#26a69a" if "bull" in str(val).lower() else ("#ef5350" if "bear" in str(val).lower() else "#6a6e7a")
                    st.markdown(f"""<div class="tv-ind-row">
                    <span style="color:#6a6e7a;">{key.upper()}</span>
                    <span style="color:{ic};font-weight:600;">{str(val)[:28]}</span>
                    </div>""", unsafe_allow_html=True)

            # Voice script summary
            if voice_seg:
                st.markdown('<div style="color:#d1d4dc;font-size:11px;font-weight:700;margin:10px 0 6px 0;">SAGE SAYS</div>', unsafe_allow_html=True)
                for seg in voice_seg[:3]:
                    st.markdown(f"""<div style="background:#1a1e2d;border-radius:6px;padding:7px 9px;
                    margin-bottom:5px;font-size:11px;color:#9598a1;line-height:1.5;">
                    <span style="color:#2962ff;font-weight:700;">#{seg['segment']}</span> {seg['text'][:100]}…
                    </div>""", unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        # LEVELS TAB
        elif panel_tab == "levels":
            st.markdown('<div class="tv-panel"><div class="tv-panel-body">', unsafe_allow_html=True)

            if sup_lvls:
                st.markdown('<div style="color:#26a69a;font-size:11px;font-weight:700;margin-bottom:6px;">SUPPORT LEVELS</div>', unsafe_allow_html=True)
                for s in sup_lvls[:4]:
                    strength_color = "#26a69a" if s.get("strength","") == "STRONG" else "#1a5c4f"
                    st.markdown(f"""
                    <div class="tv-level-row">
                      <span style="color:{strength_color};font-weight:600;">{s['label'][:20]}</span>
                      <span style="color:#26a69a;font-family:monospace;font-weight:700;">{s['price']}</span>
                    </div>
                    <div style="color:#4a4e5a;font-size:10px;padding:2px 0 5px 0;">{s.get('reason','')[:60]}</div>
                    """, unsafe_allow_html=True)

            if res_lvls:
                st.markdown('<div style="color:#ef5350;font-size:11px;font-weight:700;margin:10px 0 6px 0;">RESISTANCE LEVELS</div>', unsafe_allow_html=True)
                for r in res_lvls[:4]:
                    strength_color = "#ef5350" if r.get("strength","") == "STRONG" else "#7a2525"
                    st.markdown(f"""
                    <div class="tv-level-row">
                      <span style="color:{strength_color};font-weight:600;">{r['label'][:20]}</span>
                      <span style="color:#ef5350;font-family:monospace;font-weight:700;">{r['price']}</span>
                    </div>
                    <div style="color:#4a4e5a;font-size:10px;padding:2px 0 5px 0;">{r.get('reason','')[:60]}</div>
                    """, unsafe_allow_html=True)

            zones = draw_cmds.get("zones",[])
            if zones:
                st.markdown('<div style="color:#f0c040;font-size:11px;font-weight:700;margin:10px 0 6px 0;">ZONES</div>', unsafe_allow_html=True)
                for z in zones[:3]:
                    zc = "#26a69a" if z.get("type","") == "DEMAND_ZONE" else "#ef5350"
                    st.markdown(f"""<div class="tv-level-row">
                    <span style="color:{zc};">{z.get('label','Zone')[:20]}</span>
                    <span style="color:{zc};font-size:10px;">{z.get('bottom','')} – {z.get('top','')}</span>
                    </div>""", unsafe_allow_html=True)

            st.markdown('</div></div>', unsafe_allow_html=True)

        # CHAT TAB — TradingView style
        elif panel_tab == "chat":
            _render_sage_tv_chat(parsed, analysis)

    # Educational insight below
    insight = chat_exp.get("educational_insight",{})
    if insight:
        with st.expander("💡 Educational Insight", expanded=False):
            for key, val in insight.items():
                st.markdown(f"**{key.replace('_',' ').title()}:** {val}")

    # Disclaimer
    disc = chat_exp.get("risk_disclaimer","")
    if disc:
        st.markdown(f'<div style="background:#1a1500;border:1px solid #3d2e00;border-radius:6px;padding:7px 12px;font-size:11px;color:#8b949e;margin-top:8px;">{disc}</div>', unsafe_allow_html=True)

    # Back button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⬅ Back to Analysis View", key="sage_tv_back"):
        st.session_state.sage_tv_mode = False
        st.rerun()


def _render_sage_tv_chat(parsed: dict, analysis: dict):
    """TradingView-style embedded chat for SAGE integrated view."""
    chat_exp = analysis.get("chat_explanation",{}) if analysis else {}
    sym_name = parsed.get("display_name","Stock") if parsed else "Stock"

    st.markdown("""<style>
    .sage-tv-chat-scroll {
        max-height:340px; overflow-y:auto; background:#131722;
        border:1px solid #2a2e39; border-radius:6px; padding:8px;
        margin-bottom:8px;
    }
    .sage-tv-chat-scroll::-webkit-scrollbar { width:4px; }
    .sage-tv-chat-scroll::-webkit-scrollbar-track { background:#1a1e2d; }
    .sage-tv-chat-scroll::-webkit-scrollbar-thumb { background:#2a2e39; border-radius:2px; }
    .sage-tv-msg-u {
        background:#1e3a5f; color:#d1d4dc; border-radius:10px 10px 2px 10px;
        padding:7px 10px; margin:4px 0 4px 20%; font-size:11.5px;
        border-left:2px solid #2962ff;
    }
    .sage-tv-msg-a {
        background:#1e222d; color:#d1d4dc; border-radius:2px 10px 10px 10px;
        padding:7px 10px; margin:4px 20% 4px 0; font-size:11.5px;
        border-left:2px solid #26a69a;
    }
    .sage-tv-ai-tag { color:#26a69a; font-size:9px; font-weight:700; margin-bottom:2px; }
    </style>""", unsafe_allow_html=True)

    # Init
    if "sage_tv_chat" not in st.session_state:
        st.session_state.sage_tv_chat = [
            {"role":"ai","content":f"Namaste! Main {sym_name} ka analysis kar chuka hoon. Support/resistance levels, indicators, entry points — kuch bhi poochho."}
        ]

    # Messages
    st.markdown('<div class="sage-tv-chat-scroll">', unsafe_allow_html=True)
    for msg in st.session_state.sage_tv_chat[-25:]:
        if msg["role"] == "user":
            st.markdown(f'<div class="sage-tv-msg-u">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="sage-tv-msg-a"><div class="sage-tv-ai-tag">🤖 SAGE AI</div>{msg["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Follow-up chips
    follow_ups = chat_exp.get("follow_up_prompts",[])
    if follow_ups:
        st.markdown('<div style="margin-bottom:6px;">', unsafe_allow_html=True)
        fu_cols = st.columns(2)
        for i, prompt in enumerate(follow_ups[:4]):
            with fu_cols[i % 2]:
                lbl = prompt[:22]+"…" if len(prompt)>22 else prompt
                if st.button(lbl, key=f"sage_tv_fu_{i}",
                             use_container_width=True, help=prompt):
                    st.session_state.sage_tv_chat.append({"role":"user","content":prompt})
                    with st.spinner(""):
                        reply = sage_chat_response(prompt, analysis, parsed)
                    st.session_state.sage_tv_chat.append({"role":"ai","content":reply})
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Input
    qcol, scol = st.columns([4, 1])
    with qcol:
        tv_chat_q = st.text_input("Ask SAGE...",
            placeholder="Entry kab lein? RSI kya bol raha hai?",
            key="sage_tv_chat_input", label_visibility="collapsed")
    with scol:
        if st.button("Send", key="sage_tv_chat_send",
                     type="primary", use_container_width=True):
            if tv_chat_q.strip():
                st.session_state.sage_tv_chat.append({"role":"user","content":tv_chat_q.strip()})
                with st.spinner(""):
                    reply = sage_chat_response(tv_chat_q.strip(), analysis, parsed)
                st.session_state.sage_tv_chat.append({"role":"ai","content":reply})
                st.rerun()

    # Clear
    if st.button("🗑️ Clear Chat", key="sage_tv_chat_clear", use_container_width=True):
        st.session_state.sage_tv_chat = []
        st.rerun()


# ══════════════════════════════════════════════════════
# 10. STATE INIT
# ══════════════════════════════════════════════════════
def _init_sage_state():
    for k,v in {
        "sage_analysis":    None,
        "sage_parsed":      None,
        "sage_ohlcv":       None,
        "sage_indicators":  None,
        "sage_chat_hist":   [],
        "sage_input":       "",
        "sage_loading":     False,
        "sage_last_sym":    "",
        "sage_tv_mode":     False,
        "sage_tv_panel_tab": "analysis",
        "sage_tv_chat":     [],
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ══════════════════════════════════════════════════════
# 11. MAIN RENDER
# ══════════════════════════════════════════════════════
def render_sage_analyst():
    st.markdown(SAGE_CSS, unsafe_allow_html=True)
    _init_sage_state()

    lang = st.session_state.get("user_lang","en")

    # ── Header ────────────────────────────────────────
    st.markdown(f"""<div class="sage-header">
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      <img src="https://base44.app/api/apps/6a34884cbcecdd779c9d0281/files/mp/public/6a34884cbcecdd779c9d0281/a07ce8a2c_finsage_new_logo.jpg" class="sage-logo-img" alt="Finsage AI">
      <div>
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
          <span class="sage-title">SAGE Analyst</span>
          <span class="sage-badge">AI POWERED</span>
          <span class="sage-badge sage-badge-gold">GROQ LLAMA 3.3</span>
        </div>
        <div style="font-size:0.72rem;color:#4a7a99;margin-top:3px;">
        Chart Analysis · Voice · S/R Drawing · Education
        </div>
      </div>
      <div style="margin-left:auto;text-align:right;">
        <div style="font-size:0.68rem;color:#556;line-height:1.6;">
        🔴 LIVE &nbsp;·&nbsp; NSE / BSE / Crypto / US<br>
        Groq AI + Real yfinance Data
        </div>
      </div>
    </div>
    <div style="font-size:0.76rem;color:#4a7a99;margin-top:10px;
    padding-top:8px;border-top:1px solid rgba(0,212,255,0.08);">
    Koi bhi stock bolo → AI chart analyze karega, support/resistance draw karega,
    voice mein samjhayega aur follow-up sawaalon ka jawab dega
    </div>
    </div>""", unsafe_allow_html=True)

    # ── Quick Symbol Buttons ───────────────────────────
    st.markdown("**⚡ Quick Select:**")
    q_syms = ["Reliance","TCS","HDFC Bank","Nifty 50","SBI","Infosys","ICICI","Bitcoin","Tesla"]
    q_cols = st.columns(len(q_syms))
    for i, sym in enumerate(q_syms):
        with q_cols[i]:
            if st.button(sym, key=f"sage_q_{i}", use_container_width=True):
                st.session_state.sage_input = sym
                st.rerun()

    # ── Input Bar ─────────────────────────────────────
    st.markdown('<div class="sage-input-bar">', unsafe_allow_html=True)
    col_inp, col_tf, col_mode, col_btn = st.columns([4, 1.5, 1.5, 1])
    with col_inp:
        user_input = st.text_input(
            "",
            value=st.session_state.get("sage_input",""),
            placeholder="Reliance ka analysis karo / TCS daily chart / Nifty intraday / Bitcoin MACD explain karo",
            key="sage_text_input",
            label_visibility="collapsed"
        )
    with col_tf:
        tf_choice = st.selectbox("",
            ["Auto","Intraday (15m)","Hourly (1H)","Daily","Weekly"],
            key="sage_tf", label_visibility="collapsed")
    with col_mode:
        mode_choice = st.selectbox("",
            ["Full Analysis","Quick Scan","Pattern Search","Indicator Focus"],
            key="sage_mode", label_visibility="collapsed")
    with col_btn:
        analyze_btn = st.button("🔍 Analyze", type="primary",
                                use_container_width=True, key="sage_analyze_btn")
    st.markdown('</div>', unsafe_allow_html=True)

    # Override TF if manually selected
    tf_override = {
        "Intraday (15m)":"15","Hourly (1H)":"60",
        "Daily":"D","Weekly":"W","Auto":None
    }.get(tf_choice)
    mode_override = {
        "Full Analysis":"FULL","Quick Scan":"QUICK",
        "Pattern Search":"PATTERN","Indicator Focus":"INDICATOR","Full Analysis":None
    }.get(mode_choice)

    # ── Process Query ──────────────────────────────────
    trigger = analyze_btn or (user_input and user_input != st.session_state.get("sage_last_sym",""))

    if trigger and user_input.strip():
        st.session_state.sage_last_sym = user_input
        st.session_state.sage_input    = user_input
        st.session_state.sage_chat_hist= []

        with st.spinner("🧠 SAGE analyzing... fetching real market data..."):
            parsed = parse_user_input(user_input)
            if tf_override:
                parsed["timeframe"] = tf_override

            # Fetch real OHLCV
            ohlcv = pd.DataFrame()
            ind   = {}
            cs_patterns = []
            vwap_val = None
            fund_data = {}
            if parsed.get("yf_sym"):
                ohlcv = fetch_ohlcv(parsed["yf_sym"], parsed["timeframe"])
                if not ohlcv.empty:
                    ind = compute_indicators(ohlcv)
                    cs_patterns = detect_candlestick_patterns(ohlcv)
                    vwap_val = compute_vwap(ohlcv)
                    # Fetch fundamentals for stocks (not crypto/indices)
                    yf_s = parsed["yf_sym"]
                    if not yf_s.startswith("^") and ".NS" in yf_s or ".BO" in yf_s or (yf_s.isupper() and len(yf_s) <= 6 and "." not in yf_s and "-" not in yf_s):
                        fund_data = fetch_fundamentals(yf_s)

            # Try AI analysis first
            analysis = None
            if _groq_key() and ind:
                analysis = generate_ai_analysis(parsed, ind,
                    candlestick_patterns=cs_patterns,
                    vwap=vwap_val,
                    fundamentals=fund_data)

            # Fallback
            if not analysis and ind:
                analysis = generate_rule_based_analysis(parsed, ind,
                    candlestick_patterns=cs_patterns,
                    vwap=vwap_val,
                    fundamentals=fund_data)
            elif not analysis:
                parsed["tv_sym"] = parsed.get("tv_sym") or "NSE:RELIANCE"
                parsed["display_name"] = parsed.get("display_name") or user_input.title()
                ind = {"price":0,"rsi":50,"trend":"SIDEWAYS","ema20":0,"supports":[],"resistances":[],"vol_ratio":1.0,"macd_hist":0}
                analysis = generate_rule_based_analysis(parsed, ind,
                    candlestick_patterns=cs_patterns,
                    vwap=vwap_val,
                    fundamentals=fund_data)

            # Attach detected patterns & fundamentals to analysis for display
            analysis["detected_candlestick_patterns"] = cs_patterns
            analysis["fundamentals"] = fund_data
            analysis["vwap"] = vwap_val

            st.session_state.sage_analysis   = analysis
            st.session_state.sage_parsed     = parsed
            st.session_state.sage_ohlcv      = ohlcv
            st.session_state.sage_indicators = ind

    # ── Display Results ────────────────────────────────
    analysis = st.session_state.sage_analysis
    parsed   = st.session_state.sage_parsed
    ohlcv    = st.session_state.sage_ohlcv
    ind      = st.session_state.sage_indicators

    if not analysis:
        st.markdown("""<div style="text-align:center;padding:40px;color:#4a5568;">
        <div style="font-size:2.5rem;margin-bottom:12px;">📊</div>
        <div style="color:#7fa8c9;font-size:0.9rem;">Koi bhi stock ya index bolo upar ☝️</div>
        <div style="color:#556;font-size:0.78rem;margin-top:6px;">
        e.g. "Reliance ka analysis karo" ya "TCS daily chart"
        </div></div>""", unsafe_allow_html=True)
        return

    draw_cmds = analysis.get("draw_commands",{})
    chat_exp  = analysis.get("chat_explanation",{})
    voice_seg = analysis.get("voice_script",{}).get("segments",[])

    # ── FULL-WIDTH BIG CHART ───────────────────────────
    # Chart is now full width — no sidebar. Info goes below.

    if ohlcv is not None and not (ohlcv.empty if hasattr(ohlcv,'empty') else True):
        chart_html = build_chart_html(parsed, analysis, ohlcv,
            candlestick_patterns=analysis.get("detected_candlestick_patterns",[]),
            vwap=analysis.get("vwap"))
        components.html(chart_html, height=680, scrolling=False)
    else:
        tv_sym = parsed.get("tv_sym","NSE:RELIANCE")
        tf_tv  = {"5":"5","15":"15","60":"60","240":"240","D":"D","W":"W","M":"M"}.get(
                  parsed.get("timeframe","D"),"D")
        tv_html = _build_tv_advanced_widget(tv_sym, tf_tv)
        components.html(tv_html, height=660, scrolling=False)

    # ── CONNECT TO TRADINGVIEW BUTTON ─────────────────
    tv_sym_for_btn = parsed.get("tv_sym","NSE:RELIANCE") if parsed else "NSE:RELIANCE"
    tf_for_btn = parsed.get("timeframe","D") if parsed else "D"
    tf_tv_for_btn = {"5":"5","15":"15","60":"60","240":"240","D":"D","W":"W","M":"M"}.get(tf_for_btn,"D")

    _btncol1, _btncol2, _btncol3 = st.columns([2,2,3])
    with _btncol1:
        if st.button("📊 Connect to TradingView", key="sage_tv_connect",
                     type="primary", use_container_width=True,
                     help="TradingView mein AI-drawn analysis dekhein"):
            st.session_state.sage_tv_mode = not st.session_state.get("sage_tv_mode", False)
            st.rerun()
    with _btncol2:
        if st.button("🔄 New Analysis", key="sage_new_analysis",
                     use_container_width=True):
            st.session_state.sage_analysis = None
            st.session_state.sage_tv_mode = False
            st.rerun()

    # ── TRADINGVIEW INTEGRATED MODE ─────────────────────
    if st.session_state.get("sage_tv_mode", False):
        _render_sage_tv_integrated(parsed, analysis)
        return

    # Voice panel (full width below chart)
    if voice_seg:
        voice_html = build_voice_html(voice_seg)
        components.html(voice_html, height=260, scrolling=False)

    # ── INFO STRIP (horizontal cards below chart) ──────
    bias       = chat_exp.get("bias","NEUTRAL")
    bias_color = chat_exp.get("bias_color","#f59e0b")
    summary    = chat_exp.get("summary","Analysis")

    # Top summary bar
    st.markdown(f"""<div class="sage-card" style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
    <div>
        <div style="font-size:0.68rem;color:#4a7a99;text-transform:uppercase;letter-spacing:0.08em;">
        SAGE Analysis — {analysis.get('timeframe','Daily')}</div>
        <div style="font-size:1.05rem;font-weight:800;color:#e8f4fd;margin:3px 0;">{summary}</div>
    </div>
    <div class="sage-bias-box" style="background:{bias_color}1a;
    color:{bias_color};border:1px solid {bias_color}44;margin-left:auto;">{bias}</div>
    </div>""", unsafe_allow_html=True)

    # Key Levels in 2 columns
    # ── KEY LEVELS + INDICATORS (2-column strip) ──────
    levels = chat_exp.get("key_levels",{})
    ind_sum = chat_exp.get("indicators_summary",{})
    if levels or ind_sum:
        kl_cols = st.columns(2)
        with kl_cols[0]:
            if levels:
                st.markdown("**📐 Key Levels**")
                for key, val in levels.items():
                    if "support" in key.lower():
                        st.markdown(f"""<div class="sage-level-row">
                        <span style="color:#10b981;">🟢 {key.replace('_',' ').title()}</span>
                        <span style="color:#10b981;font-weight:700;">{val}</span>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div class="sage-level-row">
                        <span style="color:#ef4444;">🔴 {key.replace('_',' ').title()}</span>
                        <span style="color:#ef4444;font-weight:700;">{val}</span>
                        </div>""", unsafe_allow_html=True)
        with kl_cols[1]:
            if ind_sum:
                st.markdown("**📊 Indicators**")
                for key, val in ind_sum.items():
                    color = "#10b981" if "bull" in str(val).lower() else ("#ef4444" if "bear" in str(val).lower() else "#7fa8c9")
                    st.markdown(f"""<span class="sage-indicator-chip"
                    style="background:{color}1a;color:{color};
                    border:1px solid {color}33;">{key.upper()}: {str(val)[:40]}</span>""",
                    unsafe_allow_html=True)

    # Candlestick chips
    detected_cs = analysis.get("detected_candlestick_patterns", [])
    if detected_cs:
        st.write("")
        st.markdown("**🕯️ Candlestick Patterns**")
        cs_chips = ""
        for p in detected_cs[:6]:
            ptype = p.get("type","NEUTRAL")
            pcolor = {"BULLISH":"#10b981","BEARISH":"#ef4444","NEUTRAL":"#f0c040"}.get(ptype,"#8b949e")
            cs_chips += f"""<span class="sage-indicator-chip"
            style="background:{pcolor}1a;color:{pcolor};border:1px solid {pcolor}33;
            display:inline-block;margin:2px;">{p['name']} ({ptype})</span>"""
        st.markdown(cs_chips, unsafe_allow_html=True)

    # Educational Insight
    insight = chat_exp.get("educational_insight",{})
    if insight:
        st.write("")
        st.markdown("**💡 Educational Insight**")
        for key, val in insight.items():
            st.markdown(f'<div class="sage-insight"><b>{key.replace("_"," ").title()}:</b> {val}</div>',
                       unsafe_allow_html=True)

    # Disclaimer
    disc = chat_exp.get("risk_disclaimer","")
    if disc:
        st.markdown(f'<div class="sage-disclaimer">{disc}</div>',
                   unsafe_allow_html=True)

    # ── CANDLESTICK PATTERNS SECTION ───────────────────
    detected_patterns = analysis.get("detected_candlestick_patterns", [])
    if detected_patterns:
        st.markdown("---")
        st.markdown("### 🕯️ Candlestick Patterns Detected")
        cs_cols = st.columns(min(4, len(detected_patterns)))
        for i, p in enumerate(detected_patterns[:8]):
            with cs_cols[i % len(cs_cols)]:
                ptype = p.get("type", "NEUTRAL")
                bg = {"BULLISH":"rgba(16,185,129,0.08)","BEARISH":"rgba(239,68,68,0.08)","NEUTRAL":"rgba(240,196,64,0.08)"}.get(ptype, "rgba(255,255,255,0.05)")
                border = {"BULLISH":"rgba(16,185,129,0.3)","BEARISH":"rgba(239,68,68,0.3)","NEUTRAL":"rgba(240,196,64,0.3)"}.get(ptype, "rgba(255,255,255,0.1)")
                emoji = {"BULLISH":"🟢","BEARISH":"🔴","NEUTRAL":"🟡"}.get(ptype, "⚪")
                st.markdown(f"""<div style="background:{bg};border:1px solid {border};
                border-radius:8px;padding:10px;margin:4px 0;">
                <div style="font-weight:700;font-size:0.85rem;color:{p.get('color','#00d4ff')};">
                {emoji} {p['name']}</div>
                <div style="font-size:0.72rem;color:#8b949e;margin:4px 0;">
                {p.get('description','')}</div>
                <div style="font-size:0.72rem;color:#4a9eff;font-weight:600;">
                → {p.get('action','')}</div>
                </div>""", unsafe_allow_html=True)

    # ── FUNDAMENTAL ANALYSIS — PROFESSIONAL SUMMARY ────
    fund_data = analysis.get("fundamentals", {})
    if fund_data and fund_data.get("available"):
        st.markdown("---")
        st.markdown("### 📊 Fundamental Analysis")

        mg = fund_data.get("management", {})
        ratios = fund_data.get("ratios", {})
        inc = fund_data.get("income_stmt", {})
        bs = fund_data.get("balance_sheet", {})
        cf = fund_data.get("cash_flow", {})

        is_indian = ".NS" in (parsed.get("yf_sym","") or "") or ".BO" in (parsed.get("yf_sym","") or "")
        curr_sym = "Rs" if is_indian else "$"

        # ── Company Header Card ──
        company_name = mg.get('full_name', 'N/A')
        sector = mg.get('sector', 'N/A')
        industry = mg.get('industry', 'N/A')
        country = mg.get('country', 'N/A')
        mcap = ratios.get('market_cap')
        mcap_str = _fmt_inr(mcap) if mcap else 'N/A'

        st.markdown(f"""<div class="sage-card" style="padding:18px 20px;">
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
            <div style="font-size:1.1rem;font-weight:800;color:#00d4ff;">
            {company_name}</div>
            <span class="sage-badge">{sector}</span>
            <span class="sage-badge sage-badge-gold">MCap: {curr_sym}{mcap_str}</span>
        </div>
        <div style="font-size:0.76rem;color:#4a7a99;margin:6px 0;">
        {industry} · {country}
        </div>
        <div style="font-size:0.78rem;color:#b0cce0;margin-top:8px;line-height:1.7;
        padding-top:8px;border-top:1px solid rgba(0,212,255,0.08);">
        {mg.get('description','N/A')[:350]}
        </div>
        </div>""", unsafe_allow_html=True)

        # ── Valuation Ratios Grid ──
        if ratios:
            st.markdown("")
            st.markdown("""<div class="sage-section-title">Valuation & Profitability Ratios</div>""",
                       unsafe_allow_html=True)

            # Build ratio cards in 6-column grid
            ratio_defs = [
                ("P/E Ratio", "pe_ratio", "ratio", "Price-to-Earnings — lower = cheaper"),
                ("Fwd P/E", "forward_pe", "ratio", "Forward P/E based on expected earnings"),
                ("P/B Ratio", "pb_ratio", "ratio", "Price-to-Book — asset valuation"),
                ("Div Yield", "dividend_yield", "pct", "Annual dividend as % of price"),
                ("ROE", "roe", "pct", "Return on Equity — profitability"),
                ("ROA", "roa", "pct", "Return on Assets — efficiency"),
                ("D/E Ratio", "debt_to_equity", "ratio", "Debt to Equity — leverage risk"),
                ("Profit Margin", "profit_margin", "pct", "Net profit margin"),
                ("Rev Growth", "revenue_growth", "pct", "Year-over-year revenue growth"),
                ("PEG Ratio", "peg_ratio", "ratio", "P/E adjusted for growth rate"),
                ("Beta", "beta", "ratio", "Volatility vs market (1.0 = market)"),
                ("EV/EBITDA", "ev_to_ebitda", "ratio", "Enterprise value to EBITDA"),
            ]

            r_cols = st.columns(6)
            for i, (label, key, fmt, hint) in enumerate(ratio_defs):
                val = ratios.get(key)
                if val is not None:
                    with r_cols[i % 6]:
                        if fmt == "pct" and abs(val) < 10:
                            display = f"{val*100:.1f}%"
                        elif fmt == "pct":
                            display = f"{val:.2f}"
                        else:
                            display = f"{val:.2f}"
                        # Color: green for good, red for bad, neutral
                        good_keys = ["roe", "roa", "profit_margin", "revenue_growth", "dividend_yield"]
                        bad_keys = ["debt_to_equity"]
                        if key in good_keys and val > 0:
                            val_color = "#10b981"
                        elif key in bad_keys and val > 2:
                            val_color = "#ef4444"
                        else:
                            val_color = "#e8f4fd"
                        st.markdown(f"""<div style="background:linear-gradient(145deg,#050d1f,#071a30);
                        border:1px solid rgba(0,212,255,0.1);border-radius:8px;
                        padding:8px 6px;text-align:center;margin:3px 0;">
                        <div style="font-size:0.6rem;color:#4a7a99;text-transform:uppercase;
                        letter-spacing:0.05em;">{label}</div>
                        <div style="font-size:0.95rem;font-weight:800;color:{val_color};
                        font-family:JetBrains Mono,monospace;margin:2px 0;">{display}</div>
                        </div>""", unsafe_allow_html=True)

        # ── Financial Statements (3-column professional cards) ──
        st.markdown("")
        st.markdown("""<div class="sage-section-title">Financial Statements (Latest Quarter)</div>""",
                   unsafe_allow_html=True)

        col_fs1, col_fs2, col_fs3 = st.columns(3)

        with col_fs1:
            st.markdown("""<div style="background:linear-gradient(145deg,#050d1f,#071a30);
            border:1px solid rgba(0,212,255,0.12);border-radius:10px;padding:14px;">
            <div style="font-size:0.8rem;font-weight:800;color:#00d4ff;margin-bottom:10px;
            display:flex;align-items:center;gap:6px;">📋 Income Statement</div>""",
            unsafe_allow_html=True)
            if inc:
                for k, v in inc.items():
                    if v is not None:
                        label = k.replace('_',' ').title()
                        st.markdown(f"""<div style="display:flex;justify-content:space-between;
                        padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.03);
                        font-size:0.75rem;">
                        <span style="color:#8b949e;">{label}</span>
                        <span style="color:#e8f4fd;font-weight:700;font-family:monospace;">
                        {curr_sym}{_fmt_inr(v)}</span></div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size:0.72rem;color:#556;">Data not available</div>',
                           unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_fs2:
            st.markdown("""<div style="background:linear-gradient(145deg,#050d1f,#071a30);
            border:1px solid rgba(0,212,255,0.12);border-radius:10px;padding:14px;">
            <div style="font-size:0.8rem;font-weight:800;color:#00d4ff;margin-bottom:10px;
            display:flex;align-items:center;gap:6px;">🏛️ Balance Sheet</div>""",
            unsafe_allow_html=True)
            if bs:
                for k, v in bs.items():
                    if v is not None:
                        label = k.replace('_',' ').title()
                        st.markdown(f"""<div style="display:flex;justify-content:space-between;
                        padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.03);
                        font-size:0.75rem;">
                        <span style="color:#8b949e;">{label}</span>
                        <span style="color:#e8f4fd;font-weight:700;font-family:monospace;">
                        {curr_sym}{_fmt_inr(v)}</span></div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size:0.72rem;color:#556;">Data not available</div>',
                           unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_fs3:
            st.markdown("""<div style="background:linear-gradient(145deg,#050d1f,#071a30);
            border:1px solid rgba(0,212,255,0.12);border-radius:10px;padding:14px;">
            <div style="font-size:0.8rem;font-weight:800;color:#00d4ff;margin-bottom:10px;
            display:flex;align-items:center;gap:6px;">💵 Cash Flow</div>""",
            unsafe_allow_html=True)
            if cf:
                for k, v in cf.items():
                    if v is not None:
                        label = k.replace('_',' ').title()
                        # Color: green for positive CF, red for negative
                        cf_color = "#10b981" if v >= 0 else "#ef4444"
                        st.markdown(f"""<div style="display:flex;justify-content:space-between;
                        padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.03);
                        font-size:0.75rem;">
                        <span style="color:#8b949e;">{label}</span>
                        <span style="color:{cf_color};font-weight:700;font-family:monospace;">
                        {curr_sym}{_fmt_inr(v)}</span></div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size:0.72rem;color:#556;">Data not available</div>',
                           unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Industry + Economic Analysis ──
        st.markdown("")
        st.markdown("""<div class="sage-section-title">Industry & Economic Context</div>""",
                   unsafe_allow_html=True)

        ie_cols = st.columns(2)
        with ie_cols[0]:
            st.markdown(f"""<div class="sage-insight" style="height:100%;">
            <b>🏢 Sector:</b> {sector}<br>
            <b>Industry:</b> {industry}<br><br>
            Sector performance aur industry trends company ke growth ko directly affect karte hain.
            India mein {sector} sector ka growth rate aur government policies (PLI, FDI) monitor karo.
            Competition aur market share bhi check karo.
            </div>""", unsafe_allow_html=True)
        with ie_cols[1]:
            st.markdown(f"""<div class="sage-insight" style="height:100%;border-left-color:#ffd700;">
            <b>📈 Economic Factors:</b><br>
            • <b>GDP Growth:</b> India 6-7% — positive for equity<br>
            • <b>Inflation:</b> High inflation → RBI rate hikes → stock pressure<br>
            • <b>RBI Rates:</b> High rates = higher borrowing cost = lower profits<br>
            • <b>Global:</b> US Fed rates, crude oil, geo tensions affect {sector}<br><br>
            {sector} sector ke liye economic cycle aur policy environment critical hai.
            </div>""", unsafe_allow_html=True)

        # ── Management Quality ──
        officers = mg.get("officers", [])
        if officers:
            st.markdown("")
            st.markdown("""<div class="sage-section-title">Key Management</div>""",
                       unsafe_allow_html=True)
            for off in officers[:3]:
                title = off.get("title", "N/A")
                name = off.get("name", "N/A")
                st.markdown(f"""<div style="display:inline-block;background:rgba(0,212,255,0.06);
                border:1px solid rgba(0,212,255,0.15);border-radius:8px;
                padding:6px 12px;margin:3px;font-size:0.78rem;">
                <b style="color:#00d4ff;">{title}</b> — <span style="color:#b0cce0;">{name}</span>
                </div>""", unsafe_allow_html=True)

    # ── Raw JSON Expander ──────────────────────────────
    with st.expander("View Raw Analysis JSON (for developers)"):
        st.json(analysis)

    # ── SAGE CHAT — FULL WIDTH FOLLOW-UP SECTION ──────
    st.markdown("---")

    # Chat scroll CSS
    st.markdown("""<style>
    .sage-chat-scroll {
        max-height: 400px; overflow-y: auto; padding: 0.5rem;
        border: 1px solid rgba(0,212,255,0.1); border-radius: 12px;
        background: rgba(2,6,9,0.5); margin-bottom: 0.8rem;
    }
    .sage-chat-scroll::-webkit-scrollbar { width: 6px; }
    .sage-chat-scroll::-webkit-scrollbar-track { background: transparent; }
    .sage-chat-scroll::-webkit-scrollbar-thumb {
        background: rgba(0,212,255,0.2); border-radius: 3px;
    }
    </style>""", unsafe_allow_html=True)

    st.markdown("""<div class="sage-section-title" style="margin-top:20px;">
    Ask SAGE - Follow-up Questions</div>""", unsafe_allow_html=True)

    # Follow-up quick prompts as full-width buttons
    follow_ups = chat_exp.get("follow_up_prompts",[])
    if follow_ups:
        fu_cols = st.columns(min(3, len(follow_ups)))
        for i, prompt in enumerate(follow_ups[:6]):
            with fu_cols[i % 3]:
                btn_label = prompt[:35] + "..." if len(prompt) > 35 else prompt
                if st.button(btn_label, key=f"sage_fu_{i}",
                             use_container_width=True, help=prompt):
                    st.session_state.sage_chat_hist.append({"role":"user","content":prompt})
                    with st.spinner("SAGE is thinking..."):
                        reply = sage_chat_response(prompt, analysis, parsed)
                    st.session_state.sage_chat_hist.append({"role":"ai","content":reply})
                    st.rerun()

    # Chat history display — scrollable
    st.markdown('<div class="sage-chat-scroll">', unsafe_allow_html=True)
    for msg in st.session_state.sage_chat_hist:
        if msg["role"] == "user":
            st.markdown(f'<div class="sage-msg-user">{msg["content"]}</div>',
                       unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="sage-msg-ai">{msg["content"]}</div>',
                       unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Chat input - full width
    chat_col, chat_btn = st.columns([6, 1])
    with chat_col:
        chat_q = st.text_input("Ask about patterns, fundamentals, entry points...",
            placeholder="e.g. Candlestick patterns samjhao / P/E ratio kya bata raha hai?",
            key="sage_chat_q", label_visibility="collapsed")
    with chat_btn:
        if st.button("Ask SAGE", key="sage_chat_send", type="primary",
                     use_container_width=True):
            if chat_q.strip():
                st.session_state.sage_chat_hist.append({"role":"user","content":chat_q})
                with st.spinner("SAGE thinking..."):
                    reply = sage_chat_response(chat_q, analysis, parsed)
                st.session_state.sage_chat_hist.append({"role":"ai","content":reply})
                st.rerun()
