"""
FinsageAI — Live Portfolio Tracker v2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Track multiple assets · Live P&L · Add Position (improved) · Price Alerts
Data: yfinance (stocks/NSE) + CoinGecko (crypto)
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import time
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# COIN MAP
# ─────────────────────────────────────────────────────────────────────────────
GECKO_IDS = {
    "BTC":"bitcoin","ETH":"ethereum","BNB":"binancecoin","SOL":"solana",
    "XRP":"ripple","ADA":"cardano","AVAX":"avalanche-2","MATIC":"matic-network",
    "DOGE":"dogecoin","SHIB":"shiba-inu","PEPE":"pepe","FLOKI":"floki",
    "BONK":"bonk","WIF":"dogwifcoin","LINK":"chainlink","DOT":"polkadot",
    "ATOM":"cosmos","UNI":"uniswap","LTC":"litecoin","BCH":"bitcoin-cash",
}

ASSET_CATEGORIES = {
    "🇮🇳 NSE India": [
        ("RELIANCE",  "RELIANCE.NS"),  ("TCS",       "TCS.NS"),
        ("INFY",      "INFY.NS"),       ("HDFC Bank", "HDFCBANK.NS"),
        ("ICICI Bank","ICICIBANK.NS"),  ("WIPRO",     "WIPRO.NS"),
        ("ADANI ENT", "ADANIENT.NS"),   ("BAJFINANCE","BAJFINANCE.NS"),
    ],
    "🇺🇸 US Stocks": [
        ("Apple",     "AAPL"),  ("Tesla",  "TSLA"),
        ("NVIDIA",    "NVDA"),  ("Google", "GOOGL"),
        ("Microsoft", "MSFT"),  ("Amazon", "AMZN"),
        ("Meta",      "META"),  ("Netflix","NFLX"),
    ],
    "₿ Crypto Large Cap": [
        ("Bitcoin",  "BTC"),  ("Ethereum","ETH"),
        ("BNB",      "BNB"),  ("Solana",  "SOL"),
        ("XRP",      "XRP"),  ("ADA",     "ADA"),
        ("AVAX",     "AVAX"), ("DOGE",    "DOGE"),
    ],
    "🎭 Meme Coins": [
        ("SHIB",  "SHIB"),  ("PEPE", "PEPE"),
        ("FLOKI", "FLOKI"), ("BONK", "BONK"),
        ("WIF",   "WIF"),
    ],
}


def _get_live_price(sym: str) -> float | None:
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
    try:
        h = yf.Ticker(sym).history(period="1d")
        return float(h["Close"].iloc[-1]) if not h.empty else None
    except Exception:
        return None


def _fmt_price(p: float) -> str:
    if p < 0.0001: return f"${p:.8f}"
    if p < 0.01:   return f"${p:.6f}"
    if p < 1:      return f"${p:.4f}"
    if p < 1000:   return f"${p:,.2f}"
    return f"${p:,.2f}"


def _init_portfolio():
    for k, v in [
        ("pf_holdings",     []),
        ("pf_alerts",       []),
        ("pf_live_px",      {}),
        ("pf_last_refresh", 0),
        ("pf_txn_log",      []),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v


def _refresh_prices(force=False):
    now = time.time()
    if force or (now - st.session_state.get("pf_last_refresh", 0)) > 60:
        for h in st.session_state.get("pf_holdings", []):
            px = _get_live_price(h["symbol"])
            if px:
                st.session_state["pf_live_px"][h["symbol"]] = round(px, 8)
        st.session_state["pf_last_refresh"] = now


# ─────────────────────────────────────────────────────────────────────────────
# ADD POSITION HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _add_position(symbol: str, qty: float, avg_price: float,
                  notes: str = "", txn_type: str = "BUY"):
    """Add or merge a position into the portfolio."""
    symbol = symbol.upper().strip()
    holdings = st.session_state["pf_holdings"]
    existing = next((h for h in holdings if h["symbol"] == symbol), None)

    if existing:
        if txn_type == "BUY":
            total_qty    = existing["qty"] + qty
            new_avg      = (existing["qty"] * existing["avg_price"] + qty * avg_price) / total_qty
            existing["qty"]       = round(total_qty, 8)
            existing["avg_price"] = round(new_avg, 8)
            msg = f"✅ **{symbol}** position updated — new avg: {_fmt_price(new_avg)}, total qty: {total_qty:.6f}"
        else:  # SELL
            if qty > existing["qty"]:
                return False, f"❌ Can't sell {qty} — you only hold {existing['qty']} {symbol}"
            existing["qty"] = round(existing["qty"] - qty, 8)
            if existing["qty"] <= 0:
                st.session_state["pf_holdings"] = [h for h in holdings if h["symbol"] != symbol]
            msg = f"✅ Sold {qty} {symbol}"
    else:
        if txn_type == "SELL":
            return False, f"❌ {symbol} not in portfolio — can't sell what you don't hold."
        holdings.append({
            "symbol":    symbol,
            "qty":       round(qty, 8),
            "avg_price": round(avg_price, 8),
            "notes":     notes,
            "added_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        msg = f"✅ Added **{qty} {symbol}** @ {_fmt_price(avg_price)}"

    # Log transaction
    st.session_state["pf_txn_log"].append({
        "time":   datetime.now().strftime("%Y-%m-%d %H:%M"),
        "type":   txn_type,
        "symbol": symbol,
        "qty":    qty,
        "price":  avg_price,
        "notes":  notes,
    })
    return True, msg


# ═════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═════════════════════════════════════════════════════════════════════════════
def render_portfolio_tracker():
    _init_portfolio()
    try:
        from config import LOGO_URL
    except Exception:
        LOGO_URL = ""

    # ── HERO ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));
    border:1px solid rgba(74,158,255,0.25);border-radius:14px;
    padding:1.2rem 1.5rem;margin-bottom:1rem;">
      <div style="display:flex;align-items:center;gap:0.9rem;flex-wrap:wrap;">
        <div>
          <div style="font-size:1.1rem;font-weight:800;font-family:Orbitron,monospace;
          background:linear-gradient(90deg,#4a9eff,#00ff88);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          💼 Portfolio Tracker</div>
          <div style="color:#8b949e;font-size:11px;margin-top:2px;">
          Live P&L · Add/Remove Positions · Buy & Sell Log · Price Alerts · NSE + US + Crypto
          </div>
        </div>
        <div style="margin-left:auto;display:flex;gap:6px;flex-wrap:wrap;">
          <span style="background:rgba(74,158,255,0.1);color:#4a9eff;padding:3px 10px;
          border-radius:20px;font-size:10px;font-weight:700;
          border:1px solid rgba(74,158,255,0.2);">📊 Real-Time</span>
          <span style="background:rgba(0,255,136,0.08);color:#00ff88;padding:3px 10px;
          border-radius:20px;font-size:10px;font-weight:700;
          border:1px solid rgba(0,255,136,0.2);">🔔 Alerts</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab_port, tab_add, tab_alerts, tab_log = st.tabs([
        "💼 My Portfolio",
        "➕ Add / Sell Position",
        "🔔 Price Alerts",
        "📋 Transaction Log",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — PORTFOLIO VIEW
    # ══════════════════════════════════════════════════════════════════════════
    with tab_port:
        holdings = st.session_state.get("pf_holdings", [])

        if not holdings:
            st.markdown("""
            <div style="text-align:center;padding:2.5rem;color:#8b949e;">
              <div style="font-size:3rem;">💼</div>
              <div style="font-size:1rem;margin-top:8px;font-weight:600;">Portfolio is empty</div>
              <div style="font-size:13px;margin-top:4px;">Go to "Add / Sell Position" tab to add your first holding</div>
            </div>""", unsafe_allow_html=True)
            return

        rf_col, _ = st.columns([1, 5])
        with rf_col:
            if st.button("🔄 Refresh Prices", key="pf_refresh", use_container_width=True):
                _refresh_prices(force=True)
                st.rerun()

        last = st.session_state.get("pf_last_refresh", 0)
        st.caption(f"Last updated: {int(time.time()-last)}s ago | Auto-refreshes every 60s")
        _refresh_prices()

        rows = []
        for h in holdings:
            sym   = h["symbol"]
            qty   = h["qty"]
            avg   = h["avg_price"]
            live  = st.session_state["pf_live_px"].get(sym, avg)
            invested = qty * avg
            current  = qty * live
            pnl      = current - invested
            pnl_pct  = (live/avg - 1)*100 if avg > 0 else 0
            rows.append({
                "Symbol":      sym,
                "Qty":         qty,
                "Avg Price":   avg,
                "Live Price":  live,
                "Invested":    round(invested, 2),
                "Current Val": round(current, 2),
                "P&L ($)":     round(pnl, 2),
                "P&L %":       round(pnl_pct, 2),
                "Notes":       h.get("notes",""),
            })
        df = pd.DataFrame(rows)

        tot_inv = df["Invested"].sum()
        tot_cur = df["Current Val"].sum()
        tot_pnl = tot_cur - tot_inv
        tot_pct = (tot_pnl/tot_inv*100) if tot_inv > 0 else 0
        pnl_clr = "#00ff88" if tot_pnl >= 0 else "#ff4466"

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(0,20,40,0.9),rgba(5,0,30,0.85));
        border:2px solid {pnl_clr}33;border-radius:12px;
        padding:1rem 1.3rem;margin-bottom:12px;
        display:grid;grid-template-columns:repeat(4,1fr);gap:0.8rem;text-align:center;">
          <div>
            <div style="color:#8b949e;font-size:10px;text-transform:uppercase;">Invested</div>
            <div style="color:#4a9eff;font-size:1.3rem;font-weight:900;font-family:monospace;">
            ${tot_inv:,.2f}</div>
          </div>
          <div>
            <div style="color:#8b949e;font-size:10px;text-transform:uppercase;">Current Value</div>
            <div style="color:#c9d1d9;font-size:1.3rem;font-weight:900;font-family:monospace;">
            ${tot_cur:,.2f}</div>
          </div>
          <div>
            <div style="color:#8b949e;font-size:10px;text-transform:uppercase;">Total P&L</div>
            <div style="color:{pnl_clr};font-size:1.3rem;font-weight:900;font-family:monospace;">
            ${tot_pnl:+,.2f}</div>
          </div>
          <div>
            <div style="color:#8b949e;font-size:10px;text-transform:uppercase;">Return</div>
            <div style="color:{pnl_clr};font-size:1.3rem;font-weight:900;font-family:monospace;">
            {tot_pct:+.2f}%</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        def _cp(val):
            return "color:#00ff88;font-weight:700" if val > 0 else "color:#ff4466;font-weight:700"

        try:
            styled = df.drop(columns=["Notes"]).style.map(_cp, subset=["P&L ($)", "P&L %"])
        except AttributeError:
            styled = df.drop(columns=["Notes"]).style.applymap(_cp, subset=["P&L ($)", "P&L %"])

        st.dataframe(
            styled, use_container_width=True, hide_index=True,
            column_config={
                "Invested":    st.column_config.NumberColumn(format="$%.2f"),
                "Current Val": st.column_config.NumberColumn(format="$%.2f"),
                "P&L ($)":     st.column_config.NumberColumn(format="$%.2f"),
                "P&L %":       st.column_config.NumberColumn(format="%.2f%%"),
                "Avg Price":   st.column_config.NumberColumn(format="%.6f"),
                "Live Price":  st.column_config.NumberColumn(format="%.6f"),
            }
        )

        # Remove button
        rem_sym = st.selectbox("Remove position:", ["—"] + [h["symbol"] for h in holdings], key="pf_rem_sym")
        if st.button("🗑️ Remove", key="pf_rem_btn") and rem_sym != "—":
            st.session_state["pf_holdings"] = [h for h in holdings if h["symbol"] != rem_sym]
            st.rerun()

        # Charts
        if len(df) > 0:
            ch1, ch2 = st.columns(2)
            with ch1:
                st.markdown("**📊 Allocation by Current Value**")
                fig_pie = go.Figure(go.Pie(
                    labels=df["Symbol"], values=df["Current Val"], hole=0.45,
                    marker=dict(colors=["#00d4ff","#a371f7","#00ff88","#ff8c42",
                                        "#4a9eff","#f0c040","#ff4466","#58d68d"]),
                ))
                fig_pie.update_layout(paper_bgcolor="#020609", font_color="#c9d1d9",
                                      height=260, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            with ch2:
                st.markdown("**💰 P&L by Symbol**")
                colors = ["#00ff88" if v >= 0 else "#ff4466" for v in df["P&L ($)"]]
                fig_bar = go.Figure(go.Bar(
                    x=df["Symbol"], y=df["P&L ($)"], marker_color=colors,
                    text=df["P&L %"].apply(lambda x: f"{x:+.1f}%"), textposition="outside",
                ))
                fig_bar.update_layout(
                    plot_bgcolor="#020609", paper_bgcolor="#020609", font=dict(color="#c9d1d9"),
                    xaxis=dict(gridcolor="#0d1117"), yaxis=dict(gridcolor="#0d1117"),
                    height=260, margin=dict(l=0,r=0,t=10,b=0), showlegend=False,
                )
                st.plotly_chart(fig_bar, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — ADD / SELL POSITION (IMPROVED)
    # ══════════════════════════════════════════════════════════════════════════
    with tab_add:
        st.markdown("#### ➕ Add or Sell a Position")
        st.caption("Search by name or symbol, auto-fetch live price, log every transaction.")

        # ── Transaction type ─────────────────────────────────────────────────
        txn_type = st.radio(
            "Transaction Type",
            ["🟢 BUY / Add Position", "🔴 SELL / Reduce Position"],
            horizontal=True,
            key="pf_txn_type"
        )
        is_buy = "BUY" in txn_type

        # ── SEARCH / SELECT ASSET ─────────────────────────────────────────────
        st.markdown("**🔍 Step 1: Select or Search Asset**")

        search_col, cat_col = st.columns([3, 2])
        with search_col:
            new_sym = st.text_input(
                "Type symbol directly",
                placeholder="e.g. AAPL · RELIANCE.NS · BTC · ETH · SOL",
                key="pf_add_sym",
                label_visibility="collapsed"
            ).upper().strip()
        with cat_col:
            cat_choice = st.selectbox(
                "Or pick from category",
                ["— Type symbol above —"] + list(ASSET_CATEGORIES.keys()),
                key="pf_cat",
                label_visibility="collapsed"
            )

        # Category picker
        if cat_choice != "— Type symbol above —":
            st.markdown(f"**⚡ {cat_choice}:**")
            assets_in_cat = ASSET_CATEGORIES[cat_choice]
            cols_per_row  = min(4, len(assets_in_cat))
            cat_cols = st.columns(cols_per_row)
            for i, (name, sym) in enumerate(assets_in_cat):
                with cat_cols[i % cols_per_row]:
                    if st.button(f"{name}\n`{sym}`", key=f"pf_cat_{sym}", use_container_width=True):
                        st.session_state["pf_cat_selected"] = sym
                        st.rerun()

        # Merge: typed vs category selected
        selected_sym = st.session_state.pop("pf_cat_selected", None) or new_sym
        if selected_sym:
            st.markdown(f'<span style="color:#58a6ff;font-weight:700;font-size:14px;">Selected: {selected_sym}</span>', unsafe_allow_html=True)

        # ── FETCH LIVE PRICE ──────────────────────────────────────────────────
        st.markdown("**💰 Step 2: Set Price & Quantity**")

        price_col1, price_col2 = st.columns([2, 1])
        with price_col2:
            if st.button("🔍 Fetch Live Price", key="pf_fetch_live", use_container_width=True,
                         type="primary", disabled=not bool(selected_sym)):
                if selected_sym:
                    with st.spinner(f"Fetching live price for {selected_sym}…"):
                        lp = _get_live_price(selected_sym)
                    if lp:
                        st.session_state["pf_fetched_price"] = lp
                        st.success(f"Live: {_fmt_price(lp)}")
                    else:
                        st.error("Could not fetch price. Enter manually.")
                else:
                    st.warning("Select a symbol first.")

        fetched = st.session_state.get("pf_fetched_price", 0.0)

        with price_col1:
            # Show fetched price info
            if fetched > 0:
                st.markdown(
                    f'<div style="background:rgba(0,255,136,0.06);border:1px solid rgba(0,255,136,0.2);'
                    f'border-radius:8px;padding:8px 12px;margin-bottom:8px;font-size:13px;">'
                    f'📊 Live price: <b style="color:#00ff88;">{_fmt_price(fetched)}</b>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        # Inputs row
        inp1, inp2, inp3 = st.columns(3)
        with inp1:
            new_qty = st.number_input(
                "Quantity / Units",
                min_value=0.0000001, max_value=1e10,
                value=1.0, step=0.1, format="%.6f",
                key="pf_add_qty"
            )
        with inp2:
            default_price = fetched if fetched > 0 else 100.0
            new_avg = st.number_input(
                f"{'Buy' if is_buy else 'Sell'} Price ($)",
                min_value=0.000001, max_value=1e9,
                value=float(default_price),
                step=float(max(default_price * 0.001, 0.01)),
                format="%.6f",
                key="pf_add_avg"
            )
        with inp3:
            total_value = new_qty * new_avg
            st.metric(
                "Total Value",
                f"${total_value:,.2f}",
                help="Quantity × Price"
            )

        new_notes = st.text_input(
            "📝 Notes (optional)",
            placeholder="e.g. 'Long-term hold', 'Momentum trade at support', 'Part of DCA plan'",
            key="pf_notes"
        )

        # ── POSITION PREVIEW ──────────────────────────────────────────────────
        if selected_sym and new_qty > 0 and new_avg > 0:
            st.markdown("**📋 Step 3: Review & Confirm**")
            existing_h = next(
                (h for h in st.session_state.get("pf_holdings",[]) if h["symbol"] == selected_sym),
                None
            )
            preview_clr = "#00ff88" if is_buy else "#ff4466"
            action_word = "ADD" if is_buy else "SELL"

            if existing_h and is_buy:
                total_qty_after = existing_h["qty"] + new_qty
                new_avg_after   = (existing_h["qty"]*existing_h["avg_price"] + new_qty*new_avg) / total_qty_after
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.3);border:1px solid {preview_clr}44;
                border-radius:10px;padding:14px 18px;margin:8px 0;">
                  <div style="color:{preview_clr};font-weight:700;margin-bottom:8px;">{action_word} Preview — {selected_sym}</div>
                  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;font-size:12px;">
                    <div><div style="color:#8b949e;">Current Holdings</div><div style="color:#c9d1d9;font-weight:700;">{existing_h['qty']:.4f} @ {_fmt_price(existing_h['avg_price'])}</div></div>
                    <div><div style="color:#8b949e;">Adding</div><div style="color:{preview_clr};font-weight:700;">+ {new_qty:.4f} @ {_fmt_price(new_avg)}</div></div>
                    <div><div style="color:#8b949e;">New Position</div><div style="color:#e6edf3;font-weight:700;">{total_qty_after:.4f} @ {_fmt_price(new_avg_after)}</div></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.3);border:1px solid {preview_clr}44;
                border-radius:10px;padding:14px 18px;margin:8px 0;">
                  <div style="color:{preview_clr};font-weight:700;margin-bottom:6px;">{action_word} Preview — {selected_sym}</div>
                  <div style="font-size:13px;color:#c9d1d9;">
                  {new_qty:.6f} {selected_sym} × {_fmt_price(new_avg)} = <b style="color:{preview_clr};">${total_value:,.4f}</b>
                  </div>
                  {f'<div style="font-size:11px;color:#8b949e;margin-top:4px;">📝 {new_notes}</div>' if new_notes else ''}
                </div>
                """, unsafe_allow_html=True)

        # ── SUBMIT BUTTON ─────────────────────────────────────────────────────
        confirm_col, _ = st.columns([2, 3])
        with confirm_col:
            btn_label = ("✅ Confirm BUY — Add Position" if is_buy
                         else "🔴 Confirm SELL — Reduce Position")
            if st.button(btn_label, type="primary", use_container_width=True, key="pf_confirm_btn"):
                if not selected_sym:
                    st.error("⚠️ Select or type a symbol first.")
                elif new_qty <= 0:
                    st.error("⚠️ Quantity must be > 0.")
                elif new_avg <= 0:
                    st.error("⚠️ Price must be > 0.")
                else:
                    ok, msg = _add_position(
                        selected_sym, new_qty, new_avg, new_notes,
                        txn_type="BUY" if is_buy else "SELL"
                    )
                    if ok:
                        st.success(msg)
                        st.session_state["pf_fetched_price"] = 0.0
                        _refresh_prices(force=True)
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(msg)

        # ── QUICK PRESET BUTTONS ───────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**⚡ Quick Add at Live Price (1 unit):**")
        quick_syms = ["AAPL","TSLA","NVDA","RELIANCE.NS","TCS.NS","BTC","ETH","SOL","BNB","DOGE"]
        q_cols = st.columns(len(quick_syms))
        for i, sym in enumerate(quick_syms):
            with q_cols[i]:
                if st.button(sym, key=f"pf_qk_{sym}", use_container_width=True):
                    with st.spinner(f"{sym}…"):
                        px = _get_live_price(sym)
                    if px:
                        ok, msg = _add_position(sym, 1.0, px, "Quick add")
                        if ok:
                            _refresh_prices(force=True)
                            st.success(f"{sym} @ {_fmt_price(px)}")
                            st.rerun()
                    else:
                        st.error(f"Can't fetch {sym}")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — PRICE ALERTS
    # ══════════════════════════════════════════════════════════════════════════
    with tab_alerts:
        st.markdown("#### 🔔 Price Alerts")
        st.caption("Alerts checked on every page load. Session-based — resets on browser close.")

        al1, al2, al3, al4 = st.columns([2, 1, 1, 1])
        with al1:
            al_sym = st.text_input("Symbol", placeholder="BTC, AAPL, RELIANCE.NS…", key="al_sym")
        with al2:
            al_dir = st.selectbox("Condition", ["Price ABOVE", "Price BELOW"], key="al_dir")
        with al3:
            al_target = st.number_input("Target ($)", 0.0, 1e9, 100.0, format="%.4f", key="al_target")
        with al4:
            al_note = st.text_input("Note", placeholder="optional", key="al_note")

        if st.button("➕ Add Alert", type="primary", use_container_width=True, key="al_add"):
            if al_sym:
                st.session_state["pf_alerts"].append({
                    "symbol":    al_sym.upper().strip(),
                    "direction": al_dir,
                    "target":    al_target,
                    "note":      al_note,
                })
                st.success(f"Alert set: {al_sym.upper()} {al_dir} ${al_target:.4f}")
                st.rerun()
            else:
                st.warning("Enter a symbol.")

        alerts = st.session_state.get("pf_alerts", [])
        if alerts:
            st.markdown("**Active Alerts:**")
            for i, al in enumerate(alerts):
                live_px = st.session_state["pf_live_px"].get(al["symbol"])
                if live_px is None:
                    live_px = _get_live_price(al["symbol"])
                    if live_px:
                        st.session_state["pf_live_px"][al["symbol"]] = live_px

                triggered = (
                    (al["direction"] == "Price ABOVE" and live_px and live_px > al["target"]) or
                    (al["direction"] == "Price BELOW" and live_px and live_px < al["target"])
                )
                sc = "#ff4466" if triggered else "#00d4ff"
                si = "🔴 TRIGGERED!" if triggered else "🔵 Watching"
                lv = _fmt_price(live_px) if live_px else "fetching…"

                note_html = (' <span style="color:#8b949e;font-size:11px;">— ' + al.get("note","") + '</span>') if al.get("note") else ""
                alert_html = (
                    f'<div style="background:rgba(0,0,0,0.3);border:1px solid {sc}44;'
                    f'border-radius:10px;padding:10px 14px;margin-bottom:6px;'
                    f'display:flex;align-items:center;justify-content:space-between;">'
                    f'<div><span style="color:#4a9eff;font-weight:700;">{al["symbol"]}</span> '
                    f'<span style="color:#8b949e;"> {al["direction"]} </span>'
                    f'<span style="color:#f0c040;font-weight:700;">${al["target"]:.4f}</span>'
                    + note_html +
                    '</div>'
                    f'<div style="text-align:right;">'
                    f'<div style="color:{sc};font-weight:700;font-size:13px;">{si}</div>'
                    f'<div style="color:#8b949e;font-size:11px;">Live: {lv}</div>'
                    f'</div></div>'
                )
                st.markdown(alert_html, unsafe_allow_html=True)
                if triggered:
                    st.toast(f"🔔 ALERT: {al['symbol']} {al['direction']} ${al['target']:.4f}!", icon="🚨")

            if st.button("🗑️ Clear All Alerts", key="al_clear"):
                st.session_state["pf_alerts"] = []
                st.rerun()
        else:
            st.info("No alerts set yet. Add your first alert above.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — TRANSACTION LOG
    # ══════════════════════════════════════════════════════════════════════════
    with tab_log:
        st.markdown("#### 📋 Transaction History")
        txn_log = st.session_state.get("pf_txn_log", [])
        if txn_log:
            log_df = pd.DataFrame(txn_log[::-1])  # newest first
            log_df["value"] = (log_df["qty"] * log_df["price"]).round(4)

            def _style_type(v):
                return "color:#00ff88;font-weight:700" if "BUY" in str(v) else "color:#ff4466;font-weight:700"

            try:
                styled_log = log_df.style.map(_style_type, subset=["type"])
            except AttributeError:
                styled_log = log_df.style.applymap(_style_type, subset=["type"])

            st.dataframe(styled_log, use_container_width=True, hide_index=True,
                         column_config={
                             "price": st.column_config.NumberColumn(format="%.6f"),
                             "value": st.column_config.NumberColumn(format="$%.2f"),
                         })

            if st.button("🗑️ Clear Log", key="pf_clear_log"):
                st.session_state["pf_txn_log"] = []
                st.rerun()
        else:
            st.info("No transactions yet. Add your first position above.")
