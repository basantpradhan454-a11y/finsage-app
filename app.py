"""
FinSage — Global Financial Intelligence Platform
Real-time market data: yfinance + CoinGecko
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
from datetime import datetime

from data_fetcher import fetch_stock_data, fetch_crypto_data, fetch_ticker_bar_data
from analyzer import analyze_stock, analyze_crypto, format_number

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

    /* ── Navbar ── */
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


# ── Session State ──────────────────────────────────────────────────────────────
defaults = {
    "stock_data": None, "stock_report": None,
    "crypto_data": None, "crypto_report": None,
    "meme_data": None, "meme_report": None,
    "ticker_data": [], "last_ticker_refresh": 0,
    "stock_selected": "", "crypto_selected": "", "meme_selected": "",
    "authenticated": False, "current_user": None,
    "auth_mode": "login",   # "login" | "signup"
    "show_privacy": False,
    "users_db": {},         # {email: {name, password, joined}}
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Ticker refresh ─────────────────────────────────────────────────────────────
now_ts = time.time()
if now_ts - st.session_state.last_ticker_refresh > 60:
    st.session_state.ticker_data = fetch_ticker_bar_data()
    st.session_state.last_ticker_refresh = now_ts




# ══════════════════════════════════════════════════════════════════════════════
# AUTH — Login / Signup
# ══════════════════════════════════════════════════════════════════════════════

import hashlib

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def render_auth():
    """Full-screen login / signup modal."""
    st.markdown("""
    <style>
    .auth-card {
        max-width: 420px; margin: 3rem auto 0;
        background: rgba(22,27,34,0.95);
        border: 1px solid #30363d;
        border-radius: 16px; padding: 2.5rem 2rem;
        box-shadow: 0 8px 40px rgba(0,0,0,0.6);
    }
    .auth-logo { text-align:center; font-size:2.2rem; margin-bottom:0.3rem; }
    .auth-title { text-align:center; font-size:1.4rem; font-weight:700;
                  color:#e6edf3; margin-bottom:0.2rem; }
    .auth-sub   { text-align:center; color:#8b949e; font-size:0.85rem;
                  margin-bottom:1.8rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-logo">📊</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">FinSage</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Global Financial Intelligence Platform</div>', unsafe_allow_html=True)

    mode = st.session_state.auth_mode
    tab_login, tab_signup = st.tabs(["🔑 Login", "✨ Sign Up"])

    # ── LOGIN ─────────────────────────────────────────────────────────────────
    with tab_login:
        if st.session_state.auth_mode != "login":
            st.session_state.auth_mode = "login"
        email_l = st.text_input("Email", key="login_email", placeholder="you@example.com")
        pass_l  = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
        
        col_btn, col_fp = st.columns([2,1])
        with col_btn:
            if st.button("Login →", use_container_width=True, type="primary", key="btn_login"):
                db = st.session_state.users_db
                if not email_l or not pass_l:
                    st.error("Email aur password dono bharo.")
                elif email_l not in db:
                    st.error("Account nahi mila. Pehle Sign Up karo.")
                elif db[email_l]["password"] != _hash(pass_l):
                    st.error("Password galat hai.")
                else:
                    st.session_state.authenticated = True
                    st.session_state.current_user = {"email": email_l, "name": db[email_l]["name"]}
                    st.rerun()

    # ── SIGNUP ────────────────────────────────────────────────────────────────
    with tab_signup:
        name_s  = st.text_input("Full Name", key="signup_name", placeholder="Basant Pradhan")
        email_s = st.text_input("Email", key="signup_email", placeholder="you@example.com")
        pass_s  = st.text_input("Password", type="password", key="signup_pass", placeholder="Min 8 characters")
        pass_c  = st.text_input("Confirm Password", type="password", key="signup_confirm", placeholder="Repeat password")

        # Privacy policy checkbox
        agree = st.checkbox(
            "Maine **Privacy Policy** padhi aur main agree karta/karti hoon.",
            key="signup_agree"
        )
        if st.button("📄 Privacy Policy padhne ke liye yahan click karo", key="privacy_link_signup"):
            st.session_state.show_privacy = True
            st.rerun()

        if st.button("Create Account →", use_container_width=True, type="primary", key="btn_signup"):
            db = st.session_state.users_db
            if not name_s or not email_s or not pass_s:
                st.error("Sab fields bharna zaroori hai.")
            elif "@" not in email_s or "." not in email_s:
                st.error("Valid email address dalo.")
            elif len(pass_s) < 8:
                st.error("Password kam se kam 8 characters ka hona chahiye.")
            elif pass_s != pass_c:
                st.error("Passwords match nahi kar rahe.")
            elif not agree:
                st.error("Privacy Policy agree karna zaroori hai.")
            elif email_s in db:
                st.error("Is email se account pehle se hai. Login karo.")
            else:
                st.session_state.users_db[email_s] = {
                    "name": name_s,
                    "password": _hash(pass_s),
                    "joined": datetime.now().strftime("%Y-%m-%d"),
                }
                st.session_state.authenticated = True
                st.session_state.current_user = {"email": email_s, "name": name_s}
                st.success(f"Welcome, {name_s}! 🎉")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def render_privacy_policy():
    """Full Privacy Policy page."""
    if st.button("← Back to FinSage", key="back_from_privacy"):
        st.session_state.show_privacy = False
        st.rerun()

    st.markdown("""
## 🔒 Privacy Policy — FinSage

**Last Updated:** May 2026

---

### 1. Introduction
FinSage ("we", "us", "our") is a financial intelligence platform that provides real-time market data, analysis, and insights for educational purposes. This Privacy Policy explains how we collect, use, and protect your information.

---

### 2. Information We Collect
- **Account Information:** Name, email address, and encrypted password when you register.
- **Usage Data:** Pages visited, assets analyzed, and features used — to improve the platform.
- **Device Info:** Browser type, OS, and IP address for security and analytics.

---

### 3. How We Use Your Information
- To provide and maintain your FinSage account.
- To personalize your experience and remember your preferences.
- To send important updates about the platform (no spam, ever).
- To improve our analysis algorithms and data quality.

---

### 4. Data Security
- Passwords are stored using **SHA-256 hashing** — we never store plain-text passwords.
- All data is stored securely and not shared with third parties.
- Market data is fetched in real-time from public APIs (yfinance, CoinGecko) — we do not store your search history on external servers.

---

### 5. Third-Party Services
FinSage uses the following free public APIs for market data:
- **Yahoo Finance / yfinance** — Stock market data
- **CoinGecko** — Cryptocurrency data
- **Google News RSS** — Financial news headlines
- **Groq API** — AI-powered insights (no personal data is shared with Groq)

---

### 6. Data Retention
Your account data is retained as long as your account is active. You may request deletion at any time by contacting us.

---

### 7. Cookies
FinSage uses session-based cookies only to maintain your login state. No tracking or advertising cookies are used.

---

### 8. Your Rights
You have the right to:
- Access your personal data
- Correct inaccurate data
- Delete your account and all associated data
- Opt out of any communications

---

### 9. Disclaimer
> FinSage is an **educational platform only**. Nothing on this platform constitutes financial advice. Always consult a SEBI-registered advisor before investing. We are not responsible for any financial decisions made based on our analysis.

---

### 10. Contact
For any privacy concerns, contact us at: **finsage.support@example.com**

---
*FinSage — Global Financial Intelligence Platform*
""")


# ══════════════════════════════════════════════════════════════════════════════
# ROUTE: Show Privacy Policy / Auth / Main App
# ══════════════════════════════════════════════════════════════════════════════

# Privacy Policy page
if st.session_state.show_privacy:
    render_privacy_policy()
    st.stop()

# Auth wall — show login/signup if not authenticated
if not st.session_state.authenticated:
    render_auth()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP (only reached if authenticated)
# ══════════════════════════════════════════════════════════════════════════════

# ── Navbar ─────────────────────────────────────────────────────────────────────
n1, n2 = st.columns([4, 1])
with n1:
    st.markdown("""
    <div style="padding:0.5rem 0 0.3rem;">
        <span class="fs-brand">📊 FinSage</span>
        <span class="fs-tagline">Global Financial Intelligence Platform</span>
        
    </div>
    """, unsafe_allow_html=True)
with n2:
    user = st.session_state.current_user or {}
    uname = user.get("name", "").split()[0] if user.get("name") else "User"
    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown(f"<div style='padding-top:0.6rem;text-align:right;color:#8b949e;font-size:0.78rem;'>👤 {uname}</div>", unsafe_allow_html=True)
    with c2:
        if st.button("Logout", key="logout_btn", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()

st.markdown("<hr style='border-color:#30363d;margin:0.2rem 0 0.8rem;'>", unsafe_allow_html=True)


# ── Live Ticker Bar ────────────────────────────────────────────────────────────
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
                    st.error(f"❌ {d['error']} — Check the ticker symbol and try again.")
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


# ─── TAB 3: MEME COINS ────────────────────────────────────────────────────────
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


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("<hr style='border-color:#30363d;margin-top:1.5rem;'>", unsafe_allow_html=True)
f1, f2, f3 = st.columns([3, 2, 3])
with f1:
    st.markdown("<span style='color:#8b949e;font-size:0.75rem;'>📊 <b>FinSage</b> — Global Financial Intelligence Platform</span>", unsafe_allow_html=True)
with f2:
    if st.button("📄 Privacy Policy", key="footer_privacy", use_container_width=True):
        st.session_state.show_privacy = True
        st.rerun()
with f3:
    st.markdown("<span style='color:#6e7681;font-size:0.75rem;display:block;text-align:right;'>Data: Yahoo Finance · CoinGecko &nbsp;|&nbsp; For educational purposes only</span>", unsafe_allow_html=True)
