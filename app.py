"""
FinSage — Global Financial Intelligence Platform
100% Free APIs | Stocks | Crypto | Meme Coins
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
from datetime import datetime

from data_fetcher import fetch_stock_data, fetch_crypto_data, fetch_ticker_bar_data
from analyzer import analyze_stock, analyze_crypto, format_number, get_risk_label

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSage — Global Financial Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide default streamlit elements */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .stDeployButton { display: none; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="manage-app-button"] { display: none !important; }
    .viewerBadge_container__r5tak { display: none !important; }
    a[href*="github"] { display: none !important; }

    /* Main background */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stSidebar"] { background-color: #161b22; }

    /* Top navbar */
    .finsage-navbar {
        background: #161b22;
        border-bottom: 1px solid #30363d;
        padding: 0.8rem 2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0;
    }
    .navbar-brand {
        font-size: 1.5rem;
        font-weight: 800;
        color: #58a6ff;
        letter-spacing: 1px;
    }
    .navbar-tagline {
        color: #8b949e;
        font-size: 0.85rem;
    }

    /* Header */
    .finsage-header {
        background: linear-gradient(135deg, #1a1f35 0%, #0d1117 50%, #1a2744 100%);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .finsage-header h1 { font-size: 2.8rem; font-weight: 800; color: #58a6ff; margin: 0; }
    .finsage-header p { color: #8b949e; font-size: 1rem; margin: 0.3rem 0 0; }

    /* Ticker bar */
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

    /* Tab styling */
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

    /* Search box */
    .search-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    /* Quick pick buttons */
    .stButton > button {
        background: #21262d;
        color: #58a6ff;
        border: 1px solid #30363d;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 0.4rem 0.8rem;
        width: 100%;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #1f6feb;
        color: white;
        border-color: #1f6feb;
    }

    /* Analyze button */
    .analyze-btn > button {
        background: linear-gradient(135deg, #1f6feb, #388bfd) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 0.7rem !important;
        width: 100% !important;
    }

    /* Metric cards */
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        height: 100%;
    }
    .metric-card h3 { color: #8b949e; font-size: 0.75rem; margin: 0; text-transform: uppercase; letter-spacing: 1px; }
    .metric-card p { color: #c9d1d9; font-size: 1.3rem; font-weight: 700; margin: 0.3rem 0 0; }

    /* Disclaimer */
    .disclaimer {
        background: #161b22;
        border-left: 4px solid #d29922;
        border-radius: 0 8px 8px 0;
        padding: 0.8rem 1rem;
        color: #8b949e;
        font-size: 0.8rem;
        margin-top: 1rem;
    }

    /* Section header */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #58a6ff;
        margin-bottom: 0.5rem;
    }

    /* Warning box for meme */
    .meme-warning {
        background: #2d1b1b;
        border: 1px solid #f85149;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        color: #f85149;
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Session State ──────────────────────────────────────────────────────────────
for key in ["stock_data", "stock_report", "crypto_data", "crypto_report",
            "meme_data", "meme_report", "ticker_data", "last_ticker_refresh"]:
    if key not in st.session_state:
        st.session_state[key] = None if "data" in key or "report" in key else ([] if key == "ticker_data" else 0)
for flag in ["stock_auto_analyze", "crypto_auto_analyze", "meme_auto_analyze"]:
    if flag not in st.session_state:
        st.session_state[flag] = False


# ── Fetch Ticker Bar ───────────────────────────────────────────────────────────
now_ts = time.time()
if now_ts - st.session_state.last_ticker_refresh > 60:
    st.session_state.ticker_data = fetch_ticker_bar_data()
    st.session_state.last_ticker_refresh = now_ts


# ── Top Navbar ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="finsage-navbar">
    <div>
        <span class="navbar-brand">📊 FinSage</span>
        <span class="navbar-tagline">&nbsp;&nbsp;Global Financial Intelligence Platform</span>
    </div>
    <div style="color:#8b949e;font-size:0.8rem;">
        <span style="background:#1f3a1f;color:#3fb950;padding:0.2rem 0.7rem;border-radius:20px;font-weight:600;">
            ✅ 100% FREE
        </span>
        &nbsp; Stocks · Crypto · Meme Coins
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Live Ticker Bar ────────────────────────────────────────────────────────────
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


# ── Helper: render analysis results ───────────────────────────────────────────
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

    # KPI Row
    k1, k2, k3, k4, k5 = st.columns(5)
    price_str = f"${price:,.8f}" if price < 0.0001 else (f"${price:,.6f}" if price < 0.01 else f"{currency} {price:,.2f}")
    with k1: st.metric("💰 Price", price_str)
    with k2: st.metric("📈 24H Change", f"{change:+.2f}%")
    with k3: st.metric("🏦 Market Cap", format_number(market_cap))
    with k4: st.metric("⚡ Volatility", f"{vol:.1f}%")
    with k5: st.metric("🎯 Risk", f"{risk}/10")

    st.markdown("---")

    # Chart + Key Metrics
    col_chart, col_info = st.columns([3, 2])

    with col_chart:
        history = data.get("history")
        if history is not None and isinstance(history, pd.DataFrame) and not history.empty:
            has_ohlc = all(c in history.columns for c in ["Open", "High", "Low", "Close"])
            chart_label = "📊 Price Chart"
            chart_key = f"chart_type_{ticker}"
            chart_type = st.radio(
                chart_label,
                options=["📈 Line", "🕯️ Candlestick"] if has_ohlc else ["📈 Line"],
                horizontal=True,
                key=chart_key,
                label_visibility="collapsed",
            )
            close_col = "Close" if "Close" in history.columns else history.columns[0]
            y_data = history[close_col]
            x_data = history.index
            color = "#3fb950" if float(y_data.iloc[-1]) >= float(y_data.iloc[0]) else "#f85149"
            fig = go.Figure()
            if has_ohlc and chart_type == "🕯️ Candlestick":
                fig.add_trace(go.Candlestick(
                    x=x_data,
                    open=history["Open"], high=history["High"],
                    low=history["Low"], close=history["Close"],
                    increasing=dict(line=dict(color="#3fb950"), fillcolor="rgba(63,185,80,0.7)"),
                    decreasing=dict(line=dict(color="#f85149"), fillcolor="rgba(248,81,73,0.7)"),
                    name="OHLC",
                ))
                # Volume bars at bottom
                if "Volume" in history.columns:
                    vol_colors = ["#3fb950" if c >= o else "#f85149"
                                  for c, o in zip(history["Close"], history["Open"])]
                    fig.add_trace(go.Bar(
                        x=x_data, y=history["Volume"],
                        marker_color=vol_colors, opacity=0.3,
                        name="Volume", yaxis="y2",
                    ))
                fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                               showticklabels=False, range=[0, history["Volume"].max()*5]
                                               if "Volume" in history.columns else {}))
            else:
                fill_color = "rgba(63,185,80,0.1)" if color == "#3fb950" else "rgba(248,81,73,0.1)"
                fig.add_trace(go.Scatter(
                    x=x_data, y=y_data, mode="lines",
                    line=dict(color=color, width=2),
                    fill="tozeroy", fillcolor=fill_color,
                    name="Price",
                    hovertemplate="<b>%{x|%b %d}</b><br>Price: %{y:,.4f}<extra></extra>",
                ))
            fig.update_layout(
                plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                font=dict(color="#c9d1d9"),
                xaxis=dict(gridcolor="#21262d", rangeslider=dict(visible=False)),
                yaxis=dict(gridcolor="#21262d"),
                margin=dict(l=0, r=0, t=10, b=0),
                height=300, showlegend=False,
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
                "Circulating Supply": f"{data.get('circulating_supply', 0):,.0f}" if data.get("circulating_supply") else "N/A",
            }
        for k, v in metrics.items():
            ca, cb = st.columns([1, 1])
            ca.markdown(f"<span style='color:#8b949e;font-size:0.85rem;'>{k}</span>", unsafe_allow_html=True)
            cb.markdown(f"<span style='color:#c9d1d9;font-size:0.85rem;font-weight:600;'>{v}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # Full Report
    st.markdown("#### 📄 Full Analysis Report")
    st.markdown(report)

    # Download
    st.download_button(
        label="📥 Download Report",
        data=report,
        file_name=f"FinSage_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )

    # ── Latest News ───────────────────────────────────────────────────────────
    news_list = data.get("news", [])
    if news_list:
        st.markdown("---")
        st.markdown("#### 📰 Latest News")
        for i, article in enumerate(news_list[:6]):
            art_title = article.get("title", "")
            art_url   = article.get("url", "#")
            art_sum   = article.get("summary", "")
            art_src   = article.get("source", "")
            art_pub   = article.get("published", "")
            # Format date
            try:
                from datetime import datetime as _dt
                if "T" in str(art_pub):
                    parsed = _dt.fromisoformat(str(art_pub).replace("Z", "+00:00"))
                    art_date = parsed.strftime("%b %d, %Y")
                else:
                    art_date = str(art_pub)[:16] if art_pub else ""
            except Exception:
                art_date = str(art_pub)[:16] if art_pub else ""
            
            link_html = f'<a href="{art_url}" target="_blank" style="color:#58a6ff;text-decoration:none;font-weight:600;font-size:0.92rem;">{art_title}</a>' if art_url and art_url != "#" else f'<span style="color:#c9d1d9;font-weight:600;font-size:0.92rem;">{art_title}</span>'
            meta_html = f'<span style="color:#8b949e;font-size:0.78rem;">{art_src}{" · " + art_date if art_date else ""}</span>'
            sum_html  = f'<p style="color:#8b949e;font-size:0.82rem;margin:2px 0 0;">{art_sum}</p>' if art_sum else ""
            
            st.markdown(
                f'<div style="border-left:3px solid #30363d;padding:8px 12px;margin-bottom:8px;background:rgba(22,27,34,0.6);border-radius:0 8px 8px 0;">'
                f'{link_html}<br>{meta_html}{sum_html}</div>',
                unsafe_allow_html=True
            )


# ── TABS ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🌍  Global Stocks", "₿  Cryptocurrency", "🎭  Meme Coins"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — GLOBAL STOCKS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 🌍 Global Stock Analysis")
    st.markdown("Search any stock from NSE India, US, UK, Germany, Japan and more.")

    sc1, sc2 = st.columns([2, 1])
    with sc1:
        stock_ticker = st.text_input(
            "Enter Stock Ticker Symbol",
            placeholder="e.g. AAPL, RELIANCE.NS, TCS.NS, TSLA, INFY.NS",
            key="stock_ticker_input"
        )
    with sc2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Examples by Market:**")
        st.markdown("<span style='color:#8b949e;font-size:0.8rem;'>🇮🇳 NSE: RELIANCE.NS, TCS.NS, INFY.NS<br>🇺🇸 US: AAPL, TSLA, NVDA, MSFT<br>🌐 Others: add .L (London), .DE (Germany)</span>", unsafe_allow_html=True)

    st.markdown("**⚡ Quick Pick:**")
    qcols = st.columns(8)
    stock_picks = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "RELIANCE.NS", "TCS.NS", "INFY.NS"]
    for i, qp in enumerate(stock_picks):
        with qcols[i]:
            if st.button(qp, key=f"sq_{qp}"):
                st.session_state["stock_selected"] = qp
                st.session_state["stock_auto_analyze"] = True

    final_stock = st.session_state.get("stock_selected", stock_ticker).strip().upper()

    manual_analyze_s = st.button("🔍 Analyze Stock", key="analyze_stock", type="primary", use_container_width=True)
    should_analyze_s = manual_analyze_s or st.session_state.get("stock_auto_analyze", False)

    if should_analyze_s:
        st.session_state["stock_auto_analyze"] = False
        if final_stock:
            with st.spinner(f"Fetching data for **{final_stock}**..."):
                data = fetch_stock_data(final_stock)
                if "error" not in data:
                    st.session_state.stock_data = data
                    st.session_state.stock_report = analyze_stock(data)
                    if manual_analyze_s:
                        st.session_state["stock_selected"] = ""
                else:
                    st.error(f"❌ {data['error']}")
        else:
            st.warning("⚠️ Please enter a stock ticker symbol.")

    st.markdown("---")

    if st.session_state.stock_data and st.session_state.stock_report:
        render_results(st.session_state.stock_data, st.session_state.stock_report)
    else:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#8b949e;">
            <div style="font-size:3rem;">🌍</div>
            <p>Enter a stock ticker above and click <b>Analyze Stock</b> to get a full analysis report.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="disclaimer">
        ⚖️ <b>Disclaimer:</b> Stock data sourced from Yahoo Finance via yfinance. For educational purposes only. Not SEBI-registered investment advice.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CRYPTOCURRENCY
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### ₿ Cryptocurrency Analysis")
    st.markdown("Analyze major cryptocurrencies with real-time CoinGecko data.")

    cc1, cc2 = st.columns([2, 1])
    with cc1:
        crypto_ticker = st.text_input(
            "Enter Crypto Symbol",
            placeholder="e.g. BTC, ETH, SOL, BNB, ADA, XRP",
            key="crypto_ticker_input"
        )
    with cc2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Top Cryptocurrencies:**")
        st.markdown("<span style='color:#8b949e;font-size:0.8rem;'>BTC · ETH · BNB · SOL · XRP<br>ADA · AVAX · DOT · MATIC · LINK<br>LTC · ATOM · TRX · TON · UNI</span>", unsafe_allow_html=True)

    st.markdown("**⚡ Quick Pick:**")
    ccols = st.columns(8)
    crypto_picks = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT"]
    for i, qp in enumerate(crypto_picks):
        with ccols[i]:
            if st.button(qp, key=f"cq_{qp}"):
                st.session_state["crypto_selected"] = qp
                st.session_state["crypto_auto_analyze"] = True

    final_crypto = st.session_state.get("crypto_selected", crypto_ticker).strip().upper()

    manual_analyze_c = st.button("🔍 Analyze Crypto", key="analyze_crypto", type="primary", use_container_width=True)
    should_analyze_c = manual_analyze_c or st.session_state.get("crypto_auto_analyze", False)

    if should_analyze_c:
        st.session_state["crypto_auto_analyze"] = False
        if final_crypto:
            with st.spinner(f"Fetching data for **{final_crypto}**..."):
                data = fetch_crypto_data(final_crypto)
                if "error" not in data:
                    st.session_state.crypto_data = data
                    st.session_state.crypto_report = analyze_crypto(data)
                    if manual_analyze_c:
                        st.session_state["crypto_selected"] = ""
                else:
                    st.error(f"❌ {data['error']}")
        else:
            st.warning("⚠️ Please enter a crypto symbol.")

    st.markdown("---")

    if st.session_state.crypto_data and st.session_state.crypto_report:
        render_results(st.session_state.crypto_data, st.session_state.crypto_report)
    else:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#8b949e;">
            <div style="font-size:3rem;">₿</div>
            <p>Enter a crypto symbol above and click <b>Analyze Crypto</b> to get a full analysis report.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="disclaimer">
        ⚖️ <b>Disclaimer:</b> Crypto data sourced from CoinGecko Free API. Cryptocurrency is highly volatile and unregulated by SEBI. For educational purposes only. Not financial advice.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — MEME COINS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 🎭 Meme Coin Analysis")

    st.markdown("""
    <div class="meme-warning">
        ⚠️ <b>HIGH RISK WARNING:</b> Meme coins are extremely speculative assets with no fundamental value.
        Prices can drop 80-90% rapidly. Only invest what you can afford to lose completely.
    </div>
    """, unsafe_allow_html=True)

    mc1, mc2 = st.columns([2, 1])
    with mc1:
        meme_ticker = st.text_input(
            "Enter Meme Coin Symbol",
            placeholder="e.g. DOGE, SHIB, PEPE, FLOKI, BONK",
            key="meme_ticker_input"
        )
    with mc2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Popular Meme Coins:**")
        st.markdown("<span style='color:#8b949e;font-size:0.8rem;'>DOGE · SHIB · PEPE · FLOKI<br>BONK · WIF · MEME · TURBO<br>BRETT · NEIRO</span>", unsafe_allow_html=True)

    st.markdown("**⚡ Quick Pick:**")
    mcols = st.columns(8)
    meme_picks = ["DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME", "TURBO"]
    for i, qp in enumerate(meme_picks):
        with mcols[i]:
            if st.button(qp, key=f"mq_{qp}"):
                st.session_state["meme_selected"] = qp
                st.session_state["meme_auto_analyze"] = True

    final_meme = st.session_state.get("meme_selected", meme_ticker).strip().upper()

    manual_analyze_m = st.button("🔍 Analyze Meme Coin", key="analyze_meme", type="primary", use_container_width=True)
    should_analyze_m = manual_analyze_m or st.session_state.get("meme_auto_analyze", False)

    if should_analyze_m:
        st.session_state["meme_auto_analyze"] = False
        if final_meme:
            with st.spinner(f"Fetching data for **{final_meme}**..."):
                data = fetch_crypto_data(final_meme)
                if "error" not in data:
                    # Force meme coin label
                    data["asset_type"] = "Meme Coin"
                    st.session_state.meme_data = data
                    st.session_state.meme_report = analyze_crypto(data)
                    if manual_analyze_m:
                        st.session_state["meme_selected"] = ""
                else:
                    st.error(f"❌ {data['error']}")
        else:
            st.warning("⚠️ Please enter a meme coin symbol.")

    st.markdown("---")

    if st.session_state.meme_data and st.session_state.meme_report:
        render_results(st.session_state.meme_data, st.session_state.meme_report)
    else:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#8b949e;">
            <div style="font-size:3rem;">🎭</div>
            <p>Enter a meme coin symbol above and click <b>Analyze Meme Coin</b> to get a full report.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="disclaimer">
        ⚖️ <b>Disclaimer:</b> Meme coin data sourced from CoinGecko. Meme coins are highly speculative, not regulated by SEBI. Past performance means nothing. For educational purposes only. Never invest more than you can afford to lose.
    </div>
    """, unsafe_allow_html=True)
