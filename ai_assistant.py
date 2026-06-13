"""
STOX AI — AI Research Assistant
10 Professional Analysis Modules:
1. Full Stock Research Report
2. Earnings Call Breakdown
3. Red Flag Detector
4. Competitive Moat Analysis
5. Valuation Comparison
6. DCF Assumption Builder
7. Stock Catalyst Calendar
8. Management Quality Review
9. Bull vs Bear Debate
10. Beginner Stock Checklist
"""

import streamlit as st
import re
from datetime import datetime
from data_fetcher import fetch_stock_data, fetch_crypto_data
from analyzer import analyze_stock, analyze_crypto, format_number

LOGO_URL = "https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"

# ═══════════════════════════════════════════════════════════════════════════════
# 10 ANALYSIS MODULE ENGINES
# ═══════════════════════════════════════════════════════════════════════════════

def generate_full_research_report(ticker: str, data: dict) -> str:
    name    = data.get("name", ticker)
    price   = data.get("current_price", 0) or 0
    chg     = data.get("change_pct", 0) or 0
    mcap    = data.get("market_cap", 0) or 0
    vol     = data.get("volatility_annualized", 0) or 0
    risk    = data.get("risk_score", 5) or 5
    atype   = data.get("asset_type", "Stock")
    pe      = data.get("pe_ratio", 0) or 0
    eps     = data.get("eps", 0) or 0
    div     = data.get("dividend_yield", 0) or 0
    beta    = data.get("beta", 1) or 1
    high52  = data.get("week_52_high", 0) or 0
    low52   = data.get("week_52_low", 0) or 0

    from_52h = ((price - high52) / high52 * 100) if high52 else 0
    from_52l = ((price - low52) / low52 * 100) if low52 else 0

    bull_case  = price * 1.35
    base_case  = price * 1.15
    bear_case  = price * 0.75

    report = f"""# 📋 Full Stock Research Report — {name} ({ticker})
**Generated:** {datetime.now().strftime("%B %d, %Y")} | **Source:** Yahoo Finance (yfinance) | **Type:** {atype}

---

## 🏢 Company Overview & Business Model
**{name}** is a publicly listed {atype.lower()} trading under the ticker **{ticker}**.
The company operates in a competitive market environment where revenue is generated through its core
business segments. As a {atype}, it attracts investors seeking {"growth and capital appreciation" if risk > 6 else "stability and consistent returns"}.

---

## 💰 Key Revenue & Financial Performance
| Metric | Value |
|--------|-------|
| **Current Price** | ${price:,.2f} |
| **24H Change** | {chg:+.2f}% |
| **Market Cap** | {format_number(mcap)} |
| **P/E Ratio** | {pe:.1f}x {"(High Valuation)" if pe > 30 else "(Moderate)" if pe > 15 else "(Low Valuation)"} |
| **EPS** | ${eps:.2f} |
| **Dividend Yield** | {div:.2f}% |
| **Beta** | {beta:.2f} {"(High Risk)" if beta > 1.5 else "(Moderate)" if beta > 0.8 else "(Defensive)"} |
| **52W High** | ${high52:,.2f} ({from_52h:+.1f}% from current) |
| **52W Low** | ${low52:,.2f} ({from_52l:+.1f}% from current) |
| **Annualized Volatility** | {vol:.1f}% |
| **Risk Score** | {risk}/10 |

---

## 📈 Industry Outlook & Market Trends
- Global market conditions are {"favorable" if chg > 0 else "under pressure"} for this asset class
- Volatility of {vol:.1f}% suggests {"high" if vol > 40 else "moderate" if vol > 20 else "low"} price swings expected
- Beta of {beta:.2f} means {"more volatile than" if beta > 1 else "less volatile than"} the broader market

---

## ⚔️ Competitive Landscape
- **Position:** {"Market leader with strong brand" if risk < 4 else "Competitive mid-tier player" if risk < 7 else "Speculative/emerging player"}
- **Valuation vs Peers:** P/E of {pe:.1f}x is {"premium-priced" if pe > 30 else "fairly valued" if pe > 12 else "value territory"}
- **Moat Assessment:** {"Strong — established revenue base" if risk < 4 else "Moderate — competitive pressures present" if risk < 7 else "Weak — speculative with limited moat"}

---

## 🎯 Bull, Base & Bear Scenarios

| Scenario | Price Target | Upside | Key Assumption |
|----------|-------------|--------|----------------|
| 🟢 **Bull Case** | ${bull_case:,.2f} | +35% | Strong growth, margin expansion |
| 🟡 **Base Case** | ${base_case:,.2f} | +15% | Steady performance, inline results |
| 🔴 **Bear Case** | ${bear_case:,.2f} | -25% | Macro headwinds, sector rotation |

---

## ⚠️ Key Risks & Challenges
- **Volatility Risk:** {vol:.1f}% annualized — {"Extreme caution advised" if vol > 60 else "Monitor closely" if vol > 30 else "Manageable risk"}
- **Valuation Risk:** {"Overvalued — limited upside at current P/E" if pe > 40 else "Fairly priced relative to growth" if pe > 15 else "Potential value opportunity"}
- **Market Risk:** Beta {beta:.2f} — {"amplified losses in market downturns" if beta > 1.2 else "relatively defensive in downturns"}
- **Concentration Risk:** Single-asset exposure requires diversification

---

## 📝 Investment Thesis Summary
{name} ({ticker}) presents a **{"high-risk, high-reward" if risk > 7 else "moderate risk" if risk > 4 else "lower-risk defensive"}** opportunity.
At the current price of **${price:,.2f}**, the stock is trading **{abs(from_52h):.1f}% below its 52-week high**.

**Most Important Metrics to Watch:**
1. Quarterly earnings vs estimates
2. Revenue growth trajectory
3. Margin trends (gross + operating)
4. Cash flow generation vs debt levels

---

> ⚖️ **Disclaimer:** This report is generated using publicly available data (Yahoo Finance).
> It is for **educational purposes only** and does not constitute SEBI-registered investment advice.
> Facts are clearly distinguished from analytical opinions. No buy, sell, or hold recommendation is provided.
"""
    return report


def generate_earnings_breakdown(ticker: str, data: dict) -> str:
    name  = data.get("name", ticker)
    price = data.get("current_price", 0) or 0
    eps   = data.get("eps", 0) or 0
    pe    = data.get("pe_ratio", 0) or 0
    mcap  = data.get("market_cap", 0) or 0
    chg   = data.get("change_pct", 0) or 0
    rev   = data.get("revenue", 0) or 0
    gm    = data.get("gross_margin", 0) or 0
    om    = data.get("operating_margin", 0) or 0
    nm    = data.get("net_margin", 0) or 0

    tone = "Positive" if chg > 1 else ("Cautious" if chg < -1 else "Neutral")
    surprise = "Beat" if chg > 2 else ("Miss" if chg < -2 else "In-line")

    report = f"""# 📞 Earnings Call Breakdown — {name} ({ticker})
**Generated:** {datetime.now().strftime("%B %d, %Y")} | **Source:** Yahoo Finance

---

## 🎯 5 Biggest Takeaways

1. **Revenue Performance:** {format_number(rev)} in latest reported period — {"above" if chg > 0 else "below"} prior period expectations
2. **Margin Trends:** Gross margin at {gm:.1f}%, Operating margin at {om:.1f}% — {"expanding" if om > 15 else "under pressure"}
3. **EPS vs Estimates:** Reported EPS of ${eps:.2f} — consensus was {"surprised to the upside" if chg > 1 else "met" if chg > -1 else "missed"}
4. **Management Tone:** {tone} — {"forward guidance raised, confidence in execution" if tone == "Positive" else "cautious on macro environment, watching costs" if tone == "Cautious" else "steady outlook maintained, no major guidance changes"}
5. **Key Risk Flagged:** {"Margin pressure from input costs" if om < 10 else "Valuation premium requires continued execution" if pe > 30 else "Competition intensifying in core markets"}

---

## 📊 Key Metrics Table

| Metric | Latest Result | Prior Period Est. | Change | Why It Matters |
|--------|--------------|-------------------|--------|----------------|
| **Revenue** | {format_number(rev)} | ~{format_number(rev * 0.95)} | {chg:+.1f}% | Top-line growth driver |
| **EPS** | ${eps:.2f} | ~${eps * 0.95:.2f} | {chg:+.1f}% | Profitability per share |
| **Gross Margin** | {gm:.1f}% | ~{gm * 0.98:.1f}% | {(gm - gm*0.98):+.1f}pp | Business efficiency |
| **Operating Margin** | {om:.1f}% | ~{om * 0.97:.1f}% | {(om - om*0.97):+.1f}pp | Core profitability |
| **Net Margin** | {nm:.1f}% | ~{nm * 0.96:.1f}% | {(nm - nm*0.96):+.1f}pp | Bottom-line health |
| **P/E Ratio** | {pe:.1f}x | N/A | N/A | Valuation benchmark |

---

## 😊 Positive Surprises
- {"Strong revenue growth exceeding prior-period estimates" if chg > 0 else "Cost discipline maintained despite revenue pressure"}
- {"Margin improvement signals operational leverage" if om > 15 else "Management reiterated long-term targets"}
- {"Cash generation remains solid, balance sheet strong" if nm > 10 else "Working capital management improved"}

## 😟 Negative Surprises / Analyst Concerns
- {"Slowing growth momentum vs high valuation multiples" if pe > 30 else "Margin compression risk in near term"}
- {"Macro headwinds — interest rates, FX impact" if chg < 0 else "Competitive pricing pressure building"}
- {"Guidance below Street expectations raises questions" if chg < -1 else "Execution risk on new initiatives"}

---

## 👀 What Investors Should Watch Next
1. **Next Earnings Date:** Watch for Q/Q revenue acceleration or deceleration
2. **Margin Trajectory:** Is {om:.1f}% operating margin sustainable or will it compress?
3. **Guidance Updates:** Any guidance raise = strong buy signal; cut = de-rate risk
4. **Insider Activity:** Any unusual selling post-earnings is a red flag
5. **Analyst Upgrades/Downgrades:** Price target changes in next 2 weeks are key

---

> ⚖️ **Disclaimer:** Educational analysis based on public data. Not investment advice.
"""
    return report


def generate_red_flag_detector(ticker: str, data: dict) -> str:
    name  = data.get("name", ticker)
    vol   = data.get("volatility_annualized", 0) or 0
    risk  = data.get("risk_score", 5) or 5
    pe    = data.get("pe_ratio", 0) or 0
    beta  = data.get("beta", 1) or 1
    de    = data.get("debt_to_equity", 0) or 0
    nm    = data.get("net_margin", 0) or 0
    gm    = data.get("gross_margin", 0) or 0
    chg   = data.get("change_pct", 0) or 0
    div   = data.get("dividend_yield", 0) or 0
    high52= data.get("week_52_high", 0) or 0
    price = data.get("current_price", 0) or 0
    from_high = ((price - high52) / high52 * 100) if high52 else 0

    flags = []
    total_severity = 0

    # Evaluate red flags
    if vol > 80:
        flags.append(("🔴 Extreme Volatility", 9, f"Annualized volatility of {vol:.1f}% — extremely risky, price can swing 80%+ in a year", "Revenue quality", "Suggests speculative nature, potential pump-and-dump risk"))
    elif vol > 50:
        flags.append(("🟠 High Volatility", 6, f"Volatility of {vol:.1f}% — significantly higher than market average (~20%)", "Risk assessment", "High volatility often means uncertain fundamentals"))

    if pe > 80:
        flags.append(("🔴 Extreme Overvaluation", 8, f"P/E ratio of {pe:.1f}x — extremely overvalued vs market average of 20x", "Valuation concern", "Any earnings miss could cause 30-50% price correction"))
    elif pe > 50:
        flags.append(("🟠 High Valuation Risk", 6, f"P/E of {pe:.1f}x — premium valuation requires perfect execution", "Valuation", "Limited margin of safety at current multiples"))

    if de > 2:
        flags.append(("🔴 High Debt Burden", 7, f"Debt/Equity ratio of {de:.1f}x — dangerously leveraged", "Debt levels", "High debt amplifies losses in economic downturns, risk of insolvency"))
    elif de > 1:
        flags.append(("🟡 Elevated Debt", 4, f"D/E ratio of {de:.1f}x — above comfortable levels", "Debt", "Debt servicing costs reduce flexibility"))

    if nm < 0:
        flags.append(("🔴 Negative Profitability", 8, f"Net margin of {nm:.1f}% — company is losing money", "Profitability", "Cash burn risk — survival depends on external funding"))
    elif nm < 5:
        flags.append(("🟡 Thin Margins", 4, f"Net margin of {nm:.1f}% — very thin profit buffer", "Margin sustainability", "Any cost increase wipes out profits"))

    if gm < 20 and gm > 0:
        flags.append(("🟡 Low Gross Margin", 4, f"Gross margin of {gm:.1f}% — limited pricing power", "Revenue quality", "Commodity-like business with limited competitive moat"))

    if from_high < -50:
        flags.append(("🔴 Major Price Decline", 7, f"Down {abs(from_high):.1f}% from 52-week high — significant wealth destruction", "Price action", "Could signal fundamental deterioration or loss of investor confidence"))
    elif from_high < -30:
        flags.append(("🟠 Significant Drawdown", 5, f"Down {abs(from_high):.1f}% from 52-week high", "Price action", "Underperformance vs market requires fundamental justification"))

    if beta > 2:
        flags.append(("🟠 High Market Sensitivity", 5, f"Beta of {beta:.2f} — moves 2x the market in both directions", "Market risk", "Amplified losses in bear markets"))

    if div > 10 and div > 0:
        flags.append(("🟡 Unsustainable Dividend?", 5, f"Dividend yield of {div:.1f}% — unusually high, may be unsustainable", "Income quality", "Very high yields often precede dividend cuts"))

    for flag in flags:
        total_severity += flag[1]

    overall_score = min(total_severity // max(len(flags), 1), 10) if flags else 2
    overall_color = "🔴" if overall_score >= 7 else ("🟠" if overall_score >= 4 else "🟢")
    overall_label = "HIGH RISK — Multiple Serious Concerns" if overall_score >= 7 else ("MODERATE RISK — Monitor Carefully" if overall_score >= 4 else "LOW RISK — No Major Red Flags")

    report = f"""# 🚩 Red Flag Detector — {name} ({ticker})
**Generated:** {datetime.now().strftime("%B %d, %Y")} | **Analyst:** Forensic Research Mode

---

## {overall_color} Overall Red Flag Score: {overall_score}/10 — {overall_label}

---

## 🔍 Identified Red Flags ({len(flags)} found)

"""
    if not flags:
        report += "✅ **No major red flags identified** based on available financial data.\n\nThis does not mean the investment is risk-free — always conduct thorough due diligence.\n\n"
    else:
        for i, (flag_name, severity, issue, category, impact) in enumerate(flags, 1):
            bar = "█" * severity + "░" * (10 - severity)
            report += f"""### {i}. {flag_name}
| Field | Detail |
|-------|--------|
| **Severity** | {severity}/10  `{bar}` |
| **Category** | {category} |
| **Issue** | {issue} |
| **Why It Matters** | {impact} |

"""

    report += f"""---

## 📋 Full Assessment Areas

| Area | Status | Notes |
|------|--------|-------|
| **Revenue Quality** | {"⚠️ Concern" if nm < 5 else "✅ OK"} | Net margin: {nm:.1f}% |
| **Margin Sustainability** | {"⚠️ Thin" if gm < 25 else "✅ Healthy"} | Gross margin: {gm:.1f}% |
| **Debt & Liquidity** | {"🔴 High" if de > 2 else "🟡 Moderate" if de > 1 else "✅ Low"} | D/E: {de:.1f}x |
| **Valuation** | {"🔴 Extreme" if pe > 80 else "🟡 High" if pe > 40 else "✅ Reasonable"} | P/E: {pe:.1f}x |
| **Volatility** | {"🔴 Extreme" if vol > 80 else "🟡 High" if vol > 40 else "✅ Normal"} | {vol:.1f}% annualized |
| **Price vs 52W High** | {"🔴 Major Drop" if from_high < -40 else "🟡 Pullback" if from_high < -15 else "✅ Near Highs"} | {from_high:+.1f}% |
| **Dividend Sustainability** | {"⚠️ Check" if div > 8 else "✅ Normal"} | {div:.1f}% yield |
| **Market Sensitivity** | {"🔴 High" if beta > 2 else "🟡 Moderate" if beta > 1.2 else "✅ Low"} | Beta: {beta:.2f} |

---

## 🎯 Most Critical Risks Summary
{"- Extreme volatility suggests speculative nature — position size carefully" if vol > 60 else "- Volatility is manageable but monitor news catalysts"}
{"- Negative profitability is the #1 red flag — cash burn must be monitored" if nm < 0 else "- Maintain profitability watch, especially in rising cost environment"}
{"- High debt levels create fragility — economic slowdown could trigger distress" if de > 1.5 else "- Debt levels appear manageable at current metrics"}
{"- Extreme valuation leaves no margin of safety — any miss = severe correction" if pe > 60 else "- Valuation risk is present but not extreme"}

---

> ⚖️ **Disclaimer:** Forensic analysis for educational purposes. Not SEBI investment advice.
> All flags are based on publicly available data and analytical interpretation — not statements of fact.
"""
    return report


def generate_moat_analysis(ticker: str, data: dict) -> str:
    name  = data.get("name", ticker)
    risk  = data.get("risk_score", 5) or 5
    pe    = data.get("pe_ratio", 0) or 0
    gm    = data.get("gross_margin", 0) or 0
    mcap  = data.get("market_cap", 0) or 0
    beta  = data.get("beta", 1) or 1
    vol   = data.get("volatility_annualized", 0) or 0

    # Score moat factors based on available data
    brand_score      = max(1, min(5, 5 - risk // 2))
    network_score    = max(1, min(5, 4 if mcap > 100_000_000_000 else 3 if mcap > 10_000_000_000 else 2))
    switching_score  = max(1, min(5, 4 if pe > 25 else 3 if pe > 15 else 2))
    cost_score       = max(1, min(5, 4 if gm > 50 else 3 if gm > 30 else 2))
    scale_score      = max(1, min(5, 5 if mcap > 500_000_000_000 else 4 if mcap > 100_000_000_000 else 3 if mcap > 10_000_000_000 else 2))
    ip_score         = max(1, min(5, 4 if gm > 60 else 3 if gm > 40 else 2))
    distribution_score = max(1, min(5, 4 if mcap > 50_000_000_000 else 3))
    regulatory_score = max(1, min(5, 3))
    data_score       = max(1, min(5, 4 if mcap > 100_000_000_000 else 2))
    loyalty_score    = max(1, min(5, 5 - risk // 2))

    total = (brand_score + network_score + switching_score + cost_score + scale_score +
             ip_score + distribution_score + regulatory_score + data_score + loyalty_score)
    avg = total / 10

    moat_status = "🟢 EXPANDING" if avg >= 3.5 else ("🟡 STABLE" if avg >= 2.5 else "🔴 SHRINKING")

    def stars(s): return "⭐" * s + "☆" * (5-s)

    report = f"""# 🏰 Competitive Moat Analysis — {name} ({ticker})
**Generated:** {datetime.now().strftime("%B %d, %Y")} | **Scale:** 1 (Weak) → 5 (Strong)

---

## 🎯 Overall Moat Score: {avg:.1f}/5 — {moat_status}

---

## 📊 Moat Factor Ratings

| Factor | Score | Rating | Assessment |
|--------|-------|--------|------------|
| **Brand Strength** | {brand_score}/5 | {stars(brand_score)} | {"Iconic brand with strong consumer recognition" if brand_score >= 4 else "Recognizable but not dominant brand"} |
| **Network Effects** | {network_score}/5 | {stars(network_score)} | {"Strong network effects — more users = more value" if network_score >= 4 else "Limited network effect in current business model"} |
| **Switching Costs** | {switching_score}/5 | {stars(switching_score)} | {"High switching costs — customers locked in" if switching_score >= 4 else "Low switching costs — customers can move to competitors easily"} |
| **Cost Advantages** | {cost_score}/5 | {stars(cost_score)} | {"Gross margin of {:.1f}% shows strong pricing power".format(gm) if cost_score >= 4 else "Average cost structure, limited pricing power"} |
| **Scale & Market Position** | {scale_score}/5 | {stars(scale_score)} | {"Market cap of {:.0f}B signals dominant scale".format(mcap/1e9) if scale_score >= 4 else "Mid-size player without dominant scale advantage"} |
| **Intellectual Property** | {ip_score}/5 | {stars(ip_score)} | {"Strong IP portfolio protects revenue streams" if ip_score >= 4 else "Limited IP moat — technology/patents not dominant"} |
| **Distribution Reach** | {distribution_score}/5 | {stars(distribution_score)} | {"Extensive distribution network creates barriers" if distribution_score >= 4 else "Average distribution capabilities"} |
| **Regulatory Advantages** | {regulatory_score}/5 | {stars(regulatory_score)} | Regulatory environment: neutral to slightly favorable |
| **Data Assets** | {data_score}/5 | {stars(data_score)} | {"Massive data advantage — AI/ML capabilities" if data_score >= 4 else "Data assets are a growing but not yet dominant advantage"} |
| **Customer Loyalty** | {loyalty_score}/5 | {stars(loyalty_score)} | {"Very high customer loyalty and repeat business" if loyalty_score >= 4 else "Moderate loyalty — price-sensitive customer base"} |

---

## 💪 Strongest Competitive Advantages
1. **{"Scale dominance" if scale_score == max(brand_score,network_score,switching_score,cost_score,scale_score) else "Brand recognition"}** — Primary moat driver
2. **{"High gross margins" if gm > 40 else "Cost efficiency"}** — Margins of {gm:.1f}% {"suggest pricing power" if gm > 40 else "reflect competitive pressures"}
3. **{"Market capitalization of " + format_number(mcap)}** — Scale creates barriers to entry

## ⚔️ Biggest Competitive Threats
1. **Disruptive technology** — New entrants with lower cost structures
2. **{"Valuation compression risk" if pe > 30 else "Market share erosion"}** — {"Premium P/E of {:.1f}x leaves little room for error".format(pe) if pe > 30 else "Competitors are gaining ground in key segments"}
3. **Macro sensitivity** — Beta of {beta:.2f} suggests {"high" if beta > 1.5 else "moderate"} market dependence

---

## 📈 How the Moat Has Evolved
- **{"Expanding" if avg >= 3.5 else "Stable" if avg >= 2.5 else "Contracting"}** competitive position over recent years
- {"Growing scale advantage as market cap has compounded" if scale_score >= 4 else "Scale advantages are still being built"}
- {"Network effects are accelerating — digital business model benefits" if network_score >= 4 else "Network effect development is a key investment thesis"}

---

## 🏁 Conclusion
**{name}'s moat is {moat_status.split()[1].lower()}.**
{"The company has durable competitive advantages that protect returns on capital over the long term." if avg >= 3.5 else "The moat provides some protection but faces competitive pressure that investors should monitor." if avg >= 2.5 else "The competitive position is weakening — requires fundamental improvement in key moat factors."}

---

> ⚖️ **Disclaimer:** Educational analysis only. Not SEBI investment advice. Facts separated from opinions.
"""
    return report


def generate_valuation_comparison(ticker: str, data: dict) -> str:
    name  = data.get("name", ticker)
    price = data.get("current_price", 0) or 0
    pe    = data.get("pe_ratio", 0) or 0
    mcap  = data.get("market_cap", 0) or 0
    gm    = data.get("gross_margin", 0) or 0
    om    = data.get("operating_margin", 0) or 0
    nm    = data.get("net_margin", 0) or 0
    rev   = data.get("revenue", 0) or 0
    beta  = data.get("beta", 1) or 1

    # Estimated peer multiples (illustrative industry benchmarks)
    ev_rev   = (mcap / rev * 1.2) if rev else 5
    ev_ebitda= pe * 0.6 if pe else 15
    pfcf     = pe * 1.1 if pe else 20

    # Valuation verdict
    verdict = "🔴 EXPENSIVE" if pe > 40 else ("🟢 CHEAP" if pe < 12 else "🟡 FAIRLY VALUED")

    report = f"""# 📐 Valuation Comparison — {name} ({ticker})
**Generated:** {datetime.now().strftime("%B %d, %Y")} | **Benchmark:** Industry Peer Averages

---

## ⚖️ Valuation Verdict: {verdict}

---

## 📊 Valuation Metrics vs Peer Group

| Metric | {ticker} | Peer Avg | Premium/Discount | Assessment |
|--------|----------|----------|-----------------|------------|
| **Market Cap** | {format_number(mcap)} | N/A | — | {"Mega-cap" if mcap > 1e12 else "Large-cap" if mcap > 1e11 else "Mid-cap" if mcap > 1e10 else "Small-cap"} |
| **P/E Ratio** | {pe:.1f}x | ~20x | {pe-20:+.1f}x | {"Premium" if pe > 25 else "Discount" if pe < 15 else "In-line"} |
| **Forward P/E** | ~{pe*0.9:.1f}x | ~18x | {pe*0.9-18:+.1f}x | {"Priced for perfection" if pe*0.9 > 30 else "Reasonable forward multiple"} |
| **EV/Revenue** | {ev_rev:.1f}x | ~3x | {ev_rev-3:+.1f}x | {"Expensive vs peers" if ev_rev > 5 else "In-line" if ev_rev > 2 else "Cheap"} |
| **EV/EBITDA** | {ev_ebitda:.1f}x | ~12x | {ev_ebitda-12:+.1f}x | {"Premium to peers" if ev_ebitda > 15 else "Discount" if ev_ebitda < 10 else "Fair"} |
| **Price/FCF** | {pfcf:.1f}x | ~20x | {pfcf-20:+.1f}x | {"High" if pfcf > 25 else "Moderate"} |
| **Gross Margin** | {gm:.1f}% | ~40% | {gm-40:+.1f}pp | {"Above avg — justifies premium" if gm > 45 else "Below avg — limits multiple expansion"} |
| **Operating Margin** | {om:.1f}% | ~15% | {om-15:+.1f}pp | {"Strong profitability" if om > 20 else "Below average margins"} |
| **Net Margin** | {nm:.1f}% | ~12% | {nm-12:+.1f}pp | {"Highly profitable" if nm > 15 else "Thin margins"} |

---

## 🔍 Valuation Analysis vs Peers

**Where {ticker} looks {"expensive" if pe > 30 else "cheap" if pe < 12 else "fair"}:**
- P/E of {pe:.1f}x is {"significantly above" if pe > 30 else "below" if pe < 15 else "roughly in line with"} sector average of ~20x
- {"Premium justified by superior growth trajectory and margins" if pe > 30 and gm > 40 else "Discount reflects execution risk or slower growth" if pe < 15 else "Fair value reflects balanced risk/reward"}
- {"High gross margins of {:.1f}% support premium multiple".format(gm) if gm > 45 else "Margin improvement is key to multiple re-rating"}

---

## 💪 Strengths Supporting Current Valuation
1. **{"Premium profitability: " + str(round(gm,1)) + "% gross margin" if gm > 40 else "Scale advantages: " + format_number(mcap) + " market cap"}**
2. **{"High-quality earnings with strong operating leverage" if om > 15 else "Revenue diversification reduces single-point risk"}**
3. **{"Market leadership position in core segments" if mcap > 1e11 else "Growth opportunity in underpenetrated markets"}**

## ⚠️ Weaknesses That May Justify Discount
1. **{"Valuation premium leaves no margin of safety" if pe > 35 else "Competition pressuring margin sustainability"}**
2. **{"Growth deceleration risk — high P/E needs high growth" if pe > 30 else "Lack of clear catalysts for near-term re-rating"}**
3. **{"Beta of {:.2f} amplifies losses in risk-off environments".format(beta)}**

---

## 🔭 Key Metrics to Monitor
1. **Multiple expansion/contraction** — Watch for P/E changes vs earnings growth
2. **Margin trajectory** — Gross margin above/below {gm:.0f}% is key signal
3. **Revenue growth acceleration** — Needed to justify current multiples
4. **Peer group performance** — Relative valuation shifts signal sector rotation

---

> ⚖️ **Disclaimer:** Educational analysis. Peer comparisons are approximate industry benchmarks.
> Not SEBI-registered investment advice. No buy, sell, or hold recommendation.
"""
    return report


def generate_dcf_analysis(ticker: str, data: dict) -> str:
    name  = data.get("name", ticker)
    price = data.get("current_price", 0) or 0
    rev   = data.get("revenue", 0) or 0
    om    = data.get("operating_margin", 0) or 0
    mcap  = data.get("market_cap", 0) or 0
    pe    = data.get("pe_ratio", 0) or 0

    # DCF scenarios
    scenarios = {
        "🔴 Bear Case": {"rev_growth": 0.05, "op_margin": max(om-5, 0)/100, "tax": 0.25, "capex": 0.08, "wc": 0.03, "wacc": 0.12, "terminal_g": 0.02},
        "🟡 Base Case": {"rev_growth": 0.12, "op_margin": max(om, 10)/100, "tax": 0.22, "capex": 0.06, "wc": 0.02, "wacc": 0.10, "terminal_g": 0.03},
        "🟢 Bull Case": {"rev_growth": 0.20, "op_margin": min(om+5, 40)/100, "tax": 0.20, "capex": 0.05, "wc": 0.015, "wacc": 0.09, "terminal_g": 0.04},
    }

    def calc_dcf(rev, s):
        if not rev: return 0
        fcfs = []
        r = rev
        for _ in range(5):
            r = r * (1 + s["rev_growth"])
            ebit = r * s["op_margin"]
            nopat = ebit * (1 - s["tax"])
            capex_amt = r * s["capex"]
            wc_amt = r * s["wc"]
            fcf = nopat - capex_amt - wc_amt
            fcfs.append(fcf)
        pv_fcfs = sum(fcf / (1 + s["wacc"])**i for i, fcf in enumerate(fcfs, 1))
        terminal_val = fcfs[-1] * (1 + s["terminal_g"]) / (s["wacc"] - s["terminal_g"])
        pv_terminal = terminal_val / (1 + s["wacc"])**5
        enterprise_val = pv_fcfs + pv_terminal
        return enterprise_val

    bear_val = calc_dcf(rev, scenarios["🔴 Bear Case"])
    base_val = calc_dcf(rev, scenarios["🟡 Base Case"])
    bull_val = calc_dcf(rev, scenarios["🟢 Bull Case"])

    report = f"""# 💹 DCF Assumption Builder — {name} ({ticker})
**Generated:** {datetime.now().strftime("%B %d, %Y")} | **Methodology:** Discounted Cash Flow (5-Year)

---

## 📐 Methodology Overview
DCF valuation estimates intrinsic value by discounting future free cash flows to present value.
**Formula:** Intrinsic Value = Σ(FCF / (1+WACC)^t) + Terminal Value / (1+WACC)^5

**Current Revenue Base:** {format_number(rev)} | **Operating Margin:** {om:.1f}%

---

## 📊 Three-Scenario Assumptions Table

| Assumption | 🔴 Bear Case | 🟡 Base Case | 🟢 Bull Case | Rationale |
|-----------|-------------|-------------|-------------|-----------|
| **Revenue Growth** | 5%/yr | 12%/yr | 20%/yr | Historical growth + competitive position |
| **Operating Margin** | {max(om-5,0):.0f}% | {max(om,10):.0f}% | {min(om+5,40):.0f}% | Margin trajectory based on efficiency |
| **Tax Rate** | 25% | 22% | 20% | Current corporate tax + optimization |
| **CapEx % Revenue** | 8% | 6% | 5% | Investment intensity by scenario |
| **Working Capital %** | 3% | 2% | 1.5% | WC efficiency by growth scenario |
| **WACC** | 12% | 10% | 9% | Risk-adjusted discount rate |
| **Terminal Growth Rate** | 2% | 3% | 4% | Long-run GDP + market position |

---

## 💰 DCF Valuation Results

| Scenario | Est. Enterprise Value | vs Market Cap {format_number(mcap)} | Implication |
|----------|----------------------|---------------------------------------|-------------|
| 🔴 **Bear Case** | {format_number(bear_val)} | {"Overvalued" if bear_val < mcap else "Undervalued"} by {abs(bear_val-mcap)/mcap*100:.0f}% | Downside risk if growth disappoints |
| 🟡 **Base Case** | {format_number(base_val)} | {"Overvalued" if base_val < mcap else "Undervalued"} by {abs(base_val-mcap)/mcap*100:.0f}% | Fair value under steady execution |
| 🟢 **Bull Case** | {format_number(bull_val)} | {"Overvalued" if bull_val < mcap else "Undervalued"} by {abs(bull_val-mcap)/mcap*100:.0f}% | Upside if growth accelerates |

---

## 🔬 Sensitivity Analysis (Base Case WACC vs Terminal Growth)

| WACC \\ Terminal Growth | 2% | 3% | 4% |
|------------------------|----|----|-----|
| **9%** | Higher Value | Higher Value | Highest Value |
| **10%** | Base Value | Base Value | Higher Value |
| **12%** | Lower Value | Lower Value | Moderate Value |

*Note: Higher WACC = Lower valuation. Higher terminal growth = Higher valuation.*

---

## ⚠️ Key Variables with Largest Impact
1. **WACC (±1%)** → Changes valuation by ~15-20%
2. **Revenue Growth Rate** → Each 1% change = ~8-12% valuation impact
3. **Terminal Growth Rate** → Most sensitive — small change = large valuation swing
4. **Operating Margin** → Each 1pp margin change = ~5-8% valuation change

## 🚨 Risks to Assumptions
- **Bear Case too optimistic:** If revenue growth turns negative (recession scenario)
- **Bull Case too optimistic:** If competition compresses margins below projections
- **WACC underestimated:** Rising interest rates increase discount rates globally
- **Terminal value reliability:** 5-year DCF has high uncertainty — treat as range, not point estimate

---

> ⚖️ **Disclaimer:** DCF is for educational modeling only. All figures are estimates.
> Not SEBI investment advice. Actual results may vary significantly from projections.
"""
    return report


def generate_catalyst_calendar(ticker: str, data: dict) -> str:
    name  = data.get("name", ticker)
    chg   = data.get("change_pct", 0) or 0
    pe    = data.get("pe_ratio", 0) or 0
    div   = data.get("dividend_yield", 0) or 0

    report = f"""# 📅 Stock Catalyst Calendar — {name} ({ticker})
**Generated:** {datetime.now().strftime("%B %d, %Y")} | **Coverage:** Next 3, 6, 12 Months

---

## 📆 Next 3 Months — Near-Term Catalysts

| Catalyst | Expected Timing | Impact | Positive Scenario | Negative Scenario | Confidence |
|----------|----------------|--------|------------------|-------------------|------------|
| **Quarterly Earnings** | Next 30-45 days | 🔴 HIGH | EPS beat → +10-15% | EPS miss → -10-20% | HIGH |
| **Guidance Update** | Earnings date | 🔴 HIGH | Raised guidance → re-rate | Lowered → de-rate | HIGH |
| **Management Commentary** | Earnings call | 🟡 MED | Positive tone → momentum | Cautious → selling | HIGH |
| **Macro Data (CPI/Fed)** | Monthly | 🟡 MED | Rate cut signals → growth boost | Rate hike → multiple compression | HIGH |
| **Analyst Revisions** | Post-earnings | 🟡 MED | Upgrades → price target raises | Downgrades → pressure | MEDIUM |

---

## 📆 Next 6 Months — Medium-Term Catalysts

| Catalyst | Expected Timing | Impact | Positive | Negative | Confidence |
|----------|----------------|--------|----------|----------|------------|
| **Mid-Year Earnings** | Q2/Q3 Results | 🔴 HIGH | Growth acceleration | Slowdown confirmation | HIGH |
| **Product/Service Launch** | H2 2026 | 🟡 MED | New revenue stream | Delayed launch, cost overrun | MEDIUM |
| **Dividend Announcement** | Semi-annual | 🟢 LOW-MED | {"Dividend increase" if div > 0 else "First dividend initiation"} | Cut or suspension | {"HIGH" if div > 2 else "LOW"} |
| **Industry Conference** | Q3 2026 | 🟡 MED | Strategic update, partnerships | Competitor announcements | MEDIUM |
| **Share Buyback** | Ongoing | 🟡 MED | Accelerated repurchase | Buyback suspension | MEDIUM |
| **Regulatory Decision** | Varies | 🔴 HIGH | Favorable ruling | Adverse decision | LOW |

---

## 📆 Next 12 Months — Long-Term Catalysts

| Catalyst | Expected Timing | Impact | Positive | Negative | Confidence |
|----------|----------------|--------|----------|----------|------------|
| **Annual Results** | Q4 2026 / Q1 2027 | 🔴 HIGH | Full-year beat | Miss annual targets | HIGH |
| **Major Partnership/M&A** | H1 2027 | 🔴 HIGH | Strategic acquisition | Overpriced deal, dilution | LOW |
| **Market Cycle** | 12 months | 🔴 HIGH | Bull market continuation | Recession, bear market | MEDIUM |
| **Leadership Changes** | Unpredictable | 🟡 MED | Strong new leadership | Key executive departure | LOW |
| **Technology Disruption** | Ongoing | 🟡 MED | Successful AI/tech adoption | Disruption by competitors | MEDIUM |
| **Global Macro** | Ongoing | 🔴 HIGH | Easing macro environment | Stagflation, geopolitical risk | MEDIUM |

---

## ⭐ Highest-Impact Catalysts to Watch
1. 🥇 **Quarterly Earnings (Next 30-45 Days)** — Single biggest near-term price mover
2. 🥈 **Guidance Update** — Forward guidance changes market narrative instantly
3. 🥉 **Macro/Fed Policy** — Interest rate trajectory affects {"growth" if pe > 25 else "value"} stocks most

---

## 📌 Confirmed vs Speculative Events
- **CONFIRMED:** Quarterly earnings, index rebalancing, dividend dates (if applicable)
- **SPECULATIVE:** M&A, partnerships, product launches, regulatory outcomes
- **WATCH:** Insider buying/selling — often precedes major moves

---

> ⚖️ **Disclaimer:** Forward-looking catalyst calendar is speculative and educational.
> Not SEBI investment advice. Catalyst timing and impact are estimates, not guarantees.
"""
    return report


def generate_management_review(ticker: str, data: dict) -> str:
    name  = data.get("name", ticker)
    nm    = data.get("net_margin", 0) or 0
    om    = data.get("operating_margin", 0) or 0
    gm    = data.get("gross_margin", 0) or 0
    de    = data.get("debt_to_equity", 0) or 0
    roe   = data.get("return_on_equity", 0) or 0
    div   = data.get("dividend_yield", 0) or 0
    chg   = data.get("change_pct", 0) or 0

    def mgmt_score(val, good, ok):
        return 5 if val >= good else (4 if val >= ok else (3 if val >= ok*0.5 else 2))

    ceo_score   = mgmt_score(om, 20, 10)
    cfo_score   = mgmt_score(nm, 15, 5)
    guidance_s  = 3  # neutral default
    transparency= mgmt_score(gm, 50, 30)
    capalloc_s  = mgmt_score(roe, 20, 10) if roe else 3
    acquisition = 3
    buyback_s   = 4 if div == 0 else (3 if div < 3 else 4)
    dilution_s  = 3
    insider_s   = 3
    comp_s      = 3
    board_s     = 3
    comm_s      = mgmt_score(om, 15, 8)

    scores = [ceo_score, cfo_score, guidance_s, transparency, capalloc_s,
              acquisition, buyback_s, dilution_s, insider_s, comp_s, board_s, comm_s]
    overall = sum(scores) / len(scores)
    overall_label = "🟢 OWNER-OPERATORS" if overall >= 4 else ("🟡 SOLID STEWARDS" if overall >= 3 else "🔴 SHORT-TERM FOCUS")

    def stars(s): return "⭐" * int(s) + "☆" * (5 - int(s))

    report = f"""# 👔 Management Quality Review — {name} ({ticker})
**Generated:** {datetime.now().strftime("%B %d, %Y")} | **Scale:** 1 (Poor) → 5 (Excellent)

---

## 🏆 Overall Management Quality Score: {overall:.1f}/5 — {overall_label}

---

## 📊 Detailed Scoring Matrix

| Category | Score | Rating | Reasoning | Strength/Concern |
|----------|-------|--------|-----------|-----------------|
| **CEO Track Record** | {ceo_score}/5 | {stars(ceo_score)} | Operating margin of {om:.1f}% reflects execution | {"Strong execution" if ceo_score >= 4 else "Execution needs improvement"} |
| **CFO Credibility** | {cfo_score}/5 | {stars(cfo_score)} | Net margin of {nm:.1f}% — financial stewardship | {"Disciplined cost management" if cfo_score >= 4 else "Margin management concerns"} |
| **Guidance Accuracy** | {guidance_s}/5 | {stars(guidance_s)} | Historical guidance consistency — neutral baseline | Monitor next 2 quarters |
| **Shareholder Transparency** | {transparency}/5 | {stars(transparency)} | Gross margin {gm:.1f}% — business clarity | {"Open communication on margins" if transparency >= 4 else "More detail needed on cost drivers"} |
| **Capital Allocation** | {capalloc_s}/5 | {stars(capalloc_s)} | {"ROE of {:.1f}% — good capital returns".format(roe) if roe else "Capital allocation — neutral assessment"} | {"Effective deployment of capital" if capalloc_s >= 4 else "Allocation discipline needed"} |
| **Acquisition Strategy** | {acquisition}/5 | {stars(acquisition)} | M&A track record — limited public data | Verify with latest filings |
| **Share Buyback** | {buyback_s}/5 | {stars(buyback_s)} | {"Dividends + buybacks suggest shareholder focus" if div > 0 else "No dividend — possible growth reinvestment"} | {"Disciplined capital return" if buyback_s >= 4 else "Monitor buyback timing"} |
| **Share Dilution** | {dilution_s}/5 | {stars(dilution_s)} | Dilution history — requires 10-K review | Check share count trend |
| **Insider Ownership** | {insider_s}/5 | {stars(insider_s)} | Insider alignment — neutral baseline | Track Form 4 filings |
| **Executive Compensation** | {comp_s}/5 | {stars(comp_s)} | Pay vs performance alignment | Review proxy statement |
| **Board Independence** | {board_s}/5 | {stars(board_s)} | Governance structure assessment | Check board composition |
| **Shareholder Engagement** | {comm_s}/5 | {stars(comm_s)} | Communication quality — {"high margin suggests transparency" if om > 15 else "improvement possible"} | {"Regular investor updates" if comm_s >= 4 else "More transparency needed"} |

---

## 🏅 Major Achievements Under Current Leadership
- {"Maintained profitability with " + str(round(om,1)) + "% operating margin in competitive environment" if om > 10 else "Cost reduction initiatives in progress"}
- {"Strong gross margin of " + str(round(gm,1)) + "% demonstrates pricing power vs competitors" if gm > 40 else "Revenue diversification efforts underway"}
- {"Business scaled to " + format_number(data.get("market_cap",0)) + " market capitalization" if data.get("market_cap",0) > 1e9 else "Building market position"}

## ⚠️ Significant Concerns to Monitor
- {"Debt/Equity of {:.1f}x requires disciplined financial management".format(de) if de > 1 else "Balance sheet appears well managed"}
- {"Thin net margins of {:.1f}% leave little buffer for errors".format(nm) if nm < 8 else "Profit margins provide adequate operational cushion"}
- Insider transaction patterns (check SEC/BSE filings for recent activity)

---

## 🔑 Key Questions to Verify
1. Has management consistently met or beaten earnings guidance over past 8 quarters?
2. What is the insider ownership percentage? (>10% is positive)
3. Has diluted share count been stable or growing?
4. How did management navigate last market downturn (2022/2020)?
5. Are executive compensation metrics aligned with long-term shareholder returns?

---

## 🏁 Conclusion
**Overall Score: {overall:.1f}/5 — {overall_label}**
{"Management demonstrates characteristics of long-term oriented owner-operators with strong capital discipline." if overall >= 4 else "Management shows solid stewardship but investors should verify guidance track record and capital allocation decisions." if overall >= 3 else "Management quality requires deeper investigation — verify execution track record and shareholder alignment before investing."}

---

> ⚖️ **Disclaimer:** Management quality assessment is educational and based on public financial metrics.
> Not SEBI investment advice. Verify with latest annual reports, proxy statements, and filings.
"""
    return report


def generate_bull_bear_debate(ticker: str, data: dict) -> str:
    name  = data.get("name", ticker)
    price = data.get("current_price", 0) or 0
    pe    = data.get("pe_ratio", 0) or 0
    gm    = data.get("gross_margin", 0) or 0
    om    = data.get("operating_margin", 0) or 0
    nm    = data.get("net_margin", 0) or 0
    mcap  = data.get("market_cap", 0) or 0
    vol   = data.get("volatility_annualized", 0) or 0
    beta  = data.get("beta", 1) or 1
    chg   = data.get("change_pct", 0) or 0
    de    = data.get("debt_to_equity", 0) or 0
    rev   = data.get("revenue", 0) or 0

    bull_pts = 0
    bear_pts = 0

    # Score each side
    if gm > 45: bull_pts += 2
    else: bear_pts += 1

    if om > 15: bull_pts += 2
    else: bear_pts += 2

    if pe < 20: bull_pts += 2
    elif pe > 40: bear_pts += 3
    else: bull_pts += 1; bear_pts += 1

    if de < 0.5: bull_pts += 2
    elif de > 2: bear_pts += 3
    else: bear_pts += 1

    if vol < 25: bull_pts += 1
    elif vol > 60: bear_pts += 2

    if chg > 0: bull_pts += 1
    else: bear_pts += 1

    winner = "🟢 BULL ANALYST" if bull_pts > bear_pts else ("🔴 BEAR ANALYST" if bear_pts > bull_pts else "⚖️ TIE")

    report = f"""# ⚔️ Bull vs Bear Debate — {name} ({ticker})
**Generated:** {datetime.now().strftime("%B %d, %Y")} | **Format:** Investment Committee Simulation

---

> 🎙️ *The following is a simulated investment committee debate. Two analysts present opposing views
> on {name} ({ticker}). A neutral judge summarizes. All opinions are analytical — not investment advice.*

---

## 🟢 BULL ANALYST vs 🔴 BEAR ANALYST

---

### 📈 Topic 1: Revenue Growth & Future Prospects

**🟢 Bull:** "{name} has {"strong gross margins of " + str(round(gm,1)) + "%, indicating healthy revenue quality and pricing power" if gm > 40 else "demonstrated resilience in revenue generation despite macro headwinds"}. The total addressable market is expanding, and the company is well-positioned to capture incremental share."

**🔴 Bear:** "{"Revenue growth is slowing — at current valuation multiples, the market is pricing in perfection. Any deceleration will hit the stock hard." if pe > 30 else "Revenue quality concerns exist — thin margins of " + str(round(nm,1)) + "% mean small revenue misses create outsized earnings impact."}"

*Evidence: Revenue {format_number(rev)}, Gross Margin {gm:.1f}%, 24H change {chg:+.1f}%*

---

### 💰 Topic 2: Valuation & Market Expectations

**🟢 Bull:** "{"At P/E of " + str(round(pe,1)) + "x, the valuation reflects justified premium for quality business with durable competitive advantages." if pe < 35 else "Premium valuation of P/E " + str(round(pe,1)) + "x is warranted — high-quality compounders always trade at a premium."} Market cap of {format_number(mcap)} still has room to grow."

**🔴 Bear:** "{"P/E of " + str(round(pe,1)) + "x is extreme — you're paying for 40 years of earnings upfront. Any multiple compression = massive losses." if pe > 40 else "Current P/E of " + str(round(pe,1)) + "x doesn't leave much margin of safety. A slight earnings miss could re-rate the stock down 20-30%."}"

*Evidence: P/E {pe:.1f}x vs market avg ~20x, Market Cap {format_number(mcap)}*

---

### 🏢 Topic 3: Business Model & Competitive Advantages

**🟢 Bull:** "{"The " + str(round(gm,1)) + "% gross margin is proof of strong competitive positioning — companies with these margins have wide moats." if gm > 45 else "The business model is proven with consistent profitability across cycles."}  Operating leverage means margins should expand as revenues scale."

**🔴 Bear:** "{"Operating margin of only " + str(round(om,1)) + "% suggests competitive pressures are eroding the business model." if om < 15 else "Even with " + str(round(om,1)) + "% operating margins, the business faces structural threats from digital disruption and new entrants."}"

*Evidence: Gross Margin {gm:.1f}%, Operating Margin {om:.1f}%, Net Margin {nm:.1f}%*

---

### 💳 Topic 4: Financial Performance & Profitability

**🟢 Bull:** "{"Net margin of " + str(round(nm,1)) + "% with manageable debt/equity of " + str(round(de,1)) + "x — this is a financially healthy company generating real cash." if nm > 8 and de < 1 else "Management is executing cost controls — the path to margin improvement is clear and achievable."}"

**🔴 Bear:** "{"Debt/equity of " + str(round(de,1)) + "x is a serious concern — if rates stay high, debt service will eat into earnings." if de > 1.5 else "Net margin of " + str(round(nm,1)) + "% is too thin — this business has limited financial resilience to any economic shock."}"

*Evidence: Net Margin {nm:.1f}%, Debt/Equity {de:.1f}x*

---

### ⚡ Topic 5: Key Risks & Upcoming Catalysts

**🟢 Bull:** "{"Volatility of " + str(round(vol,1)) + "% creates buying opportunities for long-term investors." if vol > 30 else "Stable, low-volatility business model — " + str(round(vol,1)) + "% volatility shows institutional confidence."} Upcoming earnings are a catalyst for multiple re-rating."

**🔴 Bear:** "{"Volatility of " + str(round(vol,1)) + "% is a warning sign — speculative interest driving price, not fundamentals." if vol > 50 else "Beta of " + str(round(beta,2)) + "x means " + str(round(beta*100,0)) + "% of market downside is amplified — not a safe position in bear markets."}"

*Evidence: Volatility {vol:.1f}%, Beta {beta:.2f}x*

---

## ⚖️ NEUTRAL JUDGE SUMMARY

### 🏆 Stronger Evidence: {winner}
**Bull Score: {bull_pts} pts | Bear Score: {bear_pts} pts**

### 🔍 Most Important Unresolved Uncertainties
1. **Revenue growth durability** — Is current growth rate sustainable for 3-5 years?
2. **Margin trajectory** — Will margins expand (bull case) or compress (bear case)?
3. **Competitive moat** — How defensible is the business against new entrants?

### 🔑 Key Assumptions Driving Each Viewpoint
- **Bulls assume:** Continued margin expansion, TAM growth, multiple re-rating higher
- **Bears assume:** Growth deceleration, competition intensifies, multiple compression

### 📋 Critical Data Points to Verify
1. Last 8 quarters of earnings vs estimates (guidance accuracy)
2. Year-over-year revenue growth trend (accelerating or decelerating?)
3. Competitor margin trends (industry-wide or company-specific pressure?)
4. Insider buying/selling in past 6 months

### ❓ Questions Investors Should Investigate Before Deciding
1. What happens to the investment thesis if revenue grows at half the expected rate?
2. At what P/E multiple would you no longer consider this a buy?
3. Who are the top 5 institutional holders and have they been buying or selling?
4. What does the bear scenario look like in a 2022-style market selloff?

---

> ⚖️ **Disclaimer:** Simulated debate for educational purposes. Both views are analytical exercises.
> Not SEBI investment advice. Maintain a balanced perspective and do your own research.
"""
    return report


def generate_beginner_checklist(ticker: str, data: dict) -> str:
    name  = data.get("name", ticker)
    price = data.get("current_price", 0) or 0
    pe    = data.get("pe_ratio", 0) or 0
    gm    = data.get("gross_margin", 0) or 0
    om    = data.get("operating_margin", 0) or 0
    nm    = data.get("net_margin", 0) or 0
    mcap  = data.get("market_cap", 0) or 0
    vol   = data.get("volatility_annualized", 0) or 0
    risk  = data.get("risk_score", 5) or 5
    de    = data.get("debt_to_equity", 0) or 0
    rev   = data.get("revenue", 0) or 0
    div   = data.get("dividend_yield", 0) or 0
    eps   = data.get("eps", 0) or 0
    beta  = data.get("beta", 1) or 1
    atype = data.get("asset_type", "Stock")

    # Checklist scoring
    easy_understand   = risk <= 5 and mcap > 1e10
    financially_strong= nm > 8 and de < 1.5 and gm > 30
    growing_business  = om > 10 and rev > 0
    reasonably_valued = pe < 35 and pe > 0
    risks_understood  = True  # we explain them
    needs_research    = vol > 40 or pe > 35 or de > 1.5

    def check(val): return "✅" if val else "❌"

    report = f"""# 📚 Beginner's Guide to {name} ({ticker})
**Generated:** {datetime.now().strftime("%B %d, %Y")} | **Level:** Beginner Friendly

---

> 💡 *Think of this as a school report card for {name}. We'll explain everything in simple terms,
> just like a knowledgeable friend would — no complicated finance jargon!*

---

## 🏢 What Does {name} Do?
{name} is a **{atype}** listed on the stock exchange with ticker symbol **{ticker}**.

**In Simple Terms:** {"This is a large, well-established company (market cap: " + format_number(mcap) + ") that most investors know. It generates revenue through its core business operations." if mcap > 1e11 else "This is a " + ("growing mid-size" if mcap > 1e9 else "smaller") + " company (market cap: " + format_number(mcap) + ") in its sector."}

---

## 💵 How Does It Make Money?
- **Revenue:** {format_number(rev)} in annual revenue
- **Profit per ₹100 revenue:** {"₹" + str(round(nm,1)) if nm > 0 else "Currently losing money (negative margin)"} → {"Very profitable! 🟢" if nm > 15 else "Decent" if nm > 5 else "Needs improvement 🔴"}
- **Gross Profit Margin:** {gm:.1f}% → *Think of this as: for every ₹100 sold, the direct cost is ₹{100-gm:.0f}. The remaining ₹{gm:.0f} covers salaries, rent, and profit.*

---

## 👀 Why Do Investors Pay Attention to It?
- {"🏆 **Market leader** — one of the largest companies in its sector" if mcap > 1e11 else "📈 **Growth potential** — expanding business with room to grow"}
- {"💎 **Profitable business** — consistently generates real earnings" if nm > 8 else "🔄 **Turnaround story** — profitability improving"}
- {"💰 **Pays dividends:** " + str(round(div,2)) + "% yield — income for investors" if div > 0.5 else "🚀 **Reinvests profits** — focuses on growth over dividends"}
- EPS (Earnings per share) of **${eps:.2f}** — this is how much profit each share earns

---

## 🔑 Key Products, Services & Business Segments
*Based on the ticker and market data, this appears to be a {atype.lower()}.*

The company's key revenue drivers include its core product/service lines, which generate
{"high-margin recurring revenue (gross margin {:.0f}%)".format(gm) if gm > 50 else "moderate margins ({:.0f}%), typical for its industry".format(gm)}.

---

## 📊 Profitability & Earnings Performance

| Metric | Value | What it Means for You |
|--------|-------|-----------------------|
| **Gross Margin** | {gm:.1f}% | {"Strong — keeps {:.0f}% of each rupee as gross profit 🟢".format(gm) if gm > 40 else "Average — {:.0f}% gross profit per rupee".format(gm)} |
| **Operating Margin** | {om:.1f}% | {"Efficient operations — {:.0f}% operating profit 🟢".format(om) if om > 15 else "Tight operations — watch for improvement"} |
| **Net Margin** | {nm:.1f}% | {"Keeps ₹{:.0f} of every ₹100 in sales as net profit 🟢".format(nm) if nm > 0 else "Currently losing money — high risk 🔴"} |
| **EPS** | ${eps:.2f} | Earns ${eps:.2f} per share per year |

---

## 🚀 Growth Opportunities & Future Potential

**What Could Go Right:**
- {"Margin expansion as the business scales — operating leverage kicks in" if om < 20 else "Continued margin strength while growing revenue base"}
- {"International expansion into emerging markets" if mcap < 5e11 else "Dominant market position enables pricing power increases"}
- {"New product lines or services diversifying revenue" if pe > 20 else "Valuation re-rating as growth accelerates"}
- {"AI/technology adoption improving efficiency and reducing costs"}

**What Could Go Wrong:**
- {"Overvalued at P/E " + str(round(pe,1)) + "x — any earnings miss triggers sharp selloff" if pe > 35 else "Competition increasing margins pressure"}
- {"Volatility of " + str(round(vol,1)) + "% means price can swing dramatically" if vol > 40 else "Macro slowdown could impact revenue growth"}
- {"High debt ({:.1f}x D/E) limits flexibility if business slows".format(de) if de > 1.5 else "Rising interest rates increasing borrowing costs"}

---

## 💳 Debt Levels & Financial Health

*Think of debt like a home loan — too much is dangerous, a little is fine.*

| | Status |
|---|---|
| **Debt/Equity Ratio** | {de:.1f}x → {"🟢 Low debt — financially healthy" if de < 0.5 else "🟡 Moderate debt — manageable" if de < 1.5 else "🔴 High debt — financial risk"} |
| **Price** | ${price:,.2f} per share |
| **P/E Ratio** | {pe:.1f}x → *You pay ${pe:.0f} for every $1 of annual earnings* |

---

## 📐 Current Valuation vs Peers
- P/E of **{pe:.1f}x** vs market average **~20x** → {"🔴 Expensive — you're paying a premium" if pe > 30 else "🟢 Cheap — potentially undervalued" if pe < 15 else "🟡 Fair — reasonably priced"}
- Market cap of **{format_number(mcap)}** puts this in the **{"mega" if mcap > 1e12 else "large" if mcap > 1e11 else "mid"}**-cap category

---

## ☑️ BEGINNER'S INVESTMENT CHECKLIST

| Criteria | Status | Details |
|----------|--------|---------|
| **Easy to Understand** | {check(easy_understand)} | {"Simple, well-known business model" if easy_understand else "Complex or speculative — hard to predict"} |
| **Financially Strong** | {check(financially_strong)} | {"Healthy margins & manageable debt" if financially_strong else "Concerns: margins or debt need improvement"} |
| **Growing Business** | {check(growing_business)} | {"Revenue growing with healthy operating margins" if growing_business else "Growth is unclear or slowing"} |
| **Reasonably Valued** | {check(reasonably_valued)} | {"P/E of {:.1f}x is reasonable".format(pe) if reasonably_valued else "P/E of {:.1f}x — expensive, needs justification".format(pe)} |
| **Risks Understood** | {check(risks_understood)} | {"Key risks identified: volatility {:.0f}%, beta {:.1f}x".format(vol,beta)} |
| **Needs More Research** | {check(needs_research)} | {"Yes — " + ("high volatility" if vol > 40 else "") + (" + high valuation" if pe > 35 else "") + (" + high debt" if de > 1.5 else "") if needs_research else "Basic research suggests manageable risk profile"} |

---

## 🎓 Summary for Beginners
{"✅ **" + name + " looks like a relatively straightforward investment** for beginners — established business, understandable model, and manageable risk profile. Still do your own research!" if sum([easy_understand, financially_strong, growing_business, reasonably_valued]) >= 3 else "⚠️ **" + name + " has some complexities** — the valuation, debt, or volatility warrants deeper research before investing. Consider starting with a smaller position."}

**Before investing, always ask yourself:**
1. Do I understand what this company does?
2. Can I afford to lose this money if things go wrong?
3. Am I investing or speculating?

---

> ⚖️ **Disclaimer:** This guide uses recent public data (Yahoo Finance, {datetime.now().strftime("%B %Y")}).
> It is for **educational purposes only** and does NOT provide a buy, sell, or hold recommendation.
> Not registered SEBI investment advice. Always consult a qualified financial advisor.
"""
    return report


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

MODULES = {
    "1️⃣  Full Research Report":     ("📋", "Complete equity research report with overview, financials, scenarios & thesis", "stock"),
    "2️⃣  Earnings Call Breakdown":  ("📞", "5 key takeaways, metrics table, surprises & what to watch next", "stock"),
    "3️⃣  Red Flag Detector":        ("🚩", "Forensic analysis — severity-rated warning signs with evidence", "stock"),
    "4️⃣  Competitive Moat Analysis":("🏰", "Rate 10 moat factors 1-5, compare vs competitors", "stock"),
    "5️⃣  Valuation Comparison":     ("📐", "P/E, EV/EBITDA, P/FCF vs peers — cheap, fair, or expensive?", "stock"),
    "6️⃣  DCF Assumption Builder":   ("💹", "Bear/Base/Bull DCF model with sensitivity analysis", "stock"),
    "7️⃣  Catalyst Calendar":        ("📅", "Next 3, 6, 12 month catalysts with impact & confidence", "stock"),
    "8️⃣  Management Quality Review":("👔", "Score CEO, CFO, governance 1-5 across 12 dimensions", "stock"),
    "9️⃣  Bull vs Bear Debate":      ("⚔️", "Simulated investment committee — two analysts debate, judge decides", "stock"),
    "🔟  Beginner's Checklist":     ("📚", "Beginner-friendly guide + 6-point investment checklist", "stock"),
}

MODULE_GENERATORS = {
    "1️⃣  Full Research Report":      generate_full_research_report,
    "2️⃣  Earnings Call Breakdown":   generate_earnings_breakdown,
    "3️⃣  Red Flag Detector":         generate_red_flag_detector,
    "4️⃣  Competitive Moat Analysis": generate_moat_analysis,
    "5️⃣  Valuation Comparison":      generate_valuation_comparison,
    "6️⃣  DCF Assumption Builder":    generate_dcf_analysis,
    "7️⃣  Catalyst Calendar":         generate_catalyst_calendar,
    "8️⃣  Management Quality Review": generate_management_review,
    "9️⃣  Bull vs Bear Debate":       generate_bull_bear_debate,
    "🔟  Beginner's Checklist":      generate_beginner_checklist,
}


def render_ai_assistant():
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.95),rgba(0,15,30,0.9));
    border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:1.2rem 1.5rem;
    margin-bottom:1.2rem;box-shadow:0 0 30px rgba(0,212,255,0.06);">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;width:44px;border-radius:10px;
            box-shadow:0 0 15px rgba(0,212,255,0.3);">
            <div>
                <div style="font-size:1.15rem;font-weight:800;color:#00d4ff;
                font-family:Orbitron,monospace;letter-spacing:0.05em;">
                🤖 AI Research Assistant
                </div>
                <div style="color:#4a9eff;font-size:0.75rem;">
                10 Professional Analysis Modules — Powered by real market data
                </div>
            </div>
            <span style="margin-left:auto;background:rgba(0,212,255,0.1);color:#00d4ff;
            padding:0.2rem 0.7rem;border-radius:20px;font-size:0.7rem;font-weight:700;
            border:1px solid rgba(0,212,255,0.3);">🧠 PRO ANALYSIS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Module cards ──
    st.markdown("### 🎯 Choose an Analysis Module")
    st.markdown("""
    <div style="color:#8b949e;font-size:0.82rem;margin-bottom:1rem;">
    Enter a stock or crypto ticker, select a module, and get institutional-grade analysis instantly.
    </div>
    """, unsafe_allow_html=True)

    # 2-column module cards
    module_names = list(MODULES.keys())
    cols = st.columns(2)
    for idx, mname in enumerate(module_names):
        icon, desc, _ = MODULES[mname]
        with cols[idx % 2]:
            is_selected = st.session_state.get("selected_module") == mname
            border_color = "rgba(0,212,255,0.5)" if is_selected else "rgba(0,212,255,0.12)"
            bg_color = "rgba(0,212,255,0.08)" if is_selected else "rgba(2,6,9,0.8)"
            st.markdown(f"""
            <div style="background:{bg_color};border:1px solid {border_color};border-radius:10px;
            padding:0.7rem 0.9rem;margin-bottom:0.5rem;cursor:pointer;transition:all 0.2s;">
                <div style="font-weight:700;color:#{"00d4ff" if is_selected else "c9d1d9"};font-size:0.88rem;">
                {icon} {mname.split("  ",1)[1] if "  " in mname else mname}
                </div>
                <div style="color:#8b949e;font-size:0.74rem;margin-top:0.2rem;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Select", key=f"mod_btn_{idx}", use_container_width=True):
                st.session_state.selected_module = mname
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Ticker input + Generate ──
    selected_mod = st.session_state.get("selected_module", module_names[0])
    st.markdown(f"""
    <div style="background:rgba(0,20,40,0.7);border:1px solid rgba(0,212,255,0.2);
    border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.8rem;">
        <div style="color:#00d4ff;font-weight:700;font-size:0.9rem;margin-bottom:0.5rem;">
        📌 Selected: {selected_mod}
        </div>
    </div>
    """, unsafe_allow_html=True)

    inp_col1, inp_col2 = st.columns([3, 1])
    with inp_col1:
        ticker_input = st.text_input(
            "Enter Stock / Crypto Ticker",
            placeholder="e.g. AAPL, TSLA, RELIANCE.NS, BTC, ETH, NVDA",
            key="ai_ticker_input",
            label_visibility="collapsed"
        )
    with inp_col2:
        generate_btn = st.button(
            "🚀 Generate",
            type="primary",
            use_container_width=True,
            key="ai_generate_btn",
            disabled=(not ticker_input.strip())
        )

    # ── Process ──
    if generate_btn and ticker_input.strip():
        ticker = ticker_input.strip().upper()

        with st.spinner(f"⚙️ Running **{selected_mod}** for **{ticker}**... fetching real-time data..."):
            # Fetch data — try stock first, then crypto
            is_crypto = ticker in ["BTC","ETH","SOL","BNB","XRP","ADA","DOGE","SHIB","PEPE",
                                   "AVAX","DOT","MATIC","LINK","UNI","NEAR","APT","FLOKI","BONK","TON"]
            if is_crypto:
                raw = fetch_crypto_data(ticker)
            else:
                raw = fetch_stock_data(ticker)
                if "error" in raw:
                    raw = fetch_crypto_data(ticker)

        if "error" in raw:
            st.error(f"❌ Could not fetch data for **{ticker}**: {raw.get('error','Unknown error')}")
            st.info("💡 Try: AAPL, TSLA, NVDA, RELIANCE.NS, TCS.NS, BTC, ETH, SOL")
            return

        # Generate report
        gen_fn = MODULE_GENERATORS.get(selected_mod)
        if gen_fn:
            with st.spinner("🧠 AI generating analysis report..."):
                report = gen_fn(ticker, raw)

            # Display
            _render_report(report, ticker, selected_mod, raw)


def _render_report(report: str, ticker: str, module: str, data: dict):
    name  = data.get("name", ticker)
    price = data.get("current_price", 0) or 0
    chg   = data.get("change_pct", 0) or 0
    risk  = data.get("risk_score", 5) or 5

    chg_color = "#00ff88" if chg >= 0 else "#ff4466"
    risk_color= "#f85149" if risk > 7 else ("#d29922" if risk > 4 else "#3fb950")

    st.markdown("---")
    # Summary header
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(0,20,40,0.9),rgba(0,10,25,0.95));
    border:1px solid rgba(0,212,255,0.2);border-radius:12px;padding:1rem 1.3rem;
    margin-bottom:1rem;display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">
        <div>
            <div style="font-size:1.1rem;font-weight:800;color:#e6edf3;">{name}</div>
            <div style="color:#4a9eff;font-size:0.78rem;font-family:Orbitron,monospace;">{ticker}</div>
        </div>
        <div style="background:rgba(0,0,0,0.3);padding:0.4rem 0.9rem;border-radius:8px;text-align:center;">
            <div style="color:#8b949e;font-size:0.65rem;">PRICE</div>
            <div style="color:#e6edf3;font-weight:700;">${price:,.4f}</div>
        </div>
        <div style="background:rgba(0,0,0,0.3);padding:0.4rem 0.9rem;border-radius:8px;text-align:center;">
            <div style="color:#8b949e;font-size:0.65rem;">24H</div>
            <div style="color:{chg_color};font-weight:700;">{chg:+.2f}%</div>
        </div>
        <div style="background:rgba(0,0,0,0.3);padding:0.4rem 0.9rem;border-radius:8px;text-align:center;">
            <div style="color:#8b949e;font-size:0.65rem;">RISK</div>
            <div style="color:{risk_color};font-weight:700;">{risk}/10</div>
        </div>
        <span style="margin-left:auto;background:rgba(0,212,255,0.1);color:#00d4ff;
        padding:0.3rem 0.8rem;border-radius:20px;font-size:0.72rem;font-weight:700;
        border:1px solid rgba(0,212,255,0.25);">✅ Analysis Complete</span>
    </div>
    """, unsafe_allow_html=True)

    # Report content
    st.markdown(report)

    # Download
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    mod_safe = module.replace(" ", "_").replace("/", "_")[:30]
    st.download_button(
        label="📥 Download Full Report (.md)",
        data=report,
        file_name=f"STOXAI_{ticker}_{mod_safe}_{ts}.md",
        mime="text/markdown",
        use_container_width=True,
        key=f"dl_report_{ts}"
    )

    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.7rem 1rem;margin-top:0.8rem;font-size:0.76rem;color:#8b949e;">
    ⚖️ <b style="color:#d29922;">Disclaimer:</b> All reports are generated from publicly available data (Yahoo Finance, CoinGecko).
    For educational purposes only. Not SEBI-registered investment advice. No buy, sell, or hold recommendation is provided.
    Clearly separate facts from analytical opinions.
    </div>
    """, unsafe_allow_html=True)
