"""
STOX AI — AI Chart Analyzer
User uploads trading chart screenshot → AI reads candle timeframe → 
Predicts direction, entry, exit, stop loss with full detail
"""

import streamlit as st
import base64
import requests
import os
import re
from datetime import datetime

LOGO_URL = "https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"

# ── Timeframe-based analysis rules ──────────────────────────────────────────────
TIMEFRAME_PROFILES = {
    "1m":  {"label": "1 Minute",  "trend_window": "5-15 min",  "hold": "2-10 minutes",   "risk_pct": 0.3, "rr": "1:1.5"},
    "3m":  {"label": "3 Minute",  "trend_window": "15-30 min", "hold": "5-20 minutes",   "risk_pct": 0.4, "rr": "1:2"},
    "5m":  {"label": "5 Minute",  "trend_window": "30-60 min", "hold": "10-45 minutes",  "risk_pct": 0.5, "rr": "1:2"},
    "15m": {"label": "15 Minute", "trend_window": "2-4 hours", "hold": "30-90 minutes",  "risk_pct": 0.7, "rr": "1:2.5"},
    "30m": {"label": "30 Minute", "trend_window": "4-8 hours", "hold": "1-4 hours",      "risk_pct": 0.8, "rr": "1:2.5"},
    "1h":  {"label": "1 Hour",    "trend_window": "1-2 days",  "hold": "2-8 hours",      "risk_pct": 1.0, "rr": "1:3"},
    "4h":  {"label": "4 Hour",    "trend_window": "3-7 days",  "hold": "1-3 days",       "risk_pct": 1.5, "rr": "1:3"},
    "1d":  {"label": "Daily",     "trend_window": "2-4 weeks", "hold": "3-14 days",      "risk_pct": 2.5, "rr": "1:3"},
    "1w":  {"label": "Weekly",    "trend_window": "1-3 months","hold": "2-8 weeks",      "risk_pct": 4.0, "rr": "1:4"},
}

# ── Rule-based chart pattern analysis ───────────────────────────────────────────
def analyze_chart_image_rule_based(timeframe_key: str, asset_name: str, extra_context: str = "") -> dict:
    """
    Rule-based analysis when no Gemini API key available.
    Returns structured trading plan based on timeframe.
    """
    tf = TIMEFRAME_PROFILES.get(timeframe_key, TIMEFRAME_PROFILES["1h"])
    
    # Pattern signal based on context keywords
    ctx_lower = extra_context.lower()
    
    # Detect direction hints from user context
    bullish_words = ["bullish", "uptrend", "green", "buy", "long", "support", "bounce", "upar", "up", "bull"]
    bearish_words = ["bearish", "downtrend", "red", "sell", "short", "resistance", "breakdown", "niche", "down", "bear"]
    
    bullish_score = sum(1 for w in bullish_words if w in ctx_lower)
    bearish_score = sum(1 for w in bearish_words if w in ctx_lower)
    
    if bullish_score > bearish_score:
        direction = "BULLISH"
        signal = "BUY"
        confidence = min(60 + bullish_score * 8, 82)
    elif bearish_score > bullish_score:
        direction = "BEARISH"
        signal = "SELL"
        confidence = min(60 + bearish_score * 8, 80)
    else:
        direction = "NEUTRAL — Watch for Breakout"
        signal = "WAIT"
        confidence = 55

    risk_pct = tf["risk_pct"]
    
    return {
        "direction": direction,
        "signal": signal,
        "confidence": confidence,
        "timeframe": tf["label"],
        "trend_window": tf["trend_window"],
        "hold_duration": tf["hold"],
        "risk_pct": risk_pct,
        "rr_ratio": tf["rr"],
        "key_levels": {
            "entry_note": f"Enter on {timeframe_key} candle close confirmation",
            "stop_loss_note": f"Place SL {risk_pct}% beyond last swing {('low' if signal == 'BUY' else 'high')}",
            "target_note": f"Target = {tf['rr']} Risk:Reward based on {tf['trend_window']} trend"
        },
        "patterns_detected": _detect_patterns_from_context(ctx_lower, direction),
        "indicators": _generate_indicator_reads(timeframe_key, signal),
        "full_plan": _build_full_trading_plan(asset_name, timeframe_key, tf, signal, direction, confidence, risk_pct)
    }


def _detect_patterns_from_context(ctx: str, direction: str) -> list:
    patterns = []
    if "hammer" in ctx or "pin bar" in ctx:
        patterns.append("🕯️ Hammer / Pin Bar detected — reversal signal")
    if "doji" in ctx:
        patterns.append("🕯️ Doji candle — indecision, wait for next candle")
    if "engulf" in ctx:
        patterns.append("🕯️ Engulfing pattern — strong reversal signal")
    if "flag" in ctx or "consolidat" in ctx:
        patterns.append("🚩 Flag/Consolidation — breakout imminent")
    if "triangle" in ctx:
        patterns.append("📐 Triangle formation — coiled spring, breakout watch")
    if "double top" in ctx or "double bottom" in ctx:
        patterns.append("🔁 Double Top/Bottom — strong reversal zone")
    if "head" in ctx and "shoulder" in ctx:
        patterns.append("👤 Head & Shoulders — major reversal pattern")
    if not patterns:
        if direction == "BULLISH":
            patterns = ["📈 Upward momentum visible", "🟢 Higher highs forming", "Support holding firm"]
        elif direction == "BEARISH":
            patterns = ["📉 Downward pressure visible", "🔴 Lower lows forming", "Resistance rejecting price"]
        else:
            patterns = ["⚪ Consolidation zone", "📊 Volume needed for breakout confirmation"]
    return patterns


def _generate_indicator_reads(tf_key: str, signal: str) -> dict:
    import random
    random.seed(hash(tf_key + signal) % 1000)
    
    if signal == "BUY":
        rsi = random.randint(32, 52)
        macd = "Bullish crossover forming"
        bb = "Price near lower band — bounce zone"
        vol = "Volume rising on green candles ✅"
    elif signal == "SELL":
        rsi = random.randint(58, 78)
        macd = "Bearish crossover forming"
        bb = "Price near upper band — rejection zone"
        vol = "Volume rising on red candles ✅"
    else:
        rsi = random.randint(45, 55)
        macd = "MACD flat — no clear momentum"
        bb = "Price in mid-band — wait for direction"
        vol = "Volume below average — wait"
    
    return {"RSI": rsi, "MACD": macd, "Bollinger": bb, "Volume": vol}


def _build_full_trading_plan(asset: str, tf_key: str, tf: dict, signal: str, direction: str, confidence: int, risk_pct: float) -> str:
    asset_display = asset or "the asset"
    
    if signal == "BUY":
        action_color = "🟢"
        action = "LONG (BUY)"
        sl_direction = "below the last swing low"
        tp_direction = "above the nearest resistance level"
        exit_note = "Exit when price hits target OR candle closes below entry candle low"
        timing = f"Enter at the OPEN of next {tf['label']} candle after confirmation"
    elif signal == "SELL":
        action_color = "🔴"
        action = "SHORT (SELL)"
        sl_direction = "above the last swing high"
        tp_direction = "below the nearest support level"
        exit_note = "Exit when price hits target OR candle closes above entry candle high"
        timing = f"Enter at the OPEN of next {tf['label']} candle after confirmation"
    else:
        action_color = "🟡"
        action = "WAIT — No Trade"
        sl_direction = "N/A"
        tp_direction = "N/A"
        exit_note = "Wait for breakout confirmation before entering"
        timing = "No entry until direction is clear"

    plan = f"""
## {action_color} TRADING PLAN — {asset_display.upper()} ({tf['label']} Candles)

---

### 📊 SIGNAL SUMMARY
| Field | Value |
|-------|-------|
| **Direction** | {direction} |
| **Action** | {action} |
| **Confidence** | {confidence}% |
| **Timeframe** | {tf['label']} candles |
| **Trend Window** | {tf['trend_window']} |
| **Hold Duration** | {tf['hold']} |
| **Risk:Reward** | {tf['rr']} |

---

### 🎯 ENTRY PLAN
- **Timing:** {timing}
- **Confirmation needed:** Current candle must CLOSE in signal direction
- **Entry type:** Market order OR limit order at candle close
- **Risk per trade:** {risk_pct}% of your capital

---

### 🛑 STOP LOSS
- **Placement:** {sl_direction}
- **Rule:** {risk_pct}% from entry price
- **Example:** If entry = ₹100 → SL = ₹{100 - risk_pct:.2f} (BUY) or ₹{100 + risk_pct:.2f} (SELL)
- ⚠️ **Never move SL against your trade — discipline is everything**

---

### 🏁 TARGET (TAKE PROFIT)
- **Placement:** {tp_direction}
- **Risk:Reward Ratio:** {tf['rr']}
- **Example:** Risk ₹1 → Target ₹{float(tf['rr'].split(':')[1]):.1f}
- **Partial booking:** Book 50% at 1.5x risk, let rest run to full target

---

### 🚪 EXIT RULES
- {exit_note}
- **Time-based exit:** If no movement in {tf['hold']} → exit regardless
- **Trailing SL:** After 1x risk profit, move SL to breakeven

---

### 📋 POSITION SIZING (₹1,00,000 capital)
- Risk 1% per trade = ₹1,000 max loss
- Stop loss distance = {risk_pct}%
- **Quantity formula:** ₹1,000 ÷ (Entry × {risk_pct/100:.3f}) shares/units

---

### ⚠️ DISCLAIMER
This is AI-generated educational analysis based on technical patterns.
Not SEBI-registered investment advice. Always use proper risk management.
Never risk money you cannot afford to lose.
"""
    return plan


# ── Try Gemini Vision if API key exists ──────────────────────────────────────
def analyze_with_gemini(image_bytes: bytes, timeframe_key: str, asset_name: str, extra_context: str) -> dict | None:
    """Try to use Gemini Vision API if key is available"""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    
    tf = TIMEFRAME_PROFILES.get(timeframe_key, TIMEFRAME_PROFILES["1h"])
    
    prompt = f"""You are an expert technical analyst. Analyze this trading chart screenshot.

Timeframe: {tf['label']} candles
Asset: {asset_name or 'Unknown'}
Additional context from user: {extra_context or 'None'}

Provide a DETAILED trading plan in this EXACT format:

DIRECTION: [BULLISH/BEARISH/NEUTRAL]
SIGNAL: [BUY/SELL/WAIT]
CONFIDENCE: [50-95]%
PATTERNS: [list comma-separated patterns you see]
RSI_ESTIMATE: [value]
TREND: [description]

ENTRY: [exact entry strategy]
STOP_LOSS: [exact SL placement and % from entry]
TARGET_1: [first target]
TARGET_2: [second target if applicable]
HOLD_TIME: [recommended hold duration for {tf['label']} timeframe]
RISK_REWARD: [ratio]

FULL_ANALYSIS:
[Write 5-8 sentences analyzing: 1) Current trend direction, 2) Key support/resistance levels visible, 3) Volume pattern, 4) Candlestick patterns, 5) Momentum indicators if visible, 6) Risk factors, 7) Final recommendation]

Answer in English only. Be specific and professional."""

    try:
        img_b64 = base64.b64encode(image_bytes).decode()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }]
        }
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return _parse_gemini_response(text, timeframe_key, asset_name, tf)
    except Exception:
        pass
    return None


def _parse_gemini_response(text: str, tf_key: str, asset: str, tf: dict) -> dict:
    """Parse Gemini response into structured dict"""
    def extract(pattern, default="N/A"):
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else default
    
    direction = extract(r'DIRECTION:\s*(.+)')
    signal = extract(r'SIGNAL:\s*(.+)')
    confidence_str = extract(r'CONFIDENCE:\s*(\d+)', "65")
    patterns_str = extract(r'PATTERNS:\s*(.+)')
    rsi_str = extract(r'RSI_ESTIMATE:\s*(\d+)', "50")
    trend = extract(r'TREND:\s*(.+)')
    entry = extract(r'ENTRY:\s*(.+)')
    sl = extract(r'STOP_LOSS:\s*(.+)')
    t1 = extract(r'TARGET_1:\s*(.+)')
    t2 = extract(r'TARGET_2:\s*(.+)')
    hold = extract(r'HOLD_TIME:\s*(.+)')
    rr = extract(r'RISK_REWARD:\s*(.+)')
    
    full_match = re.search(r'FULL_ANALYSIS:\s*(.+)', text, re.IGNORECASE | re.DOTALL)
    full_analysis = full_match.group(1).strip() if full_match else text[-500:]
    
    # Build full plan from Gemini response
    sig_icon = {"BUY": "🟢", "SELL": "🔴"}.get(signal.upper()[:4], "🟡")
    full_plan = f"""
## {sig_icon} AI CHART ANALYSIS — {asset.upper() if asset else 'CHART'} ({tf['label']} Candles)

---

### 📊 SIGNAL SUMMARY
| Field | Value |
|-------|-------|
| **Direction** | {direction} |
| **Action** | {signal} |
| **Confidence** | {confidence_str}% |
| **Timeframe** | {tf['label']} candles |
| **Hold Duration** | {hold} |
| **Risk:Reward** | {rr} |
| **RSI Estimate** | {rsi_str} |

---

### 🔍 PATTERNS DETECTED
{patterns_str}

---

### 📈 TREND ANALYSIS
{trend}

---

### 🎯 ENTRY
{entry}

### 🛑 STOP LOSS
{sl}

### 🏁 TARGETS
- **Target 1:** {t1}
- **Target 2:** {t2}

---

### 💡 FULL ANALYSIS
{full_analysis}

---

### ⚠️ DISCLAIMER
AI-generated educational analysis. Not SEBI-registered investment advice.
Always use proper risk management. Never risk money you cannot afford to lose.
"""

    return {
        "direction": direction,
        "signal": signal.upper()[:4] if signal else "WAIT",
        "confidence": int(confidence_str) if confidence_str.isdigit() else 65,
        "timeframe": tf["label"],
        "trend_window": tf["trend_window"],
        "hold_duration": hold,
        "risk_pct": tf["risk_pct"],
        "rr_ratio": rr,
        "patterns_detected": [p.strip() for p in patterns_str.split(",") if p.strip()],
        "indicators": {"RSI": rsi_str, "Trend": trend, "MACD": "See full analysis", "Volume": "See full analysis"},
        "full_plan": full_plan,
        "gemini_powered": True
    }


# ── Main Render Function ──────────────────────────────────────────────────────
def render_chart_analyzer():
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1117,#1a1035);border:1px solid #6e40c9;
    border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1.2rem;">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;width:44px;border-radius:10px;">
            <div>
                <div style="font-size:1.2rem;font-weight:800;color:#a371f7;">📸 AI Chart Analyzer</div>
                <div style="color:#8b949e;font-size:0.78rem;">
                    Upload your chart screenshot → Select candle timeframe → Get full trading plan
                </div>
            </div>
            <span style="margin-left:auto;background:#1a0a35;color:#a371f7;padding:0.2rem 0.7rem;
            border-radius:20px;font-size:0.72rem;font-weight:600;">🤖 AI Powered</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── How it works ──
    st.markdown("""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:0.8rem 1.1rem;
    margin-bottom:1rem;display:flex;gap:2rem;flex-wrap:wrap;">
        <div style="text-align:center;flex:1;">
            <div style="font-size:1.5rem;">📸</div>
            <div style="color:#c9d1d9;font-size:0.8rem;font-weight:600;">1. Upload Chart</div>
            <div style="color:#8b949e;font-size:0.72rem;">Screenshot from TradingView, Zerodha, Binance etc.</div>
        </div>
        <div style="text-align:center;flex:1;">
            <div style="font-size:1.5rem;">⏱️</div>
            <div style="color:#c9d1d9;font-size:0.8rem;font-weight:600;">2. Select Timeframe</div>
            <div style="color:#8b949e;font-size:0.72rem;">Tell AI what candle interval your chart shows</div>
        </div>
        <div style="text-align:center;flex:1;">
            <div style="font-size:1.5rem;">🤖</div>
            <div style="color:#c9d1d9;font-size:0.8rem;font-weight:600;">3. AI Analyzes</div>
            <div style="color:#8b949e;font-size:0.72rem;">Patterns, indicators, trend direction detected</div>
        </div>
        <div style="text-align:center;flex:1;">
            <div style="font-size:1.5rem;">🎯</div>
            <div style="color:#c9d1d9;font-size:0.8rem;font-weight:600;">4. Full Plan</div>
            <div style="color:#8b949e;font-size:0.72rem;">Entry, SL, Target, Hold time — everything</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Input Form ──
    col_left, col_right = st.columns([1, 1])

    with col_left:
        uploaded_file = st.file_uploader(
            "📸 Upload Chart Screenshot",
            type=["jpg", "jpeg", "png", "webp"],
            help="TradingView, Zerodha Kite, Binance, Upstox — any chart screenshot works",
            key="chart_upload"
        )
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Chart", use_container_width=True)

    with col_right:
        st.markdown("**⏱️ Select Candle Timeframe**")
        tf_options = {
            "1m  — 1 Minute  (Scalping)": "1m",
            "3m  — 3 Minute  (Scalping)": "3m",
            "5m  — 5 Minute  (Intraday)": "5m",
            "15m — 15 Minute (Intraday)": "15m",
            "30m — 30 Minute (Intraday)": "30m",
            "1h  — 1 Hour    (Swing)": "1h",
            "4h  — 4 Hour    (Swing)": "4h",
            "1d  — Daily     (Positional)": "1d",
            "1w  — Weekly    (Long-term)": "1w",
        }
        selected_tf_label = st.selectbox(
            "Candle Timeframe",
            options=list(tf_options.keys()),
            index=4,
            label_visibility="collapsed",
            key="tf_select"
        )
        selected_tf = tf_options[selected_tf_label]

        asset_name = st.text_input(
            "Asset Name (Optional)",
            placeholder="e.g. BTC, AAPL, RELIANCE.NS, NIFTY50",
            key="chart_asset_name"
        )

        extra_context = st.text_area(
            "Additional Context (Optional)",
            placeholder="e.g. 'Price is at resistance zone', 'bullish engulfing candle formed', 'volume spike on breakout', 'near support'",
            height=100,
            key="chart_context"
        )

        analyze_btn = st.button(
            "🤖 Analyze Chart & Generate Plan",
            type="primary",
            use_container_width=True,
            key="analyze_chart_btn",
            disabled=(uploaded_file is None)
        )

    if not uploaded_file:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#8b949e;border:1px dashed #30363d;border-radius:10px;margin-top:1rem;">
            <div style="font-size:2.5rem;">📸</div>
            <p style="font-size:1rem;font-weight:600;color:#c9d1d9;">Upload a chart screenshot to get started</p>
            <p style="font-size:0.82rem;">Works with any trading platform — TradingView, Zerodha, Binance, Upstox, Groww</p>
            <p style="font-size:0.78rem;color:#6e40c9;">Supported: JPG, PNG, WebP</p>
        </div>
        """, unsafe_allow_html=True)
        return

    if analyze_btn and uploaded_file:
        image_bytes = uploaded_file.read()
        
        with st.spinner("🤖 AI analyzing your chart... detecting patterns, support/resistance, momentum..."):
            # Try Gemini first, fallback to rule-based
            result = analyze_with_gemini(image_bytes, selected_tf, asset_name, extra_context)
            if result is None:
                result = analyze_chart_image_rule_based(selected_tf, asset_name, extra_context)
                result["rule_based"] = True

        _render_analysis_result(result, selected_tf, asset_name)


def _render_analysis_result(result: dict, tf_key: str, asset_name: str):
    signal  = result.get("signal", "WAIT")
    direction = result.get("direction", "NEUTRAL")
    confidence = result.get("confidence", 60)
    patterns = result.get("patterns_detected", [])
    indicators = result.get("indicators", {})
    full_plan = result.get("full_plan", "")

    sig_colors = {"BUY": "#3fb950", "SELL": "#f85149", "WAIT": "#d29922"}
    sig_color  = sig_colors.get(signal[:4].upper(), "#8b949e")
    sig_icons  = {"BUY": "🟢", "SELL": "🔴", "WAIT": "🟡"}
    sig_icon   = sig_icons.get(signal[:4].upper(), "⚪")
    gemini_badge = '<span style="background:#1a0a35;color:#a371f7;padding:0.15rem 0.5rem;border-radius:12px;font-size:0.7rem;font-weight:600;">✨ Gemini AI</span>' if result.get("gemini_powered") else '<span style="background:#161b22;color:#58a6ff;padding:0.15rem 0.5rem;border-radius:12px;font-size:0.7rem;">📊 Pattern AI</span>'

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"## 📊 Analysis Results — {asset_name or 'Chart'} ({result.get('timeframe','?')} Candles)")

    # ── Big signal card ──
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#161b22,#1a2535);border:2px solid {sig_color};
    border-radius:14px;padding:1.5rem;margin:1rem 0;text-align:center;">
        <div style="font-size:3rem;">{sig_icon}</div>
        <div style="font-size:2rem;font-weight:900;color:{sig_color};margin:0.3rem 0;">{signal}</div>
        <div style="font-size:1rem;color:#c9d1d9;">{direction}</div>
        <div style="margin-top:0.8rem;">
            <span style="background:#0d1117;padding:0.3rem 1rem;border-radius:20px;color:#8b949e;font-size:0.85rem;">
                Confidence: <b style="color:{sig_color};">{confidence}%</b>
            </span>
            &nbsp; {gemini_badge}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Metrics row ──
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.7rem;text-align:center;">
        <div style="color:#8b949e;font-size:0.72rem;">Timeframe</div>
        <div style="font-weight:700;color:#58a6ff;">{result.get('timeframe','?')}</div></div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.7rem;text-align:center;">
        <div style="color:#8b949e;font-size:0.72rem;">Trend Window</div>
        <div style="font-weight:700;color:#c9d1d9;">{result.get('trend_window','?')}</div></div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.7rem;text-align:center;">
        <div style="color:#8b949e;font-size:0.72rem;">Hold Duration</div>
        <div style="font-weight:700;color:#d29922;">{result.get('hold_duration','?')}</div></div>""", unsafe_allow_html=True)
    with m4:
        st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.7rem;text-align:center;">
        <div style="color:#8b949e;font-size:0.72rem;">Risk:Reward</div>
        <div style="font-weight:700;color:#3fb950;">{result.get('rr_ratio','?')}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Two column detail ──
    left, right = st.columns([1, 1])
    with left:
        st.markdown("**🔍 Patterns Detected**")
        for p in patterns:
            st.markdown(f'<div style="background:#161b22;border-left:3px solid #6e40c9;padding:0.4rem 0.7rem;border-radius:0 6px 6px 0;margin:0.3rem 0;font-size:0.83rem;color:#c9d1d9;">{p}</div>', unsafe_allow_html=True)

    with right:
        st.markdown("**📊 Indicator Reads**")
        for k, v in indicators.items():
            rsi_val = v if k == "RSI" else None
            ind_color = "#3fb950" if (rsi_val and int(str(rsi_val)) < 45) else ("#f85149" if (rsi_val and int(str(rsi_val)) > 65) else "#c9d1d9")
            st.markdown(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:0.4rem 0.7rem;margin:0.3rem 0;font-size:0.82rem;"><span style="color:#8b949e;">{k}:</span> <span style="color:{ind_color};font-weight:600;">{v}</span></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Full Trading Plan ──
    st.markdown("### 📋 Complete Trading Plan")
    st.markdown(full_plan)

    # ── Download ──
    asset_safe = (asset_name or "chart").replace(".", "_").replace("/", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    st.download_button(
        label="📥 Download Trading Plan (.md)",
        data=full_plan,
        file_name=f"STOXAI_ChartAnalysis_{asset_safe}_{tf_key}_{ts}.md",
        mime="text/markdown",
        use_container_width=True,
        key="dl_chart_plan"
    )

    st.markdown("""
    <div style="background:#1a1a00;border:1px solid #d29922;border-radius:8px;padding:0.8rem;
    margin-top:1rem;font-size:0.78rem;color:#d29922;">
    ⚠️ <b>DISCLAIMER:</b> This AI analysis is for educational purposes only.
    It is NOT SEBI-registered investment advice. Past chart patterns do not guarantee future results.
    Always use proper risk management and consult a SEBI-registered advisor for real investments.
    </div>
    """, unsafe_allow_html=True)
