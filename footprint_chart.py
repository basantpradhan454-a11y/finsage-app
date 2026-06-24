"""
FinSage AI — Footprint Chart + Order Flow Analysis
AI-powered analysis of candlestick patterns, volume profile,
support/resistance, indicators — all shown inside a TradingView-style view.
"""

import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import requests
from datetime import datetime

try:
    from ticker_resolver import resolve_ticker
except ImportError:
    def resolve_ticker(x): return x

# ── Groq config ──────────────────────────────────────────────────────────────
def _groq_key():
    try:
        return st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY","")
    except Exception:
        return os.environ.get("GROQ_API_KEY","")

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Data fetch ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _fetch_data(sym: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.Ticker(sym).history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()

# ── Technical indicators ──────────────────────────────────────────────────────
def _compute_indicators(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 20:
        return {}
    c = df["Close"].values.astype(float)
    h = df["High"].values.astype(float)
    l = df["Low"].values.astype(float)
    v = df["Volume"].values.astype(float)

    # RSI
    delta = np.diff(c); up = np.where(delta>0, delta, 0); dn = np.where(delta<0, -delta, 0)
    def _ema(arr, n):
        out = np.zeros_like(arr); out[0] = arr[:n].mean()
        a = 2/(n+1)
        for i in range(1, len(arr)): out[i] = arr[i]*a + out[i-1]*(1-a)
        return out
    if len(up) >= 14:
        avg_up = _ema(up, 14); avg_dn = _ema(dn, 14)
        rs = np.where(avg_dn==0, 100, avg_up/avg_dn)
        rsi_arr = 100 - 100/(1+rs)
        rsi = float(rsi_arr[-1])
    else:
        rsi = 50.0

    # EMA
    def ema_series(arr, n):
        s = pd.Series(arr)
        return s.ewm(span=n, adjust=False).mean().values
    ema20 = float(ema_series(c, 20)[-1])
    ema50 = float(ema_series(c, 50)[-1]) if len(c) >= 50 else float(c.mean())
    ema200= float(ema_series(c, 200)[-1]) if len(c) >= 200 else float(c.mean())

    # MACD
    ema12 = ema_series(c, 12); ema26 = ema_series(c, 26)
    macd  = ema12 - ema26
    signal_line = ema_series(macd, 9)
    macd_hist = float(macd[-1] - signal_line[-1])
    macd_val  = float(macd[-1])

    # ATR
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    atr = float(tr[-14:].mean()) if len(tr) >= 14 else float(tr.mean())

    # VWAP (recent 20 bars)
    tp = (h + l + c) / 3
    cum_tpv = np.cumsum(tp[-20:] * v[-20:])
    cum_v   = np.cumsum(v[-20:])
    vwap = float(cum_tpv[-1] / cum_v[-1]) if cum_v[-1] > 0 else float(c[-1])

    # Volume analysis
    avg_vol = float(v[-20:].mean())
    cur_vol = float(v[-1])
    vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0

    # Support/Resistance (pivot-based)
    def find_pivots(data, window=5):
        pivots = []
        for i in range(window, len(data)-window):
            if all(data[i] >= data[i-j] for j in range(1,window+1)) and \
               all(data[i] >= data[i+j] for j in range(1,window+1)):
                pivots.append(("R", float(data[i]), i))
            elif all(data[i] <= data[i-j] for j in range(1,window+1)) and \
                 all(data[i] <= data[i+j] for j in range(1,window+1)):
                pivots.append(("S", float(data[i]), i))
        return pivots

    pivots = find_pivots(c)
    supports    = sorted([p[1] for p in pivots if p[0]=="S" and p[1] < c[-1]], reverse=True)[:3]
    resistances = sorted([p[1] for p in pivots if p[0]=="R" and p[1] > c[-1]])[:3]

    # Bollinger Bands
    sma20 = float(pd.Series(c).rolling(20).mean().iloc[-1])
    std20 = float(pd.Series(c).rolling(20).std().iloc[-1])
    bb_upper = sma20 + 2*std20
    bb_lower = sma20 - 2*std20

    # Trend
    if c[-1] > ema20 > ema50:
        trend = "BULLISH"
    elif c[-1] < ema20 < ema50:
        trend = "BEARISH"
    else:
        trend = "SIDEWAYS"

    # Stochastic RSI
    rsi_series = []
    for i in range(14, len(c)):
        d2 = np.diff(c[max(0,i-14):i+1])
        u2 = np.where(d2>0,d2,0); d3=np.where(d2<0,-d2,0)
        if len(u2) >= 1:
            au = u2.mean(); ad = d3.mean()
            rs2 = au/ad if ad > 0 else 100
            rsi_series.append(100 - 100/(1+rs2))
    if len(rsi_series) >= 14:
        rsi_min = min(rsi_series[-14:]); rsi_max = max(rsi_series[-14:])
        stoch_rsi = (rsi_series[-1]-rsi_min)/(rsi_max-rsi_min)*100 if rsi_max != rsi_min else 50
    else:
        stoch_rsi = 50.0

    return {
        "price":      float(c[-1]),
        "open":       float(df["Open"].iloc[-1]),
        "high":       float(h[-1]),
        "low":        float(l[-1]),
        "volume":     cur_vol,
        "rsi":        rsi,
        "ema20":      ema20,
        "ema50":      ema50,
        "ema200":     ema200,
        "macd":       macd_val,
        "macd_hist":  macd_hist,
        "atr":        atr,
        "vwap":       vwap,
        "vol_ratio":  vol_ratio,
        "avg_vol":    avg_vol,
        "supports":   supports,
        "resistances":resistances,
        "trend":      trend,
        "bb_upper":   bb_upper,
        "bb_lower":   bb_lower,
        "sma20":      sma20,
        "stoch_rsi":  stoch_rsi,
    }

# ── Candlestick pattern detection ─────────────────────────────────────────────
def _detect_patterns(df: pd.DataFrame) -> list:
    if df.empty or len(df) < 5:
        return []
    patterns = []
    rows = df.tail(10)
    closes = rows["Close"].values.astype(float)
    opens  = rows["Open"].values.astype(float)
    highs  = rows["High"].values.astype(float)
    lows   = rows["Low"].values.astype(float)

    for i in range(1, len(closes)):
        o1,h1,l1,c1 = opens[i-1],highs[i-1],lows[i-1],closes[i-1]
        o2,h2,l2,c2 = opens[i],  highs[i],  lows[i],  closes[i]
        body1 = abs(c1-o1); body2 = abs(c2-o2)
        rng2  = h2-l2 if h2-l2 > 0 else 0.0001

        # Doji
        if body2 < rng2*0.1:
            patterns.append({"name":"Doji","type":"NEUTRAL","bar":i,"desc":"Indecision candle — open ≈ close, wait for confirmation"})
        # Hammer
        lower_wick = min(o2,c2)-l2; upper_wick = h2-max(o2,c2)
        if lower_wick > body2*2 and upper_wick < body2*0.5 and c2 > o2:
            patterns.append({"name":"Hammer","type":"BULLISH","bar":i,"desc":"Bullish reversal — long lower wick shows buyer strength"})
        # Shooting Star
        if upper_wick > body2*2 and lower_wick < body2*0.5 and c2 < o2:
            patterns.append({"name":"Shooting Star","type":"BEARISH","bar":i,"desc":"Bearish reversal — rejected at highs"})
        # Bullish Engulfing
        if c1 < o1 and c2 > o2 and o2 < c1 and c2 > o1 and body2 > body1:
            patterns.append({"name":"Bullish Engulfing","type":"BULLISH","bar":i,"desc":"Strong bullish reversal — bulls engulf previous bearish candle"})
        # Bearish Engulfing
        if c1 > o1 and c2 < o2 and o2 > c1 and c2 < o1 and body2 > body1:
            patterns.append({"name":"Bearish Engulfing","type":"BEARISH","bar":i,"desc":"Strong bearish reversal — bears engulf previous bullish candle"})
        # Morning Star (3-candle)
        if i >= 2:
            o0,c0 = opens[i-2],closes[i-2]; body0=abs(c0-o0)
            if c0<o0 and body1<body0*0.3 and c2>o2 and c2>=(o0+c0)/2:
                patterns.append({"name":"Morning Star","type":"BULLISH","bar":i,"desc":"3-candle bullish reversal at bottom"})
        # Evening Star
        if i >= 2:
            o0,c0=opens[i-2],closes[i-2]; body0=abs(c0-o0)
            if c0>o0 and body1<body0*0.3 and c2<o2 and c2<=(o0+c0)/2:
                patterns.append({"name":"Evening Star","type":"BEARISH","bar":i,"desc":"3-candle bearish reversal at top"})
        # Marubozu (strong trend candle)
        if body2/rng2 > 0.9 and c2 > o2:
            patterns.append({"name":"Bullish Marubozu","type":"BULLISH","bar":i,"desc":"Strong bullish momentum — nearly no wicks"})
        if body2/rng2 > 0.9 and c2 < o2:
            patterns.append({"name":"Bearish Marubozu","type":"BEARISH","bar":i,"desc":"Strong bearish momentum — nearly no wicks"})
        # Spinning Top
        if 0.1 < body2/rng2 < 0.3 and lower_wick > body2*0.7 and upper_wick > body2*0.7:
            patterns.append({"name":"Spinning Top","type":"NEUTRAL","bar":i,"desc":"Indecision — equal wicks, small body"})
        # Dragonfly Doji
        if body2 < rng2*0.05 and lower_wick > rng2*0.7:
            patterns.append({"name":"Dragonfly Doji","type":"BULLISH","bar":i,"desc":"Bullish signal at support — buyers pushed price back up"})
        # Gravestone Doji
        if body2 < rng2*0.05 and upper_wick > rng2*0.7:
            patterns.append({"name":"Gravestone Doji","type":"BEARISH","bar":i,"desc":"Bearish signal at resistance — sellers pushed price back down"})

    seen = set()
    unique = []
    for p in patterns:
        if p["name"] not in seen:
            seen.add(p["name"]); unique.append(p)
    return unique[:8]

# ── Volume profile (footprint-style) ─────────────────────────────────────────
def _build_volume_profile(df: pd.DataFrame, bins: int = 20) -> list:
    if df.empty:
        return []
    price_min = float(df["Low"].min())
    price_max = float(df["High"].max())
    if price_max <= price_min:
        return []
    bin_size = (price_max - price_min) / bins
    profile = []
    for i in range(bins):
        low_b  = price_min + i*bin_size
        high_b = low_b + bin_size
        mid    = (low_b + high_b) / 2
        mask   = (df["Low"] <= high_b) & (df["High"] >= low_b)
        vol    = float(df.loc[mask, "Volume"].sum())
        profile.append({"price": round(mid, 2), "vol": vol,
                        "low": round(low_b,2), "high": round(high_b,2)})
    return sorted(profile, key=lambda x: x["vol"], reverse=True)

# ── AI analysis via Groq ──────────────────────────────────────────────────────
def _ai_footprint_analysis(sym: str, ind: dict, patterns: list, vol_profile: list) -> dict:
    key = _groq_key()
    if not key:
        return _rule_based_footprint(sym, ind, patterns)

    top_vols = vol_profile[:3] if vol_profile else []
    pattern_names = [p["name"] for p in patterns[:4]]

    prompt = f"""You are SAGE, an elite trading AI. Analyze this stock/crypto and provide a complete footprint chart analysis.

Symbol: {sym}
Current Price: {ind.get('price',0):.4f}
RSI: {ind.get('rsi',50):.1f}
EMA20: {ind.get('ema20',0):.4f} | EMA50: {ind.get('ema50',0):.4f}
MACD Histogram: {ind.get('macd_hist',0):.4f}
ATR: {ind.get('atr',0):.4f}
VWAP: {ind.get('vwap',0):.4f}
Volume Ratio: {ind.get('vol_ratio',1):.2f}x (vs 20-day avg)
Trend: {ind.get('trend','NEUTRAL')}
Stochastic RSI: {ind.get('stoch_rsi',50):.1f}
BB Upper: {ind.get('bb_upper',0):.4f} | BB Lower: {ind.get('bb_lower',0):.4f}
Support Levels: {ind.get('supports',[])}
Resistance Levels: {ind.get('resistances',[])}
Detected Patterns: {pattern_names}
High Volume Price Zones: {[f"{v['price']} (vol:{v['vol']/1e6:.1f}M)" for v in top_vols]}

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "overall_bias": "BULLISH/BEARISH/NEUTRAL",
  "bias_color": "#10b981 or #ef4444 or #f59e0b",
  "confidence": 75,
  "summary": "2-line summary in Hindi+English mix",
  "entry_zone": {{"price": 0, "reason": "why here"}},
  "stop_loss": {{"price": 0, "reason": "invalidation level"}},
  "targets": [{{"price": 0, "label": "T1", "reason": ""}}, {{"price": 0, "label": "T2", "reason": ""}}],
  "risk_reward": "1:2.5",
  "trade_quality": "EXCELLENT/GOOD/AVERAGE/POOR",
  "key_observations": [
    "RSI/MACD/trend observation",
    "Volume profile observation",
    "Support/resistance observation",
    "Pattern observation"
  ],
  "indicator_signals": {{
    "RSI": "Oversold — bounce likely",
    "MACD": "Bullish crossover",
    "EMA": "Price above 20/50 EMA — bullish",
    "Volume": "High volume confirmation",
    "VWAP": "Above VWAP — bullish",
    "BB": "Near lower band — mean reversion setup"
  }},
  "footprint_insight": "What the order flow / volume profile tells us",
  "multi_timeframe": {{
    "daily": "Daily trend observation",
    "hourly": "Hourly structure",
    "intraday": "15-min momentum"
  }},
  "risk_note": "Key risk to watch"
}}"""

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": [{"role":"user","content":prompt}],
                  "temperature": 0.2, "max_tokens": 1200},
            timeout=20
        )
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        # strip markdown
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:   raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)
    except Exception:
        return _rule_based_footprint(sym, ind, patterns)


def _rule_based_footprint(sym: str, ind: dict, patterns: list) -> dict:
    p = ind.get("price", 0)
    rsi = ind.get("rsi", 50)
    trend = ind.get("trend","SIDEWAYS")
    vol_ratio = ind.get("vol_ratio", 1.0)
    supports = ind.get("supports", [])
    resistances = ind.get("resistances", [])

    if trend == "BULLISH" and rsi < 70:
        bias = "BULLISH"; bc = "#10b981"
    elif trend == "BEARISH" and rsi > 30:
        bias = "BEARISH"; bc = "#ef4444"
    else:
        bias = "NEUTRAL"; bc = "#f59e0b"

    entry = supports[0] if supports else p*0.99
    sl    = supports[1] if len(supports)>1 else p*0.97
    t1    = resistances[0] if resistances else p*1.03
    t2    = resistances[1] if len(resistances)>1 else p*1.06

    rr_val = (t1-entry)/(entry-sl) if entry-sl > 0 else 1.0
    tq = "EXCELLENT" if rr_val >= 2.5 else "GOOD" if rr_val >= 1.5 else "AVERAGE" if rr_val >= 1.0 else "POOR"

    return {
        "overall_bias": bias, "bias_color": bc, "confidence": 65,
        "summary": f"{sym} — {bias} trend. RSI {rsi:.0f}, trend {trend}, volume {vol_ratio:.1f}x avg.",
        "entry_zone": {"price": round(entry, 4), "reason": "Near support level"},
        "stop_loss":  {"price": round(sl, 4), "reason": "Below key support"},
        "targets": [{"price": round(t1,4),"label":"T1","reason":"Next resistance"},
                    {"price": round(t2,4),"label":"T2","reason":"Extended target"}],
        "risk_reward": f"1:{rr_val:.1f}",
        "trade_quality": tq,
        "key_observations": [
            f"RSI at {rsi:.0f} — {'oversold, bounce likely' if rsi<40 else 'overbought, caution' if rsi>70 else 'neutral zone'}",
            f"Volume {vol_ratio:.1f}x average — {'high conviction' if vol_ratio>1.5 else 'below average, low conviction'}",
            f"Trend: {trend} — EMA20 {'>' if p>ind.get('ema20',p) else '<'} EMA50",
            f"Patterns: {', '.join([x['name'] for x in patterns[:3]]) or 'None detected'}"
        ],
        "indicator_signals": {
            "RSI": f"{rsi:.0f} — {'Oversold' if rsi<40 else 'Overbought' if rsi>70 else 'Neutral'}",
            "MACD": "Bullish" if ind.get("macd_hist",0) > 0 else "Bearish",
            "EMA": f"Price {'above' if p > ind.get('ema20',p) else 'below'} EMA20",
            "Volume": f"{vol_ratio:.1f}x avg — {'Confirmed' if vol_ratio>1.2 else 'Weak'}",
            "VWAP": f"{'Above' if p > ind.get('vwap',p) else 'Below'} VWAP",
            "BB": f"{'Near upper band' if p > ind.get('bb_upper',p)*0.98 else 'Near lower band' if p < ind.get('bb_lower',p)*1.02 else 'Mid-band'}"
        },
        "footprint_insight": f"Highest volume near {ind.get('supports',[p])[0]:.2f} — strong support zone",
        "multi_timeframe": {
            "daily": f"Daily trend: {trend}",
            "hourly": "Hourly: Refer to 1H chart",
            "intraday": "15-min: Refer to intraday chart"
        },
        "risk_note": "Always confirm with broader market conditions before trading"
    }

# ── Build chart HTML ──────────────────────────────────────────────────────────
def _build_footprint_html(df: pd.DataFrame, ind: dict, ai_res: dict,
                           patterns: list, vol_profile: list, sym: str) -> str:
    candle_data, vol_data, vp_data = [], [], []

    if not df.empty:
        for idx, row in df.tail(120).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            candle_data.append({"time":ts,
                "open":round(float(row["Open"]),4),  "high":round(float(row["High"]),4),
                "low": round(float(row["Low"]),4),   "close":round(float(row["Close"]),4)})
            is_up = float(row["Close"]) >= float(row["Open"])
            vol_data.append({"time":ts, "value":int(row["Volume"]),
                             "color":"rgba(16,185,129,0.35)" if is_up else "rgba(239,68,68,0.35)"})

    for vp in vol_profile[:15]:
        vp_data.append({"price":vp["price"], "vol":vp["vol"]})

    max_vol = max([v["vol"] for v in vp_data], default=1)
    bias_color = ai_res.get("bias_color","#f59e0b")
    entry_p = ai_res.get("entry_zone",{}).get("price",0)
    sl_p    = ai_res.get("stop_loss",{}).get("price",0)
    targets = ai_res.get("targets",[])
    t1_p    = targets[0]["price"] if targets else 0
    t2_p    = targets[1]["price"] if len(targets)>1 else 0
    supports    = ind.get("supports",[])
    resistances = ind.get("resistances",[])
    vwap_p      = ind.get("vwap",0)
    ema20_p     = ind.get("ema20",0)
    ema50_p     = ind.get("ema50",0)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ background:#131722; font-family:'Trebuchet MS',sans-serif; color:#d1d4dc; overflow:hidden; }}
#wrap {{ display:flex; width:100vw; height:100vh; }}
#chart-side {{ flex:1; position:relative; min-width:0; }}
#chart {{ width:100%; height:calc(100vh - 30px); }}
#footer {{ height:30px; background:#1e222d; border-top:1px solid #2a2e39;
           display:flex; align-items:center; padding:0 12px; gap:20px; font-size:11px; }}
#vp-side {{ width:72px; background:#0e1117; border-left:1px solid #2a2e39;
            display:flex; flex-direction:column; overflow:hidden; }}
.vp-bar {{ display:flex; align-items:center; flex:1; padding:0 4px; border-bottom:1px solid #13161e; }}
.vp-fill {{ height:70%; background:rgba(41,98,255,0.35); border-radius:1px; transition:width 0.3s; }}
.vp-price {{ font-size:8px; color:#4a5568; margin-left:3px; white-space:nowrap; }}
/* Legend overlay */
#legend {{ position:absolute; top:8px; left:8px; z-index:10;
           background:rgba(19,23,34,0.92); border:1px solid #2a2e39;
           border-radius:8px; padding:8px 12px; min-width:160px; max-width:220px; }}
#legend .sym {{ font-size:13px; font-weight:700; color:#d1d4dc; }}
#legend .price {{ font-size:18px; font-weight:900; color:{bias_color}; font-family:monospace; }}
#legend .bias {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:700;
                 background:{bias_color}22; color:{bias_color}; border:1px solid {bias_color}44; margin-top:3px; }}
/* Levels panel */
#levels {{ position:absolute; top:8px; right:80px; z-index:10;
           background:rgba(19,23,34,0.92); border:1px solid #2a2e39;
           border-radius:8px; padding:8px 12px; max-width:175px; }}
#levels .lh {{ font-size:10px; font-weight:700; color:#6a6e7a; margin-bottom:4px; text-transform:uppercase; }}
#levels .lr {{ font-size:11px; display:flex; justify-content:space-between; gap:8px; margin:2px 0; }}
</style>
</head>
<body>
<div id="wrap">
  <div id="chart-side">
    <div id="legend">
      <div class="sym">{sym}</div>
      <div class="price">{ind.get('price',0):.4f}</div>
      <div class="bias">{ai_res.get('overall_bias','NEUTRAL')} · {ai_res.get('confidence',65)}%</div>
    </div>
    <div id="levels">
      <div class="lh">AI Levels</div>
      <div class="lr"><span style="color:#26a69a;">Entry</span><span style="color:#26a69a;font-family:monospace;">{entry_p:.4f}</span></div>
      <div class="lr"><span style="color:#ef5350;">Stop</span><span style="color:#ef5350;font-family:monospace;">{sl_p:.4f}</span></div>
      {f'<div class="lr"><span style="color:#2962ff;">T1</span><span style="color:#2962ff;font-family:monospace;">{t1_p:.4f}</span></div>' if t1_p else ''}
      {f'<div class="lr"><span style="color:#9c27b0;">T2</span><span style="color:#9c27b0;font-family:monospace;">{t2_p:.4f}</span></div>' if t2_p else ''}
      <div class="lr" style="margin-top:4px;"><span style="color:#6a6e7a;font-size:9px;">R:R</span><span style="font-size:10px;font-weight:700;">{ai_res.get('risk_reward','—')}</span></div>
    </div>
    <div id="chart"></div>
    <div id="footer">
      <span>RSI: <b>{ind.get('rsi',50):.0f}</b></span>
      <span>MACD: <b style="color:{'#26a69a' if ind.get('macd_hist',0)>0 else '#ef5350'}">{'▲' if ind.get('macd_hist',0)>0 else '▼'}</b></span>
      <span>Vol: <b>{ind.get('vol_ratio',1):.1f}x</b></span>
      <span>ATR: <b>{ind.get('atr',0):.4f}</b></span>
      <span>VWAP: <b>{vwap_p:.4f}</b></span>
      <span style="color:{bias_color};">R:R {ai_res.get('risk_reward','—')} · {ai_res.get('trade_quality','—')}</span>
    </div>
  </div>
  <div id="vp-side">
    {''.join([f'<div class="vp-bar"><div class="vp-fill" style="width:{min(vp["vol"]/max_vol*100,100):.0f}%"></div><span class="vp-price">{vp["price"]:.0f}</span></div>' for vp in sorted(vp_data, key=lambda x:x["price"], reverse=True)[:18]])}
  </div>
</div>

<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
const candles = {json.dumps(candle_data)};
const vols    = {json.dumps(vol_data)};
const supp    = {json.dumps(supports)};
const res     = {json.dumps(resistances)};

const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
  width:  document.getElementById('chart-side').clientWidth,
  height: window.innerHeight - 30,
  layout: {{ background:{{color:'#131722'}}, textColor:'#d1d4dc' }},
  grid:   {{ vertLines:{{color:'rgba(255,255,255,0.03)'}}, horzLines:{{color:'rgba(255,255,255,0.03)'}} }},
  crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
  rightPriceScale: {{ borderColor:'#2a2e39' }},
  timeScale: {{ borderColor:'#2a2e39', timeVisible:true, secondsVisible:false }},
}});

const cs = chart.addCandlestickSeries({{
  upColor:'#26a69a', downColor:'#ef5350',
  borderUpColor:'#26a69a', borderDownColor:'#ef5350',
  wickUpColor:'#26a69a', wickDownColor:'#ef5350',
}});
if (candles.length) cs.setData(candles);

const vs = chart.addHistogramSeries({{
  priceScaleId:'vol', scaleMargins:{{top:0.8,bottom:0}},
}});
if (vols.length) vs.setData(vols);

// Support lines
supp.forEach(function(s) {{
  cs.createPriceLine({{ price:s, color:'#26a69a', lineWidth:1,
    lineStyle:LightweightCharts.LineStyle.Dashed, axisLabelVisible:true, title:'S' }});
}});
// Resistance lines
res.forEach(function(r) {{
  cs.createPriceLine({{ price:r, color:'#ef5350', lineWidth:1,
    lineStyle:LightweightCharts.LineStyle.Dashed, axisLabelVisible:true, title:'R' }});
}});
// Entry, SL, T1, T2
if ({entry_p}) cs.createPriceLine({{ price:{entry_p}, color:'#26a69a', lineWidth:2,
  lineStyle:LightweightCharts.LineStyle.Solid, axisLabelVisible:true, title:'ENTRY' }});
if ({sl_p}) cs.createPriceLine({{ price:{sl_p}, color:'#ef5350', lineWidth:2,
  lineStyle:LightweightCharts.LineStyle.Solid, axisLabelVisible:true, title:'STOP' }});
if ({t1_p}) cs.createPriceLine({{ price:{t1_p}, color:'#2962ff', lineWidth:1,
  lineStyle:LightweightCharts.LineStyle.Dashed, axisLabelVisible:true, title:'T1' }});
if ({t2_p}) cs.createPriceLine({{ price:{t2_p}, color:'#9c27b0', lineWidth:1,
  lineStyle:LightweightCharts.LineStyle.Dashed, axisLabelVisible:true, title:'T2' }});
// VWAP
if ({vwap_p}) cs.createPriceLine({{ price:{vwap_p}, color:'#fbbf24', lineWidth:1,
  lineStyle:LightweightCharts.LineStyle.Dotted, axisLabelVisible:true, title:'VWAP' }});
// EMA20, EMA50
if ({ema20_p}) cs.createPriceLine({{ price:{ema20_p}, color:'#2196f3', lineWidth:1,
  lineStyle:LightweightCharts.LineStyle.Solid, axisLabelVisible:false, title:'EMA20' }});
if ({ema50_p}) cs.createPriceLine({{ price:{ema50_p}, color:'#ff9800', lineWidth:1,
  lineStyle:LightweightCharts.LineStyle.Solid, axisLabelVisible:false, title:'EMA50' }});

chart.timeScale().fitContent();
window.addEventListener('resize', function() {{
  chart.applyOptions({{
    width:  document.getElementById('chart-side').clientWidth,
    height: window.innerHeight - 30,
  }});
}});
</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════
# MAIN RENDER
# ══════════════════════════════════════════════════════
def render_footprint_chart():
    # Full page CSS — remove sidebar, maximize chart
    st.markdown("""<style>
    header[data-testid="stHeader"], footer,
    div[data-testid="stDecoration"], div[data-testid="stToolbar"],
    div[data-testid="stStatusWidget"], .stDeployButton {
        display:none !important;
    }
    .block-container {
        padding-top:0.3rem !important;
        padding-left:0.3rem !important;
        padding-right:0.3rem !important;
        max-width:100vw !important;
    }
    </style>""", unsafe_allow_html=True)

    # ── Header bar ───────────────────────────────────────────────────────────
    h1, h2, h3 = st.columns([3, 2, 1])
    with h1:
        st.markdown("""<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:8px;
        padding:8px 14px;display:flex;align-items:center;gap:8px;">
          <span style="color:#2962ff;font-size:18px;">⬡</span>
          <span style="color:#d1d4dc;font-weight:700;font-size:14px;">SAGE Footprint Chart</span>
          <span style="background:#2962ff22;color:#2962ff;font-size:9px;padding:2px 7px;
          border-radius:10px;border:1px solid #2962ff44;font-weight:700;">AI POWERED</span>
          <span style="background:#26a69a22;color:#26a69a;font-size:9px;padding:2px 7px;
          border-radius:10px;border:1px solid #26a69a44;font-weight:700;">🔴 LIVE</span>
        </div>""", unsafe_allow_html=True)
    with h2:
        sym_raw = st.text_input("", placeholder="apple, TSLA, RELIANCE, BTC...",
                                 key="fp_sym", label_visibility="collapsed")
    with h3:
        tf_choice = st.selectbox("", ["1D","1H","15m","5m","1W"],
                                  key="fp_tf", label_visibility="collapsed")

    tf_map = {"1D":("1y","1d"), "1H":("1mo","1h"), "15m":("5d","15m"),
              "5m":("2d","5m"), "1W":("2y","1wk")}

    # Quick symbols
    qcols = st.columns(10)
    quick = ["BTC","ETH","RELIANCE","TCS","AAPL","TSLA","NVDA","NIFTY","INFY","HDFC"]
    for i, q in enumerate(quick):
        with qcols[i]:
            if st.button(q, key=f"fp_q_{i}", use_container_width=True):
                st.session_state.fp_selected = q
                st.rerun()

    sym_input = st.session_state.get("fp_selected", "") or sym_raw or "RELIANCE.NS"
    sym = resolve_ticker(sym_input.strip())

    # ── Two-panel layout: Big Chart + Analysis ───────────────────────────────
    chart_col, panel_col = st.columns([3, 1], gap="small")

    with chart_col:
        period, interval = tf_map.get(tf_choice, ("1y","1d"))

        with st.spinner(f"Loading {sym}..."):
            df = _fetch_data(sym, period, interval)

        if df.empty:
            st.error(f"❌ No data for `{sym}`. Try a different symbol.")
            return

        ind      = _compute_indicators(df)
        patterns = _detect_patterns(df)
        vp       = _build_volume_profile(df)

        # AI analysis
        cache_key = f"fp_ai_{sym}_{tf_choice}"
        if st.session_state.get(cache_key) is None or st.button("🔄 Refresh AI", key="fp_refresh"):
            with st.spinner("SAGE AI analyzing..."):
                ai_res = _ai_footprint_analysis(sym, ind, patterns, vp)
            st.session_state[cache_key] = ai_res
        else:
            ai_res = st.session_state[cache_key]

        # Build and render chart — FULLSCREEN height
        chart_html = _build_footprint_html(df, ind, ai_res, patterns, vp, sym)
        components.html(chart_html, height=720, scrolling=False)

    with panel_col:
        _render_fp_panel(ind, ai_res, patterns, vp, sym)


def _render_fp_panel(ind: dict, ai_res: dict, patterns: list, vp: list, sym: str):
    """Right-side analysis panel — TradingView style."""
    bias_color = ai_res.get("bias_color","#f59e0b")

    st.markdown(f"""<style>
    .fp-panel {{ background:#131722; border:1px solid #2a2e39; border-radius:8px; padding:10px; }}
    .fp-section-title {{ color:#6a6e7a; font-size:10px; font-weight:700;
        text-transform:uppercase; letter-spacing:0.1em; margin:10px 0 5px 0; }}
    .fp-row {{ display:flex; justify-content:space-between; padding:4px 0;
               border-bottom:1px solid #1a1e2d; font-size:12px; }}
    .fp-pattern-chip {{ display:inline-block; padding:3px 8px; border-radius:12px;
        font-size:10px; font-weight:600; margin:2px; }}
    </style>""", unsafe_allow_html=True)

    # Bias card
    rr = ai_res.get("risk_reward","—")
    tq = ai_res.get("trade_quality","—")
    tq_color = {"EXCELLENT":"#26a69a","GOOD":"#2962ff","AVERAGE":"#f59e0b","POOR":"#ef5350"}.get(tq,"#6a6e7a")
    conf = ai_res.get("confidence",65)

    st.markdown(f"""<div style="background:{bias_color}11;border:1px solid {bias_color}33;
    border-radius:8px;padding:12px;margin-bottom:8px;text-align:center;">
      <div style="font-size:22px;font-weight:900;color:{bias_color};">{ai_res.get('overall_bias','NEUTRAL')}</div>
      <div style="color:#6a6e7a;font-size:10px;margin:3px 0;">Confidence: {conf}%</div>
      <div style="background:#0e1117;border-radius:100px;height:5px;margin:4px 0;">
        <div style="background:{bias_color};height:5px;border-radius:100px;width:{conf}%;"></div>
      </div>
      <div style="font-size:11px;color:#9598a1;margin-top:6px;line-height:1.4;">
        {ai_res.get('summary','')[:80]}
      </div>
    </div>""", unsafe_allow_html=True)

    # Entry/SL/Targets
    entry_p = ai_res.get("entry_zone",{}).get("price",0)
    sl_p    = ai_res.get("stop_loss",{}).get("price",0)
    targets = ai_res.get("targets",[])

    st.markdown('<div class="fp-section-title">TRADE LEVELS</div>', unsafe_allow_html=True)
    for item in [
        ("Entry", entry_p, "#26a69a"),
        ("Stop Loss", sl_p, "#ef5350"),
        *[(f"{t['label']}", t["price"], "#2962ff") for t in targets[:2]]
    ]:
        label, price, color = item
        st.markdown(f'<div class="fp-row"><span style="color:{color};font-weight:600;">{label}</span>'
                    f'<span style="color:{color};font-family:monospace;font-weight:700;">{price:.4f}</span></div>',
                    unsafe_allow_html=True)

    st.markdown(f"""<div style="background:#1e222d;border-radius:6px;padding:6px 10px;
    margin:6px 0;display:flex;justify-content:space-between;font-size:11px;">
      <span style="color:#6a6e7a;">Risk:Reward</span>
      <span style="color:#d1d4dc;font-weight:700;">{rr}</span>
      <span style="color:{tq_color};font-weight:700;">{tq}</span>
    </div>""", unsafe_allow_html=True)

    # Indicator signals
    ind_signals = ai_res.get("indicator_signals",{})
    if ind_signals:
        st.markdown('<div class="fp-section-title">INDICATORS</div>', unsafe_allow_html=True)
        for k, v in ind_signals.items():
            ic = "#26a69a" if any(w in str(v).lower() for w in ["bull","above","oversold","buy","confirm","green"]) \
                 else "#ef5350" if any(w in str(v).lower() for w in ["bear","below","overbought","sell","weak","red"]) \
                 else "#6a6e7a"
            st.markdown(f'<div class="fp-row"><span style="color:#9598a1;">{k}</span>'
                        f'<span style="color:{ic};font-size:10px;">{str(v)[:25]}</span></div>',
                        unsafe_allow_html=True)

    # Candlestick patterns
    if patterns:
        st.markdown('<div class="fp-section-title">PATTERNS DETECTED</div>', unsafe_allow_html=True)
        for p in patterns[:5]:
            pc = {"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#f59e0b"}.get(p["type"],"#6a6e7a")
            st.markdown(f'<span class="fp-pattern-chip" style="background:{pc}22;color:{pc};'
                        f'border:1px solid {pc}44;">{p["name"]}</span>', unsafe_allow_html=True)

    # Key observations
    obs = ai_res.get("key_observations",[])
    if obs:
        st.markdown('<div class="fp-section-title">KEY OBSERVATIONS</div>', unsafe_allow_html=True)
        for o in obs[:4]:
            st.markdown(f'<div style="font-size:11px;color:#9598a1;padding:3px 0;'
                        f'border-bottom:1px solid #1a1e2d;">• {o}</div>', unsafe_allow_html=True)

    # Footprint insight
    fp_note = ai_res.get("footprint_insight","")
    if fp_note:
        st.markdown(f"""<div style="background:#1a1e2d;border-left:3px solid #2962ff;
        border-radius:0 6px 6px 0;padding:7px 10px;margin-top:8px;font-size:11px;color:#9598a1;
        line-height:1.5;"><b style="color:#2962ff;">Order Flow:</b> {fp_note}</div>""",
                    unsafe_allow_html=True)

    # Multi timeframe
    mtf = ai_res.get("multi_timeframe",{})
    if mtf:
        st.markdown('<div class="fp-section-title">MULTI-TIMEFRAME</div>', unsafe_allow_html=True)
        for tf_label, val in mtf.items():
            st.markdown(f'<div class="fp-row"><span style="color:#6a6e7a;">{tf_label.upper()}</span>'
                        f'<span style="color:#9598a1;font-size:10px;">{str(val)[:28]}</span></div>',
                        unsafe_allow_html=True)

    # Risk note
    risk_note = ai_res.get("risk_note","")
    if risk_note:
        st.markdown(f"""<div style="background:#1a1500;border:1px solid #3d2e00;border-radius:6px;
        padding:6px 10px;margin-top:8px;font-size:10px;color:#8b8070;">
        ⚠️ {risk_note}</div>""", unsafe_allow_html=True)

    # Disclaimer
    st.markdown("""<div style="background:#0e1117;border-radius:6px;padding:5px 8px;
    margin-top:8px;font-size:9px;color:#4a5568;text-align:center;">
    Not financial advice. For educational use only.<br>Past performance ≠ future results.
    </div>""", unsafe_allow_html=True)

