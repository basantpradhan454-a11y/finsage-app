"""
FinsageAI — Advanced Market Analyzer
Technical Indicators (Pure Pandas — No TA-Lib) + Groq AI Signal Generation
100% Free — yfinance + CoinGecko + Groq (free tier)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import requests
import json
import time
from datetime import datetime, timedelta

# ── Groq API Config ───────────────────────────────────────────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_groq_key() -> str:
    """Try GROW_API_KEY first (user-saved name), then GROQ_API_KEY."""
    import os
    # Try st.secrets first (Streamlit Cloud)
    for key_name in ("GROW_API_KEY", "GROQ_API_KEY"):
        try:
            v = st.secrets.get(key_name, "")
            if v: return v
        except Exception:
            pass
        v = os.environ.get(key_name, "")
        if v: return v
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlcv(symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV data with retry + caching."""
    symbol = symbol.upper().strip()
    for attempt in range(3):
        try:
            df = yf.Ticker(symbol).history(period=period, interval=interval)
            if not df.empty:
                df.index = pd.to_datetime(df.index)
                return df
            time.sleep(1)
        except Exception:
            time.sleep(1.5)
    return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_info(symbol: str) -> dict:
    """Fetch company/asset info with graceful fallback."""
    try:
        info = yf.Ticker(symbol.upper()).info
        return {
            "name":           info.get("longName", symbol),
            "sector":         info.get("sector", "N/A"),
            "market_cap":     info.get("marketCap", 0),
            "pe_ratio":       info.get("trailingPE"),
            "week52_high":    info.get("fiftyTwoWeekHigh"),
            "week52_low":     info.get("fiftyTwoWeekLow"),
            "avg_volume":     info.get("averageVolume", 0),
            "dividend_yield": info.get("dividendYield", 0),
            "beta":           info.get("beta"),
            "currency":       info.get("currency", "USD"),
            "country":        info.get("country", "N/A"),
            "industry":       info.get("industry", "N/A"),
        }
    except Exception:
        return {"name": symbol, "sector": "N/A", "currency": "USD"}


# ═══════════════════════════════════════════════════════════════════════════════
# TECHNICAL INDICATORS — Pure Pandas (No TA-Lib required)
# ═══════════════════════════════════════════════════════════════════════════════

def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).round(2)


def calc_macd(close: pd.Series, fast=12, slow=26, sig=9):
    ema_fast   = close.ewm(span=fast, adjust=False).mean()
    ema_slow   = close.ewm(span=slow, adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_ln  = macd_line.ewm(span=sig, adjust=False).mean()
    histogram  = macd_line - signal_ln
    return macd_line.round(4), signal_ln.round(4), histogram.round(4)


def calc_bb(close: pd.Series, period=20, std=2.0):
    sma   = close.rolling(period).mean()
    sigma = close.rolling(period).std()
    return (sma + sigma * std).round(2), sma.round(2), (sma - sigma * std).round(2)


def calc_ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean().round(2)


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean().round(4)


def calc_stoch(high: pd.Series, low: pd.Series, close: pd.Series, k=14, d=3):
    ll  = low.rolling(k).min()
    hh  = high.rolling(k).max()
    pct_k = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    return pct_k.round(2), pct_k.rolling(d).mean().round(2)


def calc_vwap(high: pd.Series, low: pd.Series, close: pd.Series, vol: pd.Series) -> pd.Series:
    tp = (high + low + close) / 3
    return ((tp * vol).cumsum() / vol.cumsum()).round(2)


def calc_adx(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> pd.Series:
    plus_dm  = high.diff().clip(lower=0)
    minus_dm = low.diff().abs().clip(lower=0)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr      = tr.ewm(com=period-1, min_periods=period).mean()
    plus_di  = 100 * plus_dm.ewm(com=period-1, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(com=period-1, min_periods=period).mean() / atr
    dx       = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(com=period-1, min_periods=period).mean().round(2)


def calc_obv(close: pd.Series, vol: pd.Series) -> pd.Series:
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (vol * direction).cumsum()


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Attach all indicators to OHLCV dataframe."""
    if df.empty or len(df) < 26:
        return df
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]

    # Trend
    df["EMA_9"]   = calc_ema(c, 9)
    df["EMA_20"]  = calc_ema(c, 20)
    df["EMA_50"]  = calc_ema(c, 50)
    df["EMA_200"] = calc_ema(c, 200)

    # Momentum
    df["RSI"]         = calc_rsi(c)
    df["MACD"], df["MACD_Sig"], df["MACD_Hist"] = calc_macd(c)
    df["Stoch_K"], df["Stoch_D"] = calc_stoch(h, l, c)

    # Volatility
    df["BB_Up"], df["BB_Mid"], df["BB_Lo"] = calc_bb(c)
    df["ATR"]      = calc_atr(h, l, c)
    df["BB_Width"] = ((df["BB_Up"] - df["BB_Lo"]) / df["BB_Mid"] * 100).round(2)
    df["%B"]       = ((c - df["BB_Lo"]) / (df["BB_Up"] - df["BB_Lo"])).round(4)

    # Volume
    df["VWAP"]      = calc_vwap(h, l, c, v)
    df["OBV"]       = calc_obv(c, v)
    df["Vol_Ratio"] = (v / v.rolling(20).mean()).round(2)

    # Trend strength
    df["ADX"]  = calc_adx(h, l, c)

    # Price change
    df["Chg_1d"]  = c.pct_change(1).round(4)
    df["Chg_5d"]  = c.pct_change(5).round(4)
    df["Chg_20d"] = c.pct_change(20).round(4)

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL ENGINE — Rule-based scoring -100 to +100
# ═══════════════════════════════════════════════════════════════════════════════

def generate_signals(df: pd.DataFrame) -> dict:
    """Score all indicators and produce overall signal."""
    if df.empty or len(df) < 30:
        return {"score": 0, "overall": "NEUTRAL", "signals": []}

    row  = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 2 else row
    sigs = []
    score = 0

    def s(indicator, signal, value, note, pts):
        nonlocal score
        sigs.append({"indicator": indicator, "signal": signal, "value": value, "note": note})
        score += pts

    close = float(row.get("Close", 0))

    # ── RSI ──
    rsi = float(row.get("RSI", 50))
    if rsi < 30:   s("RSI", "STRONG BUY",  f"{rsi:.1f}", "Oversold (<30)", +20)
    elif rsi < 40: s("RSI", "BUY",         f"{rsi:.1f}", "Approaching oversold", +10)
    elif rsi > 70: s("RSI", "STRONG SELL", f"{rsi:.1f}", "Overbought (>70)", -20)
    elif rsi > 60: s("RSI", "SELL",        f"{rsi:.1f}", "Approaching overbought", -10)
    else:          s("RSI", "NEUTRAL",     f"{rsi:.1f}", "Mid-range", 0)

    # ── MACD ──
    macd      = float(row.get("MACD", 0))
    macd_sig  = float(row.get("MACD_Sig", 0))
    macd_hist = float(row.get("MACD_Hist", 0))
    prev_hist = float(prev.get("MACD_Hist", 0))
    prev_macd = float(prev.get("MACD", 0))
    prev_ms   = float(prev.get("MACD_Sig", 0))

    if macd > macd_sig and prev_macd <= prev_ms:
        s("MACD", "BUY",  f"{macd:.4f}", "Bullish crossover ✅", +20)
    elif macd < macd_sig and prev_macd >= prev_ms:
        s("MACD", "SELL", f"{macd:.4f}", "Bearish crossover ❌", -20)
    elif macd_hist > 0 and macd_hist > prev_hist:
        s("MACD", "BUY",  f"{macd:.4f}", "Bullish momentum rising", +10)
    elif macd_hist < 0 and macd_hist < prev_hist:
        s("MACD", "SELL", f"{macd:.4f}", "Bearish momentum rising", -10)
    else:
        s("MACD", "NEUTRAL", f"{macd:.4f}", "No clear signal", 0)

    # ── Bollinger Bands ──
    pct_b    = float(row.get("%B", 0.5))
    bb_width = float(row.get("BB_Width", 10))
    if pct_b < 0.05:   s("BB", "STRONG BUY",  f"%B:{pct_b:.2f}", "Price at lower band", +15)
    elif pct_b > 0.95: s("BB", "STRONG SELL", f"%B:{pct_b:.2f}", "Price at upper band", -15)
    elif bb_width < 5: s("BB", "WATCH",        f"Width:{bb_width:.1f}%", "Squeeze — breakout incoming ⚡", 0)
    else:              s("BB", "NEUTRAL",       f"%B:{pct_b:.2f}", "Inside bands", 0)

    # ── EMA Trend ──
    e20  = float(row.get("EMA_20", close))
    e50  = float(row.get("EMA_50", close))
    e200 = float(row.get("EMA_200", close))
    if close > e20 > e50:   s("EMA Trend", "BUY",  "Price>EMA20>EMA50", "Short-term uptrend", +10)
    elif close < e20 < e50: s("EMA Trend", "SELL", "Price<EMA20<EMA50", "Short-term downtrend", -10)
    if close > e200:        s("EMA 200",   "BUY",  "Price>EMA200", "Long-term bullish", +10)
    else:                   s("EMA 200",   "SELL", "Price<EMA200", "Long-term bearish", -10)

    # ── Volume ──
    vol_ratio = float(row.get("Vol_Ratio", 1.0))
    chg_1d    = float(row.get("Chg_1d", 0))
    if vol_ratio > 2.0 and chg_1d > 0:  s("Volume", "BUY",  f"{vol_ratio:.1f}x avg", "High-vol breakout 🚀", +10)
    elif vol_ratio > 2.0 and chg_1d < 0: s("Volume","SELL", f"{vol_ratio:.1f}x avg", "High-vol breakdown ⬇️", -10)

    # ── ADX ──
    adx = float(row.get("ADX", 0))
    if adx > 25: s("ADX", "TRENDING", f"{adx:.1f}", "Strong trend", 0)
    elif adx < 20: s("ADX", "RANGING", f"{adx:.1f}", "Weak trend / range-bound", 0)

    # ── Stochastic ──
    sk = float(row.get("Stoch_K", 50))
    sd = float(row.get("Stoch_D", 50))
    if sk < 20 and sd < 20:   s("Stochastic", "BUY",  f"K:{sk:.0f} D:{sd:.0f}", "Oversold zone", +10)
    elif sk > 80 and sd > 80: s("Stochastic", "SELL", f"K:{sk:.0f} D:{sd:.0f}", "Overbought zone", -10)

    # ── VWAP ──
    vwap = float(row.get("VWAP", 0))
    if vwap > 0:
        if close > vwap:   s("VWAP", "BUY",  f"${close:.2f} > ${vwap:.2f}", "Price above VWAP", +5)
        else:              s("VWAP", "SELL", f"${close:.2f} < ${vwap:.2f}", "Price below VWAP", -5)

    # ── Final ──
    score = max(-100, min(100, score))
    if score >= 40:    overall = "STRONG BUY"
    elif score >= 15:  overall = "BUY"
    elif score <= -40: overall = "STRONG SELL"
    elif score <= -15: overall = "SELL"
    else:              overall = "NEUTRAL / HOLD"

    return {
        "score":         score,
        "overall":       overall,
        "signals":       sigs,
        "latest_price":  round(close, 4),
        "rsi":           round(rsi, 1),
        "macd":          round(macd, 4),
        "macd_hist":     round(macd_hist, 4),
        "atr":           round(float(row.get("ATR", 0)), 4),
        "adx":           round(adx, 1),
        "vol_ratio":     round(vol_ratio, 2),
        "stoch_k":       round(sk, 1),
        "bb_width":      round(bb_width, 2),
        "pct_b":         round(pct_b, 4),
        "ema_200":       round(e200, 2),
        "vwap":          round(vwap, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SUPPORT / RESISTANCE
# ═══════════════════════════════════════════════════════════════════════════════

def find_support_resistance(df: pd.DataFrame, window: int = 10) -> dict:
    if df.empty or len(df) < window * 2:
        return {"support": [], "resistance": []}
    rolling_max = df["High"].rolling(window=window, center=True).max()
    rolling_min = df["Low"].rolling(window=window, center=True).min()
    resistance  = sorted(set([round(v, 2) for v in df["High"][df["High"] == rolling_max].tail(5).tolist()]))
    support     = sorted(set([round(v, 2) for v in df["Low"][df["Low"] == rolling_min].tail(5).tolist()]))
    return {"support": support[-3:], "resistance": resistance[-3:]}


# ═══════════════════════════════════════════════════════════════════════════════
# GROQ AI ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def get_groq_analysis(symbol: str, tech: dict, info: dict, df: pd.DataFrame) -> dict:
    """Call Groq AI (free Llama 3.3 70B) for natural language analysis."""
    api_key = get_groq_key()

    row = df.iloc[-1] if not df.empty else {}
    chg5  = float(row.get("Chg_5d",  0)) * 100 if not df.empty else 0
    chg20 = float(row.get("Chg_20d", 0)) * 100 if not df.empty else 0

    sig_lines = "\n".join([
        f"  - {s['indicator']}: {s['signal']} | {s['value']} | {s['note']}"
        for s in tech.get("signals", [])
    ])

    prompt = f"""You are a professional stock/crypto analyst. Analyze and give a precise trading recommendation.

ASSET: {symbol}
Name: {info.get('name', symbol)} | Sector: {info.get('sector', 'N/A')}
PE Ratio: {info.get('pe_ratio', 'N/A')} | Beta: {info.get('beta', 'N/A')} | Currency: {info.get('currency','USD')}

TECHNICAL SNAPSHOT:
Price: {tech.get('latest_price')} | RSI: {tech.get('rsi')} | MACD Hist: {tech.get('macd_hist')}
ADX: {tech.get('adx')} | ATR: {tech.get('atr')} | BB %B: {tech.get('pct_b')}
Volume vs 20d avg: {tech.get('vol_ratio')}x | Stoch K: {tech.get('stoch_k')}
5d change: {chg5:.1f}% | 20d change: {chg20:.1f}%
EMA200: {tech.get('ema_200')} | VWAP: {tech.get('vwap')}

INDICATOR SIGNALS:
{sig_lines}

Technical Score: {tech.get('score')}/100 → Rule signal: {tech.get('overall')}

Respond ONLY in this exact JSON (no markdown, no explanation outside JSON):
{{
  "recommendation": "STRONG BUY / BUY / HOLD / SELL / STRONG SELL",
  "confidence": "HIGH / MEDIUM / LOW",
  "entry_price": "price or range",
  "stop_loss": "price",
  "target_1": "price",
  "target_2": "price",
  "risk_reward": "1:X",
  "timeframe": "SHORT TERM (days) / MEDIUM TERM (weeks) / LONG TERM (months)",
  "reasoning": "3-4 sentence explanation",
  "key_risks": "2-3 risks",
  "key_catalysts": "2-3 catalysts",
  "pattern_detected": "chart pattern if any, else None"
}}"""

    if not api_key:
        return _rule_based_fallback(tech, symbol)

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model":       "llama-3.3-70b-versatile",
                "messages":    [{"role": "user", "content": prompt}],
                "temperature": 0.25,
                "max_tokens":  900,
            },
            timeout=20,
        )
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            result["source"] = "Groq AI — Llama 3.3 70B (Free)"
            return result
        else:
            return _rule_based_fallback(tech, symbol)
    except Exception:
        return _rule_based_fallback(tech, symbol)


def _rule_based_fallback(tech: dict, symbol: str) -> dict:
    """Fallback when no Groq key — pure rule-based output."""
    score   = tech.get("score", 0)
    overall = tech.get("overall", "NEUTRAL")
    price   = tech.get("latest_price", 0)
    atr     = tech.get("atr", price * 0.02) or price * 0.02
    conf    = "HIGH" if abs(score) >= 40 else ("MEDIUM" if abs(score) >= 15 else "LOW")

    sl_dist = 1.5 * atr
    tp_dist = sl_dist * 2.0
    is_buy  = "BUY" in overall

    sl = round(price - sl_dist if is_buy else price + sl_dist, 4)
    t1 = round(price + tp_dist if is_buy else price - tp_dist, 4)
    t2 = round(price + tp_dist * 1.5 if is_buy else price - tp_dist * 1.5, 4)

    return {
        "recommendation":   overall,
        "confidence":       conf,
        "entry_price":      str(price),
        "stop_loss":        str(sl),
        "target_1":         str(t1),
        "target_2":         str(t2),
        "risk_reward":      "1:2",
        "timeframe":        "SHORT TERM (days)",
        "reasoning":        (
            f"Rule-based score: {score}/100. RSI at {tech.get('rsi','N/A')}, "
            f"ADX trend strength {tech.get('adx','N/A')}, "
            f"Volume ratio {tech.get('vol_ratio','N/A')}x average. "
            f"Add GROW_API_KEY in Streamlit Secrets for full AI analysis."
        ),
        "key_risks":        "Macro events, earnings surprise, low liquidity",
        "key_catalysts":    "Volume breakout, sector momentum, technical breakout",
        "pattern_detected": "None",
        "source":           "Rule-based engine (Add GROW_API_KEY to Streamlit Secrets for Groq AI)",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FULL ANALYSIS PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def run_full_analysis(symbol: str, period: str = "3mo") -> dict:
    """
    Complete pipeline:
    1. Fetch OHLCV
    2. Calculate all indicators
    3. Generate technical signals
    4. Get AI recommendation (Groq or rule-based fallback)
    5. Find support/resistance levels
    """
    sym = symbol.upper().strip()
    df  = fetch_ohlcv(sym, period=period)
    if df.empty:
        return {"error": f"No data found for '{sym}'. Check symbol spelling."}

    df      = add_all_indicators(df)
    tech    = generate_signals(df)
    info    = fetch_info(sym)
    ai_rec  = get_groq_analysis(sym, tech, info, df)
    sr      = find_support_resistance(df)

    return {
        "symbol":     sym,
        "df":         df,
        "tech":       tech,
        "info":       info,
        "ai":         ai_rec,
        "sr":         sr,
        "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error":      None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STREAMLIT UI — Full Advanced Analyzer Page
# ═══════════════════════════════════════════════════════════════════════════════

def render_advanced_analyzer():
    """Main Streamlit page for the Advanced Analyzer."""
    import plotly.graph_objects as go
    from config import LOGO_URL

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(5,0,20,0.95));
    border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1rem;
    box-shadow:0 0 30px rgba(0,212,255,0.06),inset 0 1px 0 rgba(0,212,255,0.08);">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:40px;border-radius:8px;object-fit:contain;
            filter:drop-shadow(0 0 8px rgba(0,212,255,0.3));">
            <div>
                <div style="font-size:1.15rem;font-weight:800;
                background:linear-gradient(90deg,#00d4ff,#a371f7);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                font-family:Orbitron,monospace;">📡 Advanced Market Analyzer</div>
                <div style="color:#8b949e;font-size:0.75rem;">
                10+ Indicators · Groq AI Signals · Support/Resistance · Pure Pandas
                </div>
            </div>
            <div style="margin-left:auto;display:flex;flex-direction:column;gap:0.3rem;align-items:flex-end;">
                <span style="background:rgba(0,255,136,0.1);color:#00ff88;
                padding:0.15rem 0.7rem;border-radius:20px;font-size:0.65rem;font-weight:700;
                border:1px solid rgba(0,255,136,0.25);">✅ FREE — No TA-Lib</span>
                <span style="background:rgba(110,64,201,0.1);color:#a371f7;
                padding:0.12rem 0.6rem;border-radius:20px;font-size:0.62rem;font-weight:600;
                border:1px solid rgba(110,64,201,0.2);">🤖 Groq Llama 3.3 70B</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Input ─────────────────────────────────────────────────────────────────
    col_inp, col_per, col_btn = st.columns([3, 1, 1])
    with col_inp:
        symbol = st.text_input(
            "Enter Symbol",
            placeholder="e.g. AAPL, RELIANCE.NS, BTC-USD, TSLA, INFY.NS",
            label_visibility="collapsed",
            key="adv_symbol"
        )
    with col_per:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"],
                              index=1, label_visibility="collapsed", key="adv_period")
    with col_btn:
        analyze = st.button("🔍 Analyze", type="primary", use_container_width=True, key="adv_go")

    # Quick picks
    quick = ["AAPL","TSLA","NVDA","RELIANCE.NS","TCS.NS","BTC-USD","ETH-USD","NIFTY50.NS"]
    cols  = st.columns(len(quick))
    for i, sym in enumerate(quick):
        with cols[i]:
            if st.button(sym, key=f"adv_q_{sym}", use_container_width=True):
                st.session_state["adv_symbol"] = sym
                st.rerun()

    sym_to_run = symbol or st.session_state.get("adv_symbol", "")
    if not sym_to_run and not analyze:
        st.info("👆 Enter a ticker symbol or click a quick pick to start analysis.")
        return

    if sym_to_run:
        with st.spinner(f"⚡ Analyzing {sym_to_run.upper()} — fetching data + running 10 indicators..."):
            result = run_full_analysis(sym_to_run, period=period)

        if result.get("error"):
            st.error(f"❌ {result['error']}")
            return

        df   = result["df"]
        tech = result["tech"]
        info = result["info"]
        ai   = result["ai"]
        sr   = result["sr"]
        sym  = result["symbol"]

        # ── AI Recommendation Card ────────────────────────────────────────────
        rec = ai.get("recommendation", "NEUTRAL")
        conf = ai.get("confidence", "MEDIUM")
        rec_colors = {
            "STRONG BUY": "#00ff88", "BUY": "#4a9eff",
            "HOLD": "#f0c040", "NEUTRAL / HOLD": "#f0c040",
            "SELL": "#ff8c42", "STRONG SELL": "#ff4466",
        }
        rc = rec_colors.get(rec, "#8b949e")
        rec_emojis = {
            "STRONG BUY":"🚀","BUY":"📈","HOLD":"⏸️",
            "NEUTRAL / HOLD":"⏸️","SELL":"📉","STRONG SELL":"🔻"
        }
        em = rec_emojis.get(rec, "•")

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(0,20,40,0.9),rgba(5,0,30,0.85));
        border:2px solid {rc}33;border-radius:14px;padding:1.3rem 1.5rem;margin-bottom:0.8rem;">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.7rem;">
                <div>
                    <div style="color:#8b949e;font-size:0.72rem;font-weight:700;letter-spacing:0.1em;
                    font-family:Orbitron,monospace;">AI RECOMMENDATION — {ai.get('source','')}</div>
                    <div style="font-size:2rem;font-weight:900;color:{rc};
                    font-family:Orbitron,monospace;letter-spacing:0.05em;">{em} {rec}</div>
                    <div style="color:#8b949e;font-size:0.8rem;margin-top:0.2rem;">
                    Confidence: <b style="color:{rc};">{conf}</b> &nbsp;|&nbsp;
                    Timeframe: <b style="color:#4a9eff;">{ai.get('timeframe','N/A')}</b> &nbsp;|&nbsp;
                    R:R: <b style="color:#a371f7;">{ai.get('risk_reward','N/A')}</b>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.6rem;min-width:280px;">
                    <div style="background:rgba(0,255,136,0.08);border:1px solid rgba(0,255,136,0.2);
                    border-radius:8px;padding:0.5rem 0.7rem;text-align:center;">
                        <div style="color:#8b949e;font-size:0.62rem;">ENTRY</div>
                        <div style="color:#00ff88;font-weight:700;font-size:0.88rem;">{"₹" if sym.endswith(".NS") or sym.endswith(".BO") else "$"}{ai.get('entry_price','N/A')}</div>
                    </div>
                    <div style="background:rgba(255,68,102,0.08);border:1px solid rgba(255,68,102,0.2);
                    border-radius:8px;padding:0.5rem 0.7rem;text-align:center;">
                        <div style="color:#8b949e;font-size:0.62rem;">STOP LOSS</div>
                        <div style="color:#ff4466;font-weight:700;font-size:0.88rem;">{"₹" if sym.endswith(".NS") or sym.endswith(".BO") else "$"}{ai.get('stop_loss','N/A')}</div>
                    </div>
                    <div style="background:rgba(74,158,255,0.08);border:1px solid rgba(74,158,255,0.2);
                    border-radius:8px;padding:0.5rem 0.7rem;text-align:center;">
                        <div style="color:#8b949e;font-size:0.62rem;">TARGET 1</div>
                        <div style="color:#4a9eff;font-weight:700;font-size:0.88rem;">{"₹" if sym.endswith(".NS") or sym.endswith(".BO") else "$"}{ai.get('target_1','N/A')}</div>
                    </div>
                </div>
            </div>
            <div style="margin-top:0.8rem;padding-top:0.8rem;
            border-top:1px solid rgba(255,255,255,0.06);font-size:0.82rem;color:#c9d1d9;line-height:1.6;">
                💬 {ai.get('reasoning','N/A')}
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-top:0.6rem;font-size:0.78rem;">
                <div style="color:#8b949e;">⚠️ Risks: <span style="color:#ff8c42;">{ai.get('key_risks','N/A')}</span></div>
                <div style="color:#8b949e;">🚀 Catalysts: <span style="color:#00ff88;">{ai.get('key_catalysts','N/A')}</span></div>
            </div>
            {"<div style='margin-top:0.4rem;font-size:0.78rem;color:#8b949e;'>🔍 Pattern: <span style='color:#a371f7;'>"+ai.get('pattern_detected','None')+"</span></div>" if ai.get('pattern_detected') and ai.get('pattern_detected') != 'None' else ""}
        </div>
        """, unsafe_allow_html=True)

        # ── Key Metrics Row ───────────────────────────────────────────────────
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        score = tech.get("score", 0)
        sc_color = "#00ff88" if score > 0 else ("#ff4466" if score < 0 else "#f0c040")

        _is_indian = sym.endswith(".NS") or sym.endswith(".BO")
        _curr_sym  = "₹" if _is_indian else "$"
        _price_val = tech.get('latest_price', 0)
        _price_fmt = f"{_curr_sym}{_price_val:,.2f}" if _price_val > 1 else f"{_curr_sym}{_price_val:,.4f}"
        m1.metric("💰 Price", _price_fmt)
        m2.metric("📊 RSI",      f"{tech.get('rsi',0):.1f}",
                  delta="Oversold" if tech.get('rsi',50) < 30 else ("Overbought" if tech.get('rsi',50) > 70 else "Neutral"))
        m3.metric("📈 ADX",      f"{tech.get('adx',0):.1f}",
                  delta="Trending" if tech.get('adx',0) > 25 else "Ranging")
        m4.metric("⚡ ATR",       f"{tech.get('atr',0):.4f}")
        m5.metric("📦 Vol Ratio", f"{tech.get('vol_ratio',0):.1f}x")
        m6.metric("🎯 Score",     f"{score}/100")

        # ── Chart with Indicators ─────────────────────────────────────────────
        st.markdown("---")
        tab_c, tab_i, tab_sr, tab_raw = st.tabs([
            "📊 Price + Indicators", "📋 Signal Table",
            "🎯 Support / Resistance", "🔢 Raw Data"
        ])

        with tab_c:
            fig = go.Figure()

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"],
                name=sym, increasing_line_color="#00ff88",
                decreasing_line_color="#ff4466",
                increasing_fillcolor="rgba(0,255,136,0.2)",
                decreasing_fillcolor="rgba(255,68,102,0.2)",
            ))

            # EMAs
            for ema, color in [("EMA_20","#4a9eff"),("EMA_50","#f0c040"),("EMA_200","#a371f7")]:
                if ema in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df.index, y=df[ema], name=ema.replace("_"," "),
                        line=dict(color=color, width=1.5, dash="dot"),
                        opacity=0.8,
                    ))

            # Bollinger Bands
            for col, name, clr in [("BB_Up","BB Upper","rgba(163,113,247,0.4)"),
                                    ("BB_Lo","BB Lower","rgba(163,113,247,0.4)")]:
                if col in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df.index, y=df[col], name=name,
                        line=dict(color=clr, width=1, dash="dash"), opacity=0.6,
                    ))

            # VWAP
            if "VWAP" in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df["VWAP"], name="VWAP",
                    line=dict(color="#ff8c42", width=1.5), opacity=0.7,
                ))

            # Support / Resistance lines
            for r in sr.get("resistance", []):
                fig.add_hline(y=r, line_color="#ff4466", line_width=1,
                              line_dash="dot", opacity=0.5,
                              annotation_text=f"R: {r}", annotation_font_color="#ff4466",
                              annotation_font_size=9)
            for s_ in sr.get("support", []):
                fig.add_hline(y=s_, line_color="#00ff88", line_width=1,
                              line_dash="dot", opacity=0.5,
                              annotation_text=f"S: {s_}", annotation_font_color="#00ff88",
                              annotation_font_size=9)

            fig.update_layout(
                plot_bgcolor="#020609", paper_bgcolor="#020609",
                font=dict(color="#c9d1d9", family="monospace"),
                xaxis=dict(gridcolor="#0d1117", showgrid=True, rangeslider_visible=False),
                yaxis=dict(gridcolor="#0d1117", showgrid=True),
                legend=dict(bgcolor="rgba(0,0,0,0)", font_size=10),
                margin=dict(l=0, r=0, t=10, b=0), height=420,
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Volume sub-chart
            vol_colors = ["#00ff88" if c >= o else "#ff4466"
                          for c, o in zip(df["Close"], df["Open"])]
            fig_v = go.Figure(go.Bar(
                x=df.index, y=df["Volume"], name="Volume",
                marker_color=vol_colors, opacity=0.7,
            ))
            if "VWAP" in df.columns:
                fig_v.add_trace(go.Scatter(
                    x=df.index, y=df["Vol_Ratio"] * df["Volume"].mean(),
                    name="Vol Ratio×", line=dict(color="#f0c040", width=1.5),
                ))
            fig_v.update_layout(
                plot_bgcolor="#020609", paper_bgcolor="#020609",
                font=dict(color="#c9d1d9"),
                xaxis=dict(gridcolor="#0d1117"),
                yaxis=dict(gridcolor="#0d1117", title="Volume"),
                height=150, margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False,
            )
            st.plotly_chart(fig_v, use_container_width=True)

        with tab_i:
            # Signal table
            sigs = tech.get("signals", [])
            if sigs:
                sig_colors = {
                    "STRONG BUY": "🟢🟢", "BUY": "🟢",
                    "STRONG SELL": "🔴🔴", "SELL": "🔴",
                    "NEUTRAL": "⚪", "WATCH": "🟡", "TRENDING": "🔵", "RANGING": "🔘"
                }
                rows = []
                for s in sigs:
                    rows.append({
                        "Signal": sig_colors.get(s["signal"], "•") + " " + s["signal"],
                        "Indicator": s["indicator"],
                        "Value": s["value"],
                        "Note": s["note"],
                    })
                df_sig = pd.DataFrame(rows)
                st.dataframe(df_sig, use_container_width=True, hide_index=True,
                             column_config={
                                 "Signal":    st.column_config.TextColumn("Signal", width="medium"),
                                 "Indicator": st.column_config.TextColumn("Indicator", width="medium"),
                                 "Value":     st.column_config.TextColumn("Value", width="medium"),
                                 "Note":      st.column_config.TextColumn("Analysis Note", width="large"),
                             })

            # Score gauge
            st.markdown("**📊 Overall Technical Score**")
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=score,
                delta={"reference": 0, "valueformat": "+d"},
                gauge={
                    "axis": {"range": [-100, 100]},
                    "bar":  {"color": sc_color},
                    "steps": [
                        {"range": [-100,-30], "color": "rgba(255,68,102,0.2)"},
                        {"range": [-30,30],   "color": "rgba(240,192,64,0.1)"},
                        {"range": [30,100],   "color": "rgba(0,255,136,0.2)"},
                    ],
                    "threshold": {"line": {"color": sc_color, "width": 3}, "value": score},
                },
                title={"text": tech.get("overall"), "font": {"color": sc_color, "size": 14}},
                number={"font": {"color": sc_color}},
            ))
            fig_g.update_layout(
                paper_bgcolor="#020609", font_color="#c9d1d9",
                height=250, margin=dict(l=20, r=20, t=10, b=0),
            )
            st.plotly_chart(fig_g, use_container_width=True)

        with tab_sr:
            st.markdown("### 🎯 Key Support & Resistance Levels")
            sr_c1, sr_c2 = st.columns(2)
            with sr_c1:
                st.markdown("**🔴 Resistance Levels**")
                for r in reversed(sr.get("resistance", [])):
                    st.markdown(f"""
                    <div style="background:rgba(255,68,102,0.08);border:1px solid rgba(255,68,102,0.3);
                    border-radius:8px;padding:0.5rem 1rem;margin:0.3rem 0;
                    font-size:0.88rem;color:#ff4466;font-weight:700;font-family:monospace;">
                    🔴  ${r:,.4f}
                    </div>""", unsafe_allow_html=True)
                if not sr.get("resistance"):
                    st.caption("Not enough data")
            with sr_c2:
                st.markdown("**🟢 Support Levels**")
                for s_ in sr.get("support", []):
                    st.markdown(f"""
                    <div style="background:rgba(0,255,136,0.08);border:1px solid rgba(0,255,136,0.3);
                    border-radius:8px;padding:0.5rem 1rem;margin:0.3rem 0;
                    font-size:0.88rem;color:#00ff88;font-weight:700;font-family:monospace;">
                    🟢  ${s_:,.4f}
                    </div>""", unsafe_allow_html=True)
                if not sr.get("support"):
                    st.caption("Not enough data")

            # Target 2 card
            if ai.get("target_2"):
                st.markdown(f"""
                <div style="background:rgba(74,158,255,0.06);border:1px solid rgba(74,158,255,0.2);
                border-radius:10px;padding:0.8rem 1rem;margin-top:0.8rem;font-size:0.85rem;color:#c9d1d9;">
                🎯 <b>AI Target 2:</b> <span style="color:#4a9eff;font-weight:700;">{ai.get('target_2')}</span>
                &nbsp;&nbsp; <b>R:R Ratio:</b> <span style="color:#a371f7;">{ai.get('risk_reward')}</span>
                </div>
                """, unsafe_allow_html=True)

        with tab_raw:
            st.markdown("**📊 OHLCV + All Indicators (Last 20 rows)**")
            display_cols = ["Open","High","Low","Close","Volume",
                            "RSI","MACD","MACD_Hist","BB_Up","BB_Lo",
                            "EMA_20","EMA_50","EMA_200","ATR","ADX",
                            "Stoch_K","Vol_Ratio","%B"]
            show_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(
                df[show_cols].tail(20).round(4),
                use_container_width=True,
            )

        # ── Stock Info Row ────────────────────────────────────────────────────
        st.markdown("---")
        i1, i2, i3, i4, i5 = st.columns(5)
        i1.metric("🏢 Sector",   info.get("sector","N/A"))
        i2.metric("💹 P/E",      f"{info.get('pe_ratio'):.1f}x" if info.get("pe_ratio") else "N/A")
        i3.metric("📐 Beta",     f"{info.get('beta'):.2f}" if info.get("beta") else "N/A")
        i4.metric("📅 52W High", f"${info.get('week52_high'):,.2f}" if info.get("week52_high") else "N/A")
        i5.metric("📅 52W Low",  f"${info.get('week52_low'):,.2f}" if info.get("week52_low") else "N/A")

        # Timestamp + disclaimer
        st.caption(f"⏰ Analysis generated: {result['timestamp']} | Data: yfinance | AI: {ai.get('source','Rule-based')}")
        st.markdown("""
        <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
        border-radius:8px;padding:0.5rem 0.9rem;margin-top:0.5rem;font-size:0.73rem;color:#8b949e;">
        ⚠️ <b style="color:#d29922;">Disclaimer:</b> For educational purposes only. Not investment advice.
        Always do your own research. Past performance does not guarantee future results.
        SEBI: Consult a SEBI-registered advisor before investing.
        </div>
        """, unsafe_allow_html=True)
