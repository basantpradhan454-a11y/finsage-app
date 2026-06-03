"""
FinSage — Global Financial Intelligence Platform
Free APIs: yfinance + CoinGecko
Auth: Google OAuth + Email/Password (Firestore)
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
from datetime import datetime

from data_fetcher import fetch_stock_data, fetch_crypto_data, fetch_ticker_bar_data
from analyzer import analyze_stock, analyze_crypto, format_number
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
def compute_indicators(history: pd.DataFrame):
    """Compute RSI, MACD, Bollinger Bands, MA10, MA20 from OHLCV history."""
    close = history["Close"].astype(float)
    high  = history["High"].astype(float)  if "High"   in history.columns else close
    low   = history["Low"].astype(float)   if "Low"    in history.columns else close
    vol   = history["Volume"].astype(float) if "Volume" in history.columns else pd.Series([0]*len(close), index=close.index)

    # MAs
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()

    # RSI
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, float("nan"))
    rsi   = 100 - (100 / (1 + rs))

    # MACD
    ema12  = close.ewm(span=12, adjust=False).mean()
    ema26  = close.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist_m = macd - signal

    # Bollinger Bands
    bb_mid  = close.rolling(20).mean()
    bb_std  = close.rolling(20).std()
    bb_up   = bb_mid + 2 * bb_std
    bb_dn   = bb_mid - 2 * bb_std

    return {
        "close": close, "high": high, "low": low, "volume": vol,
        "ma10": ma10, "ma20": ma20,
        "rsi": rsi, "macd": macd, "signal": signal, "hist_macd": hist_m,
        "bb_mid": bb_mid, "bb_up": bb_up, "bb_dn": bb_dn,
    }


def indicator_badge(label, value, status="neutral"):
    colors = {
        "bullish":  ("rgba(63,185,80,0.15)",  "#3fb950", "rgba(63,185,80,0.4)"),
        "bearish":  ("rgba(248,81,73,0.15)",  "#f85149", "rgba(248,81,73,0.4)"),
        "neutral":  ("rgba(88,166,255,0.10)", "#58a6ff", "rgba(88,166,255,0.3)"),
        "warning":  ("rgba(210,153,34,0.15)", "#d29922", "rgba(210,153,34,0.4)"),
    }
    bg, fg, border = colors.get(status, colors["neutral"])
    return f"""<div style="background:{bg};border:1px solid {border};border-radius:10px;
        padding:0.6rem 0.8rem;text-align:center;flex:1;min-width:90px;">
        <div style="color:#6e7681;font-size:0.68rem;font-weight:700;text-transform:uppercase;
            letter-spacing:0.5px;margin-bottom:0.25rem;">{label}</div>
        <div style="color:{fg};font-size:0.88rem;font-weight:800;">{value}</div>
    </div>"""


def render_results(data, report):
    if not data or not report:
        return

    name       = data.get("name", data.get("ticker", ""))
    ticker_sym = data.get("ticker", "")
    price      = data.get("current_price", 0) or 0
    change     = data.get("change_pct",    0) or 0
    market_cap = data.get("market_cap",    0) or 0
    risk       = data.get("risk_score",    5) or 5
    vol        = data.get("volatility_annualized", 0) or 0
    currency   = data.get("currency", "USD")
    asset_t    = data.get("asset_type", "Asset")

    chg_color = "#3fb950" if change >= 0 else "#f85149"
    chg_arrow = "▲" if change >= 0 else "▼"
    chg_bg    = "rgba(63,185,80,0.1)" if change >= 0 else "rgba(248,81,73,0.1)"

    if price < 0.0001:   price_str = f"${price:.8f}"
    elif price < 0.01:   price_str = f"${price:.6f}"
    else:                price_str = f"{currency} {price:,.2f}"

    # ── Asset Header Card ────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(145deg,rgba(22,27,34,0.95),rgba(13,17,23,0.98));
        border:1px solid rgba(88,166,255,0.2);border-radius:20px;padding:1.4rem 1.6rem;
        margin-bottom:1rem;box-shadow:0 4px 24px rgba(0,0,0,0.35),inset 0 1px 0 rgba(255,255,255,0.04);
        position:relative;overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:2px;
          background:linear-gradient(90deg,#58a6ff,#a78bfa,#3fb950);opacity:0.7;"></div>
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
        <div>
          <div style="font-size:1.5rem;font-weight:900;color:#e6edf3;letter-spacing:-0.5px;">
            {name} <span style="color:#484f58;font-size:1rem;font-weight:500;">({ticker_sym})</span>
          </div>
          <div style="color:#6e7681;font-size:0.78rem;margin-top:0.2rem;font-weight:600;
              text-transform:uppercase;letter-spacing:0.5px;">{asset_t}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:2rem;font-weight:900;color:#e6edf3;letter-spacing:-1px;">{price_str}</div>
          <div style="background:{chg_bg};color:{chg_color};padding:0.2rem 0.7rem;
              border-radius:20px;font-size:0.85rem;font-weight:800;display:inline-block;margin-top:0.2rem;">
            {chg_arrow} {abs(change):.2f}%
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Metric Cards ─────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("💰 Price",        price_str)
    with k2: st.metric("📈 24H Change",   f"{change:+.2f}%")
    with k3: st.metric("🏦 Market Cap",   format_number(market_cap))
    with k4: st.metric("⚡ Volatility",   f"{vol:.1f}%")
    with k5: st.metric("🎯 Risk Score",   f"{risk}/10")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Chart + Indicators ───────────────────────────────────────────────────
    history = data.get("history")
    has_hist = history is not None and isinstance(history, pd.DataFrame) and not history.empty

    if has_hist:
        inds = compute_indicators(history)
        close = inds["close"]

        # ─ Indicator badges ──────────────────────────────────────────────────
        rsi_val  = float(inds["rsi"].iloc[-1])  if not inds["rsi"].isna().all()  else 50.0
        macd_val = float(inds["macd"].iloc[-1]) if not inds["macd"].isna().all() else 0.0
        sig_val  = float(inds["signal"].iloc[-1]) if not inds["signal"].isna().all() else 0.0
        bb_up_v  = float(inds["bb_up"].iloc[-1])  if not inds["bb_up"].isna().all()  else price
        bb_dn_v  = float(inds["bb_dn"].iloc[-1])  if not inds["bb_dn"].isna().all()  else price
        ma10_v   = float(inds["ma10"].iloc[-1])    if not inds["ma10"].isna().all()   else price
        ma20_v   = float(inds["ma20"].iloc[-1])    if not inds["ma20"].isna().all()   else price

        rsi_status  = "bullish" if rsi_val < 30 else ("bearish" if rsi_val > 70 else "neutral")
        macd_status = "bullish" if macd_val > sig_val else "bearish"
        ma_status   = "bullish" if price > ma20_v else "bearish"
        bb_pct      = (price - bb_dn_v) / (bb_up_v - bb_dn_v) * 100 if (bb_up_v - bb_dn_v) > 0 else 50
        bb_status   = "bullish" if bb_pct < 25 else ("bearish" if bb_pct > 75 else "neutral")

        rsi_label  = "OVERSOLD" if rsi_val < 30 else ("OVERBOUGHT" if rsi_val > 70 else f"{rsi_val:.0f}")
        macd_label = "BULLISH" if macd_val > sig_val else "BEARISH"
        ma_label   = "ABOVE MA20" if price > ma20_v else "BELOW MA20"
        bb_label   = "NEAR BOTTOM" if bb_pct < 25 else ("NEAR TOP" if bb_pct > 75 else "MID BAND")

        st.markdown(f"""
        <div style="margin-bottom:1rem;">
          <div style="color:#8b949e;font-size:0.72rem;font-weight:700;text-transform:uppercase;
              letter-spacing:1px;margin-bottom:0.6rem;">📡 Technical Indicators</div>
          <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
            {indicator_badge("RSI (14)", rsi_label, rsi_status)}
            {indicator_badge("MACD", macd_label, macd_status)}
            {indicator_badge("MA Trend", ma_label, ma_status)}
            {indicator_badge("Bollinger", bb_label, bb_status)}
            {indicator_badge("MA10", f"{currency} {ma10_v:,.2f}", "neutral")}
            {indicator_badge("MA20", f"{currency} {ma20_v:,.2f}", "neutral")}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ─ Candlestick Chart ──────────────────────────────────────────────────
        from plotly.subplots import make_subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            row_heights=[0.55, 0.22, 0.23],
            vertical_spacing=0.04,
        )

        has_ohlc = all(c in history.columns for c in ["Open","High","Low","Close"])

        if has_ohlc:
            o = history["Open"].astype(float)
            h = history["High"].astype(float)
            l = history["Low"].astype(float)
            c = history["Close"].astype(float)
            fig.add_trace(go.Candlestick(
                x=history.index, open=o, high=h, low=l, close=c,
                increasing_line_color="#3fb950", decreasing_line_color="#f85149",
                increasing_fillcolor="rgba(63,185,80,0.7)",
                decreasing_fillcolor="rgba(248,81,73,0.7)",
                name="OHLC", showlegend=False,
            ), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(
                x=history.index, y=close, mode="lines",
                line=dict(color="#58a6ff", width=2),
                fill="tozeroy", fillcolor="rgba(88,166,255,0.06)",
                name="Price", showlegend=False,
            ), row=1, col=1)

        # MA10 & MA20
        fig.add_trace(go.Scatter(
            x=history.index, y=inds["ma10"], mode="lines",
            line=dict(color="#f7c948", width=1.2, dash="dot"),
            name="MA10", showlegend=True,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=history.index, y=inds["ma20"], mode="lines",
            line=dict(color="#a78bfa", width=1.2, dash="dot"),
            name="MA20", showlegend=True,
        ), row=1, col=1)

        # Bollinger Bands
        fig.add_trace(go.Scatter(
            x=list(history.index) + list(history.index[::-1]),
            y=list(inds["bb_up"]) + list(inds["bb_dn"][::-1]),
            fill="toself", fillcolor="rgba(88,166,255,0.04)",
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, name="BB",
        ), row=1, col=1)

        # Volume
        vol_colors = ["rgba(63,185,80,0.65)" if float(c.iloc[i]) >= float(c.iloc[i-1]) else "rgba(248,81,73,0.65)"
                      for i in range(len(inds["volume"]))]
        fig.add_trace(go.Bar(
            x=history.index, y=inds["volume"],
            marker_color=vol_colors, name="Volume", showlegend=False,
        ), row=2, col=1)

        # RSI
        fig.add_trace(go.Scatter(
            x=history.index, y=inds["rsi"],
            line=dict(color="#58a6ff", width=1.5),
            name="RSI", showlegend=False,
        ), row=3, col=1)
        fig.add_hline(y=70, line=dict(color="#f85149", width=0.8, dash="dash"), row=3, col=1)
        fig.add_hline(y=30, line=dict(color="#3fb950", width=0.8, dash="dash"), row=3, col=1)

        PLOT_BG = "rgba(13,17,23,0.0)"
        GRID    = "rgba(48,54,61,0.4)"
        fig.update_layout(
            plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG,
            font=dict(color="#6e7681", family="Inter", size=11),
            height=520,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                bgcolor="rgba(0,0,0,0)", font=dict(size=10, color="#8b949e"),
            ),
            xaxis=dict(gridcolor=GRID, showgrid=True, zeroline=False, rangeslider=dict(visible=False)),
            xaxis2=dict(gridcolor=GRID, showgrid=True, zeroline=False),
            xaxis3=dict(gridcolor=GRID, showgrid=True, zeroline=False),
            yaxis=dict(gridcolor=GRID,  showgrid=True, zeroline=False),
            yaxis2=dict(gridcolor=GRID, showgrid=True, zeroline=False, title=dict(text="Vol", font=dict(size=9))),
            yaxis3=dict(gridcolor=GRID, showgrid=True, zeroline=False, title=dict(text="RSI", font=dict(size=9)), range=[0,100]),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Key Metrics + MACD ───────────────────────────────────────────────────
    col_info, col_macd = st.columns([1, 1])

    with col_info:
        st.markdown("""<div style="color:#8b949e;font-size:0.72rem;font-weight:700;
            text-transform:uppercase;letter-spacing:1px;margin-bottom:0.8rem;">📋 Key Metrics</div>""",
            unsafe_allow_html=True)
        if data.get("asset_type") == "Stock":
            metrics = [
                ("Sector",    data.get("sector", "N/A")),
                ("P/E Ratio", f"{data.get('pe_ratio'):.1f}x"              if data.get("pe_ratio")       else "N/A"),
                ("EPS",       f"{currency} {data.get('eps'):.2f}"          if data.get("eps")            else "N/A"),
                ("Beta",      f"{data.get('beta'):.2f}"                    if data.get("beta")           else "N/A"),
                ("52W High",  f"{currency} {data.get('week_52_high'):,.2f}" if data.get("week_52_high")  else "N/A"),
                ("52W Low",   f"{currency} {data.get('week_52_low'):,.2f}"  if data.get("week_52_low")   else "N/A"),
                ("Analyst",   data.get("recommendation", "N/A")),
                ("Volume",    format_number(data.get("volume", 0))),
            ]
        else:
            metrics = [
                ("Rank",      f"#{data.get('market_cap_rank', 'N/A')}"),
                ("7D Chg",    f"{data.get('change_7d',  0):+.2f}%"),
                ("30D Chg",   f"{data.get('change_30d', 0):+.2f}%"),
                ("ATH",       f"${data.get('ath'):,.4f}"                   if data.get("ath")            else "N/A"),
                ("ATH Δ",     f"{data.get('ath_change_pct', 0):+.1f}%"),
                ("24H Vol",   format_number(data.get("volume_24h", 0))),
                ("Supply",    f"{data.get('circulating_supply',0):,.0f}"   if data.get("circulating_supply") else "N/A"),
                ("Prev Close",price_str),
            ]
        for label, val in metrics:
            ca, cb = st.columns([1, 1])
            ca.markdown(f"<span style='color:#484f58;font-size:0.78rem;font-weight:600;'>{label}</span>", unsafe_allow_html=True)
            cb.markdown(f"<span style='color:#e6edf3;font-size:0.78rem;font-weight:700;'>{val}</span>",   unsafe_allow_html=True)

    with col_macd:
        if has_hist:
            st.markdown("""<div style="color:#8b949e;font-size:0.72rem;font-weight:700;
                text-transform:uppercase;letter-spacing:1px;margin-bottom:0.8rem;">📊 MACD</div>""",
                unsafe_allow_html=True)
            fig_macd = go.Figure()
            macd_hist = inds["hist_macd"]
            bar_colors = ["rgba(63,185,80,0.6)" if v >= 0 else "rgba(248,81,73,0.6)" for v in macd_hist]
            fig_macd.add_trace(go.Bar(x=history.index, y=macd_hist, marker_color=bar_colors, name="Histogram", showlegend=False))
            fig_macd.add_trace(go.Scatter(x=history.index, y=inds["macd"],   line=dict(color="#58a6ff", width=1.5), name="MACD"))
            fig_macd.add_trace(go.Scatter(x=history.index, y=inds["signal"], line=dict(color="#f7c948", width=1.5), name="Signal"))
            fig_macd.update_layout(
                plot_bgcolor="rgba(13,17,23,0)", paper_bgcolor="rgba(13,17,23,0)",
                font=dict(color="#6e7681", family="Inter", size=10),
                height=230, margin=dict(l=0, r=0, t=5, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=9, color="#8b949e")),
                xaxis=dict(gridcolor="rgba(48,54,61,0.4)", showgrid=True, zeroline=False),
                yaxis=dict(gridcolor="rgba(48,54,61,0.4)", showgrid=True, zeroline=False),
            )
            st.plotly_chart(fig_macd, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── AI Analysis — Chat Style ─────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:1rem;">
      <div style="width:34px;height:34px;border-radius:50%;
          background:linear-gradient(135deg,#58a6ff,#a78bfa);
          display:flex;align-items:center;justify-content:center;font-size:1rem;
          box-shadow:0 0 12px rgba(88,166,255,0.4);">🤖</div>
      <div>
        <div style="color:#e6edf3;font-size:0.88rem;font-weight:700;">FinSage AI</div>
        <div style="color:#3fb950;font-size:0.7rem;font-weight:600;">● Online · Analyzing</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Render report as chat bubbles split by sections
    sections = report.split("\n\n")
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        st.markdown(f"""
        <div style="background:linear-gradient(145deg,rgba(22,27,34,0.9),rgba(13,17,23,0.95));
            border:1px solid rgba(48,54,61,0.5);border-left:3px solid rgba(88,166,255,0.5);
            border-radius:0 14px 14px 14px;padding:1rem 1.2rem;margin-bottom:0.7rem;
            box-shadow:0 2px 12px rgba(0,0,0,0.2);font-size:0.85rem;color:#c9d1d9;line-height:1.75;">
          {sec.replace(chr(10),"<br>")}
        </div>
        """, unsafe_allow_html=True)

    # Download
    st.download_button(
        label="📥 Download Full Report (.md)",
        data=report,
        file_name=f"FinSage_{ticker_sym}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )



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
