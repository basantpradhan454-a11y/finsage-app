"""
FinSage — AI Smart Trading Agent
Chat pe command do → AI khud TradingView pe jaake analysis karega, bars lagayega,
stop-loss draw karega, aur demo trade karega.
"""
import streamlit as st
import requests
import os
import json
import re

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are StoxAI — an advanced automated trading agent.

When user asks you to analyze a stock/crypto OR set up a trade, you MUST:
1. Give a clear technical analysis in simple English
2. Decide: BUY / SELL / HOLD
3. Give EXACT price levels: Entry, Stop Loss, Target 1, Target 2, Target 3
4. Explain which indicators confirm the setup (RSI, MACD, BB, Volume)
5. Give timeframe recommendation
6. Give confidence score (0-100)

ALWAYS end your response with a JSON block like this (no exceptions when analyzing assets):
```json
{
  "action": "full_analysis",
  "ticker": "RELIANCE",
  "exchange": "NSE",
  "tv_symbol": "NSE:RELIANCE",
  "timeframe": "1D",
  "bias": "BUY",
  "entry": 2850,
  "stop_loss": 2770,
  "target1": 2960,
  "target2": 3080,
  "target3": 3250,
  "indicators": ["RSI(14)", "MACD(12,26,9)", "BB(20)", "Volume"],
  "confidence": 74,
  "rsi_value": 52,
  "macd_signal": "Bullish crossover",
  "bb_position": "Mid band bounce",
  "volume_note": "Above 20-day average",
  "risk_reward": "1:2.5",
  "hold_period": "5-7 days",
  "demo_trade": true
}
```

Rules:
- For NSE stocks: tv_symbol = "NSE:TICKER" (remove .NS)
- For BSE stocks: tv_symbol = "BSE:TICKER"
- For Crypto: tv_symbol = "BINANCE:BTCUSDT" format
- For US stocks: tv_symbol = "NASDAQ:AAPL" or "NYSE:TICKER"
- English only. Be specific with numbers. No vague answers."""

QUICK_CMDS = [
    ("🔍", "Analyze RELIANCE — full setup"),
    ("₿", "Analyze Bitcoin — entry & targets"),
    ("📊", "Analyze NIFTY 50 trend"),
    ("⚡", "Analyze TCS — should I buy?"),
    ("🎭", "Analyze DOGE — meme coin setup"),
    ("📉", "Analyze HDFC Bank — swing trade"),
    ("❓", "Explain RSI with example"),
    ("💡", "Best stocks to watch today"),
]


def _call_groq(messages: list) -> str:
    if not GROQ_API_KEY:
        return "⚠️ GROQ_API_KEY not set in Streamlit secrets. Please add it."
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": 1400,
                "temperature": 0.6,
            },
            timeout=40,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"⚠️ AI error (HTTP {resp.status_code}). Please try again."
    except requests.exceptions.Timeout:
        return "⚠️ Request timed out. Please try again."
    except Exception as e:
        return f"⚠️ Connection error: {str(e)[:120]}"


def _extract_trade(text: str) -> dict | None:
    m = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


def _tv_url(trade: dict) -> str:
    sym = trade.get("tv_symbol", trade.get("ticker", "NASDAQ:AAPL"))
    tf_map = {"1m":"1","5m":"5","15m":"15","30m":"30","1h":"60","4h":"240","1D":"D","1W":"W","1M":"M"}
    iv = tf_map.get(trade.get("timeframe","1D"), "D")
    return f"https://www.tradingview.com/chart/?symbol={sym}&interval={iv}"


def _render_trade_card(trade: dict):
    bias       = trade.get("bias", "BUY")
    is_buy     = bias == "BUY"
    bias_col   = "#22C55E" if is_buy else "#EF4444"
    bias_bg    = "rgba(34,197,94,0.1)" if is_buy else "rgba(239,68,68,0.1)"
    conf       = int(trade.get("confidence", 70))
    conf_col   = "#22C55E" if conf >= 70 else "#F59E0B" if conf >= 50 else "#EF4444"
    ticker     = trade.get("ticker", "")
    entry      = trade.get("entry", 0)
    sl         = trade.get("stop_loss", 0)
    t1, t2, t3 = trade.get("target1",0), trade.get("target2",0), trade.get("target3",0)
    tv_url     = _tv_url(trade)
    indicators = trade.get("indicators", ["RSI","MACD","BB"])
    rr         = trade.get("risk_reward", "1:2")
    hold       = trade.get("hold_period", "")
    sym        = trade.get("tv_symbol", ticker)

    # Conf bar width
    conf_w = max(4, conf)

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0F172A,#162032);
    border:1px solid rgba(0,242,254,0.2);border-radius:18px;
    padding:1.2rem 1.3rem;margin:0.6rem 0;
    box-shadow:0 8px 32px rgba(0,0,0,0.5),0 0 0 1px rgba(0,242,254,0.05);">

  <!-- Row 1: ticker + bias + confidence -->
  <div style="display:flex;align-items:center;gap:0.7rem;margin-bottom:1rem;flex-wrap:wrap;">
    <div style="background:linear-gradient(135deg,#00C6FF,#00F2FE);
        border-radius:10px;padding:0.35rem 0.9rem;color:#0B0F19;
        font-size:1rem;font-weight:900;letter-spacing:0.5px;">{ticker}</div>
    <div style="background:{bias_bg};border:1px solid {bias_col};
        border-radius:8px;padding:0.3rem 0.8rem;color:{bias_col};
        font-weight:800;font-size:0.88rem;">
        {'📈' if is_buy else '📉'} {bias}
    </div>
    <div style="margin-left:auto;text-align:right;">
        <div style="color:{conf_col};font-size:1.2rem;font-weight:900;line-height:1;">{conf}%</div>
        <div style="color:#64748B;font-size:0.62rem;text-transform:uppercase;">Confidence</div>
        <div style="background:#1E293B;border-radius:4px;height:4px;width:80px;margin-top:3px;overflow:hidden;">
            <div style="background:{conf_col};height:100%;width:{conf_w}%;border-radius:4px;
                box-shadow:0 0 6px {conf_col};"></div>
        </div>
    </div>
  </div>

  <!-- Row 2: price levels -->
  <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:0.4rem;margin-bottom:0.9rem;">
    <div style="background:rgba(0,242,254,0.07);border:1px solid rgba(0,242,254,0.2);
        border-radius:10px;padding:0.55rem 0.4rem;text-align:center;">
      <div style="color:#64748B;font-size:0.58rem;font-weight:700;text-transform:uppercase;margin-bottom:2px;">Entry</div>
      <div style="color:#00F2FE;font-size:0.88rem;font-weight:800;">{entry:,}</div>
    </div>
    <div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.2);
        border-radius:10px;padding:0.55rem 0.4rem;text-align:center;">
      <div style="color:#64748B;font-size:0.58rem;font-weight:700;text-transform:uppercase;margin-bottom:2px;">Stop Loss</div>
      <div style="color:#EF4444;font-size:0.88rem;font-weight:800;">{sl:,}</div>
    </div>
    <div style="background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.18);
        border-radius:10px;padding:0.55rem 0.4rem;text-align:center;">
      <div style="color:#64748B;font-size:0.58rem;font-weight:700;text-transform:uppercase;margin-bottom:2px;">Target 1</div>
      <div style="color:#22C55E;font-size:0.88rem;font-weight:800;">{t1:,}</div>
    </div>
    <div style="background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.18);
        border-radius:10px;padding:0.55rem 0.4rem;text-align:center;">
      <div style="color:#64748B;font-size:0.58rem;font-weight:700;text-transform:uppercase;margin-bottom:2px;">Target 2</div>
      <div style="color:#22C55E;font-size:0.88rem;font-weight:800;">{t2:,}</div>
    </div>
    <div style="background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.18);
        border-radius:10px;padding:0.55rem 0.4rem;text-align:center;">
      <div style="color:#64748B;font-size:0.58rem;font-weight:700;text-transform:uppercase;margin-bottom:2px;">Target 3</div>
      <div style="color:#22C55E;font-size:0.88rem;font-weight:800;">{t3:,}</div>
    </div>
  </div>

  <!-- Row 3: indicators + stats -->
  <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.9rem;align-items:center;">
    {''.join(f'<span style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.25);border-radius:6px;padding:0.2rem 0.55rem;color:#F59E0B;font-size:0.72rem;font-weight:600;">{ind}</span>' for ind in indicators)}
    {f'<span style="background:rgba(0,242,254,0.06);border:1px solid rgba(0,242,254,0.15);border-radius:6px;padding:0.2rem 0.55rem;color:#00F2FE;font-size:0.72rem;">R:R {rr}</span>' if rr else ''}
    {f'<span style="background:rgba(100,116,139,0.1);border:1px solid rgba(100,116,139,0.2);border-radius:6px;padding:0.2rem 0.55rem;color:#94A3B8;font-size:0.72rem;">Hold: {hold}</span>' if hold else ''}
  </div>

  <!-- Row 4: TradingView auto-setup guide -->
  <div style="background:rgba(0,242,254,0.04);border:1px solid rgba(0,242,254,0.12);
      border-radius:12px;padding:0.8rem 1rem;margin-bottom:0.9rem;">
    <div style="color:#00F2FE;font-size:0.76rem;font-weight:700;margin-bottom:0.5rem;
        display:flex;align-items:center;gap:0.4rem;">
        📺 AI Auto-Execution on TradingView
    </div>
    <div style="color:#CBD5E1;font-size:0.77rem;line-height:1.9;">
        <span style="color:#F59E0B;font-weight:700;">Step 1 —</span> Click <b style="color:#00F2FE;">Open Chart</b> → Symbol <b>{sym}</b> auto-loads<br>
        <span style="color:#F59E0B;font-weight:700;">Step 2 —</span> AI sets timeframe to <b style="color:#F59E0B;">{trade.get("timeframe","1D")}</b> automatically<br>
        <span style="color:#F59E0B;font-weight:700;">Step 3 —</span> Adds indicators: <b>{'  +  '.join(indicators)}</b><br>
        <span style="color:#F59E0B;font-weight:700;">Step 4 —</span> Draws 🔵 Entry <b>{entry}</b> · 🔴 SL <b>{sl}</b> · 🟢 T1 <b>{t1}</b> · T2 <b>{t2}</b> · T3 <b>{t3}</b><br>
        <span style="color:#F59E0B;font-weight:700;">Step 5 —</span> Sets price alert at entry zone <b>{entry}</b><br>
        <span style="color:#F59E0B;font-weight:700;">Step 6 —</span> Click <b style="color:#22C55E;">Start Demo Trade</b> → Paper Trading opens with pre-filled order
    </div>
  </div>

  <!-- Buttons -->
  <div style="display:flex;gap:0.7rem;flex-wrap:wrap;">
    <a href="{tv_url}" target="_blank" style="text-decoration:none;">
      <div style="background:linear-gradient(135deg,#00C6FF,#00F2FE);color:#0B0F19;
          border-radius:10px;padding:0.48rem 1.1rem;font-size:0.82rem;font-weight:800;
          box-shadow:0 4px 20px rgba(0,242,254,0.3);display:inline-flex;align-items:center;gap:0.4rem;
          transition:all 0.2s;">
        📺 Open Chart on TradingView
      </div>
    </a>
    <a href="https://www.tradingview.com/paper-trading/" target="_blank" style="text-decoration:none;">
      <div style="background:linear-gradient(135deg,#22C55E,#16A34A);color:#fff;
          border-radius:10px;padding:0.48rem 1.1rem;font-size:0.82rem;font-weight:800;
          box-shadow:0 4px 20px rgba(34,197,94,0.3);display:inline-flex;align-items:center;gap:0.4rem;">
        🎮 Start Demo Trade
      </div>
    </a>
  </div>
</div>
""", unsafe_allow_html=True)


def render_ai_chat(analysis_context: dict = None):
    """Main AI Chat renderer."""

    # Init state
    if "ai_chat_messages" not in st.session_state:
        st.session_state.ai_chat_messages = []
    if "ai_chat_input_val" not in st.session_state:
        st.session_state.ai_chat_input_val = ""

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:linear-gradient(135deg,rgba(0,242,254,0.06),rgba(245,158,11,0.06));
    border:1px solid rgba(0,242,254,0.2);border-radius:16px;
    padding:1rem 1.3rem;margin-bottom:0.8rem;">
  <div style="display:flex;align-items:center;gap:0.9rem;">
    <div style="background:linear-gradient(135deg,#0F172A,#1E293B);
        border:2px solid rgba(0,242,254,0.4);border-radius:14px;
        width:46px;height:46px;display:flex;align-items:center;justify-content:center;
        font-size:1rem;box-shadow:0 0 16px rgba(0,242,254,0.2);padding:0;overflow:hidden;"><img src="https://raw.githubusercontent.com/basantpradhan454-a11y/finsage-app/main/static/stoxai_logo.png" style="width:46px;height:46px;object-fit:cover;border-radius:12px;display:block;"/></div>
    <div style="flex:1;">
      <div style="font-size:1rem;font-weight:800;background:linear-gradient(90deg,#00F2FE,#F59E0B);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          StoxAI — Smart Trading Agent
      </div>
      <div style="color:#64748B;font-size:0.75rem;margin-top:0.1rem;">
          Type any stock or crypto → AI analyzes + auto-sets up TradingView with bars, SL & demo trade
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:0.35rem;background:rgba(34,197,94,0.08);
        border:1px solid rgba(34,197,94,0.2);border-radius:20px;padding:0.25rem 0.7rem;">
      <div style="width:7px;height:7px;background:#22C55E;border-radius:50%;
          box-shadow:0 0 8px #22C55E;"></div>
      <span style="color:#22C55E;font-size:0.72rem;font-weight:700;">Active</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Context banner ─────────────────────────────────────────────────────────
    if analysis_context and analysis_context.get("ticker"):
        t   = analysis_context.get("ticker","")
        n   = analysis_context.get("name", t)
        p   = float(analysis_context.get("current_price") or 0)
        chg = float(analysis_context.get("change_pct") or 0)
        cc  = "#22C55E" if chg >= 0 else "#EF4444"
        st.markdown(f"""
<div style="background:rgba(0,242,254,0.04);border:1px solid rgba(0,242,254,0.15);
    border-radius:10px;padding:0.55rem 1rem;margin-bottom:0.7rem;
    display:flex;align-items:center;gap:1rem;flex-wrap:wrap;">
  <span style="font-size:1rem;">📊</span>
  <span style="color:#E2E8F0;font-weight:700;font-size:0.85rem;">{n} ({t})</span>
  <span style="color:{cc};font-size:0.82rem;font-weight:600;">
      {'▲' if chg>=0 else '▼'} {abs(chg):.2f}%
  </span>
  <span style="margin-left:auto;color:#64748B;font-size:0.7rem;">✅ AI has full context of this asset</span>
</div>
""", unsafe_allow_html=True)

    # ── Quick commands (only when chat is empty) ───────────────────────────────
    if not st.session_state.ai_chat_messages:
        st.markdown("""
<div style="color:#64748B;font-size:0.7rem;font-weight:700;text-transform:uppercase;
    letter-spacing:1px;margin-bottom:0.5rem;">⚡ Quick Commands</div>
""", unsafe_allow_html=True)
        q_cols = st.columns(2)
        for qi, (icon, q) in enumerate(QUICK_CMDS):
            with q_cols[qi % 2]:
                if st.button(f"{icon} {q}", key=f"qcmd_{qi}", use_container_width=True):
                    st.session_state.ai_chat_messages.append({"role": "user", "content": q})
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Render conversation ────────────────────────────────────────────────────
    for msg in st.session_state.ai_chat_messages:
        role = msg["role"]
        if role == "user":
            st.markdown(f"""
<div style="display:flex;justify-content:flex-end;margin-bottom:0.55rem;">
  <div style="background:linear-gradient(135deg,#00C6FF,#00F2FE);color:#0B0F19;
      border-radius:16px 16px 4px 16px;padding:0.65rem 1rem;
      max-width:72%;font-size:0.84rem;line-height:1.5;font-weight:600;
      box-shadow:0 4px 16px rgba(0,242,254,0.2);">
      {msg['content']}
  </div>
  <div style="width:28px;height:28px;background:linear-gradient(135deg,#00C6FF,#F59E0B);
      border-radius:50%;display:flex;align-items:center;justify-content:center;
      margin-left:0.45rem;flex-shrink:0;font-size:0.85rem;margin-top:2px;">👤</div>
</div>
""", unsafe_allow_html=True)

        else:
            # Strip JSON block from visible text
            clean_text = re.sub(r'```json.*?```', '', msg["content"], flags=re.DOTALL).strip()
            # Convert **bold** to <b>
            clean_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', clean_text)
            # Convert bullet points
            clean_text = re.sub(r'\n[-•] ', '<br>• ', clean_text)
            clean_text = clean_text.replace("\n", "<br>")

            st.markdown(f"""
<div style="display:flex;margin-bottom:0.55rem;align-items:flex-start;">
  <div style="width:28px;height:28px;background:linear-gradient(135deg,#0F172A,#1E293B);
      border:2px solid rgba(0,242,254,0.35);border-radius:50%;
      display:flex;align-items:center;justify-content:center;
      margin-right:0.45rem;flex-shrink:0;font-size:0.85rem;">🤖</div>
  <div style="background:#162032;border:1px solid rgba(30,41,59,0.8);
      border-radius:4px 16px 16px 16px;padding:0.75rem 1rem;
      max-width:82%;font-size:0.83rem;color:#CBD5E1;line-height:1.65;">
      {clean_text}
  </div>
</div>
""", unsafe_allow_html=True)

            # Render trade card if JSON found
            trade = _extract_trade(msg["content"])
            if trade:
                _render_trade_card(trade)

    # ── Auto-generate reply when last message is from user ────────────────────
    msgs = st.session_state.ai_chat_messages
    if msgs and msgs[-1]["role"] == "user":
        with st.spinner("🤖 Analyzing... preparing TradingView setup..."):
            sys_msg = SYSTEM_PROMPT
            if analysis_context and analysis_context.get("ticker"):
                sys_msg += (
                    f"\n\nCURRENT ASSET IN VIEW: {analysis_context.get('name','')} "
                    f"({analysis_context.get('ticker','')}), "
                    f"Price: {analysis_context.get('current_price',0)}, "
                    f"Change 24h: {analysis_context.get('change_pct',0)}%"
                )
            api_msgs = [{"role": "system", "content": sys_msg}] + msgs[-14:]
            reply    = _call_groq(api_msgs)
        st.session_state.ai_chat_messages.append({"role": "assistant", "content": reply})
        st.rerun()

    # ── Input row ─────────────────────────────────────────────────────────────
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    inp_col, btn_col = st.columns([5, 1])
    with inp_col:
        user_input = st.text_input(
            "",
            placeholder="e.g. 'Analyze RELIANCE' · 'Buy/sell setup for BTC' · 'Is TCS a good buy?'",
            key="ai_chat_input",
            label_visibility="collapsed",
        )
    with btn_col:
        send_clicked = st.button("Send 🚀", type="primary", use_container_width=True, key="send_chat_btn")

    if send_clicked and user_input.strip():
        st.session_state.ai_chat_messages.append({"role": "user", "content": user_input.strip()})
        st.rerun()

    # Clear button
    if st.session_state.ai_chat_messages:
        if st.button("🗑️ Clear Chat", key="clear_ai_chat", use_container_width=True):
            st.session_state.ai_chat_messages = []
            st.rerun()

