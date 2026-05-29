"""
FinSage — Global Financial Intelligence Platform
Auth: Google OAuth 2.0
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
from datetime import datetime

from data_fetcher import fetch_stock_data, fetch_crypto_data, fetch_ticker_bar_data
from analyzer import analyze_stock, analyze_crypto, format_number, get_risk_label
from auth import (
    get_google_auth_url, exchange_code_for_token, get_user_info,
    generate_state, is_logged_in, get_current_user, logout,
    GOOGLE_CLIENT_ID
)
from privacy_policy import get_privacy_policy

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSage — Global Financial Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="manage-app-button"] { display: none !important; }
    .viewerBadge_container__r5tak { display: none !important; }
    .stDeployButton { display: none !important; }

    .stApp { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stSidebar"] { background-color: #161b22; }

    /* ── Auth Page ── */
    .auth-wrapper {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .auth-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 20px;
        padding: 3rem 2.5rem;
        max-width: 440px;
        width: 100%;
        margin: 0 auto;
        text-align: center;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .auth-logo { font-size: 3.5rem; font-weight: 900; color: #58a6ff; margin-bottom: 0.2rem; }
    .auth-tagline { color: #8b949e; font-size: 0.95rem; margin-bottom: 2rem; }
    .auth-divider {
        border: none;
        border-top: 1px solid #30363d;
        margin: 1.5rem 0;
    }
    .google-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        background: #ffffff;
        color: #1f1f1f;
        border: none;
        border-radius: 10px;
        padding: 0.85rem 1.5rem;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        width: 100%;
        text-decoration: none;
        transition: background 0.2s;
        margin-bottom: 0.8rem;
    }
    .google-btn:hover { background: #f0f0f0; }
    .auth-features {
        text-align: left;
        margin: 1.5rem 0;
    }
    .auth-features li {
        color: #8b949e;
        font-size: 0.85rem;
        margin-bottom: 0.4rem;
        list-style: none;
        padding-left: 0;
    }
    .auth-footer {
        color: #8b949e;
        font-size: 0.75rem;
        margin-top: 1.5rem;
        line-height: 1.6;
    }
    .auth-footer a { color: #58a6ff; text-decoration: none; }

    /* ── Navbar ── */
    .finsage-navbar {
        background: #161b22;
        border-bottom: 1px solid #30363d;
        padding: 0.7rem 2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0;
    }
    .navbar-brand { font-size: 1.4rem; font-weight: 800; color: #58a6ff; }
    .navbar-tagline { color: #8b949e; font-size: 0.82rem; }
    .user-avatar {
        width: 34px; height: 34px;
        border-radius: 50%;
        border: 2px solid #58a6ff;
        vertical-align: middle;
        margin-right: 8px;
    }
    .user-name { color: #c9d1d9; font-size: 0.9rem; font-weight: 600; vertical-align: middle; }

    /* ── Ticker ── */
    .ticker-bar {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        margin-bottom: 1.2rem;
        overflow-x: auto;
        white-space: nowrap;
    }
    .ticker-item { display: inline-block; margin-right: 1.5rem; font-size: 0.85rem; }
    .ticker-sym { color: #58a6ff; font-weight: 700; margin-right: 4px; }
    .ticker-price { color: #c9d1d9; margin-right: 4px; }
    .up { color: #3fb950; }
    .down { color: #f85149; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: #161b22;
        border-radius: 12px 12px 0 0;
        border: 1px solid #30363d;
        border-bottom: none;
        gap: 0;
        padding: 0.4rem 0.4rem 0;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #8b949e;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        font-size: 1rem;
        padding: 0.7rem 2rem;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background: #0d1117 !important;
        color: #58a6ff !important;
        border-top: 2px solid #58a6ff !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background: #0d1117;
        border: 1px solid #30363d;
        border-top: none;
        border-radius: 0 0 12px 12px;
        padding: 1.5rem;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: #21262d;
        color: #58a6ff;
        border: 1px solid #30363d;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 0.4rem 0.8rem;
        width: 100%;
    }
    .stButton > button:hover { background: #1f6feb; color: white; border-color: #1f6feb; }

    /* ── Meme Warning ── */
    .meme-warning {
        background: #2d1b1b;
        border: 1px solid #f85149;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        color: #f85149;
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }

    /* ── Disclaimer ── */
    .disclaimer {
        background: #161b22;
        border-left: 4px solid #d29922;
        border-radius: 0 8px 8px 0;
        padding: 0.8rem 1rem;
        color: #8b949e;
        font-size: 0.8rem;
        margin-top: 1rem;
    }

    /* ── Privacy Page ── */
    .privacy-container {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 2rem 2.5rem;
        max-width: 900px;
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
defaults = {
    "user": None,
    "auth_state": None,
    "page": "login",           # login | dashboard | privacy
    "stock_data": None, "stock_report": None,
    "crypto_data": None, "crypto_report": None,
    "meme_data": None, "meme_report": None,
    "ticker_data": [], "last_ticker_refresh": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# HANDLE OAUTH CALLBACK (code in URL params)
# ══════════════════════════════════════════════════════════════════════════════
params = st.query_params
if "code" in params and st.session_state.user is None:
    code = params["code"]
    with st.spinner("Signing you in..."):
        token_data = exchange_code_for_token(code)
        if "access_token" in token_data:
            user_info = get_user_info(token_data["access_token"])
            st.session_state.user = {
                "name": user_info.get("name", "User"),
                "email": user_info.get("email", ""),
                "picture": user_info.get("picture", ""),
                "sub": user_info.get("sub", ""),
            }
            st.session_state.page = "dashboard"
            st.query_params.clear()
            st.rerun()
        else:
            st.error("❌ Authentication failed. Please try again.")
            st.query_params.clear()


# ══════════════════════════════════════════════════════════════════════════════
# PRIVACY POLICY PAGE
# ══════════════════════════════════════════════════════════════════════════════
def show_privacy_policy():
    # Minimal navbar
    st.markdown("""
    <div class="finsage-navbar">
        <div>
            <span class="navbar-brand">📊 FinSage</span>
            <span class="navbar-tagline">&nbsp;&nbsp;Global Financial Intelligence Platform</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    back_col, _ = st.columns([1, 5])
    with back_col:
        if st.button("← Back to Login"):
            st.session_state.page = "login"
            st.rerun()

    with st.container():
        st.markdown(get_privacy_policy())

    st.markdown("""
    <div style="text-align:center;margin-top:2rem;">
        <a href="#" style="color:#58a6ff;font-size:0.85rem;">↑ Back to top</a>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    # Generate OAuth state
    if not st.session_state.auth_state:
        st.session_state.auth_state = generate_state()

    auth_url = get_google_auth_url(st.session_state.auth_state) if GOOGLE_CLIENT_ID else "#"
    creds_ready = bool(GOOGLE_CLIENT_ID)

    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown(f"""
        <div class="auth-card">
            <div class="auth-logo">📊 FinSage</div>
            <div class="auth-tagline">Global Financial Intelligence Platform<br>
                <span style="font-size:0.8rem;color:#3fb950;">✅ Stocks · Cryptocurrency · Meme Coins</span>
            </div>
            <hr class="auth-divider">
            <p style="color:#c9d1d9;font-size:0.95rem;margin-bottom:1.2rem;font-weight:600;">
                Sign in to access FinSage
            </p>
            {'<a href="' + auth_url + '" class="google-btn"><svg width="20" height="20" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.14 0 5.95 1.08 8.17 2.84L38.34 6.1C34.52 2.31 29.53 0 24 0 14.62 0 6.63 5.47 2.63 13.4l7.08 5.5C11.63 13.15 17.35 9.5 24 9.5z"/><path fill="#4285F4" d="M46.52 24.5c0-1.6-.14-3.14-.4-4.64H24v9.27h12.67c-.55 2.93-2.2 5.41-4.68 7.09l7.27 5.65C43.52 38.02 46.52 31.76 46.52 24.5z"/><path fill="#FBBC05" d="M9.71 28.9A14.6 14.6 0 0 1 9.5 24c0-1.7.29-3.34.79-4.9L3.2 13.6A23.9 23.9 0 0 0 0 24c0 3.84.9 7.48 2.5 10.7l7.21-5.8z"/><path fill="#34A853" d="M24 48c5.92 0 10.88-1.96 14.52-5.32l-7.27-5.65c-2 1.35-4.57 2.15-7.25 2.15-6.65 0-12.29-4.49-14.3-10.5l-7.08 5.5C6.62 42.52 14.62 48 24 48z"/><path fill="none" d="M0 0h48v48H0z"/></svg>Continue with Google</a>' if creds_ready else '<div style="background:#21262d;border:1px solid #f85149;border-radius:10px;padding:1rem;color:#f85149;font-size:0.85rem;">⚠️ Google OAuth credentials not configured yet.<br>Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to Streamlit secrets.</div>'}
            <ul class="auth-features">
                <li>✅ Real-time stock analysis — NSE India, US & global markets</li>
                <li>₿ Live cryptocurrency data — BTC, ETH, SOL & 100+ coins</li>
                <li>🎭 Meme coin tracker — DOGE, SHIB, PEPE & more</li>
                <li>📥 Download full analysis reports</li>
                <li>🔒 Secure — we never access your financial accounts</li>
            </ul>
            <hr class="auth-divider">
            <div class="auth-footer">
                By signing in, you agree to our
                <span style="color:#58a6ff;cursor:pointer;" onclick="void(0)">Terms of Service</span>
                and acknowledge our
                <a href="?page=privacy" target="_self">Privacy Policy</a>.<br><br>
                FinSage only accesses your name, email and profile picture from Google.
                We never share or sell your data.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Privacy Policy link via button (below the card)
    st.markdown("<br>", unsafe_allow_html=True)
    _, pc, _ = st.columns([2, 1, 2])
    with pc:
        if st.button("🔒 View Privacy Policy", use_container_width=True):
            st.session_state.page = "privacy"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def render_results(data, report):
    if not data or not report:
        return

    name = data.get("name", data.get("ticker"))
    ticker = data.get("ticker")
    price = data.get("current_price", 0)
    change = data.get("change_pct", 0)
    market_cap = data.get("market_cap", 0)
    risk = data.get("risk_score", 5)
    vol = data.get("volatility_annualized", 0)
    currency = data.get("currency", "USD")
    asset_t = data.get("asset_type", "Asset")

    st.markdown(f"### 📊 {name} ({ticker}) — {asset_t}")
    k1, k2, k3, k4, k5 = st.columns(5)
    price_str = (f"${price:,.8f}" if price < 0.0001
                 else f"${price:,.6f}" if price < 0.01
                 else f"{currency} {price:,.2f}")
    with k1: st.metric("💰 Price", price_str)
    with k2: st.metric("📈 24H Change", f"{change:+.2f}%")
    with k3: st.metric("🏦 Market Cap", format_number(market_cap))
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
            x_data = history.index
            if len(y_data) > 1:
                color = "#3fb950" if float(y_data.iloc[-1]) >= float(y_data.iloc[0]) else "#f85149"
                fill_color = "rgba(63,185,80,0.1)" if color == "#3fb950" else "rgba(248,81,73,0.1)"
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=x_data, y=y_data, mode="lines",
                    line=dict(color=color, width=2),
                    fill="tozeroy", fillcolor=fill_color, name="Price",
                    hovertemplate="<b>%{x}</b><br>Price: %{y:,.4f}<extra></extra>"
                ))
                fig.update_layout(
                    plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                    font=dict(color="#c9d1d9"),
                    xaxis=dict(gridcolor="#21262d"),
                    yaxis=dict(gridcolor="#21262d"),
                    margin=dict(l=0, r=0, t=20, b=0),
                    height=280, showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

    with col_info:
        st.markdown("#### 📋 Key Metrics")
        if data.get("asset_type") == "Stock":
            metrics = {
                "Sector": data.get("sector", "N/A"),
                "P/E Ratio": f"{data.get('pe_ratio'):.1f}x" if data.get("pe_ratio") else "N/A",
                "EPS": f"{currency} {data.get('eps'):.2f}" if data.get("eps") else "N/A",
                "Beta": f"{data.get('beta'):.2f}" if data.get("beta") else "N/A",
                "52W High": f"{currency} {data.get('week_52_high'):,.2f}" if data.get("week_52_high") else "N/A",
                "52W Low": f"{currency} {data.get('week_52_low'):,.2f}" if data.get("week_52_low") else "N/A",
                "Recommendation": data.get("recommendation", "N/A"),
            }
        else:
            metrics = {
                "Market Rank": f"#{data.get('market_cap_rank', 'N/A')}",
                "7D Change": f"{data.get('change_7d', 0):+.2f}%",
                "30D Change": f"{data.get('change_30d', 0):+.2f}%",
                "ATH": f"${data.get('ath'):,.6f}" if data.get("ath") else "N/A",
                "ATH Change": f"{data.get('ath_change_pct', 0):+.1f}%",
                "24H Volume": format_number(data.get("volume_24h", 0)),
                "Supply": f"{data.get('circulating_supply', 0):,.0f}" if data.get("circulating_supply") else "N/A",
            }
        for k, v in metrics.items():
            ca, cb = st.columns([1, 1])
            ca.markdown(f"<span style='color:#8b949e;font-size:0.85rem;'>{k}</span>", unsafe_allow_html=True)
            cb.markdown(f"<span style='color:#c9d1d9;font-size:0.85rem;font-weight:600;'>{v}</span>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📄 Full Analysis Report")
    st.markdown(report)
    st.download_button(
        label="📥 Download Report",
        data=report,
        file_name=f"FinSage_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def show_dashboard():
    user = get_current_user()

    # Live ticker refresh
    now_ts = time.time()
    if now_ts - st.session_state.last_ticker_refresh > 60:
        st.session_state.ticker_data = fetch_ticker_bar_data()
        st.session_state.last_ticker_refresh = now_ts

    # ── Navbar ────────────────────────────────────────────────────────────────
    nav_left, nav_right = st.columns([3, 1])
    with nav_left:
        st.markdown("""
        <div style="padding:0.7rem 0;">
            <span style="font-size:1.4rem;font-weight:800;color:#58a6ff;">📊 FinSage</span>
            <span style="color:#8b949e;font-size:0.82rem;">&nbsp;&nbsp;Global Financial Intelligence Platform</span>
            &nbsp;&nbsp;
            <span style="background:#1f3a1f;color:#3fb950;padding:0.15rem 0.6rem;border-radius:20px;font-size:0.75rem;font-weight:600;">✅ 100% FREE</span>
        </div>
        """, unsafe_allow_html=True)
    with nav_right:
        st.markdown("<div style='padding-top:0.3rem;'></div>", unsafe_allow_html=True)
        ucol, bcol = st.columns([2, 1])
        with ucol:
            pic = user.get("picture", "")
            name = user.get("name", "User").split()[0]
            if pic:
                st.markdown(f"""<div style='text-align:right;padding-top:0.5rem;'>
                    <img src='{pic}' style='width:30px;height:30px;border-radius:50%;border:2px solid #58a6ff;vertical-align:middle;margin-right:6px;'>
                    <span style='color:#c9d1d9;font-size:0.88rem;font-weight:600;'>{name}</span>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:right;padding-top:0.5rem;color:#c9d1d9;font-size:0.88rem;font-weight:600;'>👤 {name}</div>", unsafe_allow_html=True)
        with bcol:
            if st.button("Sign Out", key="signout"):
                logout()

    st.markdown("<hr style='border-color:#30363d;margin:0 0 0.8rem;'>", unsafe_allow_html=True)

    # ── Ticker Bar ────────────────────────────────────────────────────────────
    if st.session_state.ticker_data:
        ticker_html = '<div class="ticker-bar">🔴 &nbsp;<b style="color:#f85149;">LIVE</b>&nbsp;&nbsp;|&nbsp;&nbsp;'
        for item in st.session_state.ticker_data:
            chg = item.get("change", 0)
            cls = "up" if chg >= 0 else "down"
            arrow = "▲" if chg >= 0 else "▼"
            price = item.get("price", 0)
            price_str = f"${price:,.6f}" if price < 0.01 else f"${price:,.2f}"
            ticker_html += (
                f'<span class="ticker-item">'
                f'<span class="ticker-sym">{item["symbol"]}</span>'
                f'<span class="ticker-price">{price_str}</span>'
                f'<span class="{cls}">{arrow}{abs(chg):.2f}%</span>'
                f'</span>'
            )
        ticker_html += "</div>"
        st.markdown(ticker_html, unsafe_allow_html=True)

    # ── Welcome message ───────────────────────────────────────────────────────
    st.markdown(f"<p style='color:#8b949e;font-size:0.9rem;'>Welcome back, <b style='color:#58a6ff;'>{user.get('name','User')}</b> 👋 — Select a tab below to start analyzing.</p>", unsafe_allow_html=True)

    # ── TABS ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["🌍  Global Stocks", "₿  Cryptocurrency", "🎭  Meme Coins"])

    # ── TAB 1: STOCKS ─────────────────────────────────────────────────────────
    with tab1:
        st.markdown("### 🌍 Global Stock Analysis")
        st.markdown("Search any stock from NSE India, US, UK, Germany, Japan and more.")
        sc1, sc2 = st.columns([2, 1])
        with sc1:
            stock_ticker = st.text_input("Enter Stock Ticker Symbol",
                placeholder="e.g. AAPL, RELIANCE.NS, TCS.NS, TSLA", key="stock_ticker_input")
        with sc2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Examples by Market:**")
            st.markdown("<span style='color:#8b949e;font-size:0.8rem;'>🇮🇳 NSE: RELIANCE.NS · TCS.NS · INFY.NS<br>🇺🇸 US: AAPL · TSLA · NVDA · MSFT<br>🌐 Others: add .L (London) · .DE (Germany)</span>", unsafe_allow_html=True)

        st.markdown("**⚡ Quick Pick:**")
        qcols = st.columns(8)
        for i, qp in enumerate(["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "RELIANCE.NS", "TCS.NS", "INFY.NS"]):
            with qcols[i]:
                if st.button(qp, key=f"sq_{qp}"):
                    st.session_state["stock_selected"] = qp

        final_stock = st.session_state.get("stock_selected", stock_ticker).strip().upper()
        if st.button("🔍 Analyze Stock", key="analyze_stock", type="primary", use_container_width=True):
            if final_stock:
                with st.spinner(f"Fetching data for **{final_stock}**..."):
                    data = fetch_stock_data(final_stock)
                    if "error" not in data:
                        st.session_state.stock_data = data
                        st.session_state.stock_report = analyze_stock(data)
                        st.session_state["stock_selected"] = ""
                    else:
                        st.error(f"❌ {data['error']}")
            else:
                st.warning("⚠️ Please enter a stock ticker symbol.")

        st.markdown("---")
        if st.session_state.stock_data and st.session_state.stock_report:
            render_results(st.session_state.stock_data, st.session_state.stock_report)
        else:
            st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:3rem;">🌍</div><p>Enter a stock ticker above and click <b>Analyze Stock</b>.</p></div>', unsafe_allow_html=True)

        st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Stock data from Yahoo Finance. Educational purposes only. Not SEBI-registered investment advice.</div>', unsafe_allow_html=True)

    # ── TAB 2: CRYPTO ─────────────────────────────────────────────────────────
    with tab2:
        st.markdown("### ₿ Cryptocurrency Analysis")
        st.markdown("Analyze major cryptocurrencies with real-time CoinGecko data.")
        cc1, cc2 = st.columns([2, 1])
        with cc1:
            crypto_ticker = st.text_input("Enter Crypto Symbol",
                placeholder="e.g. BTC, ETH, SOL, BNB, ADA, XRP", key="crypto_ticker_input")
        with cc2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Top Cryptocurrencies:**")
            st.markdown("<span style='color:#8b949e;font-size:0.8rem;'>BTC · ETH · BNB · SOL · XRP<br>ADA · AVAX · DOT · MATIC · LINK<br>LTC · ATOM · TRX · TON · UNI</span>", unsafe_allow_html=True)

        st.markdown("**⚡ Quick Pick:**")
        ccols = st.columns(8)
        for i, qp in enumerate(["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT"]):
            with ccols[i]:
                if st.button(qp, key=f"cq_{qp}"):
                    st.session_state["crypto_selected"] = qp

        final_crypto = st.session_state.get("crypto_selected", crypto_ticker).strip().upper()
        if st.button("🔍 Analyze Crypto", key="analyze_crypto", type="primary", use_container_width=True):
            if final_crypto:
                with st.spinner(f"Fetching data for **{final_crypto}**..."):
                    data = fetch_crypto_data(final_crypto)
                    if "error" not in data:
                        st.session_state.crypto_data = data
                        st.session_state.crypto_report = analyze_crypto(data)
                        st.session_state["crypto_selected"] = ""
                    else:
                        st.error(f"❌ {data['error']}")
            else:
                st.warning("⚠️ Please enter a crypto symbol.")

        st.markdown("---")
        if st.session_state.crypto_data and st.session_state.crypto_report:
            render_results(st.session_state.crypto_data, st.session_state.crypto_report)
        else:
            st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:3rem;">₿</div><p>Enter a crypto symbol above and click <b>Analyze Crypto</b>.</p></div>', unsafe_allow_html=True)

        st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Crypto data from CoinGecko. Highly volatile & unregulated by SEBI. Educational purposes only.</div>', unsafe_allow_html=True)

    # ── TAB 3: MEME COINS ─────────────────────────────────────────────────────
    with tab3:
        st.markdown("### 🎭 Meme Coin Analysis")
        st.markdown('<div class="meme-warning">⚠️ <b>HIGH RISK WARNING:</b> Meme coins are extremely speculative with no fundamental value. Prices can drop 80-90% rapidly. Only invest what you can afford to lose entirely.</div>', unsafe_allow_html=True)
        mc1, mc2 = st.columns([2, 1])
        with mc1:
            meme_ticker = st.text_input("Enter Meme Coin Symbol",
                placeholder="e.g. DOGE, SHIB, PEPE, FLOKI, BONK", key="meme_ticker_input")
        with mc2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Popular Meme Coins:**")
            st.markdown("<span style='color:#8b949e;font-size:0.8rem;'>DOGE · SHIB · PEPE · FLOKI<br>BONK · WIF · MEME · TURBO<br>BRETT · NEIRO</span>", unsafe_allow_html=True)

        st.markdown("**⚡ Quick Pick:**")
        mcols = st.columns(8)
        for i, qp in enumerate(["DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME", "TURBO"]):
            with mcols[i]:
                if st.button(qp, key=f"mq_{qp}"):
                    st.session_state["meme_selected"] = qp

        final_meme = st.session_state.get("meme_selected", meme_ticker).strip().upper()
        if st.button("🔍 Analyze Meme Coin", key="analyze_meme", type="primary", use_container_width=True):
            if final_meme:
                with st.spinner(f"Fetching data for **{final_meme}**..."):
                    data = fetch_crypto_data(final_meme)
                    if "error" not in data:
                        data["asset_type"] = "Meme Coin"
                        st.session_state.meme_data = data
                        st.session_state.meme_report = analyze_crypto(data)
                        st.session_state["meme_selected"] = ""
                    else:
                        st.error(f"❌ {data['error']}")
            else:
                st.warning("⚠️ Please enter a meme coin symbol.")

        st.markdown("---")
        if st.session_state.meme_data and st.session_state.meme_report:
            render_results(st.session_state.meme_data, st.session_state.meme_report)
        else:
            st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:3rem;">🎭</div><p>Enter a meme coin symbol above and click <b>Analyze Meme Coin</b>.</p></div>', unsafe_allow_html=True)

        st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Meme coins are highly speculative & not regulated by SEBI. For educational purposes only. Never invest more than you can lose.</div>', unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("<hr style='border-color:#30363d;margin-top:2rem;'>", unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        st.markdown("<span style='color:#8b949e;font-size:0.78rem;'>📊 <b>FinSage</b> — Global Financial Intelligence Platform</span>", unsafe_allow_html=True)
    with fc2:
        st.markdown("<span style='color:#8b949e;font-size:0.78rem;text-align:center;display:block;'>Data: Yahoo Finance · CoinGecko</span>", unsafe_allow_html=True)
    with fc3:
        if st.button("🔒 Privacy Policy", key="footer_privacy"):
            st.session_state.page = "privacy"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
# Check ?page= param
if "page" in params:
    pg = params["page"]
    if pg == "privacy":
        st.session_state.page = "privacy"

if st.session_state.page == "privacy":
    show_privacy_policy()
elif st.session_state.user is not None:
    st.session_state.page = "dashboard"
    show_dashboard()
else:
    show_login()
