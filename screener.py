"""
FinsageAI — Smart Stock Screener
Filter NSE India + US stocks by RSI, MACD, EMA, Volume, ATR — real yfinance data
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime


# ── Indicator helpers ──────────────────────────────────────────────────────────
def _ema(s, n):  return s.ewm(span=n, adjust=False).mean()
def _rsi(s, n=14):
    d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = g.ewm(com=n-1, min_periods=n).mean()
    al = l.ewm(com=n-1, min_periods=n).mean()
    return 100 - 100/(1 + ag/al.replace(0, np.nan))
def _macd(s):
    m = _ema(s,12)-_ema(s,26); sig = _ema(m,9); return m, sig, m-sig
def _atr(h, l, c, n=14):
    tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.ewm(com=n-1,min_periods=n).mean()
def _bb(s, n=20, k=2):
    m = s.rolling(n).mean(); sd = s.rolling(n).std()
    return m+k*sd, m, m-k*sd


# ── Watchlists ─────────────────────────────────────────────────────────────────
WATCHLISTS = {
    "🇮🇳 NSE Top 30": [
        "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
        "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
        "LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS","SUNPHARMA.NS",
        "TITAN.NS","BAJFINANCE.NS","NESTLEIND.NS","WIPRO.NS","HCLTECH.NS",
        "ULTRACEMCO.NS","TECHM.NS","POWERGRID.NS","NTPC.NS","ONGC.NS",
        "TATASTEEL.NS","JSWSTEEL.NS","M&M.NS","DIVISLAB.NS","CIPLA.NS",
    ],
    "🇺🇸 US Tech Giants": [
        "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","AVGO","ORCL",
        "AMD","INTC","QCOM","TXN","MU","AMAT","ADBE","CRM","NOW","SNOW","PLTR",
    ],
    "🪙 Crypto (yfinance)": [
        "BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD",
        "ADA-USD","AVAX-USD","DOT-USD","MATIC-USD","LINK-USD",
    ],
    "🐸 Meme Coins": [
        "DOGE-USD","SHIB-USD","PEPE-USD","FLOKI-USD","BONK-USD","WIF-USD",
    ],
    "🏦 NSE Banking": [
        "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","KOTAKBANK.NS","AXISBANK.NS",
        "BANKBARODA.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","INDUSINDBK.NS","PNB.NS",
    ],
}


@st.cache_data(ttl=300, show_spinner=False)
def _screen_symbol(sym: str) -> dict | None:
    """Fetch + compute indicators for one symbol. Returns None on error."""
    try:
        df = yf.Ticker(sym).history(period="3mo", interval="1d")
        if df.empty or len(df) < 30:
            return None
        c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]

        rsi   = float(_rsi(c).iloc[-1])
        macd, sig, hist = _macd(c)
        macd_v = float(macd.iloc[-1]); sig_v = float(sig.iloc[-1])
        e20  = float(_ema(c,20).iloc[-1]); e50 = float(_ema(c,50).iloc[-1])
        e200 = float(_ema(c,200).iloc[-1])
        atr  = float(_atr(h,l,c).iloc[-1])
        bb_u, bb_m, bb_l = _bb(c)
        pct_b = float(((c - bb_l)/(bb_u - bb_l)).iloc[-1])
        vol_ratio = float((v / v.rolling(20).mean()).iloc[-1])
        price = float(c.iloc[-1])
        chg1  = float(c.pct_change(1).iloc[-1] * 100)
        chg5  = float(c.pct_change(5).iloc[-1] * 100)
        vol_avg = float(v.rolling(20).mean().iloc[-1])

        # Simple score
        score = 0
        if rsi < 30:  score += 25
        elif rsi < 40: score += 12
        elif rsi > 70: score -= 25
        elif rsi > 60: score -= 12
        if macd_v > sig_v: score += 20
        else: score -= 20
        if price > e20 > e50: score += 15
        elif price < e20 < e50: score -= 15
        if price > e200: score += 10
        else: score -= 10
        if vol_ratio > 1.5 and chg1 > 0: score += 10
        elif vol_ratio > 1.5 and chg1 < 0: score -= 10

        return {
            "Symbol": sym.replace(".NS","").replace("-USD",""),
            "_sym": sym,
            "Price": round(price, 4),
            "1D%": round(chg1, 2),
            "5D%": round(chg5, 2),
            "RSI": round(rsi, 1),
            "MACD>Sig": macd_v > sig_v,
            "P>EMA20": price > e20,
            "P>EMA200": price > e200,
            "Vol Ratio": round(vol_ratio, 2),
            "%B": round(pct_b, 3),
            "ATR": round(atr, 4),
            "Score": max(-100, min(100, score)),
            "Signal": ("🟢 BUY" if score >= 30 else
                       "🔴 SELL" if score <= -30 else "⚪ HOLD"),
        }
    except Exception:
        return None


def render_screener():
    from config import LOGO_URL

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));
    border:1px solid rgba(0,212,255,0.25);border-radius:14px;
    padding:1.2rem 1.5rem;margin-bottom:1rem;">
      <div style="display:flex;align-items:center;gap:0.9rem;">
        <img src="{LOGO_URL}" style="height:44px;border-radius:10px;
        box-shadow:0 0 15px rgba(0,212,255,0.3);">
        <div>
          <div style="font-size:1.1rem;font-weight:800;font-family:Orbitron,monospace;
          background:linear-gradient(90deg,#00d4ff,#a371f7);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          🔍 Smart Stock Screener</div>
          <div style="color:#8b949e;font-size:0.73rem;">
          Filter NSE India + US + Crypto by RSI · MACD · EMA · Volume · Score
          </div>
        </div>
        <span style="margin-left:auto;background:rgba(0,255,136,0.1);color:#00ff88;
        padding:0.2rem 0.7rem;border-radius:20px;font-size:0.65rem;font-weight:700;
        border:1px solid rgba(0,255,136,0.25);">✅ 100% REAL DATA</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Controls ──────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        watchlist = st.selectbox("📋 Select Universe", list(WATCHLISTS.keys()), key="sc_wl")
    with c2:
        filter_mode = st.selectbox("🎯 Filter Mode", [
            "All Stocks",
            "🟢 BUY signals only",
            "🔴 SELL signals only",
            "RSI Oversold (<30)",
            "RSI Overbought (>70)",
            "MACD Bullish Crossover",
            "Price > EMA200 (Uptrend)",
            "Price < EMA200 (Downtrend)",
            "High Volume (>1.5x avg)",
            "BB Squeeze (%B < 0.1)",
            "Top 10 by Score",
        ], key="sc_filter")
    with c3:
        scan_btn = st.button("⚡ Scan Now", type="primary", use_container_width=True, key="sc_scan")

    # Custom filters expander
    with st.expander("🔧 Custom Filters (Advanced)", expanded=False):
        cf1, cf2, cf3, cf4 = st.columns(4)
        with cf1:
            rsi_min = st.number_input("RSI Min", 0, 100, 0, key="sc_rsi_min")
            rsi_max = st.number_input("RSI Max", 0, 100, 100, key="sc_rsi_max")
        with cf2:
            score_min = st.number_input("Score Min", -100, 100, -100, key="sc_score_min")
            vol_min   = st.number_input("Vol Ratio Min", 0.0, 10.0, 0.0, step=0.1, key="sc_vol_min")
        with cf3:
            chg1_min = st.number_input("1D% Min", -50.0, 50.0, -50.0, step=0.5, key="sc_chg_min")
            chg1_max = st.number_input("1D% Max", -50.0, 50.0, 50.0, step=0.5, key="sc_chg_max")
        with cf4:
            macd_bull = st.checkbox("MACD Bullish", key="sc_macd_bull")
            ema200_up = st.checkbox("Above EMA200", key="sc_ema200")
            use_custom = st.checkbox("Apply Custom Filters", key="sc_use_custom")

    if not scan_btn and "sc_results" not in st.session_state:
        st.info("👆 Select a universe and click ⚡ Scan Now to screen stocks in real-time.")
        return

    if scan_btn:
        symbols = WATCHLISTS[watchlist]
        results = []
        prog = st.progress(0, text="Scanning symbols...")
        for i, sym in enumerate(symbols):
            r = _screen_symbol(sym)
            if r:
                results.append(r)
            prog.progress((i+1)/len(symbols), text=f"Scanning {sym}... ({i+1}/{len(symbols)})")
            time.sleep(0.05)
        prog.empty()
        st.session_state["sc_results"] = results
        st.session_state["sc_wl_name"] = watchlist

    results = st.session_state.get("sc_results", [])
    if not results:
        st.warning("No data returned. Try again.")
        return

    df = pd.DataFrame(results)

    # ── Apply Filters ──────────────────────────────────────────────────────────
    if st.session_state.get("sc_use_custom"):
        df = df[df["RSI"].between(rsi_min, rsi_max)]
        df = df[df["Score"] >= score_min]
        df = df[df["Vol Ratio"] >= vol_min]
        df = df[df["1D%"].between(chg1_min, chg1_max)]
        if macd_bull: df = df[df["MACD>Sig"] == True]
        if ema200_up: df = df[df["P>EMA200"] == True]
    else:
        fm = filter_mode
        if fm == "🟢 BUY signals only":        df = df[df["Score"] >= 30]
        elif fm == "🔴 SELL signals only":     df = df[df["Score"] <= -30]
        elif fm == "RSI Oversold (<30)":       df = df[df["RSI"] < 30]
        elif fm == "RSI Overbought (>70)":     df = df[df["RSI"] > 70]
        elif fm == "MACD Bullish Crossover":   df = df[df["MACD>Sig"] == True]
        elif fm == "Price > EMA200 (Uptrend)": df = df[df["P>EMA200"] == True]
        elif fm == "Price < EMA200 (Downtrend)": df = df[df["P>EMA200"] == False]
        elif fm == "High Volume (>1.5x avg)":  df = df[df["Vol Ratio"] >= 1.5]
        elif fm == "BB Squeeze (%B < 0.1)":    df = df[df["%B"] < 0.1]
        elif fm == "Top 10 by Score":          df = df.nlargest(10, "Score")

    df = df.sort_values("Score", ascending=False)

    # ── Summary Cards ──────────────────────────────────────────────────────────
    total   = len(results)
    buy_c   = len(df[df["Score"] >= 30])  if len(df) else 0
    sell_c  = len(df[df["Score"] <= -30]) if len(df) else 0
    neutral = total - buy_c - sell_c
    avg_rsi = round(df["RSI"].mean(), 1) if len(df) else 0

    s1,s2,s3,s4,s5 = st.columns(5)
    s1.metric("📋 Scanned",   total)
    s2.metric("🟢 BUY",       buy_c,  delta=f"{buy_c/total*100:.0f}%")
    s3.metric("🔴 SELL",      sell_c, delta=f"-{sell_c/total*100:.0f}%")
    s4.metric("⚪ NEUTRAL",   neutral)
    s5.metric("📊 Avg RSI",   avg_rsi)

    if df.empty:
        st.warning(f"No stocks matched the filter: **{filter_mode}**")
        return

    st.markdown(f"**Showing {len(df)} results** — sorted by Score (highest first)")

    # ── Results Table ──────────────────────────────────────────────────────────
    display_df = df[[
        "Symbol","Signal","Price","1D%","5D%",
        "RSI","Vol Ratio","%B","ATR","Score"
    ]].copy()

    # Color formatting via styling
    def color_signal(val):
        if "BUY"  in str(val): return "color:#00ff88;font-weight:700"
        if "SELL" in str(val): return "color:#ff4466;font-weight:700"
        return "color:#8b949e"
    def color_score(val):
        if val >= 30:  return "background:rgba(0,255,136,0.12);color:#00ff88;font-weight:700"
        if val <= -30: return "background:rgba(255,68,102,0.12);color:#ff4466;font-weight:700"
        return "color:#f0c040"
    def color_rsi(val):
        if val < 30: return "color:#00ff88;font-weight:700"
        if val > 70: return "color:#ff4466;font-weight:700"
        return ""
    def color_chg(val):
        return "color:#00ff88" if val > 0 else "color:#ff4466" if val < 0 else ""

    styled = display_df.style\
        .applymap(color_signal, subset=["Signal"])\
        .applymap(color_score,  subset=["Score"])\
        .applymap(color_rsi,    subset=["RSI"])\
        .applymap(color_chg,    subset=["1D%","5D%"])

    st.dataframe(styled, use_container_width=True, hide_index=True,
        column_config={
            "Symbol":    st.column_config.TextColumn("Symbol",    width="small"),
            "Signal":    st.column_config.TextColumn("Signal",    width="medium"),
            "Price":     st.column_config.NumberColumn("Price",   format="%.4f"),
            "1D%":       st.column_config.NumberColumn("1D %",    format="%.2f%%"),
            "5D%":       st.column_config.NumberColumn("5D %",    format="%.2f%%"),
            "RSI":       st.column_config.NumberColumn("RSI",     format="%.1f"),
            "Vol Ratio": st.column_config.NumberColumn("Vol Ratio",format="%.2fx"),
            "%B":        st.column_config.NumberColumn("%B",       format="%.3f"),
            "ATR":       st.column_config.NumberColumn("ATR",      format="%.4f"),
            "Score":     st.column_config.NumberColumn("Score",    format="%d / 100"),
        }
    )

    # ── Click to analyze ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**⚡ Quick Analyze — click any symbol:**")
    cols = st.columns(min(len(df), 8))
    for i, (_, row) in enumerate(df.head(8).iterrows()):
        with cols[i]:
            if st.button(row["Symbol"], key=f"sc_q_{i}", use_container_width=True):
                st.session_state["adv_symbol"] = row["_sym"]
                st.session_state["active_page"] = "📡 Adv. Analyzer"
                st.rerun()

    st.caption(f"⏰ Scan completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data: yfinance (Real-time)")
    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.5rem 0.9rem;margin-top:0.5rem;font-size:0.73rem;color:#8b949e;">
    ⚠️ <b style="color:#d29922;">Disclaimer:</b> For educational purposes only. Not investment advice.
    </div>""", unsafe_allow_html=True)
