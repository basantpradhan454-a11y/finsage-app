"""
FinSage — Global Financial Intelligence Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
100% FREE APIs:
  • yfinance   → Global Stocks (Yahoo Finance)
  • CoinGecko  → Crypto + Meme Coins (free public API)
  • Gemini AI  → AI-powered insights (gemini-2.5-flash)
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import logging

from data_fetcher import fetch_stock_data, fetch_crypto_data, fetch_live_prices
from analyzer import generate_report

logger = logging.getLogger("finsage.app")

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSage — Financial Intelligence",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Premium SaaS CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * { font-family: 'Inter', sans-serif !important; }

    /* ── Hide Streamlit branding ── */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 0.5rem !important; padding-bottom: 1rem !important; }

    /* ── Animated gradient background ── */
    .stApp {
        background: linear-gradient(135deg, #060913 0%, #0a0f1e 40%, #050d1a 100%);
        min-height: 100vh;
    }

    /* ── Hero Header ── */
    .hero-header {
        background: linear-gradient(135deg, #0d1b2a 0%, #1a1a2e 50%, #16213e 100%);
        border: 1px solid rgba(88,166,255,0.15);
        border-radius: 20px;
        padding: 2.5rem 3rem 2rem;
        margin-bottom: 1.2rem;
        position: relative;
        overflow: hidden;
    }
    .hero-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at 30% 50%, rgba(88,166,255,0.06) 0%, transparent 50%),
                    radial-gradient(circle at 70% 50%, rgba(63,185,80,0.04) 0%, transparent 50%);
        pointer-events: none;
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #58a6ff 0%, #79c0ff 50%, #a5d6ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-sub {
        font-size: 1rem;
        color: #7d8590;
        margin: 0.3rem 0 1rem 0;
        font-weight: 400;
    }
    .badge-row { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-top: 0.8rem; }
    .badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
    }
    .badge-green  { background: rgba(63,185,80,0.12);  border: 1px solid rgba(63,185,80,0.3);  color: #3fb950; }
    .badge-blue   { background: rgba(88,166,255,0.12); border: 1px solid rgba(88,166,255,0.3); color: #58a6ff; }
    .badge-purple { background: rgba(188,140,255,0.12);border: 1px solid rgba(188,140,255,0.3);color: #bc8cff; }
    .badge-orange { background: rgba(255,166,87,0.12); border: 1px solid rgba(255,166,87,0.3); color: #ffa657; }

    /* ── Ticker Bar ── */
    .ticker-wrap {
        background: rgba(22,27,34,0.8);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(48,54,61,0.8);
        border-radius: 12px;
        padding: 0.7rem 1.2rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
        flex-wrap: wrap;
        font-size: 0.82rem;
    }
    .ticker-label { color: #f85149; font-weight: 700; font-size: 0.72rem; letter-spacing: 1px; }
    .tick-up   { color: #3fb950; font-weight: 600; }
    .tick-down { color: #f85149; font-weight: 600; }
    .tick-name { color: #7d8590; font-size: 0.72rem; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #0a0f1a 100%) !important;
        border-right: 1px solid rgba(48,54,61,0.5) !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background: rgba(22,27,34,0.8) !important;
        border: 1px solid rgba(48,54,61,0.8) !important;
        color: #c9d1d9 !important;
        border-radius: 8px !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        border-color: rgba(88,166,255,0.5) !important;
        color: #58a6ff !important;
        background: rgba(88,166,255,0.08) !important;
    }

    /* ── Cards ── */
    .glass-card {
        background: rgba(22,27,34,0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(48,54,61,0.7);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s;
    }
    .glass-card:hover { border-color: rgba(88,166,255,0.2); }

    .metric-card {
        background: rgba(13,17,23,0.6);
        border: 1px solid rgba(48,54,61,0.6);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
        transition: all 0.2s;
    }
    .metric-card:hover {
        border-color: rgba(88,166,255,0.3);
        background: rgba(88,166,255,0.04);
    }
    .metric-label { font-size: 0.72rem; color: #7d8590; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 1.3rem; font-weight: 700; color: #e6edf3; margin: 0.3rem 0 0; }

    /* ── Asset Hero ── */
    .asset-hero {
        background: linear-gradient(135deg, rgba(22,27,34,0.9), rgba(13,17,23,0.9));
        border: 1px solid rgba(48,54,61,0.7);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .asset-name { font-size: 1.8rem; font-weight: 800; color: #e6edf3; margin: 0; }
    .asset-ticker {
        display: inline-block;
        background: rgba(88,166,255,0.1);
        border: 1px solid rgba(88,166,255,0.25);
        border-radius: 8px;
        padding: 0.2rem 0.7rem;
        font-size: 1rem;
        font-weight: 600;
        color: #58a6ff;
        margin-left: 0.5rem;
    }
    .asset-price { font-size: 2.2rem; font-weight: 800; color: #e6edf3; }
    .price-up   { color: #3fb950 !important; }
    .price-down { color: #f85149 !important; }
    .price-change { font-size: 1rem; font-weight: 600; }

    /* ── Section Headers ── */
    .section-title {
        font-size: 1rem;
        font-weight: 700;
        color: #7d8590;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin: 1.5rem 0 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .section-title::after {
        content: '';
        flex: 1;
        height: 1px;
        background: rgba(48,54,61,0.8);
    }

    /* ── Meme Warning ── */
    .meme-alert {
        background: linear-gradient(135deg, rgba(45,26,0,0.9), rgba(35,20,0,0.9));
        border: 1px solid rgba(212,120,10,0.5);
        border-left: 4px solid #d4780a;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin: 0.8rem 0;
        color: #ffa657;
    }

    /* ── AI Insight ── */
    .ai-card {
        background: linear-gradient(135deg, rgba(13,31,45,0.9), rgba(10,20,35,0.9));
        border: 1px solid rgba(88,166,255,0.25);
        border-radius: 16px;
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .ai-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #58a6ff, #bc8cff, #58a6ff);
    }
    .ai-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(88,166,255,0.1);
        border: 1px solid rgba(88,166,255,0.2);
        border-radius: 20px;
        padding: 0.2rem 0.8rem;
        font-size: 0.72rem;
        font-weight: 600;
        color: #58a6ff;
        margin-bottom: 0.8rem;
    }
    .ai-text { color: #c9d1d9; line-height: 1.7; font-size: 0.95rem; }

    /* ── Pulse Section ── */
    .pulse-card {
        background: rgba(13,17,23,0.5);
        border: 1px solid rgba(48,54,61,0.5);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        line-height: 1.8;
        color: #c9d1d9;
    }

    /* ── Risk Score ── */
    .risk-score-box {
        border-radius: 14px;
        padding: 1.5rem;
        text-align: center;
    }
    .risk-num { font-size: 3.5rem; font-weight: 800; line-height: 1; }
    .risk-denom { font-size: 1.2rem; color: #7d8590; }
    .risk-label { font-size: 0.9rem; font-weight: 600; margin-top: 0.5rem; }

    /* ── Verdict ── */
    .verdict-card {
        background: rgba(13,17,23,0.5);
        border: 1px solid rgba(48,54,61,0.5);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        line-height: 1.8;
    }

    /* ── Welcome Screen ── */
    .welcome-hero {
        background: linear-gradient(135deg, rgba(22,27,34,0.8), rgba(13,17,23,0.8));
        border: 1px solid rgba(48,54,61,0.6);
        border-radius: 20px;
        padding: 3rem;
        text-align: center;
        margin: 1rem 0;
    }
    .welcome-title { font-size: 2rem; font-weight: 700; color: #e6edf3; margin-bottom: 0.5rem; }
    .welcome-sub   { color: #7d8590; font-size: 1rem; margin-bottom: 2rem; }
    .step-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1.5rem 0; }
    .step-box {
        background: rgba(13,17,23,0.6);
        border: 1px solid rgba(48,54,61,0.5);
        border-radius: 12px;
        padding: 1.2rem;
        transition: border-color 0.2s;
    }
    .step-box:hover { border-color: rgba(88,166,255,0.3); }
    .step-num { font-size: 1.5rem; font-weight: 800; color: #58a6ff; }
    .step-text { font-size: 0.85rem; color: #7d8590; margin-top: 0.4rem; }

    .example-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.8rem; margin-top: 1.5rem; text-align: left; }
    .example-box {
        background: rgba(13,17,23,0.5);
        border: 1px solid rgba(48,54,61,0.4);
        border-radius: 10px;
        padding: 1rem 1.2rem;
    }
    .example-title { font-size: 0.8rem; font-weight: 600; color: #58a6ff; margin-bottom: 0.4rem; }
    .example-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
    .chip {
        background: rgba(48,54,61,0.5);
        border: 1px solid rgba(48,54,61,0.8);
        border-radius: 6px;
        padding: 0.15rem 0.5rem;
        font-size: 0.75rem;
        color: #c9d1d9;
        font-family: monospace !important;
    }

    /* ── Download Button ── */
    .stDownloadButton button {
        background: linear-gradient(135deg, rgba(88,166,255,0.1), rgba(88,166,255,0.05)) !important;
        border: 1px solid rgba(88,166,255,0.3) !important;
        color: #58a6ff !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    .stDownloadButton button:hover {
        background: rgba(88,166,255,0.15) !important;
        border-color: rgba(88,166,255,0.5) !important;
    }

    /* ── Disclaimer ── */
    .disclaimer {
        background: rgba(22,15,15,0.7);
        border: 1px solid rgba(248,81,73,0.15);
        border-left: 3px solid rgba(248,81,73,0.5);
        border-radius: 10px;
        padding: 1rem 1.5rem;
        font-size: 0.78rem;
        color: #6e7681;
        margin-top: 2rem;
        line-height: 1.6;
    }

    /* ── Streamlit overrides ── */
    .stMetric { background: rgba(13,17,23,0.5) !important; border-radius: 10px !important; padding: 0.8rem !important; border: 1px solid rgba(48,54,61,0.5) !important; }
    div[data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 700 !important; }
    div[data-testid="stMetricLabel"] { font-size: 0.72rem !important; }
    .stSelectbox > div { background: rgba(22,27,34,0.8) !important; border: 1px solid rgba(48,54,61,0.8) !important; border-radius: 10px !important; }
    .stTextInput > div > div { background: rgba(22,27,34,0.8) !important; border: 1px solid rgba(48,54,61,0.8) !important; border-radius: 10px !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(48,54,61,0.5) !important; }
    .stDivider { border-color: rgba(48,54,61,0.5) !important; }
    .stExpander { background: rgba(13,17,23,0.4) !important; border: 1px solid rgba(48,54,61,0.4) !important; border-radius: 10px !important; }
    .stDataFrame { border-radius: 10px !important; overflow: hidden; }
    .stAlert { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)


# ── Hero Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
        <div>
            <h1 class="hero-title">💹 FinSage</h1>
            <p class="hero-sub">Global Financial Intelligence — AI-Powered Analysis</p>
            <div class="badge-row">
                <span class="badge badge-green">✅ 100% Free APIs</span>
                <span class="badge badge-blue">🤖 Gemini AI</span>
                <span class="badge badge-purple">🌍 Global Markets</span>
                <span class="badge badge-orange">⚡ Real-Time Data</span>
            </div>
        </div>
        <div style="text-align:right; color:#7d8590; font-size:0.8rem; line-height:1.8;">
            <div>📈 NSE · BSE · NYSE · NASDAQ</div>
            <div>₿ 10,000+ Cryptocurrencies</div>
            <div>🎭 Meme Coins & Speculative Assets</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Live Ticker Bar ───────────────────────────────────────────────────────────
with st.spinner(""):
    live = fetch_live_prices()

if live:
    labels = {
        "bitcoin": "BTC", "ethereum": "ETH", "dogecoin": "DOGE",
        "solana": "SOL", "shiba-inu": "SHIB", "binancecoin": "BNB"
    }
    items_html = ""
    for coin_id, label in labels.items():
        if coin_id in live:
            price = live[coin_id].get("usd", 0)
            chg   = live[coin_id].get("usd_24h_change", 0) or 0
            cls   = "tick-up" if chg >= 0 else "tick-down"
            arrow = "▲" if chg >= 0 else "▼"
            pfmt  = f"${price:,.4f}" if price < 1 else f"${price:,.2f}"
            items_html += f'<span><span class="tick-name">{label}</span> <span class="{cls}">{pfmt} {arrow}{abs(chg):.1f}%</span></span> '

    st.markdown(f'''
    <div class="ticker-wrap">
        <span class="ticker-label">● LIVE</span>
        {items_html}
    </div>''', unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Asset Search")
    st.markdown('<span class="badge badge-green">✅ FREE — No API Keys Required</span>', unsafe_allow_html=True)
    st.markdown("")

    asset_type = st.selectbox(
        "Asset Type",
        ["🌍 Global Stock", "₿ Cryptocurrency", "🎭 Meme Coin"],
        label_visibility="collapsed",
    )

    if "Stock" in asset_type:
        placeholder = "e.g. AAPL, RELIANCE.NS, TSLA"
        quick_picks = ["AAPL", "RELIANCE.NS", "TCS.NS", "TSLA", "NVDA", "MSFT"]
    elif "Cryptocurrency" in asset_type:
        placeholder = "e.g. BTC, ETH, SOL"
        quick_picks = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA"]
    else:
        placeholder = "e.g. DOGE, SHIB, PEPE"
        quick_picks = ["DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF"]

    ticker_input = st.text_input("", placeholder=placeholder, label_visibility="collapsed")

    st.markdown('<div style="font-size:0.75rem; color:#7d8590; margin-bottom:0.4rem;">⚡ Quick Pick</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    selected_quick = None
    for i, ex in enumerate(quick_picks):
        if cols[i % 3].button(ex, key=f"qp_{ex}", use_container_width=True):
            selected_quick = ex

    final_ticker = selected_quick or ticker_input

    analyze_btn = st.button("🔍 Analyze Now", use_container_width=True, type="primary")

    st.divider()

    with st.expander("🌍 Exchange Formats"):
        st.markdown("""
| Exchange  | Suffix | Example |
|-----------|--------|---------|
| NSE India | `.NS`  | `RELIANCE.NS` |
| BSE India | `.BO`  | `TCS.BO` |
| US Market | —      | `AAPL` |
| London    | `.L`   | `BP.L` |
| Frankfurt | `.DE`  | `BMW.DE` |
| Tokyo     | `.T`   | `7203.T` |
""")

    st.divider()
    st.markdown('<div style="font-size:0.78rem; color:#7d8590; font-weight:600; text-transform:uppercase; letter-spacing:1px; margin-bottom:0.6rem;">API Status</div>', unsafe_allow_html=True)
    st.success("✅ yfinance — FREE")
    st.success("✅ CoinGecko — FREE")
    st.success("✅ Gemini AI — FREE")
    st.caption("Cache: 5min · Retries: 3x · Timeout: 15s")


# ── Main Analysis Panel ───────────────────────────────────────────────────────
if analyze_btn and final_ticker:
    with st.spinner(f"Fetching live data for **{final_ticker.upper()}**…"):
        try:
            if "Stock" in asset_type:
                data = fetch_stock_data(final_ticker)
            else:
                data = fetch_crypto_data(final_ticker)
            report = generate_report(data)
        except ValueError as ve:
            st.error(f"❌ **Data Error:** {ve}")
            st.stop()
        except Exception as e:
            logger.error(f"Error for {final_ticker}: {e}", exc_info=True)
            st.error(f"❌ **Error:** {str(e)[:250]}")
            st.stop()

    # ── Asset Hero ────────────────────────────────────────────────────────────
    cp  = data.get("current_price")
    cur = data.get("currency", "$") if data["asset_type"] == "stock" else "$"
    chg = data.get("change_pct") or data.get("change_24h") or 0
    chg_cls = "price-up" if chg >= 0 else "price-down"
    chg_arrow = "▲" if chg >= 0 else "▼"
    price_str = f"{cur}{cp:,.4f}" if cp and cp < 1 else (f"{cur}{cp:,.2f}" if cp else "N/A")

    st.markdown(f"""
    <div class="asset-hero">
        <div>
            <div>
                <span class="asset-name">{report['name']}</span>
                <span class="asset-ticker">{report['ticker']}</span>
            </div>
            <div style="margin-top:0.5rem; display:flex; gap:0.6rem; flex-wrap:wrap; align-items:center;">
                <span class="badge badge-blue">📍 {report['exchange']}</span>
                <span class="badge badge-purple">{report['category']}</span>
                <span class="badge badge-green">✅ {data.get('data_source','Free API')}</span>
            </div>
        </div>
        <div style="text-align:right;">
            <div class="asset-price">{price_str}</div>
            <div class="price-change {chg_cls}">{chg_arrow} {abs(chg):.2f}% (24h)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Meme Warning ──────────────────────────────────────────────────────────
    if report.get("is_meme"):
        st.markdown("""
        <div class="meme-alert">
            <b>⚠️ EXTREME RISK — SPECULATIVE / MEME ASSET</b><br>
            Koi fundamental value nahi hai. Price 100% social hype aur speculation se chalta hai.
            Invest sirf utna karein jo aap poora kho sakte hain.
        </div>
        """, unsafe_allow_html=True)

    # ── Key Metrics Grid ──────────────────────────────────────────────────────
    st.markdown('<div class="section-title">📊 Key Metrics</div>', unsafe_allow_html=True)
    metrics = report["metrics"]
    items   = list(metrics.items())
    cols    = st.columns(5)
    for i, (k, v) in enumerate(items[:10]):
        cols[i % 5].metric(label=k, value=v)

    with st.expander("📋 Full Metrics Table"):
        df = pd.DataFrame(list(metrics.items()), columns=["Metric", "Value"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    if report["asset_type"] == "stock" and data.get("hist_closes"):
        st.markdown('<div class="section-title">📈 5-Day Price Trend</div>', unsafe_allow_html=True)
        closes = data["hist_closes"]
        color  = "#3fb950" if closes[-1] >= closes[0] else "#f85149"
        fill   = "rgba(63,185,80,0.08)" if color == "#3fb950" else "rgba(248,81,73,0.08)"
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=closes, mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=8, color=color, line=dict(color="#0d1117", width=2)),
            fill="tozeroy", fillcolor=fill,
        ))
        fig.update_layout(
            paper_bgcolor="rgba(13,17,23,0.5)", plot_bgcolor="rgba(13,17,23,0.5)",
            font=dict(color="#7d8590", size=11),
            xaxis=dict(showgrid=False, title="Trading Day", color="#7d8590"),
            yaxis=dict(showgrid=True, gridcolor="rgba(48,54,61,0.4)", color="#7d8590"),
            height=280, margin=dict(t=20, b=30, l=10, r=10),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    elif report["asset_type"] == "crypto":
        c1, c2 = st.columns(2)
        high = data.get("high_24h") or 0
        low  = data.get("low_24h") or 0
        curr = data.get("current_price") or 0

        with c1:
            if high and low:
                st.markdown('<div class="section-title">📈 24h Range</div>', unsafe_allow_html=True)
                vfmt = ",.4f" if curr < 1 else (",.2f" if curr < 1000 else ",.0f")
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=curr,
                    gauge={
                        "axis": {"range": [low * 0.95, high * 1.05], "tickformat": vfmt, "tickfont": {"size": 10}},
                        "bar":  {"color": "#58a6ff", "thickness": 0.25},
                        "bgcolor": "rgba(13,17,23,0)",
                        "bordercolor": "rgba(48,54,61,0.3)",
                        "steps": [
                            {"range": [low * 0.95, low],        "color": "rgba(248,81,73,0.1)"},
                            {"range": [low, (low+high)/2],      "color": "rgba(13,17,23,0.5)"},
                            {"range": [(low+high)/2, high],     "color": "rgba(63,185,80,0.1)"},
                            {"range": [high, high * 1.05],      "color": "rgba(63,185,80,0.2)"},
                        ],
                    },
                    title={"text": f"${low:{vfmt}} — ${high:{vfmt}}", "font": {"size": 11, "color": "#7d8590"}},
                    number={"prefix": "$", "valueformat": vfmt, "font": {"size": 18, "color": "#e6edf3"}}
                ))
                fig_g.update_layout(
                    paper_bgcolor="rgba(13,17,23,0.5)", font=dict(color="#7d8590"),
                    height=240, margin=dict(t=20, b=10, l=10, r=10)
                )
                st.plotly_chart(fig_g, use_container_width=True)

        with c2:
            st.markdown('<div class="section-title">💬 Sentiment</div>', unsafe_allow_html=True)
            sent_up   = data.get("sentiment_up_pct") or 50
            sent_down = 100 - sent_up
            fig_s = go.Figure(go.Pie(
                labels=["Bullish 📈", "Bearish 📉"],
                values=[sent_up, sent_down],
                hole=0.6,
                marker=dict(
                    colors=["#3fb950", "#f85149"],
                    line=dict(color="rgba(13,17,23,0.8)", width=2)
                ),
                textinfo="label+percent",
                textfont=dict(size=12, color="#c9d1d9"),
            ))
            fig_s.update_layout(
                paper_bgcolor="rgba(13,17,23,0.5)", font=dict(color="#c9d1d9"),
                showlegend=False, height=240, margin=dict(t=10, b=10)
            )
            st.plotly_chart(fig_s, use_container_width=True)

            socials = {
                "🐦 Twitter": data.get("twitter_followers"),
                "📢 Reddit":  data.get("reddit_subscribers"),
                "👥 Active (48h)": data.get("reddit_active_48h"),
            }
            for lbl, val in socials.items():
                if val:
                    st.caption(f"{lbl}: **{val:,}**")

    # ── The Pulse ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">🔬 The Pulse</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pulse-card">{report["pulse"]}</div>', unsafe_allow_html=True)

    # ── AI Insight ────────────────────────────────────────────────────────────
    if report.get("ai_insight"):
        st.markdown('<div class="section-title">🤖 AI Insight</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="ai-card">
            <div class="ai-badge">✨ Gemini 2.5 Flash</div>
            <div class="ai-text">{report["ai_insight"]}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Risk Matrix ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">⚖️ Risk Matrix</div>', unsafe_allow_html=True)
    r1, r2, r3 = st.columns([1, 2, 1])

    score_color = "#f85149" if report["risk_score"] >= 7 else "#d4780a" if report["risk_score"] >= 5 else "#3fb950"
    score_bg    = "rgba(248,81,73,0.08)" if report["risk_score"] >= 7 else "rgba(212,120,10,0.08)" if report["risk_score"] >= 5 else "rgba(63,185,80,0.08)"

    with r1:
        st.markdown(f"""
        <div class="risk-score-box" style="background:{score_bg}; border:1px solid {score_color}33;">
            <div class="risk-num" style="color:{score_color}">{report['risk_score']}</div>
            <div class="risk-denom">/10</div>
            <div class="risk-label" style="color:{score_color}">{report['risk_label']}</div>
        </div>
        """, unsafe_allow_html=True)

    with r2:
        fig_risk = go.Figure(go.Indicator(
            mode="gauge+number",
            value=report["risk_score"],
            gauge={
                "axis": {"range": [1, 10], "tickvals": [1,3,5,7,10], "tickfont": {"size": 10}, "tickcolor": "#7d8590"},
                "bar":  {"color": score_color, "thickness": 0.25},
                "bgcolor": "rgba(13,17,23,0)",
                "bordercolor": "rgba(48,54,61,0.3)",
                "steps": [
                    {"range": [1, 3],  "color": "rgba(63,185,80,0.12)"},
                    {"range": [3, 5],  "color": "rgba(63,185,80,0.06)"},
                    {"range": [5, 7],  "color": "rgba(212,120,10,0.1)"},
                    {"range": [7, 9],  "color": "rgba(248,81,73,0.1)"},
                    {"range": [9, 10], "color": "rgba(248,81,73,0.2)"},
                ],
            },
            number={"font": {"size": 18, "color": score_color}}
        ))
        fig_risk.update_layout(
            paper_bgcolor="rgba(13,17,23,0.5)", font=dict(color="#7d8590"),
            height=200, margin=dict(t=10, b=10, l=20, r=20)
        )
        st.plotly_chart(fig_risk, use_container_width=True)

    with r3:
        vtype = "Extreme Volatility" if report.get("is_meme") else \
                ("Crypto Volatility" if report["asset_type"] == "crypto" else "Market Cyclicality")
        st.markdown(f"""
        <div style="background:rgba(13,17,23,0.5); border:1px solid rgba(48,54,61,0.5);
                    border-radius:12px; padding:1.2rem; text-align:center; height:100%;">
            <div style="font-size:0.7rem; color:#7d8590; text-transform:uppercase; letter-spacing:1px;">Risk Driver</div>
            <div style="font-size:0.9rem; font-weight:700; color:#c9d1d9; margin-top:0.8rem; line-height:1.4;">{vtype}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:rgba(13,17,23,0.4); border:1px solid rgba(48,54,61,0.4);
                border-radius:10px; padding:1rem 1.2rem; margin-top:0.8rem; color:#c9d1d9; font-size:0.9rem; line-height:1.6;">
        📌 {report['risk_explanation']}
    </div>
    """, unsafe_allow_html=True)

    # ── Verdict ───────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">🎯 Verdict</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="verdict-card">{report["verdict"]}</div>', unsafe_allow_html=True)

    st.markdown("")

    # ── Download ──────────────────────────────────────────────────────────────
    full_text = f"""FinSage — Financial Intelligence Report
{"=" * 50}
Asset    : {report['name']} ({report['ticker']})
Market   : {report['exchange']}
Category : {report['category']}
Source   : {data.get('data_source', 'Free API')}

KEY METRICS
{"-" * 40}
{chr(10).join(f"{k:<22}: {v}" for k,v in metrics.items())}

THE PULSE
{"-" * 40}
{report['pulse']}

AI INSIGHT (Gemini)
{"-" * 40}
{report.get('ai_insight') or 'Not available'}

RISK MATRIX
{"-" * 40}
Score       : {report['risk_score']}/10
Rating      : {report['risk_label']}
Explanation : {report['risk_explanation']}

VERDICT
{"-" * 40}
{report['verdict']}

{"=" * 50}
DISCLAIMER: Educational purposes only. NOT financial advice.
NOT SEBI-registered. Investing involves risk including total loss of principal. DYOR.
"""
    st.download_button(
        "📥 Download Full Report (.txt)",
        data=full_text,
        file_name=f"finsage_{report['ticker'].replace('/', '_')}_report.txt",
        mime="text/plain",
        use_container_width=True,
    )

elif analyze_btn and not final_ticker:
    st.warning("⚠️ Ticker symbol enter karein ya quick pick use karein.")

else:
    # ── Welcome Screen ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="welcome-hero">
        <div class="welcome-title">Welcome to FinSage 💹</div>
        <div class="welcome-sub">AI-Powered Financial Intelligence for Stocks, Crypto & Meme Coins</div>
        <div class="step-grid">
            <div class="step-box">
                <div class="step-num">01</div>
                <div class="step-text">Asset Type choose karein<br><b style="color:#c9d1d9">Stock / Crypto / Meme</b></div>
            </div>
            <div class="step-box">
                <div class="step-num">02</div>
                <div class="step-text">Ticker enter karein ya<br><b style="color:#c9d1d9">Quick Pick</b> use karein</div>
            </div>
            <div class="step-box">
                <div class="step-num">03</div>
                <div class="step-text">Click <b style="color:#58a6ff">Analyze Now</b> aur<br>full report dekhein</div>
            </div>
        </div>
        <div class="example-grid">
            <div class="example-box">
                <div class="example-title">🇮🇳 Indian Markets (NSE/BSE)</div>
                <div class="example-chips">
                    <span class="chip">RELIANCE.NS</span>
                    <span class="chip">TCS.NS</span>
                    <span class="chip">HDFCBANK.NS</span>
                    <span class="chip">INFY.NS</span>
                </div>
            </div>
            <div class="example-box">
                <div class="example-title">🇺🇸 US Markets (NYSE/NASDAQ)</div>
                <div class="example-chips">
                    <span class="chip">AAPL</span>
                    <span class="chip">NVDA</span>
                    <span class="chip">TSLA</span>
                    <span class="chip">MSFT</span>
                </div>
            </div>
            <div class="example-box">
                <div class="example-title">₿ Cryptocurrency</div>
                <div class="example-chips">
                    <span class="chip">BTC</span>
                    <span class="chip">ETH</span>
                    <span class="chip">SOL</span>
                    <span class="chip">BNB</span>
                </div>
            </div>
            <div class="example-box">
                <div class="example-title">🎭 Meme Coins</div>
                <div class="example-chips">
                    <span class="chip">DOGE</span>
                    <span class="chip">SHIB</span>
                    <span class="chip">PEPE</span>
                    <span class="chip">FLOKI</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Live Prices on Welcome
    if live:
        st.markdown('<div class="section-title">🔴 Live Crypto Prices</div>', unsafe_allow_html=True)
        price_labels = {"bitcoin": "Bitcoin", "ethereum": "Ethereum", "solana": "Solana",
                        "binancecoin": "BNB", "dogecoin": "Dogecoin"}
        pcols = st.columns(len(price_labels))
        for i, (cid, lbl) in enumerate(price_labels.items()):
            if cid in live:
                p   = live[cid].get("usd", 0)
                chg = live[cid].get("usd_24h_change", 0) or 0
                pfmt = f"${p:,.4f}" if p < 1 else f"${p:,.2f}"
                pcols[i].metric(lbl, pfmt, f"{chg:+.2f}%")


# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer">
    <b>⚖️ IMPORTANT DISCLAIMER</b> — This application is for <b>educational and informational purposes only</b>
    and does not constitute financial, investment, or trading advice. We are <b>NOT SEBI-registered financial advisors</b>.
    All investments involve significant risk including <b>possible loss of principal</b>.
    You are solely responsible for your own investment decisions. Please DYOR and consult a qualified professional.<br>
    <i>Data: Yahoo Finance (yfinance) · CoinGecko Free API · AI: Google Gemini 2.5 Flash · Data may be delayed. Not for live trading.</i>
</div>
""", unsafe_allow_html=True)
