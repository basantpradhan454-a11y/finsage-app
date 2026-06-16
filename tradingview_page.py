"""
FinsageAI — TradingView Live Charts
Fullscreen mode + live OHLCV price display + candlestick guide
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
    "1 Min": "1",  "3 Min": "3",   "5 Min": "5",
    "15 Min":"15", "30 Min":"30",  "1 Hour":"60",
    "4 Hour":"240","1 Day": "D",   "1 Week":"W",
}

YF_PERIOD_MAP = {
    "1 Min":"1d",  "3 Min":"1d",   "5 Min":"1d",
    "15 Min":"5d", "30 Min":"5d",  "1 Hour":"1mo",
    "4 Hour":"3mo","1 Day":"1y",   "1 Week":"5y",
}

YF_INTERVAL_MAP = {
    "1 Min":"1m",  "3 Min":"5m",   "5 Min":"5m",
    "15 Min":"15m","30 Min":"30m", "1 Hour":"1h",
    "4 Hour":"1d", "1 Day":"1d",   "1 Week":"1wk",
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
    """Map TradingView symbol → yfinance symbol."""
    for label, tv, yf_sym in POPULAR_SYMBOLS:
        if tv == tv_sym or label.upper() in tv_sym.upper():
            return yf_sym
    # Heuristic: BINANCE:XYZUSDT → XYZ-USD
    if "BINANCE:" in tv_sym:
        base = tv_sym.replace("BINANCE:","").replace("USDT","").replace("USD","")
        return f"{base}-USD"
    if "NASDAQ:" in tv_sym or "NYSE:" in tv_sym:
        return tv_sym.split(":")[1]
    if "NSE:" in tv_sym:
        return tv_sym.split(":")[1] + ".NS"
    return tv_sym.split(":")[-1] if ":" in tv_sym else tv_sym


def render_tradingview_page():
    # ── Fullscreen mode ──────────────────────────────────────────────────────
    is_fullscreen = st.session_state.get("tv_fullscreen", False)

    if not is_fullscreen:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(2,6,9,0.95),rgba(0,15,30,0.9));
        border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:1.1rem 1.4rem;
        margin-bottom:1rem;box-shadow:0 0 30px rgba(0,212,255,0.06);">
            <div style="display:flex;align-items:center;gap:0.8rem;">
                <img src="{LOGO_URL}" style="height:42px;border-radius:10px;
                box-shadow:0 0 15px rgba(0,212,255,0.3);">
                <div>
                    <div style="font-size:1.05rem;font-weight:800;color:#00d4ff;
                    font-family:Orbitron,monospace;letter-spacing:0.05em;">
                    📈 TradingView Live Charts</div>
                    <div style="color:#4a9eff;font-size:0.72rem;">
                    Real-time candlesticks · OHLCV · Fullscreen · 35+ assets
                    </div>
                </div>
                <span style="margin-left:auto;background:rgba(255,68,102,0.15);
                color:#ff4466;padding:0.2rem 0.7rem;border-radius:20px;
                font-size:0.65rem;font-weight:700;border:1px solid rgba(255,68,102,0.3);
                animation:pulse 1s infinite;">🔴 LIVE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Controls ──────────────────────────────────────────────────────────────
    if not is_fullscreen:
        # Quick symbol buttons — row 1
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

    # ── Main controls row ──────────────────────────────────────────────────────
    if is_fullscreen:
        cc1, cc2, cc3, cc4, cc5 = st.columns([3,2,2,1,1])
    else:
        cc1, cc2, cc3, cc4, cc5 = st.columns([3,2,2,1,1])

    with cc1:
        cur_sym = st.session_state.get("tv_symbol","BINANCE:BTCUSDT")
        custom_sym = st.text_input("Symbol", value=cur_sym,
            placeholder="BINANCE:BTCUSDT / NASDAQ:AAPL / NSE:RELIANCE",
            key="tv_csym", label_visibility="collapsed")
        if custom_sym != cur_sym:
            st.session_state.tv_symbol = custom_sym

    with cc2:
        interval = st.selectbox("Interval", list(INTERVALS.keys()),
            index=7, key="tv_iv", label_visibility="collapsed")

    with cc3:
        chart_type = st.selectbox("Type",
            ["Candlestick","Heikin Ashi","Line","Bar","Area"],
            key="tv_ct", label_visibility="collapsed")

    with cc4:
        theme = st.selectbox("Theme", ["Dark","Light"],
            key="tv_th", label_visibility="collapsed")

    with cc5:
        fs_label = "🗗 Exit" if is_fullscreen else "⛶ Full"
        if st.button(fs_label, key="tv_fs_btn", use_container_width=True, type="primary"):
            st.session_state.tv_fullscreen = not is_fullscreen
            st.rerun()

    # ── Indicators ────────────────────────────────────────────────────────────
    if not is_fullscreen:
        ind_list   = ["MA","EMA","RSI","MACD","BB","Volume","VWAP","ATR","StochRSI","CCI"]
        ind_defaults = {"MA","Volume","EMA"}
        ind_row    = st.columns(len(ind_list))
        selected_inds = []
        for i, ind in enumerate(ind_list):
            with ind_row[i]:
                if st.checkbox(ind, key=f"tv_ind_{ind}", value=(ind in ind_defaults)):
                    selected_inds.append(ind)
    else:
        selected_inds = ["Volume"]

    # ── Build TradingView widget ───────────────────────────────────────────────
    symbol      = st.session_state.get("tv_symbol","BINANCE:BTCUSDT")
    iv_val      = INTERVALS.get(interval,"D")
    tv_theme    = "dark" if theme == "Dark" else "light"
    chart_style = {"Candlestick":"1","Heikin Ashi":"8","Line":"2",
                   "Bar":"0","Area":"3"}.get(chart_type,"1")

    studies_map = {
        "MA":       '"MASimple@tv-basicstudies"',
        "EMA":      '"MAExp@tv-basicstudies"',
        "RSI":      '"RSI@tv-basicstudies"',
        "MACD":     '"MACD@tv-basicstudies"',
        "BB":       '"BB@tv-basicstudies"',
        "Volume":   '"Volume@tv-basicstudies"',
        "VWAP":     '"VWAP@tv-basicstudies"',
        "ATR":      '"ATR@tv-basicstudies"',
        "StochRSI": '"StochasticRSI@tv-basicstudies"',
        "CCI":      '"CCI@tv-basicstudies"',
    }
    studies_json = "[" + ",".join(studies_map[s] for s in selected_inds if s in studies_map) + "]"

    chart_height = 700 if is_fullscreen else 580

    tv_html = f"""<!DOCTYPE html><html><head>
    <style>
      body {{margin:0;padding:0;background:#020609;}}
      #tv_wrap {{border-radius:12px;overflow:hidden;
                border:1px solid rgba(0,212,255,0.15);
                box-shadow:0 0 30px rgba(0,212,255,0.08);}}
    </style></head><body>
    <div id="tv_wrap">
    <div class="tradingview-widget-container" style="height:{chart_height}px;">
      <div id="tv_main" style="height:{chart_height}px;"></div>
      <script src="https://s3.tradingview.com/tv.js"></script>
      <script>
      new TradingView.widget({{
        "autosize": true,
        "height": {chart_height},
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
        "allow_symbol_change": true,
        "container_id": "tv_main",
        "studies": {studies_json},
        "backgroundColor": "rgba(2,6,9,1)",
        "gridColor": "rgba(0,212,255,0.04)",
        "show_popup_button": true,
        "popup_width": "1200",
        "popup_height": "800",
        "withdateranges": true,
        "details": true,
        "hotlist": false,
        "calendar": false
      }});
      </script>
    </div></div></body></html>"""

    components.html(tv_html, height=chart_height + 20, scrolling=False)

    # ── LIVE OHLCV Price Panel ─────────────────────────────────────────────────
    if not is_fullscreen:
        st.markdown("---")
        st.markdown("#### 📊 Live OHLCV + Price Movement")

        yf_sym  = _get_yf_sym(symbol)
        period  = YF_PERIOD_MAP.get(interval, "1y")
        yf_iv   = YF_INTERVAL_MAP.get(interval, "1d")

        with st.spinner(f"Loading OHLCV for {yf_sym}..."):
            df = _fetch_ohlcv(yf_sym, period, yf_iv)

        if not df.empty:
            latest = df.iloc[-1]
            prev   = df.iloc[-2] if len(df) > 1 else df.iloc[-1]

            o  = float(latest["Open"])
            h  = float(latest["High"])
            l  = float(latest["Low"])
            c  = float(latest["Close"])
            v  = float(latest["Volume"])
            pc = float(prev["Close"])

            chg    = c - pc
            chg_pct= (chg/pc*100) if pc else 0
            body   = abs(c - o)
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - l
            candle_range = h - l

            up      = c >= o
            c_color = "#00ff88" if up else "#ff4466"
            d_arrow = "▲" if up else "▼"
            c_type  = "Bullish 🟢" if up else "Bearish 🔴"

            # Price display
            if c < 0.01:      p_fmt = f"${c:.8f}"
            elif c < 1:       p_fmt = f"${c:.6f}"
            elif c < 100:     p_fmt = f"${c:.4f}"
            else:             p_fmt = f"${c:,.2f}"

            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(0,20,40,0.95),rgba(5,0,30,0.9));
            border:2px solid {c_color}33;border-radius:14px;padding:1.1rem 1.4rem;margin-bottom:0.8rem;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.8rem;">
                <div>
                  <span style="font-size:0.75rem;color:#8b949e;font-family:Orbitron,monospace;">{yf_sym}</span>
                  &nbsp;&nbsp;
                  <span style="font-size:1.8rem;font-weight:900;color:{c_color};
                  font-family:Orbitron,monospace;">{p_fmt}</span>
                  &nbsp;
                  <span style="font-size:1rem;font-weight:700;color:{c_color};">
                  {d_arrow} {abs(chg_pct):.2f}%</span>
                </div>
                <div style="text-align:right;">
                  <div style="font-size:0.75rem;color:#8b949e;">Candle Type</div>
                  <div style="font-size:1rem;font-weight:700;color:{c_color};">{c_type}</div>
                </div>
              </div>
              <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.7rem;">
                <div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:0.5rem 0.7rem;text-align:center;">
                  <div style="color:#8b949e;font-size:0.65rem;font-weight:700;">OPEN</div>
                  <div style="color:#4a9eff;font-weight:800;font-family:monospace;">
                  {"${:,.6f}".format(o) if o<1 else "${:,.2f}".format(o)}</div>
                </div>
                <div style="background:rgba(0,255,136,0.08);border-radius:8px;padding:0.5rem 0.7rem;text-align:center;border:1px solid rgba(0,255,136,0.2);">
                  <div style="color:#8b949e;font-size:0.65rem;font-weight:700;">HIGH</div>
                  <div style="color:#00ff88;font-weight:800;font-family:monospace;">
                  {"${:,.6f}".format(h) if h<1 else "${:,.2f}".format(h)}</div>
                </div>
                <div style="background:rgba(255,68,102,0.08);border-radius:8px;padding:0.5rem 0.7rem;text-align:center;border:1px solid rgba(255,68,102,0.2);">
                  <div style="color:#8b949e;font-size:0.65rem;font-weight:700;">LOW</div>
                  <div style="color:#ff4466;font-weight:800;font-family:monospace;">
                  {"${:,.6f}".format(l) if l<1 else "${:,.2f}".format(l)}</div>
                </div>
                <div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:0.5rem 0.7rem;text-align:center;">
                  <div style="color:#8b949e;font-size:0.65rem;font-weight:700;">CLOSE</div>
                  <div style="color:{c_color};font-weight:800;font-family:monospace;">
                  {"${:,.6f}".format(c) if c<1 else "${:,.2f}".format(c)}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Candle Anatomy Panel ───────────────────────────────────────────
            st.markdown("**🕯️ Candle Anatomy — Current Candle**")
            an1, an2, an3, an4, an5 = st.columns(5)
            an1.metric("📏 Candle Range",
                       f"${candle_range:.4f}" if candle_range < 10 else f"${candle_range:,.2f}",
                       help="High − Low (full candle range)")
            an2.metric("🟦 Body Size",
                       f"${body:.4f}" if body < 10 else f"${body:,.2f}",
                       help="|Close − Open| (real body)")
            an3.metric("⬆️ Upper Wick",
                       f"${upper_wick:.4f}" if upper_wick < 10 else f"${upper_wick:,.2f}",
                       help="High − max(Open,Close)")
            an4.metric("⬇️ Lower Wick",
                       f"${lower_wick:.4f}" if lower_wick < 10 else f"${lower_wick:,.2f}",
                       help="min(Open,Close) − Low")
            an5.metric("📦 Volume",
                       f"{v/1e9:.2f}B" if v>1e9 else f"{v/1e6:.2f}M" if v>1e6 else f"{v/1e3:.1f}K",
                       delta=f"{chg:+.4f}" if c<10 else f"${chg:+,.2f}")

            # ── Body/Wick ratio bar ────────────────────────────────────────────
            if candle_range > 0:
                body_pct  = round(body / candle_range * 100, 1)
                upper_pct = round(upper_wick / candle_range * 100, 1)
                lower_pct = round(lower_wick / candle_range * 100, 1)

                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.3);border-radius:10px;
                padding:0.8rem 1rem;margin-bottom:0.5rem;">
                  <div style="color:#8b949e;font-size:0.72rem;margin-bottom:0.5rem;
                  font-weight:700;">CANDLE STRUCTURE (% of full range)</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;">
                    <div style="text-align:center;">
                      <div style="background:#ff8c42;height:8px;border-radius:4px;
                      width:{upper_pct}%;margin:0 auto;"></div>
                      <div style="color:#ff8c42;font-size:0.7rem;margin-top:0.2rem;">
                      Upper Wick {upper_pct}%</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="background:{c_color};height:8px;border-radius:4px;
                      width:{body_pct}%;margin:0 auto;"></div>
                      <div style="color:{c_color};font-size:0.7rem;margin-top:0.2rem;">
                      Body {body_pct}%</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="background:#4a9eff;height:8px;border-radius:4px;
                      width:{lower_pct}%;margin:0 auto;"></div>
                      <div style="color:#4a9eff;font-size:0.7rem;margin-top:0.2rem;">
                      Lower Wick {lower_pct}%</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            # ── Recent candles mini-table ──────────────────────────────────────
            st.markdown("**📋 Recent Candles (Last 10)**")
            recent = df.tail(10).copy()
            recent_display = pd.DataFrame({
                "Time":   recent.index.strftime("%m/%d %H:%M") if hasattr(recent.index[0],'hour') else recent.index.strftime("%Y-%m-%d"),
                "Open":   recent["Open"].round(4),
                "High":   recent["High"].round(4),
                "Low":    recent["Low"].round(4),
                "Close":  recent["Close"].round(4),
                "Change": (recent["Close"] - recent["Open"]).round(4),
                "Chg%":   ((recent["Close"]-recent["Open"])/recent["Open"]*100).round(2),
                "Volume": recent["Volume"].apply(lambda x:
                    f"{x/1e9:.2f}B" if x>1e9 else f"{x/1e6:.2f}M" if x>1e6 else f"{x/1e3:.1f}K"),
                "Type":   ["🟢 Bull" if c>=o else "🔴 Bear"
                           for c,o in zip(recent["Close"],recent["Open"])],
            }).reset_index(drop=True)

            def _style_type(v):
                return "color:#00ff88;font-weight:700" if "Bull" in str(v) else "color:#ff4466;font-weight:700"
            def _style_chg(v):
                return "color:#00ff88" if v>0 else "color:#ff4466" if v<0 else ""

            try:
                styled = recent_display.style\
                    .map(_style_type, subset=["Type"])\
                    .map(_style_chg,  subset=["Change","Chg%"])
            except AttributeError:
                styled = recent_display.style\
                    .applymap(_style_type, subset=["Type"])\
                    .applymap(_style_chg,  subset=["Change","Chg%"])

            st.dataframe(styled, use_container_width=True, hide_index=True,
                column_config={
                    "Chg%": st.column_config.NumberColumn(format="%.2f%%"),
                })

            # ── Mini price chart ───────────────────────────────────────────────
            st.markdown("**📈 Price Movement — Last 30 Candles**")
            plot_df = df.tail(30)
            fig = go.Figure()
            colors = ["rgba(0,255,136,0.8)" if c>=o else "rgba(255,68,102,0.8)"
                      for c,o in zip(plot_df["Close"], plot_df["Open"])]
            fig.add_trace(go.Candlestick(
                x=plot_df.index,
                open=plot_df["Open"], high=plot_df["High"],
                low=plot_df["Low"],   close=plot_df["Close"],
                name=yf_sym,
                increasing=dict(line=dict(color="#00ff88",width=1.5),
                                fillcolor="rgba(0,255,136,0.2)"),
                decreasing=dict(line=dict(color="#ff4466",width=1.5),
                                fillcolor="rgba(255,68,102,0.2)"),
            ))
            # Add price labels for last 5 candles
            for i, row in plot_df.tail(5).iterrows():
                fig.add_annotation(
                    x=i, y=float(row["High"]),
                    text=f"${float(row['Close']):.2f}" if float(row['Close'])>=1 else f"${float(row['Close']):.5f}",
                    showarrow=False,
                    font=dict(size=9, color="#f0c040"),
                    yshift=8,
                )
            fig.update_layout(
                plot_bgcolor="#020609", paper_bgcolor="#020609",
                font=dict(color="#c9d1d9", family="monospace", size=10),
                xaxis=dict(gridcolor="#0d1117", rangeslider_visible=False,
                           showticklabels=True),
                yaxis=dict(gridcolor="#0d1117", title="Price ($)"),
                height=300, margin=dict(l=0,r=0,t=10,b=0),
                hovermode="x unified",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info(f"Could not fetch OHLCV for `{yf_sym}` — chart still works above ↑")

        # ── Candlestick Pattern Guide ──────────────────────────────────────────
        st.markdown("---")
        with st.expander("🕯️ Candlestick Pattern Reference Guide", expanded=False):
            patterns = [
                ("🟢 Hammer",         "Bullish reversal after downtrend. Small body, long lower wick (>2×body).", "Bullish",  "Strong"),
                ("🟢 Bullish Engulf", "Large green candle fully engulfs previous red candle.", "Bullish",  "Strong"),
                ("🟢 Morning Star",   "3-candle: red → small doji → large green (reversal)", "Bullish",  "Very Strong"),
                ("🟢 Doji (bottom)",  "Open≈Close. Indecision at bottom → possible reversal.", "Neutral",  "Medium"),
                ("🟢 Piercing Line",  "Green candle opens below prev low, closes above midpoint.", "Bullish", "Medium"),
                ("🔴 Shooting Star",  "Bearish reversal after uptrend. Small body, long upper wick.", "Bearish", "Strong"),
                ("🔴 Bearish Engulf", "Large red candle fully engulfs previous green candle.", "Bearish",  "Strong"),
                ("🔴 Evening Star",   "3-candle: green → small doji → large red (reversal)", "Bearish",  "Very Strong"),
                ("🔴 Hanging Man",    "Small body at top after uptrend. Long lower wick = warning.", "Bearish", "Medium"),
                ("🔴 Dark Cloud",     "Red candle opens above prev high, closes below midpoint.", "Bearish", "Medium"),
            ]
            pc = st.columns(2)
            for i, (name, desc, signal, strength) in enumerate(patterns):
                color = "#00ff88" if "Bullish" in signal else ("#ff4466" if "Bearish" in signal else "#f0c040")
                with pc[i % 2]:
                    st.markdown(f"""
                    <div style="background:rgba(0,15,30,0.8);border-left:3px solid {color};
                    border-radius:8px;padding:0.65rem 0.9rem;margin-bottom:0.5rem;">
                      <div style="font-weight:700;color:{color};font-size:0.83rem;">{name}
                        <span style="font-size:0.65rem;color:#8b949e;font-weight:400;"> — {strength}</span>
                      </div>
                      <div style="color:#c9d1d9;font-size:0.75rem;margin-top:0.2rem;">{desc}</div>
                    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.5rem 0.9rem;font-size:0.72rem;color:#8b949e;">
    ⚖️ <b style="color:#d29922;">Disclaimer:</b> Charts are for educational purposes only.
    Not SEBI/SEC investment advice. Always use proper risk management.
    </div>""", unsafe_allow_html=True)
