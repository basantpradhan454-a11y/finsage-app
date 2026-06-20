"""
FinSage — AI Trading Learning Module v2.0
==========================================
Three-layer hybrid system:
  Layer 1 — Fixed Course Library (JSON cache, Udemy-style)
  Layer 2 — AI Deep-Dive on-demand per lesson
  Layer 3 — Full AI fallback + auto-save to library

API Keys via Streamlit secrets or env vars:
  GROQ_API_KEY   — Groq (llama-3.3-70b) — primary AI engine
  GROW_API_KEY   — alias (auto-detected, same as GROQ_API_KEY)
  OPENAI_API_KEY — optional fallback
"""

import streamlit as st
import json
import os
import time
import random
import hashlib
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ══════════════════════════════════════════════════════
# 0.  CONSTANTS & PATHS
# ══════════════════════════════════════════════════════
COURSE_LIBRARY_PATH = os.path.join(os.path.dirname(__file__), "course_library.json")
USER_PROGRESS_PATH  = os.path.join(os.path.dirname(__file__), "user_progress.json")
PASS_THRESHOLD = 70   # % to unlock next topic

# ══════════════════════════════════════════════════════
# 1.  API HELPERS  (Groq as primary — same pattern as rest of FinSage)
# ══════════════════════════════════════════════════════
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"   # same model used across FinSage

def _get_key(name: str) -> str:
    v = os.environ.get(name, "")
    if not v:
        try:
            v = st.secrets.get(name, "")
        except Exception:
            pass
    return v or ""

def _get_groq_key() -> str:
    """Try GROQ_API_KEY first, then GROW_API_KEY (user's saved secret name)."""
    return _get_key("GROQ_API_KEY") or _get_key("GROW_API_KEY")

def call_groq(prompt: str, system: str = "", max_tokens: int = 2500,
              temperature: float = 0.6) -> str:
    """Primary AI engine — Groq llama-3.3-70b (fast, free tier generous)."""
    api_key = _get_groq_key()
    if not api_key:
        return _call_openai_fallback(prompt, system, max_tokens)
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": msgs,
                  "temperature": temperature, "max_tokens": max_tokens},
            timeout=60
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return _call_openai_fallback(prompt, system, max_tokens)

def _call_openai_fallback(prompt: str, system: str = "", max_tokens: int = 2500) -> str:
    """Fallback to OpenAI if Groq key not set."""
    api_key = _get_key("OPENAI_API_KEY")
    if not api_key:
        return "⚠️ No AI key configured. Add GROQ_API_KEY to Streamlit secrets to enable AI features."
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"model": "gpt-4o", "messages": msgs,
                  "temperature": 0.7, "max_tokens": max_tokens},
            timeout=60
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ AI Error: {e}"

# Route: ALL tasks (text + visual) → Groq.  OpenAI is fallback only.
def ai_text(prompt: str, system: str = "", max_tokens: int = 2500) -> str:
    """Teaching, grading, Q&A — Groq primary."""
    return call_groq(prompt, system, max_tokens=max_tokens)

def ai_visual(prompt: str, system: str = "") -> str:
    """Chart/visual explanations — Groq primary (fast + capable)."""
    return call_groq(prompt, system, max_tokens=1800)

# ══════════════════════════════════════════════════════
# 2.  LANGUAGE SUPPORT
# ══════════════════════════════════════════════════════
LANGUAGES = {
    "English": "en",
    "हिंदी (Hindi)": "hi",
    "తెలుగు (Telugu)": "te",
    "தமிழ் (Tamil)": "ta",
    "বাংলা (Bengali)": "bn",
    "मराठी (Marathi)": "mr",
    "ਪੰਜਾਬੀ (Punjabi)": "pa",
    "ગુજરાતી (Gujarati)": "gu",
    "Español (Spanish)": "es",
    "Français (French)": "fr",
}
LANG_INSTR = {
    "en": "Respond in English.",
    "hi": "हिंदी में जवाब दो।",
    "te": "తెలుగులో సమాధానం ఇవ్వండి.",
    "ta": "தமிழில் பதில் அளிக்கவும்.",
    "bn": "বাংলায় উত্তর দিন।",
    "mr": "मराठीत उत्तर द्या.",
    "pa": "ਪੰਜਾਬੀ ਵਿੱਚ ਜਵਾਬ ਦਿਓ।",
    "gu": "ગુજરાતીમાં જવાબ આપો.",
    "es": "Responde en español.",
    "fr": "Réponds en français.",
}

def lang_instr() -> str:
    code = st.session_state.get("tl_lang", "en")
    return LANG_INSTR.get(code, "Respond in English.")

# ══════════════════════════════════════════════════════
# 3.  MARKET / STYLE CATALOG
# ══════════════════════════════════════════════════════
MARKET_CATALOG = {
    "📈 Stock Market": {
        "desc": "NSE, BSE, NYSE, NASDAQ — India & global equities",
        "styles": {
            "📊 Options Trading":     "Trade contracts for leverage, hedging & income strategies.",
            "🏦 Long-term Investing":  "Hold months–years. Fundamental analysis & wealth building.",
        }
    },
    "₿ Crypto Market": {
        "desc": "Bitcoin, Ethereum, Altcoins — 24/7 global markets",
        "styles": {
            "🔄 Swing Trading":   "Ride crypto trends over days/weeks with TA + sentiment.",
            "🌐 DeFi & Long-term": "Stake, earn yield, hold through market cycles.",
        }
    },
    "💱 Forex Market": {
        "desc": "EUR/USD, GBP/INR — world's largest $7T/day market",
        "styles": {
            "🔄 Swing Trading":   "Multi-day trades following currency macro trends.",
            "📌 Position Trading": "Long-term holds driven by macroeconomics.",
        }
    }
}

# 12 fixed topic titles per any market+style
BASE_TOPICS = [
    {"title": "Introduction & Market Foundations",          "est_min": 8},
    {"title": "How the Market Works — Mechanics & Players", "est_min": 10},
    {"title": "Essential Terminology",                      "est_min": 7},
    {"title": "Reading Candlestick Charts",                  "est_min": 12},
    {"title": "Technical Indicators — RSI, MACD & MAs",     "est_min": 15},
    {"title": "Chart Patterns — Flags, H&S, Double Top/Bottom", "est_min": 14},
    {"title": "Support & Resistance Levels",                 "est_min": 12},
    {"title": "Style-Specific Strategy Deep-Dive",           "est_min": 18},
    {"title": "Entry & Exit Rules",                          "est_min": 14},
    {"title": "Risk Management & Position Sizing",           "est_min": 16},
    {"title": "Trading Psychology & Discipline",             "est_min": 12},
    {"title": "Building Your Personal Trading Plan",         "est_min": 15},
]

# ══════════════════════════════════════════════════════
# 4.  COURSE LIBRARY  (Layer 1 — JSON persistence)
# ══════════════════════════════════════════════════════
def _load_library() -> dict:
    if os.path.exists(COURSE_LIBRARY_PATH):
        try:
            with open(COURSE_LIBRARY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_library(lib: dict):
    try:
        with open(COURSE_LIBRARY_PATH, "w", encoding="utf-8") as f:
            json.dump(lib, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _course_key(market: str, style: str) -> str:
    return hashlib.md5(f"{market}|{style}".encode()).hexdigest()[:12]

def get_course(market: str, style: str) -> dict | None:
    lib = _load_library()
    return lib.get(_course_key(market, style))

def save_course(market: str, style: str, course: dict):
    lib = _load_library()
    lib[_course_key(market, style)] = course
    _save_library(lib)

# ══════════════════════════════════════════════════════
# 5.  USER PROGRESS  (per-user, per-topic)
# ══════════════════════════════════════════════════════
def _load_progress() -> dict:
    if os.path.exists(USER_PROGRESS_PATH):
        try:
            with open(USER_PROGRESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_progress(prog: dict):
    try:
        with open(USER_PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(prog, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _user_id() -> str:
    """Use session-based anonymous ID or auth email if available."""
    uid = st.session_state.get("user_email") or st.session_state.get("tl_anon_id")
    if not uid:
        uid = "anon_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        st.session_state["tl_anon_id"] = uid
    return uid

def get_user_progress(topic_id: str) -> dict:
    prog = _load_progress()
    uid = _user_id()
    return prog.get(uid, {}).get(topic_id, {
        "status": "locked",   # locked | unlocked | completed | failed
        "score_history": [],
        "best_score": 0,
        "passed": False,
        "retake_count": 0,
        "reteach_used": False,
    })

def set_user_progress(topic_id: str, data: dict):
    prog = _load_progress()
    uid = _user_id()
    if uid not in prog:
        prog[uid] = {}
    existing = prog[uid].get(topic_id, {})
    existing.update(data)
    prog[uid][topic_id] = existing
    _save_progress(prog)

def get_all_user_progress_for_course(course: dict) -> dict:
    result = {}
    for t in course.get("topics", []):
        result[t["id"]] = get_user_progress(t["id"])
    return result

# ══════════════════════════════════════════════════════
# 6.  AI CONTENT GENERATION
# ══════════════════════════════════════════════════════
def _tutor_system(market, style) -> str:
    return (
        f"You are FinSage AI Tutor — expert trading educator. "
        f"Market: {market} | Style: {style}. "
        f"{lang_instr()} "
        "Teach practically, not theoretically. Use numbered sections, bold key terms, "
        "emojis for section headers, real-world examples with numbers/percentages. "
        "Never give specific buy/sell signals for real stocks."
    )

def generate_lesson_content(market: str, style: str, topic_title: str,
                             topic_idx: int, total: int, mode: str = "standard") -> str:
    """Generate ebook-style lesson content. mode: standard | simpler | deeper"""
    level_label = "Beginner" if topic_idx < 4 else "Intermediate" if topic_idx < 9 else "Advanced"
    depth_instr = {
        "standard": f"Chapter {topic_idx+1} of {total} — {level_label} level.",
        "simpler":  "Re-explain in MUCH simpler language. Use everyday analogies, avoid all jargon. Extra Indian examples.",
        "deeper":   "Advanced deep-dive. Include professional techniques, edge cases, quantitative insights.",
    }[mode]

    prompt = f"""You are FinSage AI — expert trading educator creating a PREMIUM EBOOK CHAPTER.
{depth_instr}

Market: {market} | Trading Style: {style}
Topic: {topic_title}
{lang_instr()}

Write a RICH, EBOOK-STYLE chapter with this exact structure:

# 📖 {topic_title}

## 🎯 What You Will Learn
- (learning objective 1)
- (learning objective 2)
- (learning objective 3)

## 📌 Chapter Overview
(2-3 sentence intro — why this topic matters for {style} traders)

---

## 💡 Core Concept
(Main explanation with simple language. Start with a relatable analogy like kirana shop, chai, cricket etc.)

### Key Points:
(5-6 bullet points, **bold** the key terms)

---

## ⚙️ Step-by-Step Walkthrough
(5-7 numbered practical steps)

---

## 🇮🇳 Indian Market Example
(Realistic example using NSE/BSE: Reliance, TCS, HDFC Bank, Infosys, Nifty 50.
Use ₹ amounts, realistic scenarios, specific numbers.)

---

## 📊 Quick Reference Table or Visual
(Create a clear text table with headers — e.g. | Signal | Meaning | Action |
OR a mini ASCII chart to illustrate the concept visually)

---

## 🔢 Formula / Rule
(If applicable: formula + worked example with ₹ and Indian stocks)

---

## ⚠️ Common Mistakes
(4 mistakes with ❌ Wrong vs ✅ Right format)

---

## ✅ Chapter Summary
(2-3 bullet points — the most important takeaways to remember)

## 🔗 Up Next
(One-line teaser for the next chapter)

---
Total: 700-1000 words. Premium course quality. India-focused. Use ₹ throughout.
"""
    return ai_text(prompt, _tutor_system(market, style), max_tokens=2800)

def generate_full_course_structure(market: str, style: str) -> dict:
    """Layer 3 fallback: generate and save a full course."""
    course_id = _course_key(market, style)
    topics = []
    for i, t in enumerate(BASE_TOPICS):
        topic_id = f"{course_id}_t{i}"
        topics.append({
            "id":       topic_id,
            "order":    i,
            "title":    t["title"],
            "est_min":  t["est_min"],
            "content":  None,   # generated on first open (lazy)
            "generated_at": None,
        })
    course = {
        "id":         course_id,
        "market":     market,
        "style":      style,
        "created_at": datetime.now().isoformat(),
        "topics":     topics,
    }
    save_course(market, style, course)
    return course

def ensure_course(market: str, style: str) -> dict:
    """Get from library or generate (Layer 3 fallback)."""
    course = get_course(market, style)
    if not course:
        course = generate_full_course_structure(market, style)
    return course

def ensure_topic_content(course: dict, topic_idx: int,
                         market: str, style: str, mode: str = "standard") -> str:
    """Get topic content from library or generate it lazily."""
    topic = course["topics"][topic_idx]
    if mode == "standard" and topic.get("content"):
        return topic["content"]
    # Generate
    content = generate_lesson_content(
        market, style, topic["title"], topic_idx, len(course["topics"]), mode
    )
    if mode == "standard":
        # Save back to library
        topic["content"] = content
        topic["generated_at"] = datetime.now().isoformat()
        save_course(market, style, course)
    return content

def generate_exam_questions(market: str, style: str, topic_title: str, n: int = 7) -> list:
    system = _tutor_system(market, style)
    prompt = f"""Create exactly {n} exam questions about: **{topic_title}**
Return ONLY valid JSON — no markdown fences, no other text.
{{
  "questions": [
    {{
      "id": 1,
      "type": "mcq",
      "question": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "A",
      "concept": "short tag, e.g. RSI"
    }},
    {{
      "id": 2,
      "type": "short_answer",
      "question": "...",
      "options": null,
      "correct_answer": "key points expected",
      "concept": "tag"
    }},
    {{
      "id": 3,
      "type": "scenario",
      "question": "Scenario: ... What do you do?",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "B",
      "concept": "tag"
    }}
  ]
}}
Distribute: 4 MCQ, 2 short_answer, 1 scenario. Test real understanding."""
    raw = ai_text(prompt, system, max_tokens=2000)
    # Strip any markdown fences
    raw = raw.strip()
    for fence in ["```json", "```"]:
        if raw.startswith(fence):
            raw = raw[len(fence):]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    try:
        return json.loads(raw).get("questions", [])
    except Exception:
        # Minimal fallback
        return [
            {"id": 1, "type": "mcq", "question": f"Which best describes {topic_title}?",
             "options": ["A. Buy low sell high", "B. Disciplined rule-based approach",
                         "C. Trade on emotions", "D. Ignore risk management"],
             "correct_answer": "B", "concept": topic_title},
            {"id": 2, "type": "short_answer",
             "question": f"In your own words, explain the core idea behind {topic_title}.",
             "options": None, "correct_answer": "Core principle applied to context.", "concept": topic_title},
        ]

def grade_answer(q: dict, user_ans: str, market: str, style: str) -> dict:
    system = _tutor_system(market, style)
    prompt = f"""Grade this exam answer. Return ONLY valid JSON.
Question ({q['type']}): {q['question']}
{"Options: " + str(q.get('options')) if q.get('options') else ""}
Correct answer: {q['correct_answer']}
User's answer: {user_ans}

{{"is_correct": true/false, "score": 0-100, "short_verdict": "...",
  "explanation": "why correct answer is right (2-3 sentences)",
  "user_error": "what user got wrong (null if correct)",
  "memory_tip": "practical tip to remember",
  "encouragement": "brief supportive message"}}"""
    raw = ai_text(prompt, system, max_tokens=600)
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        return json.loads(raw)
    except Exception:
        is_c = user_ans.strip().upper()[:1] == q.get("correct_answer","").strip().upper()[:1]
        return {"is_correct": is_c, "score": 100 if is_c else 0,
                "short_verdict": "Correct! ✅" if is_c else "Not quite ❌",
                "explanation": f"Correct: {q['correct_answer']}",
                "user_error": None if is_c else f"You said: {user_ans}",
                "memory_tip": "Review this in the lesson.",
                "encouragement": "Keep going! 💪"}

# ══════════════════════════════════════════════════════
# 7.  CHART ENGINE
# ══════════════════════════════════════════════════════
def _make_ohlcv(days: int = 40, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = [datetime.now() - timedelta(days=days - i) for i in range(days)]
    price = 100.0
    rows = []
    for _ in range(days):
        chg  = rng.normal(0, 1.8)
        o    = price
        c    = price + chg
        h    = max(o, c) + abs(rng.normal(0, 0.6))
        l    = min(o, c) - abs(rng.normal(0, 0.6))
        vol  = int(rng.uniform(500_000, 2_000_000))
        rows.append((o, h, l, c, vol))
        price = c
    df = pd.DataFrame(rows, columns=["Open","High","Low","Close","Volume"], index=dates)
    # indicators
    delta = df["Close"].diff()
    g, ls = delta.clip(lower=0).rolling(14).mean(), -delta.clip(upper=0).rolling(14).mean()
    df["RSI"]    = 100 - 100/(1 + g/ls.replace(0, 1e-9))
    df["EMA12"]  = df["Close"].ewm(span=12).mean()
    df["EMA26"]  = df["Close"].ewm(span=26).mean()
    df["MACD"]   = df["EMA12"] - df["EMA26"]
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    df["MA20"]   = df["Close"].rolling(20).mean()
    df["BB_upper"] = df["MA20"] + 2 * df["Close"].rolling(20).std()
    df["BB_lower"] = df["MA20"] - 2 * df["Close"].rolling(20).std()
    return df

def render_demo_chart(concept: str, title: str = "Live Example") -> go.Figure:
    c = concept.lower()
    show_rsi  = any(k in c for k in ["rsi","oversold","overbought","relative strength"])
    show_macd = any(k in c for k in ["macd","momentum","convergence","divergence"])
    show_bb   = any(k in c for k in ["bollinger","bb","band","squeeze"])
    show_sr   = any(k in c for k in ["support","resistance","level","zone","break"])

    rows   = 1 + (1 if show_rsi else 0) + (1 if show_macd else 0)
    heights = [0.65] + ([0.175] if show_rsi else []) + ([0.175] if show_macd else [])

    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                        vertical_spacing=0.04, row_heights=heights,
                        subplot_titles=[title]+
                                       (["RSI (14)"] if show_rsi else [])+
                                       (["MACD"] if show_macd else []))

    df = _make_ohlcv(40)

    # Candles
    fig.add_trace(go.Candlestick(
        x=df.index, open=df.Open, high=df.High, low=df.Low, close=df.Close,
        increasing_line_color="#00d4ff", decreasing_line_color="#ff4466",
        name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df.MA20,
        line=dict(color="#f7b731", width=1.2), name="MA20"), row=1, col=1)

    if show_bb:
        fig.add_trace(go.Scatter(x=df.index, y=df.BB_upper,
            line=dict(color="#7b2ff7", width=0.8, dash="dot"), name="BB Upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df.BB_lower,
            line=dict(color="#7b2ff7", width=0.8, dash="dot"), name="BB Lower",
            fill="tonexty", fillcolor="rgba(123,47,247,0.04)"), row=1, col=1)

    if show_sr:
        sup = float(df["Low"].rolling(5).min().dropna().iloc[-1])
        res = float(df["High"].rolling(5).max().dropna().iloc[-1])
        fig.add_hline(y=sup, line_dash="dash", line_color="#00ff88",
                      annotation_text="Support", row=1, col=1)
        fig.add_hline(y=res, line_dash="dash", line_color="#ff4466",
                      annotation_text="Resistance", row=1, col=1)

    row_n = 2
    if show_rsi:
        fig.add_trace(go.Scatter(x=df.index, y=df.RSI,
            line=dict(color="#7b2ff7", width=1.5), name="RSI"), row=row_n, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ff4466", row=row_n, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00d4ff", row=row_n, col=1)
        row_n += 1

    if show_macd:
        hist = df.MACD - df.Signal
        fig.add_trace(go.Bar(x=df.index, y=hist, name="Histogram",
            marker_color=["#00d4ff" if v >= 0 else "#ff4466" for v in hist]), row=row_n, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df.MACD,
            line=dict(color="#00d4ff", width=1.4), name="MACD"), row=row_n, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df.Signal,
            line=dict(color="#f7b731", width=1.4), name="Signal"), row=row_n, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a1220", plot_bgcolor="#0a1220",
        xaxis_rangeslider_visible=False,
        height=350 + 120 * (rows - 1),
        margin=dict(l=8, r=8, t=35, b=8),
        font=dict(color="#c9d1d9", size=11),
        legend=dict(orientation="h", y=1.07, font_size=10),
        showlegend=True,
    )
    return fig

# ══════════════════════════════════════════════════════
# 8.  CSS
# ══════════════════════════════════════════════════════
TL_CSS = """
<style>
/* ── Cards ── */
.tl-card {
    background: linear-gradient(135deg,#071525 0%,#0d2040 100%);
    border: 1px solid rgba(0,212,255,0.18);
    border-radius: 14px; padding: 20px 22px; margin: 8px 0;
    transition: all 0.25s ease;
}
.tl-card:hover { border-color:#00d4ff; box-shadow:0 0 22px rgba(0,212,255,0.18); }
.tl-market-title { font-size:1.25rem; font-weight:800; color:#00d4ff; }
/* ── Progress bar ── */
.tl-prog-wrap { display:flex; align-items:center; gap:12px; margin:8px 0; }
.tl-prog-track { flex:1; background:#0d2040; border-radius:50px; height:7px; overflow:hidden; }
.tl-prog-fill { background:linear-gradient(90deg,#00d4ff,#7b2ff7); height:100%;
                border-radius:50px; transition:width 0.5s ease; }
/* ── Topic row in TOC ── */
.tl-topic-row {
    display:flex; align-items:center; gap:10px;
    padding: 9px 14px; border-radius: 10px; margin: 4px 0;
    background: rgba(0,20,45,0.5);
    border: 1px solid rgba(0,212,255,0.07);
    cursor:pointer; transition: all 0.2s;
}
.tl-topic-row:hover { border-color:rgba(0,212,255,0.3); background:rgba(0,212,255,0.05); }
.tl-topic-row.active { border-color:#00d4ff; background:rgba(0,212,255,0.08);
                        box-shadow:0 0 10px rgba(0,212,255,0.12); }
.tl-topic-row.completed { border-color:rgba(0,255,136,0.3); }
.tl-topic-row.failed { border-color:rgba(255,68,102,0.3); }
.tl-topic-row.locked { opacity:0.45; }
/* ── Lesson box ── */
.tl-lesson {
    background: rgba(7,21,37,0.95);
    border: 1px solid rgba(0,212,255,0.1);
    border-radius: 14px; padding: 28px 32px;
    line-height: 1.85; color: #d4dde8;
    font-size: 0.94rem;
}
/* ── Exam question ── */
.tl-q-box {
    background: #071525;
    border-left: 3px solid #00d4ff;
    border-radius: 0 10px 10px 0;
    padding: 16px 18px; margin: 16px 0;
}
/* ── Feedback ── */
.tl-ok  { background:#00d4ff0e; border:1px solid #00d4ff44; border-radius:9px; padding:12px; margin:8px 0; }
.tl-err { background:#ff446611; border:1px solid #ff446644; border-radius:9px; padding:12px; margin:8px 0; }
/* ── Live demo panel ── */
.tl-live {
    background: #060f1e;
    border: 1px solid #7b2ff7;
    border-radius: 12px; padding: 16px; margin-top:10px;
}
/* ── Wizard header ── */
.tl-wiz-hdr {
    text-align:center; padding:18px 0;
    border-bottom:1px solid rgba(0,212,255,0.12);
    margin-bottom:22px;
}
/* ── Score badge ── */
.tl-score-pass { color:#00ff88; font-weight:800; font-size:1.3rem; }
.tl-score-fail { color:#ff4466; font-weight:800; font-size:1.3rem; }
/* ── Reteach banner ── */
.tl-reteach {
    background: linear-gradient(90deg,rgba(123,47,247,0.12),rgba(0,212,255,0.08));
    border: 1px solid rgba(123,47,247,0.3);
    border-radius: 10px; padding: 12px 16px; margin: 14px 0;
}
/* ── Whiteboard Teacher Chat ── */
.wb-container {
    background: linear-gradient(135deg,#040d1a,#071525);
    border: 2px solid rgba(0,212,255,0.25);
    border-radius: 16px;
    padding: 0;
    margin: 20px 0;
    overflow: hidden;
}
.wb-header {
    background: linear-gradient(90deg, rgba(0,212,255,0.12), rgba(74,158,255,0.08));
    border-bottom: 1px solid rgba(0,212,255,0.2);
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.wb-header-title {
    font-size: 14px;
    font-weight: 800;
    color: #00d4ff;
    letter-spacing: 0.03em;
}
.wb-header-sub {
    font-size: 11px;
    color: #4a9eff;
    margin-top: 1px;
}
.wb-live-dot {
    width: 8px; height: 8px;
    background: #00ff88;
    border-radius: 50%;
    animation: wb-pulse 1.5s ease-in-out infinite;
    flex-shrink: 0;
}
@keyframes wb-pulse {
    0%,100% { opacity:1; box-shadow:0 0 0 0 rgba(0,255,136,0.4); }
    50% { opacity:0.8; box-shadow:0 0 0 5px rgba(0,255,136,0); }
}
.wb-messages {
    padding: 16px 18px;
    max-height: 400px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.wb-messages::-webkit-scrollbar { width: 3px; }
.wb-messages::-webkit-scrollbar-thumb { background: #1a3a5c; border-radius: 3px; }
.wb-msg-teacher {
    background: linear-gradient(135deg,#071f3a,#0a2848);
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 4px 14px 14px 14px;
    padding: 13px 16px;
    color: #c9d8ea;
    font-size: 13px;
    line-height: 1.7;
    position: relative;
}
.wb-msg-teacher::before {
    content: "🎓 AI Teacher";
    display: block;
    font-size: 10px;
    font-weight: 700;
    color: #00d4ff;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.wb-msg-student {
    background: linear-gradient(135deg,#0f1e35,#142540);
    border: 1px solid rgba(74,158,255,0.2);
    border-radius: 14px 14px 4px 14px;
    padding: 11px 14px;
    color: #a5c8f0;
    font-size: 13px;
    align-self: flex-end;
    max-width: 85%;
    text-align: right;
}
.wb-msg-student::before {
    content: "👤 You";
    display: block;
    font-size: 10px;
    font-weight: 700;
    color: #4a9eff;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.wb-board {
    background: #071525;
    border: 1px solid rgba(0,212,255,0.1);
    border-radius: 10px;
    padding: 14px;
    margin: 10px 0;
    font-family: monospace;
    font-size: 12px;
    color: #7dd3fc;
    white-space: pre-wrap;
    line-height: 1.8;
}
.wb-thinking {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #4a9eff;
    font-size: 12px;
    padding: 8px 4px;
}
.wb-dot-1, .wb-dot-2, .wb-dot-3 {
    width: 6px; height: 6px;
    background: #00d4ff;
    border-radius: 50%;
    animation: wb-bounce 1.2s ease-in-out infinite;
}
.wb-dot-2 { animation-delay: 0.2s; }
.wb-dot-3 { animation-delay: 0.4s; }
@keyframes wb-bounce {
    0%,80%,100% { transform: scale(0.6); opacity: 0.4; }
    40% { transform: scale(1); opacity: 1; }
}
.wb-quick-asks {
    padding: 10px 18px;
    border-top: 1px solid rgba(0,212,255,0.1);
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.wb-input-area {
    padding: 12px 18px 16px;
    border-top: 1px solid rgba(0,212,255,0.1);
}
</style>
"""

# ══════════════════════════════════════════════════════
# 9.  STATE MANAGEMENT
# ══════════════════════════════════════════════════════
def init_tl_state():
    D = {
        "tl_step":              "market",
        "tl_lang":              st.session_state.get("user_lang", "en"),
        "tl_market":            None,
        "tl_style":             None,
        "tl_course":            None,
        "tl_topic_idx":         0,
        "tl_phase":             "lesson",
        "tl_exam_qs":           {},
        "tl_exam_ans":          {},
        "tl_exam_fb":           {},
        "tl_submitted":         set(),
        "tl_live_chats":        {},
        "tl_active_live":       "",
        "tl_reteach_content":   {},
        "tl_whiteboard_chats":  {},   # {tid: [{"role":"teacher"|"student","content":str}]}
        "tl_wb_open":           {},   # {tid: bool}
    }
    for k, v in D.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # submitted must be a set (JSON doesn't persist sets)
    if isinstance(st.session_state.tl_submitted, list):
        st.session_state.tl_submitted = set(st.session_state.tl_submitted)

# ══════════════════════════════════════════════════════
# 10.  HELPER RENDERERS
# ══════════════════════════════════════════════════════
def _prog_bar(current: int, total: int, label: str = ""):
    pct = int(current / total * 100) if total else 0
    st.markdown(f"""
    <div class="tl-prog-wrap">
        <span style="color:#888;font-size:0.8rem;white-space:nowrap;">{label or f"Topic {current} of {total}"}</span>
        <div class="tl-prog-track"><div class="tl-prog-fill" style="width:{pct}%"></div></div>
        <span style="color:#00d4ff;font-size:0.82rem;font-weight:700;">{pct}%</span>
    </div>""", unsafe_allow_html=True)

def _topic_status_icon(prog: dict) -> tuple[str, str]:
    """Returns (icon, css_class)"""
    s = prog.get("status", "locked")
    if s == "completed" and prog.get("passed"):
        return "✅", "completed"
    if s == "failed":
        return "❌", "failed"
    if s in ("unlocked", "completed"):
        return "📖", "active"
    return "🔒", "locked"

def _render_toc(course: dict, all_prog: dict, current_idx: int):
    """Udemy-style table of contents with jump navigation."""
    topics = course["topics"]
    completed = sum(1 for p in all_prog.values() if p.get("passed"))
    _prog_bar(completed, len(topics), f"{completed} of {len(topics)} topics passed")

    for i, t in enumerate(topics):
        prog   = all_prog.get(t["id"], {})
        icon, css = _topic_status_icon(prog)
        active = "active" if i == current_idx else ""
        score_txt = ""
        if prog.get("best_score"):
            score_txt = f" · {prog['best_score']}%"
        locked = prog.get("status", "locked") == "locked" and i > 0

        col_toc, col_btn = st.columns([6, 1])
        with col_toc:
            st.markdown(f"""
            <div class="tl-topic-row {active} {css} {'locked' if locked else ''}">
                <span style="font-size:1rem;">{icon}</span>
                <span style="font-size:0.85rem;font-weight:600;color:{'#00d4ff' if not locked else '#556'};flex:1;">
                    {i+1}. {t['title']}</span>
                <span style="font-size:0.73rem;color:#556;">⏱ {t['est_min']}m{score_txt}</span>
            </div>""", unsafe_allow_html=True)
        with col_btn:
            if not locked:
                if st.button("▶", key=f"toc_go_{i}", help=f"Open topic {i+1}",
                             use_container_width=True):
                    st.session_state.tl_topic_idx = i
                    st.session_state.tl_phase = "lesson"
                    st.session_state.tl_step  = "lesson"
                    st.rerun()

# ══════════════════════════════════════════════════════
# 11.  PAGE RENDERERS
# ══════════════════════════════════════════════════════


# ── 11b. Market ────────────────────────────────────────
def render_market_select():
    st.markdown('<div class="tl-wiz-hdr">', unsafe_allow_html=True)
    st.markdown("# 📚 AI Trading Academy")
    st.markdown("*Structured learning from beginner to advanced — AI-powered*")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("### Step 1 — Choose Your Market")

    for market, data in MARKET_CATALOG.items():
        c1, c2 = st.columns([5, 1])
        with c1:
            styles_preview = " · ".join(list(data["styles"].keys())[:3]) + "…"
            st.markdown(f"""<div class="tl-card">
            <div class="tl-market-title">{market}</div>
            <div style="color:#4a9eff;font-size:0.82rem;margin:4px 0;">{data['desc']}</div>
            <div style="color:#556;font-size:0.78rem;">{styles_preview}</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.write("")
            st.write("")
            if st.button("Select →", key=f"mkt_{market}", use_container_width=True):
                st.session_state.tl_market = market
                st.session_state.tl_step   = "style"
                st.rerun()

# ── 11c. Style ─────────────────────────────────────────
def render_style_select():
    market = st.session_state.tl_market
    data   = MARKET_CATALOG[market]

    st.markdown(f'<div class="tl-wiz-hdr"><h2>{market}</h2>'
                '<p>Step 2 — Choose Your Trading Style</p></div>', unsafe_allow_html=True)

    if st.button("← Back", key="back_to_market"):
        st.session_state.tl_step = "market"; st.rerun()

    for style, desc in data["styles"].items():
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(f"""<div class="tl-card">
            <div style="font-size:1.05rem;font-weight:700;color:#e0e6f0;">{style}</div>
            <div style="color:#8899aa;font-size:0.83rem;margin-top:5px;">{desc}</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.write("")
            st.write("")
            if st.button("Start →", key=f"sty_{style}", use_container_width=True):
                st.session_state.tl_style  = style
                # Load / generate course
                with st.spinner("🔄 Loading course…"):
                    course = ensure_course(market, style)
                    # unlock first topic
                    t0 = course["topics"][0]
                    p0 = get_user_progress(t0["id"])
                    if p0["status"] == "locked":
                        set_user_progress(t0["id"], {"status": "unlocked"})
                st.session_state.tl_course    = course
                st.session_state.tl_topic_idx = 0
                st.session_state.tl_phase     = "lesson"
                st.session_state.tl_step      = "lesson"
                st.rerun()

# ── 11e. Lesson ────────────────────────────────────────
def render_lesson():
    market = st.session_state.tl_market
    style  = st.session_state.tl_style
    course = st.session_state.tl_course
    idx    = st.session_state.tl_topic_idx
    topic  = course["topics"][idx]
    tid    = topic["id"]
    all_p  = get_all_user_progress_for_course(course)

    # ── top bar ───────────────────────────────────────
    c_market, c_topic_lbl, c_prog = st.columns([1, 1, 4])
    with c_market:
        if st.button("← Markets", key="lesson_back_market"):
            st.session_state.tl_step = "market"; st.rerun()
    with c_topic_lbl:
        st.markdown(f"<div style='font-size:0.78rem;color:#556;padding-top:8px;'>"
                    f"Topic {idx+1} of {len(course['topics'])}</div>", unsafe_allow_html=True)
    with c_prog:
        passed = sum(1 for p in all_p.values() if p.get("passed"))
        _prog_bar(passed, len(course["topics"]))

    st.markdown(f"## 📖 {idx+1}. {topic['title']}")
    st.markdown(f"<div style='color:#556;font-size:0.8rem;'>⏱ ~{topic['est_min']} min read</div>",
                unsafe_allow_html=True)

    # ── Content ───────────────────────────────────────
    # Check if reteach version is active
    rk = st.session_state.tl_reteach_content.get(tid)
    if rk:
        mode_label, cached = rk
        st.markdown(f'<div class="tl-reteach">🔁 <strong>Showing: {mode_label}</strong> — '
                    f'<small style="color:#888;">AI-regenerated explanation</small></div>',
                    unsafe_allow_html=True)
        content = cached
    else:
        if not topic.get("content"):
            with st.spinner(f"🤖 Generating lesson: {topic['title']}…"):
                content = ensure_topic_content(course, idx, market, style, "standard")
        else:
            content = topic["content"]
        # Refresh course from session state (was mutated in ensure_topic_content)
        st.session_state.tl_course = course

    st.markdown(f'<div class="tl-lesson">{content}</div>', unsafe_allow_html=True)

    # ── Layer 2 — Go Deeper / Re-teach buttons ────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**🧠 Not satisfied? Go deeper or re-learn:**")
    rb1, rb2, rb3 = st.columns(3)
    with rb1:
        if st.button("🔁 Explain Simpler", key=f"simpler_{tid}", use_container_width=True):
            with st.spinner("🤖 Re-teaching in simpler language…"):
                c2 = ensure_topic_content(course, idx, market, style, "simpler")
            st.session_state.tl_reteach_content[tid] = ("Simpler Explanation", c2)
            set_user_progress(tid, {"reteach_used": True})
            st.rerun()
    with rb2:
        if st.button("🚀 Go Deeper", key=f"deeper_{tid}", use_container_width=True):
            with st.spinner("🤖 Generating advanced deep-dive…"):
                c2 = ensure_topic_content(course, idx, market, style, "deeper")
            st.session_state.tl_reteach_content[tid] = ("Advanced Deep-Dive", c2)
            set_user_progress(tid, {"reteach_used": True})
            st.rerun()
    with rb3:
        if rk:
            if st.button("↩ Show Original Lesson", key=f"orig_{tid}", use_container_width=True):
                del st.session_state.tl_reteach_content[tid]
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI Whiteboard Teacher Chat ─────────────────────
    _render_whiteboard_chat(tid, topic["title"], market, style)

    st.markdown("<br>", unsafe_allow_html=True)
    # ── CTA ───────────────────────────────────────────
    _, c_cta, _ = st.columns([2, 3, 2])
    with c_cta:
        if st.button("📝 Take Topic Exam →", key=f"go_exam_{tid}",
                     use_container_width=True, type="primary"):
            st.session_state.tl_phase = "exam"
            st.session_state.tl_step  = "exam"
            st.rerun()

# ── 11f. Exam ──────────────────────────────────────────
def render_exam():
    market = st.session_state.tl_market
    style  = st.session_state.tl_style
    course = st.session_state.tl_course
    idx    = st.session_state.tl_topic_idx
    topic  = course["topics"][idx]
    tid    = topic["id"]

    # back to lesson
    c_back, c_hdr = st.columns([1, 5])
    with c_back:
        if st.button("← Back to Lesson", key="exam_back_lesson"):
            st.session_state.tl_step  = "lesson"
            st.session_state.tl_phase = "lesson"
            st.rerun()
    with c_hdr:
        st.markdown(f"## 📝 Exam — {topic['title']}")
        st.caption("Answer all questions · 70% to pass · Retake with fresh questions")

    # ── Generate questions ────────────────────────────
    if tid not in st.session_state.tl_exam_qs:
        with st.spinner("🤖 Generating exam questions…"):
            qs = generate_exam_questions(market, style, topic["title"], n=7)
        st.session_state.tl_exam_qs[tid] = qs

    qs = st.session_state.tl_exam_qs[tid]
    submitted = tid in st.session_state.tl_submitted

    st.markdown("---")
    answers = {}

    for i, q in enumerate(qs):
        qk    = f"q_{tid}_{i}"
        livek = f"live_{tid}_{i}"
        q_type_lbl = {"mcq": "MCQ", "short_answer": "Short Answer", "scenario": "Scenario"}.get(
            q.get("type","mcq"), "MCQ")

        st.markdown('<div class="tl-q-box">', unsafe_allow_html=True)
        st.markdown(f"""<span style="background:#7b2ff722;border:1px solid #7b2ff7;border-radius:10px;
        padding:2px 9px;font-size:0.72rem;color:#a371f7;">{q_type_lbl}</span>""",
                    unsafe_allow_html=True)
        st.markdown(f"**Q{i+1}.** {q['question']}")

        if submitted:
            # Show saved answer + feedback
            saved_ans = st.session_state.tl_exam_ans.get(tid, {}).get(i, "")
            fb = st.session_state.tl_exam_fb.get(tid, {}).get(i, {})
            if q.get("options"):
                st.radio("", q["options"], key=f"disp_{qk}",
                         index=None, disabled=True, label_visibility="collapsed")
            else:
                st.text_area("", value=saved_ans, key=f"disp_{qk}",
                             disabled=True, label_visibility="collapsed", height=70)
            if fb:
                if fb.get("is_correct"):
                    st.markdown(f"""<div class="tl-ok">
                    ✅ <strong>{fb.get('short_verdict','Correct!')}</strong><br>
                    {fb.get('explanation','')} <em>· 💡 {fb.get('memory_tip','')}</em></div>""",
                                unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="tl-err">
                    ❌ <strong>{fb.get('short_verdict','Not quite')}</strong><br>
                    {fb.get('explanation','')}<br>
                    <em>🔍 {fb.get('user_error','')}</em><br>
                    <em>💡 Tip: {fb.get('memory_tip','')}</em></div>""",
                                unsafe_allow_html=True)
        else:
            if q.get("options"):
                ans = st.radio("", q["options"], key=f"ans_{qk}",
                               index=None, label_visibility="collapsed")
                answers[i] = ans
            else:
                ans = st.text_area("", key=f"ans_{qk}",
                                   placeholder="Type your answer…",
                                   label_visibility="collapsed", height=70)
                answers[i] = ans

        # ── Show Me Live button ───────────────────────
        concept = q.get("concept", topic["title"])
        if st.button(f"🔴 Show Me Live", key=f"slbtn_{qk}",
                     help="AI demonstrates this concept with a live chart"):
            st.session_state.tl_active_live = (
                "" if st.session_state.tl_active_live == livek else livek
            )
            st.rerun()

        if st.session_state.tl_active_live == livek:
            _render_live_panel(livek, concept, q["question"], market, style)

        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")

    # ── Submit / result ───────────────────────────────
    if not submitted:
        _, c_sub, _ = st.columns([2, 3, 2])
        with c_sub:
            if st.button("✅ Submit Exam", key=f"submit_{tid}",
                         use_container_width=True, type="primary"):
                missing = [i for i, a in answers.items() if not a]
                if missing:
                    st.warning(f"Answer all questions first. Missing: Q{[m+1 for m in missing]}")
                else:
                    with st.spinner("🤖 AI is grading your exam…"):
                        fb_dict = {}
                        total   = 0
                        for i, q in enumerate(qs):
                            fb = grade_answer(q, str(answers.get(i,"")), market, style)
                            fb_dict[i] = fb
                            total += fb.get("score", 0)
                        avg = int(total / len(qs))

                    st.session_state.tl_exam_ans.setdefault(tid, {}).update(answers)
                    st.session_state.tl_exam_fb[tid]   = fb_dict
                    st.session_state.tl_submitted.add(tid)

                    passed = avg >= PASS_THRESHOLD
                    prog_update = {
                        "status":        "completed" if passed else "failed",
                        "passed":        passed,
                        "best_score":    max(avg, get_user_progress(tid).get("best_score", 0)),
                        "retake_count":  get_user_progress(tid).get("retake_count", 0) + 1,
                    }
                    h = get_user_progress(tid).get("score_history", [])
                    h.append({"score": avg, "ts": datetime.now().isoformat()})
                    prog_update["score_history"] = h
                    set_user_progress(tid, prog_update)

                    # Unlock next topic
                    if passed:
                        next_topics = course["topics"]
                        if idx + 1 < len(next_topics):
                            nt = next_topics[idx + 1]
                            set_user_progress(nt["id"], {"status": "unlocked"})
                    else:
                        # Flag as weak
                        wp = st.session_state.get("tl_weak_topics", [])
                        if idx not in wp:
                            wp.append(idx)
                        st.session_state.tl_weak_topics = wp

                    st.rerun()
    else:
        _render_exam_result(tid, idx, course)

def _render_exam_result(tid: str, idx: int, course: dict):
    prog   = get_user_progress(tid)
    score  = prog.get("best_score", 0)
    passed = prog.get("passed", False)
    n_top  = len(course["topics"])

    st.markdown("---")
    if passed:
        st.markdown(f"""<div style="background:#00d4ff0d;border:1px solid #00d4ff33;
        border-radius:14px;padding:22px;text-align:center;">
        🎉 <span class="tl-score-pass">Passed! {score}%</span><br>
        <span style="color:#888;font-size:0.85rem;">Great work — next topic unlocked!</span>
        </div>""", unsafe_allow_html=True)
        st.write("")
        cl, cr = st.columns(2)
        with cl:
            if st.button("📖 Review Lesson", key=f"res_rev_{tid}", use_container_width=True):
                st.session_state.tl_step = "lesson"; st.session_state.tl_phase = "lesson"; st.rerun()
        with cr:
            if idx + 1 < n_top:
                if st.button("▶️ Next Topic →", key=f"res_nxt_{tid}",
                             use_container_width=True, type="primary"):
                    st.session_state.tl_topic_idx = idx + 1
                    st.session_state.tl_step  = "lesson"
                    st.session_state.tl_phase = "lesson"
                    st.rerun()
            else:
                st.success("🏆 Congratulations! You've completed the entire course!")
                if st.button("🎓 Course Complete! Start Over", key="done_summary", use_container_width=True):
                    st.session_state.tl_step = "market"; st.rerun()
    else:
        st.markdown(f"""<div style="background:#ff446611;border:1px solid #ff446633;
        border-radius:14px;padding:22px;text-align:center;">
        📚 <span class="tl-score-fail">{score}% — Need {PASS_THRESHOLD}% to pass</span><br>
        <span style="color:#888;font-size:0.85rem;">Review the lesson then retake with fresh questions.</span>
        </div>""", unsafe_allow_html=True)
        st.write("")
        cl, cr = st.columns(2)
        with cl:
            if st.button("📖 Re-read Lesson", key=f"res_rl_{tid}", use_container_width=True):
                st.session_state.tl_step = "lesson"; st.session_state.tl_phase = "lesson"; st.rerun()
        with cr:
            if st.button("🔄 Retake (New Qs)", key=f"res_ret_{tid}",
                         use_container_width=True, type="primary"):
                # Clear old questions & submission for fresh retake
                st.session_state.tl_exam_qs.pop(tid, None)
                st.session_state.tl_exam_ans.pop(tid, None)
                st.session_state.tl_exam_fb.pop(tid, None)
                st.session_state.tl_submitted.discard(tid)
                st.session_state.tl_step  = "exam"
                st.session_state.tl_phase = "exam"
                st.rerun()

# ── 11f-2. AI Whiteboard Teacher Chat ─────────────────
WHITEBOARD_TEACHER_SYSTEM = """You are FinSage AI Teacher — a warm, engaging trading educator who teaches like a real classroom teacher at a whiteboard.

PERSONA & STYLE:
- You are like a brilliant professor who draws on a whiteboard while explaining
- Use step-by-step explanations, like writing things out one point at a time
- Use "📋 Writing on board:" to show what you'd write on whiteboard
- Use "🎙️ Explaining:" for your verbal explanation
- Use "💡 Key Insight:" for the main point
- Use "✏️ Example:" for worked examples
- Use "❓ Check:" to ask the student a question to verify understanding
- Be warm, encouraging, patient — never condescending

LANGUAGE: Match user's language — Hindi, Hinglish, or English automatically.

TEACHING RULES:
- Teach ONE thing at a time, then ask if they understood
- Use Indian examples: NSE/BSE, ₹ amounts, Indian company names
- After explaining, ALWAYS ask: "Kya samajh aaya? Koi doubt?" or "Got it? Any questions?"
- Celebrate when student gets something right: "Bilkul sahi! 🎉" or "Perfect! 👏"
- Never give investment advice — educational only

FORMAT each response like a whiteboard session:
---
📋 [WHITEBOARD]
(What you'd write/draw — use ASCII, tables, arrows like → ↑ ↓)

🎙️ [TEACHER SAYS]
(Your verbal explanation — conversational, warm)

💡 [KEY POINT]
(The one thing to remember)

❓ [CHECK]
(A simple question to verify understanding)
---

Keep responses focused and not too long — this is interactive teaching, not a lecture."""

def _whiteboard_greeting(topic_title: str, market: str, style: str) -> str:
    """Generate the opening teacher message for a topic."""
    lang = st.session_state.get("user_lang", "en")
    lang_note = {
        "hi": "Respond in Hindi/Hinglish.",
        "te": "Respond in Telugu mixed with English.",
        "ta": "Respond in Tamil mixed with English.",
    }.get(lang, "Respond in English.")

    prompt = f"""You are starting a whiteboard teaching session for: **{topic_title}**
Market: {market} | Style: {style}
{lang_note}

Open the session like a real teacher:
1. Greet the student warmly (1-2 lines)
2. Write the topic title on the whiteboard: 📋 [WHITEBOARD]: {topic_title}
3. Ask them ONE question to gauge their current knowledge before teaching
   Example: "Pehle mujhe batao — {topic_title} ke baare mein aapne pehle kuch suna hai?"

Keep it short (4-6 lines total). Be warm and inviting.
End with a question to start the dialogue."""

    return ai_text(prompt, WHITEBOARD_TEACHER_SYSTEM, max_tokens=350)

def _whiteboard_respond(history: list, student_msg: str,
                        topic_title: str, market: str, style: str) -> str:
    """Generate teacher response to student input."""
    lang = st.session_state.get("user_lang", "en")
    lang_note = {
        "hi": "Respond in Hindi/Hinglish.",
        "te": "Respond in Telugu mixed with English.",
        "ta": "Respond in Tamil mixed with English.",
    }.get(lang, "Respond in English.")

    # Build conversation context
    ctx = []
    for m in history[-6:]:  # last 6 messages for context
        role = "assistant" if m["role"] == "teacher" else "user"
        ctx.append({"role": role, "content": m["content"]})
    ctx.append({"role": "user", "content": student_msg})

    system = (WHITEBOARD_TEACHER_SYSTEM +
              f"\n\nCurrent topic: {topic_title} | Market: {market} | Style: {style} | {lang_note}")

    msgs = [{"role": "system", "content": system}] + ctx

    k = os.environ.get("GROQ_API_KEY","") or os.environ.get("GROW_API_KEY","")
    try:
        import requests as _req
        r = _req.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": msgs,
                  "temperature": 0.7, "max_tokens": 600},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Teacher error: {e}"

def _render_whiteboard_chat(tid: str, topic_title: str, market: str, style: str):
    """Render the AI Whiteboard Teacher chat section below a lesson."""
    # Init state for this topic
    if tid not in st.session_state.tl_whiteboard_chats:
        st.session_state.tl_whiteboard_chats[tid] = []
    if tid not in st.session_state.tl_wb_open:
        st.session_state.tl_wb_open[tid] = False

    history = st.session_state.tl_whiteboard_chats[tid]
    is_open = st.session_state.tl_wb_open.get(tid, False)

    # ── Toggle button ──────────────────────────────────
    toggle_label = ("🎓 Chat with AI Teacher — Ask anything about this chapter ▼"
                    if not is_open else
                    "🎓 AI Whiteboard Teacher (Active) ▲")

    st.markdown("""<div style="margin: 24px 0 8px;">
    <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(0,212,255,0.3),transparent);
    margin-bottom:14px;"></div></div>""", unsafe_allow_html=True)

    if st.button(toggle_label, key=f"wb_toggle_{tid}", use_container_width=True, type="secondary"):
        st.session_state.tl_wb_open[tid] = not is_open
        # Auto-open: generate greeting if first time
        if not st.session_state.tl_wb_open[tid] is False and not history:
            pass  # greeting generated below
        st.rerun()

    if not st.session_state.tl_wb_open.get(tid, False):
        return

    # ── Whiteboard container ───────────────────────────
    st.markdown("""<div class="wb-container">
    <div class="wb-header">
        <div class="wb-live-dot"></div>
        <div>
            <div class="wb-header-title">🎓 AI Whiteboard Teacher</div>
            <div class="wb-header-sub">Interactive teaching session — ask anything, learn step by step</div>
        </div>
    </div>
    </div>""", unsafe_allow_html=True)

    # ── Auto-greeting (first open) ─────────────────────
    if not history:
        with st.spinner("🎓 Teacher preparing the whiteboard..."):
            greeting = _whiteboard_greeting(topic_title, market, style)
        history.append({"role": "teacher", "content": greeting})
        st.session_state.tl_whiteboard_chats[tid] = history
        st.rerun()

    # ── Message history ────────────────────────────────
    for msg in history:
        if msg["role"] == "teacher":
            st.markdown(f'<div class="wb-msg-teacher">{msg["content"]}</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="wb-msg-student">{msg["content"]}</div>',
                        unsafe_allow_html=True)

    st.write("")

    # ── Quick ask chips ────────────────────────────────
    quick_asks = [
        f"Explain {topic_title} in very simple words",
        "Ek aur example do",
        "Yeh concept practically kaise use karein?",
        "Indian market mein kaise apply hota hai?",
        "Main confused hoon — phir se samjhao",
        "Quiz me — ek question poocho",
    ]
    st.markdown("**💬 Quick questions:**")
    qa_cols = st.columns(3)
    for i, qa in enumerate(quick_asks):
        with qa_cols[i % 3]:
            if st.button(qa[:38], key=f"wbqa_{tid}_{i}", use_container_width=True):
                history.append({"role": "student", "content": qa})
                st.session_state.tl_whiteboard_chats[tid] = history
                with st.spinner("🎓 Teacher thinking..."):
                    reply = _whiteboard_respond(history, qa, topic_title, market, style)
                history.append({"role": "teacher", "content": reply})
                st.session_state.tl_whiteboard_chats[tid] = history
                st.rerun()

    # ── Free text input ────────────────────────────────
    st.write("")
    col_inp, col_send = st.columns([5, 1])
    with col_inp:
        student_q = st.text_input(
            "", key=f"wb_inp_{tid}",
            placeholder="Type your question or response to the teacher...",
            label_visibility="collapsed"
        )
    with col_send:
        if st.button("Send 📤", key=f"wb_send_{tid}", use_container_width=True, type="primary"):
            if student_q.strip():
                history.append({"role": "student", "content": student_q.strip()})
                st.session_state.tl_whiteboard_chats[tid] = history
                with st.spinner("🎓 Teacher responding..."):
                    reply = _whiteboard_respond(history, student_q.strip(),
                                                topic_title, market, style)
                history.append({"role": "teacher", "content": reply})
                st.session_state.tl_whiteboard_chats[tid] = history
                st.rerun()

    # ── Clear session ──────────────────────────────────
    if len(history) > 2:
        if st.button("🔄 Reset Chat", key=f"wb_clear_{tid}"):
            st.session_state.tl_whiteboard_chats[tid] = []
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

# ── 11g. Live demo panel ───────────────────────────────
def _render_live_panel(live_key: str, concept: str, q_text: str,
                       market: str, style: str):
    if live_key not in st.session_state.tl_live_chats:
        st.session_state.tl_live_chats[live_key] = []

    history = st.session_state.tl_live_chats[live_key]

    st.markdown('<div class="tl-live">', unsafe_allow_html=True)
    st.markdown(f"#### 🔴 Live Demo — *{concept}*")

    # Auto-generate first message
    if not history:
        sys_v = (f"You are FinSage Visual AI Tutor. Market: {market} | Style: {style}. "
                 f"{lang_instr()} Explain the concept visually referencing the chart "
                 f"that will be shown below. Be specific about chart values, patterns, zones. "
                 "Mention candle color, indicator values, S/R levels where relevant.")
        prompt = (f"Show me a live visual explanation of: **{concept}**\n"
                  f"Context — exam question: {q_text}\n"
                  "Describe what you see in the chart, what pattern it forms, and what a trader should do.")
        with st.spinner("🤖 Generating visual explanation…"):
            reply = ai_visual(prompt, sys_v)
        history.append({"role": "ai", "content": reply})
        st.session_state.tl_live_chats[live_key] = history

    # Show chart
    fig = render_demo_chart(concept, f"Live Example: {concept}")
    st.plotly_chart(fig, use_container_width=True)

    # Chat history
    for msg in history:
        if msg["role"] == "ai":
            st.markdown(f"""<div style="background:#0d2040;border-radius:8px;
            padding:13px;margin:7px 0;">🤖 <strong>FinSage AI</strong><br>{msg['content']}</div>""",
                        unsafe_allow_html=True)
        else:
            st.markdown(f"""<div style="background:#1a2744;border-radius:8px;
            padding:11px;margin:7px 0;text-align:right;">
            👤 <strong>You</strong>: {msg['content']}</div>""",
                        unsafe_allow_html=True)

    # Follow-up
    followup = st.text_input("Ask a follow-up…", key=f"fu_{live_key}",
                             placeholder="e.g. Why is this bearish? Show another example.")
    c_send, c_close = st.columns([2, 1])
    with c_send:
        if st.button("Send 📤", key=f"send_{live_key}", use_container_width=True):
            if followup.strip():
                history.append({"role": "user", "content": followup})
                sys_v2 = (f"You are FinSage Visual AI Tutor continuing a chart discussion. "
                          f"Market: {market} | Style: {style}. {lang_instr()} "
                          f"Stay focused on: {concept}.")
                prev = "\n".join(f"{'AI' if m['role']=='ai' else 'User'}: {m['content'][:200]}"
                                 for m in history[-4:])
                with st.spinner("Thinking…"):
                    reply = ai_visual(
                        f"Previous context:\n{prev}\n\nFollow-up: {followup}", sys_v2)
                history.append({"role": "ai", "content": reply})
                st.session_state.tl_live_chats[live_key] = history
                st.rerun()
    with c_close:
        if st.button("❌ Close", key=f"cls_{live_key}", use_container_width=True):
            st.session_state.tl_active_live = ""
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# 12.  MAIN ENTRY POINT
# ══════════════════════════════════════════════════════
def show_trading_learning():
    """Call this from app.py to render the full learning module."""
    st.markdown(TL_CSS, unsafe_allow_html=True)
    init_tl_state()

    step = st.session_state.tl_step

    if step == "market":
        render_market_select()
    elif step == "style":
        render_style_select()
    elif step in ("toc", "lesson", "exam"):
        # Weak topic warning only
        weak = st.session_state.get("tl_weak_topics", [])
        course = st.session_state.tl_course
        if weak and course:
            titles = [course["topics"][i]["title"][:22] for i in weak
                      if i < len(course["topics"])]
            st.warning(f"⚠️ Weak areas: {', '.join(titles)} — consider revisiting them.")

        phase = st.session_state.tl_phase
        if phase == "lesson":
            render_lesson()
        else:
            render_exam()
