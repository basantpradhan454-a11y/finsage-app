"""
FinSage — Global Financial Intelligence Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
100% FREE APIs:
  • yfinance   → Global Stocks (Yahoo Finance)
  • CoinGecko  → Crypto + Meme Coins (free public API)

Run: streamlit run app.py
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
    page_title="FinSage — Global Financial Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        padding: 2rem 2rem 1.5rem;
        border-radius: 14px;
        margin-bottom: 1.2rem;
        text-align: center;
        color: white;
    }
    .main-header h1 { font-size: 2.4rem; margin-bottom: 0.2rem; }
    .main-header p  { opacity: 0.75; margin: 0.2rem 0; }

    .ticker-bar {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.85rem;
        color: #c9d1d9;
        display: flex; gap: 2rem; flex-wrap: wrap;
    }
    .ticker-item-up   { color: #3fb950; font-weight: 600; }
    .ticker-item-down { color: #f85149; font-weight: 600; }

    .report-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .meme-warning {
        background: #2d1a00;
        border: 2px solid #d4780a;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        margin: 0.8rem 0;
        color: #ffa657;
    }
    .disclaimer-box {
        background: #160f0f;
        border-left: 4px solid #f85149;
        padding: 1rem 1.5rem;
        border-radius: 6px;
        font-size: 0.82rem;
        color: #8b949e;
        margin-top: 2rem;
    }
    .free-badge {
        background: #1a3a1a;
        border: 1px solid #3fb950;
        border-radius: 6px;
        padding: 0.3rem 0.8rem;
        color: #3fb950;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    [data-testid="stSidebar"] { background: #0d1117; }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📊 FinSage</h1>
    <p style="font-size:1.05rem">Global Financial Intelligence Platform</p>
    <p style="font-size:0.8rem">Stocks · Cryptocurrency · Meme Coins</p>
    <br>
    <span class="free-badge">✅ 100% FREE — No API Key Required</span>
</div>
""", unsafe_allow_html=True)


# ── Live Ticker Bar ───────────────────────────────────────────────────────────
with st.spinner("Loading live prices…"):
    live = fetch_live_prices()

if live:
    labels = {
        "bitcoin": "BTC", "ethereum": "ETH", "dogecoin": "DOGE",
        "solana": "SOL", "shiba-inu": "SHIB", "binancecoin": "BNB"
    }
    items_html = ""
    for coin_id, label in labels.items():
        if coin_id in live:
            price  = live[coin_id].get("usd", 0)
            chg    = live[coin_id].get("usd_24h_change", 0) or 0
            color  = "ticker-item-up" if chg >= 0 else "ticker-item-down"
            arrow  = "▲" if chg >= 0 else "▼"
            p_fmt  = f"${price:,.4f}" if price < 1 else f"${price:,.2f}"
            items_html += f'<span class="{color}">{label} {p_fmt} {arrow}{abs(chg):.1f}%</span> '

    st.markdown(f'<div class="ticker-bar">🔴 LIVE &nbsp;|&nbsp; {items_html}</div>', unsafe_allow_html=True)


# ── Sidebar Controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Asset Search")
    st.markdown('<span class="free-badge">✅ FREE APIs Only</span>', unsafe_allow_html=True)
    st.markdown("---")

    asset_type = st.selectbox(
        "Select Asset Type",
        ["🌍 Global Stock", "₿ Cryptocurrency", "🎭 Meme Coin"],
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

    ticker_input = st.text_input("Enter Ticker Symbol", placeholder=placeholder)

    st.markdown("**⚡ Quick Pick:**")
    cols = st.columns(3)
    selected_quick = None
    for i, ex in enumerate(quick_picks):
        if cols[i % 3].button(ex, key=f"qp_{ex}", use_container_width=True):
            selected_quick = ex

    final_ticker = selected_quick or ticker_input

    analyze_btn = st.button("🔍 Analyze Now", use_container_width=True, type="primary")

    st.markdown("---")
    st.markdown("### 🌍 Exchange Formats")
    st.markdown("""
| Exchange  | Suffix    | Example         |
|-----------|-----------|-----------------|
| NSE India | `.NS`     | `RELIANCE.NS`   |
| BSE India | `.BO`     | `TCS.BO`        |
| US Market | —         | `AAPL`, `NVDA`  |
| London    | `.L`      | `BP.L`          |
| Frankfurt | `.DE`     | `BMW.DE`        |
| Tokyo     | `.T`      | `7203.T`        |
| Crypto    | —         | `BTC`, `ETH`    |
| Meme Coin | —         | `DOGE`, `SHIB`  |
""")
    st.markdown("---")
    st.markdown("### 🔑 API Status")
    st.success("✅ yfinance — FREE (No Key)")
    st.success("✅ CoinGecko — FREE (No Key)")
    st.info("💡 Want higher rate limits?\nGet a FREE demo key at [coingecko.com](https://coingecko.com)")
    st.caption("Cache: 5 min | Retries: 3x | Timeout: 15s")


# ── Main Analysis Panel ───────────────────────────────────────────────────────
if analyze_btn and final_ticker:
    with st.spinner(f"🔍 Fetching live data for **{final_ticker.upper()}**…"):
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
            st.error(f"❌ **Error:** {str(e)[:250]}\n\nPlease check the ticker symbol and try again.")
            st.stop()

    # ── Data Source Badge ─────────────────────────────────────────────────────
    src = data.get("data_source", "")
    st.markdown(f'<span class="free-badge">✅ {src}</span>', unsafe_allow_html=True)
    st.markdown("")

    # ── Asset Identity ────────────────────────────────────────────────────────
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(f"## 🏷️ {report['name']} `{report['ticker']}`")
        st.markdown(f"**Exchange/Market:** {report['exchange']}  |  **Category:** {report['category']}")
    with col_b:
        cp = data.get("current_price")
        currency = data.get("currency", "$") if data["asset_type"] == "stock" else "$"
        chg = data.get("change_pct") or data.get("change_24h") or 0
        if cp:
            st.metric(
                label="Live Price",
                value=f"{currency} {cp:,.4f}" if cp < 1 else f"{currency} {cp:,.2f}",
                delta=f"{chg:+.2f}%"
            )

    # ── Meme Warning ──────────────────────────────────────────────────────────
    if report.get("is_meme"):
        st.markdown("""
        <div class="meme-warning">
            <b>⚠️ EXTREME RISK — SPECULATIVE / MEME ASSET</b><br>
            Koi fundamental value nahi hai. Price 100% social hype aur speculation se chalta hai.
            Invest sirf utna karein jo aap poora kho sakte hain.
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Key Metrics ───────────────────────────────────────────────────────────
    st.markdown("### 📊 Key Metrics")
    metrics = report["metrics"]
    items = list(metrics.items())
    cols = st.columns(5)
    for i, (k, v) in enumerate(items[:10]):
        cols[i % 5].metric(label=k, value=v)

    # Full metrics table
    with st.expander("📋 View Full Metrics Table"):
        df = pd.DataFrame(list(metrics.items()), columns=["Metric", "Value"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Price Chart (Stock) ───────────────────────────────────────────────────
    if report["asset_type"] == "stock" and data.get("hist_closes"):
        st.markdown("### 📈 5-Day Price Trend")
        closes = data["hist_closes"]
        color  = "#3fb950" if closes[-1] >= closes[0] else "#f85149"
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=closes, mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=7, color=color),
            fill="tozeroy", fillcolor="rgba(63,185,80,0.08)" if color == "#3fb950" else "rgba(248,81,73,0.08)",
        ))
        fig.update_layout(
            title=f"{report['name']} — Last 5 Trading Days",
            paper_bgcolor="#161b22", plot_bgcolor="#161b22",
            font=dict(color="#c9d1d9"),
            xaxis=dict(showgrid=False, title="Day"),
            yaxis=dict(showgrid=True, gridcolor="#21262d"),
            height=280, margin=dict(t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Crypto: 24h Range Gauge + Sentiment ──────────────────────────────────
    elif report["asset_type"] == "crypto":
        c1, c2 = st.columns(2)

        with c1:
            high = data.get("high_24h") or 0
            low  = data.get("low_24h") or 0
            curr = data.get("current_price") or 0
            if high and low:
                st.markdown("### 📈 24h Price Range")
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=curr,
                    gauge={
                        "axis": {"range": [low * 0.95, high * 1.05], "tickformat": ",.4f" if curr < 1 else (",.2f" if curr < 1000 else ",.0f")},
                        "bar": {"color": "#58a6ff"},
                        "steps": [
                            {"range": [low * 0.95, low], "color": "#2d1a00"},
                            {"range": [low, high], "color": "#161b22"},
                            {"range": [high, high * 1.05], "color": "#0d2818"},
                        ],
                    },
                    title={"text": (f"Range: ${low:,.4f} — ${high:,.4f}" if curr < 1 else f"Range: ${low:,.2f} — ${high:,.2f}"), "font": {"size": 12}},
                    number={"prefix": "$", "valueformat": ",.4f" if curr < 1 else (",.2f" if curr < 1000 else ",.0f")}
                ))
                fig_g.update_layout(paper_bgcolor="#161b22", font=dict(color="#c9d1d9"), height=250, margin=dict(t=20,b=10))
                st.plotly_chart(fig_g, use_container_width=True)

        with c2:
            st.markdown("### 💬 Community Sentiment")
            sent_up   = data.get("sentiment_up_pct") or 50
            sent_down = 100 - sent_up
            fig_s = go.Figure(go.Pie(
                labels=["Bullish 📈", "Bearish 📉"],
                values=[sent_up, sent_down],
                hole=0.55,
                marker=dict(colors=["#3fb950", "#f85149"]),
                textinfo="label+percent",
                textfont=dict(size=13)
            ))
            fig_s.update_layout(
                paper_bgcolor="#161b22", font=dict(color="#c9d1d9"),
                showlegend=False, height=250, margin=dict(t=20, b=10)
            )
            st.plotly_chart(fig_s, use_container_width=True)

            # Social stats
            socials = {
                "🐦 Twitter": data.get("twitter_followers"),
                "📢 Reddit": data.get("reddit_subscribers"),
                "👥 Active (48h)": data.get("reddit_active_48h"),
            }
            for label, val in socials.items():
                if val:
                    st.caption(f"{label}: **{val:,}**")

    st.divider()

    # ── The Pulse ─────────────────────────────────────────────────────────────
    st.markdown("### 🔬 The Pulse — Deep Analysis")
    st.markdown(report["pulse"])

    # ── Gemini AI Insight ────────────────────────────────────────────────────
    if report.get("ai_insight"):
        st.markdown("### 🤖 AI Insight — Gemini")
        st.markdown(f"""
        <div style="background:#0d1f2d; border:1px solid #58a6ff; border-radius:10px; padding:1.2rem 1.5rem; margin-bottom:0.5rem;">
            <span style="font-size:0.8rem; color:#58a6ff; font-weight:600;">✨ Powered by Gemini 2.5 Flash</span>
            <p style="color:#c9d1d9; margin-top:0.6rem; line-height:1.6;">{report["ai_insight"]}</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Risk Matrix ───────────────────────────────────────────────────────────
    st.markdown("### ⚖️ Unified Risk Matrix")
    r1, r2, r3 = st.columns([1, 2, 1])

    score_color = "#f85149" if report["risk_score"] >= 7 else "#d4780a" if report["risk_score"] >= 5 else "#3fb950"
    with r1:
        st.markdown(f"""
        <div style="text-align:center; padding:1.5rem; background:#161b22;
                    border:1px solid {score_color}; border-radius:10px;">
            <div style="font-size:0.85rem; color:#8b949e;">Risk Score</div>
            <div style="font-size:3rem; font-weight:bold; color:{score_color}">
                {report['risk_score']}/10
            </div>
            <div style="font-size:1rem;">{report['risk_label']}</div>
        </div>
        """, unsafe_allow_html=True)

    with r2:
        fig_risk = go.Figure(go.Indicator(
            mode="gauge+number",
            value=report["risk_score"],
            gauge={
                "axis": {"range": [1, 10], "tickvals": [1,3,5,7,10], "tickfont": {"size": 11}},
                "bar":  {"color": score_color, "thickness": 0.3},
                "steps": [
                    {"range": [1, 3],  "color": "#0d2818"},
                    {"range": [3, 5],  "color": "#1a2d00"},
                    {"range": [5, 7],  "color": "#2d1f00"},
                    {"range": [7, 9],  "color": "#2d0f00"},
                    {"range": [9, 10], "color": "#3d0000"},
                ],
            },
            number={"font": {"size": 20, "color": score_color}}
        ))
        fig_risk.update_layout(
            paper_bgcolor="#161b22", font=dict(color="#c9d1d9"),
            height=210, margin=dict(t=10, b=10, l=20, r=20)
        )
        st.plotly_chart(fig_risk, use_container_width=True)

    with r3:
        vtype = "Extreme Volatility" if report.get("is_meme") else \
                ("Crypto Volatility" if report["asset_type"] == "crypto" else "Market Cyclicality")
        st.markdown(f"""
        <div style="text-align:center; padding:1.5rem; background:#161b22;
                    border:1px solid #30363d; border-radius:10px; margin-top:0.3rem;">
            <div style="font-size:0.82rem; color:#8b949e;">Risk Driver</div>
            <div style="font-size:0.95rem; font-weight:600; color:#c9d1d9; margin-top:0.5rem;">
                {vtype}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"**📌 Risk Explanation:** {report['risk_explanation']}")

    st.divider()

    # ── Verdict ───────────────────────────────────────────────────────────────
    st.markdown("### 🎯 Verdict — Price Move Triggers")
    st.markdown(report["verdict"])

    st.divider()

    # ── Download Report ───────────────────────────────────────────────────────
    full_text = f"""
FinSage — Financial Intelligence Report
{"=" * 50}
Asset  : {report['name']} ({report['ticker']})
Market : {report['exchange']}
Category: {report['category']}
Source : {data.get('data_source', 'Free API')}

KEY METRICS
{"-" * 40}
{chr(10).join(f"{k:<22}: {v}" for k,v in metrics.items())}

THE PULSE
{"-" * 40}
{report['pulse']}

RISK MATRIX
{"-" * 40}
Score       : {report['risk_score']}/10
Rating      : {report['risk_label']}
Explanation : {report['risk_explanation']}

VERDICT
{"-" * 40}
{report['verdict']}

{"=" * 50}
DISCLAIMER: This analysis is for educational purposes only. It is NOT financial advice.
Investing involves significant risk including total loss of principal.
We are NOT SEBI-registered advisors. Please DYOR and consult a qualified professional.
"""
    st.download_button(
        "📥 Download Full Report (.txt)",
        data=full_text,
        file_name=f"finsage_{report['ticker'].replace('/', '_')}_report.txt",
        mime="text/plain",
        use_container_width=True,
    )

elif analyze_btn and not final_ticker:
    st.warning("⚠️ Ticker symbol enter karein ya quick pick karein.")

else:
    # Welcome Screen
    st.markdown("""
    <div class="report-card">
        <h3>👋 FinSage mein swagat hai!</h3>
        <p>Global Financial Intelligence Platform — 100% FREE APIs se powered.</p>
        <br>
        <b>Kaise use karein:</b>
        <ol>
            <li>Left sidebar mein <b>Asset Type</b> select karein</li>
            <li><b>Ticker symbol</b> type karein ya Quick Pick button dabayein</li>
            <li><b>Analyze Now</b> dabayein</li>
        </ol>
        <br>
        <b>Examples:</b>
        <ul>
            <li>🇮🇳 NSE: <code>RELIANCE.NS</code>, <code>TCS.NS</code>, <code>HDFCBANK.NS</code></li>
            <li>🇺🇸 US: <code>AAPL</code>, <code>NVDA</code>, <code>TSLA</code>, <code>MSFT</code></li>
            <li>₿ Crypto: <code>BTC</code>, <code>ETH</code>, <code>SOL</code>, <code>BNB</code></li>
            <li>🎭 Meme: <code>DOGE</code>, <code>SHIB</code>, <code>PEPE</code>, <code>FLOKI</code></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Live prices preview
    if live:
        st.markdown("### 🔴 Live Crypto Prices")
        labels = {"bitcoin": "Bitcoin", "ethereum": "Ethereum", "dogecoin": "Dogecoin",
                  "solana": "Solana", "binancecoin": "BNB"}
        cols = st.columns(len(labels))
        for i, (cid, lbl) in enumerate(labels.items()):
            if cid in live:
                p   = live[cid].get("usd", 0)
                chg = live[cid].get("usd_24h_change", 0) or 0
                p_fmt = f"${p:,.4f}" if p < 1 else f"${p:,.2f}"
                cols[i].metric(lbl, p_fmt, f"{chg:+.2f}%")


# ── SEBI / Legal Disclaimer ───────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer-box">
    <b>⚖️ IMPORTANT DISCLAIMER</b><br><br>
    The information provided in this application is for <b>educational and informational purposes only</b>
    and does not constitute financial, investment, or trading advice.
    We are <b>NOT SEBI-registered financial advisors</b>.
    All stock market, cryptocurrency, and meme coin investments involve significant risk,
    including the <b>possible loss of principal</b>.
    You are solely responsible for your own investment decisions.
    We do not guarantee the accuracy, completeness, or reliability of any data presented.
    Please conduct your own research (<b>DYOR</b>) and consult with a qualified financial
    professional before making any financial commitments.<br><br>
    <i>
    Data sources: Yahoo Finance (via yfinance) · CoinGecko Free API · Data may be delayed.
    Not suitable for live trading. FinSage is not affiliated with any exchange or regulator.
    </i>
</div>
""", unsafe_allow_html=True)
