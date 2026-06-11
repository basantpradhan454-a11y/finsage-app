"""
STOX AI — Paper Trading Agent
Chat se command do, AI trade execute kare (virtual/paper only)
"""

import streamlit as st
import pandas as pd
import json
import re
import time
from datetime import datetime
from data_fetcher import fetch_stock_data, fetch_crypto_data

# ── Session State Init ─────────────────────────────────────────────────────────
def init_trading_state():
    defaults = {
        "paper_portfolio": {},        # {symbol: {qty, avg_price, type}}
        "paper_trades": [],           # list of trade dicts
        "paper_balance": 100000.0,    # virtual ₹1,00,000 starting balance
        "chat_history": [],           # [{role, content, time}]
        "agent_thinking": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── NLP Command Parser ─────────────────────────────────────────────────────────
def parse_command(text: str) -> dict:
    """
    Parse natural language trading commands.
    Returns: {action, symbol, qty, asset_type, raw}
    """
    text_lower = text.lower().strip()
    result = {"raw": text, "action": None, "symbol": None, "qty": 1, "asset_type": "stock"}

    # ── ACTION detection ──
    buy_patterns  = r'\b(buy|purchase|kharido|lo|le lo|long|enter|add)\b'
    sell_patterns = r'\b(sell|becho|nikal|exit|close|hat jao|short)\b'
    check_patterns = r'\b(check|dekho|show|dikhao|analyse|analyze|report|status)\b'
    pnl_patterns   = r'\b(pnl|profit|loss|portfolio|balance|kitna|how much|returns)\b'
    clear_patterns = r'\b(clear|reset|sab becho|close all|sab nikal|exit all)\b'

    if re.search(clear_patterns, text_lower):
        result["action"] = "close_all"
        return result
    if re.search(pnl_patterns, text_lower):
        result["action"] = "portfolio"
        return result
    if re.search(sell_patterns, text_lower):
        result["action"] = "sell"
    elif re.search(buy_patterns, text_lower):
        result["action"] = "buy"
    elif re.search(check_patterns, text_lower):
        result["action"] = "analyze"
    else:
        result["action"] = "unknown"

    # ── QTY detection ──
    qty_match = re.search(r'(\d+(?:\.\d+)?)\s*(shares?|units?|coins?|lots?|nos?|pieces?)?', text_lower)
    if qty_match:
        result["qty"] = float(qty_match.group(1))

    # ── SYMBOL detection ──
    # Common crypto keywords
    crypto_coins = ["btc", "eth", "sol", "bnb", "xrp", "ada", "doge", "shib",
                    "pepe", "floki", "bonk", "wif", "avax", "dot", "matic",
                    "bitcoin", "ethereum", "solana", "dogecoin", "shibainu"]
    
    # Known stock patterns
    # Try to find TICKER pattern (uppercase 1-6 chars, possibly with .NS/.BO)
    ticker_match = re.findall(r'\b([A-Z]{1,6}(?:\.[A-Z]{1,3})?)\b', text.upper())
    
    # Check crypto symbols first
    for coin in crypto_coins:
        if coin in text_lower:
            result["asset_type"] = "crypto"
            coin_map = {
                "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL",
                "dogecoin": "DOGE", "shibainu": "SHIB"
            }
            result["symbol"] = coin_map.get(coin, coin.upper())
            break
    
    # If no crypto found, look for stock ticker
    if not result["symbol"]:
        skip_words = {"BUY", "SELL", "THE", "AND", "FOR", "GET", "SET", "ADD",
                      "ALL", "ME", "MY", "OF", "IN", "ON", "AT", "IS", "IT",
                      "KA", "KO", "DO", "LO", "TO", "AI"}
        for t in ticker_match:
            if t not in skip_words and len(t) >= 2:
                result["symbol"] = t
                break

    # ── Try to detect NSE suffix ──
    if result["symbol"] and ".NS" not in result["symbol"] and ".BO" not in result["symbol"]:
        nse_hint = r'\b(nse|india|reliance|tcs|infosys|infy|wipro|hdfc|icici|sbi|bajaj)\b'
        if re.search(nse_hint, text_lower):
            symbol_map = {
                "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS",
                "WIPRO": "WIPRO.NS", "HDFC": "HDFCBANK.NS", "ICICI": "ICICIBANK.NS",
                "SBI": "SBIN.NS", "BAJAJ": "BAJAJFINSV.NS", "INFOSYS": "INFY.NS"
            }
            result["symbol"] = symbol_map.get(result["symbol"], result["symbol"] + ".NS")
            result["asset_type"] = "stock"

    return result


# ── Fetch Current Price ────────────────────────────────────────────────────────
def get_live_price(symbol: str, asset_type: str) -> tuple:
    """Returns (price, name, error)"""
    try:
        if asset_type == "crypto":
            d = fetch_crypto_data(symbol)
            if "error" in d:
                return None, None, d["error"]
            return d.get("current_price", 0), d.get("name", symbol), None
        else:
            d = fetch_stock_data(symbol)
            if "error" in d:
                return None, None, d["error"]
            return d.get("current_price", 0), d.get("name", symbol), None
    except Exception as e:
        return None, None, str(e)


# ── Execute Trade ──────────────────────────────────────────────────────────────
def execute_buy(symbol: str, qty: float, asset_type: str) -> str:
    price, name, err = get_live_price(symbol, asset_type)
    if err:
        return f"❌ Price fetch failed for **{symbol}**: {err}"
    if not price or price <= 0:
        return f"❌ Invalid price received for **{symbol}**"

    total_cost = price * qty
    balance = st.session_state.paper_balance

    if total_cost > balance:
        return (f"❌ Insufficient balance!\n"
                f"Required: ₹{total_cost:,.2f} | Available: ₹{balance:,.2f}")

    # Update portfolio
    port = st.session_state.paper_portfolio
    if symbol in port:
        old_qty   = port[symbol]["qty"]
        old_price = port[symbol]["avg_price"]
        new_qty   = old_qty + qty
        new_avg   = ((old_qty * old_price) + (qty * price)) / new_qty
        port[symbol] = {"qty": new_qty, "avg_price": new_avg, "type": asset_type, "name": name}
    else:
        port[symbol] = {"qty": qty, "avg_price": price, "type": asset_type, "name": name}

    st.session_state.paper_balance -= total_cost

    # Log trade
    st.session_state.paper_trades.append({
        "time": datetime.now().strftime("%d %b %H:%M:%S"),
        "action": "BUY",
        "symbol": symbol,
        "name": name,
        "qty": qty,
        "price": price,
        "total": total_cost,
        "balance_after": st.session_state.paper_balance
    })

    return (f"✅ **BUY ORDER EXECUTED**\n\n"
            f"📌 **{name}** ({symbol})\n"
            f"🔢 Qty: {qty} units\n"
            f"💰 Price: ₹{price:,.4f}\n"
            f"💸 Total Cost: ₹{total_cost:,.2f}\n"
            f"🏦 Remaining Balance: ₹{st.session_state.paper_balance:,.2f}\n\n"
            f"_Paper trade — No real money involved_")


def execute_sell(symbol: str, qty: float, asset_type: str) -> str:
    port = st.session_state.paper_portfolio
    if symbol not in port:
        # Try partial match
        matches = [k for k in port if symbol in k or k.startswith(symbol)]
        if matches:
            symbol = matches[0]
        else:
            held = ", ".join(port.keys()) if port else "None"
            return f"❌ **{symbol}** not in portfolio!\nHeld assets: {held}"

    held_qty = port[symbol]["qty"]
    sell_qty = min(qty, held_qty)

    price, name, err = get_live_price(symbol, asset_type)
    if err:
        price = port[symbol]["avg_price"]  # fallback
        name  = port[symbol].get("name", symbol)

    avg_buy  = port[symbol]["avg_price"]
    proceeds = price * sell_qty
    pnl      = (price - avg_buy) * sell_qty
    pnl_pct  = ((price - avg_buy) / avg_buy) * 100 if avg_buy else 0
    pnl_icon = "🟢" if pnl >= 0 else "🔴"

    # Update portfolio
    remaining = held_qty - sell_qty
    if remaining <= 0.0001:
        del port[symbol]
    else:
        port[symbol]["qty"] = remaining

    st.session_state.paper_balance += proceeds

    # Log
    st.session_state.paper_trades.append({
        "time": datetime.now().strftime("%d %b %H:%M:%S"),
        "action": "SELL",
        "symbol": symbol,
        "name": name,
        "qty": sell_qty,
        "price": price,
        "total": proceeds,
        "pnl": pnl,
        "balance_after": st.session_state.paper_balance
    })

    return (f"✅ **SELL ORDER EXECUTED**\n\n"
            f"📌 **{name}** ({symbol})\n"
            f"🔢 Qty Sold: {sell_qty} units\n"
            f"💰 Sell Price: ₹{price:,.4f}\n"
            f"💵 Proceeds: ₹{proceeds:,.2f}\n"
            f"{pnl_icon} P&L: ₹{pnl:+,.2f} ({pnl_pct:+.2f}%)\n"
            f"🏦 New Balance: ₹{st.session_state.paper_balance:,.2f}\n\n"
            f"_Paper trade — No real money involved_")


def get_portfolio_summary() -> str:
    port = st.session_state.paper_portfolio
    balance = st.session_state.paper_balance

    if not port:
        return (f"📊 **Portfolio Status**\n\n"
                f"💵 Cash Balance: ₹{balance:,.2f}\n"
                f"📂 Holdings: None\n\n"
                f"_Start trading with commands like: 'Buy 10 AAPL' or 'Buy 5 BTC'_")

    lines = [f"📊 **Live Portfolio**\n"]
    total_invested = 0
    total_current  = 0

    for sym, info in port.items():
        price, _, err = get_live_price(sym, info["type"])
        if err or not price:
            price = info["avg_price"]

        invested = info["avg_price"] * info["qty"]
        current  = price * info["qty"]
        pnl      = current - invested
        pnl_pct  = (pnl / invested * 100) if invested else 0
        icon     = "🟢" if pnl >= 0 else "🔴"

        total_invested += invested
        total_current  += current

        lines.append(
            f"{icon} **{sym}** — {info['qty']} units\n"
            f"   Avg Buy: ₹{info['avg_price']:,.4f} | LTP: ₹{price:,.4f}\n"
            f"   Invested: ₹{invested:,.2f} | Current: ₹{current:,.2f}\n"
            f"   P&L: ₹{pnl:+,.2f} ({pnl_pct:+.2f}%)\n"
        )

    total_pnl     = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0
    net_worth     = balance + total_current
    total_icon    = "🟢" if total_pnl >= 0 else "🔴"

    lines.append(f"\n{'─'*30}")
    lines.append(f"💵 Cash: ₹{balance:,.2f}")
    lines.append(f"📈 Holdings Value: ₹{total_current:,.2f}")
    lines.append(f"🏦 Net Worth: ₹{net_worth:,.2f}")
    lines.append(f"{total_icon} Total P&L: ₹{total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)")

    return "\n".join(lines)


def close_all_positions() -> str:
    port = st.session_state.paper_portfolio
    if not port:
        return "📂 No open positions to close."

    results = []
    for sym in list(port.keys()):
        info = port[sym]
        msg = execute_sell(sym, info["qty"], info["type"])
        results.append(f"• {sym}: done")

    return f"✅ **All positions closed!**\n\n" + "\n".join(results) + f"\n\n💵 Cash Balance: ₹{st.session_state.paper_balance:,.2f}"


def analyze_asset(symbol: str, asset_type: str) -> str:
    if asset_type == "crypto":
        from analyzer import analyze_crypto
        d = fetch_crypto_data(symbol)
        if "error" in d:
            return f"❌ {d['error']}"
        report = analyze_crypto(d)
    else:
        from analyzer import analyze_stock
        d = fetch_stock_data(symbol)
        if "error" in d:
            return f"❌ {d['error']}"
        report = analyze_stock(d)

    price = d.get("current_price", 0)
    name  = d.get("name", symbol)
    rec   = report.get("recommendation", "HOLD")
    score = report.get("score", 0)
    risk  = report.get("risk_level", "Medium")

    rec_icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡", "STRONG BUY": "💚", "STRONG SELL": "❤️"}.get(rec, "⚪")

    return (f"🔍 **Analysis: {name}** ({symbol})\n\n"
            f"💰 Current Price: ₹{price:,.4f}\n"
            f"{rec_icon} Recommendation: **{rec}**\n"
            f"📊 Score: {score}/100\n"
            f"⚠️ Risk Level: {risk}\n\n"
            f"_{report.get('summary', 'Rule-based analysis')}_\n\n"
            f"_Want to trade? Say: 'Buy 5 {symbol}' or 'Sell 10 {symbol}'_")


# ── Process Chat Command ───────────────────────────────────────────────────────
def process_command(user_input: str) -> str:
    cmd = parse_command(user_input)
    action = cmd["action"]

    if action == "portfolio":
        return get_portfolio_summary()

    if action == "close_all":
        return close_all_positions()

    if action == "unknown" or not cmd["symbol"]:
        return (f"🤖 Samajh nahi aaya! Try these commands:\n\n"
                f"• `Buy 10 AAPL` — Apple ke 10 shares kharido\n"
                f"• `Buy 5 BTC` — 5 Bitcoin kharido\n"
                f"• `Sell 10 TSLA` — Tesla ke 10 shares becho\n"
                f"• `Check RELIANCE.NS` — Analysis dekho\n"
                f"• `Portfolio` — Apna portfolio dekho\n"
                f"• `Close all` — Sab positions band karo\n\n"
                f"_Hindi commands bhi chalti hain: 'Buy 10 TCS.NS lo'_")

    sym = cmd["symbol"]
    qty = cmd["qty"]
    atype = cmd["asset_type"]

    if action == "buy":
        return execute_buy(sym, qty, atype)
    elif action == "sell":
        return execute_sell(sym, qty, atype)
    elif action == "analyze":
        return analyze_asset(sym, atype)
    else:
        return f"❓ Action unclear for: `{user_input}`"


# ── Render Trade History Table ─────────────────────────────────────────────────
def render_trade_history():
    trades = st.session_state.paper_trades
    if not trades:
        st.info("No trades yet. Start with a command like `Buy 10 AAPL`")
        return

    df = pd.DataFrame(trades[::-1])  # newest first
    cols = ["time", "action", "symbol", "qty", "price", "total"]
    if "pnl" in df.columns:
        cols.append("pnl")
    df = df[[c for c in cols if c in df.columns]]
    df.columns = [c.upper() for c in df.columns]
    if "PRICE" in df.columns:
        df["PRICE"] = df["PRICE"].apply(lambda x: f"₹{x:,.4f}")
    if "TOTAL" in df.columns:
        df["TOTAL"] = df["TOTAL"].apply(lambda x: f"₹{x:,.2f}")
    if "PNL" in df.columns:
        df["PNL"] = df["PNL"].apply(lambda x: f"₹{x:+,.2f}")

    st.dataframe(df, use_container_width=True, hide_index=True)


# ── Main Render Function ───────────────────────────────────────────────────────
def render_trading_agent():
    init_trading_state()

    st.markdown("""
    <div style="background:linear-gradient(135deg,#0d1117,#161b22);border:1px solid #30363d;
    border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:1rem;">
        <div style="font-size:1.3rem;font-weight:800;color:#58a6ff;">🤖 AI Trading Agent</div>
        <div style="color:#8b949e;font-size:0.85rem;margin-top:0.2rem;">
        Chat se command do — Agent live price fetch karke paper trade execute karega
        </div>
        <div style="margin-top:0.6rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
            <span style="background:#1a3a1a;color:#3fb950;padding:0.2rem 0.6rem;border-radius:20px;font-size:0.72rem;">✅ Paper Trading Only</span>
            <span style="background:#1a2535;color:#58a6ff;padding:0.2rem 0.6rem;border-radius:20px;font-size:0.72rem;">💵 Virtual ₹1,00,000</span>
            <span style="background:#2d1a1a;color:#f85149;padding:0.2rem 0.6rem;border-radius:20px;font-size:0.72rem;">⚠️ No Real Money</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Balance Bar ────────────────────────────────────────────────────────────
    bal = st.session_state.paper_balance
    trades_count = len(st.session_state.paper_trades)
    holdings_count = len(st.session_state.paper_portfolio)

    b1, b2, b3 = st.columns(3)
    with b1:
        st.metric("💵 Cash Balance", f"₹{bal:,.0f}")
    with b2:
        st.metric("📂 Open Positions", holdings_count)
    with b3:
        st.metric("📋 Total Trades", trades_count)

    st.markdown("---")

    # ── Chat Interface ─────────────────────────────────────────────────────────
    chat_col, port_col = st.columns([3, 2])

    with chat_col:
        st.markdown("#### 💬 Command Chat")

        # Quick command buttons
        st.markdown("**⚡ Quick Commands:**")
        qc = st.columns(4)
        quick_cmds = [
            ("📊 Portfolio", "portfolio"),
            ("🟢 Buy BTC", "Buy 1 BTC"),
            ("🔴 Sell BTC", "Sell 1 BTC"),
            ("📈 Check AAPL", "Check AAPL"),
        ]
        for i, (label, cmd) in enumerate(quick_cmds):
            with qc[i]:
                if st.button(label, key=f"qcmd_{i}", use_container_width=True):
                    st.session_state.chat_history.append({
                        "role": "user", "content": cmd,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    with st.spinner("Agent processing..."):
                        response = process_command(cmd)
                    st.session_state.chat_history.append({
                        "role": "agent", "content": response,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    st.rerun()

        # Chat history display
        chat_container = st.container()
        with chat_container:
            history = st.session_state.chat_history[-20:]  # last 20 messages
            if not history:
                st.markdown("""
                <div style="text-align:center;padding:2rem;color:#8b949e;border:1px dashed #30363d;border-radius:8px;">
                    <div style="font-size:2rem;">🤖</div>
                    <p>Agent ready! Type a command below.</p>
                    <p style="font-size:0.8rem;">Examples: <code>Buy 10 AAPL</code> · <code>Buy 5 BTC</code> · <code>Portfolio</code></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                for msg in history:
                    if msg["role"] == "user":
                        st.markdown(f"""
                        <div style="display:flex;justify-content:flex-end;margin:0.4rem 0;">
                            <div style="background:#1a3a1a;border:1px solid #3fb950;border-radius:12px 12px 2px 12px;
                            padding:0.6rem 1rem;max-width:80%;color:#e6edf3;font-size:0.88rem;">
                                <b>You</b> · <span style="color:#8b949e;font-size:0.75rem;">{msg['time']}</span><br>
                                {msg['content']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        content_html = msg['content'].replace('\n', '<br>').replace('**', '<b>').replace('**', '</b>')
                        # Simple bold fix
                        import re as _re
                        content_html = _re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', msg['content'].replace('\n', '<br>'))
                        content_html = content_html.replace('`', '<code>').replace('`', '</code>')
                        st.markdown(f"""
                        <div style="display:flex;justify-content:flex-start;margin:0.4rem 0;">
                            <div style="background:#161b22;border:1px solid #30363d;border-radius:12px 12px 12px 2px;
                            padding:0.6rem 1rem;max-width:90%;color:#e6edf3;font-size:0.85rem;">
                                <b style="color:#58a6ff;">🤖 Agent</b> · <span style="color:#8b949e;font-size:0.75rem;">{msg['time']}</span><br><br>
                                {content_html}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

        # Input
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input(
                "Command",
                placeholder="e.g. Buy 10 AAPL | Sell 5 BTC | Portfolio | Check RELIANCE.NS",
                label_visibility="collapsed"
            )
            submitted = st.form_submit_button("🚀 Execute", type="primary", use_container_width=True)

            if submitted and user_input.strip():
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input.strip(),
                    "time": datetime.now().strftime("%H:%M")
                })
                with st.spinner("🤖 Agent processing..."):
                    response = process_command(user_input.strip())
                st.session_state.chat_history.append({
                    "role": "agent",
                    "content": response,
                    "time": datetime.now().strftime("%H:%M")
                })
                st.rerun()

    # ── Portfolio Panel ────────────────────────────────────────────────────────
    with port_col:
        st.markdown("#### 📂 Live Portfolio")

        port = st.session_state.paper_portfolio
        if not port:
            st.markdown("""
            <div style="text-align:center;padding:1.5rem;color:#8b949e;border:1px dashed #30363d;border-radius:8px;">
                <div style="font-size:1.8rem;">📂</div>
                <p>No holdings yet</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            total_pnl = 0
            for sym, info in port.items():
                price, _, err = get_live_price(sym, info["type"])
                if err or not price:
                    price = info["avg_price"]
                pnl = (price - info["avg_price"]) * info["qty"]
                pnl_pct = ((price - info["avg_price"]) / info["avg_price"] * 100) if info["avg_price"] else 0
                total_pnl += pnl
                icon = "🟢" if pnl >= 0 else "🔴"
                st.markdown(f"""
                <div style="background:#161b22;border:1px solid {'#238636' if pnl>=0 else '#da3633'};
                border-radius:8px;padding:0.7rem;margin-bottom:0.5rem;">
                    <div style="font-weight:700;color:#e6edf3;">{icon} {sym}</div>
                    <div style="font-size:0.78rem;color:#8b949e;">{info['qty']} units @ ₹{info['avg_price']:,.4f}</div>
                    <div style="font-size:0.82rem;color:#e6edf3;">LTP: ₹{price:,.4f}</div>
                    <div style="font-size:0.85rem;font-weight:600;color:{'#3fb950' if pnl>=0 else '#f85149'};">
                        P&L: ₹{pnl:+,.2f} ({pnl_pct:+.2f}%)
                    </div>
                </div>
                """, unsafe_allow_html=True)

            pnl_color = "#3fb950" if total_pnl >= 0 else "#f85149"
            st.markdown(f"""
            <div style="background:#0d1117;border:1px solid #58a6ff;border-radius:8px;padding:0.8rem;text-align:center;">
                <div style="color:#8b949e;font-size:0.8rem;">Total P&L</div>
                <div style="font-size:1.3rem;font-weight:800;color:{pnl_color};">₹{total_pnl:+,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        # Reset button
        if st.button("🔄 Reset Portfolio (₹1L)", key="reset_port", use_container_width=True):
            st.session_state.paper_portfolio = {}
            st.session_state.paper_trades = []
            st.session_state.paper_balance = 100000.0
            st.session_state.chat_history = []
            st.rerun()

    # ── Trade History ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📋 Trade History")
    render_trade_history()

    # ── Disclaimer ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#1a1a00;border:1px solid #d29922;border-radius:8px;padding:0.8rem;
    margin-top:1rem;font-size:0.78rem;color:#d29922;">
    ⚠️ <b>PAPER TRADING DISCLAIMER:</b> This is a virtual trading simulation using real market data.
    No real money is involved. All trades are simulated for educational purposes only.
    Past performance does not guarantee future results. Not SEBI-registered investment advice.
    </div>
    """, unsafe_allow_html=True)
