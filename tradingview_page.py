"""
STOX AI — TradingView Live Charts
Embed TradingView widgets directly in the app.
"""

import streamlit as st
import streamlit.components.v1 as components

LOGO_URL = "https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"

POPULAR_SYMBOLS = [
    # Crypto
    ("BTC/USDT", "BINANCE:BTCUSDT"), ("ETH/USDT", "BINANCE:ETHUSDT"),
    ("SOL/USDT", "BINANCE:SOLUSDT"), ("BNB/USDT", "BINANCE:BNBUSDT"),
    ("DOGE/USDT","BINANCE:DOGEUSDT"),
    # US Stocks
    ("AAPL",    "NASDAQ:AAPL"),  ("TSLA",    "NASDAQ:TSLA"),
    ("NVDA",    "NASDAQ:NVDA"),  ("MSFT",    "NASDAQ:MSFT"),
    ("GOOGL",   "NASDAQ:GOOGL"),
    # India
    ("RELIANCE","NSE:RELIANCE"), ("TCS",     "NSE:TCS"),
    ("INFY",    "NSE:INFY"),     ("HDFCBANK","NSE:HDFCBANK"),
    ("NIFTY 50","NSE:NIFTY"),
]

INTERVALS = {
    "1 Min":   "1",   "5 Min":  "5",   "15 Min": "15",
    "30 Min":  "30",  "1 Hour": "60",  "4 Hour": "240",
    "1 Day":   "D",   "1 Week": "W",   "1 Month":"M",
}

THEMES = {"Dark (Cyberpunk)": "dark", "Light": "light"}


def render_tradingview_page():
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.95),rgba(0,15,30,0.9));
    border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:1.2rem 1.5rem;
    margin-bottom:1rem;box-shadow:0 0 30px rgba(0,212,255,0.06);">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;width:44px;border-radius:10px;
            box-shadow:0 0 15px rgba(0,212,255,0.3);">
            <div>
                <div style="font-size:1.15rem;font-weight:800;color:#00d4ff;
                font-family:Orbitron,monospace;letter-spacing:0.05em;">
                📈 TradingView Live Charts
                </div>
                <div style="color:#4a9eff;font-size:0.75rem;">
                Professional charts powered by TradingView — Real-time data
                </div>
            </div>
            <span style="margin-left:auto;background:rgba(0,212,255,0.1);color:#00d4ff;
            padding:0.2rem 0.7rem;border-radius:20px;font-size:0.68rem;font-weight:700;
            border:1px solid rgba(0,212,255,0.3);">🔴 LIVE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Quick symbol buttons ────────────────────────────────────────────────────
    st.markdown("**⚡ Quick Select:**")
    cols = st.columns(5)
    for i, (label, sym) in enumerate(POPULAR_SYMBOLS[:10]):
        with cols[i % 5]:
            if st.button(label, key=f"tv_quick_{i}", use_container_width=True):
                st.session_state.tv_symbol = sym
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Controls ────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
    with c1:
        custom_sym = st.text_input(
            "Symbol",
            value=st.session_state.get("tv_symbol", "BINANCE:BTCUSDT"),
            placeholder="e.g. BINANCE:BTCUSDT, NASDAQ:AAPL, NSE:RELIANCE",
            key="tv_custom_symbol",
            label_visibility="collapsed"
        )
        if custom_sym != st.session_state.get("tv_symbol", "BINANCE:BTCUSDT"):
            st.session_state.tv_symbol = custom_sym

    with c2:
        interval = st.selectbox(
            "Interval", list(INTERVALS.keys()),
            index=6,  # 1 Day default
            key="tv_interval",
            label_visibility="collapsed"
        )

    with c3:
        chart_type = st.selectbox(
            "Chart Type",
            ["Candlestick", "Line", "Bar", "Area", "Heikin Ashi"],
            key="tv_chart_type",
            label_visibility="collapsed"
        )

    with c4:
        theme = st.selectbox("Theme", list(THEMES.keys()), key="tv_theme",
                             label_visibility="collapsed")

    # ── Indicator pills ─────────────────────────────────────────────────────────
    st.markdown("**📊 Indicators:**")
    ind_cols = st.columns(8)
    indicators = ["MA", "EMA", "RSI", "MACD", "BB", "Volume", "VWAP", "ATR"]
    selected_inds = []
    for i, ind in enumerate(indicators):
        with ind_cols[i]:
            if st.checkbox(ind, key=f"ind_{ind}", value=(ind in ["MA", "Volume"])):
                selected_inds.append(ind)

    # ── Build TradingView widget ────────────────────────────────────────────────
    symbol  = st.session_state.get("tv_symbol", "BINANCE:BTCUSDT")
    iv_val  = INTERVALS.get(interval, "D")
    tv_theme = THEMES.get(theme, "dark")

    chart_type_map = {
        "Candlestick": "1", "Line": "2", "Bar": "0",
        "Area": "3", "Heikin Ashi": "8"
    }
    chart_style = chart_type_map.get(chart_type, "1")

    studies = []
    if "MA"     in selected_inds: studies.append('"MASimple@tv-basicstudies"')
    if "EMA"    in selected_inds: studies.append('"MAExp@tv-basicstudies"')
    if "RSI"    in selected_inds: studies.append('"RSI@tv-basicstudies"')
    if "MACD"   in selected_inds: studies.append('"MACD@tv-basicstudies"')
    if "BB"     in selected_inds: studies.append('"BB@tv-basicstudies"')
    if "Volume" in selected_inds: studies.append('"Volume@tv-basicstudies"')
    if "VWAP"   in selected_inds: studies.append('"VWAP@tv-basicstudies"')
    if "ATR"    in selected_inds: studies.append('"ATR@tv-basicstudies"')

    studies_json = "[" + ",".join(studies) + "]"

    tv_html = f"""
    <div id="tradingview_chart" style="border-radius:12px;overflow:hidden;
    border:1px solid rgba(0,212,255,0.15);box-shadow:0 0 30px rgba(0,212,255,0.06);">
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container">
      <div id="tradingview_main"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "autosize": true,
        "height": 580,
        "symbol": "{symbol}",
        "interval": "{iv_val}",
        "timezone": "Asia/Kolkata",
        "theme": "{tv_theme}",
        "style": "{chart_style}",
        "locale": "en",
        "toolbar_bg": "#020609",
        "enable_publishing": false,
        "hide_top_toolbar": false,
        "hide_legend": false,
        "save_image": true,
        "container_id": "tradingview_main",
        "studies": {studies_json},
        "backgroundColor": "rgba(2, 6, 9, 1)",
        "gridColor": "rgba(0, 212, 255, 0.05)",
        "show_popup_button": true,
        "popup_width": "1000",
        "popup_height": "650"
      }});
      </script>
    </div>
    <!-- TradingView Widget END -->
    </div>
    """
    components.html(tv_html, height=600, scrolling=False)

    # ── Candlestick Pattern Guide ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🕯️ Candlestick Pattern Quick Reference")

    patterns = [
        ("🟢 Hammer",        "Bullish reversal after downtrend. Small body, long lower shadow.", "Bullish"),
        ("🟢 Engulfing",     "Large green candle fully engulfs previous red candle.", "Bullish"),
        ("🟢 Morning Star",  "3-candle pattern: red → small doji → large green.", "Bullish"),
        ("🟢 Doji",          "Open = Close. Market indecision — watch for breakout direction.", "Neutral"),
        ("🔴 Shooting Star", "Bearish reversal after uptrend. Small body, long upper shadow.", "Bearish"),
        ("🔴 Engulfing",     "Large red candle fully engulfs previous green candle.", "Bearish"),
        ("🔴 Evening Star",  "3-candle pattern: green → small doji → large red.", "Bearish"),
        ("🔴 Hanging Man",   "Small body at top, long lower shadow after uptrend.", "Bearish"),
    ]

    pc = st.columns(2)
    for i, (name, desc, signal) in enumerate(patterns):
        color = "#00ff88" if signal == "Bullish" else ("#ff4466" if signal == "Bearish" else "#f0c040")
        with pc[i % 2]:
            st.markdown(f"""
            <div style="background:rgba(0,15,30,0.8);border:1px solid rgba(0,212,255,0.1);
            border-left:3px solid {color};border-radius:8px;padding:0.7rem 0.9rem;
            margin-bottom:0.6rem;">
                <div style="font-weight:700;color:{color};font-size:0.85rem;">{name}</div>
                <div style="color:#8b949e;font-size:0.78rem;margin-top:0.2rem;">{desc}</div>
                <span style="background:rgba(0,0,0,0.3);color:{color};font-size:0.68rem;
                padding:0.1rem 0.4rem;border-radius:10px;border:1px solid {color}33;
                margin-top:0.3rem;display:inline-block;">{signal}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.6rem 1rem;margin-top:0.5rem;font-size:0.75rem;color:#8b949e;">
    ⚖️ <b style="color:#d29922;">Disclaimer:</b> TradingView charts are for educational purposes.
    Candlestick patterns are technical indicators, not guaranteed signals.
    Not SEBI investment advice. Always use proper risk management.
    </div>
    """, unsafe_allow_html=True)
