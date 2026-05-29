"""
FinSage — Global Financial Intelligence Platform
Auth: Google OAuth 2.0 | Free APIs: yfinance + CoinGecko
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
from datetime import datetime

from data_fetcher import fetch_stock_data, fetch_crypto_data, fetch_ticker_bar_data
from analyzer import analyze_stock, analyze_crypto, format_number
from auth import (
    get_google_auth_url, exchange_code_for_token, get_user_info,
    generate_state, get_current_user, logout,
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
    a[data-testid="stAppViewerLink"] { display: none !important; }

    .stApp { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stSidebar"] { background-color: #161b22; }

    /* ── Auth Card ── */
    .auth-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 20px;
        padding: 2.5rem 2.2rem 2rem;
        max-width: 420px;
        width: 100%;
        margin: 2rem auto;
        text-align: center;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .auth-logo { font-size: 2.8rem; font-weight: 900; color: #58a6ff; margin: 0.5rem 0 0.2rem; }
    .auth-tagline { color: #8b949e; font-size: 0.9rem; margin-bottom: 1.5rem; }
    .auth-divider { border: none; border-top: 1px solid #30363d; margin: 1.2rem 0; }

    .google-signin-btn {
        display: block;
        background: #ffffff;
        color: #1f1f1f !important;
        border-radius: 10px;
        padding: 0.8rem 1.2rem;
        font-size: 0.95rem;
        font-weight: 600;
        text-decoration: none !important;
        margin-bottom: 0.7rem;
        transition: background 0.2s, box-shadow 0.2s;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    .google-signin-btn:hover { background: #f5f5f5; box-shadow: 0 4px 14px rgba(0,0,0,0.4); }

    .demo-notice {
        background: #1c2333;
        border: 1px solid #388bfd;
        border-radius: 8px;
        padding: 0.65rem 0.9rem;
        color: #8b949e;
        font-size: 0.78rem;
        margin-top: 0.5rem;
    }

    .auth-features { text-align: left; margin: 1.2rem 0 0.5rem; }
    .auth-features li {
        color: #8b949e; font-size: 0.82rem;
        margin-bottom: 0.35rem; list-style: none;
    }
    .auth-footer { color: #6e7681; font-size: 0.73rem; margin-top: 1.2rem; line-height: 1.6; }
    .auth-footer a { color: #58a6ff; text-decoration: none; }

    /* ── Navbar ── */
    .fs-navbar {
        background: #161b22;
        border-bottom: 1px solid #30363d;
        padding: 0.65rem 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .fs-brand { font-size: 1.35rem; font-weight: 800; color: #58a6ff; }
    .fs-tagline { color: #8b949e; font-size: 0.8rem; margin-left: 0.7rem; }

    /* ── Ticker ── */
    .ticker-bar {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 10px; padding: 0.55rem 1.1rem;
        margin-bottom: 1rem; overflow-x: auto; white-space: nowrap;
    }
    .ticker-item { display: inline-block; margin-right: 1.4rem; font-size: 0.83rem; }
    .ticker-sym { color: #58a6ff; font-weight: 700; margin-right: 3px; }
    .ticker-price { color: #c9d1d9; margin-right: 3px; }
    .up { color: #3fb950; } .down { color: #f85149; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: #161b22; border-radius: 12px 12px 0 0;
        border: 1px solid #30363d; border-bottom: none;
        gap: 0; padding: 0.35rem 0.35rem 0;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent; color: #8b949e;
        border-radius: 8px 8px 0 0; font-weight: 600;
        font-size: 0.95rem; padding: 0.65rem 1.8rem; border: none;
    }
    .stTabs [aria-selected="true"] {
        background: #0d1117 !important; color: #58a6ff !important;
        border-top: 2px solid #58a6ff !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background: #0d1117; border: 1px solid #30363d;
        border-top: none; border-radius: 0 0 12px 12px; padding: 1.4rem;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: #21262d; color: #58a6ff;
        border: 1px solid #30363d; border-radius: 8px;
        font-size: 0.83rem; font-weight: 600; width: 100%;
    }
    .stButton > button:hover { background: #1f6feb; color: white; border-color: #1f6feb; }

    /* ── Meme Warning ── */
    .meme-warning {
        background: #2d1b1b; border: 1px solid #f85149;
        border-radius: 8px; padding: 0.75rem 0.9rem;
        color: #f85149; font-size: 0.83rem; margin-bottom: 0.9rem;
    }

    /* ── Disclaimer ── */
    .disclaimer {
        background: #161b22; border-left: 4px solid #d29922;
        border-radius: 0 8px 8px 0; padding: 0.7rem 0.9rem;
        color: #8b949e; font-size: 0.78rem; margin-top: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
defaults = {
    "user": None, "auth_state": None, "page": "login",
    "stock_data": None, "stock_report": None,
    "crypto_data": None, "crypto_report": None,
    "meme_data": None, "meme_report": None,
    "ticker_data": [], "last_ticker_refresh": 0,
    "stock_selected": "", "crypto_selected": "", "meme_selected": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# HANDLE OAUTH CALLBACK
# ══════════════════════════════════════════════════════════════════════════════
params = st.query_params

if "code" in params and st.session_state.user is None:
    with st.spinner("🔄 Signing you in with Google..."):
        try:
            token_data = exchange_code_for_token(params["code"])
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
                st.error(f"❌ Google sign-in failed: {token_data.get('error_description', 'Unknown error')}")
                st.query_params.clear()
        except Exception as e:
            st.error(f"❌ Authentication error: {str(e)}")
            st.query_params.clear()

if "page" in params and params["page"] == "privacy":
    st.session_state.page = "privacy"


# ══════════════════════════════════════════════════════════════════════════════
# PRIVACY POLICY PAGE
# ══════════════════════════════════════════════════════════════════════════════
def show_privacy_policy():
    st.markdown("""
    <div class="fs-navbar">
        <div><span class="fs-brand">📊 FinSage</span>
        <span class="fs-tagline">Global Financial Intelligence Platform</span></div>
    </div><br>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1, 6])
    with c1:
        if st.button("← Back"):
            st.session_state.page = "login" if st.session_state.user is None else "dashboard"
            st.rerun()

    with st.container():
        st.markdown(get_privacy_policy())


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    if not st.session_state.auth_state:
        st.session_state.auth_state = generate_state()

    creds_ready = bool(GOOGLE_CLIENT_ID)
    auth_url = get_google_auth_url(st.session_state.auth_state) if creds_ready else ""

    _, center, _ = st.columns([1, 2, 1])
    with center:
        # Logo + tagline
        st.markdown("""
        <div class="auth-card">
            <div style="font-size:3rem;">📊</div>
            <div class="auth-logo">FinSage</div>
            <div class="auth-tagline">
                Global Financial Intelligence Platform<br>
                <span style="color:#3fb950;font-size:0.78rem;">✅ Stocks &nbsp;·&nbsp; Cryptocurrency &nbsp;·&nbsp; Meme Coins</span>
            </div>
            <hr class="auth-divider">
            <p style="color:#c9d1d9;font-size:0.9rem;font-weight:600;margin-bottom:1rem;">
                Sign in to access FinSage
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Google button (always show, works when creds ready)
        if creds_ready:
            st.markdown(f"""
            <a href="{auth_url}" class="google-signin-btn">
                <svg width="18" height="18" viewBox="0 0 48 48" style="vertical-align:middle;margin-right:10px;">
                    <path fill="#EA4335" d="M24 9.5c3.14 0 5.95 1.08 8.17 2.84L38.34 6.1C34.52 2.31 29.53 0 24 0 14.62 0 6.63 5.47 2.63 13.4l7.08 5.5C11.63 13.15 17.35 9.5 24 9.5z"/>
                    <path fill="#4285F4" d="M46.52 24.5c0-1.6-.14-3.14-.4-4.64H24v9.27h12.67c-.55 2.93-2.2 5.41-4.68 7.09l7.27 5.65C43.52 38.02 46.52 31.76 46.52 24.5z"/>
                    <path fill="#FBBC05" d="M9.71 28.9A14.6 14.6 0 0 1 9.5 24c0-1.7.29-3.34.79-4.9L3.2 13.6A23.9 23.9 0 0 0 0 24c0 3.84.9 7.48 2.5 10.7l7.21-5.8z"/>
                    <path fill="#34A853" d="M24 48c5.92 0 10.88-1.96 14.52-5.32l-7.27-5.65c-2 1.35-4.57 2.15-7.25 2.15-6.65 0-12.29-4.49-14.3-10.5l-7.08 5.5C6.62 42.52 14.62 48 24 48z"/>
                </svg>
                Continue with Google
            </a>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#1c2333;border:1px dashed #388bfd;border-radius:10px;padding:1rem;margin-bottom:0.7rem;">
                <p style="color:#58a6ff;font-size:0.88rem;font-weight:700;margin:0 0 0.5rem;">🔧 Setup Required</p>
                <p style="color:#8b949e;font-size:0.8rem;margin:0;">Google OAuth credentials not yet configured.<br>
                Add <code style="color:#f0883e;">GOOGLE_CLIENT_ID</code> and <code style="color:#f0883e;">GOOGLE_CLIENT_SECRET</code> to Streamlit secrets to enable login.</p>
            </div>
            """, unsafe_allow_html=True)

        # Demo mode button — always visible
        st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)

        if st.button("🚀 Continue as Guest (Demo Mode)", use_container_width=True):
            st.session_state.user = {
                "name": "Guest User",
                "email": "guest@finsage.app",
                "picture": "",
                "sub": "guest",
            }
            st.session_state.page = "dashboard"
            st.rerun()

        st.markdown("""
        <div class="demo-notice">
            💡 <b>Demo Mode</b> gives full access to all features — stocks, crypto & meme coins.<br>
            Sign in with Google to save your profile and preferences.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <hr class="auth-divider">
        <ul class="auth-features">
            <li>✅ Real-time stocks — NSE India, US & global markets</li>
            <li>₿ Live crypto data — BTC, ETH, SOL & 100+ coins</li>
            <li>🎭 Meme coin tracker — DOGE, SHIB, PEPE & more</li>
            <li>📥 Download full analysis reports</li>
            <li>🔒 We never access your financial accounts</li>
        </ul>
        """, unsafe_allow_html=True)

    # Privacy Policy button below card
    st.markdown("<br>", unsafe_allow_html=True)
    _, pc, _ = st.columns([2, 1, 2])
    with pc:
        if st.button("🔒 Privacy Policy", use_container_width=True, key="login_privacy"):
            st.session_state.page = "privacy"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS RESULTS RENDERER
# ══════════════════════════════════════════════════════════════════════════════
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
    if price < 0.0001: price_str = f"${price:.8f}"
    elif price < 0.01: price_str = f"${price:.6f}"
    else: price_str = f"{currency} {price:,.2f}"

    with k1: st.metric("💰 Price", price_str)
    with k2: st.metric("📈 24H", f"{change:+.2f}%", delta_color="normal")
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
                    xaxis=dict(gridcolor="#21262d", showgrid=True),
                    yaxis=dict(gridcolor="#21262d", showgrid=True),
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
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def show_dashboard():
    user = get_current_user()

    # Refresh ticker every 60s
    now_ts = time.time()
    if now_ts - st.session_state.last_ticker_refresh > 60:
        st.session_state.ticker_data = fetch_ticker_bar_data()
        st.session_state.last_ticker_refresh = now_ts

    # ── Navbar ────────────────────────────────────────────────────────────────
    n1, n2 = st.columns([4, 1])
    with n1:
        st.markdown("""
        <div style="padding:0.5rem 0 0.3rem;">
            <span class="fs-brand" style="font-size:1.35rem;font-weight:800;color:#58a6ff;">📊 FinSage</span>
            <span class="fs-tagline" style="color:#8b949e;font-size:0.8rem;margin-left:0.7rem;">Global Financial Intelligence Platform</span>
            &nbsp;
            <span style="background:#1a3a1a;color:#3fb950;padding:0.15rem 0.55rem;border-radius:20px;font-size:0.72rem;font-weight:600;">✅ 100% FREE</span>
        </div>
        """, unsafe_allow_html=True)
    with n2:
        pic = user.get("picture", "")
        name = user.get("name", "User").split()[0]
        ua, ub = st.columns([2, 1])
        with ua:
            if pic:
                st.markdown(f"<div style='text-align:right;padding-top:0.4rem;'><img src='{pic}' style='width:28px;height:28px;border-radius:50%;border:2px solid #58a6ff;vertical-align:middle;margin-right:5px;'><span style='color:#c9d1d9;font-size:0.85rem;font-weight:600;'>{name}</span></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:right;padding-top:0.5rem;color:#c9d1d9;font-size:0.85rem;'>👤 {name}</div>", unsafe_allow_html=True)
        with ub:
            if st.button("Sign Out", key="signout_btn"):
                logout()

    st.markdown("<hr style='border-color:#30363d;margin:0.2rem 0 0.8rem;'>", unsafe_allow_html=True)

    # ── Ticker Bar ────────────────────────────────────────────────────────────
    if st.session_state.ticker_data:
        html = '<div class="ticker-bar">🔴 <b style="color:#f85149;">LIVE</b>&nbsp;&nbsp;|&nbsp;&nbsp;'
        for item in st.session_state.ticker_data:
            chg = item.get("change", 0) or 0
            p = item.get("price", 0) or 0
            cls = "up" if chg >= 0 else "down"
            arrow = "▲" if chg >= 0 else "▼"
            ps = f"${p:,.6f}" if p < 0.01 else f"${p:,.2f}"
            html += f'<span class="ticker-item"><span class="ticker-sym">{item["symbol"]}</span><span class="ticker-price">{ps}</span><span class="{cls}">{arrow}{abs(chg):.2f}%</span></span>'
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    # Welcome
    is_guest = user.get("sub") == "guest"
    if is_guest:
        st.markdown("<p style='color:#8b949e;font-size:0.88rem;'>👋 Welcome to <b style='color:#58a6ff;'>FinSage</b> — Guest Mode. <a href='#' style='color:#58a6ff;'>Sign in with Google</a> to save preferences.</p>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color:#8b949e;font-size:0.88rem;'>Welcome back, <b style='color:#58a6ff;'>{user.get('name','User')}</b> 👋</p>", unsafe_allow_html=True)

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["🌍  Global Stocks", "₿  Cryptocurrency", "🎭  Meme Coins"])

    # ─── TAB 1: STOCKS ────────────────────────────────────────────────────────
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
                        st.error(f"❌ {d['error']} — Check the ticker symbol and try again.")
            else:
                st.warning("⚠️ Please enter or select a stock ticker.")

        st.markdown("---")
        if st.session_state.stock_data:
            render_results(st.session_state.stock_data, st.session_state.stock_report)
        else:
            st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">🌍</div><p>Enter a ticker symbol above and click <b>Analyze Stock</b>.</p></div>', unsafe_allow_html=True)

        st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Data from Yahoo Finance (yfinance). For educational purposes only. Not SEBI-registered investment advice.</div>', unsafe_allow_html=True)

    # ─── TAB 2: CRYPTO ────────────────────────────────────────────────────────
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
            st.caption("Others: LINK · LTC · ATOM · TON")

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
                        st.error(f"❌ {d['error']} — Try symbols like BTC, ETH, SOL, BNB.")
            else:
                st.warning("⚠️ Please enter or select a crypto symbol.")

        st.markdown("---")
        if st.session_state.crypto_data:
            render_results(st.session_state.crypto_data, st.session_state.crypto_report)
        else:
            st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">₿</div><p>Enter a crypto symbol above and click <b>Analyze Crypto</b>.</p></div>', unsafe_allow_html=True)

        st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Data from CoinGecko. Crypto is highly volatile & unregulated by SEBI. Educational purposes only.</div>', unsafe_allow_html=True)

    # ─── TAB 3: MEME COINS ────────────────────────────────────────────────────
    with tab3:
        st.markdown("### 🎭 Meme Coin Analysis")
        st.markdown('<div class="meme-warning">⚠️ <b>HIGH RISK:</b> Meme coins are purely speculative with no fundamental value. Prices can crash 80-90% overnight. Only use money you can afford to lose completely.</div>', unsafe_allow_html=True)

        m1, m2 = st.columns([2, 1])
        with m1:
            meme_ticker = st.text_input("Enter Meme Coin Symbol",
                placeholder="e.g. DOGE, SHIB, PEPE, FLOKI, BONK", key="meme_input")
        with m2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("Popular: DOGE · SHIB · PEPE · FLOKI")
            st.caption("Trending: BONK · WIF · MEME · TURBO")
            st.caption("Others: BRETT · NEIRO · COQ")

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
                        st.error(f"❌ {d['error']} — Try DOGE, SHIB, PEPE, FLOKI, BONK.")
            else:
                st.warning("⚠️ Please enter or select a meme coin symbol.")

        st.markdown("---")
        if st.session_state.meme_data:
            render_results(st.session_state.meme_data, st.session_state.meme_report)
        else:
            st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">🎭</div><p>Enter a meme coin symbol above and click <b>Analyze Meme Coin</b>.</p></div>', unsafe_allow_html=True)

        st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Meme coins are unregulated & highly speculative. Not SEBI advice. Never invest borrowed money in meme coins.</div>', unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("<hr style='border-color:#30363d;margin-top:1.5rem;'>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("<span style='color:#8b949e;font-size:0.75rem;'>📊 <b>FinSage</b> — Global Financial Intelligence</span>", unsafe_allow_html=True)
    with f2:
        st.markdown("<span style='color:#6e7681;font-size:0.75rem;display:block;text-align:center;'>Data: Yahoo Finance · CoinGecko</span>", unsafe_allow_html=True)
    with f3:
        if st.button("🔒 Privacy Policy", key="footer_pp"):
            st.session_state.page = "privacy"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "privacy":
    show_privacy_policy()
elif st.session_state.user is not None:
    st.session_state.page = "dashboard"
    show_dashboard()
else:
    show_login()
