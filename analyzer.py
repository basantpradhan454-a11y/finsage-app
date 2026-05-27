"""
FinSage AI Analyzer
━━━━━━━━━━━━━━━━━━
Generates structured financial intelligence reports.
Rule-based analysis + Gemini AI insights (gemini-2.5-flash, free tier).
"""

import os
import logging
import requests

logger = logging.getLogger("finsage.analyzer")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL   = "gemini-2.5-flash"
GEMINI_URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


# ── Gemini AI Helper ──────────────────────────────────────────────────────────
def _ask_gemini(prompt: str) -> str | None:
    """Call Gemini free API. Returns text or None on failure."""
    if not GEMINI_API_KEY:
        return None
    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"maxOutputTokens": 400, "temperature": 0.7}},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        logger.warning(f"Gemini API error {resp.status_code}: {resp.text[:100]}")
        return None
    except Exception as e:
        logger.warning(f"Gemini call failed: {e}")
        return None


def generate_ai_insight(data: dict, category: str, risk_label: str) -> str | None:
    """Generate a concise AI insight using Gemini."""
    if data["asset_type"] == "stock":
        prompt = f"""You are a sharp financial analyst. Give a 3-sentence insight on this stock in simple English (mix Hindi is fine).
Asset: {data.get('name')} ({data.get('ticker')})
Category: {category} | Risk: {risk_label}
Price: {data.get('currency','$')}{data.get('current_price')} | Change today: {data.get('change_pct',0):.2f}%
P/E: {data.get('pe_ratio','N/A')} | Market Cap: {data.get('market_cap','N/A')} | Beta: {data.get('beta','N/A')}
ROE: {(data.get('roe') or 0)*100:.1f}% | Debt/Equity: {data.get('debt_to_equity','N/A')}%
Analyst rating: {data.get('analyst_key','N/A')} | Target: {data.get('currency','$')}{data.get('target_price','N/A')}
52W Range: {data.get('52w_low','?')} - {data.get('52w_high','?')}

Give: 1) Current momentum, 2) Key risk, 3) One-line verdict. Be direct and concise. End with a disclaimer that this is not financial advice."""
    else:
        is_meme = "Meme" in category or "Speculative" in category
        prompt = f"""You are a sharp crypto analyst. Give a 3-sentence insight on this {"meme coin" if is_meme else "crypto"} in simple English (mix Hindi is fine).
Asset: {data.get('name')} ({data.get('ticker')})
Category: {category} | Risk: {risk_label}
Price: ${data.get('current_price')} | 24h: {data.get('change_24h',0):.2f}% | 7d: {data.get('change_7d',0):.2f}%
Market Cap: ${data.get('market_cap','N/A')} | Rank: #{data.get('market_cap_rank','N/A')}
Sentiment: {data.get('sentiment_up_pct',50):.0f}% bullish | ATH change: {data.get('ath_change_pct','N/A')}%

Give: 1) Current momentum, 2) Key risk, 3) One-line verdict. Be direct. {"Warn about meme coin risks clearly." if is_meme else ""} End with a disclaimer that this is not financial advice."""

    return _ask_gemini(prompt)


# ── Category Classification ───────────────────────────────────────────────────
def classify_asset(data: dict) -> str:
    if data["asset_type"] == "stock":
        sector = (data.get("sector") or "").lower()
        mcap   = data.get("market_cap") or 0
        pe     = data.get("pe_ratio") or 0
        if mcap > 200_000_000_000:
            return "🔵 Blue-Chip Stock"
        elif "technology" in sector or "software" in sector or pe > 40:
            return "🚀 High-Growth Tech Stock"
        else:
            return "📊 Growth / Value Stock"
    else:
        name     = (data.get("name") or "").lower()
        coin_id  = (data.get("coin_id") or "").lower()
        cats     = [c.lower() for c in data.get("categories", [])]
        MEME_KW  = ["meme", "dog", "shib", "pepe", "floki", "bonk", "wif", "trump", "doge", "baby", "wojak"]
        is_meme  = (
            any(k in name for k in MEME_KW) or
            any(k in coin_id for k in MEME_KW) or
            any("meme" in c for c in cats)
        )
        if is_meme:
            return "🎭 Speculative / Meme Asset"
        LARGE_CAPS = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple",
                      "cardano", "polkadot", "the-open-network", "tron"]
        if coin_id in LARGE_CAPS:
            return "⚡ Utility Crypto (Large Cap)"
        return "💎 Mid-Cap Cryptocurrency"


# ── Risk Rating ───────────────────────────────────────────────────────────────
def calculate_risk_rating(data: dict, category: str) -> tuple:
    score = 5

    if data["asset_type"] == "stock":
        risk_type = "Market Cyclicality"
        beta  = float(data.get("beta") or 1.0)
        de    = float(data.get("debt_to_equity") or 0)
        vol   = float(data.get("volatility_5d_pct") or 0)
        mcap  = float(data.get("market_cap") or 0)

        if mcap > 500_000_000_000: score -= 1
        elif mcap < 2_000_000_000: score += 2
        if beta > 1.5: score += 2
        elif beta < 0.8: score -= 1
        if de > 200: score += 2
        elif de > 100: score += 1
        if vol > 3: score += 1

        explanation = (
            f"Beta {beta:.2f} indicates {'high' if beta > 1.2 else 'moderate'} market sensitivity. "
            f"Debt/Equity {de:.0f}% {'—elevated leverage' if de > 150 else '—manageable'}. "
            f"5-day volatility: {vol:.2f}%. Risk driven by **{risk_type}** — macro cycles, earnings surprises."
        )

    else:
        is_meme   = "Meme" in category or "Speculative" in category
        risk_type = "Extreme Volatility" if is_meme else "Crypto Market Volatility"
        vol_24h   = float(data.get("volatility_24h_pct") or 0)
        chg_7d    = abs(float(data.get("change_7d") or 0))
        mcap      = float(data.get("market_cap") or 0)
        sentiment = float(data.get("sentiment_up_pct") or 50)

        if mcap < 100_000_000: score += 3
        elif mcap < 1_000_000_000: score += 2
        elif mcap < 10_000_000_000: score += 1
        if vol_24h > 10: score += 2
        elif vol_24h > 5: score += 1
        if chg_7d > 30: score += 1
        if is_meme: score += 1

        if is_meme:
            explanation = (
                f"⚠️ **{risk_type}** dominates. 24h volatility: {vol_24h:.2f}%. "
                f"7-day swing: {chg_7d:.1f}%. Community sentiment: {sentiment:.0f}% bullish. "
                f"Meme coins are driven by social hype — NOT fundamentals. Can drop 80%+ in hours."
            )
        else:
            explanation = (
                f"**{risk_type}** primary driver. 24h volatility: {vol_24h:.2f}%. "
                f"7-day move: {chg_7d:.1f}%. Market cap {'strong' if mcap > 10_000_000_000 else 'moderate'} liquidity. "
                f"Susceptible to regulatory shifts and macro correlation."
            )

    score = max(1, min(10, score))
    label = (
        "🟢 Low Risk"      if score <= 3 else
        "🟡 Moderate Risk" if score <= 5 else
        "🟠 High Risk"     if score <= 7 else
        "🔴 Very High Risk"
    )
    return score, label, explanation


# ── Verdict ───────────────────────────────────────────────────────────────────
def generate_verdict(data: dict, category: str) -> str:
    if data["asset_type"] == "stock":
        change  = float(data.get("change_pct") or 0)
        target  = data.get("target_price")
        rating  = data.get("analyst_key", "")
        current = float(data.get("current_price") or 0)
        upside  = ((target - current) / current * 100) if (target and current) else None
        cur     = data.get("currency", "$")

        bullish, bearish = [], []
        if upside and upside > 10:
            bullish.append(f"Analyst target implies **{upside:.1f}% upside** ({cur}{target:.2f})")
        if rating in ["buy", "strong_buy"]:
            bullish.append(f"Analyst rating: **{rating.replace('_', ' ').title()}**")
        if change > 1:
            bullish.append(f"Positive today: +{change:.2f}%")
        if (data.get("roe") or 0) > 0.15:
            bullish.append(f"Strong ROE: {(data['roe']*100):.1f}%")
        if upside and upside < -5:
            bearish.append("Trading above analyst target — overvaluation risk")
        if (data.get("debt_to_equity") or 0) > 150:
            bearish.append("High leverage — rate-sensitive")
        if change < -1:
            bearish.append(f"Sell pressure: {change:.2f}% today")
    else:
        chg_24h   = float(data.get("change_24h") or 0)
        chg_7d    = float(data.get("change_7d") or 0)
        sentiment = float(data.get("sentiment_up_pct") or 50)
        ath_chg   = float(data.get("ath_change_pct") or 0)
        is_meme   = "Meme" in category or "Speculative" in category

        bullish, bearish = [], []
        if sentiment > 65:
            bullish.append(f"Strongly bullish sentiment: {sentiment:.0f}% positive")
        if chg_24h > 5:
            bullish.append(f"Strong 24h momentum: +{chg_24h:.2f}%")
        if chg_7d > 10:
            bullish.append(f"Weekly uptrend: +{chg_7d:.2f}%")
        if ath_chg > -20:
            bullish.append(f"Near ATH — only {abs(ath_chg):.1f}% below peak")
        if sentiment < 40:
            bearish.append(f"Negative sentiment: {sentiment:.0f}% bullish only")
        if chg_24h < -5:
            bearish.append(f"Sell pressure: {chg_24h:.2f}% (24h)")
        if ath_chg < -80:
            bearish.append(f"Deep ATH discount ({ath_chg:.1f}%) — recovery uncertain")
        if is_meme:
            bullish.append("Viral moment / influencer tweet → potential 2x–10x spike")
            bearish.append("No catalyst = gradual bleed risk")
            bearish.append("No intrinsic value floor — near-zero possible")

    parts = []
    if bullish:
        parts.append("**📈 Bullish Triggers:**\n" + "\n".join(f"- {b}" for b in bullish))
    if bearish:
        parts.append("**📉 Bearish Triggers:**\n" + "\n".join(f"- {b}" for b in bearish))
    if not parts:
        parts.append("**↔️ Neutral:** No strong directional signals. Monitor volume and news.")
    return "\n\n".join(parts)


# ── Master Report ─────────────────────────────────────────────────────────────
def generate_report(data: dict) -> dict:
    category                             = classify_asset(data)
    risk_score, risk_label, risk_explanation = calculate_risk_rating(data, category)
    verdict                              = generate_verdict(data, category)
    ai_insight                           = generate_ai_insight(data, category, risk_label)

    def fmt(val, prefix="$") -> str:
        if val is None: return "N/A"
        try:
            v = float(val)
            if v >= 1e12: return f"{prefix}{v/1e12:.2f}T"
            if v >= 1e9:  return f"{prefix}{v/1e9:.2f}B"
            if v >= 1e6:  return f"{prefix}{v/1e6:.2f}M"
            if v >= 1e3:  return f"{prefix}{v/1e3:.1f}K"
            return f"{prefix}{v:,.4f}"
        except: return str(val)

    if data["asset_type"] == "stock":
        cur = data.get("currency", "$")
        metrics = {
            "Current Price":  f"{cur} {data.get('current_price', 'N/A')}",
            "24h Change":     f"{data.get('change_pct', 0):.2f}%" if data.get('change_pct') is not None else "N/A",
            "Market Cap":     fmt(data.get("market_cap")),
            "P/E Ratio":      f"{data.get('pe_ratio', 'N/A')}",
            "Volume":         fmt(data.get("volume"), ""),
            "Avg Volume":     fmt(data.get("avg_volume"), ""),
            "5d Volatility":  f"{data.get('volatility_5d_pct', 'N/A')}%",
            "52W High":       f"{cur} {data.get('52w_high', 'N/A')}",
            "52W Low":        f"{cur} {data.get('52w_low', 'N/A')}",
            "Beta":           f"{data.get('beta', 'N/A')}",
        }
        beta  = data.get("beta") or 1.0
        roe   = (data.get("roe") or 0) * 100
        de    = data.get("debt_to_equity") or 0
        chg   = abs(data.get("change_pct") or 0)
        pulse = (
            f"**Financial Health:** "
            f"{'Profitable' if (data.get('profit_margin') or 0) > 0 else 'Unprofitable'} — "
            f"ROE {roe:.1f}%, Debt/Equity {de:.0f}%.\n\n"
            f"**Market Trend:** Price {'up' if (data.get('change_pct') or 0) > 0 else 'down'} "
            f"{chg:.2f}% today. 52W: {data.get('currency','')}{data.get('52w_low','?')} — "
            f"{data.get('currency','')}{data.get('52w_high','?')}. "
            f"Analyst: **{(data.get('analyst_key') or 'N/A').replace('_',' ').title()}** "
            f"(target: {data.get('currency','')}{data.get('target_price', 'N/A')}).\n\n"
            f"**Macro Sensitivity:** Beta {beta:.2f} — moves "
            f"{'more' if beta > 1 else 'less'} than the broader market."
        )
    else:
        is_meme = "Meme" in category or "Speculative" in category
        metrics = {
            "Current Price":  f"${data.get('current_price', 'N/A')}",
            "24h Change":     f"{data.get('change_24h', 0):.2f}%" if data.get('change_24h') is not None else "N/A",
            "7d Change":      f"{data.get('change_7d', 0):.2f}%" if data.get('change_7d') is not None else "N/A",
            "Market Cap":     fmt(data.get("market_cap")),
            "24h Volume":     fmt(data.get("total_volume")),
            "24h Volatility": f"{data.get('volatility_24h_pct', 'N/A')}%",
            "ATH":            f"${data.get('ath', 'N/A')}",
            "ATH Change":     f"{data.get('ath_change_pct', 'N/A')}%",
            "CMC Rank":       f"#{data.get('market_cap_rank', 'N/A')}",
            "Sentiment":      f"{data.get('sentiment_up_pct', 'N/A'):.0f}% Bullish",
        }
        sent = float(data.get("sentiment_up_pct") or 50)
        pulse = (
            f"**Community Sentiment:** {sent:.0f}% bullish. "
            f"Twitter: {fmt(data.get('twitter_followers'), '')} followers. "
            f"Reddit: {fmt(data.get('reddit_subscribers'), '')} subscribers.\n\n"
            f"**Volume Volatility:** 24h volume {fmt(data.get('total_volume'))}. "
            f"{'Active speculation.' if is_meme else 'Healthy liquidity.'}\n\n"
        )
        if is_meme:
            pulse += (
                "**⚠️ Social Hype Risk:** NO fundamental value — no earnings, no cash flows. "
                "Price moves 100% on narrative, tweets, and herd behavior. "
                "A single influencer post can move price ±50%. Treat as pure speculation."
            )
        else:
            pulse += (
                f"**On-Chain Trend:** {'Strong' if sent > 55 else 'Weak'} community conviction. "
                f"30-day change: {data.get('change_30d', 'N/A')}%."
            )

    return {
        "name":             data.get("name"),
        "ticker":           data.get("ticker"),
        "exchange":         data.get("exchange") or "CoinGecko / Crypto Market",
        "category":         category,
        "metrics":          metrics,
        "pulse":            pulse,
        "risk_score":       risk_score,
        "risk_label":       risk_label,
        "risk_explanation": risk_explanation,
        "verdict":          verdict,
        "ai_insight":       ai_insight,
        "asset_type":       data["asset_type"],
        "is_meme":          is_meme if data["asset_type"] == "crypto" else False,
    }
