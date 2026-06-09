"""
FinSage — AI Chat Support
Full-guide conversational AI for trading questions.
"""
import streamlit as st
import requests
import os
import json
from datetime import datetime

GROQ_API_KEY = os.getenv("GROQ_API_KEY","")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are FinSage AI — an expert financial analyst and trading guide.
You help users understand stock markets, cryptocurrency, technical analysis, and trading strategies.
Always reply in simple, clear English. Structure your answers with:
- Clear explanation of the concept
- Real example with numbers when possible
- What action the user should take (Buy/Sell/Hold/Wait)
- Risk warning if applicable

You are knowledgeable about: NSE/BSE (Indian markets), NYSE/NASDAQ (US markets), 
Crypto markets, Technical Analysis (RSI, MACD, Bollinger Bands, Candlesticks),
Fundamental Analysis, Risk Management, Options & Futures basics.

Never give guaranteed profit promises. Always mention risk. Keep answers concise and actionable."""

QUICK_QUESTIONS = [
    "What does RSI above 70 mean?",
    "How to read a candlestick chart?",
    "What is a stop loss and how to set it?",
    "Explain Bollinger Bands simply",
    "When should I buy vs wait?",
    "What is support and resistance?",
    "How does MACD signal work?",
    "What is the safest way to invest in stocks?",
]


def _call_groq(messages: list) -> str:
    if not GROQ_API_KEY:
        return "⚠️ AI service not configured. Please add GROQ_API_KEY to secrets."
    try:
        resp = requests.post(GROQ_URL, headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }, json={
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": 800,
            "temperature": 0.7
        }, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"⚠️ AI error ({resp.status_code}). Try again."
    except Exception as e:
        return f"⚠️ Connection error: {str(e)[:100]}"


def render_ai_chat(analysis_context: dict = None):
    """Render the full AI Chat Support UI."""

    # Init session state
    if "ai_chat_messages" not in st.session_state:
        st.session_state.ai_chat_messages = []

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(99,179,237,0.12),rgba(154,117,234,0.12));
        border:1px solid rgba(99,179,237,0.25);border-radius:18px;padding:1.2rem 1.5rem;
        margin-bottom:1.2rem;display:flex;align-items:center;gap:1rem;">
        <div style="font-size:2rem;">🤖</div>
        <div>
            <div style="color:#e6edf3;font-size:1.1rem;font-weight:800;
                background:linear-gradient(90deg,#63b3ed,#9a75ea);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                FinSage AI Chat
            </div>
            <div style="color:#8b949e;font-size:0.8rem;margin-top:0.1rem;">
                Ask anything about stocks, crypto, charts, or trading strategy
            </div>
        </div>
        <div style="margin-left:auto;display:flex;align-items:center;gap:0.4rem;">
            <div style="width:8px;height:8px;background:#48bb78;border-radius:50%;
                box-shadow:0 0 6px #48bb78;animation:pulse 2s infinite;"></div>
            <span style="color:#48bb78;font-size:0.75rem;font-weight:600;">Live</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── If analysis context exists, show context card ─────────────────────────
    if analysis_context and analysis_context.get("ticker"):
        ticker = analysis_context.get("ticker","")
        name   = analysis_context.get("name", ticker)
        price  = analysis_context.get("current_price", 0)
        chg    = analysis_context.get("change_pct", 0)
        chg_color = "#48bb78" if chg >= 0 else "#fc8181"
        st.markdown(f"""
        <div style="background:rgba(72,187,120,0.07);border:1px solid rgba(72,187,120,0.2);
            border-radius:12px;padding:0.7rem 1rem;margin-bottom:1rem;
            display:flex;align-items:center;gap:1rem;">
            <div style="font-size:1.2rem;">📊</div>
            <div>
                <span style="color:#e6edf3;font-weight:700;font-size:0.88rem;">{name} ({ticker})</span>
                <span style="color:{chg_color};font-size:0.82rem;margin-left:0.8rem;">
                    ₹{price:,.2f} &nbsp; {'+' if chg>=0 else ''}{chg:.2f}%
                </span>
            </div>
            <span style="margin-left:auto;color:#8b949e;font-size:0.72rem;">
                Context loaded — ask about this asset!
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── Quick Questions ────────────────────────────────────────────────────────
    if not st.session_state.ai_chat_messages:
        st.markdown('<div style="color:#8b949e;font-size:0.78rem;font-weight:600;margin-bottom:0.5rem;text-transform:uppercase;letter-spacing:0.5px;">💡 Quick Questions</div>', unsafe_allow_html=True)
        q_cols = st.columns(2)
        for qi, q in enumerate(QUICK_QUESTIONS):
            with q_cols[qi % 2]:
                if st.button(q, key=f"qq_{qi}", use_container_width=True):
                    st.session_state.ai_chat_messages.append({"role":"user","content":q})
                    st.rerun()

    # ── Chat history ──────────────────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.ai_chat_messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style="display:flex;justify-content:flex-end;margin-bottom:0.7rem;">
                    <div style="background:linear-gradient(135deg,#63b3ed,#9a75ea);
                        color:#fff;border-radius:16px 16px 4px 16px;padding:0.7rem 1rem;
                        max-width:75%;font-size:0.85rem;line-height:1.5;
                        box-shadow:0 4px 15px rgba(99,179,237,0.25);">
                        {msg['content']}
                    </div>
                    <div style="width:32px;height:32px;background:linear-gradient(135deg,#63b3ed,#9a75ea);
                        border-radius:50%;display:flex;align-items:center;justify-content:center;
                        margin-left:0.5rem;flex-shrink:0;font-size:1rem;">👤</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Format AI reply - convert markdown-like to HTML
                content = msg["content"].replace("\n","<br>")
                st.markdown(f"""
                <div style="display:flex;margin-bottom:0.7rem;align-items:flex-start;">
                    <div style="width:32px;height:32px;background:linear-gradient(135deg,#1a1f2e,#2d3748);
                        border:2px solid rgba(99,179,237,0.4);border-radius:50%;
                        display:flex;align-items:center;justify-content:center;
                        margin-right:0.5rem;flex-shrink:0;font-size:1rem;">🤖</div>
                    <div style="background:rgba(22,27,34,0.9);border:1px solid rgba(48,54,61,0.6);
                        border-radius:4px 16px 16px 16px;padding:0.8rem 1rem;
                        max-width:80%;font-size:0.84rem;color:#c9d1d9;line-height:1.6;">
                        {content}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── If last message is from user, generate AI reply ───────────────────────
    msgs = st.session_state.ai_chat_messages
    if msgs and msgs[-1]["role"] == "user":
        with st.spinner("FinSage AI is analyzing..."):
            # Build context-aware system prompt
            sys_msg = SYSTEM_PROMPT
            if analysis_context and analysis_context.get("ticker"):
                sys_msg += f"\n\nCURRENT ANALYSIS CONTEXT:\nAsset: {analysis_context.get('name','')} ({analysis_context.get('ticker','')})\nPrice: {analysis_context.get('current_price',0)}\nChange 24h: {analysis_context.get('change_pct',0)}%\nMarket Cap: {analysis_context.get('market_cap',0)}"

            api_messages = [{"role":"system","content":sys_msg}] + msgs[-10:]  # last 10 msgs
            reply = _call_groq(api_messages)
            st.session_state.ai_chat_messages.append({"role":"assistant","content":reply})
            st.rerun()

    # ── Input box ─────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    input_col, btn_col = st.columns([5, 1])
    with input_col:
        user_input = st.text_input("",
            placeholder="Ask me anything about trading, charts, stocks...",
            key="ai_chat_input", label_visibility="collapsed")
    with btn_col:
        send = st.button("Send 🚀", type="primary", use_container_width=True)

    if send and user_input.strip():
        st.session_state.ai_chat_messages.append({"role":"user","content":user_input.strip()})
        st.rerun()

    # Clear chat button
    if st.session_state.ai_chat_messages:
        if st.button("🗑️ Clear Chat", key="clear_ai_chat"):
            st.session_state.ai_chat_messages = []
            st.rerun()

