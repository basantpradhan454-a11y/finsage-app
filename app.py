"""
FinSage — Global Financial Intelligence Platform
Free APIs: yfinance + CoinGecko
Auth: Google OAuth + Email/Password (Firestore)
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import time
from datetime import datetime

from data_fetcher import fetch_stock_data, fetch_crypto_data, fetch_ticker_bar_data
from analyzer import (analyze_stock, analyze_crypto, format_number,
                       compute_confidence_score, dynamic_stop_loss,
                       partial_take_profit, rug_pull_flags)
from auth_page import render_auth_page, is_logged_in, get_current_user
from history_page import render_history_page, save_search
from privacy_policy import render_privacy_policy

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSage — Global Financial Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Premium Global CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── Hide Streamlit chrome ── */
#MainMenu,footer,header,[data-testid="stToolbar"],
[data-testid="manage-app-button"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],[data-testid="stBottom"],
.stDeployButton,.viewerBadge_container__r5tak,
button[kind="header"],.st-emotion-cache-czk5ss,
._link_gzau3_10,.st-emotion-cache-1dp5vir {
    visibility:hidden !important; display:none !important;
}

/* ── Deep space background ── */
html, body, .stApp {
    background: #020510 !important;
    font-family: 'Inter', sans-serif !important;
    color: #e6edf3 !important;
}
.stApp {
    background:
        radial-gradient(ellipse 90% 60% at 15% 5%,  rgba(88,166,255,0.10) 0%, transparent 55%),
        radial-gradient(ellipse 70% 50% at 85% 90%,  rgba(167,139,250,0.09) 0%, transparent 55%),
        radial-gradient(ellipse 50% 40% at 50% 50%, rgba(63,185,80,0.04) 0%, transparent 60%),
        #020510 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(13,17,23,0.95) !important;
    border-right: 1px solid rgba(48,54,61,0.6) !important;
    backdrop-filter: blur(20px);
}

/* ── Navbar brand ── */
.fs-brand {
    font-size:1.5rem; font-weight:900; letter-spacing:-0.5px;
    background: linear-gradient(135deg,#58a6ff,#a78bfa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text;
}
.fs-tagline { color:#484f58; font-size:0.78rem; margin-left:0.6rem; }
.fs-free-badge {
    background: linear-gradient(135deg,rgba(63,185,80,0.2),rgba(63,185,80,0.08));
    color:#3fb950; border:1px solid rgba(63,185,80,0.3);
    padding:0.18rem 0.65rem; border-radius:20px; font-size:0.7rem; font-weight:700;
    letter-spacing:0.3px;
}

/* ── Ticker bar ── */
.ticker-bar {
    background: linear-gradient(135deg, rgba(22,27,34,0.9), rgba(13,17,23,0.95));
    border:1px solid rgba(48,54,61,0.7);
    border-radius:12px; padding:0.6rem 1.2rem;
    margin-bottom:1rem; overflow-x:auto; white-space:nowrap;
    backdrop-filter:blur(12px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04);
}
.ticker-item { display:inline-block; margin-right:1.6rem; font-size:0.82rem; }
.ticker-sym   { color:#58a6ff; font-weight:700; margin-right:4px; }
.ticker-price { color:#c9d1d9; margin-right:3px; }
.up   { color:#3fb950; font-weight:600; }
.down { color:#f85149; font-weight:600; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(22,27,34,0.8) !important;
    border-radius:14px 14px 0 0 !important;
    border:1px solid rgba(48,54,61,0.6) !important;
    border-bottom:none !important;
    gap:0; padding:0.4rem 0.4rem 0;
    backdrop-filter:blur(12px);
}
.stTabs [data-baseweb="tab"] {
    background:transparent !important; color:#6e7681 !important;
    border-radius:10px 10px 0 0 !important; font-weight:600 !important;
    font-size:0.92rem !important; padding:0.65rem 1.8rem !important;
    border:none !important; transition:all 0.2s !important;
}
.stTabs [data-baseweb="tab"]:hover { color:#c9d1d9 !important; }
.stTabs [aria-selected="true"] {
    background: linear-gradient(180deg, rgba(88,166,255,0.12), rgba(88,166,255,0.05)) !important;
    color:#58a6ff !important;
    border-top:2px solid #58a6ff !important;
    box-shadow: inset 0 -1px 0 rgba(88,166,255,0.1) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: rgba(13,17,23,0.8) !important;
    border:1px solid rgba(48,54,61,0.6) !important;
    border-top:none !important; border-radius:0 0 14px 14px !important;
    padding:1.6rem !important;
    backdrop-filter:blur(12px);
}

/* ── Section headings ── */
.section-heading {
    font-size:1.35rem; font-weight:800; letter-spacing:-0.5px;
    background:linear-gradient(135deg,#e6edf3,#8b949e);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text; margin-bottom:0.2rem;
}
.section-sub { color:#484f58; font-size:0.83rem; margin-bottom:1rem; }

/* ── Inputs ── */
[data-testid="stTextInput"] input {
    background: rgba(13,17,23,0.9) !important;
    border:1px solid rgba(48,54,61,0.8) !important;
    border-radius:10px !important; color:#e6edf3 !important;
    font-size:0.92rem !important; font-family:'Inter',sans-serif !important;
    transition:border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color:rgba(88,166,255,0.6) !important;
    box-shadow:0 0 0 3px rgba(88,166,255,0.1), 0 0 20px rgba(88,166,255,0.06) !important;
    outline:none !important;
}
[data-testid="stTextInput"] label { color:#8b949e !important; font-size:0.82rem !important; font-weight:600 !important; }

/* ── Buttons ── */
.stButton > button {
    background: rgba(22,27,34,0.9) !important;
    color:#58a6ff !important; border:1px solid rgba(88,166,255,0.25) !important;
    border-radius:10px !important; font-size:0.82rem !important; font-weight:600 !important;
    transition:all 0.2s !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg,rgba(88,166,255,0.2),rgba(167,139,250,0.15)) !important;
    border-color:rgba(88,166,255,0.6) !important; color:#ffffff !important;
    transform:translateY(-1px) !important;
    box-shadow:0 4px 16px rgba(88,166,255,0.2) !important;
}
/* Primary button */
[data-testid="stFormSubmitButton"] button,
button[kind="primary"] {
    background: linear-gradient(135deg,#1a6bc7,#2563eb 50%,#7c3aed) !important;
    color:#ffffff !important; border:none !important;
    border-radius:12px !important; font-weight:700 !important;
    font-size:0.95rem !important;
    box-shadow:0 4px 16px rgba(37,99,235,0.35), inset 0 1px 0 rgba(255,255,255,0.1) !important;
    transition:all 0.2s !important;
}
button[kind="primary"]:hover {
    transform:translateY(-2px) !important;
    box-shadow:0 8px 24px rgba(37,99,235,0.45), 0 0 40px rgba(124,58,237,0.15) !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(22,27,34,0.95), rgba(13,17,23,0.98)) !important;
    border:1px solid rgba(48,54,61,0.7) !important;
    border-radius:14px !important; padding:1rem 1.1rem !important;
    box-shadow:0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04) !important;
    transition:transform 0.2s, box-shadow 0.2s !important;
    position:relative; overflow:hidden;
}
[data-testid="stMetric"]::before {
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:linear-gradient(90deg,#58a6ff,#a78bfa);
    opacity:0.6;
}
[data-testid="stMetric"]:hover {
    transform:translateY(-2px) !important;
    box-shadow:0 8px 24px rgba(0,0,0,0.4), 0 0 24px rgba(88,166,255,0.06) !important;
}
[data-testid="stMetricLabel"]  { color:#8b949e !important; font-size:0.78rem !important; font-weight:600 !important; }
[data-testid="stMetricValue"]  { color:#e6edf3 !important; font-size:1.3rem !important; font-weight:800 !important; }
[data-testid="stMetricDelta"]  { font-size:0.8rem !important; font-weight:700 !important; }

/* ── Section card (result area) ── */
.result-card {
    background:linear-gradient(145deg,rgba(22,27,34,0.9),rgba(13,17,23,0.95));
    border:1px solid rgba(48,54,61,0.6); border-radius:16px;
    padding:1.4rem; margin-bottom:1rem;
    box-shadow:0 4px 20px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04);
}

/* ── Divider ── */
hr { border-color:rgba(48,54,61,0.5) !important; margin:1rem 0 !important; }

/* ── Quick pick label ── */
.quickpick-label {
    color:#58a6ff; font-size:0.78rem; font-weight:700;
    letter-spacing:0.5px; text-transform:uppercase; margin-bottom:0.4rem;
}

/* ── Meme warning ── */
.meme-warning {
    background:linear-gradient(135deg,rgba(45,27,27,0.9),rgba(35,17,17,0.95));
    border:1px solid rgba(248,81,73,0.35);
    border-radius:12px; padding:0.8rem 1rem;
    color:#f85149; font-size:0.83rem; margin-bottom:0.9rem;
    box-shadow:0 0 20px rgba(248,81,73,0.06);
}

/* ── Disclaimer ── */
.disclaimer {
    background:linear-gradient(135deg,rgba(22,27,34,0.8),rgba(13,17,23,0.9));
    border-left:3px solid rgba(210,153,34,0.6);
    border-radius:0 10px 10px 0; padding:0.75rem 1rem;
    color:#6e7681; font-size:0.78rem; margin-top:1rem;
    backdrop-filter:blur(8px);
}

/* ── Empty state ── */
.empty-state {
    text-align:center; padding:3rem 1rem; color:#484f58;
    background:rgba(13,17,23,0.5); border-radius:16px;
    border:1px dashed rgba(48,54,61,0.5);
}
.empty-state-icon { font-size:3rem; margin-bottom:0.5rem; opacity:0.6; }

/* ── Analysis report text ── */
.stMarkdown h4 { color:#c9d1d9 !important; font-weight:700 !important; }
.stMarkdown p  { color:#8b949e !important; line-height:1.7 !important; }

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background:rgba(22,27,34,0.8) !important;
    border:1px solid rgba(88,166,255,0.2) !important;
    color:#58a6ff !important; border-radius:10px !important;
    font-weight:600 !important;
}
[data-testid="stDownloadButton"] button:hover {
    background:rgba(88,166,255,0.1) !important;
    border-color:rgba(88,166,255,0.5) !important;
}

/* ── Caption ── */
.stCaption { color:#484f58 !important; font-size:0.75rem !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:rgba(13,17,23,0.5); }
::-webkit-scrollbar-thumb { background:rgba(48,54,61,0.8); border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:rgba(88,166,255,0.4); }

</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
defaults = {
    "user": None,
    "stock_data": None, "stock_report": None,
    "crypto_data": None, "crypto_report": None,
    "meme_data":   None, "meme_report":   None,
    "ticker_data": [], "last_ticker_refresh": 0,
    "stock_selected": "", "crypto_selected": "", "meme_selected": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Privacy Policy (no login needed) ──────────────────────────────────────────
if st.query_params.get("page") == "privacy":
    render_privacy_policy()
    st.stop()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
if not is_logged_in():
    render_auth_page()
    st.stop()

user = get_current_user()

# ── Ticker refresh ─────────────────────────────────────────────────────────────
now_ts = time.time()
if now_ts - st.session_state.last_ticker_refresh > 60:
    st.session_state.ticker_data = fetch_ticker_bar_data()
    st.session_state.last_ticker_refresh = now_ts

# ── Navbar ─────────────────────────────────────────────────────────────────────
nb1, nb2 = st.columns([6, 1])
with nb1:
    st.markdown("""
    <div style="padding:0.6rem 0 0.3rem;display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;">
        <span class="fs-brand">📊 FinSage</span>
        <span class="fs-tagline">Global Financial Intelligence Platform</span>
        <span class="fs-free-badge">✅ 100% FREE</span>
    </div>
    """, unsafe_allow_html=True)
with nb2:
    if st.button("🚪 Logout", key="logout_top"):
        from auth_page import logout
        logout()

st.markdown("<hr>", unsafe_allow_html=True)

# ── Live Ticker Bar ────────────────────────────────────────────────────────────
if st.session_state.ticker_data:
    html = '<div class="ticker-bar">🔴 <b style="color:#f85149;letter-spacing:0.5px;">LIVE</b>&nbsp;&nbsp;|&nbsp;&nbsp;'
    for item in st.session_state.ticker_data:
        chg = item.get("change", 0) or 0
        p   = item.get("price",  0) or 0
        cls   = "up" if chg >= 0 else "down"
        arrow = "▲"  if chg >= 0 else "▼"
        ps = f"${p:,.6f}" if p < 0.01 else f"${p:,.2f}"
        html += f'<span class="ticker-item"><span class="ticker-sym">{item["symbol"]}</span><span class="ticker-price">{ps}</span><span class="{cls}">{arrow}{abs(chg):.2f}%</span></span>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ── Results Renderer ───────────────────────────────────────────────────────────

import math as _math

def compute_indicators(history):
    close = history["Close"].astype(float)
    high  = history["High"].astype(float)   if "High"   in history.columns else close
    low   = history["Low"].astype(float)    if "Low"    in history.columns else close
    vol_s = history["Volume"].astype(float) if "Volume" in history.columns else pd.Series([0]*len(close),index=close.index)
    ma10  = close.rolling(10).mean()
    ma20  = close.rolling(20).mean()
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, float("nan"))
    rsi   = 100 - (100/(1+rs))
    ema12 = close.ewm(span=12,adjust=False).mean()
    ema26 = close.ewm(span=26,adjust=False).mean()
    macd  = ema12 - ema26
    signal= macd.ewm(span=9,adjust=False).mean()
    hist_m= macd - signal
    bb_mid= close.rolling(20).mean()
    bb_std= close.rolling(20).std()
    bb_up = bb_mid + 2*bb_std
    bb_dn = bb_mid - 2*bb_std
    return dict(close=close,high=high,low=low,volume=vol_s,
                ma10=ma10,ma20=ma20,rsi=rsi,
                macd=macd,signal=signal,hist_macd=hist_m,
                bb_mid=bb_mid,bb_up=bb_up,bb_dn=bb_dn)


def _last(series):
    try:
        v = series.dropna()
        return float(v.iloc[-1]) if len(v) else None
    except: return None


def _fp(price, currency="USD"):
    if price < 0.0001: return f"${price:.8f}"
    if price < 0.01:   return f"${price:.6f}"
    return f"{currency} {price:,.4f}"


def render_results(data, report):
    if not data or not report:
        return

    import re as _re

    name       = data.get("name", data.get("ticker",""))
    ticker_sym = data.get("ticker","")
    price      = float(data.get("current_price") or 0)
    change     = float(data.get("change_pct") or 0)
    market_cap = data.get("market_cap", 0) or 0
    risk       = int(data.get("risk_score") or 5)
    vol_a      = float(data.get("volatility_annualized") or 0)
    currency   = data.get("currency","USD")
    asset_t    = data.get("asset_type","Asset")
    is_meme    = asset_t == "Meme Coin"

    chg_color = "#3fb950" if change >= 0 else "#ef5350"
    chg_bg    = "rgba(63,185,80,0.12)" if change >= 0 else "rgba(239,83,80,0.12)"
    chg_arrow = "▲" if change >= 0 else "▼"
    price_str = _fp(price, currency)

    # Compute indicators
    history  = data.get("history")
    has_hist = (history is not None and isinstance(history, pd.DataFrame) and not history.empty)
    inds     = compute_indicators(history) if has_hist else None

    # Advanced analytics
    conf      = compute_confidence_score(data, inds)
    sl_data   = dynamic_stop_loss(data, inds)
    tp_tiers  = partial_take_profit(data, sl_data["sl_pct"])
    rug_flags = rug_pull_flags(data)

    # ── HEADER ───────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:linear-gradient(145deg,rgba(18,24,32,0.98),rgba(10,14,20,0.99));'
        f'border:1px solid rgba(88,166,255,0.18);border-radius:18px;padding:1.2rem 1.6rem;'
        f'margin-bottom:1rem;box-shadow:0 8px 32px rgba(0,0,0,0.4);position:relative;overflow:hidden;">'
        f'<div style="position:absolute;top:0;left:0;right:0;height:2px;'
        f'background:linear-gradient(90deg,#58a6ff,#a78bfa,#3fb950);"></div>'
        f'<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.8rem;">'
        f'<div>'
        f'<span style="font-size:1.4rem;font-weight:900;color:#e6edf3;">{name}</span>'
        f'<span style="color:#484f58;font-size:0.95rem;margin-left:0.4rem;">• {ticker_sym}</span>'
        f'<div style="color:#6e7681;font-size:0.7rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-top:0.2rem;">{asset_t}</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:1.9rem;font-weight:900;color:#e6edf3;letter-spacing:-1px;">{price_str}</div>'
        f'<div style="background:{chg_bg};color:{chg_color};border-radius:20px;padding:0.18rem 0.7rem;font-size:0.82rem;font-weight:800;display:inline-block;">{chg_arrow} {abs(change):.2f}% today</div>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )

    # ── CONFIDENCE SCORE GAUGE ────────────────────────────────────────────────
    score     = conf["score"]
    ring_col  = conf["color"]
    r_g, cx_g, cy_g = 54, 70, 70
    circ      = 2 * _math.pi * r_g
    filled    = circ * score / 100

    bd_html = ""
    for lbl, pts, det in conf["breakdown"][:6]:
        pc = "#3fb950" if (pts.startswith("+") and pts != "+0") else ("#ef5350" if pts.startswith("-") else "#484f58")
        bd_html += (
            f'<div style="background:rgba(13,17,23,0.8);border:1px solid rgba(48,54,61,0.6);'
            f'border-radius:8px;padding:0.45rem 0.6rem;font-size:0.72rem;">'
            f'<span style="color:#6e7681;">{lbl}</span>'
            f'<span style="color:{pc};font-weight:800;margin-left:0.3rem;">{pts}</span>'
            f'<div style="color:#484f58;font-size:0.65rem;margin-top:0.1rem;">{det}</div></div>'
        )

    st.markdown(
        f'<div style="background:linear-gradient(145deg,rgba(18,24,32,0.98),rgba(10,14,20,0.99));'
        f'border:1px solid rgba(88,166,255,0.12);border-radius:16px;padding:1.2rem 1.4rem;'
        f'margin-bottom:1rem;box-shadow:0 4px 24px rgba(0,0,0,0.3);">'
        f'<div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">'
        f'<div style="flex-shrink:0;text-align:center;">'
        f'<svg width="140" height="110" viewBox="0 0 140 110">'
        f'<circle cx="{cx_g}" cy="{cy_g}" r="{r_g}" fill="none" stroke="rgba(48,54,61,0.6)" stroke-width="10"/>'
        f'<circle cx="{cx_g}" cy="{cy_g}" r="{r_g}" fill="none" stroke="{ring_col}" stroke-width="10"'
        f' stroke-linecap="round" stroke-dasharray="{filled:.1f} {circ:.1f}"'
        f' transform="rotate(-90 {cx_g} {cy_g})"'
        f' style="filter:drop-shadow(0 0 6px {ring_col}88)"/>'
        f'<text x="{cx_g}" y="{cy_g+8}" text-anchor="middle" font-size="24" font-weight="900"'
        f' fill="{ring_col}" font-family="Inter">{score}</text>'
        f'<text x="{cx_g}" y="{cy_g+22}" text-anchor="middle" font-size="9" fill="#6e7681" font-family="Inter">/ 100</text>'
        f'</svg>'
        f'<div style="color:{ring_col};font-size:0.78rem;font-weight:800;margin-top:-0.3rem;">{conf["emoji"]} {conf["label"]}</div>'
        f'</div>'
        f'<div style="flex:1;">'
        f'<div style="color:#8b949e;font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.6rem;">Confidence Score Breakdown</div>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:0.4rem;">{bd_html}</div>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )

    # ── RUG PULL FLAGS ────────────────────────────────────────────────────────
    if rug_flags:
        flags_html = ""
        for fl in rug_flags:
            fc   = "#ef5350" if fl["severity"]=="high" else "#d29922"
            rgb  = "239,83,80" if fl["severity"]=="high" else "210,153,34"
            icon = "🚨" if fl["severity"]=="high" else "⚠️"
            flags_html += (
                f'<div style="background:rgba({rgb},0.08);border:1px solid rgba({rgb},0.25);'
                f'border-radius:10px;padding:0.55rem 0.8rem;display:flex;gap:0.5rem;align-items:flex-start;">'
                f'<span>{icon}</span>'
                f'<div><div style="color:{fc};font-size:0.78rem;font-weight:800;">{fl["label"]}</div>'
                f'<div style="color:#6e7681;font-size:0.7rem;margin-top:0.1rem;">{fl["detail"]}</div></div></div>'
            )
        st.markdown(
            f'<div style="background:rgba(239,83,80,0.05);border:1px solid rgba(239,83,80,0.2);'
            f'border-radius:14px;padding:1rem 1.2rem;margin-bottom:1rem;">'
            f'<div style="color:#ef5350;font-size:0.75rem;font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.7rem;">🚨 Risk Flags Detected</div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:0.5rem;">{flags_html}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── METRIC STRIP ─────────────────────────────────────────────────────────
    m1,m2,m3,m4,m5 = st.columns(5)
    with m1: st.metric("Price",      price_str)
    with m2: st.metric("24h Change", f"{change:+.2f}%")
    with m3: st.metric("Market Cap", format_number(market_cap))
    with m4: st.metric("Volatility", f"{vol_a:.1f}%")
    with m5: st.metric("Risk",       f"{risk}/10")

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # ── CHART ─────────────────────────────────────────────────────────────────
    if has_hist and inds:
        sl_price = sl_data["stop_loss"]
        if change > 3:    entry_price = round(price*0.97, 8)
        elif change < -3: entry_price = round(price*1.00, 8)
        else:             entry_price = round(price*0.99, 8)

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.60, 0.20, 0.20],
            vertical_spacing=0.0,
        )

        has_ohlc = all(c in history.columns for c in ["Open","High","Low","Close"])
        c_s = history["Close"].astype(float)
        o_s = history["Open"].astype(float) if "Open" in history.columns else c_s

        if has_ohlc:
            fig.add_trace(go.Candlestick(
                x=history.index,
                open=history["Open"].astype(float),
                high=history["High"].astype(float),
                low=history["Low"].astype(float),
                close=c_s,
                increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
                increasing_fillcolor="#26a69a",  decreasing_fillcolor="#ef5350",
                name="Price", showlegend=False, line=dict(width=1),
            ), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(
                x=history.index, y=c_s, mode="lines",
                line=dict(color="#58a6ff",width=2),
                fill="tozeroy", fillcolor="rgba(88,166,255,0.05)",
                name="Price", showlegend=False,
            ), row=1, col=1)

        fig.add_trace(go.Scatter(x=history.index, y=inds["ma10"],
            line=dict(color="#f7c948",width=1.2,dash="dot"), name="MA10"), row=1,col=1)
        fig.add_trace(go.Scatter(x=history.index, y=inds["ma20"],
            line=dict(color="#a78bfa",width=1.2,dash="dot"), name="MA20"), row=1,col=1)
        fig.add_trace(go.Scatter(
            x=list(history.index)+list(history.index[::-1]),
            y=list(inds["bb_up"])+list(inds["bb_dn"][::-1]),
            fill="toself", fillcolor="rgba(88,166,255,0.03)",
            line=dict(color="rgba(88,166,255,0.18)",width=0.7),
            name="BB", showlegend=True,
        ), row=1,col=1)

        # Level lines + labels
        xmax = history.index[-1]
        t_prices = [t["price"] for t in tp_tiers]
        t_labels = [t["label"].replace("Sell ","").replace("Hold ","") for t in tp_tiers]
        t_colors = [t["color"] for t in tp_tiers]
        levels = [
            ("ENTRY", entry_price, "#58a6ff", "dash"),
            ("SL",    sl_price,    "#ef5350", "dot"),
        ]
        for i, (tp, tlbl, tc) in enumerate(zip(t_prices, t_labels, t_colors)):
            levels.append((f"T{i+1}", tp, tc, "dash"))

        for lname, y_val, lcolor, ldash in levels:
            fig.add_hline(y=y_val, line=dict(color=lcolor,width=1.2,dash=ldash), row=1,col=1)
            fig.add_annotation(
                x=xmax, y=y_val, xanchor="left", showarrow=False,
                text=f"  {lname} {_fp(y_val, currency)}",
                font=dict(size=9,color=lcolor,family="Inter"),
                row=1, col=1,
            )

        up_days = c_s.values >= o_s.values
        vcols = ["rgba(38,166,154,0.5)" if u else "rgba(239,83,80,0.5)" for u in up_days]
        fig.add_trace(go.Bar(x=history.index, y=inds["volume"],
            marker_color=vcols, name="Volume", showlegend=False), row=2,col=1)

        fig.add_trace(go.Scatter(x=history.index, y=inds["rsi"],
            line=dict(color="#58a6ff",width=1.5),
            fill="tozeroy", fillcolor="rgba(88,166,255,0.04)",
            name="RSI", showlegend=False), row=3,col=1)
        fig.add_hline(y=70, line=dict(color="#ef5350",width=0.7,dash="dash"), row=3,col=1)
        fig.add_hline(y=30, line=dict(color="#26a69a",width=0.7,dash="dash"), row=3,col=1)

        BG = "rgba(10,14,20,0)"; GRID = "rgba(42,48,58,0.6)"
        fig.update_layout(
            plot_bgcolor=BG, paper_bgcolor=BG,
            font=dict(color="#5d6673",family="Inter",size=10),
            height=580, margin=dict(l=10,r=95,t=12,b=10),
            legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0,
                bgcolor="rgba(0,0,0,0)",font=dict(size=9,color="#8b949e")),
            xaxis=dict(gridcolor=GRID,showgrid=True,zeroline=False,
                rangeslider=dict(visible=False),
                showspikes=True,spikecolor="#484f58",spikethickness=1,
                spikedash="dot",spikemode="across"),
            xaxis2=dict(gridcolor=GRID,showgrid=True,zeroline=False),
            xaxis3=dict(gridcolor=GRID,showgrid=True,zeroline=False),
            yaxis=dict(gridcolor=GRID,showgrid=True,zeroline=False,
                showspikes=True,spikecolor="#484f58",spikethickness=1),
            yaxis2=dict(gridcolor=GRID,showgrid=True,zeroline=False,
                title=dict(text="Vol",font=dict(size=8))),
            yaxis3=dict(gridcolor=GRID,showgrid=True,zeroline=False,
                range=[0,100],title=dict(text="RSI",font=dict(size=8))),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="rgba(18,24,32,0.95)",font_size=11,
                font_family="Inter",bordercolor="rgba(88,166,255,0.3)"),
            dragmode="pan",
        )
        fig.update_xaxes(showline=True,linecolor="rgba(42,48,58,0.8)")
        fig.update_yaxes(showline=True,linecolor="rgba(42,48,58,0.8)")
        st.plotly_chart(fig, use_container_width=True, config={
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["select2d","lasso2d","toggleSpikelines"],
            "displaylogo": False,
            "scrollZoom": True,
        })

    # ── TRADE SETUP CARDS ─────────────────────────────────────────────────────
    sl_pct   = sl_data["sl_pct"]
    sl_price = sl_data["stop_loss"]
    dyn_note = sl_data["note"]
    is_dyn   = sl_data["is_dynamic"]

    if change > 3:    e_lo, e_hi, e_note = round(price*0.97,8), round(price*0.99,8), "Running up — wait for pullback before buying"
    elif change < -3: e_lo, e_hi, e_note = round(price*1.00,8), round(price*1.02,8), "Dipped today — good zone if overall trend is up"
    else:             e_lo, e_hi, e_note = round(price*0.99,8), round(price*1.01,8), "Stable price — enter in small parts, not all at once"

    rr = round((tp_tiers[0]["price"]-price)/(price-sl_price),1) if (price > sl_price and tp_tiers) else 0

    if   conf["score"] >= 70: action_k, ac = "BUY",         "#3fb950"
    elif conf["score"] >= 55: action_k, ac = "CAUTIOUS BUY","#26a69a"
    elif conf["score"] >= 40: action_k, ac = "HOLD",         "#d29922"
    elif conf["score"] >= 25: action_k, ac = "WATCH",        "#58a6ff"
    else:                     action_k, ac = "AVOID",        "#ef5350"

    # Build TP cards HTML
    tp_cards_html = ""
    for t in tp_tiers:
        tp_cards_html += (
            f'<div style="background:rgba(38,166,154,0.06);border:1px solid rgba(38,166,154,0.2);'
            f'border-radius:12px;padding:0.8rem;">'
            f'<div style="color:#484f58;font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.35rem;">{t["label"]}</div>'
            f'<div style="color:{t["color"]};font-size:0.88rem;font-weight:800;">{_fp(t["price"],currency)}</div>'
            f'<div style="color:#484f58;font-size:0.67rem;margin-top:0.25rem;">{t["note"]}</div></div>'
        )

    rr_color = "#3fb950" if rr >= 1.5 else "#f7c948"
    st.markdown(
        f'<div style="background:linear-gradient(145deg,rgba(18,24,32,0.98),rgba(10,14,20,0.99));'
        f'border:1px solid rgba(88,166,255,0.12);border-radius:16px;padding:1.2rem 1.4rem;'
        f'margin:0.8rem 0;box-shadow:0 4px 24px rgba(0,0,0,0.3);">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;flex-wrap:wrap;gap:0.5rem;">'
        f'<span style="color:#e6edf3;font-weight:800;font-size:1rem;">🎯 Trade Setup</span>'
        f'<div style="background:rgba(0,0,0,0.2);color:{ac};border:1px solid {ac}55;border-radius:20px;padding:0.22rem 1rem;font-size:0.82rem;font-weight:800;">{action_k}</div>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:0.6rem;">'
        f'<div style="background:rgba(88,166,255,0.07);border:1px solid rgba(88,166,255,0.18);border-radius:12px;padding:0.8rem;">'
        f'<div style="color:#484f58;font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.35rem;">Entry Zone</div>'
        f'<div style="color:#58a6ff;font-size:0.88rem;font-weight:800;">{_fp(e_lo,currency)} – {_fp(e_hi,currency)}</div>'
        f'<div style="color:#484f58;font-size:0.67rem;margin-top:0.25rem;">{e_note}</div></div>'
        f'<div style="background:rgba(239,83,80,0.07);border:1px solid rgba(239,83,80,0.18);border-radius:12px;padding:0.8rem;">'
        f'<div style="color:#484f58;font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.35rem;">Stop Loss {"⚡ Dynamic" if is_dyn else ""}</div>'
        f'<div style="color:#ef5350;font-size:0.88rem;font-weight:800;">{_fp(sl_price,currency)} ({sl_pct:.0f}%)</div>'
        f'<div style="color:#484f58;font-size:0.67rem;margin-top:0.25rem;">{dyn_note}</div></div>'
        f'{tp_cards_html}'
        f'<div style="background:rgba(167,139,250,0.07);border:1px solid rgba(167,139,250,0.18);border-radius:12px;padding:0.8rem;">'
        f'<div style="color:#484f58;font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.35rem;">Risk / Reward</div>'
        f'<div style="color:{rr_color};font-size:0.88rem;font-weight:800;">{rr}:1</div>'
        f'<div style="color:#484f58;font-size:0.67rem;margin-top:0.25rem;">{"Good setup — worth the risk" if rr >= 1.5 else "Below ideal — be cautious"}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # ── AI CHAT BUBBLES ───────────────────────────────────────────────────────
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="display:flex;align-items:center;gap:0.7rem;margin-bottom:0.9rem;">'
        '<div style="width:36px;height:36px;border-radius:50%;flex-shrink:0;'
        'background:linear-gradient(135deg,#1a6bc7,#7c3aed);'
        'display:flex;align-items:center;justify-content:center;font-size:1rem;'
        'box-shadow:0 0 14px rgba(88,166,255,0.3);">🤖</div>'
        '<div>'
        '<div style="color:#e6edf3;font-size:0.9rem;font-weight:700;">FinSage AI Analysis</div>'
        '<div style="color:#3fb950;font-size:0.68rem;font-weight:600;letter-spacing:0.3px;">● Groq LLaMA 3.3</div>'
        '</div></div>',
        unsafe_allow_html=True
    )

    raw_sections = _re.split(r'\n#{1,3} |\n---\n|\n\n', report)
    for sec in raw_sections:
        sec = sec.strip()
        if not sec or sec == "---" or len(sec) < 15:
            continue
        sec = _re.sub(r'\*\*(.+?)\*\*', r'\1', sec)
        sec = _re.sub(r'\*(.+?)\*',       r'\1', sec)
        sec = _re.sub(r'^#{1,4}\s*',       '',    sec, flags=_re.MULTILINE)
        sec = _re.sub(r'^\|.+\|',          '',    sec, flags=_re.MULTILINE)
        sec = _re.sub(r'\|',               '',    sec)
        sec = _re.sub(r'-{3,}',            '',    sec)
        sec = sec.strip()
        if len(sec) < 15:
            continue
        kw = sec.lower()
        if any(x in kw for x in ["entry","buy","bullish","uptrend","oversold","bounce","accumulate"]):
            border = "#26a69a"
        elif any(x in kw for x in ["stop","loss","risk","bearish","sell","avoid","caution","crash","rug"]):
            border = "#ef5350"
        elif any(x in kw for x in ["target","profit","exit","moon","potential"]):
            border = "#3fb950"
        else:
            border = "#58a6ff"
        st.markdown(
            f'<div style="background:rgba(16,21,28,0.85);border:1px solid rgba(48,54,61,0.4);'
            f'border-left:2px solid {border};border-radius:0 12px 12px 12px;'
            f'padding:0.85rem 1.05rem;margin-bottom:0.55rem;'
            f'font-size:0.84rem;color:#c9d1d9;line-height:1.8;">{sec.replace(chr(10),"<br>")}</div>',
            unsafe_allow_html=True
        )

    # Key metrics grid
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    if data.get("asset_type") == "Stock":
        metrics = [
            ("Sector",   data.get("sector","N/A")),
            ("P/E",      f"{data.get('pe_ratio'):.1f}x"                  if data.get("pe_ratio")     else "N/A"),
            ("EPS",      f"{currency} {data.get('eps'):.2f}"              if data.get("eps")          else "N/A"),
            ("Beta",     f"{data.get('beta'):.2f}"                        if data.get("beta")         else "N/A"),
            ("52W High", f"{currency} {data.get('week_52_high'):,.2f}"    if data.get("week_52_high") else "N/A"),
            ("52W Low",  f"{currency} {data.get('week_52_low'):,.2f}"     if data.get("week_52_low")  else "N/A"),
            ("Analyst",  data.get("recommendation","N/A")),
            ("Volume",   format_number(data.get("volume",0))),
        ]
    else:
        metrics = [
            ("Rank",     f"#{data.get('market_cap_rank','N/A')}"),
            ("7D",       f"{data.get('change_7d',0):+.2f}%"),
            ("30D",      f"{data.get('change_30d',0):+.2f}%"),
            ("ATH",      f"${data.get('ath'):,.4f}"           if data.get("ath")                else "N/A"),
            ("ATH Drop", f"{data.get('ath_change_pct',0):+.1f}%"),
            ("24H Vol",  format_number(data.get("volume_24h",0))),
            ("Supply",   f"{data.get('circulating_supply',0):,.0f}" if data.get("circulating_supply") else "N/A"),
            ("High 24H", f"${data.get('high_24h',0):,.4f}"   if data.get("high_24h")           else "N/A"),
        ]
    cols4 = st.columns(4)
    for idx_m,(label,val) in enumerate(metrics):
        with cols4[idx_m%4]:
            st.markdown(
                f'<div style="background:rgba(13,17,23,0.8);border:1px solid rgba(48,54,61,0.4);'
                f'border-radius:10px;padding:0.55rem 0.75rem;margin-bottom:0.45rem;">'
                f'<div style="color:#484f58;font-size:0.63rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>'
                f'<div style="color:#e6edf3;font-size:0.86rem;font-weight:700;margin-top:0.12rem;">{val}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.download_button("📥 Download Report",
        data=report,
        file_name=f"FinSage_{ticker_sym}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown", use_container_width=True)



# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["🌍  Global Stocks", "₿  Cryptocurrency", "🎭  Meme Coins", "🕐  History"])

# ─── TAB 1: STOCKS ────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-heading">🌍 Global Stock Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Real-time data from NSE India, US, UK, Germany, Japan & more.</div>', unsafe_allow_html=True)

    s1, s2 = st.columns([2, 1])
    with s1:
        stock_ticker = st.text_input("Enter Stock Ticker Symbol",
            placeholder="e.g. AAPL, RELIANCE.NS, TCS.NS, TSLA", key="stock_input")
    with s2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🇮🇳 NSE: RELIANCE.NS · TCS.NS · INFY.NS")
        st.caption("🇺🇸 US: AAPL · TSLA · NVDA · MSFT")
        st.caption("🌐 Others: .L (London) · .DE (Germany)")

    st.markdown('<div class="quickpick-label">⚡ Quick Pick</div>', unsafe_allow_html=True)
    sc = st.columns(8)
    for i, s in enumerate(["AAPL","TSLA","NVDA","MSFT","GOOGL","RELIANCE.NS","TCS.NS","INFY.NS"]):
        with sc[i]:
            if st.button(s, key=f"sq_{s}"):
                st.session_state.stock_selected = s
                st.rerun()

    sym = (st.session_state.stock_selected or stock_ticker).strip().upper()
    if st.button("🔍 Analyze Stock", key="btn_stock", type="primary", use_container_width=True):
        if sym:
            with st.spinner(f"Fetching data for **{sym}**..."):
                d = fetch_stock_data(sym)
                if "error" not in d:
                    st.session_state.stock_data   = d
                    st.session_state.stock_report = analyze_stock(d)
                    if is_logged_in():
                        save_search(user["email"], "Stock", sym, d.get("name", sym))
                    st.session_state.stock_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning("⚠️ Please enter or select a stock ticker.")

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.session_state.stock_data:
        render_results(st.session_state.stock_data, st.session_state.stock_report)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🌍</div>
            <p style="color:#8b949e;font-size:0.95rem;">Enter a ticker symbol above and click <b>Analyze Stock</b></p>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Data from Yahoo Finance (yfinance). For educational purposes only. Not SEBI-registered investment advice.</div>', unsafe_allow_html=True)


# ─── TAB 2: CRYPTO ────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-heading">₿ Cryptocurrency Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Real-time data from CoinGecko — 100+ coins supported.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        crypto_ticker = st.text_input("Enter Crypto Symbol",
            placeholder="e.g. BTC, ETH, SOL, BNB, ADA, XRP", key="crypto_input")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Large Cap: BTC · ETH · BNB · SOL")
        st.caption("Mid Cap: ADA · AVAX · DOT · MATIC")

    st.markdown('<div class="quickpick-label">⚡ Quick Pick</div>', unsafe_allow_html=True)
    cc = st.columns(8)
    for i, c in enumerate(["BTC","ETH","SOL","BNB","XRP","ADA","AVAX","DOT"]):
        with cc[i]:
            if st.button(c, key=f"cq_{c}"):
                st.session_state.crypto_selected = c
                st.rerun()

    csym = (st.session_state.crypto_selected or crypto_ticker).strip().upper()
    if st.button("🔍 Analyze Crypto", key="btn_crypto", type="primary", use_container_width=True):
        if csym:
            with st.spinner(f"Fetching data for **{csym}**..."):
                d = fetch_crypto_data(csym)
                if "error" not in d:
                    st.session_state.crypto_data   = d
                    st.session_state.crypto_report = analyze_crypto(d)
                    if is_logged_in():
                        save_search(user["email"], "Crypto", csym, d.get("name", csym))
                    st.session_state.crypto_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning("⚠️ Please enter or select a crypto symbol.")

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.session_state.crypto_data:
        render_results(st.session_state.crypto_data, st.session_state.crypto_report)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">₿</div>
            <p style="color:#8b949e;font-size:0.95rem;">Enter a crypto symbol and click <b>Analyze Crypto</b></p>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Data from CoinGecko. Crypto is highly volatile & unregulated by SEBI. Educational purposes only.</div>', unsafe_allow_html=True)


# ─── TAB 3: MEME COINS ────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-heading">🎭 Meme Coin Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="meme-warning">⚠️ <b>HIGH RISK:</b> Meme coins are purely speculative. Prices can crash 80–90% overnight. Only use money you can afford to lose completely.</div>', unsafe_allow_html=True)

    m1, m2 = st.columns([2, 1])
    with m1:
        meme_ticker = st.text_input("Enter Meme Coin Symbol",
            placeholder="e.g. DOGE, SHIB, PEPE, FLOKI, BONK", key="meme_input")
    with m2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Popular: DOGE · SHIB · PEPE · FLOKI")
        st.caption("Trending: BONK · WIF · MEME · TURBO")

    st.markdown('<div class="quickpick-label">⚡ Quick Pick</div>', unsafe_allow_html=True)
    mc = st.columns(8)
    for i, m in enumerate(["DOGE","SHIB","PEPE","FLOKI","BONK","WIF","MEME","TURBO"]):
        with mc[i]:
            if st.button(m, key=f"mq_{m}"):
                st.session_state.meme_selected = m
                st.rerun()

    msym = (st.session_state.meme_selected or meme_ticker).strip().upper()
    if st.button("🔍 Analyze Meme Coin", key="btn_meme", type="primary", use_container_width=True):
        if msym:
            with st.spinner(f"Fetching data for **{msym}**..."):
                d = fetch_crypto_data(msym)
                if "error" not in d:
                    d["asset_type"] = "Meme Coin"
                    st.session_state.meme_data   = d
                    st.session_state.meme_report = analyze_crypto(d)
                    if is_logged_in():
                        save_search(user["email"], "Meme", msym, d.get("name", msym))
                    st.session_state.meme_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning("⚠️ Please enter or select a meme coin symbol.")

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.session_state.meme_data:
        render_results(st.session_state.meme_data, st.session_state.meme_report)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🎭</div>
            <p style="color:#8b949e;font-size:0.95rem;">Enter a meme coin symbol and click <b>Analyze Meme Coin</b></p>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Meme coins are unregulated & highly speculative. Not SEBI advice. Never invest borrowed money in meme coins.</div>', unsafe_allow_html=True)


# ─── TAB 4: HISTORY ───────────────────────────────────────────────────────────
with tab4:
    if is_logged_in():
        render_history_page(get_current_user())
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🔒</div>
            <p style="color:#c9d1d9;font-size:1rem;font-weight:600;">Login required</p>
            <p style="color:#8b949e;">Please log in to view your search history.</p>
        </div>""", unsafe_allow_html=True)


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
f1, f2 = st.columns(2)
with f1:
    st.markdown("<span style='color:#484f58;font-size:0.75rem;'>📊 <b style=\"color:#58a6ff;\">FinSage</b> — Global Financial Intelligence Platform</span>", unsafe_allow_html=True)
with f2:
    st.markdown("<span style='color:#30363d;font-size:0.75rem;display:block;text-align:right;'>Data: Yahoo Finance · CoinGecko &nbsp;|&nbsp; Educational purposes only</span>", unsafe_allow_html=True)
