"""
FinSage — Global Financial Intelligence Platform
100% Free APIs | Stocks | Crypto | Meme Coins
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
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
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main theme */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    
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
        margin-bottom: 1rem;
        display: flex;
        gap: 2rem;
        overflow-x: auto;
        white-space: nowrap;
    }
    .ticker-item { display: inline-block; font-size: 0.85rem; }
    .ticker-sym { color: #58a6ff; font-weight: 700; margin-right: 4px; }
    .ticker-price { color: #c9d1d9; margin-right: 4px; }
    .up { color: #3fb950; }
    .down { color: #f85149; }
    
    /* Metric cards */
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-card h3 { color: #8b949e; font-size: 0.8rem; margin: 0; text-transform: uppercase; letter-spacing: 1px; }
    .metric-card p { color: #c9d1d9; font-size: 1.4rem; font-weight: 700; margin: 0.3rem 0 0; }
    
    /* Risk badge */
    .risk-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }
    
    /* Sidebar */
    .sidebar-section {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #1f6feb, #388bfd);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
        padding: 0.6rem;
    }
    .stButton > button:hover { background: linear-gradient(135deg, #388bfd, #58a6ff); }
    
    /* Analysis report */
    .analysis-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.5rem;
    }
    
    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* Quick pick buttons */
    .quick-pick-btn > button {
        background: #21262d !important;
        color: #58a6ff !important;
        border: 1px solid #30363d !important;
        font-size: 0.8rem !important;
        padding: 0.3rem 0.6rem !important;
        border-radius: 6px !important;
    }
    
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
</style>
""", unsafe_allow_html=True)


# ── Session State ──────────────────────────────────────────────────────────────
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None
if "analysis_report" not in st.session_state:
    st.session_state.analysis_report = None
if "ticker_data" not in st.session_state:
    st.session_state.ticker_data = []
if "last_ticker_refresh" not in st.session_state:
    st.session_state.last_ticker_refresh = 0


# ── Fetch Ticker Bar ───────────────────────────────────────────────────────────
now_ts = time.time()
if now_ts - st.session_state.last_ticker_refresh > 60:
    st.session_state.ticker_data = fetch_ticker_bar_data()
    st.session_state.last_ticker_refresh = now_ts


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="finsage-header">
    <h1>📊 FinSage</h1>
    <p>Global Financial Intelligence Platform &nbsp;·&nbsp; Stocks · Cryptocurrency · Meme Coins</p>
    <p style="margin-top:0.5rem;">
        <span style="background:#1f3a1f;color:#3fb950;padding:0.2rem 0.8rem;border-radius:20px;font-size:0.8rem;font-weight:600;">
            ✅ 100% FREE — No API Key Required
        </span>
    </p>
</div>
""", unsafe_allow_html=True)


# ── Live Ticker Bar ────────────────────────────────────────────────────────────
if st.session_state.ticker_data:
    ticker_html = '<div class="ticker-bar">🔴 LIVE &nbsp;|'
    for item in st.session_state.ticker_data:
        chg = item.get("change", 0)
        cls = "up" if chg >= 0 else "down"
        arrow = "▲" if chg >= 0 else "▼"
        price = item.get("price", 0)
        price_str = f"${price:,.6f}" if price < 0.01 else f"${price:,.2f}"
        ticker_html += f'<span class="ticker-item"><span class="ticker-sym">{item["symbol"]}</span><span class="ticker-price">{price_str}</span><span class="{cls}">{arrow}{abs(chg):.2f}%</span></span>&nbsp;&nbsp;'
    ticker_html += "</div>"
    st.markdown(ticker_html, unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Asset Search")
    st.markdown('<span style="background:#1f3a1f;color:#3fb950;padding:0.2rem 0.6rem;border-radius:10px;font-size:0.75rem;">✅ FREE APIs Only</span>', unsafe_allow_html=True)
    st.markdown("---")

    # Asset type
    asset_type = st.selectbox(
        "Select Asset Type",
        ["🌍 Global Stock", "₿ Cryptocurrency", "🎭 Meme Coin"],
        index=0,
    )

    # Ticker input
    if "Global Stock" in asset_type:
        placeholder = "e.g. AAPL, RELIANCE.NS, TSLA"
        quick_picks = ["AAPL", "RELIANCE.NS", "TCS.NS", "TSLA", "NVDA", "MSFT", "INFY.NS", "GOOGL"]
    elif "Cryptocurrency" in asset_type:
        placeholder = "e.g. BTC, ETH, SOL, BNB"
        quick_picks = ["BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "AVAX", "DOT"]
    else:
        placeholder = "e.g. DOGE, SHIB, PEPE, FLOKI"
        quick_picks = ["DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME", "TURBO"]

    ticker_input = st.text_input("Enter Ticker Symbol", placeholder=placeholder, key="ticker_input")

    # Quick picks
    st.markdown("⚡ **Quick Pick:**")
    cols = st.columns(3)
    for i, qp in enumerate(quick_picks):
        with cols[i % 3]:
            if st.button(qp, key=f"qp_{qp}", use_container_width=True):
                st.session_state["selected_quick"] = qp

    # Use quick pick if selected
    symbol = st.session_state.get("selected_quick", ticker_input).strip().upper()

    st.markdown("---")
    analyze_btn = st.button("🔍 Analyze Now", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.75rem;color:#8b949e;">
    <b>Data Sources</b><br>
    📈 Stocks → Yahoo Finance (yfinance)<br>
    ₿ Crypto → CoinGecko Free API<br>
    🔄 Updates every 60 seconds
    </div>
    """, unsafe_allow_html=True)


# ── Main Content ───────────────────────────────────────────────────────────────
if analyze_btn and symbol:
    st.session_state.analysis_data = None
    st.session_state.analysis_report = None

    with st.spinner(f"Fetching real-time data for **{symbol}**..."):
        if "Global Stock" in asset_type:
            data = fetch_stock_data(symbol)
            if "error" not in data:
                report = analyze_stock(data)
                st.session_state.analysis_data = data
                st.session_state.analysis_report = report
            else:
                st.error(f"❌ {data['error']}")
                st.stop()
        else:
            data = fetch_crypto_data(symbol)
            if "error" not in data:
                report = analyze_crypto(data)
                st.session_state.analysis_data = data
                st.session_state.analysis_report = report
            else:
                st.error(f"❌ {data['error']}")
                st.stop()

elif analyze_btn and not symbol:
    st.warning("⚠️ Please enter a ticker symbol or select from Quick Pick.")


# ── Display Results ────────────────────────────────────────────────────────────
if st.session_state.analysis_data and st.session_state.analysis_report:
    data = st.session_state.analysis_data
    report = st.session_state.analysis_report

    name = data.get("name", data.get("ticker"))
    ticker = data.get("ticker")
    price = data.get("current_price", 0)
    change = data.get("change_pct", 0)
    market_cap = data.get("market_cap", 0)
    risk = data.get("risk_score", 5)
    vol = data.get("volatility_annualized", 0)
    currency = data.get("currency", "USD")
    asset_t = data.get("asset_type", "Asset")

    # ── KPI Row ────────────────────────────────────────────────────────────────
    st.markdown(f"### 📊 {name} ({ticker}) — {asset_t}")
    k1, k2, k3, k4, k5 = st.columns(5)

    price_str = f"${price:,.6f}" if price < 0.01 else f"{currency} {price:,.4f}"
    with k1:
        st.metric("💰 Current Price", price_str)
    with k2:
        st.metric("📈 24H Change", f"{change:+.2f}%", delta=f"{change:+.2f}%")
    with k3:
        st.metric("🏦 Market Cap", format_number(market_cap))
    with k4:
        st.metric("⚡ Volatility", f"{vol:.1f}%")
    with k5:
        st.metric("🎯 Risk Score", f"{risk}/10", delta=get_risk_label(risk))

    st.markdown("---")

    # ── Chart + Analysis ───────────────────────────────────────────────────────
    col_chart, col_info = st.columns([3, 2])

    with col_chart:
        history = data.get("history")
        if history is not None and not (isinstance(history, pd.DataFrame) and history.empty):
            st.markdown("#### 📈 30-Day Price Chart")
            if isinstance(history, pd.DataFrame):
                if "Close" in history.columns:
                    close_col = "Close"
                else:
                    close_col = history.columns[0]
                y_data = history[close_col]
                x_data = history.index
            else:
                y_data = []
                x_data = []

            if len(y_data) > 0:
                color = "#3fb950" if float(y_data.iloc[-1]) >= float(y_data.iloc[0]) else "#f85149"
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=x_data, y=y_data,
                    mode="lines",
                    line=dict(color=color, width=2),
                    fill="tozeroy",
                    fillcolor=f"rgba({'63,185,80' if color == '#3fb950' else '248,81,73'},0.1)",
                    name="Price",
                    hovertemplate=f"<b>%{{x}}</b><br>Price: {currency} %{{y:,.4f}}<extra></extra>"
                ))
                fig.update_layout(
                    plot_bgcolor="#0d1117",
                    paper_bgcolor="#0d1117",
                    font=dict(color="#c9d1d9"),
                    xaxis=dict(gridcolor="#21262d", showgrid=True),
                    yaxis=dict(gridcolor="#21262d", showgrid=True),
                    margin=dict(l=0, r=0, t=20, b=0),
                    height=300,
                    showlegend=False,
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
                "Analyst Target": f"{currency} {data.get('analyst_target'):,.2f}" if data.get("analyst_target") else "N/A",
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
            col_a, col_b = st.columns([1, 1])
            col_a.markdown(f"<span style='color:#8b949e;font-size:0.85rem;'>{k}</span>", unsafe_allow_html=True)
            col_b.markdown(f"<span style='color:#c9d1d9;font-size:0.85rem;font-weight:600;'>{v}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Full Analysis Report ───────────────────────────────────────────────────
    st.markdown("#### 📄 Full Analysis Report")
    with st.container():
        st.markdown(report)

    # ── Download ───────────────────────────────────────────────────────────────
    st.download_button(
        label="📥 Download Analysis Report",
        data=report,
        file_name=f"FinSage_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )

else:
    # ── Welcome Screen ─────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:3rem 1rem;">
        <h2 style="color:#58a6ff;">👋 Welcome to FinSage!</h2>
        <p style="color:#8b949e;font-size:1.1rem;">Global Financial Intelligence Platform — powered by 100% FREE APIs</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="metric-card">
            <h3>🌍 Global Stocks</h3>
            <p style="font-size:1rem;margin-top:0.5rem;color:#8b949e;">NSE India, US, UK, Germany, Japan & more</p>
            <p style="font-size:0.85rem;color:#3fb950;">Try: RELIANCE.NS, AAPL, TSLA</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="metric-card">
            <h3>₿ Cryptocurrencies</h3>
            <p style="font-size:1rem;margin-top:0.5rem;color:#8b949e;">BTC, ETH, SOL, BNB and 100+ coins</p>
            <p style="font-size:0.85rem;color:#3fb950;">Try: BTC, ETH, SOL, XRP</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="metric-card">
            <h3>🎭 Meme Coins</h3>
            <p style="font-size:1rem;margin-top:0.5rem;color:#8b949e;">DOGE, SHIB, PEPE, FLOKI & more</p>
            <p style="font-size:0.85rem;color:#f85149;">⚠️ High Risk Assets</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;color:#8b949e;font-size:0.9rem;">
        <b>How to use:</b><br>
        1. Select Asset Type from the left sidebar<br>
        2. Enter ticker symbol or click Quick Pick<br>
        3. Click <b>🔍 Analyze Now</b>
    </div>
    """, unsafe_allow_html=True)

    # Disclaimer
    st.markdown("""
    <div class="disclaimer">
        ⚖️ <b>Legal Disclaimer:</b> FinSage is for <b>educational purposes only</b>. 
        Not financial advice. Not SEBI-registered. Past performance ≠ future results. 
        Consult a qualified financial advisor before investing.
    </div>
    """, unsafe_allow_html=True)
