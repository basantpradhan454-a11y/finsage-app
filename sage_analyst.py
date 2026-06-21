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

    # If not found, try to extract a ticker-like word
    if not tv_sym:
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
# 4. AI ANALYSIS GENERATION (SAGE SYSTEM PROMPT)
# ══════════════════════════════════════════════════════
SAGE_SYSTEM = """Tu hai "SAGE Analyst" — FinSage ka AI Chart Analyst.

Tu HAMESHA valid JSON return karega — koi extra text nahi, sirf JSON.

JSON mein yeh fields hongi:
- symbol, timeframe, analysis_type
- draw_commands: support_levels, resistance_levels, trendlines, indicators, zones, patterns, current_price_analysis
- voice_script: segments array (each with segment number, duration_seconds, text, draw_action)
- chat_explanation: summary, bias, key_levels, indicators_summary, educational_insight, follow_up_prompts

Rules:
- Indian stocks: ₹ currency
- Hinglish voice script (Hindi + English mix)
- Har level ka reason batao
- Educational tone — koi direct buy/sell tip nahi
- Max 3 support + 3 resistance levels
- Voice total 60-90 seconds
- Disclaimer hamesha shamil karo"""

def generate_ai_analysis(parsed: dict, indicators: dict) -> dict | None:
    """Call Groq to generate SAGE analysis JSON."""
    sym  = parsed["tv_sym"] or parsed["display_name"]
    tf   = parsed["timeframe"]
    mode = parsed["mode"]

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
Detected Supports: {supp}
Detected Resistances: {res}

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
def generate_rule_based_analysis(parsed: dict, ind: dict) -> dict:
    """Generate analysis without AI when no API key."""
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
            ]
        }
    }

# ══════════════════════════════════════════════════════
# 6. TRADINGVIEW LIGHTWEIGHT CHART WITH DRAWINGS
# ══════════════════════════════════════════════════════
def build_chart_html(parsed: dict, analysis: dict, ohlcv: pd.DataFrame) -> str:
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
SAGE_CSS = """<style>
.sage-header {
  background:linear-gradient(135deg,#020609,#0a1220,#050010);
  border:1px solid rgba(0,212,255,0.25);border-radius:16px;
  padding:18px 22px;margin-bottom:16px;
}
.sage-title {
  font-size:1.3rem;font-weight:900;font-family:Orbitron,monospace;
  background:linear-gradient(90deg,#00d4ff,#a371f7);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
.sage-badge {
  display:inline-block;font-size:9px;font-weight:700;padding:2px 8px;
  border-radius:12px;margin-left:8px;
  background:rgba(0,255,136,0.1);color:#00ff88;
  border:1px solid rgba(0,255,136,0.3);
}
.sage-input-bar {
  background:#060f1e;border:1px solid rgba(0,212,255,0.2);
  border-radius:12px;padding:14px;margin-bottom:12px;
}
.sage-card {
  background:linear-gradient(145deg,#060f1e,#071525);
  border:1px solid rgba(0,212,255,0.14);border-radius:12px;padding:14px;margin:8px 0;
}
.sage-bias-box {
  display:inline-block;padding:6px 16px;border-radius:20px;
  font-size:1rem;font-weight:900;margin:6px 0;
}
.sage-level-row {
  display:flex;justify-content:space-between;align-items:center;
  padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);
  font-size:0.82rem;
}
.sage-indicator-chip {
  display:inline-block;padding:4px 10px;border-radius:8px;
  font-size:0.75rem;font-weight:600;margin:3px;
}
.sage-insight {
  background:#060f1e;border-left:3px solid #00d4ff;
  border-radius:0 8px 8px 0;padding:10px 14px;margin:8px 0;
  font-size:0.8rem;color:#c9d8ea;line-height:1.7;
}
.sage-disclaimer {
  background:rgba(255,170,0,0.06);border:1px solid rgba(255,170,0,0.2);
  border-radius:8px;padding:10px 14px;margin:10px 0;
  font-size:0.76rem;color:#ffaa00;
}
.sage-followup {
  background:#060f1e;border:1px solid rgba(0,212,255,0.1);
  border-radius:8px;padding:8px 12px;margin:4px 0;
  font-size:0.78rem;color:#4a9eff;cursor:pointer;
}
.sage-followup:hover { border-color:rgba(0,212,255,0.4); }
.sage-msg-user {
  background:rgba(74,158,255,0.1);border:1px solid rgba(74,158,255,0.2);
  border-radius:12px 12px 4px 12px;padding:10px 14px;margin:6px 0;
  font-size:0.85rem;color:#e8f4fd;max-width:85%;margin-left:auto;
}
.sage-msg-ai {
  background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.15);
  border-radius:4px 12px 12px 12px;padding:10px 14px;margin:6px 0;
  font-size:0.85rem;color:#c9d8ea;max-width:90%;line-height:1.6;
}
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

    system = f"""Tu SAGE Analyst hai. User ne {sym} ka analysis dekha:
Bias: {bias}
Key Levels: {json.dumps(levels)}
Indicators: {json.dumps(ind)}
Educational Insight: {json.dumps(chat.get('educational_insight',{}))}

User ke follow-up questions ka jawab do:
- Hinglish mein (Hindi + English mix)
- Educational tone — koi direct buy/sell tip nahi
- 100-200 words
- Specific levels aur indicators reference karo
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
    if "support" in q or "support kyun" in q:
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
    st.markdown("""<div class="sage-header">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <div>
        <span class="sage-title">🧠 SAGE Analyst</span>
        <span class="sage-badge">AI POWERED</span>
        <span class="sage-badge" style="background:rgba(123,47,247,0.1);color:#a371f7;border-color:rgba(123,47,247,0.3);">
        GROQ LLAMA 3.3</span>
      </div>
      <div style="margin-left:auto;text-align:right;">
        <div style="font-size:0.72rem;color:#8b949e;">Real-time Chart Analysis</div>
        <div style="font-size:0.68rem;color:#556;">Voice · Drawing · Education</div>
      </div>
    </div>
    <div style="font-size:0.78rem;color:#7fa8c9;margin-top:8px;">
    Koi bhi stock bolo → AI chart analyze karega, levels draw karega, aur voice mein samjhayega
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
            if parsed.get("yf_sym"):
                ohlcv = fetch_ohlcv(parsed["yf_sym"], parsed["timeframe"])
                if not ohlcv.empty:
                    ind = compute_indicators(ohlcv)

            # Try AI analysis first
            analysis = None
            if _groq_key() and ind:
                analysis = generate_ai_analysis(parsed, ind)

            # Fallback
            if not analysis and ind:
                analysis = generate_rule_based_analysis(parsed, ind)
            elif not analysis:
                # No data, no AI — minimal fallback
                parsed["tv_sym"] = parsed.get("tv_sym") or "NSE:RELIANCE"
                parsed["display_name"] = parsed.get("display_name") or user_input.title()
                ind = {"price":0,"rsi":50,"trend":"SIDEWAYS","ema20":0,"supports":[],"resistances":[],"vol_ratio":1.0,"macd_hist":0}
                analysis = generate_rule_based_analysis(parsed, ind)

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

    # ── CHART + VOICE ──────────────────────────────────
    col_chart, col_info = st.columns([3, 2])

    with col_chart:
        if ohlcv is not None and not (ohlcv.empty if hasattr(ohlcv,'empty') else True):
            chart_html = build_chart_html(parsed, analysis, ohlcv)
            components.html(chart_html, height=540, scrolling=False)
        else:
            # Fallback to TradingView embed
            tv_sym = parsed.get("tv_sym","NSE:RELIANCE")
            tf_tv  = {"5":"5","15":"15","60":"60","240":"240","D":"D","W":"W","M":"M"}.get(
                      parsed.get("timeframe","D"),"D")
            tv_html = f"""<div style="background:#020609;border-radius:10px;overflow:hidden;height:480px;">
            <iframe src="https://www.tradingview.com/widgetbar-chart-only/?symbol={tv_sym}&interval={tf_tv}&theme=dark&style=1&locale=en&toolbar_bg=020609&hide_side_toolbar=false&allow_symbol_change=false&saveimage=false&calendar=false&hotlist=false&details=false&news=false"
            width="100%" height="480" frameborder="0" scrolling="no" allowtransparency="true"></iframe></div>"""
            components.html(tv_html, height=500, scrolling=False)

        # Voice panel
        if voice_seg:
            voice_html = build_voice_html(voice_seg)
            components.html(voice_html, height=260, scrolling=False)

    with col_info:
        # Bias + Summary
        bias       = chat_exp.get("bias","NEUTRAL")
        bias_color = chat_exp.get("bias_color","#f59e0b")
        summary    = chat_exp.get("summary","Analysis")

        st.markdown(f"""<div class="sage-card">
        <div style="font-size:0.72rem;color:#8b949e;text-transform:uppercase;
        letter-spacing:0.5px;">SAGE Analysis — {analysis.get('timeframe','Daily')}</div>
        <div style="font-size:1.1rem;font-weight:800;color:#e8f4fd;margin:4px 0;">{summary}</div>
        <div class="sage-bias-box" style="background:{bias_color}1a;
        color:{bias_color};border:1px solid {bias_color}44;">{bias}</div>
        </div>""", unsafe_allow_html=True)

        # Key Levels
        levels = chat_exp.get("key_levels",{})
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

        # Indicators
        st.write("")
        ind_sum = chat_exp.get("indicators_summary",{})
        if ind_sum:
            st.markdown("**📊 Indicators**")
            for key, val in ind_sum.items():
                color = "#10b981" if "bull" in str(val).lower() else ("#ef4444" if "bear" in str(val).lower() else "#7fa8c9")
                st.markdown(f"""<span class="sage-indicator-chip"
                style="background:{color}1a;color:{color};
                border:1px solid {color}33;">{key.upper()}: {str(val)[:40]}</span>""",
                unsafe_allow_html=True)

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

    # ── Raw JSON Expander ──────────────────────────────
    with st.expander("🔢 View Raw Analysis JSON (for developers)"):
        st.json(analysis)

    # ── SAGE CHAT ──────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💬 Ask SAGE — Follow-up Questions")

    # Follow-up prompts
    follow_ups = chat_exp.get("follow_up_prompts",[])
    if follow_ups:
        fu_cols = st.columns(min(4, len(follow_ups)))
        for i, prompt in enumerate(follow_ups[:4]):
            with fu_cols[i]:
                if st.button(prompt[:30]+"..." if len(prompt)>30 else prompt,
                             key=f"sage_fu_{i}", use_container_width=True):
                    st.session_state.sage_chat_hist.append({"role":"user","content":prompt})
                    with st.spinner("SAGE is thinking..."):
                        reply = sage_chat_response(prompt, analysis, parsed)
                    st.session_state.sage_chat_hist.append({"role":"ai","content":reply})
                    st.rerun()

    # Chat history
    for msg in st.session_state.sage_chat_hist:
        if msg["role"] == "user":
            st.markdown(f'<div class="sage-msg-user">👤 {msg["content"]}</div>',
                       unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="sage-msg-ai">🧠 {msg["content"]}</div>',
                       unsafe_allow_html=True)

    # Chat input
    chat_col, chat_btn = st.columns([5, 1])
    with chat_col:
        chat_q = st.text_input("",
            placeholder="Yeh support kyun important hai? / Entry kahan milegi? / MACD samjhao...",
            key="sage_chat_q", label_visibility="collapsed")
    with chat_btn:
        if st.button("Ask", key="sage_chat_send", type="primary",
                     use_container_width=True):
            if chat_q.strip():
                st.session_state.sage_chat_hist.append({"role":"user","content":chat_q})
                with st.spinner("🧠 SAGE thinking..."):
                    reply = sage_chat_response(chat_q, analysis, parsed)
                st.session_state.sage_chat_hist.append({"role":"ai","content":reply})
                st.rerun()
