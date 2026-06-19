"""
FinSage - AI Trading Learning Module
=====================================
Drop this file into your FinSage project and import it in your main app.
Requires: openai, google-generativeai, plotly, pandas, streamlit
API Keys via environment variables:
  OPENAI_API_KEY   — for GPT-4o (teaching, grading, Q&A)
  GEMINI_API_KEY   — for chart/visual explanations
"""

import streamlit as st
import json
import random
import os
import time
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from openai import OpenAI
import google.generativeai as genai

# ─────────────────────────────────────────────
# AI CLIENT SETUP
# ─────────────────────────────────────────────
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")

def call_llm(prompt: str, system: str = "", model: str = "gpt-4o") -> str:
    """Primary LLM call via OpenAI."""
    client = get_openai_client()
    if not client:
        return "⚠️ OpenAI API key not configured. Please set OPENAI_API_KEY in your environment."
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI Error: {str(e)}"

def call_gemini(prompt: str) -> str:
    """Gemini call for chart/visual explanations."""
    client = get_gemini_client()
    if not client:
        # Fallback to OpenAI if Gemini not configured
        return call_llm(prompt)
    try:
        response = client.generate_content(prompt)
        return response.text
    except Exception as e:
        # Fallback to OpenAI
        return call_llm(prompt)

# ─────────────────────────────────────────────
# LANGUAGE SUPPORT
# ─────────────────────────────────────────────
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

LANG_INSTRUCTIONS = {
    "en": "Respond in English.",
    "hi": "हिंदी में जवाब दो। (Respond in Hindi.)",
    "te": "తెలుగులో సమాధానం ఇవ్వండి. (Respond in Telugu.)",
    "ta": "தமிழில் பதில் அளிக்கவும். (Respond in Tamil.)",
    "bn": "বাংলায় উত্তর দিন। (Respond in Bengali.)",
    "mr": "मराठीत उत्तर द्या. (Respond in Marathi.)",
    "pa": "ਪੰਜਾਬੀ ਵਿੱਚ ਜਵਾਬ ਦਿਓ। (Respond in Punjabi.)",
    "gu": "ગુજરાતીમાં જવાબ આપો. (Respond in Gujarati.)",
    "es": "Responde en español. (Respond in Spanish.)",
    "fr": "Réponds en français. (Respond in French.)",
}

def lang_instruction():
    lang_code = st.session_state.get("learn_lang", "en")
    return LANG_INSTRUCTIONS.get(lang_code, "Respond in English.")

# ─────────────────────────────────────────────
# CURRICULUM DATA
# ─────────────────────────────────────────────
MARKET_STYLES = {
    "📈 Stock Market": {
        "icon": "📈",
        "styles": {
            "⚡ Intraday Trading": "Buy and sell within the same day. Fast-paced, uses technical analysis.",
            "🔄 Swing Trading": "Hold trades for days to weeks. Captures medium-term price swings.",
            "📊 Options Trading": "Trade contracts, not shares. Leverage, hedging, and income strategies.",
            "🏦 Long-term Investing": "Hold for months to years. Fundamental analysis, wealth building.",
        }
    },
    "₿ Crypto Market": {
        "icon": "₿",
        "styles": {
            "🪙 Spot Trading": "Buy/sell actual crypto. Simple, no leverage. Good for beginners.",
            "📉 Futures/Margin Trading": "Trade with leverage. High risk, high reward. For experienced traders.",
            "🔄 Swing Trading": "Ride crypto trends over days/weeks. Technical + sentiment analysis.",
            "🌐 DeFi/Staking & Long-term": "Earn yield, stake tokens, hold for the long term.",
        }
    },
    "💱 Forex Market": {
        "icon": "💱",
        "styles": {
            "⚡ Scalping": "Dozens of quick trades per day. Tiny profits per trade, high volume.",
            "☀️ Day Trading": "Open and close all positions within one trading day.",
            "🔄 Swing Trading": "Multi-day trades following currency trends.",
            "📌 Position Trading": "Long-term holds based on macroeconomics and fundamentals.",
        }
    }
}

# Topics per market+style (AI fills in the actual content)
TOPIC_TEMPLATES = [
    "Introduction & Foundations",
    "How the Market Works",
    "Key Terminology",
    "Reading Candlestick Charts",
    "Technical Indicators (RSI, MACD, Moving Averages)",
    "Chart Patterns (Head & Shoulders, Double Top, Flags)",
    "Support & Resistance Levels",
    "Strategy-Specific Techniques",
    "Entry & Exit Rules",
    "Risk Management & Position Sizing",
    "Trading Psychology & Discipline",
    "Building Your Trading Plan",
]

# ─────────────────────────────────────────────
# STATE MANAGEMENT
# ─────────────────────────────────────────────
def init_learn_state():
    defaults = {
        "learn_step": "language",       # language → market → style → curriculum → exam → live_chat
        "learn_lang": "en",
        "learn_market": None,
        "learn_style": None,
        "learn_topics": [],
        "learn_current_topic_idx": 0,
        "learn_lesson_content": {},      # topic_idx -> lesson text
        "learn_exam_questions": {},      # topic_idx -> list of questions
        "learn_exam_answers": {},        # topic_idx -> {q_idx: user_answer}
        "learn_exam_scores": {},         # topic_idx -> score (0-100)
        "learn_exam_feedback": {},       # topic_idx -> {q_idx: feedback}
        "learn_exam_passed": {},         # topic_idx -> bool
        "learn_weak_topics": [],
        "learn_live_chat": {},           # q_key -> list of messages
        "learn_active_live_q": None,
        "learn_phase": "lesson",        # lesson | exam | result
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ─────────────────────────────────────────────
# CSS STYLING
# ─────────────────────────────────────────────
LEARN_CSS = """
<style>
.learn-card {
    background: linear-gradient(135deg, #0d1b2a 0%, #1a2744 100%);
    border: 1px solid #00d4ff33;
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    cursor: pointer;
    transition: all 0.3s ease;
}
.learn-card:hover {
    border-color: #00d4ff;
    box-shadow: 0 0 20px #00d4ff44;
}
.learn-market-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #00d4ff;
}
.learn-progress-bar {
    background: #1a2744;
    border-radius: 50px;
    height: 8px;
    overflow: hidden;
    margin: 10px 0;
}
.learn-progress-fill {
    background: linear-gradient(90deg, #00d4ff, #7b2ff7);
    height: 100%;
    border-radius: 50px;
    transition: width 0.5s ease;
}
.topic-badge {
    background: #7b2ff722;
    border: 1px solid #7b2ff7;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.8rem;
    color: #7b2ff7;
    display: inline-block;
}
.topic-badge.completed {
    background: #00d4ff22;
    border-color: #00d4ff;
    color: #00d4ff;
}
.topic-badge.failed {
    background: #ff444422;
    border-color: #ff4444;
    color: #ff4444;
}
.exam-question-box {
    background: #0d1b2a;
    border-left: 3px solid #00d4ff;
    border-radius: 0 8px 8px 0;
    padding: 15px;
    margin: 15px 0;
}
.ai-feedback-correct {
    background: #00d4ff11;
    border: 1px solid #00d4ff55;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
}
.ai-feedback-wrong {
    background: #ff444411;
    border: 1px solid #ff444455;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
}
.live-chat-panel {
    background: #0a1628;
    border: 1px solid #7b2ff7;
    border-radius: 12px;
    padding: 15px;
    margin-top: 10px;
}
.lesson-content {
    background: #0d1b2a;
    border-radius: 12px;
    padding: 25px;
    line-height: 1.8;
    color: #e0e0e0;
}
.wizard-header {
    text-align: center;
    padding: 20px 0;
    border-bottom: 1px solid #00d4ff22;
    margin-bottom: 25px;
}
</style>
"""

# ─────────────────────────────────────────────
# CHART GENERATORS
# ─────────────────────────────────────────────
def generate_sample_candlestick(days=30, pattern_hint=""):
    """Generate a realistic-looking sample candlestick chart."""
    np.random.seed(42)
    dates = [datetime.now() - timedelta(days=days - i) for i in range(days)]
    
    price = 100.0
    opens, highs, lows, closes, volumes = [], [], [], [], []
    
    for i in range(days):
        change = np.random.randn() * 2
        open_p = price
        close_p = price + change
        high_p = max(open_p, close_p) + abs(np.random.randn() * 0.8)
        low_p = min(open_p, close_p) - abs(np.random.randn() * 0.8)
        vol = int(np.random.uniform(800000, 2000000))
        
        opens.append(open_p)
        closes.append(close_p)
        highs.append(high_p)
        lows.append(low_p)
        volumes.append(vol)
        price = close_p
    
    df = pd.DataFrame({
        "Date": dates, "Open": opens, "High": highs,
        "Low": lows, "Close": closes, "Volume": volumes
    })
    
    # RSI calculation
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # MACD
    df["EMA12"] = df["Close"].ewm(span=12).mean()
    df["EMA26"] = df["Close"].ewm(span=26).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean() if days >= 50 else df["Close"].rolling(days // 2).mean()
    
    return df

def plot_candlestick_with_indicators(df, title="Sample Chart", show_rsi=False, show_macd=False, show_sr=False):
    """Build a full interactive Plotly chart with optional indicators."""
    rows = 1
    specs = [[{"secondary_y": False}]]
    row_heights = [0.7]
    
    if show_rsi:
        rows += 1
        specs.append([{"secondary_y": False}])
        row_heights.append(0.15)
    if show_macd:
        rows += 1
        specs.append([{"secondary_y": False}])
        row_heights.append(0.15)
    
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                        vertical_spacing=0.04, row_heights=row_heights,
                        subplot_titles=[title] + (["RSI (14)"] if show_rsi else []) + (["MACD"] if show_macd else []))
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df["Date"], open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        increasing_line_color="#00d4ff", decreasing_line_color="#ff4444",
        name="Price"
    ), row=1, col=1)
    
    # Moving averages
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MA20"], line=dict(color="#f7b731", width=1), name="MA20"), row=1, col=1)
    
    # Support/Resistance
    if show_sr:
        support = df["Low"].rolling(5).min().iloc[-1]
        resistance = df["High"].rolling(5).max().iloc[-1]
        fig.add_hline(y=support, line_dash="dash", line_color="#00ff88", annotation_text="Support", row=1, col=1)
        fig.add_hline(y=resistance, line_dash="dash", line_color="#ff4444", annotation_text="Resistance", row=1, col=1)
    
    row_idx = 2
    # RSI panel
    if show_rsi:
        fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], line=dict(color="#7b2ff7", width=1.5), name="RSI"), row=row_idx, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ff4444", row=row_idx, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00d4ff", row=row_idx, col=1)
        row_idx += 1
    
    # MACD panel
    if show_macd:
        fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], line=dict(color="#00d4ff", width=1.5), name="MACD"), row=row_idx, col=1)
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], line=dict(color="#f7b731", width=1.5), name="Signal"), row=row_idx, col=1)
        macd_hist = df["MACD"] - df["Signal"]
        fig.add_trace(go.Bar(x=df["Date"], y=macd_hist, 
                             marker_color=["#00d4ff" if v >= 0 else "#ff4444" for v in macd_hist],
                             name="Histogram"), row=row_idx, col=1)
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1b2a",
        plot_bgcolor="#0d1b2a",
        xaxis_rangeslider_visible=False,
        height=400 + (100 * (rows - 1)),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=1.05),
        font=dict(color="#e0e0e0")
    )
    return fig

# ─────────────────────────────────────────────
# AI FUNCTIONS
# ─────────────────────────────────────────────
def generate_lesson(market, style, topic, topic_idx, total_topics, user_level="beginner"):
    """Generate a lesson for a specific topic."""
    system = f"""You are FinSage AI Tutor — an expert trading educator. 
You teach trading clearly, practically, and engagingly.
Market: {market} | Style: {style}
{lang_instruction()}
Keep lessons structured with:
1. Core concept explanation
2. Real-world example
3. Key takeaways (bullet points)
4. Common beginner mistakes to avoid
Format with emojis and clear sections. Keep it conversational and engaging."""
    
    prompt = f"""Teach me Topic {topic_idx+1} of {total_topics}: **{topic}**
for {style} in the {market}.
User level: {user_level}.
Make it practical, not theoretical. Include specific numbers/percentages where relevant."""
    
    return call_llm(prompt, system)

def generate_exam_questions(market, style, topic, num_questions=7):
    """Generate exam questions for a topic."""
    system = f"""You are an expert trading exam creator.
Market: {market} | Style: {style} | Topic: {topic}
{lang_instruction()}
Create exactly {num_questions} questions. Return ONLY valid JSON, no other text.
Format:
{{
  "questions": [
    {{
      "id": 1,
      "type": "mcq",
      "question": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "A",
      "concept": "brief concept tag for Show Me Live"
    }},
    {{
      "id": 2,
      "type": "short_answer",
      "question": "...",
      "options": null,
      "correct_answer": "...",
      "concept": "brief concept tag"
    }},
    {{
      "id": 3,
      "type": "scenario",
      "question": "Scenario: ... What would you do?",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "B",
      "concept": "concept tag"
    }}
  ]
}}
Mix MCQ (4), short answer (2), scenario (1). Make questions test real understanding, not just memorization."""
    
    prompt = f"Create {num_questions} exam questions about: {topic}"
    
    response = call_llm(prompt, system, model="gpt-4o")
    try:
        # Clean up response
        response = response.strip()
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        data = json.loads(response)
        return data.get("questions", [])
    except:
        # Fallback hardcoded questions
        return [
            {"id": 1, "type": "mcq", "question": f"What is the primary goal of {topic}?",
             "options": ["A. Maximize profit at any cost", "B. Consistent, disciplined trading", "C. Trade as often as possible", "D. Avoid all risk"],
             "correct_answer": "B", "concept": topic},
            {"id": 2, "type": "short_answer", "question": f"Explain in your own words what {topic} means in the context of {style}.",
             "options": None, "correct_answer": f"Understanding of {topic} applied to {style}.", "concept": topic},
        ]

def grade_answer(question, user_answer, market, style):
    """Grade a single answer and provide feedback."""
    system = f"""You are a strict but encouraging trading exam grader.
Market: {market} | Style: {style}
{lang_instruction()}
Be specific, educational, and constructive in feedback.
Return ONLY valid JSON."""
    
    q_type = question.get("type", "mcq")
    correct = question.get("correct_answer", "")
    
    prompt = f"""Grade this answer:
Question: {question['question']}
Question Type: {q_type}
{"Options: " + str(question.get('options')) if question.get('options') else ""}
Correct Answer: {correct}
User's Answer: {user_answer}

Return JSON:
{{
  "is_correct": true/false,
  "score": 0-100,
  "short_verdict": "Correct!" or "Not quite.",
  "explanation": "Why the correct answer is right (2-3 sentences)",
  "user_error": "What the user got wrong (if incorrect, else null)",
  "memory_tip": "A practical tip to remember this concept",
  "encouragement": "Brief encouraging message"
}}"""
    
    response = call_llm(prompt, system, model="gpt-4o")
    try:
        response = response.strip()
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        return json.loads(response)
    except:
        is_correct = user_answer.strip().upper().startswith(correct.strip().upper()[:1]) if correct else False
        return {
            "is_correct": is_correct,
            "score": 100 if is_correct else 0,
            "short_verdict": "Correct! ✅" if is_correct else "Not quite. ❌",
            "explanation": f"The correct answer is: {correct}",
            "user_error": None if is_correct else f"You answered: {user_answer}",
            "memory_tip": "Review this concept in the lesson.",
            "encouragement": "Keep going! 💪"
        }

def get_live_demo(concept, question_text, follow_up="", market="", style=""):
    """Get AI explanation + determine which chart type to show."""
    show_rsi = any(kw in (concept + question_text + follow_up).lower() for kw in ["rsi", "relative strength", "overbought", "oversold"])
    show_macd = any(kw in (concept + question_text + follow_up).lower() for kw in ["macd", "moving average convergence", "momentum"])
    show_sr = any(kw in (concept + question_text + follow_up).lower() for kw in ["support", "resistance", "level", "zone"])
    show_candle = any(kw in (concept + question_text + follow_up).lower() for kw in ["candlestick", "candle", "pattern", "engulf", "doji", "hammer", "bullish", "bearish"])
    
    system = f"""You are FinSage AI Visual Tutor — you explain trading concepts using charts and visual examples.
Market: {market} | Style: {style}
{lang_instruction()}
The user clicked "Show Me Live" while studying: {concept}
You are showing them a chart and explaining it visually.
Be specific about what they see in the chart. Reference actual values, patterns, zones.
Format your response with clear sections and emojis."""
    
    user_msg = follow_up if follow_up else f"Show me a live example of: {concept}\nRelated to this question: {question_text}"
    
    explanation = call_gemini(f"{system}\n\n{user_msg}")
    
    return explanation, show_rsi, show_macd, show_sr, (show_candle or not any([show_rsi, show_macd, show_sr]))

# ─────────────────────────────────────────────
# UI COMPONENTS
# ─────────────────────────────────────────────
def render_progress_bar(current, total):
    pct = int((current / total) * 100) if total > 0 else 0
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin:10px 0;">
        <span style="color:#888; font-size:0.85rem;">Topic {current} of {total}</span>
        <div class="learn-progress-bar" style="flex:1;">
            <div class="learn-progress-fill" style="width:{pct}%;"></div>
        </div>
        <span style="color:#00d4ff; font-size:0.85rem; font-weight:700;">{pct}%</span>
    </div>
    """, unsafe_allow_html=True)

def render_topic_list():
    topics = st.session_state.learn_topics
    current = st.session_state.learn_current_topic_idx
    scores = st.session_state.learn_exam_scores
    passed = st.session_state.learn_exam_passed
    
    cols = st.columns(3)
    for i, topic in enumerate(topics):
        col = cols[i % 3]
        with col:
            if i < current:
                score = scores.get(i, 0)
                badge_class = "completed" if passed.get(i) else "failed"
                icon = "✅" if passed.get(i) else "❌"
                st.markdown(f'<span class="topic-badge {badge_class}">{icon} {i+1}. {topic[:20]}... ({score}%)</span>', unsafe_allow_html=True)
            elif i == current:
                st.markdown(f'<span class="topic-badge" style="background:#00d4ff22; border-color:#00d4ff; color:#00d4ff;">📖 {i+1}. {topic[:20]}...</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="topic-badge" style="opacity:0.4;">🔒 {i+1}. {topic[:20]}...</span>', unsafe_allow_html=True)

def render_live_chat_panel(q_key, concept, question_text, market, style):
    """Render the inline AI chat panel for Show Me Live."""
    if q_key not in st.session_state.learn_live_chat:
        st.session_state.learn_live_chat[q_key] = []
    
    chat_history = st.session_state.learn_live_chat[q_key]
    
    st.markdown('<div class="live-chat-panel">', unsafe_allow_html=True)
    st.markdown(f"### 🔴 Live Demo — *{concept}*")
    
    # Auto-generate first message if chat is empty
    if not chat_history:
        with st.spinner("🤖 Generating live visual explanation..."):
            explanation, show_rsi, show_macd, show_sr, show_candle = get_live_demo(
                concept, question_text, "", market, style
            )
            chat_history.append({
                "role": "ai",
                "content": explanation,
                "chart": {"show_rsi": show_rsi, "show_macd": show_macd, "show_sr": show_sr, "show_candle": show_candle}
            })
            st.session_state.learn_live_chat[q_key] = chat_history
    
    # Display chat history
    for msg in chat_history:
        if msg["role"] == "ai":
            st.markdown(f"""<div style="background:#0d1b2a; border-radius:8px; padding:15px; margin:8px 0;">
            🤖 <strong>FinSage AI</strong><br>{msg['content']}</div>""", unsafe_allow_html=True)
            
            # Show chart
            if msg.get("chart"):
                c = msg["chart"]
                df = generate_sample_candlestick(30)
                fig = plot_candlestick_with_indicators(
                    df,
                    title=f"Live Example: {concept}",
                    show_rsi=c.get("show_rsi", False),
                    show_macd=c.get("show_macd", False),
                    show_sr=c.get("show_sr", False)
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(f"""<div style="background:#1a2744; border-radius:8px; padding:12px; margin:8px 0; text-align:right;">
            👤 <strong>You</strong>: {msg['content']}</div>""", unsafe_allow_html=True)
    
    # Follow-up input
    follow_up_key = f"followup_{q_key}"
    follow_up = st.text_input(
        "Ask a follow-up question...",
        key=follow_up_key,
        placeholder="e.g., Why is this pattern bullish? Show me another example."
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Send 📤", key=f"send_{q_key}"):
            if follow_up.strip():
                chat_history.append({"role": "user", "content": follow_up})
                with st.spinner("Thinking..."):
                    explanation, show_rsi, show_macd, show_sr, show_candle = get_live_demo(
                        concept, question_text, follow_up, market, style
                    )
                    chat_history.append({
                        "role": "ai",
                        "content": explanation,
                        "chart": {"show_rsi": show_rsi, "show_macd": show_macd, "show_sr": show_sr, "show_candle": show_candle}
                    })
                    st.session_state.learn_live_chat[q_key] = chat_history
                    st.rerun()
    with col2:
        if st.button("❌ Close Demo", key=f"close_{q_key}"):
            st.session_state.learn_active_live_q = None
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE RENDERS
# ─────────────────────────────────────────────
def render_language_select():
    st.markdown('<div class="wizard-header">', unsafe_allow_html=True)
    st.markdown("# 🌐 Choose Your Language")
    st.markdown("*Select the language you want to learn trading in*")
    st.markdown("</div>", unsafe_allow_html=True)
    
    lang_cols = st.columns(4)
    for i, (lang_name, lang_code) in enumerate(LANGUAGES.items()):
        with lang_cols[i % 4]:
            if st.button(lang_name, key=f"lang_{lang_code}", use_container_width=True):
                st.session_state.learn_lang = lang_code
                st.session_state.learn_step = "market"
                st.rerun()

def render_market_select():
    st.markdown('<div class="wizard-header">', unsafe_allow_html=True)
    st.markdown("# 📚 AI Trading Academy")
    st.markdown("*Structured learning from beginner to advanced — powered by AI*")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("### Step 1 — Choose Your Market")
    st.markdown("Which market do you want to master?")
    st.write("")
    
    for market_name, market_data in MARKET_STYLES.items():
        col1, col2 = st.columns([5, 1])
        with col1:
            style_list = ", ".join(list(market_data["styles"].keys())[:2]) + "..."
            st.markdown(f"""<div class="learn-card">
            <div class="learn-market-title">{market_name}</div>
            <div style="color:#888; font-size:0.9rem; margin-top:5px;">Styles: {style_list}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.write("")
            st.write("")
            if st.button("Select →", key=f"market_{market_name}", use_container_width=True):
                st.session_state.learn_market = market_name
                st.session_state.learn_step = "style"
                st.rerun()

def render_style_select():
    market = st.session_state.learn_market
    market_data = MARKET_STYLES[market]
    
    st.markdown('<div class="wizard-header">', unsafe_allow_html=True)
    st.markdown(f"# {market}")
    st.markdown("### Step 2 — Choose Your Trading Style")
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("← Back to Market Selection"):
        st.session_state.learn_step = "market"
        st.rerun()
    
    st.write("")
    for style_name, style_desc in market_data["styles"].items():
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"""<div class="learn-card">
            <div style="font-size:1.1rem; font-weight:600; color:#e0e0e0;">{style_name}</div>
            <div style="color:#888; font-size:0.85rem; margin-top:5px;">{style_desc}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.write("")
            st.write("")
            if st.button("Start →", key=f"style_{style_name}", use_container_width=True):
                st.session_state.learn_style = style_name
                # Build curriculum topics
                st.session_state.learn_topics = TOPIC_TEMPLATES.copy()
                st.session_state.learn_current_topic_idx = 0
                st.session_state.learn_phase = "lesson"
                st.session_state.learn_step = "curriculum"
                st.rerun()

def render_lesson():
    """Render the lesson view for the current topic."""
    market = st.session_state.learn_market
    style = st.session_state.learn_style
    topics = st.session_state.learn_topics
    idx = st.session_state.learn_current_topic_idx
    topic = topics[idx]
    
    # Progress
    render_progress_bar(idx + 1, len(topics))
    
    # Breadcrumb
    st.markdown(f"""<div style="color:#888; font-size:0.85rem; margin-bottom:15px;">
    {market} → {style} → Topic {idx+1}: {topic}
    </div>""", unsafe_allow_html=True)
    
    # Topic overview chips
    with st.expander("📋 All Topics (click to expand)", expanded=False):
        render_topic_list()
    
    st.markdown(f"## 📖 Topic {idx+1}: {topic}")
    
    # Generate or use cached lesson
    lesson_key = f"{market}_{style}_{idx}"
    if lesson_key not in st.session_state.learn_lesson_content:
        with st.spinner(f"🤖 AI Tutor is preparing your lesson on **{topic}**..."):
            user_level = "beginner" if idx < 3 else ("intermediate" if idx < 8 else "advanced")
            lesson = generate_lesson(market, style, topic, idx, len(topics), user_level)
            st.session_state.learn_lesson_content[lesson_key] = lesson
    
    lesson_text = st.session_state.learn_lesson_content[lesson_key]
    
    st.markdown(f'<div class="lesson-content">{lesson_text}</div>', unsafe_allow_html=True)
    
    st.write("")
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        if st.button("📝 Take Topic Exam →", use_container_width=True, type="primary"):
            st.session_state.learn_phase = "exam"
            st.rerun()

def render_exam():
    """Render the exam for the current topic."""
    market = st.session_state.learn_market
    style = st.session_state.learn_style
    topics = st.session_state.learn_topics
    idx = st.session_state.learn_current_topic_idx
    topic = topics[idx]
    
    render_progress_bar(idx + 1, len(topics))
    
    st.markdown(f"## 📝 Exam — Topic {idx+1}: {topic}")
    st.markdown("*Answer all questions. Pass 70% to unlock the next topic.*")
    st.markdown("---")
    
    # Generate or use cached questions
    exam_key = f"exam_{market}_{style}_{idx}"
    if exam_key not in st.session_state.learn_exam_questions:
        with st.spinner("🤖 Generating personalized exam questions..."):
            questions = generate_exam_questions(market, style, topic, num_questions=7)
            st.session_state.learn_exam_questions[exam_key] = questions
    
    questions = st.session_state.learn_exam_questions[exam_key]
    submitted_key = f"submitted_{exam_key}"
    
    if not questions:
        st.error("Failed to generate questions. Please try again.")
        if st.button("Retry"):
            del st.session_state.learn_exam_questions[exam_key]
            st.rerun()
        return
    
    answers = {}
    
    for i, q in enumerate(questions):
        q_key = f"q_{exam_key}_{i}"
        live_key = f"live_{exam_key}_{i}"
        
        st.markdown(f'<div class="exam-question-box">', unsafe_allow_html=True)
        
        q_type_label = {"mcq": "MCQ", "short_answer": "Short Answer", "scenario": "Scenario"}.get(q.get("type"), "")
        st.markdown(f"""<span style="background:#7b2ff722; border:1px solid #7b2ff7; border-radius:12px; 
        padding:2px 10px; font-size:0.75rem; color:#7b2ff7;">{q_type_label}</span>""", unsafe_allow_html=True)
        
        st.markdown(f"**Q{i+1}. {q['question']}**")
        
        # Already submitted — show feedback
        if submitted_key in st.session_state:
            feedback = st.session_state.learn_exam_feedback.get(exam_key, {}).get(i, {})
            saved_answer = st.session_state.learn_exam_answers.get(exam_key, {}).get(i, "")
            
            if q.get("options"):
                st.radio("Your answer:", q["options"], key=f"ans_{q_key}_display",
                         index=None, disabled=True, label_visibility="collapsed")
            else:
                st.text_area("Your answer:", value=saved_answer, key=f"ans_{q_key}_display",
                             disabled=True, label_visibility="collapsed")
            
            if feedback:
                if feedback.get("is_correct"):
                    st.markdown(f"""<div class="ai-feedback-correct">
                    ✅ <strong>{feedback.get('short_verdict', 'Correct!')}</strong><br>
                    {feedback.get('explanation', '')}<br>
                    <em>💡 {feedback.get('memory_tip', '')}</em>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="ai-feedback-wrong">
                    ❌ <strong>{feedback.get('short_verdict', 'Incorrect')}</strong><br>
                    {feedback.get('explanation', '')}<br>
                    <em>🔍 Your answer: {feedback.get('user_error', '')}</em><br>
                    <em>💡 Tip: {feedback.get('memory_tip', '')}</em>
                    </div>""", unsafe_allow_html=True)
        else:
            # Answer input
            if q.get("options"):
                user_ans = st.radio("Choose:", q["options"], key=f"ans_{q_key}", index=None, label_visibility="collapsed")
                answers[i] = user_ans
            else:
                user_ans = st.text_area("Your answer:", key=f"ans_{q_key}", 
                                         placeholder="Type your answer here...", 
                                         label_visibility="collapsed", height=80)
                answers[i] = user_ans
        
        # Show Me Live button
        concept = q.get("concept", topic)
        if st.button(f"🔴 Show Me Live", key=f"show_live_{q_key}", help="AI will demonstrate this concept visually"):
            if st.session_state.learn_active_live_q == live_key:
                st.session_state.learn_active_live_q = None
            else:
                st.session_state.learn_active_live_q = live_key
            st.rerun()
        
        # Inline live demo panel
        if st.session_state.learn_active_live_q == live_key:
            render_live_chat_panel(live_key, concept, q["question"], market, style)
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")
    
    # Submit button (only before submission)
    if submitted_key not in st.session_state:
        col1, col2, col3 = st.columns([2, 3, 2])
        with col2:
            if st.button("✅ Submit Exam", use_container_width=True, type="primary"):
                # Check all answered
                unanswered = [i for i, a in answers.items() if not a]
                if unanswered:
                    st.warning(f"Please answer all questions. Missing: Q{[u+1 for u in unanswered]}")
                else:
                    with st.spinner("🤖 AI is grading your exam..."):
                        feedback_dict = {}
                        total_score = 0
                        for i, q in enumerate(questions):
                            fb = grade_answer(q, str(answers.get(i, "")), market, style)
                            feedback_dict[i] = fb
                            total_score += fb.get("score", 0)
                        
                        avg_score = int(total_score / len(questions))
                        passed = avg_score >= 70
                        
                        if exam_key not in st.session_state.learn_exam_feedback:
                            st.session_state.learn_exam_feedback[exam_key] = {}
                        st.session_state.learn_exam_feedback[exam_key] = feedback_dict
                        st.session_state.learn_exam_answers[exam_key] = answers
                        st.session_state.learn_exam_scores[idx] = avg_score
                        st.session_state.learn_exam_passed[idx] = passed
                        st.session_state[submitted_key] = True
                        
                        if not passed and idx not in st.session_state.learn_weak_topics:
                            st.session_state.learn_weak_topics.append(idx)
                        
                        st.session_state.learn_phase = "result"
                        st.rerun()
    else:
        # Show result navigation
        render_exam_result(exam_key, idx)

def render_exam_result(exam_key, idx):
    """Show exam result and navigation."""
    score = st.session_state.learn_exam_scores.get(idx, 0)
    passed = st.session_state.learn_exam_passed.get(idx, False)
    topics = st.session_state.learn_topics
    
    st.markdown("---")
    
    if passed:
        st.markdown(f"""<div style="background:#00d4ff11; border:1px solid #00d4ff; border-radius:12px; 
        padding:20px; text-align:center;">
        <div style="font-size:2rem;">🎉</div>
        <div style="color:#00d4ff; font-size:1.4rem; font-weight:700;">Passed! Score: {score}%</div>
        <div style="color:#888; margin-top:8px;">You've mastered this topic. Onwards!</div>
        </div>""", unsafe_allow_html=True)
        st.write("")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📖 Review Lesson", use_container_width=True):
                st.session_state.learn_phase = "lesson"
                st.rerun()
        with col2:
            if idx + 1 < len(topics):
                if st.button("▶️ Next Topic →", use_container_width=True, type="primary"):
                    st.session_state.learn_current_topic_idx = idx + 1
                    st.session_state.learn_phase = "lesson"
                    st.rerun()
            else:
                st.success("🏆 You've completed the entire curriculum!")
                if st.button("🔄 Start New Market"):
                    for key in list(st.session_state.keys()):
                        if key.startswith("learn_"):
                            del st.session_state[key]
                    st.rerun()
    else:
        st.markdown(f"""<div style="background:#ff444411; border:1px solid #ff4444; border-radius:12px; 
        padding:20px; text-align:center;">
        <div style="font-size:2rem;">📚</div>
        <div style="color:#ff4444; font-size:1.4rem; font-weight:700;">Score: {score}% — Need 70% to pass</div>
        <div style="color:#888; margin-top:8px;">Review the lesson and try again with fresh questions.</div>
        </div>""", unsafe_allow_html=True)
        st.write("")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📖 Review Lesson Again", use_container_width=True):
                st.session_state.learn_phase = "lesson"
                st.rerun()
        with col2:
            if st.button("🔄 Retake Exam (New Questions)", use_container_width=True, type="primary"):
                # Clear questions to regenerate
                if exam_key in st.session_state.learn_exam_questions:
                    del st.session_state.learn_exam_questions[exam_key]
                submitted_key = f"submitted_{exam_key}"
                if submitted_key in st.session_state:
                    del st.session_state[submitted_key]
                st.session_state.learn_phase = "exam"
                st.rerun()

def render_curriculum():
    """Main curriculum view — lesson or exam."""
    phase = st.session_state.get("learn_phase", "lesson")
    
    # Sidebar summary
    weak = st.session_state.get("learn_weak_topics", [])
    topics = st.session_state.get("learn_topics", [])
    if weak:
        st.info(f"⚠️ Weak Topics: {', '.join([topics[i][:20] for i in weak if i < len(topics)])}")
    
    if phase == "lesson":
        render_lesson()
    elif phase == "exam":
        render_exam()
    elif phase == "result":
        render_exam()  # result is embedded in exam view

# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────
def show_trading_learning():
    """Main function to call from your FinSage app."""
    st.markdown(LEARN_CSS, unsafe_allow_html=True)
    init_learn_state()
    
    step = st.session_state.learn_step
    
    if step == "language":
        render_language_select()
    elif step == "market":
        render_market_select()
    elif step == "style":
        render_style_select()
    elif step == "curriculum":
        render_curriculum()
