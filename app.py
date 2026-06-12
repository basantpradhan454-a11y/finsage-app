"""
FinSage — Global Financial Intelligence Platform
Free APIs: yfinance + CoinGecko
Auth: Google OAuth + Email/Password
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
from datetime import datetime

from data_fetcher import fetch_stock_data, fetch_crypto_data, fetch_ticker_bar_data
from analyzer import analyze_stock, analyze_crypto, format_number
from auth_page import render_auth_page, render_sidebar_auth, is_logged_in, get_current_user, logout
from admin_panel import render_admin_panel
from ai_assistant import render_ai_assistant
from feedback_dashboard import render_feedback_dashboard
from advanced_features import render_advanced_features
from chart_analyzer import render_chart_analyzer

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="STOX AI — Analyze. Attract. Thrive.",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ─── Hide Streamlit chrome ─── */
    #MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="manage-app-button"],
    [data-testid="stDecoration"],[data-testid="stStatusWidget"],[data-testid="stBottom"],
    .stDeployButton,.viewerBadge_container__r5tak,button[kind="header"],
    .st-emotion-cache-czk5ss,._link_gzau3_10,.st-emotion-cache-1dp5vir,
    [data-testid="stSidebarCollapsedControl"] { display:none !important; visibility:hidden !important; }

    /* ─── Base ─── */
    .stApp { background:#050a12 !important; color:#c9d1d9; font-family:'Inter',sans-serif; }
    [data-testid="stSidebar"] { background:#0a0f1a !important; border-right:1px solid #1a2535; }

    /* ─── Futuristic glow scrollbar ─── */
    ::-webkit-scrollbar { width:4px; height:4px; }
    ::-webkit-scrollbar-track { background:#0d1117; }
    ::-webkit-scrollbar-thumb { background:#1f6feb; border-radius:4px; }

    /* ─── Navbar ─── */
    .stox-navbar {
        background:linear-gradient(135deg,rgba(13,17,23,0.98),rgba(22,27,34,0.98));
        border:1px solid rgba(88,166,255,0.18);
        border-radius:14px; padding:0.7rem 1.2rem;
        margin-bottom:0.6rem;
        box-shadow:0 0 30px rgba(88,166,255,0.06),inset 0 0 30px rgba(88,166,255,0.02);
        backdrop-filter:blur(20px);
    }

    /* ─── Ticker ─── */
    .ticker-bar {
        background:linear-gradient(90deg,#0a0f1a,#0d1117,#0a0f1a);
        border:1px solid rgba(88,166,255,0.12);
        border-radius:10px; padding:0.55rem 1.1rem;
        margin-bottom:1rem; overflow-x:auto; white-space:nowrap;
        box-shadow:0 0 20px rgba(88,166,255,0.04);
    }
    .ticker-item { display:inline-block; margin-right:1.5rem; font-size:0.82rem; }
    .ticker-sym  { color:#58a6ff; font-weight:700; margin-right:4px; letter-spacing:0.03em; }
    .ticker-price{ color:#c9d1d9; margin-right:4px; }
    .up   { color:#3fb950; font-weight:600; }
    .down { color:#f85149; font-weight:600; }

    /* ─── Tabs ─── */
    .stTabs [data-baseweb="tab-list"] {
        background:rgba(22,27,34,0.8); border-radius:12px 12px 0 0;
        border:1px solid rgba(88,166,255,0.12); border-bottom:none;
        gap:0; padding:0.3rem 0.3rem 0;
        backdrop-filter:blur(10px);
    }
    .stTabs [data-baseweb="tab"] {
        background:transparent; color:#8b949e;
        border-radius:8px 8px 0 0; font-weight:600;
        font-size:0.92rem; padding:0.6rem 1.6rem; border:none;
        transition:all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background:rgba(88,166,255,0.08) !important; color:#58a6ff !important;
        border-top:2px solid #58a6ff !important;
        box-shadow:0 -4px 20px rgba(88,166,255,0.15) !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background:rgba(13,17,23,0.95); border:1px solid rgba(88,166,255,0.1);
        border-top:none; border-radius:0 0 12px 12px; padding:1.4rem;
    }

    /* ─── Buttons ─── */
    .stButton > button {
        background:linear-gradient(135deg,#161b22,#1a2535);
        color:#58a6ff; border:1px solid rgba(88,166,255,0.25);
        border-radius:8px; font-size:0.83rem; font-weight:600;
        transition:all 0.2s ease; width:100%;
    }
    .stButton > button:hover {
        background:linear-gradient(135deg,#1f6feb,#388bfd) !important;
        color:white !important; border-color:#1f6feb !important;
        box-shadow:0 0 20px rgba(31,111,235,0.4) !important;
        transform:translateY(-1px);
    }
    .stButton > button[kind="primary"] {
        background:linear-gradient(135deg,#1f6feb,#388bfd) !important;
        color:white !important; border-color:#1f6feb !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow:0 0 25px rgba(31,111,235,0.5) !important;
        transform:translateY(-1px);
    }

    /* ─── Inputs ─── */
    .stTextInput > div > div > input, .stSelectbox > div > div {
        background:#0d1117 !important; color:#c9d1d9 !important;
        border:1px solid rgba(88,166,255,0.2) !important; border-radius:8px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color:#58a6ff !important;
        box-shadow:0 0 12px rgba(88,166,255,0.2) !important;
    }

    /* ─── Metrics ─── */
    [data-testid="stMetric"] {
        background:linear-gradient(135deg,#0d1117,#161b22);
        border:1px solid rgba(88,166,255,0.1); border-radius:10px;
        padding:0.6rem 0.8rem;
        box-shadow:0 0 15px rgba(88,166,255,0.03);
    }

    /* ─── 3-dot hover menu ─── */
    .dot-menu-wrapper { position:relative; display:inline-block; }
    .dot-menu-trigger {
        background:rgba(22,27,34,0.9); border:1px solid rgba(88,166,255,0.2);
        border-radius:8px; padding:0.35rem 0.7rem; cursor:pointer;
        color:#58a6ff; font-size:1.2rem; font-weight:700;
        transition:all 0.2s; line-height:1;
        box-shadow:0 0 15px rgba(88,166,255,0.08);
    }
    .dot-menu-trigger:hover { background:#1f6feb; color:white; border-color:#1f6feb; }

    /* ─── Misc ─── */
    .meme-warning {
        background:linear-gradient(135deg,#1a0808,#2d1b1b);
        border:1px solid rgba(248,81,73,0.4); border-radius:8px;
        padding:0.75rem 0.9rem; color:#f85149; font-size:0.83rem;
        margin-bottom:0.9rem;
        box-shadow:0 0 15px rgba(248,81,73,0.08);
    }
    .disclaimer {
        background:linear-gradient(135deg,#161b22,#1a2010);
        border-left:3px solid rgba(210,153,34,0.6);
        border-radius:0 8px 8px 0; padding:0.7rem 0.9rem;
        color:#8b949e; font-size:0.78rem; margin-top:0.9rem;
    }
    .user-badge {
        background:rgba(22,27,34,0.9); border:1px solid rgba(88,166,255,0.2);
        border-radius:20px; padding:0.3rem 0.9rem;
        color:#c9d1d9; font-size:0.82rem; display:inline-flex;
        align-items:center; gap:0.4rem;
    }
    hr { border-color:rgba(88,166,255,0.1) !important; }
    [data-testid="stMarkdownContainer"] h3 { color:#e6edf3; }
</style>
""", unsafe_allow_html=True)

# ── Session State ───────────────────────────────────────────────────────────── ──────────────────────────────────────────────────────────────
if "active_page" not in st.session_state:
    st.session_state.active_page = "main"

defaults = {
    "user": None,
    "stock_data": None, "stock_report": None,
    "crypto_data": None, "crypto_report": None,
    "meme_data": None, "meme_report": None,
    "ticker_data": [], "last_ticker_refresh": 0,
    "stock_selected": "", "crypto_selected": "", "meme_selected": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Public App — Optional Sidebar Login ──────────────────────────────────────
render_sidebar_auth()
user = get_current_user()

# ── Ticker refresh ─────────────────────────────────────────────────────────────
now_ts = time.time()
if now_ts - st.session_state.last_ticker_refresh > 60:
    st.session_state.ticker_data = fetch_ticker_bar_data()
    st.session_state.last_ticker_refresh = now_ts

# ── Navbar ─────────────────────────────────────────────────────────────────────
nb_left, nb_right = st.columns([6, 1])
with nb_left:
    st.markdown("""
    <div class="stox-navbar" style="display:flex;align-items:center;gap:0.8rem;">
        <img src="https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"
             style="height:46px;width:46px;border-radius:10px;object-fit:cover;box-shadow:0 0 15px rgba(88,166,255,0.3);">
        <div>
            <div style="font-size:1.4rem;font-weight:900;background:linear-gradient(90deg,#58a6ff,#a5d6ff,#79c0ff);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.1;letter-spacing:-0.02em;">
                STOX AI
            </div>
            <div style="font-size:0.64rem;color:#8b949e;letter-spacing:0.18em;font-weight:600;text-transform:uppercase;">
                Analyze &middot; Attract &middot; Thrive
            </div>
        </div>
        <span style="background:linear-gradient(135deg,#0f2a0f,#1a3a1a);color:#3fb950;padding:0.18rem 0.65rem;
        border-radius:20px;font-size:0.7rem;font-weight:700;border:1px solid rgba(63,185,80,0.3);
        box-shadow:0 0 10px rgba(63,185,80,0.15);letter-spacing:0.05em;">✅ 100% FREE</span>
    </div>
    """, unsafe_allow_html=True)

with nb_right:
    st.markdown("<div style='padding-top:0.4rem;'>", unsafe_allow_html=True)
    with st.popover("⋮", use_container_width=True):
        st.markdown("""
        <div style="font-size:0.9rem;font-weight:700;color:#58a6ff;margin-bottom:0.5rem;">
        ⚡ Quick Navigation
        </div>""", unsafe_allow_html=True)
        
        menu_items = {
            "🤖 AI Assistant": "🤖 AI Assistant",
            "📸 Chart Analyzer": "📸 Chart Analyzer",
            "⭐ Community": "⭐ Feedback & Community",
            "🧠 Advanced Intel": "🧠 Advanced Intelligence",
        }
        for label, page_key in menu_items.items():
            if st.button(label, key=f"nav_{label}", use_container_width=True):
                st.session_state.active_page = page_key
                st.rerun()
        
        if user:
            st.markdown("---")
            if st.button("🚪 Logout", key="logout_dot_menu", use_container_width=True):
                logout()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:0.3rem 0 0.7rem;'>", unsafe_allow_html=True)

# ── Live Ticker Bar ────────────────────────────────────────────────────────────
if st.session_state.ticker_data:
    ticker_html = '<div class="ticker-bar">🔴 <b style="color:#f85149;">LIVE</b>&nbsp;&nbsp;|&nbsp;&nbsp;'
    for item in st.session_state.ticker_data:
        chg = item.get("change", 0) or 0
        p   = item.get("price", 0) or 0
        cls = "up" if chg >= 0 else "down"
        arrow = "▲" if chg >= 0 else "▼"
        ps  = f"${p:,.6f}" if p < 0.01 else f"${p:,.2f}"
        ticker_html += f'<span class="ticker-item"><span class="ticker-sym">{item["symbol"]}</span><span class="ticker-price">{ps}</span><span class="{cls}">{arrow}{abs(chg):.2f}%</span></span>'
    ticker_html += "</div>"
    st.markdown(ticker_html, unsafe_allow_html=True)


# ── Results Renderer ───────────────────────────────────────────────────────────
def render_results(data, report):
    if not data or not report:
        return

    name = data.get("name", data.get("ticker", ""))
    ticker = data.get("ticker", "")
    price = data.get("current_price", 0) or 0
    change = data.get("change_pct", 0) or 0
    market_cap = data.get("market_cap", 0) or 0
    risk = data.get("risk_score", 5) or 5
    vol = data.get("volatility_annualized", 0) or 0
    currency = data.get("currency", "USD")
    asset_t = data.get("asset_type", "Asset")

    st.markdown(f"### 📊 {name} ({ticker}) — {asset_t}")

    k1, k2, k3, k4, k5 = st.columns(5)
    if price < 0.0001:   price_str = f"${price:.8f}"
    elif price < 0.01:   price_str = f"${price:.6f}"
    else:                price_str = f"{currency} {price:,.2f}"

    with k1: st.metric("💰 Price", price_str)
    with k2: st.metric("📈 24H", f"{change:+.2f}%")
    with k3: st.metric("🏦 Mkt Cap", format_number(market_cap))
    with k4: st.metric("⚡ Volatility", f"{vol:.1f}%")
    with k5: st.metric("🎯 Risk", f"{risk}/10")

    st.markdown("---")
    col_chart, col_info = st.columns([3, 2])

    with col_chart:
        history = data.get("history")
        if history is not None and isinstance(history, pd.DataFrame) and not history.empty:
            st.markdown("#### 📈 30-Day Price Chart")
            close_col = "Close" if "Close" in history.columns else history.columns[0]
            y_data = history[close_col]
            if len(y_data) > 1:
                is_up = float(y_data.iloc[-1]) >= float(y_data.iloc[0])
                color = "#3fb950" if is_up else "#f85149"
                fill_color = "rgba(63,185,80,0.1)" if is_up else "rgba(248,81,73,0.1)"
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=history.index, y=y_data, mode="lines",
                    line=dict(color=color, width=2),
                    fill="tozeroy", fillcolor=fill_color,
                    hovertemplate="<b>%{x}</b><br>%{y:,.6f}<extra></extra>"
                ))
                fig.update_layout(
                    plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                    font=dict(color="#c9d1d9"),
                    xaxis=dict(gridcolor="#21262d"),
                    yaxis=dict(gridcolor="#21262d"),
                    margin=dict(l=0, r=0, t=10, b=0),
                    height=270, showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

    with col_info:
        st.markdown("#### 📋 Key Metrics")
        if data.get("asset_type") == "Stock":
            metrics = [
                ("Sector", data.get("sector", "N/A")),
                ("P/E Ratio", f"{data.get('pe_ratio'):.1f}x" if data.get("pe_ratio") else "N/A"),
                ("EPS", f"{currency} {data.get('eps'):.2f}" if data.get("eps") else "N/A"),
                ("Beta", f"{data.get('beta'):.2f}" if data.get("beta") else "N/A"),
                ("52W High", f"{currency} {data.get('week_52_high'):,.2f}" if data.get("week_52_high") else "N/A"),
                ("52W Low", f"{currency} {data.get('week_52_low'):,.2f}" if data.get("week_52_low") else "N/A"),
                ("Analyst", data.get("recommendation", "N/A")),
            ]
        else:
            metrics = [
                ("Market Rank", f"#{data.get('market_cap_rank', 'N/A')}"),
                ("7D Change", f"{data.get('change_7d', 0):+.2f}%"),
                ("30D Change", f"{data.get('change_30d', 0):+.2f}%"),
                ("ATH", f"${data.get('ath'):,.6f}" if data.get("ath") else "N/A"),
                ("ATH Δ", f"{data.get('ath_change_pct', 0):+.1f}%"),
                ("24H Vol", format_number(data.get("volume_24h", 0))),
                ("Supply", f"{data.get('circulating_supply', 0):,.0f}" if data.get("circulating_supply") else "N/A"),
            ]
        for label, val in metrics:
            ca, cb = st.columns([1, 1])
            ca.markdown(f"<span style='color:#8b949e;font-size:0.82rem;'>{label}</span>", unsafe_allow_html=True)
            cb.markdown(f"<span style='color:#c9d1d9;font-size:0.82rem;font-weight:600;'>{val}</span>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📄 Full Analysis Report")
    st.markdown(report)
    st.download_button(
        label="📥 Download Report (.md)",
        data=report,
        file_name=f"FinSage_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
# ── Page Router ───────────────────────────────────────────────────────────────
def _back_btn(key):
    if st.button("← Back to Dashboard", key=key):
        st.session_state.active_page = "main"
        st.rerun()

_ap = st.session_state.get("active_page", "main")
if _ap == "🤖 AI Assistant":
    _back_btn("back_ai"); render_ai_assistant(); st.stop()
elif _ap == "📸 Chart Analyzer":
    _back_btn("back_ca"); render_chart_analyzer(); st.stop()
elif _ap == "⭐ Feedback & Community":
    _back_btn("back_fb"); render_feedback_dashboard(); st.stop()
elif _ap == "🧠 Advanced Intelligence":
    _back_btn("back_adv"); render_advanced_features(); st.stop()

tab1, tab2, tab3 = st.tabs(["🌍  Global Stocks", "₿  Cryptocurrency", "🎭  Meme Coins"])

# ─── TAB 1: STOCKS ────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 🌍 Global Stock Analysis")
    st.markdown("Real-time data from NSE India, US, UK, Germany, Japan & more.")

    s1, s2 = st.columns([2, 1])
    with s1:
        stock_ticker = st.text_input("Enter Stock Ticker Symbol",
            placeholder="e.g. AAPL, RELIANCE.NS, TCS.NS, TSLA", key="stock_input")
    with s2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🇮🇳 NSE: RELIANCE.NS · TCS.NS · INFY.NS")
        st.caption("🇺🇸 US: AAPL · TSLA · NVDA · MSFT")
        st.caption("🌐 Others: .L (London) · .DE (Germany)")

    st.markdown("**⚡ Quick Pick:**")
    sc = st.columns(8)
    for i, s in enumerate(["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "RELIANCE.NS", "TCS.NS", "INFY.NS"]):
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
                    st.session_state.stock_data = d
                    st.session_state.stock_report = analyze_stock(d)
                    st.session_state.stock_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning("⚠️ Please enter or select a stock ticker.")

    st.markdown("---")
    if st.session_state.stock_data:
        render_results(st.session_state.stock_data, st.session_state.stock_report)
    else:
        st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">🌍</div><p>Enter a ticker symbol above and click <b>Analyze Stock</b>.</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Data from Yahoo Finance (yfinance). For educational purposes only. Not SEBI-registered investment advice.</div>', unsafe_allow_html=True)


# ─── TAB 2: CRYPTO ────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### ₿ Cryptocurrency Analysis")
    st.markdown("Real-time data from CoinGecko — 100+ coins supported.")

    c1, c2 = st.columns([2, 1])
    with c1:
        crypto_ticker = st.text_input("Enter Crypto Symbol",
            placeholder="e.g. BTC, ETH, SOL, BNB, ADA, XRP", key="crypto_input")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Large Cap: BTC · ETH · BNB · SOL")
        st.caption("Mid Cap: ADA · AVAX · DOT · MATIC")

    st.markdown("**⚡ Quick Pick:**")
    cc = st.columns(8)
    for i, c in enumerate(["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT"]):
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
                    st.session_state.crypto_data = d
                    st.session_state.crypto_report = analyze_crypto(d)
                    st.session_state.crypto_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning("⚠️ Please enter or select a crypto symbol.")

    st.markdown("---")
    if st.session_state.crypto_data:
        render_results(st.session_state.crypto_data, st.session_state.crypto_report)
    else:
        st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">₿</div><p>Enter a crypto symbol and click <b>Analyze Crypto</b>.</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Data from CoinGecko. Crypto is highly volatile & unregulated by SEBI. Educational purposes only.</div>', unsafe_allow_html=True)


# ─── TAB 3: MEME COINS ────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 🎭 Meme Coin Analysis")
    st.markdown('<div class="meme-warning">⚠️ <b>HIGH RISK:</b> Meme coins are purely speculative. Prices can crash 80-90% overnight. Only use money you can afford to lose completely.</div>', unsafe_allow_html=True)

    m1, m2 = st.columns([2, 1])
    with m1:
        meme_ticker = st.text_input("Enter Meme Coin Symbol",
            placeholder="e.g. DOGE, SHIB, PEPE, FLOKI, BONK", key="meme_input")
    with m2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Popular: DOGE · SHIB · PEPE · FLOKI")
        st.caption("Trending: BONK · WIF · MEME · TURBO")

    st.markdown("**⚡ Quick Pick:**")
    mc = st.columns(8)
    for i, m in enumerate(["DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME", "TURBO"]):
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
                    st.session_state.meme_data = d
                    st.session_state.meme_report = analyze_crypto(d)
                    st.session_state.meme_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning("⚠️ Please enter or select a meme coin symbol.")

    st.markdown("---")
    if st.session_state.meme_data:
        render_results(st.session_state.meme_data, st.session_state.meme_report)
    else:
        st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">🎭</div><p>Enter a meme coin symbol and click <b>Analyze Meme Coin</b>.</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Meme coins are unregulated & highly speculative. Not SEBI advice. Never invest borrowed money in meme coins.</div>', unsafe_allow_html=True)



# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("<hr style='border-color:#30363d;margin-top:1.5rem;'>", unsafe_allow_html=True)
f1, f2 = st.columns(2)
with f1:
    st.markdown("<span style='color:#8b949e;font-size:0.75rem;'>📊 <b>FinSage</b> — Global Financial Intelligence Platform</span>", unsafe_allow_html=True)
with f2:
    st.markdown("<span style='color:#6e7681;font-size:0.75rem;display:block;text-align:right;'>Data: Yahoo Finance · CoinGecko &nbsp;|&nbsp; For educational purposes only</span>", unsafe_allow_html=True)
