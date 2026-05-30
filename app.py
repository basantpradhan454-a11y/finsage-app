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
from auth_page import render_auth_page, is_logged_in, get_current_user, logout

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
    [data-testid="stAppViewBlockContainer"] > div:last-child { display: none !important; }
    .st-emotion-cache-1dp5vir { display: none !important; }
    button[kind="header"] { display: none !important; }
    .viewerBadge_container__r5tak { display: none !important; }
    .stDeployButton { display: none !important; }
    .__web-inspector-hide-shortcut__ { display: none !important; }
    [data-testid="manage-app-button"] { visibility: hidden !important; width: 0 !important; height: 0 !important; }

    .stApp { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stSidebar"] { background-color: #161b22; }

    .fs-brand { font-size: 1.35rem; font-weight: 800; color: #58a6ff; }
    .fs-tagline { color: #8b949e; font-size: 0.8rem; margin-left: 0.7rem; }

    .ticker-bar {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 10px; padding: 0.55rem 1.1rem;
        margin-bottom: 1rem; overflow-x: auto; white-space: nowrap;
    }
    .ticker-item { display: inline-block; margin-right: 1.4rem; font-size: 0.83rem; }
    .ticker-sym { color: #58a6ff; font-weight: 700; margin-right: 3px; }
    .ticker-price { color: #c9d1d9; margin-right: 3px; }
    .up { color: #3fb950; } .down { color: #f85149; }

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

    .stButton > button {
        background: #21262d; color: #58a6ff;
        border: 1px solid #30363d; border-radius: 8px;
        font-size: 0.83rem; font-weight: 600; width: 100%;
    }
    .stButton > button:hover { background: #1f6feb; color: white; border-color: #1f6feb; }

    .meme-warning {
        background: #2d1b1b; border: 1px solid #f85149;
        border-radius: 8px; padding: 0.75rem 0.9rem;
        color: #f85149; font-size: 0.83rem; margin-bottom: 0.9rem;
    }

    .disclaimer {
        background: #161b22; border-left: 4px solid #d29922;
        border-radius: 0 8px 8px 0; padding: 0.7rem 0.9rem;
        color: #8b949e; font-size: 0.78rem; margin-top: 0.9rem;
    }

    .user-badge {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 20px; padding: 0.3rem 0.9rem;
        color: #c9d1d9; font-size: 0.82rem; display: inline-flex;
        align-items: center; gap: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
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

# ══════════════════════════════════════════════════════════════════════════════
# AUTH GATE — show login if not logged in
# ══════════════════════════════════════════════════════════════════════════════
if not render_auth_page():
    st.stop()

# ── Past this point: user is logged in ────────────────────────────────────────
user = get_current_user()

# ── Ticker refresh ─────────────────────────────────────────────────────────────
now_ts = time.time()
if now_ts - st.session_state.last_ticker_refresh > 60:
    st.session_state.ticker_data = fetch_ticker_bar_data()
    st.session_state.last_ticker_refresh = now_ts

# ── Navbar ─────────────────────────────────────────────────────────────────────
n1, n2 = st.columns([5, 2])
with n1:
    st.markdown("""
    <div style="padding:0.5rem 0 0.3rem;">
        <span class="fs-brand">📊 FinSage</span>
        <span class="fs-tagline">Global Financial Intelligence Platform</span>
        &nbsp;
        <span style="background:#1a3a1a;color:#3fb950;padding:0.15rem 0.55rem;border-radius:20px;font-size:0.72rem;font-weight:600;">✅ 100% FREE</span>
    </div>
    """, unsafe_allow_html=True)
with n2:
    # User info + logout
    provider_icon = "🔵" if user.get("provider") == "google" else "📧"
    user_name = user.get("name", "User")
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f"""
        <div style="padding-top:0.5rem;text-align:right;">
            <span class="user-badge">{provider_icon} {user_name}</span>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        if st.button("Logout", key="logout_btn"):
            logout()

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
            # ── Detect candlestick patterns ──────────────────────────────────
            def detect_patterns(df):
                patterns = []
                if not all(c in df.columns for c in ["Open","High","Low","Close"]):
                    return patterns
                for i in range(2, len(df)):
                    o, h, l, c = df["Open"].iloc[i], df["High"].iloc[i], df["Low"].iloc[i], df["Close"].iloc[i]
                    po, ph, pl, pc = df["Open"].iloc[i-1], df["High"].iloc[i-1], df["Low"].iloc[i-1], df["Close"].iloc[i-1]
                    body = abs(c - o)
                    upper_wick = h - max(c, o)
                    lower_wick = min(c, o) - l
                    full_range = h - l if h != l else 0.0001

                    # Doji
                    if body / full_range < 0.1:
                        patterns.append((df.index[i], h * 1.002, "⊙ Doji", "#e3b341"))
                    # Hammer
                    elif lower_wick > 2 * body and upper_wick < body * 0.5 and c > o:
                        patterns.append((df.index[i], l * 0.998, "🔨 Hammer", "#3fb950"))
                    # Shooting Star
                    elif upper_wick > 2 * body and lower_wick < body * 0.5 and c < o:
                        patterns.append((df.index[i], h * 1.002, "⭐ Shoot Star", "#f85149"))
                    # Bullish Engulfing
                    elif pc < po and c > o and c > po and o < pc:
                        patterns.append((df.index[i], l * 0.998, "🟢 Bull Engulf", "#3fb950"))
                    # Bearish Engulfing
                    elif pc > po and c < o and c < po and o > pc:
                        patterns.append((df.index[i], h * 1.002, "🔴 Bear Engulf", "#f85149"))
                    # Morning Star (3-candle)
                    elif i >= 2:
                        ppo = df["Open"].iloc[i-2]; ppc = df["Close"].iloc[i-2]
                        if ppc < ppo and body / full_range < 0.15 and c > o and c > (ppo + ppc) / 2:
                            patterns.append((df.index[i], l * 0.997, "🌅 Morning ☆", "#3fb950"))
                return patterns

            has_ohlc = all(c in history.columns for c in ["Open","High","Low","Close"])
            has_vol  = "Volume" in history.columns

            st.markdown("#### 📊 Candlestick Chart with Volume & Patterns")

            if has_ohlc:
                patterns = detect_patterns(history)

                # ── Build subplot: candlestick (top) + volume (bottom) ────────
                from plotly.subplots import make_subplots
                row_heights = [0.68, 0.32] if has_vol else [1.0]
                rows = 2 if has_vol else 1
                fig = make_subplots(
                    rows=rows, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.04,
                    row_heights=row_heights,
                    subplot_titles=["", "Volume" if has_vol else ""]
                )

                # Candlestick trace
                fig.add_trace(go.Candlestick(
                    x=history.index,
                    open=history["Open"], high=history["High"],
                    low=history["Low"],  close=history["Close"],
                    increasing_line_color="#3fb950", decreasing_line_color="#f85149",
                    increasing_fillcolor="#3fb950", decreasing_fillcolor="#f85149",
                    name="Price",
                    hovertext=[
                        f"O: {o:.4f}  H: {h:.4f}<br>L: {l:.4f}  C: {c:.4f}"
                        for o,h,l,c in zip(history["Open"],history["High"],history["Low"],history["Close"])
                    ],
                    hoverinfo="text+x",
                ), row=1, col=1)

                # MA lines on candle chart
                if len(history) >= 10:
                    ma10 = history["Close"].rolling(10).mean()
                    fig.add_trace(go.Scatter(
                        x=history.index, y=ma10, mode="lines",
                        line=dict(color="#58a6ff", width=1.2, dash="dot"),
                        name="MA10", hovertemplate="MA10: %{y:,.4f}<extra></extra>"
                    ), row=1, col=1)
                if len(history) >= 20:
                    ma20 = history["Close"].rolling(20).mean()
                    fig.add_trace(go.Scatter(
                        x=history.index, y=ma20, mode="lines",
                        line=dict(color="#a78bfa", width=1.2, dash="dash"),
                        name="MA20", hovertemplate="MA20: %{y:,.4f}<extra></extra>"
                    ), row=1, col=1)

                # Pattern annotations
                for dt, price, label, clr in patterns[-6:]:  # max 6 annotations
                    fig.add_annotation(
                        x=dt, y=price, text=label,
                        showarrow=False,
                        font=dict(size=9, color=clr),
                        bgcolor="rgba(13,17,23,0.75)",
                        bordercolor=clr, borderwidth=1,
                        borderpad=3,
                        row=1, col=1
                    )

                # Volume bars
                if has_vol and rows == 2:
                    vol_colors = [
                        "#3fb950" if c >= o else "#f85149"
                        for c, o in zip(history["Close"], history["Open"])
                    ]
                    fig.add_trace(go.Bar(
                        x=history.index, y=history["Volume"],
                        marker_color=vol_colors,
                        name="Volume",
                        hovertemplate="Vol: %{y:,.0f}<extra></extra>",
                        opacity=0.7,
                    ), row=2, col=1)

                # Layout
                chart_height = 420 if has_vol else 300
                fig.update_layout(
                    plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                    font=dict(color="#c9d1d9", size=11),
                    xaxis=dict(gridcolor="#21262d", rangeslider_visible=False, showspikes=True),
                    yaxis=dict(gridcolor="#21262d", showspikes=True),
                    xaxis2=dict(gridcolor="#21262d") if has_vol else {},
                    yaxis2=dict(gridcolor="#21262d", title="Vol") if has_vol else {},
                    margin=dict(l=0, r=0, t=28, b=0),
                    height=chart_height,
                    showlegend=True,
                    legend=dict(
                        orientation="h", x=0, y=1.06,
                        font=dict(size=10),
                        bgcolor="rgba(0,0,0,0)"
                    ),
                    hovermode="x unified",
                )
                fig.update_xaxes(showgrid=True, gridcolor="#21262d")

                st.plotly_chart(fig, use_container_width=True)

                # Pattern legend below chart
                if patterns:
                    last_patterns = patterns[-4:]
                    cols_p = st.columns(len(last_patterns))
                    for idx_p, (dt, _, label, clr) in enumerate(last_patterns):
                        cols_p[idx_p].markdown(
                            f"<div style='text-align:center;background:rgba(13,17,23,0.8);"
                            f"border:1px solid {clr};border-radius:8px;padding:4px 6px;"
                            f"font-size:0.72rem;color:{clr};'>{label}<br>"
                            f"<span style='color:#8b949e;font-size:0.65rem;'>{str(dt)[:10]}</span></div>",
                            unsafe_allow_html=True
                        )
            else:
                # Fallback: simple line chart if no OHLC data
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
                        hovertemplate="<b>%{x}</b><br>%{y:,.4f}<extra></extra>"
                    ))
                    fig.update_layout(
                        plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                        font=dict(color="#c9d1d9"),
                        xaxis=dict(gridcolor="#21262d"),
                        yaxis=dict(gridcolor="#21262d"),
                        margin=dict(l=0, r=0, t=10, b=0),
                        height=300, showlegend=False,
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
