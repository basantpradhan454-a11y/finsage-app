"""
FinsageAI — Live Portfolio Tracker + Price Alerts
Track multiple assets with real P&L, set price alerts (session-based)
Data: yfinance + CoinGecko — 100% free
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import time
from datetime import datetime


# ── CoinGecko ID map ──────────────────────────────────────────────────────────
GECKO_IDS = {
    "BTC":"bitcoin","ETH":"ethereum","BNB":"binancecoin","SOL":"solana",
    "XRP":"ripple","ADA":"cardano","AVAX":"avalanche-2","MATIC":"matic-network",
    "DOGE":"dogecoin","SHIB":"shiba-inu","PEPE":"pepe","FLOKI":"floki",
    "BONK":"bonk","WIF":"dogwifcoin","LINK":"chainlink","DOT":"polkadot",
}

def _get_live_price(sym: str) -> float | None:
    """Get live price: CoinGecko for crypto, yfinance for stocks."""
    sym_up = sym.upper().replace("-USD","").replace("-USDT","")
    if sym_up in GECKO_IDS:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": GECKO_IDS[sym_up], "vs_currencies": "usd"},
                timeout=8
            )
            return r.json()[GECKO_IDS[sym_up]]["usd"]
        except Exception:
            return None
    else:
        try:
            t    = yf.Ticker(sym)
            hist = t.history(period="1d")
            return float(hist["Close"].iloc[-1]) if not hist.empty else None
        except Exception:
            return None


def _init_portfolio():
    if "pf_holdings" not in st.session_state:
        st.session_state["pf_holdings"] = []
    if "pf_alerts"   not in st.session_state:
        st.session_state["pf_alerts"]   = []
    if "pf_live_px"  not in st.session_state:
        st.session_state["pf_live_px"]  = {}
    if "pf_last_refresh" not in st.session_state:
        st.session_state["pf_last_refresh"] = 0


def _refresh_prices(force=False):
    now = time.time()
    if force or (now - st.session_state.get("pf_last_refresh",0)) > 60:
        holdings = st.session_state.get("pf_holdings", [])
        for h in holdings:
            px = _get_live_price(h["symbol"])
            if px:
                st.session_state["pf_live_px"][h["symbol"]] = round(px, 6)
        st.session_state["pf_last_refresh"] = now


def render_portfolio_tracker():
    from config import LOGO_URL
    _init_portfolio()

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));
    border:1px solid rgba(74,158,255,0.25);border-radius:14px;
    padding:1.2rem 1.5rem;margin-bottom:1rem;">
      <div style="display:flex;align-items:center;gap:0.9rem;">
        <img src="{LOGO_URL}" style="height:44px;border-radius:10px;">
        <div>
          <div style="font-size:1.1rem;font-weight:800;font-family:Orbitron,monospace;
          background:linear-gradient(90deg,#4a9eff,#00ff88);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          💼 Portfolio Tracker</div>
          <div style="color:#8b949e;font-size:0.73rem;">
          Live P&L · Allocation Chart · Price Alerts · NSE + US + Crypto
          </div>
        </div>
        <div style="margin-left:auto;display:flex;gap:0.5rem;">
          <span style="background:rgba(74,158,255,0.1);color:#4a9eff;
          padding:0.2rem 0.7rem;border-radius:20px;font-size:0.65rem;font-weight:700;
          border:1px solid rgba(74,158,255,0.25);">📊 Real-Time</span>
          <span style="background:rgba(0,255,136,0.08);color:#00ff88;
          padding:0.2rem 0.7rem;border-radius:20px;font-size:0.65rem;font-weight:700;
          border:1px solid rgba(0,255,136,0.2);">🔔 Alerts</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab_port, tab_add, tab_alerts = st.tabs([
        "💼 My Portfolio", "➕ Add Position", "🔔 Price Alerts"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: Portfolio View
    # ══════════════════════════════════════════════════════════════════════════
    with tab_port:
        holdings = st.session_state.get("pf_holdings", [])

        if not holdings:
            st.markdown("""
            <div style="text-align:center;padding:2rem;color:#8b949e;">
              <div style="font-size:2.5rem;">💼</div>
              <div style="font-size:1rem;margin-top:0.5rem;">Your portfolio is empty</div>
              <div style="font-size:0.8rem;margin-top:0.3rem;">Go to "Add Position" tab to add your holdings</div>
            </div>""", unsafe_allow_html=True)
            return

        # Refresh prices
        rf_col1, rf_col2 = st.columns([5,1])
        with rf_col2:
            if st.button("🔄 Refresh", key="pf_refresh", use_container_width=True):
                _refresh_prices(force=True)
                st.rerun()
        with rf_col1:
            last = st.session_state.get("pf_last_refresh", 0)
            age  = int(time.time() - last)
            st.caption(f"Last updated: {age}s ago | Auto-refreshes every 60s")

        _refresh_prices()

        # Build DataFrame
        rows = []
        for h in holdings:
            sym   = h["symbol"]
            qty   = h["qty"]
            avg   = h["avg_price"]
            live  = st.session_state["pf_live_px"].get(sym)
            if live is None:
                live = avg  # fallback

            invested = qty * avg
            current  = qty * live
            pnl      = current - invested
            pnl_pct  = (live/avg - 1)*100 if avg > 0 else 0

            rows.append({
                "Symbol":      sym,
                "Qty":         qty,
                "Avg Price":   avg,
                "Live Price":  round(live, 6),
                "Invested":    round(invested, 2),
                "Current Val": round(current, 2),
                "P&L ($)":     round(pnl, 2),
                "P&L %":       round(pnl_pct, 2),
                "_pnl":        pnl,
            })

        df = pd.DataFrame(rows)

        # Portfolio summary
        total_invested = df["Invested"].sum()
        total_current  = df["Current Val"].sum()
        total_pnl      = total_current - total_invested
        total_pnl_pct  = (total_pnl / total_invested * 100) if total_invested > 0 else 0

        pnl_color = "#00ff88" if total_pnl >= 0 else "#ff4466"
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(0,20,40,0.9),rgba(5,0,30,0.85));
        border:2px solid {pnl_color}33;border-radius:12px;
        padding:1rem 1.3rem;margin-bottom:0.8rem;
        display:grid;grid-template-columns:repeat(4,1fr);gap:0.8rem;text-align:center;">
          <div>
            <div style="color:#8b949e;font-size:0.68rem;">INVESTED</div>
            <div style="color:#4a9eff;font-size:1.4rem;font-weight:900;
            font-family:Orbitron,monospace;">${total_invested:,.2f}</div>
          </div>
          <div>
            <div style="color:#8b949e;font-size:0.68rem;">CURRENT VALUE</div>
            <div style="color:#c9d1d9;font-size:1.4rem;font-weight:900;
            font-family:Orbitron,monospace;">${total_current:,.2f}</div>
          </div>
          <div>
            <div style="color:#8b949e;font-size:0.68rem;">TOTAL P&L</div>
            <div style="color:{pnl_color};font-size:1.4rem;font-weight:900;
            font-family:Orbitron,monospace;">${total_pnl:+,.2f}</div>
          </div>
          <div>
            <div style="color:#8b949e;font-size:0.68rem;">RETURN %</div>
            <div style="color:{pnl_color};font-size:1.4rem;font-weight:900;
            font-family:Orbitron,monospace;">{total_pnl_pct:+.2f}%</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Holdings table
        def _cp(val):
            return "color:#00ff88;font-weight:700" if val > 0 else "color:#ff4466;font-weight:700"

        display_df = df.drop(columns=["_pnl"])
        st.dataframe(
            display_df.style.applymap(_cp, subset=["P&L ($)","P&L %"]),
            use_container_width=True, hide_index=True,
            column_config={
                "Invested":    st.column_config.NumberColumn(format="$%.2f"),
                "Current Val": st.column_config.NumberColumn(format="$%.2f"),
                "P&L ($)":     st.column_config.NumberColumn(format="$%.2f"),
                "P&L %":       st.column_config.NumberColumn(format="%.2f%%"),
                "Avg Price":   st.column_config.NumberColumn(format="%.6f"),
                "Live Price":  st.column_config.NumberColumn(format="%.6f"),
            }
        )

        # Remove position
        rem_sym = st.selectbox("Remove position:", ["—"] + [h["symbol"] for h in holdings], key="pf_rem_sym")
        if st.button("🗑️ Remove", key="pf_rem_btn") and rem_sym != "—":
            st.session_state["pf_holdings"] = [h for h in holdings if h["symbol"] != rem_sym]
            st.rerun()

        # ── Charts ─────────────────────────────────────────────────────────────
        if len(df) > 0:
            ch1, ch2 = st.columns(2)
            with ch1:
                st.markdown("**📊 Allocation by Current Value**")
                fig_pie = go.Figure(go.Pie(
                    labels=df["Symbol"], values=df["Current Val"],
                    hole=0.45,
                    marker=dict(colors=[
                        "#00d4ff","#a371f7","#00ff88","#ff8c42",
                        "#4a9eff","#f0c040","#ff4466","#58d68d"
                    ]),
                    textfont_size=11,
                ))
                fig_pie.update_layout(
                    paper_bgcolor="#020609", font_color="#c9d1d9",
                    height=280, margin=dict(l=0,r=0,t=0,b=0),
                    legend=dict(bgcolor="rgba(0,0,0,0)", font_size=10),
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with ch2:
                st.markdown("**💰 P&L by Symbol**")
                colors = ["#00ff88" if v >= 0 else "#ff4466" for v in df["P&L ($)"]]
                fig_bar = go.Figure(go.Bar(
                    x=df["Symbol"], y=df["P&L ($)"],
                    marker_color=colors, text=df["P&L %"].apply(lambda x: f"{x:+.1f}%"),
                    textposition="outside",
                ))
                fig_bar.update_layout(
                    plot_bgcolor="#020609", paper_bgcolor="#020609",
                    font=dict(color="#c9d1d9"),
                    xaxis=dict(gridcolor="#0d1117"),
                    yaxis=dict(gridcolor="#0d1117", title="P&L ($)"),
                    height=280, margin=dict(l=0,r=0,t=10,b=0),
                    showlegend=False,
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        st.caption(f"⏰ Prices: yfinance (stocks) + CoinGecko (crypto) | {datetime.now().strftime('%H:%M:%S')}")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: Add Position
    # ══════════════════════════════════════════════════════════════════════════
    with tab_add:
        st.markdown("#### ➕ Add New Position")

        a1, a2, a3 = st.columns(3)
        with a1:
            new_sym = st.text_input("Symbol", placeholder="AAPL, RELIANCE.NS, BTC, ETH...", key="pf_add_sym").upper()
        with a2:
            new_qty = st.number_input("Quantity / Units", 0.0000001, 1e8, 1.0, step=0.1, format="%.6f", key="pf_add_qty")
        with a3:
            new_avg = st.number_input("Avg Buy Price ($)", 0.000001, 1e7, 100.0, step=1.0, format="%.6f", key="pf_add_avg")

        fetch_live_check = st.checkbox("Auto-fill live price as avg price", key="pf_autofill")

        if fetch_live_check and new_sym:
            with st.spinner(f"Fetching live price for {new_sym}..."):
                live_px = _get_live_price(new_sym)
            if live_px:
                st.info(f"Live price for {new_sym}: ${live_px:.6f}")
                new_avg = live_px
            else:
                st.warning(f"Could not fetch price for {new_sym}")

        add_btn = st.button("✅ Add to Portfolio", type="primary", use_container_width=True, key="pf_add_btn")

        if add_btn:
            if not new_sym:
                st.error("Enter a symbol first.")
            elif new_qty <= 0:
                st.error("Quantity must be > 0.")
            elif new_avg <= 0:
                st.error("Avg price must be > 0.")
            else:
                # Check duplicate
                existing = [h for h in st.session_state["pf_holdings"] if h["symbol"] == new_sym]
                if existing:
                    # Merge — weighted average
                    old = existing[0]
                    total_qty = old["qty"] + new_qty
                    old["avg_price"] = (old["qty"]*old["avg_price"] + new_qty*new_avg) / total_qty
                    old["qty"] = total_qty
                    st.success(f"✅ {new_sym} position updated — new avg: ${old['avg_price']:.6f}")
                else:
                    st.session_state["pf_holdings"].append({
                        "symbol": new_sym, "qty": new_qty, "avg_price": new_avg
                    })
                    st.success(f"✅ Added {new_qty} {new_sym} @ ${new_avg:.4f}")
                _refresh_prices(force=True)
                st.rerun()

        # Quick add presets
        st.markdown("**⚡ Quick Add Presets:**")
        presets = ["AAPL","TSLA","NVDA","RELIANCE.NS","TCS.NS","BTC","ETH","SOL","DOGE","PEPE"]
        preset_cols = st.columns(len(presets))
        for i, psym in enumerate(presets):
            with preset_cols[i]:
                if st.button(psym, key=f"pf_preset_{psym}", use_container_width=True):
                    with st.spinner(f"Fetching {psym}..."):
                        px = _get_live_price(psym)
                    if px:
                        st.session_state["pf_holdings"].append({
                            "symbol": psym, "qty": 1.0, "avg_price": round(px, 6)
                        })
                        _refresh_prices(force=True)
                        st.success(f"Added 1 {psym} @ ${px:.4f}")
                        st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: Price Alerts
    # ══════════════════════════════════════════════════════════════════════════
    with tab_alerts:
        st.markdown("#### 🔔 Price Alerts")
        st.caption("Alerts are checked every time you open this page. Session-based — resets on browser close.")

        # Add alert
        al1, al2, al3, al4 = st.columns([2,1,1,1])
        with al1:
            al_sym = st.text_input("Symbol", placeholder="BTC, AAPL, RELIANCE.NS...", key="al_sym").upper()
        with al2:
            al_dir = st.selectbox("Alert when", ["Price ABOVE", "Price BELOW"], key="al_dir")
        with al3:
            al_px  = st.number_input("Target Price ($)", 0.0, 1e8, 0.0, step=0.01, format="%.6f", key="al_px")
        with al4:
            al_note = st.text_input("Note (optional)", placeholder="Take profit!", key="al_note")

        if st.button("🔔 Set Alert", type="primary", key="al_set", use_container_width=True):
            if al_sym and al_px > 0:
                st.session_state["pf_alerts"].append({
                    "symbol": al_sym,
                    "direction": al_dir,
                    "target": al_px,
                    "note": al_note,
                    "triggered": False,
                    "created": datetime.now().strftime("%H:%M:%S"),
                })
                st.success(f"✅ Alert set: {al_sym} {al_dir} ${al_px:.4f}")
            else:
                st.error("Enter symbol and target price.")

        # Check alerts
        alerts = st.session_state.get("pf_alerts", [])
        if alerts:
            st.markdown("---")
            st.markdown("**Active Alerts:**")

            triggered_any = False
            for i, al in enumerate(alerts):
                live_px = st.session_state["pf_live_px"].get(al["symbol"])
                if live_px is None:
                    live_px = _get_live_price(al["symbol"])
                    if live_px:
                        st.session_state["pf_live_px"][al["symbol"]] = live_px

                is_triggered = False
                if live_px:
                    if al["direction"] == "Price ABOVE" and live_px > al["target"]:
                        is_triggered = True
                    elif al["direction"] == "Price BELOW" and live_px < al["target"]:
                        is_triggered = True

                status_color = "#ff4466" if is_triggered else "#00d4ff"
                status_icon  = "🔴 TRIGGERED!" if is_triggered else "🔵 Watching"
                live_str     = f"${live_px:,.6f}" if live_px else "fetching..."

                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.3);border:1px solid {status_color}44;
                border-radius:10px;padding:0.7rem 1rem;margin-bottom:0.4rem;
                display:flex;align-items:center;justify-content:space-between;">
                  <div>
                    <span style="color:#4a9eff;font-weight:700;font-family:monospace;">{al['symbol']}</span>
                    &nbsp;
                    <span style="color:#8b949e;font-size:0.8rem;">{al['direction']}</span>
                    &nbsp;
                    <span style="color:#f0c040;font-weight:700;">${al['target']:.6f}</span>
                    {f"<span style='color:#8b949e;font-size:0.75rem;'> — {al['note']}</span>" if al['note'] else ""}
                  </div>
                  <div style="text-align:right;">
                    <div style="color:{status_color};font-weight:700;font-size:0.85rem;">{status_icon}</div>
                    <div style="color:#8b949e;font-size:0.72rem;">Live: {live_str}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

                if is_triggered:
                    st.toast(f"🔔 ALERT: {al['symbol']} {al['direction']} ${al['target']:.4f}! Current: {live_str}", icon="🚨")
                    triggered_any = True

            # Clear all button
            if st.button("🗑️ Clear All Alerts", key="al_clear", use_container_width=True):
                st.session_state["pf_alerts"] = []
                st.rerun()
        else:
            st.info("No alerts set. Add your first price alert above.")

        st.caption("⏰ Alerts checked on page load | For push notifications, upgrade to a backend deployment")
