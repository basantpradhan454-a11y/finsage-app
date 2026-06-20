"""
FinsageAI — Finsage Academy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Interactive AI Trading Education Platform
Level 1 (Basics) → Level 2 (Intermediate) → Level 3 (Advanced)
Quiz-based learning · AI Teacher · TradingView charts · Gamification
"""

import streamlit as st
import requests
import os
import json
import random
from datetime import datetime
import streamlit.components.v1 as components

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _get_key() -> str:
    k = os.environ.get("GEMINI_API_KEY", "")
    if not k:
        try: k = st.secrets.get("GEMINI_API_KEY", "")
        except Exception: pass
    return k or ""

def _call_gemini(prompt: str, max_tokens: int = 2000) -> str:
    api_key = _get_key()
    if not api_key:
        return "⚠️ Add `GEMINI_API_KEY` to Streamlit secrets to enable AI Teacher."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": max_tokens},
        "systemInstruction": {
            "parts": [{"text": (
                "You are FinsageAI Academy Teacher — an expert trading coach. "
                "Your ONLY goal is to TEACH technical analysis concepts step-by-step. "
                "You NEVER give buy/sell signals for specific stocks. "
                "You NEVER say 'Buy X now' or 'Sell Y today'. "
                "You explain CONCEPTS using historical/simulated examples. "
                "You always use simple language first, then technical terms. "
                "You treat every student as a curious beginner even if they know some things. "
                "End every lesson with 1 quiz question to check understanding."
            )}]
        }
    }
    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"❌ Error: {str(e)}"

def _call_gemini_vision(prompt: str, image_b64: str, mime: str = "image/jpeg") -> str:
    import base64
    api_key = _get_key()
    if not api_key:
        return "⚠️ Add `GEMINI_API_KEY` to Streamlit secrets."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": mime, "data": image_b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 3000},
        "systemInstruction": {
            "parts": [{"text": (
                "You are FinsageAI Academy Teacher. Analyze chart images for EDUCATIONAL purposes only. "
                "Describe what patterns, indicators, and conditions you see. "
                "NEVER say 'Buy X now' — always say 'This CONDITION historically triggers a momentum strategy'. "
                "Frame everything as learning material, not financial advice."
            )}]
        }
    }
    try:
        r = requests.post(url, json=payload, timeout=90)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ─────────────────────────────────────────────────────────────────────────────
# CURRICULUM DATA
# ─────────────────────────────────────────────────────────────────────────────
CURRICULUM = {
    "🟢 Level 1 — Basics": {
        "color": "#3fb950",
        "badge": "🥉 Beginner",
        "chapters": [
            {
                "id": "L1C1", "title": "Stock Market Kaise Kaam Karta Hai?",
                "emoji": "📈",
                "summary": "Market structure, buyers/sellers, price discovery, NSE vs BSE vs Crypto",
                "key_concepts": ["Bull Market", "Bear Market", "Market Cap", "Bid/Ask Spread"],
                "quiz": {
                    "q": "Agar ek stock ka price ₹100 se badhkar ₹150 ho jaata hai, toh yeh kaisa market hai?",
                    "options": ["Bear Market", "Bull Market", "Sideways Market", "Crash"],
                    "answer": 1,
                    "explanation": "Bull Market = prices oopar jaate hain (jaise bull apne seengh se oopar uthata hai 🐂). Bear Market = prices neeche girte hain (jaise bear apne panje se neeche marta hai 🐻)."
                }
            },
            {
                "id": "L1C2", "title": "Candlestick Charts — Ye Kya Hoti Hain?",
                "emoji": "🕯️",
                "summary": "Open, High, Low, Close. Green vs Red candles. Body vs Wick. Timeframes.",
                "key_concepts": ["OHLC", "Bullish Candle", "Bearish Candle", "Wick/Shadow", "Timeframe"],
                "quiz": {
                    "q": "Ek candle ka Open ₹100, Close ₹120 hai. Yeh candle kaisi hogi?",
                    "options": ["Red / Bearish", "Green / Bullish", "Neutral / Doji", "Spinning Top"],
                    "answer": 1,
                    "explanation": "Jab Close > Open hota hai, candle GREEN (Bullish) hoti hai — matlab buyers ne sellers ko haraaya aur price oopar gayi. 🟢"
                }
            },
            {
                "id": "L1C3", "title": "Support & Resistance — Price ke Walls",
                "emoji": "🧱",
                "summary": "Why prices bounce at certain levels. Drawing S/R lines. Breakout vs Breakdown.",
                "key_concepts": ["Support Level", "Resistance Level", "Breakout", "Breakdown", "Role Reversal"],
                "quiz": {
                    "q": "Price bar bar ₹500 pe touch karke neeche aa jaati hai. Yeh level kya hai?",
                    "options": ["Support", "Resistance", "Stop Loss", "Take Profit"],
                    "answer": 1,
                    "explanation": "₹500 ek RESISTANCE level hai — yahan bahut zyada sellers hain jo price ko oopar nahi jaane dete. Socho iska ek ceiling ki tarah. 🚧"
                }
            },
        ]
    },
    "🟡 Level 2 — Intermediate": {
        "color": "#d29922",
        "badge": "🥈 Intermediate",
        "chapters": [
            {
                "id": "L2C1", "title": "RSI — Relative Strength Index",
                "emoji": "📊",
                "summary": "RSI formula, overbought/oversold, divergence. How to USE it (not misuse).",
                "key_concepts": ["RSI 30/70 levels", "Overbought", "Oversold", "Divergence", "False Signals"],
                "quiz": {
                    "q": "RSI 25 hai. Yeh kya signal deta hai (CONCEPT mein, specific stock nahi)?",
                    "options": ["Overbought zone — sellers ka pressure", "Oversold zone — potential buyers interest", "Neutral — no edge", "Crash signal"],
                    "answer": 1,
                    "explanation": "RSI < 30 = Oversold zone. Historically, jab RSI itna low hota hai, toh buyers interest dikhane lagte hain. Lekin SIRF RSI pe buy mat karo — confirm karo dusre indicators se bhi! ⚠️"
                }
            },
            {
                "id": "L2C2", "title": "MACD — Moving Average Convergence Divergence",
                "emoji": "📉",
                "summary": "EMA 12/26/9. Histogram. Signal line crossovers. Momentum measurement.",
                "key_concepts": ["MACD Line", "Signal Line", "Histogram", "Bullish Crossover", "Bearish Crossover"],
                "quiz": {
                    "q": "MACD line Signal line ke oopar cross karti hai. Historical context mein yeh kya condition create karta hai?",
                    "options": ["Bearish momentum increasing", "Bullish momentum condition — buyers gaining strength", "Price will definitely go up", "Sell signal"],
                    "answer": 1,
                    "explanation": "MACD above Signal = Bullish crossover condition. Yeh batata hai ki short-term momentum long-term se tez ho gayi hai. Remember: MACD lag wala indicator hai — always use it with price action! 📐"
                }
            },
            {
                "id": "L2C3", "title": "Volume Analysis — Market ki Asli Aawaz",
                "emoji": "📦",
                "summary": "Volume confirms price moves. High volume breakout vs low volume fake. OBV basics.",
                "key_concepts": ["Volume Spike", "Breakout Confirmation", "OBV", "Volume Divergence"],
                "quiz": {
                    "q": "Price oopar gayi lekin volume bahut kam tha. Yeh historical context mein kya suggest karta hai?",
                    "options": ["Strong breakout — enter immediately", "Weak move — possible fake breakout, wait for confirmation", "Perfect buy opportunity", "Guaranteed profit"],
                    "answer": 1,
                    "explanation": "Low volume + price move = Weak signal. Strong breakouts mein volume zyada hona chahiye. Yeh rule hai: 'Volume is the fuel that drives price moves.' ⛽"
                }
            },
        ]
    },
    "🔴 Level 3 — Advanced": {
        "color": "#f85149",
        "badge": "🥇 Advanced",
        "chapters": [
            {
                "id": "L3C1", "title": "Risk Management — Capital Bachana Hi Asli Trading Hai",
                "emoji": "🛡️",
                "summary": "Position sizing, R:R ratio, Kelly criterion, max drawdown, 1% rule.",
                "key_concepts": ["Risk:Reward Ratio", "Position Sizing", "Max Drawdown", "Kelly Criterion", "1% Rule"],
                "quiz": {
                    "q": "Ek trade mein ₹10,000 portfolio se max kitna risk lena chahiye (1% rule)?",
                    "options": ["₹5,000", "₹1,000", "₹100", "₹500"],
                    "answer": 2,
                    "explanation": "1% Rule = Portfolio ka sirf 1% ek trade mein risk karo. ₹10,000 × 1% = ₹100. Iska matlab yeh nahi ki aap sirf ₹100 lagao — aap zyada laga sakte ho lekin stop loss ₹100 pe rakho. 🎯"
                }
            },
            {
                "id": "L3C2", "title": "Trading Psychology — Mann Ko Control Karo",
                "emoji": "🧠",
                "summary": "FOMO, revenge trading, loss aversion, overconfidence, the disciplined trader mindset.",
                "key_concepts": ["FOMO", "Revenge Trading", "Loss Aversion", "Overconfidence Bias", "Trading Journal"],
                "quiz": {
                    "q": "Ek trade mein loss hua, aur tum turant double size mein dusra trade lete ho loss recover karne ke liye. Yeh kya hai?",
                    "options": ["Smart averaging", "Revenge Trading — bahut dangerous habit", "Dollar Cost Averaging", "Hedging"],
                    "answer": 1,
                    "explanation": "Revenge Trading = Emotion-driven trading. Ek loss ke baad emotional ho jaana aur larger position lena — yeh account barbad karne ka sabse fast tarika hai. Always take a break after a loss! 🛑"
                }
            },
            {
                "id": "L3C3", "title": "Algorithmic Trading Logic — Code Karo Apni Strategy",
                "emoji": "🤖",
                "summary": "How algo trading works. Strategy → Rule → Code → Backtest → Deploy. Pine Script basics.",
                "key_concepts": ["Strategy Rules", "Backtesting", "Overfitting", "Forward Testing", "Pine Script"],
                "quiz": {
                    "q": "Ek strategy 95% win rate backtesting mein dikhati hai. Live market mein kya hoga?",
                    "options": ["Definitely profitable — high win rate hai", "Likely overfitted — live performance will be much lower", "Perfect strategy", "Should deploy immediately"],
                    "answer": 1,
                    "explanation": "95% backtest win rate = Almost certainly OVERFITTED. Strategy ne historical data ko memorize kar liya, market ka actual pattern nahi seekha. Hamesha out-of-sample forward testing karo! 📉"
                }
            },
        ]
    }
}

# Scenario challenges for quiz
SCENARIO_CHALLENGES = [
    {
        "id": "SC1",
        "title": "Breakout ya Fake-out?",
        "tv_symbol": "BINANCE:BTCUSDT",
        "question": "Price ek strong resistance level ke upar close hui hai. Volume average se 3x zyada hai. Yeh scenario historically kya suggest karta hai?",
        "options": [
            "Fake breakout — hamesha neeche aata hai",
            "High-probability breakout condition — volume ne confirm kiya",
            "No edge — random movement",
            "Always short in this scenario"
        ],
        "answer": 1,
        "explanation": "High volume + price break above resistance = Classic breakout condition. Historical data mein yeh setup 60-65% times momentum continue karta hai. Lekin ALWAYS wait for candle close above resistance + volume confirmation. ✅",
        "points": 20
    },
    {
        "id": "SC2",
        "title": "RSI Divergence",
        "tv_symbol": "NASDAQ:AAPL",
        "question": "Price Higher High bana rahi hai lekin RSI Lower High bana raha hai. Yeh kya hai aur historical context mein kya suggest karta hai?",
        "options": [
            "Regular Bullish Divergence — buy signal",
            "Regular Bearish Divergence — momentum weakening, historically precedes pullback",
            "Hidden Bullish Divergence",
            "Normal RSI behavior — no signal"
        ],
        "answer": 1,
        "explanation": "Bearish Divergence = Price oopar ja rahi hai but momentum (RSI) ghatt raha hai. Historically, yeh condition often price pullback se pehle aati hai. It's a WARNING, not a guarantee. Always combine with other signals. ⚠️",
        "points": 25
    },
    {
        "id": "SC3",
        "title": "Support Level Test",
        "tv_symbol": "NSE:RELIANCE",
        "question": "Price apne strong historical support level par aa gayi hai — yahi level se 3 baar bounce ho chuki hai. Volume low hai. Historically kya hota hai?",
        "options": [
            "Always buy at support — guaranteed bounce",
            "Low volume support touch = weak demand, wait for volume confirmation before assuming bounce",
            "Always break below — sell immediately",
            "No significance — random level"
        ],
        "answer": 1,
        "explanation": "Support par low volume = Sellers nahi hain lekin buyers bhi forceful nahi hain. Wait karo ki price support pe hold kare AAND volume increase ho. Phir woh high-probability bounce condition ban jaata hai. 📊",
        "points": 30
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
def _init_academy():
    defaults = {
        "academy_points": 0,
        "academy_badges": [],
        "academy_completed": set(),
        "academy_chat_history": [],
        "academy_current_level": "🟢 Level 1 — Basics",
        "academy_quiz_answered": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# POINTS & BADGE SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
def _award_points(pts: int, reason: str):
    st.session_state["academy_points"] += pts
    st.toast(f"🎉 +{pts} points — {reason}!", icon="⭐")
    # Check badge thresholds
    total = st.session_state["academy_points"]
    badges = st.session_state["academy_badges"]
    if total >= 50  and "📚 Reader"        not in badges: badges.append("📚 Reader")
    if total >= 100 and "🎯 Sharp Mind"    not in badges: badges.append("🎯 Sharp Mind")
    if total >= 200 and "🏆 Market Scholar" not in badges: badges.append("🏆 Market Scholar")
    if total >= 300 and "💎 Elite Trader"  not in badges: badges.append("💎 Elite Trader")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────
def render_finsage_academy():
    _init_academy()

    # ── HERO ──────────────────────────────────────────────────────────────────
    pts    = st.session_state["academy_points"]
    badges = st.session_state["academy_badges"]
    comp   = len(st.session_state["academy_completed"])

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1117,#0a1628,#0d1117);
    border:1px solid rgba(88,166,255,0.2);border-radius:16px;
    padding:20px 24px;margin-bottom:16px;position:relative;overflow:hidden;">
      <div style="position:absolute;top:-30px;right:-30px;width:150px;height:150px;
      background:radial-gradient(circle,rgba(88,166,255,0.06),transparent 70%);"></div>
      <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
        <div style="font-size:36px;">🎓</div>
        <div>
          <div style="font-size:18px;font-weight:800;background:linear-gradient(90deg,#58a6ff,#3fb950);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          Finsage Academy — AI Trading School</div>
          <div style="color:#8b949e;font-size:12px;margin-top:3px;">
          Learn Technical Analysis · Interactive Quizzes · Earn Badges · AI Teacher
          </div>
        </div>
        <div style="margin-left:auto;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
          <div style="background:rgba(88,166,255,0.1);border:1px solid rgba(88,166,255,0.3);
          border-radius:10px;padding:8px 14px;text-align:center;">
            <div style="font-size:10px;color:#8b949e;text-transform:uppercase;">Points</div>
            <div style="font-size:20px;font-weight:900;color:#58a6ff;">{pts}</div>
          </div>
          <div style="background:rgba(63,185,80,0.1);border:1px solid rgba(63,185,80,0.3);
          border-radius:10px;padding:8px 14px;text-align:center;">
            <div style="font-size:10px;color:#8b949e;text-transform:uppercase;">Completed</div>
            <div style="font-size:20px;font-weight:900;color:#3fb950;">{comp}</div>
          </div>
        </div>
      </div>
      + ('<div style="margin-top:10px;">' + ''.join('<span style="background:rgba(88,166,255,0.1);border:1px solid rgba(88,166,255,0.3);border-radius:20px;padding:2px 10px;font-size:11px;color:#58a6ff;margin:2px;display:inline-block;">' + b + '</span>' for b in badges) + '</div>' if badges else '')
    </div>
    """, unsafe_allow_html=True)

    # ── DISCLAIMER ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:rgba(63,185,80,0.05);border:1px solid rgba(63,185,80,0.2);
    border-radius:8px;padding:8px 14px;margin-bottom:12px;font-size:11px;color:#8b949e;">
    📚 <b style="color:#3fb950;">Educational Platform:</b>
    Finsage Academy teaches trading CONCEPTS using historical & simulated data.
    <b>We do NOT provide buy/sell signals or investment advice.</b>
    Our AI Teacher explains conditions and patterns — you decide how to act.
    Not SEBI-registered. For educational purposes only.
    </div>
    """, unsafe_allow_html=True)

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab_ai_teacher, tab_scenarios, tab_vision = st.tabs([
        "🤖 AI Teacher",
        "🎯 Scenario Challenges",
        "🔬 Vision-to-Strategy Lab",
    ])

    with tab_ai_teacher:
        st.markdown("#### 🤖 Ask the AI Teacher Anything")
        st.markdown(
            "Koi bhi trading concept poochho — simple language mein samjhayega. "
            "**No buy/sell signals** — sirf education."
        )

        # Chat history
        for msg in st.session_state["academy_chat_history"]:
            role = "user" if msg["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.markdown(msg["content"])

        # Quick question chips
        st.markdown("**💡 Quick Questions:**")
        quick_qs = [
            "Candlestick patterns ke top 5 kaunse hain?",
            "RSI aur MACD mein kya farak hai?",
            "Stop Loss kaha lagaun?",
            "Breakout trade kaise identify karein?",
            "Market cap kya hota hai?",
            "Support level kaise draw karein?",
        ]
        qcols = st.columns(3)
        for i, q in enumerate(quick_qs):
            with qcols[i % 3]:
                if st.button(q, key=f"aq_{i}", use_container_width=True):
                    st.session_state["academy_chat_history"].append({"role": "user", "content": q})
                    with st.spinner("AI Teacher thinking…"):
                        resp = _call_gemini(f"Student question: {q}\n\nTeach this concept step-by-step with a real-world example.")
                    st.session_state["academy_chat_history"].append({"role": "assistant", "content": resp})
                    _award_points(5, "Question asked")
                    st.rerun()

        # Text input
        user_input = st.chat_input("Apna sawaal type karo… (e.g. 'RSI kya hota hai?')")
        if user_input:
            st.session_state["academy_chat_history"].append({"role": "user", "content": user_input})
            with st.spinner("🤖 AI Teacher answering…"):
                resp = _call_gemini(f"Student question: {user_input}\n\nTeach this clearly with examples.")
            st.session_state["academy_chat_history"].append({"role": "assistant", "content": resp})
            _award_points(5, "Question asked")
            st.rerun()

        if st.button("🗑️ Clear Chat", key="ac_clear"):
            st.session_state["academy_chat_history"] = []
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: SCENARIO CHALLENGES
    # ══════════════════════════════════════════════════════════════════════════
    with tab_scenarios:
        st.markdown("#### 🎯 Real-Time Scenario Challenges")
        st.markdown(
            "Live TradingView charts dekhkar batao — kya pattern dikh raha hai? "
            "AI explain karega sahi answer aur reason."
        )

        for sc in SCENARIO_CHALLENGES:
            sc_id   = sc["id"]
            done_sc = st.session_state["academy_quiz_answered"].get(sc_id)

            with st.expander(
                f"{'✅' if done_sc else '🎯'} Challenge: {sc['title']} — {sc['points']} pts",
                expanded=not done_sc
            ):
                # TradingView mini chart
                tv_html = f"""
                <div style="border-radius:10px;overflow:hidden;margin-bottom:12px;">
                <div class="tradingview-widget-container" style="height:320px;">
                  <div class="tradingview-widget-container__widget" style="height:288px;width:100%;"></div>
                  <script type="text/javascript"
                    src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
                  {{
                    "autosize": true, "symbol": "{sc['tv_symbol']}",
                    "interval": "D", "timezone": "Asia/Kolkata",
                    "theme": "dark", "style": "1", "locale": "en",
                    "studies": ["RSI@tv-basicstudies","Volume@tv-basicstudies"],
                    "show_popup_button": false
                  }}
                  </script>
                </div></div>
                """
                components.html(tv_html, height=340, scrolling=False)

                st.markdown(f"**❓ {sc['question']}**")

                if done_sc is None:
                    sel = st.radio(
                        "Apna jawab chunno:",
                        sc["options"],
                        key=f"sc_radio_{sc_id}",
                        index=None
                    )
                    if st.button("✅ Submit Answer", key=f"sc_submit_{sc_id}", type="primary"):
                        if sel is None:
                            st.warning("Pehle ek option choose karo!")
                        else:
                            chosen_idx = sc["options"].index(sel)
                            correct = chosen_idx == sc["answer"]
                            st.session_state["academy_quiz_answered"][sc_id] = {
                                "correct": correct,
                                "chosen": sel
                            }
                            if correct:
                                _award_points(sc["points"], f"Scenario '{sc['title']}' correct!")
                                st.session_state["academy_completed"].add(sc_id)
                            st.rerun()

                elif done_sc:
                    correct = done_sc["correct"]
                    chosen  = done_sc["chosen"]
                    correct_ans = sc["options"][sc["answer"]]
                    if correct:
                        st.success(f"✅ Bilkul sahi! +{sc['points']} points earned!")
                    else:
                        st.error(f"❌ Galat. Tumhara answer: *{chosen}*")
                        st.info(f"✅ Sahi jawab: **{correct_ans}**")
                    st.markdown(f"**📖 Explanation:** {sc['explanation']}")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4: VISION-TO-STRATEGY LAB
    # ══════════════════════════════════════════════════════════════════════════
    with tab_vision:
        st.markdown("#### 🔬 Vision-to-Strategy Lab")
        st.markdown(
            "Chart screenshot upload karo → AI **educational analysis** karega → "
            "**Conditions** identify karega (sirf signals nahi) → "
            "Strategy **logic** aur **backtest simulation** show karega."
        )

        st.markdown("""
        <div style="background:rgba(88,166,255,0.05);border:1px solid rgba(88,166,255,0.2);
        border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:12px;">
        ⚠️ <b style="color:#58a6ff;">Safe AI Analysis:</b>
        AI will describe <b>CONDITIONS</b> it sees (e.g., "breakout condition at ₹2500").
        It will NEVER say "Buy this stock now". Results are for learning only.
        Automated backtest shows historical win rates on similar conditions.
        </div>
        """, unsafe_allow_html=True)

        col_up, col_prev = st.columns([1, 1])
        with col_up:
            uploaded = st.file_uploader(
                "Upload Chart Screenshot",
                type=["png", "jpg", "jpeg", "webp"],
                key="acad_upload",
                label_visibility="collapsed"
            )
            context = st.text_input(
                "Context (optional)",
                placeholder="e.g. 'RELIANCE daily chart' or 'BTC 1H looking for pattern'",
                key="acad_ctx"
            )
        with col_prev:
            if uploaded:
                st.image(uploaded, caption="Uploaded Chart", use_column_width=True)
            else:
                st.markdown(
                    '<div style="border:2px dashed #30363d;border-radius:12px;height:180px;'
                    'display:flex;align-items:center;justify-content:center;color:#8b949e;font-size:13px;">'
                    '🖼️ Chart preview</div>',
                    unsafe_allow_html=True
                )

        if uploaded:
            analyze_btn = st.button(
                "🔬 Analyze Chart — Educational Breakdown",
                use_container_width=True,
                type="primary",
                key="acad_analyze"
            )
            if analyze_btn:
                import base64
                img_bytes = uploaded.read()
                img_b64   = base64.b64encode(img_bytes).decode()
                mime      = "image/png" if uploaded.name.lower().endswith(".png") else "image/jpeg"

                prompt = f"""You are an expert trading EDUCATOR analyzing this chart for a student.

Context: {context if context else 'General chart analysis'}

Your task is to EDUCATE, not to give investment advice.

## 📊 Educational Chart Analysis

### 1. What I See (Objective Facts)
List every visual element: indicators visible, price structure, candle patterns, volume behavior.
Use factual language: "The chart shows..." not "You should..."

### 2. Conditions Identified (Not Signals)
Describe conditions using educational language:
- CORRECT: "This shows a breakout CONDITION at [level]. Historically, when this condition forms..."
- WRONG: "Buy now at [price]"
For each condition: name it, define it, explain what it means historically.

### 3. Strategy Logic (Rules, Not Advice)
Convert conditions into IF-THEN rules a student can learn from:
- "IF [condition A] AND [condition B] THEN [historical outcome pattern]"
- Example: "IF RSI crosses below 30 AND price touches support THEN historically this combination has shown mean-reversion tendency"

### 4. What Would Backtest Show?
If a student backtested this exact set of conditions on historical data, what win rate and R:R ratio would be typical? Give an educational estimate based on well-known academic research on these patterns.

### 5. Learning Summary
3 key things this chart teaches. What would you ask a student to identify here?

Remember: NEVER say buy/sell. Always frame as "conditions", "historical patterns", "what research shows"."""

                with st.spinner("🔬 AI analyzing chart for educational breakdown…"):
                    result = _call_gemini_vision(prompt, img_b64, mime)
                    st.session_state["acad_vision_result"] = result
                    _award_points(15, "Vision analysis completed")

        if st.session_state.get("acad_vision_result"):
            st.markdown("---")
            st.markdown("### 📋 Educational Analysis Report")
            st.markdown(
                '<div style="background:rgba(13,17,23,0.9);border:1px solid rgba(88,166,255,0.2);'
                'border-left:3px solid #58a6ff;border-radius:12px;padding:20px 24px;line-height:1.8;">',
                unsafe_allow_html=True
            )
            st.markdown(st.session_state["acad_vision_result"])
            st.markdown("</div>", unsafe_allow_html=True)

            # Convert to strategy button
            if st.button("⚙️ Convert to Strategy Rules & Backtest →", key="acad_to_bt", type="primary"):
                with st.spinner("Converting analysis to strategy rules…"):
                    bt_prompt = f"""Based on this educational chart analysis:

{st.session_state['acad_vision_result']}

Convert the identified CONDITIONS into:

## 📐 Strategy Rules (Educational Format)

### Entry Conditions (IF-THEN logic)
Write 3-5 specific, backtestable rules in this format:
- IF [Indicator A] [condition] [value] AND [Indicator B] [condition] [value] THEN [historical tendency]

### Exit Conditions
- Stop Loss placement logic (structure-based)
- Take Profit levels (R:R based)

### Backtest Simulation (Historical Education)
If we ran these rules on 6 months of daily data for a major index/asset:
- Estimated win rate: [X%] — based on academic research on these specific patterns
- Typical R:R: [X:Y]
- Max drawdown estimate: [X%]
- Best market conditions for this strategy: [trending/ranging/volatile]

### What a Student Should Practice
3 specific exercises to internalize these rules using paper trading.

Remember: this is EDUCATIONAL simulation, not a guarantee of future performance."""
                    bt_result = _call_gemini(bt_prompt)
                    st.session_state["acad_bt_result"] = bt_result

            if st.session_state.get("acad_bt_result"):
                st.markdown("---")
                st.markdown("### 📊 Strategy Rules & Backtest Simulation")
                st.markdown(
                    '<div style="background:rgba(13,17,23,0.9);border:1px solid rgba(63,185,80,0.2);'
                    'border-left:3px solid #3fb950;border-radius:12px;padding:20px 24px;line-height:1.8;">',
                    unsafe_allow_html=True
                )
                st.markdown(st.session_state["acad_bt_result"])
                st.markdown("</div>", unsafe_allow_html=True)

                ts = datetime.now().strftime("%Y%m%d_%H%M")
                st.download_button(
                    "📥 Download Educational Report",
                    data=f"# Educational Chart Analysis\n\n{st.session_state['acad_vision_result']}\n\n---\n\n# Strategy Rules & Backtest\n\n{st.session_state['acad_bt_result']}",
                    file_name=f"FinsageAcademy_Report_{ts}.md",
                    mime="text/markdown",
                    key="acad_download"
                )


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER RENDER HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _render_chapter(chap: dict, color: str):
    # Back button
    if st.button("← Back to Chapters", key=f"back_chap_{chap['id']}", type="secondary"):
        st.session_state["academy_active_chapter"] = None
        st.rerun()

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(13,17,23,0.95),rgba(22,27,34,0.9));
    border:1px solid {color}44;border-left:3px solid {color};
    border-radius:12px;padding:20px 24px;margin:12px 0;">
    <div style="font-size:16px;font-weight:800;color:#e6edf3;margin-bottom:6px;">
    {chap['emoji']} {chap['title']}</div>
    </div>
    """, unsafe_allow_html=True)

    # AI-generated lesson
    lesson_key = f"lesson_{chap['id']}"
    if lesson_key not in st.session_state:
        with st.spinner(f"AI Teacher loading lesson: {chap['title']}…"):
            prompt = f"""Teach this trading concept to a beginner:

Topic: {chap['title']}
Key Concepts to cover: {', '.join(chap['key_concepts'])}
Summary: {chap['summary']}

Structure your lesson as:
1. **Simple Explanation** (1 paragraph, very simple language, Hindi/English mix ok)
2. **Real-World Example** (use a relatable everyday analogy first, then market example)
3. **How to Identify This** (step-by-step visual guide — what to look for on a chart)
4. **Common Mistakes** (what beginners get wrong, why it's dangerous)
5. **Pro Tip** (one advanced insight that separates good traders from average)

Keep it engaging, conversational, and educational. End with the quiz question already embedded."""
            lesson = _call_gemini(prompt, max_tokens=1500)
            st.session_state[lesson_key] = lesson

    st.markdown(st.session_state[lesson_key])

    # QUIZ
    st.markdown("---")
    st.markdown("**📝 Chapter Quiz — Test Your Understanding:**")
    quiz = chap["quiz"]
    quiz_key = f"quiz_answered_{chap['id']}"

    if quiz_key not in st.session_state:
        sel = st.radio(quiz["q"], quiz["options"], key=f"qr_{chap['id']}", index=None)
        if st.button("Submit Answer", key=f"qsub_{chap['id']}", type="primary"):
            if sel is None:
                st.warning("Pehle ek option select karo!")
            else:
                chosen_idx = quiz["options"].index(sel)
                correct    = chosen_idx == quiz["answer"]
                st.session_state[quiz_key] = {"correct": correct, "chosen": sel}
                if correct:
                    _award_points(10, f"Quiz correct: {chap['title']}")
                    st.session_state["academy_completed"].add(chap["id"])
                st.rerun()
    else:
        result = st.session_state[quiz_key]
        correct_ans = quiz["options"][quiz["answer"]]
        if result["correct"]:
            st.success("✅ Bilkul sahi! +10 points!")
            st.markdown(f"**📖** {quiz['explanation']}")
        else:
            st.error(f"❌ Galat. Tumhara jawab: *{result['chosen']}*")
            st.info(f"✅ Sahi jawab: **{correct_ans}**")
            st.markdown(f"**📖** {quiz['explanation']}")
