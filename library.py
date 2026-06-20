"""
FinSage Library — Book Library + AI Book Assistant + FinSage Trading Mentor
All AI via Groq (llama-3.3-70b) — same as rest of FinSage
"""
import streamlit as st
import os
import requests
import time

# ═══════════════════════════════════════════════════════════════════
# 0. API HELPER — Groq (same as trading_learning.py)
# ═══════════════════════════════════════════════════════════════════
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

def _get_key(name: str) -> str:
    v = os.environ.get(name, "")
    if not v:
        try: v = st.secrets.get(name, "")
        except Exception: pass
    return v or ""

def _groq_key() -> str:
    return _get_key("GROQ_API_KEY") or _get_key("GROW_API_KEY")

def _call_groq(messages: list, max_tokens: int = 2000) -> str:
    k = _groq_key()
    if not k:
        return "⚠️ GROQ_API_KEY not set in Streamlit Secrets."
    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages,
                  "temperature": 0.65, "max_tokens": max_tokens},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ AI Error: {e}"

# ═══════════════════════════════════════════════════════════════════
# 1. BOOK DATA
# ═══════════════════════════════════════════════════════════════════
BOOKS = {
    "📊 Fundamental Analysis": [
        {"title":"Security Analysis","author":"Benjamin Graham & David Dodd",
         "level":"Advanced","level_color":"#ef4444",
         "tags":["Value Investing","Bonds","Stocks"],
         "description":"The bible of value investing — teaches how to analyze securities with discipline and margin of safety."},
        {"title":"The Intelligent Investor","author":"Benjamin Graham",
         "level":"Intermediate","level_color":"#f97316",
         "tags":["Value Investing","Mr. Market","Margin of Safety"],
         "description":"The most important investing book ever written — teaches how to think about markets and avoid emotional mistakes."},
        {"title":"Common Stocks and Uncommon Profits","author":"Philip Fisher",
         "level":"Intermediate","level_color":"#f97316",
         "tags":["Growth Investing","Scuttlebutt","Management"],
         "description":"Fisher's masterpiece on finding exceptional growth companies through qualitative research."},
        {"title":"One Up on Wall Street","author":"Peter Lynch",
         "level":"Beginner","level_color":"#22c55e",
         "tags":["Growth Investing","GARP","Everyday Investor"],
         "description":"Lynch shows how ordinary investors can beat Wall Street by investing in what they know."},
        {"title":"Financial Shenanigans","author":"Howard Schilit",
         "level":"Advanced","level_color":"#ef4444",
         "tags":["Accounting Fraud","Red Flags","Due Diligence"],
         "description":"How to detect accounting tricks and fraud before they destroy your portfolio."},
    ],
    "📈 Technical Analysis": [
        {"title":"Technical Analysis of the Financial Markets","author":"John J. Murphy",
         "level":"Intermediate","level_color":"#f97316",
         "tags":["Charts","Indicators","Trends"],
         "description":"The complete guide to technical analysis — the definitive reference for traders worldwide."},
        {"title":"Japanese Candlestick Charting Techniques","author":"Steve Nison",
         "level":"Beginner","level_color":"#22c55e",
         "tags":["Candlesticks","Patterns","Price Action"],
         "description":"The book that introduced candlestick charting to the Western world — essential for every trader."},
        {"title":"Encyclopedia of Chart Patterns","author":"Thomas N. Bulkowski",
         "level":"Advanced","level_color":"#ef4444",
         "tags":["Chart Patterns","Breakouts","Statistics"],
         "description":"A statistical deep-dive into every known chart pattern — backed by real data, not theory."},
        {"title":"How to Make Money in Stocks","author":"William J. O'Neil",
         "level":"Intermediate","level_color":"#f97316",
         "tags":["CANSLIM","Growth","Momentum"],
         "description":"O'Neil's CANSLIM system — combining fundamentals and technicals to find winning stocks."},
        {"title":"Trading for a Living","author":"Alexander Elder",
         "level":"Intermediate","level_color":"#f97316",
         "tags":["Psychology","Indicators","Risk Management"],
         "description":"A complete trading system covering psychology, tactics, and money management."},
    ],
    "🧠 Psychology & Philosophy": [
        {"title":"The Psychology of Money","author":"Morgan Housel",
         "level":"Beginner","level_color":"#22c55e",
         "tags":["Behavioral Finance","Wealth","Mindset"],
         "description":"19 timeless lessons about how people think about money — and how to think better."},
        {"title":"Market Wizards","author":"Jack D. Schwager",
         "level":"Intermediate","level_color":"#f97316",
         "tags":["Interviews","Trading Systems","Discipline"],
         "description":"Interviews with the world's greatest traders — revealing their methods and mindsets."},
        {"title":"Reminiscences of a Stock Operator","author":"Edwin Lefèvre",
         "level":"Beginner","level_color":"#22c55e",
         "tags":["Trading Psychology","Speculation","Classic"],
         "description":"The fictionalized biography of Jesse Livermore — the greatest stock trader in history."},
        {"title":"Trading in the Zone","author":"Mark Douglas",
         "level":"Intermediate","level_color":"#f97316",
         "tags":["Psychology","Discipline","Probability"],
         "description":"How to develop the mental edge needed to trade consistently and profitably."},
        {"title":"Fooled by Randomness","author":"Nassim Nicholas Taleb",
         "level":"Advanced","level_color":"#ef4444",
         "tags":["Probability","Luck vs Skill","Risk"],
         "description":"How randomness and luck play a far bigger role in markets than most investors realize."},
    ],
    "🇮🇳 Indian Market Context": [
        {"title":"Coffee Can Investing","author":"Saurabh Mukherjea, Rakshit Ranjan & Pranab Uniyal",
         "level":"Beginner","level_color":"#22c55e",
         "tags":["Indian Market","Long-term","Quality Stocks"],
         "description":"Buy great Indian businesses and hold them for 10+ years — a proven framework for Indian investors."},
        {"title":"Stocks to Riches","author":"Parag Parikh",
         "level":"Beginner","level_color":"#22c55e",
         "tags":["Indian Market","Behavioral Finance","Value"],
         "description":"Parag Parikh's insights on investor psychology and value investing in the Indian context."},
        {"title":"How to Avoid Loss and Earn Consistently","author":"Prasenjit Paul",
         "level":"Beginner","level_color":"#22c55e",
         "tags":["Indian Market","Beginners","Practical"],
         "description":"A practical guide for Indian retail investors on avoiding common mistakes and building wealth."},
    ],
    "⚙️ Specialized & Strategy": [
        {"title":"Options as a Strategic Investment","author":"Lawrence G. McMillan",
         "level":"Advanced","level_color":"#ef4444",
         "tags":["Options","Derivatives","Strategies"],
         "description":"The definitive guide to options trading strategies — comprehensive and deeply detailed."},
        {"title":"The Little Book of Common Sense Investing","author":"John C. Bogle",
         "level":"Beginner","level_color":"#22c55e",
         "tags":["Index Funds","Passive Investing","Long-term"],
         "description":"Bogle's simple but powerful case for index fund investing over active stock picking."},
    ],
}

# ═══════════════════════════════════════════════════════════════════
# 2. SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════════
BOOK_ASSISTANT_SYSTEM = """You are FinSage Library Assistant — an expert financial educator specializing in investment and trading books.

YOUR ROLE: When a user selects or asks about any book, provide a structured response:

1. 📖 BOOK OVERVIEW (2-3 lines): What this book is about and why it matters.
2. 💡 CORE PHILOSOPHY: The central idea or investment worldview the author teaches.
3. 🎯 KEY LESSONS (5-7 points): Most important takeaways, explained simply.
4. 🔑 FAMOUS CONCEPTS: Any frameworks, rules, or mental models.
5. 🇮🇳 INDIAN MARKET APPLICATION: How these lessons apply to NSE/BSE, Indian stocks, Indian investor mindset. Use Indian examples (Reliance, TCS, Infosys, Nifty 50, SIP, etc.).
6. 👤 WHO SHOULD READ THIS: Beginner / Intermediate / Advanced — what type of investor benefits most.
7. 💬 KEY INSIGHT: Capture the spirit of the book's most memorable idea in your own words — do NOT reproduce exact copyrighted text.
8. 📚 NEXT BOOK: Based on this book, suggest the next best book from the library and why.

LANGUAGE RULES: Detect user's language (Hindi, Hinglish, English) and respond in the same language.

BOUNDARIES: Never reproduce large passages or exact quotes. Always paraphrase. If asked for full book/PDF, decline and redirect to learning concepts.

TONE: Mentor-like, warm, practical, India-focused."""

MENTOR_SYSTEM = """You are FinSage Trading Mentor — an expert trading and investing educator who teaches through clear explanations, structured lessons, and visual storytelling.

DISCLAIMER (include at start of first message): "⚠️ Yeh sirf educational content hai. Koi bhi investment decision lene se pehle apne financial advisor se consult karein. FinSage koi SEBI-registered advisor nahi hai."

CURRICULUM YOU TEACH:
LEVEL 1 — BASICS: Stock Market kya hota hai, BSE/NSE, Shares, Broker/Demat, Market Timings, Bull/Bear Market, Index (Nifty/Sensex), Order Types
LEVEL 2 — FUNDAMENTAL ANALYSIS: Balance Sheet, P&L, Cash Flow, PE/PB/ROE/ROCE ratios, EPS, Sector Analysis, Moat, Management Quality
LEVEL 3 — TECHNICAL ANALYSIS: Candlestick Patterns, Chart Types, Support/Resistance, Trend Lines, Moving Averages, RSI/MACD/Bollinger Bands, Volume, Chart Patterns, Fibonacci
LEVEL 4 — TRADING STRATEGIES: Intraday, Swing, Positional, Long-term, Momentum, Breakout, Mean Reversion, CANSLIM
LEVEL 5 — RISK MANAGEMENT: Position Sizing, Risk-Reward, Stop Loss, Diversification, Capital Allocation, Drawdown, 2% Rule
LEVEL 6 — DERIVATIVES: Futures, Options, Call/Put, Strike Price/Expiry/Premium, Greeks, Option Strategies, F&O mistakes
LEVEL 7 — PSYCHOLOGY: Fear/Greed, FOMO, Revenge Trading, Confirmation Bias, Loss Aversion, Trading Journal, Discipline
LEVEL 8 — ADVANCED: Algo Trading, Quantitative Analysis, IPO Analysis, Mutual Funds vs Stocks, ETFs, Tax (STCG/LTCG/F&O)

TEACHING FORMAT — use this EVERY time you explain a concept:

[ANIMATION_START]
SCENE: {visual description — background, colors, elements}
VISUAL_ELEMENTS: {charts, graphs, arrows, icons}
[ANIMATION_END]

🎬 VISUAL STORY: {Simple relatable story — Indian context: Ramu kirana, Priya portfolio, etc.}

📊 ANIMATION SEQUENCE:
Step 1 → {what appears on screen}
Step 2 → {next frame}
...up to 8 steps

💡 CORE CONCEPT: {Simple explanation, max 5 lines}

🔢 FORMULA / RULE (if applicable): {Formula with Indian example — ₹, Nifty, Indian stocks}

🇮🇳 INDIAN EXAMPLE: {Real: Reliance, TCS, HDFC Bank, Infosys, SBI, Nifty 50}

✅ KEY TAKEAWAY: {One line — most important point}

⚠️ COMMON MISTAKE: {What beginners get wrong}

🔗 NEXT TOPIC: {Connected topic to study next}

Then ALWAYS end with:
❓ QUICK QUIZ:
Question: {concept-based}
A) B) C) D) {options}

INTERACTION RULES:
- First time: ask experience level → Beginner (Level 1) / Intermediate (Level 3-4) / Advanced (Level 6-8)
- ONE concept at a time. Ask "Kya samajh aaya? Aage badhein?" after each lesson.
- Celebrate correct quiz answers 🎉, gently correct wrong ones.
- Track progress: "Aapne aaj X concepts seekhe!"
- Always use Indian context, ₹ currency, NSE/BSE examples.

WHAT YOU NEVER DO:
❌ Specific stock tips ("yeh stock kharido")
❌ Guaranteed returns
❌ Complex jargon without explanation
❌ 5+ concepts at once
❌ SEBI-regulated advice

LANGUAGE: Match user's language — Hindi, Hinglish, or English."""

# ═══════════════════════════════════════════════════════════════════
# 3. CSS
# ═══════════════════════════════════════════════════════════════════
LIB_CSS = """
<style>
.book-card {
    background: linear-gradient(135deg, #0d1b2e, #111827);
    border: 1px solid #1e3a5f;
    border-radius: 14px; padding: 16px; margin-bottom: 12px;
    transition: all 0.25s ease;
}
.book-card:hover { border-color: #3b82f6; box-shadow: 0 0 16px rgba(59,130,246,0.18); }
.book-title { font-size: 14px; font-weight: 700; color: #e2e8f0; margin-bottom: 3px; }
.book-author { font-size: 11px; color: #64748b; margin-bottom: 6px; }
.book-desc { font-size: 12px; color: #94a3b8; line-height: 1.5; margin-bottom: 9px; }
.btag {
    display: inline-block; background: #1e2d45; color: #7dd3fc;
    font-size: 10px; padding: 2px 7px; border-radius: 20px;
    margin-right: 3px; margin-bottom: 3px;
}
.level-badge { display: inline-block; font-size: 10px; padding: 2px 8px;
    border-radius: 20px; font-weight: 600; margin-bottom: 6px; }
.cat-header {
    font-size: 16px; font-weight: 700; color: #e2e8f0;
    margin: 20px 0 10px; padding-bottom: 6px;
    border-bottom: 1px solid #1e3a5f;
}
.lib-hero {
    background: linear-gradient(135deg, #0a1628 0%, #0f2442 50%, #0a1628 100%);
    border-radius: 16px; padding: 28px; text-align: center; margin-bottom: 20px;
    border: 1px solid #1e3a5f;
}
.lib-hero-title { font-size: 26px; font-weight: 900; color: #60a5fa; margin-bottom: 6px;
    font-family: Orbitron, monospace; letter-spacing: 0.05em; }
.lib-hero-sub { font-size: 13px; color: #7dd3fc; }
.lib-stat { text-align: center; }
.lib-stat-n { font-size: 22px; font-weight: 800; color: #3b82f6; }
.lib-stat-l { font-size: 11px; color: #64748b; }
.chat-msg-user {
    background: linear-gradient(135deg, #1e3a5f, #0f2442);
    border: 1px solid #2563eb; border-radius: 12px 12px 4px 12px;
    padding: 12px 15px; margin: 8px 0; color: #e2e8f0; font-size: 13px;
}
.chat-msg-ai {
    background: linear-gradient(135deg, #0d1b2e, #111827);
    border: 1px solid #1e3a5f; border-radius: 4px 12px 12px 12px;
    padding: 14px 16px; margin: 8px 0; color: #cbd5e1; font-size: 13px;
    line-height: 1.65;
}
.mentor-chip {
    display: inline-block; background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.3); border-radius: 20px;
    padding: 4px 14px; font-size: 11px; color: #60a5fa; cursor: pointer;
    margin: 4px 3px; transition: all 0.2s;
}
.mentor-chip:hover { background: rgba(59,130,246,0.25); }
</style>
"""

# ═══════════════════════════════════════════════════════════════════
# 4. MAIN RENDER
# ═══════════════════════════════════════════════════════════════════
def show_library_page():
    st.markdown(LIB_CSS, unsafe_allow_html=True)

    # ── Session init ──
    for k, v in {
        "lib_messages": [], "lib_selected_book": None,
        "lib_tab": "books",  # books | mentor
        "mentor_messages": [], "mentor_started": False,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Hero ──
    total_books = sum(len(v) for v in BOOKS.values())
    st.markdown(f"""
    <div class="lib-hero">
        <div class="lib-hero-title">📚 FinSage Library</div>
        <div class="lib-hero-sub">Investment & Trading की दुनिया की सर्वश्रेष्ठ किताबें — AI Mentor के साथ</div>
        <div style="display:flex;justify-content:center;gap:40px;margin-top:16px;">
            <div class="lib-stat"><div class="lib-stat-n">{total_books}</div><div class="lib-stat-l">Books</div></div>
            <div class="lib-stat"><div class="lib-stat-n">{len(BOOKS)}</div><div class="lib-stat-l">Categories</div></div>
            <div class="lib-stat"><div class="lib-stat-n">🤖</div><div class="lib-stat-l">AI Powered</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Top tab selector ──
    t1, t2 = st.tabs(["📚 Book Library", "🎓 FinSage Trading Mentor"])

    # ══════════════════════════════════════════════
    # TAB 1 — BOOK LIBRARY + AI BOOK ASSISTANT
    # ══════════════════════════════════════════════
    with t1:
        col_books, col_chat = st.columns([1.1, 0.9], gap="large")

        with col_books:
            st.markdown("#### 🔍 Browse Books")
            search = st.text_input("", placeholder="📖 Book या topic search करें...",
                                   key="lib_search", label_visibility="collapsed")
            lvl_f  = st.selectbox("", ["All Levels","Beginner","Intermediate","Advanced"],
                                  key="lvl_filter", label_visibility="collapsed")

            for cat, books in BOOKS.items():
                filtered = books
                if search:
                    filtered = [b for b in filtered
                                if search.lower() in b["title"].lower()
                                or search.lower() in b["author"].lower()
                                or any(search.lower() in t.lower() for t in b["tags"])]
                if lvl_f != "All Levels":
                    filtered = [b for b in filtered if b["level"] == lvl_f]
                if not filtered: continue

                st.markdown(f'<div class="cat-header">{cat}</div>', unsafe_allow_html=True)
                for book in filtered:
                    tags_html = "".join(f'<span class="btag">{t}</span>' for t in book["tags"])
                    lvl_bg = {"Beginner":"#14532d","Intermediate":"#78350f","Advanced":"#7f1d1d"}.get(book["level"],"#1e293b")
                    st.markdown(f"""
                    <div class="book-card">
                        <div class="book-title">{book['title']}</div>
                        <div class="book-author">✍️ {book['author']}</div>
                        <div><span class="level-badge" style="background:{lvl_bg};color:{book['level_color']};">{book['level']}</span></div>
                        <div class="book-desc">{book['description']}</div>
                        <div>{tags_html}</div>
                    </div>""", unsafe_allow_html=True)

                    if st.button(f"🤖 AI Summary", key=f"bk_{book['title'][:25]}"):
                        st.session_state.lib_selected_book = book["title"]
                        st.session_state.lib_messages = []
                        msg = f"Mujhe '{book['title']}' by {book['author']} ke baare mein poori detail do — saare sections mein."
                        st.session_state.lib_messages.append({"role":"user","content":msg})
                        st.rerun()

        with col_chat:
            st.markdown("#### 🤖 AI Book Assistant")

            if not st.session_state.lib_selected_book:
                st.markdown("""
                <div style="background:#0d1b2e;border:1px dashed #1e3a5f;border-radius:12px;
                    padding:40px 20px;text-align:center;color:#4a5568;margin-top:10px;">
                    <div style="font-size:42px;margin-bottom:10px;">📖</div>
                    <div style="font-size:14px;font-weight:600;color:#64748b;margin-bottom:6px;">
                        कोई भी book select करें</div>
                    <div style="font-size:12px;color:#4a5568;">
                        "AI Summary" button दबाएं और उस book की<br>पूरी AI-powered analysis पाएं</div>
                </div>""", unsafe_allow_html=True)
            else:
                # Selected book badge
                st.markdown(f"""<div style="background:linear-gradient(90deg,#1e3a5f,#0f2442);
                    border-radius:10px;padding:10px 14px;margin-bottom:10px;
                    font-size:12px;color:#7dd3fc;font-weight:600;">
                    📚 Selected: {st.session_state.lib_selected_book}</div>""",
                    unsafe_allow_html=True)

                # Auto-fetch AI response for pending user msg
                msgs = st.session_state.lib_messages
                if msgs and msgs[-1]["role"] == "user":
                    with st.spinner("🤖 FinSage Library AI analysing..."):
                        reply = _call_groq(
                            [{"role":"system","content":BOOK_ASSISTANT_SYSTEM}] + msgs,
                            max_tokens=1800
                        )
                        st.session_state.lib_messages.append({"role":"assistant","content":reply})
                        st.rerun()

                # Render conversation
                for m in st.session_state.lib_messages:
                    if m["role"] == "user":
                        st.markdown(f'<div class="chat-msg-user">👤 {m["content"]}</div>',
                                    unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="chat-msg-ai">🤖 {m["content"]}</div>',
                                    unsafe_allow_html=True)

                # Follow-up input
                st.write("")
                with st.form("lib_followup", clear_on_submit=True):
                    fu = st.text_input("", placeholder="इस book के बारे में कोई सवाल पूछें...",
                                       label_visibility="collapsed", key="lib_fu_inp")
                    if st.form_submit_button("Ask →", use_container_width=True):
                        if fu.strip():
                            st.session_state.lib_messages.append({"role":"user","content":fu.strip()})
                            st.rerun()

                if st.button("🔄 New Book Select करें", key="lib_clear"):
                    st.session_state.lib_selected_book = None
                    st.session_state.lib_messages = []
                    st.rerun()

    # ══════════════════════════════════════════════
    # TAB 2 — FINSAGE TRADING MENTOR
    # ══════════════════════════════════════════════
    with t2:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0a1628,#0f2442);border-radius:14px;
            padding:20px 24px;margin-bottom:18px;border:1px solid #1e3a5f;">
            <div style="font-size:17px;font-weight:800;color:#60a5fa;margin-bottom:4px;">
            🎓 FinSage Trading Mentor</div>
            <div style="font-size:12px;color:#64748b;">
            Beginner से Advanced तक — structured lessons, visual explanations,
            quizzes aur Indian market examples के साथ</div>
        </div>""", unsafe_allow_html=True)

        # Quick start chips
        if not st.session_state.mentor_started:
            st.markdown("**📌 Quick Start — इन topics से शुरू करें:**")
            chips = [
                "मुझे Stock Market basics सिखाओ",
                "Candlestick patterns explain karo",
                "RSI aur MACD kya hote hain?",
                "Intraday trading kaise karein?",
                "Risk management sikhao",
                "Options trading basics",
                "Trading psychology",
                "Nifty 50 kya hota hai?",
            ]
            rows = [chips[:4], chips[4:]]
            for row in rows:
                cs = st.columns(4)
                for i, chip in enumerate(row):
                    with cs[i]:
                        if st.button(chip, key=f"mc_{chip[:20]}", use_container_width=True):
                            st.session_state.mentor_messages.append({"role":"user","content":chip})
                            st.session_state.mentor_started = True
                            st.rerun()
            st.markdown("---")

        # Chat container
        chat_area = st.container()

        # Auto-respond to pending message
        mentor_msgs = st.session_state.mentor_messages
        if mentor_msgs and mentor_msgs[-1]["role"] == "user":
            with st.spinner("🎓 FinSage Mentor सोच रहा है..."):
                reply = _call_groq(
                    [{"role":"system","content":MENTOR_SYSTEM}] + mentor_msgs,
                    max_tokens=2000
                )
                st.session_state.mentor_messages.append({"role":"assistant","content":reply})
                st.session_state.mentor_started = True
                st.rerun()

        # Render messages
        with chat_area:
            if not st.session_state.mentor_messages:
                st.markdown("""
                <div style="background:#0d1b2e;border:1px dashed #1e3a5f;border-radius:12px;
                    padding:30px 20px;text-align:center;color:#4a5568;">
                    <div style="font-size:36px;margin-bottom:8px;">🎓</div>
                    <div style="font-size:14px;font-weight:600;color:#64748b;margin-bottom:5px;">
                    FinSage Trading Mentor तैयार है</div>
                    <div style="font-size:12px;color:#4a5568;">
                    ऊपर कोई chip select करें या नीचे type करें</div>
                </div>""", unsafe_allow_html=True)
            else:
                for m in st.session_state.mentor_messages:
                    if m["role"] == "user":
                        st.markdown(f'<div class="chat-msg-user">👤 {m["content"]}</div>',
                                    unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="chat-msg-ai">🎓 {m["content"]}</div>',
                                    unsafe_allow_html=True)

        # Input
        st.write("")
        col_inp, col_btn = st.columns([5, 1])
        with col_inp:
            user_input = st.text_input("", placeholder="अपना सवाल यहाँ लिखें...",
                                       label_visibility="collapsed", key="mentor_inp")
        with col_btn:
            send = st.button("Send", key="mentor_send", use_container_width=True, type="primary")

        if send and user_input.strip():
            st.session_state.mentor_messages.append({"role":"user","content":user_input.strip()})
            st.session_state.mentor_started = True
            st.rerun()

        # Clear
        if st.session_state.mentor_messages:
            st.write("")
            if st.button("🔄 New Session", key="mentor_clear"):
                st.session_state.mentor_messages = []
                st.session_state.mentor_started = False
                st.rerun()
