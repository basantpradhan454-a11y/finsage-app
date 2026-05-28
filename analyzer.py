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

    report += f"""

---

### ⚖️ Legal Disclaimer

> This report is generated by **FinSage** for **educational and informational purposes only**. It does **not** constitute financial advice, investment recommendation, or solicitation to buy or sell any cryptocurrency. Cryptocurrency investments are subject to high market risk and are **not regulated by SEBI**. Past performance is not indicative of future results. Please consult a qualified financial advisor before making any investment decisions. **FinSage is not a SEBI-registered investment advisor.**

*Report generated by FinSage Global Financial Intelligence Platform | {now}*
"""
    report += groq_crypto_insight(data)
    return report
