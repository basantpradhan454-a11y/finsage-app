"""
FinSage — AI Chat Support
Full-guide conversational AI. User types commands → agent auto-executes on TradingView (via URL scheme).
"""
import streamlit as st
import requests
import os
import json
import re
from datetime import datetime

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are FinSage AI — an expert trading analyst and coach.
When user asks to analyze an asset or set up a trade, you MUST:
1. Give full technical analysis in clear English
2. Provide exact Entry Price, Stop Loss, Target 1, Target 2, Target 3
3. Give step-by-step instructions for TradingView setup
4. Explain WHY each level is chosen
5. Mention risk/reward ratio and confidence level

Always output a structured JSON block at the END of your response like this:
```json
{
  "action": "analyze",
  "ticker": "RELIANCE",
  "exchange": "NSE",
  "tv_symbol": "NSE:RELIANCE",
  "entry": 2850,
  "stop_loss": 2780,
  "target1": 2950,
  "target2": 3050,
  "target3": 3200,
  "timeframe": "1D",
  "bias": "BUY",
  "confidence": 72,
  "indicators": ["RSI", "MACD", "BB"],
  "demo_trade": true
}
```
If user just asks a question (no trade setup needed), omit the JSON block.
Language: English only. Be specific with numbers."""

QUICK_QUESTIONS = [
    "🔍 Analyze RELIANCE and set up trade",
    "📊 Analyze TCS — entry, SL, targets",
    "₿ Analyze Bitcoin — full setup",
    "📈 Analyze NIFTY 50 movement",
    "❓ What does RSI above 70 mean?",
    "🛑 How to set a perfect stop loss?",
    "📉 What is MACD crossover signal?",
    "💡 Best indicator for swing trading?",
]


def _call_groq(messages: list) -> str:
    if not GROQ_API_KEY:
        return "⚠️ AI not configured. Please add GROQ_API_KEY to Streamlit secrets."
    try:
        resp = requests.post(GROQ_URL, headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }, json={
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": 1200,
            "temperature": 0.65
        }, timeout=35)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"⚠️ AI error ({resp.status_code}). Try again."
    except Exception as e:
        return f"⚠️ Connection error: {str(e)[:100]}"


def _extract_trade_json(text: str) -> dict | None:
    """Extract JSON trade setup block from AI response."""
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    return None


def _build_tv_url(trade: dict) -> str:
    """Build TradingView chart URL with symbol."""
    symbol = trade.get("tv_symbol", trade.get("ticker", "NASDAQ:AAPL"))
    return f"https://www.tradingview.com/chart/?symbol={symbol}"


def _build_tv_study_url(trade: dict) -> str:
    """Build TradingView URL with indicators pre-loaded via URL params."""
    symbol   = trade.get("tv_symbol", "NSE:RELIANCE")
    tf       = trade.get("timeframe", "1D")
    # TradingView supports ?symbol= and ?interval= params
    interval_map = {"1m":"1","5m":"5","15m":"15","30m":"30","1h":"60","4h":"240","1D":"D","1W":"W","1M":"M"}
    interval = interval_map.get(tf, "D")
    return f"https://www.tradingview.com/chart/?symbol={symbol}&interval={interval}"


def _render_trade_setup_card(trade: dict):
    """Render a beautiful trade setup execution card."""
    bias     = trade.get("bias", "BUY")
    bias_color = "#10b981" if bias == "BUY" else "#ef4444"
    conf     = trade.get("confidence", 70)
    conf_color = "#10b981" if conf >= 70 else "#F59E0B" if conf >= 50 else "#ef4444"
    ticker   = trade.get("ticker", "")
    entry    = trade.get("entry", 0)
    sl       = trade.get("stop_loss", 0)
    t1       = trade.get("target1", 0)
    t2       = trade.get("target2", 0)
    t3       = trade.get("target3", 0)
    tv_url   = _build_tv_study_url(trade)
    demo     = trade.get("demo_trade", False)
    indicators = trade.get("indicators", ["RSI","MACD","BB"])

    # Risk/Reward
    risk     = abs(entry - sl) if entry and sl else 0
    reward   = abs(t1 - entry) if entry and t1 else 0
    rr_ratio = round(reward / risk, 1) if risk > 0 else 0

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(15,23,42,0.98),rgba(11,18,35,0.98));
        border:1px solid rgba(0,242,254,0.3);border-radius:18px;padding:1.3rem;
        margin:0.8rem 0;box-shadow:0 8px 32px rgba(0,0,0,0.4);">

        <!-- Header -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
            <div style="display:flex;align-items:center;gap:0.8rem;">
                <div style="background:linear-gradient(135deg,#00F2FE,#00C6FF);
                    border-radius:10px;padding:0.5rem 0.8rem;
                    color:#fff;font-size:1rem;font-weight:900;">{ticker}</div>
                <div style="background:rgba({('16,185,129' if bias=='BUY' else '239,68,68')},0.15);
                    border:1px solid {bias_color};border-radius:8px;
                    padding:0.3rem 0.8rem;color:{bias_color};font-weight:800;font-size:0.9rem;">
                    {'📈 ' if bias=='BUY' else '📉 '}{bias}
                </div>
            </div>
            <div style="background:rgba({conf_color.replace('#','').upper()},0.1);
                border:1px solid {conf_color}44;border-radius:10px;padding:0.4rem 0.8rem;text-align:center;">
                <div style="color:{conf_color};font-size:1.1rem;font-weight:900;">{conf}%</div>
                <div style="color:#64748b;font-size:0.65rem;text-transform:uppercase;">Confidence</div>
            </div>
        </div>

        <!-- Price levels grid -->
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:0.5rem;margin-bottom:1rem;">
            <div style="background:rgba(0,242,254,0.08);border:1px solid rgba(0,242,254,0.25);
                border-radius:10px;padding:0.6rem;text-align:center;">
                <div style="color:#64748b;font-size:0.6rem;font-weight:700;text-transform:uppercase;">Entry</div>
                <div style="color:#00F2FE;font-size:0.92rem;font-weight:800;">{entry:,}</div>
            </div>
            <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);
                border-radius:10px;padding:0.6rem;text-align:center;">
                <div style="color:#64748b;font-size:0.6rem;font-weight:700;text-transform:uppercase;">Stop Loss</div>
                <div style="color:#ef4444;font-size:0.92rem;font-weight:800;">{sl:,}</div>
            </div>
            <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);
                border-radius:10px;padding:0.6rem;text-align:center;">
                <div style="color:#64748b;font-size:0.6rem;font-weight:700;text-transform:uppercase;">T1</div>
                <div style="color:#10b981;font-size:0.92rem;font-weight:800;">{t1:,}</div>
            </div>
            <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);
                border-radius:10px;padding:0.6rem;text-align:center;">
                <div style="color:#64748b;font-size:0.6rem;font-weight:700;text-transform:uppercase;">T2</div>
                <div style="color:#10b981;font-size:0.92rem;font-weight:800;">{t2:,}</div>
            </div>
            <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);
                border-radius:10px;padding:0.6rem;text-align:center;">
                <div style="color:#64748b;font-size:0.6rem;font-weight:700;text-transform:uppercase;">T3</div>
                <div style="color:#10b981;font-size:0.92rem;font-weight:800;">{t3:,}</div>
            </div>
        </div>

        <!-- Risk/Reward + Indicators -->
        <div style="display:flex;gap:0.8rem;margin-bottom:1rem;flex-wrap:wrap;">
            <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);
                border-radius:8px;padding:0.4rem 0.8rem;font-size:0.78rem;">
                <span style="color:#64748b;">Risk/Reward: </span>
                <span style="color:#F59E0B;font-weight:700;">1:{rr_ratio}</span>
            </div>
            {''.join(f'<div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);border-radius:8px;padding:0.4rem 0.8rem;font-size:0.78rem;color:#F59E0B;font-weight:600;">{ind}</div>' for ind in indicators)}
        </div>

        <!-- TradingView actions -->
        <div style="background:rgba(0,242,254,0.05);border:1px solid rgba(0,242,254,0.15);
            border-radius:12px;padding:0.8rem;margin-bottom:0.8rem;">
            <div style="color:#00F2FE;font-size:0.78rem;font-weight:700;margin-bottom:0.5rem;">
                📺 Auto-Setup on TradingView
            </div>
            <div style="color:#94a3b8;font-size:0.76rem;line-height:1.8;">
                1️⃣ Click <b style="color:#00C6FF;">Open TradingView</b> → Chart opens with <b>{trade.get("tv_symbol","")}</b><br>
                2️⃣ Add: <b style="color:#F59E0B;">{" + ".join(indicators)}</b> indicators from top toolbar<br>
                3️⃣ Set timeframe to <b style="color:#F59E0B;">{trade.get("timeframe","1D")}</b><br>
                4️⃣ Draw horizontal lines: 🔵 Entry <b>{entry}</b> · 🔴 SL <b>{sl}</b> · 🟢 T1 <b>{t1}</b> · T2 <b>{t2}</b> · T3 <b>{t3}</b><br>
                5️⃣ Right-click → <b>"Add Alert"</b> at entry price <b>{entry}</b> to get notified<br>
                {'6️⃣ Click <b style="color:#10b981;">Paper Trading</b> (top right) → Enter demo trade' if demo else ''}
            </div>
        </div>

        <!-- Buttons -->
        <div style="display:flex;gap:0.7rem;flex-wrap:wrap;">
            <a href="{tv_url}" target="_blank" style="text-decoration:none;">
                <div style="background:linear-gradient(135deg,#00F2FE,#00C6FF);color:#fff;
                    border-radius:10px;padding:0.5rem 1.1rem;font-size:0.82rem;font-weight:700;
                    box-shadow:0 4px 15px rgba(0,242,254,0.3);display:inline-flex;
                    align-items:center;gap:0.4rem;">
                    📺 Open TradingView
                </div>
            </a>
            <a href="https://www.tradingview.com/paper-trading/" target="_blank" style="text-decoration:none;">
                <div style="background:linear-gradient(135deg,#10b981,#059669);color:#fff;
                    border-radius:10px;padding:0.5rem 1.1rem;font-size:0.82rem;font-weight:700;
                    box-shadow:0 4px 15px rgba(16,185,129,0.3);display:inline-flex;
                    align-items:center;gap:0.4rem;">
                    🎮 Start Demo Trade
                </div>
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_ai_chat(analysis_context: dict = None):
    """Render the full AI Chat with TradingView automation."""

    if "ai_chat_messages" not in st.session_state:
        st.session_state.ai_chat_messages = []

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(0,242,254,0.1),rgba(245,158,11,0.1));
        border:1px solid rgba(0,242,254,0.25);border-radius:18px;padding:1.2rem 1.5rem;
        margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:1rem;">
            <div style="font-size:2rem;">🤖</div>
            <div style="flex:1;">
                <div style="font-size:1.1rem;font-weight:800;
                    background:linear-gradient(90deg,#00F2FE,#00C6FF,#F59E0B);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                    FinSage AI — Smart Trading Agent
                </div>
                <div style="color:#64748b;font-size:0.8rem;margin-top:0.2rem;">
                    Type any stock/crypto → AI analyzes + sets up TradingView automatically
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:0.4rem;">
                <div style="width:8px;height:8px;background:#10b981;border-radius:50%;
                    box-shadow:0 0 8px #10b981;"></div>
                <span style="color:#10b981;font-size:0.75rem;font-weight:600;">Live</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Context banner ────────────────────────────────────────────────────────
    if analysis_context and analysis_context.get("ticker"):
        ticker = analysis_context.get("ticker","")
        name   = analysis_context.get("name", ticker)
        price  = float(analysis_context.get("current_price") or 0)
        chg    = float(analysis_context.get("change_pct") or 0)
        chg_color = "#10b981" if chg >= 0 else "#ef4444"
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.2);
            border-radius:10px;padding:0.6rem 1rem;margin-bottom:0.8rem;
            display:flex;align-items:center;gap:1rem;">
            <span style="font-size:1.1rem;">📊</span>
            <span style="color:#e2e8f0;font-weight:700;font-size:0.88rem;">{name} ({ticker})</span>
            <span style="color:{chg_color};font-size:0.82rem;font-weight:600;">
                ₹{price:,.2f} &nbsp;{'▲' if chg>=0 else '▼'}{abs(chg):.2f}%
            </span>
            <span style="margin-left:auto;color:#64748b;font-size:0.72rem;">
                ✅ Context loaded — AI knows this asset
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── Quick Questions ───────────────────────────────────────────────────────
    if not st.session_state.ai_chat_messages:
        st.markdown('<div style="color:#64748b;font-size:0.75rem;font-weight:700;margin-bottom:0.5rem;text-transform:uppercase;letter-spacing:0.5px;">⚡ Quick Actions</div>', unsafe_allow_html=True)
        q_cols = st.columns(2)
        for qi, q in enumerate(QUICK_QUESTIONS):
            with q_cols[qi % 2]:
                if st.button(q, key=f"qq_{qi}", use_container_width=True):
                    st.session_state.ai_chat_messages.append({"role":"user","content":q})
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Chat messages ─────────────────────────────────────────────────────────
    for idx_msg, msg in enumerate(st.session_state.ai_chat_messages):
        if msg["role"] == "user":
            st.markdown(f"""
            <div style="display:flex;justify-content:flex-end;margin-bottom:0.6rem;">
                <div style="background:linear-gradient(135deg,#00F2FE,#00C6FF);color:#fff;
                    border-radius:16px 16px 4px 16px;padding:0.7rem 1rem;
                    max-width:72%;font-size:0.85rem;line-height:1.5;
                    box-shadow:0 4px 15px rgba(0,242,254,0.2);">
                    {msg['content']}
                </div>
                <div style="width:30px;height:30px;background:linear-gradient(135deg,#00F2FE,#F59E0B);
                    border-radius:50%;display:flex;align-items:center;justify-content:center;
                    margin-left:0.5rem;flex-shrink:0;font-size:0.9rem;margin-top:2px;">👤</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Strip JSON block from display text
            display_text = re.sub(r'```json.*?```', '', msg["content"], flags=re.DOTALL).strip()
            display_html = display_text.replace("\n", "<br>")

            st.markdown(f"""
            <div style="display:flex;margin-bottom:0.6rem;align-items:flex-start;">
                <div style="width:30px;height:30px;background:linear-gradient(135deg,#1E293B,#1e3a5f);
                    border:2px solid rgba(0,242,254,0.4);border-radius:50%;
                    display:flex;align-items:center;justify-content:center;
                    margin-right:0.5rem;flex-shrink:0;font-size:0.9rem;">🤖</div>
                <div style="background:rgba(15,23,42,0.9);border:1px solid rgba(30,41,59,0.6);
                    border-radius:4px 16px 16px 16px;padding:0.8rem 1rem;
                    max-width:80%;font-size:0.84rem;color:#CBD5E1;line-height:1.6;">
                    {display_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # If this AI message has a trade setup, render the card
            trade = _extract_trade_json(msg["content"])
            if trade:
                _render_trade_setup_card(trade)

    # ── Generate AI reply if last message is from user ────────────────────────
    msgs = st.session_state.ai_chat_messages
    if msgs and msgs[-1]["role"] == "user":
        with st.spinner("🤖 FinSage AI is analyzing & preparing TradingView setup..."):
            sys_msg = SYSTEM_PROMPT
            if analysis_context and analysis_context.get("ticker"):
                sys_msg += f"\n\nCURRENT CONTEXT: {analysis_context.get('name','')} ({analysis_context.get('ticker','')}), Price: {analysis_context.get('current_price',0)}, Change: {analysis_context.get('change_pct',0)}%"

            api_msgs = [{"role":"system","content":sys_msg}] + msgs[-12:]
            reply    = _call_groq(api_msgs)
            st.session_state.ai_chat_messages.append({"role":"assistant","content":reply})
            st.rerun()

    # ── Input ─────────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    inp_col, btn_col = st.columns([5, 1])
    with inp_col:
        user_input = st.text_input("",
            placeholder="Type: 'Analyze RELIANCE' or 'Set up BITCOIN trade with SL and targets'...",
            key="ai_chat_input", label_visibility="collapsed")
    with btn_col:
        send = st.button("Send 🚀", type="primary", use_container_width=True)

    if send and user_input.strip():
        st.session_state.ai_chat_messages.append({"role":"user","content":user_input.strip()})
        st.rerun()

    if st.session_state.ai_chat_messages:
        if st.button("🗑️ Clear Chat", key="clear_chat"):
            st.session_state.ai_chat_messages = []
            st.rerun()

