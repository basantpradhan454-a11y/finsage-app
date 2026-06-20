"""
FinsageAI — TradingView Live Charts
Fullscreen mode + live OHLCV + candle price movement + real-time tick display
"""

import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

LOGO_URL = "https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"

POPULAR_SYMBOLS = [
    ("BTC",      "BINANCE:BTCUSDT",  "BTC-USD"),
    ("ETH",      "BINANCE:ETHUSDT",  "ETH-USD"),
    ("SOL",      "BINANCE:SOLUSDT",  "SOL-USD"),
    ("DOGE",     "BINANCE:DOGEUSDT", "DOGE-USD"),
    ("AAPL",     "NASDAQ:AAPL",      "AAPL"),
    ("TSLA",     "NASDAQ:TSLA",      "TSLA"),
    ("NVDA",     "NASDAQ:NVDA",      "NVDA"),
    ("MSFT",     "NASDAQ:MSFT",      "MSFT"),
    ("RELIANCE", "NSE:RELIANCE",     "RELIANCE.NS"),
    ("TCS",      "NSE:TCS",          "TCS.NS"),
    ("INFY",     "NSE:INFY",         "INFY.NS"),
    ("NIFTY",    "NSE:NIFTY",        "^NSEI"),
    ("BNB",      "BINANCE:BNBUSDT",  "BNB-USD"),
    ("XRP",      "BINANCE:XRPUSDT",  "XRP-USD"),
    ("PEPE",     "BINANCE:PEPEUSDT", "PEPE-USD"),
]

INTERVALS = {
    "1 Min":  "1",
    "3 Min":  "3",
    "5 Min":  "5",
    "15 Min": "15",
    "30 Min": "30",
    "1 Hour": "60",
    "4 Hour": "240",
    "1 Day":  "D",
    "1 Week": "W",
}

YF_PERIOD_MAP = {
    "1 Min":  "1d",  "3 Min":  "1d",  "5 Min":  "1d",
    "15 Min": "5d",  "30 Min": "5d",  "1 Hour": "1mo",
    "4 Hour": "3mo", "1 Day":  "1y",  "1 Week": "5y",
}
YF_INTERVAL_MAP = {
    "1 Min":  "1m",  "3 Min":  "5m",  "5 Min":  "5m",
    "15 Min": "15m", "30 Min": "30m", "1 Hour": "1h",
    "4 Hour": "1d",  "1 Day":  "1d",  "1 Week": "1wk",
}


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_ohlcv(yf_sym: str, period: str, interval: str) -> pd.DataFrame:
    try:
        df = yf.Ticker(yf_sym).history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        return df.tail(120)
    except Exception:
        return pd.DataFrame()


def _get_yf_sym(tv_sym: str) -> str:
    for label, tv, yf_sym in POPULAR_SYMBOLS:
        if tv == tv_sym or label.upper() in tv_sym.upper():
            return yf_sym
    if "BINANCE:" in tv_sym:
        base = tv_sym.replace("BINANCE:", "").replace("USDT", "").replace("USD", "")
        return f"{base}-USD"
    if "NASDAQ:" in tv_sym or "NYSE:" in tv_sym:
        return tv_sym.split(":")[1]
    if "NSE:" in tv_sym:
        return tv_sym.split(":")[1] + ".NS"
    return tv_sym.split(":")[-1] if ":" in tv_sym else tv_sym


def _fmt_price(p: float) -> str:
    if p < 0.0001:  return f"${p:.8f}"
    if p < 0.01:    return f"${p:.6f}"
    if p < 1:       return f"${p:.4f}"
    if p < 100:     return f"${p:,.4f}"
    return f"${p:,.2f}"


def render_tradingview_page():
    is_fullscreen = st.session_state.get("tv_fullscreen", False)

    # ── FULLSCREEN CSS — hides Streamlit chrome for true full-screen experience ──
    if is_fullscreen:
        st.markdown("""<style>
        /* Hide Streamlit header, footer, sidebar, deploy button */
        header[data-testid="stHeader"]          { display:none !important; }
        footer                                   { display:none !important; }
        section[data-testid="stSidebar"]         { display:none !important; }
        div[data-testid="stSidebarNav"]          { display:none !important; }
        #MainMenu                                { display:none !important; }
        div[data-testid="stDecoration"]          { display:none !important; }
        div[data-testid="stToolbar"]             { display:none !important; }
        .block-container {
            padding-top: 0.5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }
        /* Make iframe expand to near full window */
        iframe { width:100% !important; }
        </style>""", unsafe_allow_html=True)

    # ── PAGE HEADER (hide in fullscreen) ──────────────────────────────────────
    if not is_fullscreen:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#020609,#0a1628);
        border:1px solid rgba(0,212,255,0.15);border-radius:14px;
        padding:1rem 1.4rem;margin-bottom:0.8rem;">
            <div style="display:flex;align-items:center;gap:0.8rem;">
                <div>
                    <span style="font-size:1.1rem;font-weight:800;font-family:Orbitron,monospace;
                    background:linear-gradient(90deg,#00d4ff,#4a9eff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                    📈 TradingView Live Charts</span>
                    <span style="margin-left:12px;background:rgba(0,255,136,0.1);color:#00ff88;
                    padding:2px 10px;border-radius:20px;font-size:10px;font-weight:700;
                    border:1px solid rgba(0,255,136,0.2);">🔴 LIVE</span>
                    <div style="color:#8b949e;font-size:11px;margin-top:2px;">
                    Real-time candlesticks · OHLCV · Price movement · Fullscreen mode · 35+ assets
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── QUICK SYMBOL BUTTONS ──────────────────────────────────────────────────
    if not is_fullscreen:
        st.markdown("**⚡ Quick Select:**")
        q_cols = st.columns(8)
        for i, (label, tv_sym, _) in enumerate(POPULAR_SYMBOLS[:8]):
            with q_cols[i]:
                if st.button(label, key=f"tv_q_{i}", use_container_width=True):
                    st.session_state.tv_symbol = tv_sym
                    st.rerun()
        q_cols2 = st.columns(7)
        for i, (label, tv_sym, _) in enumerate(POPULAR_SYMBOLS[8:15]):
            with q_cols2[i]:
                if st.button(label, key=f"tv_q2_{i}", use_container_width=True):
                    st.session_state.tv_symbol = tv_sym
                    st.rerun()

    # ── CONTROLS ROW ──────────────────────────────────────────────────────────
    cc1, cc2, cc3, cc4, cc5 = st.columns([3, 2, 2, 1, 1])
    with cc1:
        cur_sym = st.session_state.get("tv_symbol", "BINANCE:BTCUSDT")
        custom_sym = st.text_input(
            "Symbol", value=cur_sym,
            placeholder="BINANCE:BTCUSDT / NASDAQ:AAPL / NSE:RELIANCE",
            key="tv_csym", label_visibility="collapsed"
        )
        if custom_sym != cur_sym:
            st.session_state.tv_symbol = custom_sym
    with cc2:
        interval = st.selectbox("Interval", list(INTERVALS.keys()), index=7,
                                key="tv_iv", label_visibility="collapsed")
    with cc3:
        chart_type = st.selectbox("Type",
            ["Candlestick", "Heikin Ashi", "Line", "Bar", "Area"],
            key="tv_ct", label_visibility="collapsed")
    with cc4:
        theme = st.selectbox("Theme", ["Dark", "Light"],
                             key="tv_th", label_visibility="collapsed")
    with cc5:
        fs_label = "🗗 Exit Fullscreen" if is_fullscreen else "⛶ Fullscreen"
        if st.button(fs_label, key="tv_fs_btn", use_container_width=True, type="primary"):
            st.session_state.tv_fullscreen = not is_fullscreen
            st.rerun()

    # ── INDICATORS ROW ────────────────────────────────────────────────────────
    if not is_fullscreen:
        ind_list = ["MA", "EMA", "RSI", "MACD", "BB", "Volume", "VWAP", "ATR", "StochRSI", "CCI"]
        ind_defaults = {"MA", "Volume", "EMA"}
        ind_row = st.columns(len(ind_list))
        selected_inds = []
        for i, ind in enumerate(ind_list):
            with ind_row[i]:
                if st.checkbox(ind, key=f"tv_ind_{ind}", value=(ind in ind_defaults)):
                    selected_inds.append(ind)
    else:
        selected_inds = ["Volume"]

    # ── BUILD TRADINGVIEW WIDGET ───────────────────────────────────────────────
    symbol   = st.session_state.get("tv_symbol", "BINANCE:BTCUSDT")
    iv_val   = INTERVALS.get(interval, "D")
    tv_theme = "dark" if theme == "Dark" else "light"
    chart_style = {
        "Candlestick": "1", "Heikin Ashi": "8",
        "Line": "2", "Bar": "0", "Area": "3"
    }.get(chart_type, "1")
    studies_map = {
        "MA":      '"MASimple@tv-basicstudies"',
        "EMA":     '"MAExp@tv-basicstudies"',
        "RSI":     '"RSI@tv-basicstudies"',
        "MACD":    '"MACD@tv-basicstudies"',
        "BB":      '"BB@tv-basicstudies"',
        "Volume":  '"Volume@tv-basicstudies"',
        "VWAP":    '"VWAP@tv-basicstudies"',
        "ATR":     '"ATR@tv-basicstudies"',
        "StochRSI":'"StochasticRSI@tv-basicstudies"',
        "CCI":     '"CCI@tv-basicstudies"',
    }
    studies_json = "[" + ",".join(studies_map[s] for s in selected_inds if s in studies_map) + "]"

    # Fullscreen = almost full window height
    chart_height = 920 if is_fullscreen else 580

    tv_html = f"""
    <style>
    body {{ margin:0;padding:0;background:#020609; }}
    .tv-wrap {{ border-radius:{'4px' if is_fullscreen else '12px'};overflow:hidden;
      border:1px solid rgba(0,212,255,0.12);
      box-shadow:0 0 40px rgba(0,212,255,0.05); }}
    </style>
    <div class="tv-wrap">
    <div class="tradingview-widget-container" style="height:{chart_height}px;width:100%;">
      <div class="tradingview-widget-container__widget"
           style="height:calc(100% - 32px);width:100%;"></div>
      <script type="text/javascript"
        src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
      {{
        "autosize": true,
        "symbol": "{symbol}",
        "interval": "{iv_val}",
        "timezone": "Asia/Kolkata",
        "theme": "{tv_theme}",
        "style": "{chart_style}",
        "locale": "en",
        "toolbar_bg": "#020609",
        "backgroundColor": "rgba(2,6,9,1)",
        "gridColor": "rgba(0,212,255,0.03)",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "save_image": true,
        "calendar": false,
        "hide_side_toolbar": false,
        "withdateranges": true,
        "studies": {studies_json},
        "show_popup_button": true,
        "popup_width": "1000",
        "popup_height": "650",
        "support_host": "https://www.tradingview.com"
      }}
      </script>
    </div>
    </div>
    """
    components.html(tv_html, height=chart_height + 30, scrolling=False)

    # ── FULLSCREEN: show minimal price strip only ──────────────────────────────
    if is_fullscreen:
        yf_sym  = _get_yf_sym(symbol)
        period  = YF_PERIOD_MAP.get(interval, "1y")
        yf_iv   = YF_INTERVAL_MAP.get(interval, "1d")
        df      = _fetch_ohlcv(yf_sym, period, yf_iv)
        if not df.empty:
            lat = df.iloc[-1]
            prv = df.iloc[-2] if len(df) > 1 else lat
            c   = float(lat["Close"])
            pc  = float(prv["Close"])
            chg_pct = (c - pc) / pc * 100 if pc else 0
            arrow = "▲" if c >= pc else "▼"
            col_c = "#00ff88" if c >= pc else "#ff4466"
            st.markdown(
                f"""<div style="display:flex;gap:20px;align-items:center;padding:8px 0;
                font-family:monospace;">
                <span style="font-weight:900;font-size:16px;color:#e6edf3;">{yf_sym}</span>
                <span style="font-size:22px;font-weight:900;color:{col_c};">{_fmt_price(c)}</span>
                <span style="color:{col_c};font-weight:700;">{arrow} {abs(chg_pct):.2f}%</span>
                <span style="color:#8b949e;font-size:12px;">
                  H:{_fmt_price(float(lat['High']))} &nbsp;
                  L:{_fmt_price(float(lat['Low']))} &nbsp;
                  O:{_fmt_price(float(lat['Open']))}
                </span>
                </div>""",
                unsafe_allow_html=True
            )
        st.markdown(
            '<div style="font-size:10px;color:#8b949e;margin-top:4px;">'
            '⚖️ Charts by TradingView · Educational only · Not investment advice</div>',
            unsafe_allow_html=True
        )
        return  # Don't show full panel in fullscreen

    # ══════════════════════════════════════════════════════════════════════════
    # LIVE OHLCV + CANDLE PRICE MOVEMENT PANEL
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")

    yf_sym = _get_yf_sym(symbol)
    period = YF_PERIOD_MAP.get(interval, "1y")
    yf_iv  = YF_INTERVAL_MAP.get(interval, "1d")

    with st.spinner(f"Loading OHLCV for {yf_sym}…"):
        df = _fetch_ohlcv(yf_sym, period, yf_iv)

    if df.empty:
        st.warning(f"⚠️ Could not load OHLCV data for `{yf_sym}`. Try a different symbol or timeframe.")
        return

    latest = df.iloc[-1]
    prev   = df.iloc[-2] if len(df) > 1 else df.iloc[-1]

    o  = float(latest["Open"])
    h  = float(latest["High"])
    l  = float(latest["Low"])
    c  = float(latest["Close"])
    v  = float(latest["Volume"])
    pc = float(prev["Close"])
    po = float(prev["Open"])

    chg     = c - pc
    chg_pct = (chg / pc * 100) if pc else 0
    body    = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    candle_range = h - l
    up      = c >= o
    c_color = "#00ff88" if up else "#ff4466"
    arrow   = "▲" if up else "▼"
    c_type  = "Bullish 🟢" if up else "Bearish 🔴"

    # ── BIG PRICE DISPLAY ─────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:rgba(2,6,9,0.9);border:1px solid rgba(0,212,255,0.12);
    border-radius:12px;padding:16px 20px;margin-bottom:12px;">
      <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
        <div>
          <div style="font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:2px;">{yf_sym}</div>
          <div style="font-family:Orbitron,monospace;font-size:32px;font-weight:900;color:{c_color};">
            {_fmt_price(c)}
          </div>
        </div>
        <div style="border-left:1px solid #30363d;padding-left:16px;">
          <div style="font-size:22px;font-weight:900;color:{c_color};">
            {arrow} {abs(chg_pct):.2f}%
          </div>
          <div style="font-size:13px;color:{c_color};">
            {'+' if chg >= 0 else ''}{_fmt_price(abs(chg))} vs prev close
          </div>
        </div>
        <div style="border-left:1px solid #30363d;padding-left:16px;">
          <div style="font-size:11px;color:#8b949e;">Candle Type</div>
          <div style="font-size:16px;font-weight:700;color:{c_color};">{c_type}</div>
        </div>
        <div style="border-left:1px solid #30363d;padding-left:16px;">
          <div style="font-size:11px;color:#8b949e;">Timeframe</div>
          <div style="font-size:14px;font-weight:700;color:#58a6ff;">{interval}</div>
        </div>
      </div>

      <div style="display:flex;gap:20px;margin-top:14px;flex-wrap:wrap;">
        <div style="background:rgba(0,212,255,0.04);border:1px solid rgba(0,212,255,0.1);
        border-radius:8px;padding:10px 14px;min-width:90px;text-align:center;">
          <div style="font-size:10px;color:#8b949e;text-transform:uppercase;">OPEN</div>
          <div style="font-family:monospace;font-size:14px;font-weight:700;color:#e6edf3;">{_fmt_price(o)}</div>
        </div>
        <div style="background:rgba(0,255,136,0.04);border:1px solid rgba(0,255,136,0.15);
        border-radius:8px;padding:10px 14px;min-width:90px;text-align:center;">
          <div style="font-size:10px;color:#8b949e;text-transform:uppercase;">HIGH</div>
          <div style="font-family:monospace;font-size:14px;font-weight:700;color:#00ff88;">{_fmt_price(h)}</div>
        </div>
        <div style="background:rgba(255,68,102,0.04);border:1px solid rgba(255,68,102,0.15);
        border-radius:8px;padding:10px 14px;min-width:90px;text-align:center;">
          <div style="font-size:10px;color:#8b949e;text-transform:uppercase;">LOW</div>
          <div style="font-family:monospace;font-size:14px;font-weight:700;color:#ff4466;">{_fmt_price(l)}</div>
        </div>
        <div style="background:rgba(88,166,255,0.04);border:1px solid rgba(88,166,255,0.15);
        border-radius:8px;padding:10px 14px;min-width:90px;text-align:center;">
          <div style="font-size:10px;color:#8b949e;text-transform:uppercase;">CLOSE</div>
          <div style="font-family:monospace;font-size:14px;font-weight:700;color:#58a6ff;">{_fmt_price(c)}</div>
        </div>
        <div style="background:rgba(163,113,247,0.04);border:1px solid rgba(163,113,247,0.15);
        border-radius:8px;padding:10px 14px;min-width:90px;text-align:center;">
          <div style="font-size:10px;color:#8b949e;text-transform:uppercase;">VOLUME</div>
          <div style="font-family:monospace;font-size:14px;font-weight:700;color:#a371f7;">
            {"%.2fB" % (v/1e9) if v>1e9 else "%.2fM" % (v/1e6) if v>1e6 else "%.1fK" % (v/1e3)}
          </div>
        </div>
        <div style="background:rgba(210,153,34,0.04);border:1px solid rgba(210,153,34,0.15);
        border-radius:8px;padding:10px 14px;min-width:90px;text-align:center;">
          <div style="font-size:10px;color:#8b949e;text-transform:uppercase;">PREV CLOSE</div>
          <div style="font-family:monospace;font-size:14px;font-weight:700;color:#d29922;">{_fmt_price(pc)}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CANDLE ANATOMY ────────────────────────────────────────────────────────
    st.markdown("**🕯️ Candle Anatomy & Price Movement Breakdown**")
    an1, an2, an3, an4, an5 = st.columns(5)
    an1.metric("📏 Full Range",   _fmt_price(candle_range),  help="High − Low")
    an2.metric("🟦 Body Size",    _fmt_price(body),          help="|Close − Open|")
    an3.metric("⬆️ Upper Wick",   _fmt_price(upper_wick),   help="High − max(O,C)")
    an4.metric("⬇️ Lower Wick",   _fmt_price(lower_wick),   help="min(O,C) − Low")
    an5.metric("💸 Price Move",
               f"{'+'if chg>=0 else ''}{_fmt_price(abs(chg))}",
               delta=f"{chg_pct:+.2f}%")

    # Candle structure bar
    if candle_range > 0:
        body_pct  = round(body / candle_range * 100, 1)
        upper_pct = round(upper_wick / candle_range * 100, 1)
        lower_pct = round(lower_wick / candle_range * 100, 1)
        strength  = "Strong" if body_pct > 60 else "Moderate" if body_pct > 30 else "Weak/Indecision"
        candle_interp = (
            "🟢 Strong Bullish Momentum — buyers in full control"
            if up and body_pct > 60 else
            "🔴 Strong Bearish Momentum — sellers dominating"
            if not up and body_pct > 60 else
            "🟢 Bullish Pin Bar — rejection of lower prices, reversal possible"
            if up and lower_pct > 50 else
            "🔴 Bearish Shooting Star — rejection at highs, reversal possible"
            if not up and upper_pct > 50 else
            "⚪ Doji / Indecision — market balanced, wait for next candle"
            if body_pct < 15 else
            f"{'🟢' if up else '🔴'} {strength} {'bullish' if up else 'bearish'} candle"
        )
        st.markdown(f"""
        <div style="background:rgba(13,17,23,0.8);border:1px solid #21262d;border-radius:10px;padding:14px 18px;margin-bottom:10px;">
          <div style="font-size:12px;color:#8b949e;margin-bottom:8px;">
            CANDLE STRUCTURE (% of full range) &nbsp;|&nbsp;
            <span style="color:{'#00ff88' if up else '#ff4466'};font-weight:700;">{candle_interp}</span>
          </div>
          <div style="display:flex;gap:0;height:20px;border-radius:4px;overflow:hidden;margin-bottom:6px;">
            <div style="width:{upper_pct}%;background:#d29922;opacity:0.7;" title="Upper wick {upper_pct}%"></div>
            <div style="width:{body_pct}%;background:{'#00ff88' if up else '#ff4466'};" title="Body {body_pct}%"></div>
            <div style="width:{lower_pct}%;background:#58a6ff;opacity:0.7;" title="Lower wick {lower_pct}%"></div>
          </div>
          <div style="display:flex;gap:20px;font-size:11px;">
            <span style="color:#d29922;">🟡 Upper Wick {upper_pct}%</span>
            <span style="color:{'#00ff88' if up else '#ff4466'};">{'🟢' if up else '🔴'} Body {body_pct}%</span>
            <span style="color:#58a6ff;">🔵 Lower Wick {lower_pct}%</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── PRICE MOVEMENT MINI CHART (last 30 candles) ───────────────────────────
    st.markdown("**📈 Price Movement — Last 30 Candles**")
    plot_df = df.tail(30).copy()
    if not plot_df.empty:
        fig_c = go.Figure()
        fig_c.add_trace(go.Candlestick(
            x=plot_df.index,
            open=plot_df["Open"], high=plot_df["High"],
            low=plot_df["Low"],   close=plot_df["Close"],
            increasing_line_color="#00ff88", decreasing_line_color="#ff4466",
            increasing_fillcolor="rgba(0,255,136,0.7)",
            decreasing_fillcolor="rgba(255,68,102,0.7)",
            name="Price",
        ))
        # Highlight last candle
        last_row = plot_df.iloc[-1]
        fig_c.add_trace(go.Scatter(
            x=[plot_df.index[-1]],
            y=[float(last_row["Close"])],
            mode="markers+text",
            marker=dict(size=10, color=c_color, symbol="circle"),
            text=[_fmt_price(float(last_row["Close"]))],
            textposition="top center",
            textfont=dict(color=c_color, size=11),
            showlegend=False,
            name="Latest"
        ))
        fig_c.update_layout(
            plot_bgcolor="#020609", paper_bgcolor="#020609",
            font=dict(color="#c9d1d9", family="monospace"),
            xaxis=dict(gridcolor="#0d1117", showgrid=True, rangeslider_visible=False),
            yaxis=dict(gridcolor="#0d1117", showgrid=True),
            height=280, margin=dict(l=0, r=0, t=10, b=0),
            hovermode="x unified",
        )
        st.plotly_chart(fig_c, use_container_width=True)

    # ── RECENT CANDLES TABLE ──────────────────────────────────────────────────
    st.markdown("**📋 Recent Candles — Price Movement Table (Last 15)**")
    recent = df.tail(15).copy()
    if not recent.empty:
        time_fmt = "%m/%d %H:%M" if hasattr(recent.index[0], 'hour') else "%Y-%m-%d"
        recent_display = pd.DataFrame({
            "Time":   recent.index.strftime(time_fmt),
            "Open":   recent["Open"].round(4),
            "High":   recent["High"].round(4),
            "Low":    recent["Low"].round(4),
            "Close":  recent["Close"].round(4),
            "Move $": (recent["Close"] - recent["Open"]).round(4),
            "Move %": ((recent["Close"] - recent["Open"]) / recent["Open"] * 100).round(2),
            "Range":  (recent["High"] - recent["Low"]).round(4),
            "Volume": recent["Volume"].apply(
                lambda x: f"{x/1e9:.2f}B" if x > 1e9 else f"{x/1e6:.2f}M" if x > 1e6 else f"{x/1e3:.1f}K"
            ),
            "Signal": ["🟢 Bull" if c >= o else "🔴 Bear"
                       for c, o in zip(recent["Close"], recent["Open"])],
        }).reset_index(drop=True)

        def _style_signal(v):
            return "color:#00ff88;font-weight:700" if "Bull" in str(v) else "color:#ff4466;font-weight:700"
        def _style_move(v):
            try:
                return "color:#00ff88" if float(v) > 0 else "color:#ff4466" if float(v) < 0 else ""
            except Exception:
                return ""

        try:
            styled = (recent_display.style
                      .map(_style_signal, subset=["Signal"])
                      .map(_style_move,   subset=["Move $", "Move %"]))
        except AttributeError:
            styled = (recent_display.style
                      .applymap(_style_signal, subset=["Signal"])
                      .applymap(_style_move,   subset=["Move $", "Move %"]))

        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Move %": st.column_config.NumberColumn(format="%.2f%%"),
            }
        )

    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:6px 12px;margin-top:8px;font-size:11px;color:#8b949e;">
    ⚖️ Charts powered by TradingView · OHLCV via Yahoo Finance ·
    For educational purposes only · Not investment advice
    </div>
    """, unsafe_allow_html=True)
