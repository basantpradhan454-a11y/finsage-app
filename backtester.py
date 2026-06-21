"""
FinsageAI — Strategy Backtesting Engine
Test RSI, MACD, EMA crossover strategies on real historical data (yfinance)
Pure pandas — no external libraries needed
"""

import streamlit as st
from ticker_resolver import resolve_ticker
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date


# ── Indicator helpers ─────────────────────────────────────────────────────────
def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def _rsi(s, n=14):
    d  = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = g.ewm(com=n-1, min_periods=n).mean()
    al = l.ewm(com=n-1, min_periods=n).mean()
    return 100 - 100/(1 + ag/al.replace(0, np.nan))

def _macd(s, f=12, sl=26, sig=9):
    m = _ema(s,f) - _ema(s,sl)
    return m, _ema(m,sig)

def _bb(s, n=20, k=2):
    m  = s.rolling(n).mean(); sd = s.rolling(n).std()
    return m+k*sd, m, m-k*sd

def _atr(h, l, c, n=14):
    tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.ewm(com=n-1, min_periods=n).mean()


# ── Strategy definitions ──────────────────────────────────────────────────────
STRATEGIES = {
    "RSI Reversal": {
        "desc": "Buy when RSI < 30 (oversold). Sell when RSI > 70 (overbought).",
        "params": {"rsi_buy": 30, "rsi_sell": 70},
    },
    "MACD Crossover": {
        "desc": "Buy when MACD crosses above Signal. Sell when MACD crosses below Signal.",
        "params": {},
    },
    "EMA Crossover (9/21)": {
        "desc": "Buy when EMA9 crosses above EMA21. Sell on opposite crossover.",
        "params": {},
    },
    "EMA Golden/Death Cross (50/200)": {
        "desc": "Golden Cross (EMA50>EMA200) = Buy. Death Cross = Sell.",
        "params": {},
    },
    "Bollinger Band Bounce": {
        "desc": "Buy when price touches lower BB. Sell when price touches upper BB.",
        "params": {},
    },
    "RSI + MACD Combo": {
        "desc": "Buy only when RSI < 40 AND MACD > Signal (double confirmation).",
        "params": {"rsi_buy": 40},
    },
}


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_data(sym: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.Ticker(sym).history(period=period, interval=interval)
    if df.empty:
        return pd.DataFrame()
    df.index = pd.to_datetime(df.index)
    return df


def _run_backtest(df: pd.DataFrame, strategy: str, params: dict,
                  initial_capital: float = 100_000,
                  position_pct: float = 0.95,
                  stop_loss_pct: float = 0.0,
                  take_profit_pct: float = 0.0) -> dict:
    """
    Run backtest for a given strategy.
    Returns trades list + equity curve + stats.
    """
    if df.empty or len(df) < 50:
        return {"error": "Insufficient data"}

    c = df["Close"].copy()
    h = df["High"].copy()
    l = df["Low"].copy()

    # Build signal column
    signals = pd.Series(0, index=df.index)  # 1=buy, -1=sell

    if strategy == "RSI Reversal":
        rsi = _rsi(c)
        signals[rsi < params.get("rsi_buy", 30)]  =  1
        signals[rsi > params.get("rsi_sell", 70)] = -1

    elif strategy == "MACD Crossover":
        macd, sig = _macd(c)
        cross_up   = (macd > sig) & (macd.shift() <= sig.shift())
        cross_down = (macd < sig) & (macd.shift() >= sig.shift())
        signals[cross_up]   =  1
        signals[cross_down] = -1

    elif strategy == "EMA Crossover (9/21)":
        e9, e21 = _ema(c, 9), _ema(c, 21)
        signals[(e9 > e21) & (e9.shift() <= e21.shift())]  =  1
        signals[(e9 < e21) & (e9.shift() >= e21.shift())] = -1

    elif strategy == "EMA Golden/Death Cross (50/200)":
        e50, e200 = _ema(c, 50), _ema(c, 200)
        signals[(e50 > e200) & (e50.shift() <= e200.shift())]  =  1
        signals[(e50 < e200) & (e50.shift() >= e200.shift())] = -1

    elif strategy == "Bollinger Band Bounce":
        bb_u, bb_m, bb_l = _bb(c)
        signals[c <= bb_l]  =  1
        signals[c >= bb_u] = -1

    elif strategy == "RSI + MACD Combo":
        rsi = _rsi(c); macd, sig = _macd(c)
        signals[(rsi < params.get("rsi_buy", 40)) & (macd > sig)]  =  1
        signals[(rsi > 60) & (macd < sig)] = -1

    # ── Simulate trades ──────────────────────────────────────────────────────
    cash     = initial_capital
    position = 0.0      # units held
    entry_px = 0.0
    trades   = []
    equity   = []
    in_trade = False

    for i, (ts, row) in enumerate(df.iterrows()):
        price  = float(row["Close"])
        sig    = int(signals.iloc[i])

        # Stop loss / Take profit exit
        if in_trade and entry_px > 0:
            if stop_loss_pct > 0 and price <= entry_px * (1 - stop_loss_pct/100):
                pnl  = (price - entry_px) * position
                cash = cash + position * price
                trades.append({
                    "Entry Date":  entry_date.strftime("%Y-%m-%d"),
                    "Exit Date":   ts.strftime("%Y-%m-%d"),
                    "Entry Price": round(entry_px, 4),
                    "Exit Price":  round(price, 4),
                    "Units":       round(position, 4),
                    "PnL ($)":     round(pnl, 2),
                    "PnL %":       round((price/entry_px - 1)*100, 2),
                    "Exit Reason": "🛑 Stop Loss",
                })
                position = 0; in_trade = False; entry_px = 0
            elif take_profit_pct > 0 and price >= entry_px * (1 + take_profit_pct/100):
                pnl  = (price - entry_px) * position
                cash = cash + position * price
                trades.append({
                    "Entry Date":  entry_date.strftime("%Y-%m-%d"),
                    "Exit Date":   ts.strftime("%Y-%m-%d"),
                    "Entry Price": round(entry_px, 4),
                    "Exit Price":  round(price, 4),
                    "Units":       round(position, 4),
                    "PnL ($)":     round(pnl, 2),
                    "PnL %":       round((price/entry_px - 1)*100, 2),
                    "Exit Reason": "🎯 Take Profit",
                })
                position = 0; in_trade = False; entry_px = 0

        # Signal-based entry/exit
        if sig == 1 and not in_trade and cash > 0:
            invest   = cash * position_pct
            position = invest / price
            cash     = cash - invest
            entry_px = price
            entry_date = ts
            in_trade = True

        elif sig == -1 and in_trade:
            pnl  = (price - entry_px) * position
            cash = cash + position * price
            trades.append({
                "Entry Date":  entry_date.strftime("%Y-%m-%d"),
                "Exit Date":   ts.strftime("%Y-%m-%d"),
                "Entry Price": round(entry_px, 4),
                "Exit Price":  round(price, 4),
                "Units":       round(position, 4),
                "PnL ($)":     round(pnl, 2),
                "PnL %":       round((price/entry_px - 1)*100, 2),
                "Exit Reason": "📊 Signal",
            })
            position = 0; in_trade = False; entry_px = 0

        total_equity = cash + position * price
        equity.append({"Date": ts, "Equity": round(total_equity, 2),
                        "Price": round(price, 4)})

    # Close open position at end
    if in_trade and position > 0:
        price = float(df["Close"].iloc[-1])
        pnl   = (price - entry_px) * position
        cash  = cash + position * price
        trades.append({
            "Entry Date":  entry_date.strftime("%Y-%m-%d"),
            "Exit Date":   df.index[-1].strftime("%Y-%m-%d"),
            "Entry Price": round(entry_px, 4),
            "Exit Price":  round(price, 4),
            "Units":       round(position, 4),
            "PnL ($)":     round(pnl, 2),
            "PnL %":       round((price/entry_px - 1)*100, 2),
            "Exit Reason": "📅 Period End",
        })

    equity_df = pd.DataFrame(equity).set_index("Date")
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()

    # ── Stats ─────────────────────────────────────────────────────────────────
    final_equity   = float(equity_df["Equity"].iloc[-1]) if not equity_df.empty else initial_capital
    total_return   = (final_equity / initial_capital - 1) * 100
    bh_return      = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[0]) - 1) * 100

    if not trades_df.empty:
        wins       = trades_df[trades_df["PnL ($)"] > 0]
        losses     = trades_df[trades_df["PnL ($)"] <= 0]
        win_rate   = len(wins) / len(trades_df) * 100
        avg_win    = wins["PnL ($)"].mean()    if len(wins)   else 0
        avg_loss   = losses["PnL ($)"].mean()  if len(losses) else 0
        profit_factor = abs(wins["PnL ($)"].sum() / losses["PnL ($)"].sum()) if losses["PnL ($)"].sum() != 0 else float("inf")
        max_dd     = _max_drawdown(equity_df["Equity"])
        sharpe     = _sharpe(equity_df["Equity"])
    else:
        win_rate = avg_win = avg_loss = profit_factor = max_dd = sharpe = 0

    return {
        "equity_df":      equity_df,
        "trades_df":      trades_df,
        "initial":        initial_capital,
        "final":          round(final_equity, 2),
        "total_return":   round(total_return, 2),
        "bh_return":      round(bh_return, 2),
        "n_trades":       len(trades_df) if not trades_df.empty else 0,
        "win_rate":       round(win_rate, 1),
        "avg_win":        round(avg_win, 2),
        "avg_loss":       round(avg_loss, 2),
        "profit_factor":  round(profit_factor, 2) if profit_factor != float("inf") else "∞",
        "max_drawdown":   round(max_dd, 2),
        "sharpe":         round(sharpe, 2),
        "alpha":          round(total_return - bh_return, 2),
        "error":          None,
    }


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd   = (equity - peak) / peak * 100
    return float(dd.min())


def _sharpe(equity: pd.Series, rf=0.0) -> float:
    returns = equity.pct_change().dropna()
    if returns.std() == 0:
        return 0.0
    return float((returns.mean() - rf/252) / returns.std() * np.sqrt(252))


def render_backtester():
    from config import LOGO_URL

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));
    border:1px solid rgba(163,113,247,0.3);border-radius:14px;
    padding:1.2rem 1.5rem;margin-bottom:1rem;">
      <div style="display:flex;align-items:center;gap:0.9rem;">
        <img src="{LOGO_URL}" style="height:44px;border-radius:10px;">
        <div>
          <div style="font-size:1.1rem;font-weight:800;font-family:Orbitron,monospace;
          background:linear-gradient(90deg,#a371f7,#00d4ff);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          📊 Strategy Backtester</div>
          <div style="color:#8b949e;font-size:0.73rem;">
          Test RSI · MACD · EMA · BB strategies on real historical data
          </div>
        </div>
        <span style="margin-left:auto;background:rgba(163,113,247,0.1);color:#a371f7;
        padding:0.2rem 0.7rem;border-radius:20px;font-size:0.65rem;font-weight:700;
        border:1px solid rgba(163,113,247,0.25);">📈 Historical yfinance Data</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Config ────────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        sym = st.text_input("Symbol", value="RELIANCE.NS",
                            placeholder="AAPL, RELIANCE.NS, BTC-USD...", key="bt_sym")
    with col2:
        strategy = st.selectbox("Strategy", list(STRATEGIES.keys()), key="bt_strat")
    with col3:
        period = st.selectbox("Period", ["1y","2y","3y","5y","max"], index=1, key="bt_period")

    # Strategy description
    st.info(f"📋 **{strategy}:** {STRATEGIES[strategy]['desc']}")

    # Advanced settings
    with st.expander("⚙️ Advanced Settings", expanded=False):
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            capital = st.number_input("Initial Capital ($)", 1000, 10_000_000,
                                      100_000, step=1000, key="bt_cap")
        with a2:
            pos_pct = st.slider("Position Size %", 10, 100, 95, key="bt_pos")
        with a3:
            sl_pct  = st.number_input("Stop Loss %", 0.0, 50.0, 0.0,
                                       step=0.5, key="bt_sl",
                                       help="0 = disabled")
        with a4:
            tp_pct  = st.number_input("Take Profit %", 0.0, 200.0, 0.0,
                                       step=1.0, key="bt_tp",
                                       help="0 = disabled")

        # RSI custom params
        if "RSI" in strategy:
            p1, p2 = st.columns(2)
            with p1:
                rsi_buy  = st.slider("RSI Buy Level",  10, 50, 30, key="bt_rbuy")
            with p2:
                rsi_sell = st.slider("RSI Sell Level", 50, 90, 70, key="bt_rsell")
            STRATEGIES[strategy]["params"]["rsi_buy"]  = rsi_buy
            STRATEGIES[strategy]["params"]["rsi_sell"] = rsi_sell

    run_btn = st.button("🚀 Run Backtest", type="primary", use_container_width=True, key="bt_run")

    if not run_btn and "bt_result" not in st.session_state:
        st.info("👆 Configure your strategy and click Run Backtest.")
        return

    if run_btn:
        with st.spinner(f"Running {strategy} backtest on {sym} ({period})..."):
            df_raw = _fetch_data(sym, period, "1d")
            if df_raw.empty:
                st.error(f"❌ No data for {sym}"); return
            result = _run_backtest(
                df_raw, strategy, STRATEGIES[strategy]["params"],
                initial_capital=capital,
                position_pct=pos_pct/100,
                stop_loss_pct=sl_pct,
                take_profit_pct=tp_pct,
            )
        if result.get("error"):
            st.error(result["error"]); return
        st.session_state["bt_result"] = result
        st.session_state["bt_df_raw"] = df_raw
        st.session_state["bt_sym_display"] = sym

    result  = st.session_state["bt_result"]
    df_raw  = st.session_state["bt_df_raw"]
    sym_d   = st.session_state.get("bt_sym_display", sym)

    # ── Stats Dashboard ───────────────────────────────────────────────────────
    total_ret = result["total_return"]
    ret_color = "#00ff88" if total_ret > 0 else "#ff4466"
    alpha     = result["alpha"]
    alpha_col = "#00ff88" if alpha > 0 else "#ff4466"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(0,20,40,0.9),rgba(5,0,30,0.85));
    border:2px solid {ret_color}33;border-radius:14px;
    padding:1.1rem 1.3rem;margin-bottom:0.8rem;">
      <div style="color:#8b949e;font-size:0.7rem;font-weight:700;
      letter-spacing:0.1em;font-family:Orbitron,monospace;">
      BACKTEST RESULT — {sym_d} | {strategy}</div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.8rem;margin-top:0.8rem;">
        <div style="text-align:center;">
          <div style="color:#8b949e;font-size:0.68rem;">STRATEGY RETURN</div>
          <div style="font-size:1.6rem;font-weight:900;color:{ret_color};
          font-family:Orbitron,monospace;">{total_ret:+.1f}%</div>
        </div>
        <div style="text-align:center;">
          <div style="color:#8b949e;font-size:0.68rem;">BUY & HOLD</div>
          <div style="font-size:1.6rem;font-weight:900;color:#4a9eff;
          font-family:Orbitron,monospace;">{result['bh_return']:+.1f}%</div>
        </div>
        <div style="text-align:center;">
          <div style="color:#8b949e;font-size:0.68rem;">ALPHA vs B&H</div>
          <div style="font-size:1.6rem;font-weight:900;color:{alpha_col};
          font-family:Orbitron,monospace;">{alpha:+.1f}%</div>
        </div>
        <div style="text-align:center;">
          <div style="color:#8b949e;font-size:0.68rem;">WIN RATE</div>
          <div style="font-size:1.6rem;font-weight:900;color:#a371f7;
          font-family:Orbitron,monospace;">{result['win_rate']:.1f}%</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("💰 Initial",       f"${result['initial']:,.0f}")
    m2.metric("💎 Final",         f"${result['final']:,.0f}",
              delta=f"{total_ret:+.1f}%")
    m3.metric("🔢 Total Trades",  result["n_trades"])
    m4.metric("📉 Max Drawdown",  f"{result['max_drawdown']:.1f}%")
    m5.metric("⚡ Sharpe Ratio",  result["sharpe"])
    m6.metric("🎯 Profit Factor", result["profit_factor"])

    # ── Charts ────────────────────────────────────────────────────────────────
    tab_eq, tab_tr, tab_pr = st.tabs(["📈 Equity Curve", "📋 Trade Log", "🕯️ Price Chart"])

    with tab_eq:
        eq_df = result["equity_df"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=eq_df.index, y=eq_df["Equity"], name="Strategy Equity",
            line=dict(color="#00ff88", width=2.5),
            fill="tozeroy", fillcolor="rgba(0,255,136,0.05)",
        ))
        # Buy & Hold line
        bh = (df_raw["Close"] / float(df_raw["Close"].iloc[0])) * result["initial"]
        fig.add_trace(go.Scatter(
            x=df_raw.index, y=bh, name="Buy & Hold",
            line=dict(color="#4a9eff", width=1.5, dash="dot"),
        ))
        fig.update_layout(
            plot_bgcolor="#020609", paper_bgcolor="#020609",
            font=dict(color="#c9d1d9", family="monospace"),
            xaxis=dict(gridcolor="#0d1117"), yaxis=dict(gridcolor="#0d1117"),
            height=380, margin=dict(l=0,r=0,t=10,b=0),
            hovermode="x unified", legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Drawdown chart
        peak = eq_df["Equity"].cummax()
        dd   = (eq_df["Equity"] - peak) / peak * 100
        fig_dd = go.Figure(go.Scatter(
            x=dd.index, y=dd, name="Drawdown %",
            line=dict(color="#ff4466", width=1.5),
            fill="tozeroy", fillcolor="rgba(255,68,102,0.1)",
        ))
        fig_dd.update_layout(
            plot_bgcolor="#020609", paper_bgcolor="#020609",
            font=dict(color="#c9d1d9"),
            xaxis=dict(gridcolor="#0d1117"), yaxis=dict(gridcolor="#0d1117", title="Drawdown %"),
            height=150, margin=dict(l=0,r=0,t=0,b=0), showlegend=False,
        )
        st.plotly_chart(fig_dd, use_container_width=True)

    with tab_tr:
        trades_df = result["trades_df"]
        if trades_df.empty:
            st.warning("No completed trades in this period.")
        else:
            def _color_pnl(val):
                return "color:#00ff88;font-weight:700" if val > 0 else "color:#ff4466;font-weight:700"
            styled_t = trades_df.style.map(_color_pnl, subset=["PnL ($)", "PnL %"])
            st.dataframe(styled_t, use_container_width=True, hide_index=True,
                column_config={
                    "PnL ($)": st.column_config.NumberColumn(format="$%.2f"),
                    "PnL %":   st.column_config.NumberColumn(format="%.2f%%"),
                })

            # Win/Loss breakdown
            wins   = trades_df[trades_df["PnL ($)"] > 0]
            losses = trades_df[trades_df["PnL ($)"] <= 0]
            wl1, wl2, wl3, wl4 = st.columns(4)
            wl1.metric("🟢 Wins",     len(wins))
            wl2.metric("🔴 Losses",   len(losses))
            wl3.metric("💰 Avg Win",  f"${result['avg_win']:,.2f}")
            wl4.metric("💸 Avg Loss", f"${result['avg_loss']:,.2f}")

    with tab_pr:
        fig_p = go.Figure()
        fig_p.add_trace(go.Candlestick(
            x=df_raw.index, open=df_raw["Open"], high=df_raw["High"],
            low=df_raw["Low"], close=df_raw["Close"], name=sym_d,
            increasing_line_color="#00ff88", decreasing_line_color="#ff4466",
            increasing_fillcolor="rgba(0,255,136,0.15)",
            decreasing_fillcolor="rgba(255,68,102,0.15)",
        ))
        # Plot trade markers
        if not result["trades_df"].empty:
            td = result["trades_df"]
            fig_p.add_trace(go.Scatter(
                x=pd.to_datetime(td["Entry Date"]), y=td["Entry Price"],
                mode="markers", name="Entry",
                marker=dict(symbol="triangle-up", color="#00ff88", size=10),
            ))
            fig_p.add_trace(go.Scatter(
                x=pd.to_datetime(td["Exit Date"]), y=td["Exit Price"],
                mode="markers", name="Exit",
                marker=dict(symbol="triangle-down", color="#ff4466", size=10),
            ))
        fig_p.update_layout(
            plot_bgcolor="#020609", paper_bgcolor="#020609",
            font=dict(color="#c9d1d9", family="monospace"),
            xaxis=dict(gridcolor="#0d1117", rangeslider_visible=False),
            yaxis=dict(gridcolor="#0d1117"),
            height=400, margin=dict(l=0,r=0,t=10,b=0),
            hovermode="x unified", legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_p, use_container_width=True)

    st.caption(f"⏰ Backtest on real yfinance data | Period: {period} | Trades simulated, not real")
    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.5rem 0.9rem;margin-top:0.5rem;font-size:0.73rem;color:#8b949e;">
    ⚠️ <b style="color:#d29922;">Disclaimer:</b> Backtesting does not guarantee future results.
    Past performance ≠ future returns. For educational purposes only.
    </div>""", unsafe_allow_html=True)
