"""
FinSage Analyzer
Generates professional English analysis reports from real market data.
Rule-based intelligence + Groq LLaMA 3.3 AI insights.
"""

import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger("finsage.analyzer")

GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("FINSAGE_API_KEY")
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"


def _ask_groq(prompt, max_tokens=350):
    """Call Groq LLaMA API. Returns text or empty string."""
    if not GROQ_API_KEY:
        return ""
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": "Bearer " + GROQ_API_KEY, "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": max_tokens, "temperature": 0.7},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        logger.warning("Groq %s: %s", resp.status_code, resp.text[:100])
        return ""
    except Exception as e:
        logger.warning("Groq failed: %s", e)
        return ""


def groq_stock_insight(data):
    name     = data.get("name", data.get("ticker", "?"))
    ticker   = data.get("ticker", "?")
    price    = data.get("current_price", "?")
    change   = data.get("change_pct", 0) or 0
    currency = data.get("currency", "USD")
    pe       = data.get("pe_ratio", "N/A")
    beta     = data.get("beta", "N/A")
    mktcap   = data.get("market_cap", "N/A")
    rec      = data.get("recommendation", "N/A")
    target   = data.get("analyst_target", "N/A")
    sector   = data.get("sector", "N/A")
    wk_high  = data.get("week_52_high", "N/A")
    wk_low   = data.get("week_52_low", "N/A")

    # Include latest news headlines for context
    news_list = data.get("news", [])
    news_block = ""
    if news_list:
        headlines = [n.get("title", "") for n in news_list[:4] if n.get("title")]
        if headlines:
            news_block = "\nLatest News Headlines:\n" + "\n".join(f"- {h}" for h in headlines) + "\n"

    prompt = (
        "You are a sharp financial analyst for Indian retail investors.\n"
        "Analyze this stock using the data AND latest news headlines below.\n"
        "Give a 4-5 sentence insight in simple Hinglish (English + Hindi mix).\n\n"
        f"Stock: {name} ({ticker}) | Sector: {sector}\n"
        f"Price: {currency} {price} | 24H Change: {change:+.2f}%\n"
        f"Market Cap: {mktcap} | P/E Ratio: {pe} | Beta: {beta}\n"
        f"52W Range: {wk_low} to {wk_high}\n"
        f"Analyst Rating: {rec} | Target Price: {currency} {target}\n"
        + news_block +
        "\nCover: (1) News-driven momentum ya catalyst, (2) Key risk, (3) Ek clear verdict.\n"
        "Last sentence must be: 'Yeh financial advice nahi hai — sirf educational analysis hai.'"
    )
    result = _ask_groq(prompt, max_tokens=350)
    if result:
        return "\n\n---\n\n### 🤖 AI Insight (News-Powered) — Groq LLaMA 3.3\n\n" + result + "\n"
    return ""


def groq_crypto_insight(data):
    name    = data.get("name", data.get("ticker", "?"))
    ticker  = data.get("ticker", "?")
    atype   = data.get("asset_type", "Crypto")
    price   = data.get("current_price", "?")
    chg24   = data.get("change_pct", 0) or 0
    chg7d   = data.get("change_7d", 0) or 0
    mktcap  = data.get("market_cap", 0) or 0
    rank    = data.get("market_cap_rank", "?")
    ath     = data.get("ath", "N/A")
    ath_chg = data.get("ath_change_pct", 0) or 0
    is_meme = (atype == "Meme Coin")

    # Include latest news headlines for context
    news_list = data.get("news", [])
    news_block = ""
    if news_list:
        headlines = [n.get("title", "") for n in news_list[:4] if n.get("title")]
        if headlines:
            news_block = "\nLatest News Headlines:\n" + "\n".join(f"- {h}" for h in headlines) + "\n"

    meme_warning = "IMPORTANT: Yeh ek MEME COIN hai — bahut speculative, koi fundamental value nahi. Clearly warn karo.\n" if is_meme else ""

    prompt = (
        "You are a sharp crypto analyst for Indian retail investors.\n"
        f"Analyze this {'MEME COIN' if is_meme else 'cryptocurrency'} using data AND latest news.\n"
        "Give a 4-5 sentence insight in simple Hinglish (English + Hindi mix).\n"
        + meme_warning + "\n"
        f"Asset: {name} ({ticker}) | Type: {atype}\n"
        f"Price: ${price} | 24H: {chg24:+.2f}% | 7D: {chg7d:+.2f}%\n"
        f"Market Cap: ${mktcap:,.0f} | CMC Rank: #{rank}\n"
        f"ATH: ${ath} | ATH Change: {ath_chg:+.1f}%\n"
        + news_block +
        "\nCover: (1) News-driven momentum ya catalyst, (2) Key risk, (3) Short verdict.\n"
        "Last sentence must be: 'Yeh financial advice nahi hai — sirf educational analysis hai.'"
    )
    result = _ask_groq(prompt, max_tokens=350)
    if result:
        return "\n\n---\n\n### 🤖 AI Insight (News-Powered) — Groq LLaMA 3.3\n\n" + result + "\n"
    return ""




def trading_signals_stock(data: dict) -> str:
    """Generate Entry / Stop-Loss / Target / Risk levels for a stock."""
    price    = data.get("current_price") or 0
    change   = data.get("change_pct", 0) or 0
    currency = data.get("currency", "USD")
    risk     = data.get("risk_score", 5)
    vol      = data.get("volatility_annualized", 0) or 0
    day_high = data.get("day_high") or price
    day_low  = data.get("day_low")  or price
    wk_high  = data.get("week_52_high") or price
    wk_low   = data.get("week_52_low")  or price
    rec      = (data.get("recommendation") or "").upper()
    target   = data.get("analyst_target")
    beta     = data.get("beta") or 1.0

    if not price or price <= 0:
        return ""

    # ── Stop-Loss: based on volatility + risk score ──────────────────────────
    sl_pct = 5.0          # default 5%
    if vol > 60 or risk >= 8:  sl_pct = 10.0
    elif vol > 35 or risk >= 6: sl_pct = 7.0
    elif vol <= 15 or risk <= 3: sl_pct = 3.0
    stop_loss = round(price * (1 - sl_pct / 100), 2)

    # ── Entry Zone ────────────────────────────────────────────────────────────
    # Ideal entry: slight dip from current or if already dipped, current zone
    if change > 3:  # running up — wait for pullback
        entry_low  = round(price * 0.97, 2)
        entry_high = round(price * 0.99, 2)
        entry_note = "⏳ Stock oopar ja raha hai — thoda pullback ka wait karo"
    elif change < -3:  # dipped — potential buy zone
        entry_low  = round(price * 1.00, 2)
        entry_high = round(price * 1.02, 2)
        entry_note = "🟢 Dip mein entry ka mauka — confirm karo ki trend reverse ho raha hai"
    else:
        entry_low  = round(price * 0.99, 2)
        entry_high = round(price * 1.01, 2)
        entry_note = "📊 Current zone theek hai — SIP ya staggered entry better hai"

    # ── Targets ───────────────────────────────────────────────────────────────
    t1_pct = sl_pct * 1.5   # minimum reward = 1.5x risk
    t2_pct = sl_pct * 2.5
    t3_pct = sl_pct * 4.0

    t1 = round(price * (1 + t1_pct / 100), 2)
    t2 = round(price * (1 + t2_pct / 100), 2)
    t3 = round(price * (1 + t3_pct / 100), 2)

    # Use analyst target if it gives a better T3
    if target and target > t3:
        t3 = round(target, 2)
    
    # ── Risk:Reward ───────────────────────────────────────────────────────────
    risk_amt  = price - stop_loss
    reward_t1 = t1 - price
    rr_ratio  = round(reward_t1 / risk_amt, 1) if risk_amt > 0 else 0

    # ── Action Signal ─────────────────────────────────────────────────────────
    if rec in ("STRONG_BUY", "BUY") and risk <= 5:
        action = "🟢 BUY / ACCUMULATE"
        action_color = "green"
    elif rec in ("STRONG_BUY", "BUY") and risk <= 7:
        action = "🟡 CAUTIOUS BUY"
        action_color = "yellow"
    elif rec in ("SELL", "STRONG_SELL") or risk >= 8:
        action = "🔴 AVOID / WAIT"
        action_color = "red"
    elif risk >= 6:
        action = "🟠 HOLD / SMALL POSITION"
        action_color = "orange"
    else:
        action = "🟡 WATCH & WAIT"
        action_color = "yellow"

    # ── Position Sizing ───────────────────────────────────────────────────────
    if risk <= 3:   pos_size = "Portfolio ka 10-15%"
    elif risk <= 5: pos_size = "Portfolio ka 5-10%"
    elif risk <= 7: pos_size = "Portfolio ka 2-5%"
    else:           pos_size = "Portfolio ka max 1-2% (bahut risky)"

    # ── When to Sell ──────────────────────────────────────────────────────────
    sell_rules = []
    sell_rules.append(f"**T1 hit ho jaye** ({fmt_price(t1, currency)}) → 30-40% position book karo")
    sell_rules.append(f"**T2 hit ho jaye** ({fmt_price(t2, currency)}) → aur 30% nikalo, stop-loss trail karo")
    sell_rules.append(f"**T3 / Full Target** ({fmt_price(t3, currency)}) → baaki position exit")
    sell_rules.append(f"**Stop-Loss breach** ({fmt_price(stop_loss, currency)}) → TURANT exit, argument mat karo")
    sell_rules.append("**Fundamentals change ho jaye** → earnings miss, fraud, management change → immediate exit")

    return f"""
---

## 🎯 Trading Signals & Action Plan

> ⚡ **Signal:** {action}

| Parameter | Value |
|-----------|-------|
| **Current Price** | {fmt_price(price, currency)} |
| **Entry Zone** | {fmt_price(entry_low, currency)} – {fmt_price(entry_high, currency)} |
| **Stop-Loss** | 🛑 {fmt_price(stop_loss, currency)} ({sl_pct:.0f}% neeche) |
| **Target 1 (Conservative)** | 🎯 {fmt_price(t1, currency)} (+{t1_pct:.0f}%) |
| **Target 2 (Moderate)** | 🎯 {fmt_price(t2, currency)} (+{t2_pct:.0f}%) |
| **Target 3 (Full Potential)** | 🎯 {fmt_price(t3, currency)} (+{t3_pct:.0f}%) |
| **Risk : Reward Ratio** | {rr_ratio}:1 {'✅ Achha' if rr_ratio >= 1.5 else '⚠️ Kam'} |
| **Suggested Position Size** | {pos_size} |
| **Stop-Loss %** | {sl_pct:.0f}% (Risk Score {risk}/10 ke basis par) |

### 📍 Entry Strategy
{entry_note}

> **Tip:** Ek saath poora amount mat lagao — 3 parts mein entry karo (SIP style).

### 📤 Sell / Exit Rules
{"".join(chr(10) + "- " + r for r in sell_rules)}

### ⚠️ Risk in Rupees (Example)
| Investment | Max Loss (at Stop-Loss) | T1 Profit |
|-----------|------------------------|-----------|
| ₹10,000 | ₹{int(10000 * sl_pct/100):,} | ₹{int(10000 * t1_pct/100):,} |
| ₹50,000 | ₹{int(50000 * sl_pct/100):,} | ₹{int(50000 * t1_pct/100):,} |
| ₹1,00,000 | ₹{int(100000 * sl_pct/100):,} | ₹{int(100000 * t1_pct/100):,} |

"""


def trading_signals_crypto(data: dict) -> str:
    """Generate Entry / Stop-Loss / Target / Risk levels for crypto/meme coins."""
    price    = data.get("current_price") or 0
    change   = data.get("change_pct", 0) or 0
    change_7d = data.get("change_7d", 0) or 0
    risk     = data.get("risk_score", 5)
    vol      = data.get("volatility_annualized", 0) or 0
    high_24h = data.get("high_24h") or price
    low_24h  = data.get("low_24h")  or price
    ath      = data.get("ath") or price
    ath_chg  = data.get("ath_change_pct", 0) or 0
    is_meme  = data.get("asset_type") == "Meme Coin"

    if not price or price <= 0:
        return ""

    # ── Stop-Loss: crypto needs wider stops ───────────────────────────────────
    if is_meme:          sl_pct = 20.0
    elif vol > 100:      sl_pct = 15.0
    elif vol > 60:       sl_pct = 10.0
    elif risk >= 7:      sl_pct = 12.0
    else:                sl_pct = 8.0
    stop_loss = price * (1 - sl_pct / 100)

    # ── Entry Zone ────────────────────────────────────────────────────────────
    if change > 5:
        entry_low  = price * 0.95
        entry_high = price * 0.98
        entry_note = "⏳ Strong pump chal raha hai — pullback ka wait karo, FOMO mein mat kudo"
    elif change < -5 and change_7d < -10:
        entry_low  = price * 1.00
        entry_high = price * 1.03
        entry_note = "🟢 Significant dip — small position le sakte ho, par DCA karo"
    else:
        entry_low  = price * 0.98
        entry_high = price * 1.02
        entry_note = "📊 Sideways phase — accumulate carefully, zyada leverage mat lo"

    # ── Targets ───────────────────────────────────────────────────────────────
    t1_pct = sl_pct * 1.5
    t2_pct = sl_pct * 2.5
    t3_pct = sl_pct * 4.0 if not is_meme else sl_pct * 3.0

    t1 = price * (1 + t1_pct / 100)
    t2 = price * (1 + t2_pct / 100)
    t3 = price * (1 + t3_pct / 100)

    risk_amt  = price - stop_loss
    reward_t1 = t1 - price
    rr_ratio  = round(reward_t1 / risk_amt, 1) if risk_amt > 0 else 0

    # ── Action Signal ─────────────────────────────────────────────────────────
    if is_meme:
        action = "🔴 HIGHLY SPECULATIVE — Sirf gamble money use karo"
    elif risk <= 4 and change_7d > 0:
        action = "🟢 BUY / ACCUMULATE (DCA recommended)"
    elif risk <= 6:
        action = "🟡 CAUTIOUS — Small position only"
    else:
        action = "🔴 HIGH RISK — Expert traders only"

    # ── Position Size ─────────────────────────────────────────────────────────
    if is_meme:       pos_size = "Portfolio ka max 1-2% (meme = pure speculation)"
    elif risk <= 4:   pos_size = "Portfolio ka 5-10%"
    elif risk <= 6:   pos_size = "Portfolio ka 2-5%"
    else:             pos_size = "Portfolio ka max 1-3%"

    # ── Sell Rules ────────────────────────────────────────────────────────────
    sell_rules = []
    sell_rules.append(f"**T1 hit** ({fmt_price(t1)}) → 40% nikalo, baki hold karo")
    sell_rules.append(f"**T2 hit** ({fmt_price(t2)}) → aur 30% exit, stop-loss trail karo cost price par")
    sell_rules.append(f"**T3** ({fmt_price(t3)}) → poori position exit")
    sell_rules.append(f"**Stop-Loss** ({fmt_price(stop_loss)}) → TURANT exit — crypto mein fast move hota hai")
    if is_meme:
        sell_rules.append("**Meme coins:** Jaise hi 2x ya 3x ho, original investment nikalo — baaki 'free ride' hai")
    sell_rules.append("**News-based exit:** Exchange hack, regulatory ban, whale dump → turant niklo")

    return f"""
---

## 🎯 Trading Signals & Action Plan

> ⚡ **Signal:** {action}
{">" + chr(10) + "> ⚠️ **MEME COIN WARNING:** Yeh asset pure speculation hai. Sirf itna lagao jo doob jaye toh chale." if is_meme else ""}

| Parameter | Value |
|-----------|-------|
| **Current Price** | {fmt_price(price)} |
| **Entry Zone** | {fmt_price(entry_low)} – {fmt_price(entry_high)} |
| **Stop-Loss** | 🛑 {fmt_price(stop_loss)} ({sl_pct:.0f}% neeche) |
| **Target 1** | 🎯 {fmt_price(t1)} (+{t1_pct:.0f}%) |
| **Target 2** | 🎯 {fmt_price(t2)} (+{t2_pct:.0f}%) |
| **Target 3** | 🎯 {fmt_price(t3)} (+{t3_pct:.0f}%) |
| **Risk : Reward** | {rr_ratio}:1 {'✅' if rr_ratio >= 1.5 else '⚠️'} |
| **Position Size** | {pos_size} |

### 📍 Entry Strategy
{entry_note}

### 📤 Kab Sell Karna Hai
{"".join(chr(10) + "- " + r for r in sell_rules)}

### ⚠️ Risk in Rupees (Example — ₹10,000 investment par)
| Investment | Max Loss (Stop-Loss) | T1 Profit |
|-----------|---------------------|-----------|
| ₹10,000 | ₹{int(10000 * sl_pct/100):,} | ₹{int(10000 * t1_pct/100):,} |
| ₹50,000 | ₹{int(50000 * sl_pct/100):,} | ₹{int(50000 * t1_pct/100):,} |
| ₹1,00,000 | ₹{int(100000 * sl_pct/100):,} | ₹{int(100000 * t1_pct/100):,} |

"""



def get_trend(change_pct: float) -> str:
    if change_pct > 5: return "Strong Uptrend 📈"
    elif change_pct > 1: return "Uptrend 🔼"
    elif change_pct > -1: return "Sideways / Neutral ➡️"
    elif change_pct > -5: return "Downtrend 🔽"
    else: return "Strong Downtrend 📉"


def get_risk_label(score: int) -> str:
    if score <= 2: return "Very Low Risk 🟢"
    elif score <= 4: return "Low Risk 🟡"
    elif score <= 6: return "Moderate Risk 🟠"
    elif score <= 8: return "High Risk 🔴"
    else: return "Very High Risk ⛔"


def get_sentiment(change_pct: float, change_7d: float = 0) -> str:
    combined = (change_pct + change_7d) / 2 if change_7d else change_pct
    if combined > 10: return "Very Bullish 🚀"
    elif combined > 3: return "Bullish 📈"
    elif combined > -3: return "Neutral 😐"
    elif combined > -10: return "Bearish 📉"
    else: return "Very Bearish 🐻"


def fmt_price(price, currency="USD") -> str:
    if price is None: return "N/A"
    if price < 0.000001: return f"{currency} {price:.10f}"
    elif price < 0.01: return f"{currency} {price:.8f}"
    elif price < 1: return f"{currency} {price:.6f}"
    elif price < 100: return f"{currency} {price:.4f}"
    else: return f"{currency} {price:,.2f}"


def format_number(n) -> str:
    if n is None or n == 0: return "N/A"
    if n >= 1_000_000_000_000: return f"${n/1_000_000_000_000:.2f}T"
    elif n >= 1_000_000_000: return f"${n/1_000_000_000:.2f}B"
    elif n >= 1_000_000: return f"${n/1_000_000:.2f}M"
    elif n >= 1_000: return f"${n:,.0f}"
    else: return f"${n:.2f}"



# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE SCORE + DYNAMIC SIGNALS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_confidence_score(data: dict, inds: dict = None) -> dict:
    """
    0-100 Confidence Score based on:
      Technical (40pts) + Momentum (25pts) + Volume (20pts) + Risk Penalty (15pts)
    Returns dict with score, label, color, breakdown.
    """
    score = 0
    breakdown = []

    price     = float(data.get("current_price") or 0)
    change_24h= float(data.get("change_pct") or 0)
    change_7d = float(data.get("change_7d") or 0)
    change_30d= float(data.get("change_30d") or 0)
    vol_ann   = float(data.get("volatility_annualized") or 30)
    risk      = int(data.get("risk_score") or 5)
    mktcap    = float(data.get("market_cap") or 0)
    vol_24h   = float(data.get("volume_24h") or data.get("volume") or 0)
    rec       = str(data.get("recommendation") or "").upper()
    asset     = data.get("asset_type", "")

    # ── 1. Technical (40 pts) ─────────────────────────────────────────────────
    tech = 0
    if inds:
        close = inds.get("close")
        ma10  = inds.get("ma10")
        ma20  = inds.get("ma20")
        rsi   = inds.get("rsi")
        macd  = inds.get("macd")
        sig   = inds.get("signal")
        bb_up = inds.get("bb_up")
        bb_dn = inds.get("bb_dn")

        def last(s):
            try:
                v = s.dropna()
                return float(v.iloc[-1]) if len(v) else None
            except: return None

        rsi_v   = last(rsi)   or 50
        macd_v  = last(macd)  or 0
        sig_v   = last(sig)   or 0
        ma10_v  = last(ma10)  or price
        ma20_v  = last(ma20)  or price
        bb_up_v = last(bb_up) or price
        bb_dn_v = last(bb_dn) or price

        # MA trend (10 pts)
        if price > ma10_v > ma20_v:
            tech += 10; breakdown.append(("MA Trend", "+10", "Price > MA10 > MA20 — strong uptrend"))
        elif price > ma20_v:
            tech += 6;  breakdown.append(("MA Trend", "+6",  "Price above MA20 — mild uptrend"))
        elif price < ma20_v:
            tech += 0;  breakdown.append(("MA Trend", "+0",  "Price below MA20 — downtrend"))

        # RSI (10 pts)
        if 40 <= rsi_v <= 60:
            tech += 8; breakdown.append(("RSI", "+8", f"RSI {rsi_v:.0f} — healthy neutral zone"))
        elif rsi_v < 30:
            tech += 10; breakdown.append(("RSI", "+10", f"RSI {rsi_v:.0f} — oversold, bounce likely"))
        elif rsi_v < 40:
            tech += 6; breakdown.append(("RSI", "+6",  f"RSI {rsi_v:.0f} — slightly oversold"))
        elif rsi_v > 80:
            tech += 1; breakdown.append(("RSI", "+1",  f"RSI {rsi_v:.0f} — very overbought, caution"))
        elif rsi_v > 70:
            tech += 3; breakdown.append(("RSI", "+3",  f"RSI {rsi_v:.0f} — overbought, may correct"))

        # MACD (10 pts)
        if macd_v > sig_v and macd_v > 0:
            tech += 10; breakdown.append(("MACD", "+10", "Bullish crossover above zero"))
        elif macd_v > sig_v:
            tech += 7;  breakdown.append(("MACD", "+7",  "Bullish crossover below zero"))
        elif macd_v < sig_v:
            tech += 2;  breakdown.append(("MACD", "+2",  "Bearish crossover — selling pressure"))

        # Bollinger (10 pts)
        bb_range = bb_up_v - bb_dn_v
        bb_pos   = ((price - bb_dn_v) / bb_range * 100) if bb_range > 0 else 50
        if bb_pos < 20:
            tech += 10; breakdown.append(("Bollinger", "+10", "Near lower band — oversold zone"))
        elif bb_pos < 40:
            tech += 7;  breakdown.append(("Bollinger", "+7",  "Lower half of bands — buy zone"))
        elif bb_pos < 70:
            tech += 5;  breakdown.append(("Bollinger", "+5",  "Mid bands — neutral"))
        else:
            tech += 2;  breakdown.append(("Bollinger", "+2",  "Near upper band — overbought zone"))
    else:
        # No indicators — use price change as proxy
        if change_24h > 2:   tech += 25
        elif change_24h > 0: tech += 18
        else:                tech += 8

    score += tech

    # ── 2. Momentum (25 pts) ──────────────────────────────────────────────────
    mom = 0
    if change_24h > 5:    mom += 10; breakdown.append(("24H Move", "+10", f"+{change_24h:.1f}% strong momentum"))
    elif change_24h > 2:  mom += 7;  breakdown.append(("24H Move", "+7",  f"+{change_24h:.1f}% positive"))
    elif change_24h > 0:  mom += 4;  breakdown.append(("24H Move", "+4",  f"+{change_24h:.1f}% slightly up"))
    elif change_24h > -3: mom += 2;  breakdown.append(("24H Move", "+2",  f"{change_24h:.1f}% minor dip"))
    else:                            breakdown.append(("24H Move", "+0",  f"{change_24h:.1f}% strong sell-off"))

    if change_7d > 10:    mom += 8;  breakdown.append(("7D Trend", "+8",  f"+{change_7d:.1f}% weekly uptrend"))
    elif change_7d > 0:   mom += 5;  breakdown.append(("7D Trend", "+5",  f"+{change_7d:.1f}% weekly positive"))
    elif change_7d > -10: mom += 2;  breakdown.append(("7D Trend", "+2",  f"{change_7d:.1f}% mild weekly dip"))
    else:                            breakdown.append(("7D Trend", "+0",  f"{change_7d:.1f}% weekly downtrend"))

    if change_30d > 20:   mom += 7;  breakdown.append(("30D Trend", "+7", f"+{change_30d:.1f}% strong monthly"))
    elif change_30d > 0:  mom += 4;  breakdown.append(("30D Trend", "+4", f"+{change_30d:.1f}% monthly positive"))
    else:                            breakdown.append(("30D Trend", "+0",  f"{change_30d:.1f}% monthly decline"))

    score += mom

    # ── 3. Volume Health (20 pts) ─────────────────────────────────────────────
    vol_pts = 0
    if mktcap and vol_24h and mktcap > 0:
        vr = vol_24h / mktcap
        if vr > 0.3:    vol_pts = 20; breakdown.append(("Volume", "+20", f"Very high activity ({vr:.1%} of mktcap)"))
        elif vr > 0.1:  vol_pts = 14; breakdown.append(("Volume", "+14", f"Strong activity ({vr:.1%} of mktcap)"))
        elif vr > 0.03: vol_pts = 8;  breakdown.append(("Volume", "+8",  f"Normal volume ({vr:.1%} of mktcap)"))
        else:           vol_pts = 3;  breakdown.append(("Volume", "+3",  f"Low volume ({vr:.1%}) — thin market"))
    elif rec in ("STRONG_BUY","BUY"):
        vol_pts = 12; breakdown.append(("Analyst", "+12", "Strong buy recommendation"))
    score += vol_pts

    # ── 4. Risk Penalty (up to -15) ───────────────────────────────────────────
    penalty = 0
    if risk >= 9:    penalty = 15; breakdown.append(("Risk", "-15", f"Extreme risk ({risk}/10)"))
    elif risk >= 7:  penalty = 10; breakdown.append(("Risk", "-10", f"High risk ({risk}/10)"))
    elif risk >= 5:  penalty = 5;  breakdown.append(("Risk", "-5",  f"Moderate risk ({risk}/10)"))
    else:            breakdown.append(("Risk",  "+0", f"Low risk ({risk}/10) — no penalty"))
    score -= penalty

    score = max(0, min(100, score))

    # Label + color
    if score >= 80:   label, color, emoji = "Very High Confidence", "#3fb950", "🟢"
    elif score >= 65: label, color, emoji = "High Confidence",      "#26a69a", "🟢"
    elif score >= 50: label, color, emoji = "Moderate Confidence",  "#f7c948", "🟡"
    elif score >= 35: label, color, emoji = "Low Confidence",       "#d29922", "🟠"
    else:             label, color, emoji = "Avoid — High Risk",    "#ef5350", "🔴"

    return dict(score=score, label=label, color=color, emoji=emoji, breakdown=breakdown)


def dynamic_stop_loss(data: dict, inds: dict = None) -> dict:
    """
    Volatility-adjusted stop-loss.
    If volatility is rising (last 7d std > 14d std), tighten the stop.
    Returns: stop_loss, sl_pct, is_dynamic, note
    """
    price   = float(data.get("current_price") or 0)
    vol_ann = float(data.get("volatility_annualized") or 30)
    risk    = int(data.get("risk_score") or 5)
    if not price: return dict(stop_loss=0, sl_pct=5, is_dynamic=False, note="")

    # Base SL from volatility
    if vol_ann > 120:   base_sl = 15.0
    elif vol_ann > 80:  base_sl = 12.0
    elif vol_ann > 50:  base_sl = 8.0
    elif vol_ann > 30:  base_sl = 6.0
    elif vol_ann > 15:  base_sl = 4.5
    else:               base_sl = 3.0

    # Tighten if volatility recently spiked (dynamic adjustment)
    is_dynamic = False
    note       = f"Based on {vol_ann:.0f}% annual volatility"
    if inds is not None:
        try:
            close = inds["close"].dropna()
            if len(close) >= 14:
                vol_7d  = float(close.pct_change().dropna().tail(7).std()  * 100)
                vol_14d = float(close.pct_change().dropna().tail(14).std() * 100)
                if vol_7d > vol_14d * 1.3:
                    # Volatility spiking — tighten by 20%
                    base_sl = round(base_sl * 0.80, 1)
                    is_dynamic = True
                    note = f"Volatility spiking ({vol_7d:.1f}% > {vol_14d:.1f}%) — stop tightened automatically"
                elif vol_7d < vol_14d * 0.7:
                    # Volatility contracting — slightly wider
                    base_sl = round(base_sl * 1.10, 1)
                    note = f"Volatility contracting — slightly wider stop"
        except: pass

    sl_pct    = round(base_sl, 1)
    stop_loss = round(price * (1 - sl_pct/100), 6)
    return dict(stop_loss=stop_loss, sl_pct=sl_pct, is_dynamic=is_dynamic, note=note)


def partial_take_profit(data: dict, sl_pct: float) -> list:
    """
    Returns tiered exit plan:
    - For meme: 25%@2x, 50%@5x, 25%@moon
    - For stocks/crypto: based on R:R multiples
    """
    price    = float(data.get("current_price") or 0)
    is_meme  = data.get("asset_type") == "Meme Coin"
    currency = data.get("currency","USD")
    if not price: return []

    def fp(v):
        if v < 0.0001: return f"${v:.8f}"
        if v < 0.01:   return f"${v:.6f}"
        return f"{currency} {v:,.4f}"

    if is_meme:
        return [
            dict(pct_sell=25, label="Sell 25%",  price=round(price*2,   8), note="2x — Get your investment back",    color="#f7c948"),
            dict(pct_sell=50, label="Sell 50%",  price=round(price*5,   8), note="5x — Lock major profits",          color="#26a69a"),
            dict(pct_sell=25, label="Hold 25%",  price=round(price*20,  8), note="Let it moon — only house money",   color="#3fb950"),
        ]
    else:
        t1_pct = sl_pct * 1.5
        t2_pct = sl_pct * 3.0
        t3_pct = sl_pct * 5.0
        return [
            dict(pct_sell=35, label="Sell 35%",  price=round(price*(1+t1_pct/100),4), note=f"+{t1_pct:.0f}% — Conservative target",  color="#f7c948"),
            dict(pct_sell=40, label="Sell 40%",  price=round(price*(1+t2_pct/100),4), note=f"+{t2_pct:.0f}% — Main target",           color="#26a69a"),
            dict(pct_sell=25, label="Hold 25%",  price=round(price*(1+t3_pct/100),4), note=f"+{t3_pct:.0f}% — Full potential",        color="#3fb950"),
        ]


def rug_pull_flags(data: dict) -> list:
    """
    Heuristic rug pull / red flag detection for meme/micro-cap coins.
    Returns list of flag dicts: {severity, label, detail}
    """
    flags = []
    price      = float(data.get("current_price") or 0)
    mktcap     = float(data.get("market_cap") or 0)
    vol_24h    = float(data.get("volume_24h") or 0)
    change_24h = float(data.get("change_pct") or 0)
    change_7d  = float(data.get("change_7d") or 0)
    rank       = data.get("market_cap_rank")
    supply     = data.get("circulating_supply") or 0
    is_meme    = data.get("asset_type") == "Meme Coin"

    if not is_meme and mktcap > 1e9:
        return []  # established coins — skip

    # Low market cap = high manipulation risk
    if mktcap < 1e6:
        flags.append(dict(severity="high",   label="Micro Cap",        detail="Market cap under $1M — extremely easy to manipulate"))
    elif mktcap < 10e6:
        flags.append(dict(severity="medium", label="Very Small Cap",   detail=f"Market cap ${mktcap/1e6:.1f}M — pump/dump risk"))

    # Extreme pump in 24h = possible rug setup
    if change_24h > 100:
        flags.append(dict(severity="high",   label="Pump Detected",    detail=f"+{change_24h:.0f}% in 24h — potential pump before dump"))
    elif change_24h > 50:
        flags.append(dict(severity="medium", label="Rapid Pump",       detail=f"+{change_24h:.0f}% today — enter with extreme caution"))

    # Extreme crash = possible rug already happening
    if change_24h < -50:
        flags.append(dict(severity="high",   label="Possible Rug",     detail=f"{change_24h:.0f}% crash today — may already be rugging"))
    elif change_7d < -70:
        flags.append(dict(severity="high",   label="Severe Weekly Drop",detail=f"{change_7d:.0f}% in 7 days — collapsing"))

    # Volume/Mcap suspiciously high (wash trading)
    if mktcap and vol_24h and mktcap > 0:
        vr = vol_24h / mktcap
        if vr > 5:
            flags.append(dict(severity="high",   label="Wash Trading Risk", detail=f"Volume is {vr:.0f}x market cap — abnormal, possible fake volume"))
        elif vr > 2:
            flags.append(dict(severity="medium", label="High Vol Ratio",    detail=f"Volume {vr:.1f}x market cap — monitor closely"))

    # Very low volume = illiquid = hard to exit
    if mktcap and vol_24h and mktcap > 0:
        vr2 = vol_24h / mktcap
        if vr2 < 0.005 and is_meme:
            flags.append(dict(severity="high",   label="Illiquid Market",   detail="Very low 24h volume — hard to sell when needed"))

    # No rank = not on major exchanges
    if not rank and is_meme:
        flags.append(dict(severity="medium", label="Unranked Coin",    detail="Not ranked on CoinGecko top list — very early/risky"))

    return flags


def analyze_stock(data: dict) -> str:
    name = data.get("name", data.get("ticker", "N/A"))
    ticker = data.get("ticker", "N/A")
    price = data.get("current_price")
    currency = data.get("currency", "USD")
    change = data.get("change_pct", 0) or 0
    risk = data.get("risk_score", 5)
    vol = data.get("volatility_annualized", 0) or 0
    beta = data.get("beta")
    pe = data.get("pe_ratio")
    eps = data.get("eps")
    mktcap = data.get("market_cap")
    div = data.get("dividend_yield")
    rec = data.get("recommendation", "N/A")
    target = data.get("analyst_target")
    week_high = data.get("week_52_high")
    week_low = data.get("week_52_low")
    sector = data.get("sector", "N/A")
    day_high = data.get("day_high")
    day_low = data.get("day_low")
    volume = data.get("volume", 0) or 0
    avg_vol = data.get("avg_volume", 0) or 0

    now = datetime.now().strftime("%B %d, %Y %H:%M IST")
    trend = get_trend(change)
    risk_label = get_risk_label(risk)
    sentiment = get_sentiment(change)

    # Volume analysis
    vol_analysis = ""
    if volume and avg_vol and avg_vol > 0:
        vol_ratio = volume / avg_vol
        if vol_ratio > 1.5:
            vol_analysis = f"Trading volume is **{vol_ratio:.1f}x above average** — strong institutional interest or news-driven activity."
        elif vol_ratio < 0.5:
            vol_analysis = f"Trading volume is **below average ({vol_ratio:.1f}x)** — low conviction in current price movement."
        else:
            vol_analysis = "Trading volume is **near average** — normal market activity."

    # 52-week range
    range_analysis = ""
    if week_high and week_low and price and (week_high - week_low) > 0:
        range_pct = ((price - week_low) / (week_high - week_low)) * 100
        if range_pct > 80:
            range_analysis = f"Trading near **52-week high** ({range_pct:.0f}% of annual range) — potential resistance zone ahead."
        elif range_pct < 20:
            range_analysis = f"Trading near **52-week low** ({range_pct:.0f}% of annual range) — potential support/value zone."
        else:
            range_analysis = f"At **{range_pct:.0f}% of 52-week range** — mid-range positioning with room in both directions."

    # Valuation
    val_analysis = ""
    if pe:
        if pe > 50:
            val_analysis = f"P/E of **{pe:.1f}x** — stock is **richly valued**, priced for high growth expectations."
        elif pe > 25:
            val_analysis = f"P/E of **{pe:.1f}x** — moderate growth premium priced in."
        elif pe > 0:
            val_analysis = f"P/E of **{pe:.1f}x** — **reasonably valued** relative to earnings."
        else:
            val_analysis = "Negative P/E — company is currently **loss-making**."

    # Analyst recommendation
    rec_text = ""
    if rec and rec not in ("N/A", ""):
        rec_map = {
            "STRONG_BUY": "Analysts have a **Strong Buy** consensus",
            "BUY": "Analysts maintain a **Buy** recommendation",
            "HOLD": "Analysts suggest **Hold** — wait for a better entry point",
            "SELL": "Analysts recommend **Sell** — caution advised",
            "STRONG_SELL": "Analysts have a **Strong Sell** consensus — significant downside risk",
        }
        rec_text = rec_map.get(rec.upper().replace(" ", "_"), f"Analyst consensus: **{rec}**")
        if target and price:
            upside = ((target - price) / price) * 100
            rec_text += f". Mean price target: **{fmt_price(target, currency)}** ({'+' if upside > 0 else ''}{upside:.1f}% from current)."

    # Market cap label
    if mktcap:
        if mktcap > 200e9: cap_label = "Mega Cap (>$200B)"
        elif mktcap > 10e9: cap_label = "Large Cap (>$10B)"
        elif mktcap > 2e9: cap_label = "Mid Cap"
        else: cap_label = "Small Cap"
    else:
        cap_label = "N/A"

    # Volatility label
    if vol > 60: vol_label = "Very High"
    elif vol > 35: vol_label = "High"
    elif vol > 20: vol_label = "Moderate"
    else: vol_label = "Low"

    report = f"""## 📊 FinSage Analysis Report — {name} ({ticker})
**Generated:** {now}  
**Asset Class:** Global Stock | **Exchange:** {data.get('exchange', 'N/A')} | **Sector:** {sector}

---

### 💰 Current Market Data

| Metric | Value |
|--------|-------|
| **Current Price** | {fmt_price(price, currency)} |
| **24H Change** | {'🔴' if change < 0 else '🟢'} {change:+.2f}% |
| **Day High / Low** | {fmt_price(day_high, currency)} / {fmt_price(day_low, currency)} |
| **52-Week High** | {fmt_price(week_high, currency)} |
| **52-Week Low** | {fmt_price(week_low, currency)} |
| **Market Cap** | {format_number(mktcap)} |
| **P/E Ratio** | {f'{pe:.2f}x' if pe else 'N/A'} |
| **EPS** | {fmt_price(eps, currency) if eps else 'N/A'} |
| **Dividend Yield** | {f'{div*100:.2f}%' if div else 'N/A'} |
| **Beta** | {f'{beta:.2f}' if beta else 'N/A'} |
| **Annualized Volatility** | {vol:.1f}% |

---

### 📈 Trend & Sentiment Analysis

- **Current Trend:** {trend}
- **Market Sentiment:** {sentiment}
- **Risk Score:** {risk}/10 — {risk_label}

{range_analysis}

{vol_analysis}

---

### 🔍 Fundamental Analysis

{val_analysis}

{rec_text}

**Dividend:** {'This stock pays a **' + f'{div*100:.2f}% annual dividend yield**' + ' — attractive for income investors.' if div and div > 0 else 'This stock currently pays **no dividend** — growth-focused.'}

{'**Beta:** ' + f'Beta of **{beta:.2f}** — stock is **{"more volatile" if beta > 1.2 else "less volatile" if beta < 0.8 else "similarly volatile"}** compared to the broader market.' if beta else ''}

---

### ⚠️ Risk Assessment

| Factor | Assessment |
|--------|-----------|
| **Overall Risk** | {risk_label} ({risk}/10) |
| **Volatility** | {vol_label} ({vol:.1f}% annualized) |
| **Market Cap** | {cap_label} |
| **Sector** | {sector} |

---

### 💡 Investment Perspective

"""

    if risk <= 3:
        report += "This asset exhibits **conservative risk characteristics** — suitable for long-term, risk-averse investors seeking stable capital appreciation."
    elif risk <= 6:
        report += "This asset carries **moderate risk** — suitable for balanced investors with a medium-term horizon (1–3 years). Consider systematic investment (SIP) for better cost averaging."
    else:
        report += "This asset carries **elevated risk** — suitable only for experienced investors with high risk tolerance and clearly defined stop-loss levels."

    if change > 5:
        report += " Recent strong momentum suggests bullish participation, but watch for potential pullbacks near resistance."
    elif change < -5:
        report += " Recent decline may present a buying opportunity for long-term investors — confirm with broader market trends before entry."

    # Trading Signals Section
    report += trading_signals_stock(data)

    report += f"""

---

### ⚖️ Legal Disclaimer

> This report is generated by **FinSage** for **educational and informational purposes only**. It does **not** constitute financial advice, investment recommendation, or solicitation to buy or sell any security. Past performance is not indicative of future results. Investing involves risk, including possible loss of principal. Please consult a SEBI-registered financial advisor before making any investment decisions. **FinSage is not a SEBI-registered investment advisor.**

*Report generated by FinSage Global Financial Intelligence Platform | {now}*
"""
    report += groq_stock_insight(data)
    return report


def analyze_crypto(data: dict) -> str:
    name = data.get("name", data.get("ticker", "N/A"))
    ticker = data.get("ticker", "N/A")
    asset_type = data.get("asset_type", "Cryptocurrency")
    price = data.get("current_price", 0) or 0
    change_24h = data.get("change_pct", 0) or 0
    change_7d = data.get("change_7d", 0) or 0
    change_30d = data.get("change_30d", 0) or 0
    market_cap = data.get("market_cap", 0) or 0
    volume_24h = data.get("volume_24h", 0) or 0
    risk = data.get("risk_score", 5)
    vol = data.get("volatility_annualized", 0) or 0
    ath = data.get("ath")
    ath_chg = data.get("ath_change_pct") or 0
    supply = data.get("circulating_supply")
    rank = data.get("market_cap_rank")
    high_24h = data.get("high_24h", 0) or 0
    low_24h = data.get("low_24h", 0) or 0

    now = datetime.now().strftime("%B %d, %Y %H:%M IST")
    trend = get_trend(change_24h)
    risk_label = get_risk_label(risk)
    sentiment = get_sentiment(change_24h, change_7d)
    is_meme = asset_type == "Meme Coin"

    # ATH analysis
    ath_text = ""
    if ath and ath_chg is not None:
        if ath_chg > -10:
            ath_text = f"Trading **near All-Time High** ({ath_chg:+.1f}% from ATH of {fmt_price(ath)}) — extremely bullish but correction risk is elevated."
        elif ath_chg > -50:
            ath_text = f"Trading **{abs(ath_chg):.0f}% below All-Time High** of {fmt_price(ath)} — potential recovery opportunity for risk-tolerant investors."
        else:
            ath_text = f"Trading **{abs(ath_chg):.0f}% below All-Time High** of {fmt_price(ath)} — significant recovery needed; high caution advised."

    # Volume/market cap ratio
    vol_ratio_text = ""
    if market_cap and volume_24h and market_cap > 0:
        ratio = volume_24h / market_cap
        if ratio > 0.5:
            vol_ratio_text = f"**Extremely high volume/market cap ratio ({ratio:.1%})** — unusual trading activity, possible volatility ahead."
        elif ratio > 0.1:
            vol_ratio_text = f"**Strong trading activity** — 24H volume is {ratio:.1%} of market cap, indicating healthy market interest."
        else:
            vol_ratio_text = f"**Normal trading volume** ({ratio:.1%} of market cap) — steady market participation."

    # Market cap label
    if market_cap > 100e9: cap_label = "Large Cap (>$100B)"
    elif market_cap > 10e9: cap_label = "Mid Cap (>$10B)"
    elif market_cap > 1e9: cap_label = "Small Cap (>$1B)"
    elif market_cap > 100e6: cap_label = "Micro Cap (>$100M)"
    else: cap_label = "Nano Cap (<$100M)"

    # Volatility label
    if vol > 150: vol_label = "Extreme"
    elif vol > 80: vol_label = "Very High"
    elif vol > 40: vol_label = "High"
    else: vol_label = "Moderate"

    report = f"""## {'🎭' if is_meme else '₿'} FinSage Analysis Report — {name} ({ticker})
**Generated:** {now}  
**Asset Class:** {asset_type} | **Market Rank:** {'#' + str(rank) if rank else 'N/A'}

---

### 💰 Current Market Data

| Metric | Value |
|--------|-------|
| **Current Price** | {fmt_price(price)} |
| **24H Change** | {'🔴' if change_24h < 0 else '🟢'} {change_24h:+.2f}% |
| **7D Change** | {'🔴' if change_7d < 0 else '🟢'} {change_7d:+.2f}% |
| **30D Change** | {'🔴' if change_30d < 0 else '🟢'} {change_30d:+.2f}% |
| **24H High / Low** | {fmt_price(high_24h)} / {fmt_price(low_24h)} |
| **Market Cap** | {format_number(market_cap)} |
| **24H Volume** | {format_number(volume_24h)} |
| **Circulating Supply** | {f'{supply:,.0f} {ticker}' if supply else 'N/A'} |
| **All-Time High** | {fmt_price(ath) if ath else 'N/A'} |
| **ATH Change** | {f'{ath_chg:+.1f}%' if ath_chg else 'N/A'} |
| **Annualized Volatility** | {vol:.1f}% |

---

### 📈 Trend & Sentiment Analysis

- **Current Trend:** {trend}
- **Market Sentiment:** {sentiment}
- **Risk Score:** {risk}/10 — {risk_label}

{ath_text}

{vol_ratio_text}

---

### 🔍 Market Analysis

**Short-Term (24H):** {'Positive momentum' if change_24h > 0 else 'Negative pressure'} — {abs(change_24h):.2f}% {'gain' if change_24h > 0 else 'decline'}.

**Medium-Term (7D):** {'Bulls in control' if change_7d > 0 else 'Bears dominating'} — {abs(change_7d):.2f}% {'gain' if change_7d > 0 else 'loss'} over the past week.

**Monthly Trend (30D):** {'Strong upward trajectory' if change_30d > 5 else 'Significant decline — consider waiting for stabilization' if change_30d < -10 else 'Consolidation phase'} — {change_30d:+.2f}% over 30 days.

---

### ⚠️ Risk Assessment

| Factor | Assessment |
|--------|-----------|
| **Overall Risk** | {risk_label} ({risk}/10) |
| **Volatility** | {vol_label} ({vol:.1f}% annualized) |
| **Market Cap** | {format_number(market_cap)} ({cap_label}) |
| **Asset Class** | {asset_type} — {'⚠️ Highly speculative, community-driven' if is_meme else '✅ Established digital asset'} |

---

### 💡 Investment Perspective

"""

    if is_meme:
        report += """**Meme coins are highly speculative assets** driven primarily by social media sentiment, community hype, and influencer activity — not by fundamental value or utility.

**Key Risks to Understand:**
- Extreme price volatility — can drop 80-90% rapidly without warning
- No underlying fundamental value or real-world utility
- Susceptible to pump-and-dump schemes and whale manipulation
- Highly sensitive to celebrity statements and social media trends

**If considering an allocation:** Only use capital you can afford to lose entirely. Limit position to 1-5% of total portfolio maximum. Never invest borrowed money in meme coins."""
    elif risk <= 4:
        report += "This cryptocurrency demonstrates **relatively stable characteristics** for the crypto asset class. Suitable for investors seeking blockchain exposure with managed risk. A systematic DCA (Dollar-Cost Averaging) approach is recommended over lump-sum investment."
    elif risk <= 7:
        report += "This asset carries **significant volatility** typical of the crypto market. Use dollar-cost averaging (DCA) as an entry strategy. Set clear stop-loss levels and take-profit targets before entering a position."
    else:
        report += "This asset exhibits **extreme volatility**. Suitable only for active traders with strict risk management. Position sizing should be minimal (1-3% of portfolio maximum). Always use stop-loss orders."

    # Trading Signals Section
    report += trading_signals_crypto(data)

    report += f"""

---

### ⚖️ Legal Disclaimer

> This report is generated by **FinSage** for **educational and informational purposes only**. It does **not** constitute financial advice, investment recommendation, or solicitation to buy or sell any cryptocurrency. Cryptocurrency investments are subject to high market risk and are **not regulated by SEBI**. Past performance is not indicative of future results. Please consult a qualified financial advisor before making any investment decisions. **FinSage is not a SEBI-registered investment advisor.**

*Report generated by FinSage Global Financial Intelligence Platform | {now}*
"""
    report += groq_crypto_insight(data)
    return report
