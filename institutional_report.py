"""
FinSage AI — Institutional Research Report
BNP Paribas / Goldman Sachs style full fundamental + technical analysis.
Renders as a colorful multi-section research paper inside the platform.
"""
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import json, os, requests
from datetime import datetime, timedelta

try:
    from ticker_resolver import resolve_ticker
except ImportError:
    def resolve_ticker(x): return x

# ── API ───────────────────────────────────────────────────────────────────────
def _get_key(name):
    try: return st.secrets.get(name) or os.environ.get(name,"")
    except: return os.environ.get(name,"")

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
DEEPSEEK_URL   = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ── Fundamental Data Fetch ────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_fundamental(sym: str) -> dict:
    try:
        t = yf.Ticker(sym)
        info = t.info

        # Income / Balance / Cash flow
        try:
            fin = t.financials
            rev_growth = None
            if fin is not None and not fin.empty and len(fin.columns) >= 2:
                r1 = fin.loc["Total Revenue", fin.columns[0]] if "Total Revenue" in fin.index else None
                r2 = fin.loc["Total Revenue", fin.columns[1]] if "Total Revenue" in fin.index else None
                if r1 and r2 and r2 != 0:
                    rev_growth = round((r1 - r2) / abs(r2) * 100, 2)
        except:
            rev_growth = None

        # 52-week range %
        h52 = info.get("fiftyTwoWeekHigh", 0)
        l52 = info.get("fiftyTwoWeekLow", 0)
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        pos_in_range = round((price - l52) / (h52 - l52) * 100, 1) if h52 > l52 else 50

        # Analyst consensus
        try:
            rec = t.recommendations
            if rec is not None and not rec.empty:
                latest = rec.tail(5)
                strong_buy = int(latest.get("strongBuy", pd.Series([0])).iloc[-1]) if "strongBuy" in latest else 0
                buy_c      = int(latest.get("buy", pd.Series([0])).iloc[-1]) if "buy" in latest else 0
                hold_c     = int(latest.get("hold", pd.Series([0])).iloc[-1]) if "hold" in latest else 0
                sell_c     = int(latest.get("sell", pd.Series([0])).iloc[-1]) if "sell" in latest else 0
                analyst_summary = {"strongBuy": strong_buy, "buy": buy_c, "hold": hold_c, "sell": sell_c}
            else:
                analyst_summary = {}
        except:
            analyst_summary = {}

        # Price targets
        target_mean  = info.get("targetMeanPrice", 0)
        target_high  = info.get("targetHighPrice", 0)
        target_low   = info.get("targetLowPrice", 0)
        upside = round((target_mean - price) / price * 100, 1) if price and target_mean else None

        mktcap = info.get("marketCap", 0)
        mktcap_str = f"₹{mktcap/1e12:.2f}T" if mktcap > 1e12 else f"₹{mktcap/1e9:.1f}B" if mktcap > 1e9 else f"${mktcap/1e9:.1f}B"

        return {
            "sym": sym,
            "name": info.get("longName") or info.get("shortName", sym),
            "sector": info.get("sector", "—"),
            "industry": info.get("industry", "—"),
            "country": info.get("country", "—"),
            "exchange": info.get("exchange", "—"),
            "currency": info.get("currency", "INR"),
            "description": info.get("longBusinessSummary", "")[:600],
            "price": price,
            "mktcap": mktcap,
            "mktcap_str": mktcap_str,
            "pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb": info.get("priceToBook"),
            "ps": info.get("priceToSalesTrailing12Months"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "eps": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "revenue": info.get("totalRevenue", 0),
            "gross_margin": info.get("grossMargins"),
            "profit_margin": info.get("profitMargins"),
            "ebitda_margin": info.get("ebitdaMargins"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "debt_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "div_yield": info.get("dividendYield"),
            "payout_ratio": info.get("payoutRatio"),
            "beta": info.get("beta"),
            "h52": h52, "l52": l52,
            "pos_in_range": pos_in_range,
            "avg_vol": info.get("averageVolume", 0),
            "float_shares": info.get("floatShares", 0),
            "analyst_key": info.get("recommendationKey", "—"),
            "analyst_summary": analyst_summary,
            "target_mean": target_mean,
            "target_high": target_high,
            "target_low": target_low,
            "upside": upside,
            "rev_growth": rev_growth,
            "employees": info.get("fullTimeEmployees", 0),
            "website": info.get("website", ""),
        }
    except Exception as e:
        return {"sym": sym, "name": sym, "_error": str(e)}

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_technical(sym: str) -> dict:
    try:
        df = yf.Ticker(sym).history(period="6mo", interval="1d")
        if df.empty: return {}
        c = df["Close"].values.astype(float)
        h = df["High"].values.astype(float)
        l = df["Low"].values.astype(float)
        v = df["Volume"].values.astype(float)
        o = df["Open"].values.astype(float)

        def ema(arr, n): return pd.Series(arr).ewm(span=n, adjust=False).mean().values

        # RSI
        d = np.diff(c, prepend=c[0])
        up = np.where(d>0, d, 0); dn = np.where(d<0, -d, 0)
        au = ema(up, 14); ad = ema(dn, 14)
        rsi = float((100 - 100/(1 + np.where(ad==0, 100, au/np.where(ad==0, 1e-9, ad))))[-1])

        ema20 = float(ema(c, 20)[-1])
        ema50 = float(ema(c, 50)[-1]) if len(c) >= 50 else float(c.mean())
        ema200= float(ema(c, 200)[-1]) if len(c) >= 200 else float(c.mean())

        macd_line = ema(c,12) - ema(c,26)
        sig = ema(macd_line, 9)
        macd_hist = float(macd_line[-1] - sig[-1])

        sma20 = float(np.mean(c[-20:])); std20 = float(np.std(c[-20:]))
        bb_upper = sma20 + 2*std20; bb_lower = sma20 - 2*std20

        tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
        atr = float(tr[-14:].mean()) if len(tr) >= 14 else 0

        tp = (h+l+c)/3; n20 = min(20, len(tp))
        vwap = float(np.sum(tp[-n20:]*v[-n20:]) / np.sum(v[-n20:])) if np.sum(v[-n20:]) > 0 else float(c[-1])

        vol_ratio = float(v[-1] / v[-20:].mean()) if v[-20:].mean() > 0 else 1.0

        # Pivots
        window = 5; ps = []; pr = []
        for i in range(window, len(c)-window):
            if all(l[i]<=l[i-j] for j in range(1,window+1)) and all(l[i]<=l[i+j] for j in range(1,window+1)):
                ps.append(float(l[i]))
            if all(h[i]>=h[i-j] for j in range(1,window+1)) and all(h[i]>=h[i+j] for j in range(1,window+1)):
                pr.append(float(h[i]))

        cur = c[-1]
        supports    = sorted([x for x in ps if x < cur], reverse=True)[:3]
        resistances = sorted([x for x in pr if x > cur])[:3]

        # Trend
        if cur > ema20 > ema50: trend = "BULLISH"
        elif cur < ema20 < ema50: trend = "BEARISH"
        else: trend = "SIDEWAYS"

        # Momentum score (-100 to +100)
        score = 0
        if cur > ema20: score += 15
        if cur > ema50: score += 20
        if cur > ema200: score += 25
        if rsi > 50: score += 15
        if rsi < 30: score -= 20
        if rsi > 70: score -= 10
        if macd_hist > 0: score += 15
        if vol_ratio > 1.5: score += 10
        momentum_score = max(-100, min(100, score))

        # Perf vs 52W
        h52 = float(h[-252:].max()) if len(h)>=252 else float(h.max())
        l52 = float(l[-252:].min()) if len(l)>=252 else float(l.min())
        perf_1m = round((cur - c[-21])/c[-21]*100, 2) if len(c)>=21 else 0
        perf_3m = round((cur - c[-63])/c[-63]*100, 2) if len(c)>=63 else 0
        perf_6m = round((cur - c[0])/c[0]*100, 2)
        perf_ytd = perf_6m  # approximate

        # Stoch RSI
        rsi_series = []
        for i in range(14, len(c)):
            d2 = np.diff(c[max(0,i-14):i+1], prepend=c[max(0,i-14)])
            u2 = np.where(d2>0,d2,0); d3 = np.where(d2<0,-d2,0)
            au2 = u2.mean(); ad2 = d3.mean()
            rsi_series.append(100 - 100/(1+(au2/ad2 if ad2>0 else 100)))
        if len(rsi_series) >= 14:
            rm = min(rsi_series[-14:]); rx = max(rsi_series[-14:])
            stoch_rsi = float((rsi_series[-1]-rm)/(rx-rm)*100) if rx!=rm else 50.0
        else:
            stoch_rsi = 50.0

        return {
            "price": cur, "ema20": ema20, "ema50": ema50, "ema200": ema200,
            "rsi": rsi, "stoch_rsi": stoch_rsi, "macd_hist": macd_hist,
            "bb_upper": bb_upper, "bb_lower": bb_lower, "sma20": sma20,
            "atr": atr, "vwap": vwap, "vol_ratio": vol_ratio,
            "supports": supports, "resistances": resistances, "trend": trend,
            "momentum_score": momentum_score,
            "perf_1m": perf_1m, "perf_3m": perf_3m, "perf_6m": perf_6m,
            "h52": h52, "l52": l52,
        }
    except Exception as e:
        return {}

# ── AI Comprehensive Analysis ─────────────────────────────────────────────────
def _ai_research_report(sym: str, fund: dict, tech: dict) -> dict:
    ds_key  = _get_key("DEEPSEEK_API_KEY")
    groq_key= _get_key("GROQ_API_KEY")

    name = fund.get("name", sym)
    price= fund.get("price", tech.get("price", 0))

    prompt = f"""You are a senior analyst at a top-tier institution (like BNP Paribas / Goldman Sachs).
Write a complete institutional research report for {name} ({sym}).

FUNDAMENTAL DATA:
Sector: {fund.get('sector')} | Industry: {fund.get('industry')} | Country: {fund.get('country')}
Market Cap: {fund.get('mktcap_str')} | Price: {price}
P/E: {fund.get('pe')} | Forward P/E: {fund.get('forward_pe')} | P/B: {fund.get('pb')} | P/S: {fund.get('ps')}
EV/EBITDA: {fund.get('ev_ebitda')} | EPS: {fund.get('eps')} | Fwd EPS: {fund.get('eps_forward')}
Revenue: {fund.get('revenue',0)/1e9:.1f}B | Gross Margin: {(fund.get('gross_margin') or 0)*100:.1f}%
Profit Margin: {(fund.get('profit_margin') or 0)*100:.1f}% | ROE: {(fund.get('roe') or 0)*100:.1f}%
Debt/Equity: {fund.get('debt_equity')} | Current Ratio: {fund.get('current_ratio')} | Beta: {fund.get('beta')}
Dividend Yield: {(fund.get('div_yield') or 0)*100:.2f}% | Analyst: {fund.get('analyst_key')}
Price Target Mean: {fund.get('target_mean')} | Upside: {fund.get('upside')}%
52W High: {fund.get('h52')} | 52W Low: {fund.get('l52')} | Position in Range: {fund.get('pos_in_range')}%
Business: {fund.get('description','')[:300]}

TECHNICAL DATA:
RSI: {tech.get('rsi',50):.1f} | Stoch RSI: {tech.get('stoch_rsi',50):.1f} | Trend: {tech.get('trend')}
EMA20: {tech.get('ema20',0):.2f} | EMA50: {tech.get('ema50',0):.2f} | EMA200: {tech.get('ema200',0):.2f}
MACD Hist: {tech.get('macd_hist',0):.4f} | BB Upper: {tech.get('bb_upper',0):.2f} | BB Lower: {tech.get('bb_lower',0):.2f}
Vol Ratio: {tech.get('vol_ratio',1):.2f}x | ATR: {tech.get('atr',0):.4f} | Momentum Score: {tech.get('momentum_score',0)}/100
Perf 1M: {tech.get('perf_1m',0):+.1f}% | 3M: {tech.get('perf_3m',0):+.1f}% | 6M: {tech.get('perf_6m',0):+.1f}%
Supports: {tech.get('supports',[])} | Resistances: {tech.get('resistances',[])}

Return ONLY valid JSON:
{{
  "rating": "BUY/HOLD/SELL/STRONG BUY/STRONG SELL",
  "rating_color": "#26a69a",
  "price_target": 0,
  "upside_potential": 0,
  "investment_horizon": "3-6 months",
  "risk_level": "LOW/MEDIUM/HIGH",
  "confidence": 82,
  "executive_summary": "3-4 sentence summary like BNP Paribas style. Mention specific numbers.",
  "key_thesis": ["3-4 main investment thesis points with specific data"],
  "key_risks": ["3-4 specific risk factors"],
  "valuation_analysis": {{
    "assessment": "UNDERVALUED/FAIRLY VALUED/OVERVALUED",
    "assessment_color": "#26a69a",
    "pe_vs_sector": "comment on PE relative to sector peers",
    "pb_analysis": "price-to-book analysis",
    "dcf_comment": "DCF / fair value estimate comment",
    "z_score_mispricing": "institutional Z-score style comment on mispricing"
  }},
  "fundamental_analysis": {{
    "revenue_quality": "comment on revenue trends and quality",
    "margin_analysis": "gross/profit margin analysis",
    "balance_sheet": "debt, liquidity, financial health",
    "dividend_analysis": "yield and sustainability",
    "management_quality": "brief comment",
    "growth_outlook": "forward growth commentary"
  }},
  "technical_analysis": {{
    "trend_analysis": "EMA structure and trend",
    "momentum": "RSI, MACD, StochRSI combined reading",
    "key_levels": "critical support/resistance",
    "volume_confirmation": "volume analysis",
    "pattern_setup": "chart pattern if any",
    "short_term_outlook": "1-4 week technical view",
    "medium_term_outlook": "1-3 month technical view"
  }},
  "trade_setup": {{
    "entry": 0,
    "stop_loss": 0,
    "target1": 0,
    "target2": 0,
    "target3": 0,
    "risk_reward": "1:2.5",
    "position_sizing": "recommended % of portfolio"
  }},
  "sector_context": "2-3 lines on sector dynamics and where this stock fits",
  "catalyst_events": ["2-3 upcoming catalysts like earnings, policy, sector events"],
  "comparative_analysis": "brief comparison to 1-2 peers",
  "macro_factors": "macro/global factors affecting this stock",
  "voice_brief": "45-60 word spoken brief in Hindi+English: mention stock name, rating, price target, why buy/hold/sell, key risk. Sound like Bloomberg TV analyst."
}}"""

    for api_url, api_key, model in [
        (DEEPSEEK_URL, ds_key, DEEPSEEK_MODEL),
        (GROQ_URL, groq_key, GROQ_MODEL),
    ]:
        if not api_key: continue
        try:
            r = requests.post(api_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role":"user","content":prompt}],
                      "temperature": 0.3, "max_tokens": 2500},
                timeout=35)
            raw = r.json()["choices"][0]["message"]["content"].strip()
            if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw: raw = raw.split("```")[1].split("```")[0].strip()
            result = json.loads(raw)
            result["_api"] = "DeepSeek" if "deepseek" in api_url else "Groq"
            return result
        except:
            continue

    return _rule_based_report(sym, fund, tech)

def _rule_based_report(sym, fund, tech):
    price = fund.get("price", tech.get("price", 0))
    pe = fund.get("pe") or 0
    trend = tech.get("trend","SIDEWAYS")
    rsi = tech.get("rsi",50)
    analyst = fund.get("analyst_key","hold")
    if "buy" in str(analyst).lower() and trend=="BULLISH":
        rating="BUY"; rc="#26a69a"
    elif "sell" in str(analyst).lower() or trend=="BEARISH":
        rating="SELL"; rc="#ef5350"
    else:
        rating="HOLD"; rc="#f59e0b"
    sup = tech.get("supports",[]); res = tech.get("resistances",[])
    entry=sup[0] if sup else price*0.99; sl=sup[1] if len(sup)>1 else price*0.97
    t1=res[0] if res else price*1.05; t2=res[1] if len(res)>1 else price*1.10
    tm = fund.get("target_mean") or round(t1*1.02, 2)
    return {
        "rating": rating, "rating_color": rc,
        "price_target": round(tm, 2),
        "upside_potential": round((tm-price)/price*100, 1) if price else 0,
        "investment_horizon": "3-6 months", "risk_level": "MEDIUM",
        "confidence": 60,
        "executive_summary": f"{fund.get('name',sym)} is trading at {price:.2f} with {trend} technical trend. P/E of {pe:.1f} vs sector average. RSI at {rsi:.0f}. Analyst consensus: {analyst}.",
        "key_thesis": [
            f"Technical trend: {trend} with EMA structure support",
            f"RSI at {rsi:.0f} — {'momentum building' if 40<rsi<60 else 'oversold bounce potential' if rsi<40 else 'overbought caution'}",
            f"Volume {tech.get('vol_ratio',1):.1f}x average — {'confirming move' if tech.get('vol_ratio',1)>1.2 else 'below-average conviction'}",
            f"Analyst consensus: {analyst.upper()} with target {tm:.2f}",
        ],
        "key_risks": [
            "Market-wide volatility and sector rotation risk",
            f"Stop loss breach below {sl:.2f} would invalidate setup",
            "Macro headwinds: interest rates, currency, inflation",
            "Company-specific execution risk on growth plans",
        ],
        "valuation_analysis": {
            "assessment": "FAIRLY VALUED",
            "assessment_color": "#f59e0b",
            "pe_vs_sector": f"P/E of {pe:.1f} — further context needed vs sector peers",
            "pb_analysis": f"P/B: {fund.get('pb') or '—'}",
            "dcf_comment": f"Based on analyst target of {tm:.2f}, implied upside of {round((tm-price)/price*100,1) if price else 0:.1f}%",
            "z_score_mispricing": "Insufficient data for Z-score calculation — use with caution",
        },
        "fundamental_analysis": {
            "revenue_quality": f"Revenue: {fund.get('revenue',0)/1e9:.1f}B",
            "margin_analysis": f"Profit margin: {(fund.get('profit_margin') or 0)*100:.1f}% | Gross: {(fund.get('gross_margin') or 0)*100:.1f}%",
            "balance_sheet": f"D/E: {fund.get('debt_equity') or '—'} | Current ratio: {fund.get('current_ratio') or '—'}",
            "dividend_analysis": f"Yield: {(fund.get('div_yield') or 0)*100:.2f}%",
            "management_quality": "Refer to latest annual report for management commentary",
            "growth_outlook": f"Forward EPS: {fund.get('eps_forward') or '—'}",
        },
        "technical_analysis": {
            "trend_analysis": f"Trend: {trend} | EMA20: {tech.get('ema20',0):.2f} | EMA50: {tech.get('ema50',0):.2f}",
            "momentum": f"RSI {rsi:.0f} | MACD {'bullish' if tech.get('macd_hist',0)>0 else 'bearish'}",
            "key_levels": f"Support: {', '.join([str(round(x,2)) for x in tech.get('supports',[])[:2]])} | Resistance: {', '.join([str(round(x,2)) for x in tech.get('resistances',[])[:2]])}",
            "volume_confirmation": f"Volume {tech.get('vol_ratio',1):.1f}x average",
            "pattern_setup": "No clear pattern detected — monitor for breakout",
            "short_term_outlook": "1-4 weeks: follow EMA20 for directional cue",
            "medium_term_outlook": f"1-3 months: {trend} bias, watch for EMA50 cross",
        },
        "trade_setup": {
            "entry": round(entry,2), "stop_loss": round(sl,2),
            "target1": round(t1,2), "target2": round(t2,2), "target3": round(t2*1.03,2),
            "risk_reward": f"1:{(t1-entry)/(entry-sl):.1f}" if entry-sl>0 else "1:1.5",
            "position_sizing": "2-3% of portfolio"
        },
        "sector_context": f"{fund.get('sector','—')} sector — monitor sector rotation and peer performance.",
        "catalyst_events": ["Quarterly earnings release", "Sector policy update", "Macro data (inflation, rates)"],
        "comparative_analysis": "Insufficient peer data for comparison — refer to sector screener.",
        "macro_factors": "Global rate environment, USD/INR, oil prices, FII flows affecting Indian markets.",
        "voice_brief": f"Main {fund.get('name',sym)} ka analysis kar raha hoon. Stock {price:.2f} pe hai. Humara rating {rating} hai target {tm:.2f} ke saath. RSI {rsi:.0f} aur trend {trend} hai. Key risk market volatility hai.",
        "_api": "Rule-based"
    }

# ══════════════════════════════════════════════════════════════════════════════
# RENDER INSTITUTIONAL REPORT
# ══════════════════════════════════════════════════════════════════════════════
def render_institutional_report():
    st.markdown("""<style>
    header[data-testid="stHeader"],footer,
    div[data-testid="stDecoration"],div[data-testid="stToolbar"],
    div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}
    .block-container{padding:0.4rem 0.6rem!important;max-width:100vw!important;}
    </style>""", unsafe_allow_html=True)

    # ── Top Header ────────────────────────────────────────────────────────────
    st.markdown(f"""<div style="background:linear-gradient(135deg,#0a0e1a,#131722);
    border:1px solid #2a2e39;border-radius:12px;padding:12px 18px;margin-bottom:10px;">
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
        <div>
          <span style="font-size:16px;font-weight:900;color:#d1d4dc;">FinSage AI</span>
          <span style="color:#2962ff;font-weight:900;"> Research</span>
          <span style="background:#2962ff22;color:#2962ff;font-size:9px;padding:2px 7px;
          border-radius:10px;border:1px solid #2962ff44;font-weight:700;margin-left:8px;">INSTITUTIONAL GRADE</span>
        </div>
        <div style="margin-left:auto;color:#6a6e7a;font-size:11px;">
          🕐 {datetime.now().strftime('%B %d, %Y · %H:%M IST')}
        </div>
      </div>
      <div style="color:#6a6e7a;font-size:11px;margin-top:4px;">
        Full fundamental + technical analysis — BNP Paribas / Goldman Sachs style research report
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Symbol Input ──────────────────────────────────────────────────────────
    ic1, ic2, ic3 = st.columns([3, 1, 1])
    with ic1:
        sym_input = st.text_input("", placeholder="Enter symbol: RELIANCE.NS / AAPL / BTC-USD / TCS.NS",
                                   key="ir_sym", label_visibility="collapsed")
    with ic2:
        run_btn = st.button("📊 Generate Report", key="ir_run", type="primary", use_container_width=True)
    with ic3:
        clear_btn = st.button("🗑️ Clear", key="ir_clear", use_container_width=True)

    # Quick buttons
    quick_syms = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","AAPL","TSLA","NVDA","BTC-USD"]
    qc = st.columns(len(quick_syms))
    for i, q in enumerate(quick_syms):
        with qc[i]:
            if st.button(q.replace(".NS",""), key=f"ir_q_{i}", use_container_width=True):
                st.session_state.ir_sym_sel = q
                st.session_state.ir_report = None
                st.rerun()

    if clear_btn:
        st.session_state.ir_report = None
        st.session_state.ir_fund = None
        st.session_state.ir_tech = None
        st.rerun()

    sym_to_use = st.session_state.get("ir_sym_sel","") or sym_input.strip()
    if not sym_to_use and not run_btn:
        st.markdown("""<div style="text-align:center;padding:3rem;color:#6a6e7a;">
          <div style="font-size:3rem;margin-bottom:12px;">📊</div>
          <div style="font-size:16px;font-weight:700;color:#d1d4dc;margin-bottom:8px;">Institutional Research Report</div>
          <div style="font-size:13px;">Enter any symbol above or click a quick button to generate a full BNP Paribas style analysis</div>
        </div>""", unsafe_allow_html=True)
        return

    sym = resolve_ticker(sym_to_use)

    if run_btn or st.session_state.get("ir_report") is None:
        with st.spinner(f"📊 Fetching fundamental & technical data for {sym}..."):
            fund = _fetch_fundamental(sym)
            tech = _fetch_technical(sym)
            st.session_state.ir_fund = fund
            st.session_state.ir_tech = tech

        with st.spinner("🤖 AI generating institutional research report..."):
            report = _ai_research_report(sym, fund, tech)
            st.session_state.ir_report = report
        st.session_state.ir_sym_sel = sym_to_use

    fund = st.session_state.get("ir_fund", {})
    tech = st.session_state.get("ir_tech", {})
    report = st.session_state.get("ir_report", {})

    if not report or not fund:
        st.warning("No data available. Try a different symbol.")
        return

    _render_report_ui(sym, fund, tech, report)


def _render_report_ui(sym: str, fund: dict, tech: dict, report: dict):
    rc  = report.get("rating_color","#f59e0b")
    rat = report.get("rating","HOLD")
    conf= report.get("confidence",65)
    pt  = report.get("price_target",0)
    up  = report.get("upside_potential",0)
    price = fund.get("price", tech.get("price",0))
    api_used = report.get("_api","AI")
    trend = tech.get("trend","—")
    tc = "#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"
    name = fund.get("name", sym)

    # ══ COVER PAGE ════════════════════════════════════════════════════════════
    st.markdown(f"""<div style="background:linear-gradient(135deg,#0a0e1a 0%,#131722 50%,#0d1117 100%);
    border:2px solid #2a2e39;border-radius:16px;padding:20px 24px;margin-bottom:12px;
    position:relative;overflow:hidden;">
      <!-- Decorative lines -->
      <div style="position:absolute;top:0;left:0;right:0;height:4px;
      background:linear-gradient(90deg,#2962ff,#26a69a,#f59e0b,#ef5350);"></div>
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;">
        <div>
          <div style="color:#6a6e7a;font-size:11px;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:4px;">
            FinSage AI Research · {datetime.now().strftime('%B %d, %Y')}
          </div>
          <div style="font-size:26px;font-weight:900;color:#d1d4dc;margin-bottom:2px;">{name}</div>
          <div style="color:#6a6e7a;font-size:13px;margin-bottom:10px;">{sym} · {fund.get('exchange','—')} · {fund.get('sector','—')}</div>
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
            <div style="background:{rc}22;border:2px solid {rc};border-radius:10px;
            padding:6px 18px;font-size:16px;font-weight:900;color:{rc};">{rat}</div>
            <div>
              <div style="color:#6a6e7a;font-size:10px;">Price Target</div>
              <div style="font-size:18px;font-weight:900;color:#d1d4dc;font-family:monospace;">{pt:.2f}</div>
            </div>
            <div>
              <div style="color:#6a6e7a;font-size:10px;">Upside</div>
              <div style="font-size:18px;font-weight:900;color:{'#26a69a' if up>0 else '#ef5350'};">{up:+.1f}%</div>
            </div>
            <div>
              <div style="color:#6a6e7a;font-size:10px;">Risk</div>
              <div style="font-size:13px;font-weight:700;color:#f59e0b;">{report.get('risk_level','—')}</div>
            </div>
            <div style="margin-left:8px;">
              <div style="color:#6a6e7a;font-size:10px;">AI Confidence</div>
              <div style="background:#0e1117;border-radius:100px;height:6px;width:100px;margin-top:3px;">
                <div style="background:{rc};height:6px;border-radius:100px;width:{conf}%;"></div>
              </div>
              <div style="font-size:10px;color:{rc};margin-top:2px;">{conf}%</div>
            </div>
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:28px;font-weight:900;color:#d1d4dc;font-family:monospace;">{price:.2f}</div>
          <div style="color:#6a6e7a;font-size:11px;">{fund.get('currency','')}</div>
          <div style="color:{tc};font-size:13px;font-weight:700;margin-top:4px;">⬡ {trend}</div>
          <div style="color:#6a6e7a;font-size:11px;margin-top:4px;">{fund.get('mktcap_str','—')} mkt cap</div>
          <div style="color:#6a6e7a;font-size:10px;margin-top:2px;">via {api_used}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ══ EXECUTIVE SUMMARY ════════════════════════════════════════════════════
    st.markdown(f"""<div style="background:#131722;border:1px solid #2962ff33;
    border-left:4px solid #2962ff;border-radius:0 10px 10px 0;
    padding:14px 18px;margin-bottom:12px;">
      <div style="color:#2962ff;font-size:11px;font-weight:700;text-transform:uppercase;
      letter-spacing:0.12em;margin-bottom:6px;">EXECUTIVE SUMMARY</div>
      <div style="color:#d1d4dc;font-size:13px;line-height:1.7;">{report.get('executive_summary','')}</div>
    </div>""", unsafe_allow_html=True)

    # ══ KEY METRICS GRID ═════════════════════════════════════════════════════
    st.markdown("""<div style="color:#6a6e7a;font-size:10px;font-weight:700;text-transform:uppercase;
    letter-spacing:0.12em;margin-bottom:6px;">KEY METRICS</div>""", unsafe_allow_html=True)

    def _metric_cell(label, value, color="#d1d4dc", sub=""):
        val_str = str(value) if value is not None else "—"
        return f"""<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:8px;
        padding:10px 12px;text-align:center;">
          <div style="color:#6a6e7a;font-size:10px;font-weight:600;text-transform:uppercase;">{label}</div>
          <div style="font-size:17px;font-weight:900;color:{color};font-family:monospace;margin-top:3px;">{val_str}</div>
          {f'<div style="color:#6a6e7a;font-size:10px;margin-top:2px;">{sub}</div>' if sub else ''}
        </div>"""

    pe_v = f"{fund.get('pe'):.1f}" if fund.get('pe') else "—"
    pb_v = f"{fund.get('pb'):.2f}" if fund.get('pb') else "—"
    roe_v = f"{(fund.get('roe') or 0)*100:.1f}%" if fund.get('roe') else "—"
    pm_v  = f"{(fund.get('profit_margin') or 0)*100:.1f}%" if fund.get('profit_margin') else "—"
    de_v  = f"{fund.get('debt_equity'):.1f}" if fund.get('debt_equity') else "—"
    dy_v  = f"{(fund.get('div_yield') or 0)*100:.2f}%" if fund.get('div_yield') else "—"
    beta_v= f"{fund.get('beta'):.2f}" if fund.get('beta') else "—"
    rsi_v = f"{tech.get('rsi',50):.0f}"
    volr_v= f"{tech.get('vol_ratio',1):.1f}x"

    mcols = st.columns(9)
    metrics = [
        ("P/E Ratio", pe_v, "#2962ff"),
        ("P/B Ratio", pb_v, "#7986cb"),
        ("ROE", roe_v, "#26a69a"),
        ("Net Margin", pm_v, "#26a69a"),
        ("Debt/Equity", de_v, "#f59e0b"),
        ("Div Yield", dy_v, "#4caf50"),
        ("Beta", beta_v, "#9c27b0"),
        ("RSI(14)", rsi_v, "#26a69a" if tech.get("rsi",50)<50 else "#ef5350"),
        ("Volume", volr_v, "#2962ff"),
    ]
    for i, (label, val, color) in enumerate(metrics):
        with mcols[i]:
            st.markdown(_metric_cell(label, val, color), unsafe_allow_html=True)

    # ══ 52-WEEK RANGE BAR ════════════════════════════════════════════════════
    pos = fund.get("pos_in_range", 50); h52 = fund.get("h52",0); l52 = fund.get("l52",0)
    st.markdown(f"""<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:8px;
    padding:10px 14px;margin:8px 0;">
      <div style="display:flex;justify-content:space-between;margin-bottom:5px;font-size:11px;">
        <span style="color:#6a6e7a;">52W Low: <b style="color:#ef5350;">{l52:.2f}</b></span>
        <span style="color:#6a6e7a;font-weight:700;letter-spacing:0.08em;">52-WEEK RANGE</span>
        <span style="color:#6a6e7a;">52W High: <b style="color:#26a69a;">{h52:.2f}</b></span>
      </div>
      <div style="position:relative;background:#0e1117;border-radius:100px;height:8px;">
        <div style="position:absolute;left:0;top:0;height:8px;border-radius:100px;
        background:linear-gradient(90deg,#ef5350,#f59e0b,#26a69a);width:{pos}%;"></div>
        <div style="position:absolute;top:-4px;left:calc({pos}% - 8px);width:16px;height:16px;
        background:#fff;border:3px solid #2962ff;border-radius:50%;box-shadow:0 0 8px rgba(41,98,255,0.6);"></div>
      </div>
      <div style="text-align:center;font-size:11px;color:#d1d4dc;margin-top:6px;">
        Current: <b style="font-family:monospace;">{price:.2f}</b> — at <b style="color:#2962ff;">{pos:.1f}%</b> of 52-week range
      </div>
    </div>""", unsafe_allow_html=True)

    # ══ SECTION GRID: Valuation + Fundamental + Technical ════════════════════
    col1, col2, col3 = st.columns(3)

    # Valuation
    with col1:
        val_a = report.get("valuation_analysis",{})
        acolor = {"UNDERVALUED":"#26a69a","FAIRLY VALUED":"#f59e0b","OVERVALUED":"#ef5350"}.get(
            val_a.get("assessment","FAIRLY VALUED"),"#f59e0b")
        st.markdown(f"""<div style="background:#131722;border:1px solid #2a2e39;
        border-top:3px solid {acolor};border-radius:0 0 10px 10px;padding:12px;height:100%;">
          <div style="color:#6a6e7a;font-size:10px;font-weight:700;text-transform:uppercase;
          letter-spacing:0.1em;margin-bottom:8px;">📐 VALUATION</div>
          <div style="background:{acolor}22;border:1px solid {acolor}44;border-radius:6px;
          padding:6px 10px;text-align:center;margin-bottom:8px;">
            <div style="color:{acolor};font-weight:900;font-size:14px;">{val_a.get('assessment','—')}</div>
          </div>
          {''.join([f'<div style="font-size:11px;color:#9598a1;padding:4px 0;border-bottom:1px solid #1a1e2d;">• {v}</div>' for v in [val_a.get('pe_vs_sector',''), val_a.get('pb_analysis',''), val_a.get('dcf_comment',''), val_a.get('z_score_mispricing','')] if v])}
        </div>""", unsafe_allow_html=True)

    # Fundamental
    with col2:
        fund_a = report.get("fundamental_analysis",{})
        st.markdown(f"""<div style="background:#131722;border:1px solid #2a2e39;
        border-top:3px solid #26a69a;border-radius:0 0 10px 10px;padding:12px;height:100%;">
          <div style="color:#6a6e7a;font-size:10px;font-weight:700;text-transform:uppercase;
          letter-spacing:0.1em;margin-bottom:8px;">🏢 FUNDAMENTAL</div>
          {''.join([f'<div style="margin-bottom:6px;"><div style="color:#6a6e7a;font-size:9px;text-transform:uppercase;">{k.replace("_"," ")}</div><div style="font-size:11px;color:#9598a1;line-height:1.4;">{v}</div></div>' for k,v in fund_a.items() if v])}
        </div>""", unsafe_allow_html=True)

    # Technical
    with col3:
        tech_a = report.get("technical_analysis",{})
        st.markdown(f"""<div style="background:#131722;border:1px solid #2a2e39;
        border-top:3px solid #2962ff;border-radius:0 0 10px 10px;padding:12px;height:100%;">
          <div style="color:#6a6e7a;font-size:10px;font-weight:700;text-transform:uppercase;
          letter-spacing:0.1em;margin-bottom:8px;">📊 TECHNICAL</div>
          <!-- Momentum score bar -->
          <div style="margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;font-size:10px;margin-bottom:3px;">
              <span style="color:#6a6e7a;">MOMENTUM SCORE</span>
              <span style="color:{tc};font-weight:700;">{tech.get('momentum_score',0)}/100</span>
            </div>
            <div style="background:#0e1117;border-radius:4px;height:6px;">
              <div style="background:{tc};height:6px;border-radius:4px;
              width:{min(abs(tech.get('momentum_score',0)),100)}%;"></div>
            </div>
          </div>
          {''.join([f'<div style="margin-bottom:5px;"><div style="color:#6a6e7a;font-size:9px;text-transform:uppercase;">{k.replace("_"," ")}</div><div style="font-size:11px;color:#9598a1;line-height:1.4;">{v}</div></div>' for k,v in tech_a.items() if v])}
        </div>""", unsafe_allow_html=True)

    # ══ PERFORMANCE TABLE ════════════════════════════════════════════════════
    st.markdown("""<div style="color:#6a6e7a;font-size:10px;font-weight:700;text-transform:uppercase;
    letter-spacing:0.12em;margin:12px 0 6px;">PRICE PERFORMANCE</div>""", unsafe_allow_html=True)
    perf_cols = st.columns(5)
    perfs = [
        ("1 Month", tech.get("perf_1m",0)),
        ("3 Months", tech.get("perf_3m",0)),
        ("6 Months", tech.get("perf_6m",0)),
        ("vs 52W High", round((price - fund.get("h52",price))/fund.get("h52",price)*100,1) if fund.get("h52") else 0),
        ("vs 52W Low",  round((price - fund.get("l52",price))/fund.get("l52",price)*100,1) if fund.get("l52") else 0),
    ]
    for i,(label,val) in enumerate(perfs):
        with perf_cols[i]:
            c2="#26a69a" if val>=0 else "#ef5350"
            st.markdown(f"""<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:8px;
            padding:8px;text-align:center;">
              <div style="color:#6a6e7a;font-size:10px;">{label}</div>
              <div style="font-size:16px;font-weight:900;color:{c2};">{val:+.1f}%</div>
            </div>""", unsafe_allow_html=True)

    # ══ INVESTMENT THESIS + RISKS ════════════════════════════════════════════
    th1, th2 = st.columns(2)
    with th1:
        thesis = report.get("key_thesis",[])
        st.markdown("""<div style="background:#122017;border:1px solid #26a69a33;
        border-radius:10px;padding:12px 14px;margin-top:8px;">
          <div style="color:#26a69a;font-size:11px;font-weight:700;text-transform:uppercase;
          letter-spacing:0.1em;margin-bottom:8px;">✅ INVESTMENT THESIS</div>""" +
          "".join([f'<div style="display:flex;gap:8px;padding:4px 0;border-bottom:1px solid #1a3022;font-size:12px;color:#9598a1;"><span style="color:#26a69a;font-weight:700;">+</span><span>{t}</span></div>' for t in thesis]) +
          "</div>", unsafe_allow_html=True)
    with th2:
        risks = report.get("key_risks",[])
        st.markdown("""<div style="background:#1a0d0d;border:1px solid #ef535033;
        border-radius:10px;padding:12px 14px;margin-top:8px;">
          <div style="color:#ef5350;font-size:11px;font-weight:700;text-transform:uppercase;
          letter-spacing:0.1em;margin-bottom:8px;">⚠️ KEY RISKS</div>""" +
          "".join([f'<div style="display:flex;gap:8px;padding:4px 0;border-bottom:1px solid #2d1515;font-size:12px;color:#9598a1;"><span style="color:#ef5350;font-weight:700;">−</span><span>{r}</span></div>' for r in risks]) +
          "</div>", unsafe_allow_html=True)

    # ══ TRADE SETUP (BNP Paribas "Trade Idea" style) ═════════════════════════
    ts = report.get("trade_setup",{})
    entry_p=ts.get("entry",0); sl_p=ts.get("stop_loss",0)
    t1_p=ts.get("target1",0); t2_p=ts.get("target2",0); t3_p=ts.get("target3",0)

    st.markdown(f"""<div style="background:linear-gradient(135deg,#0d1117,#161b22);
    border:2px solid #2962ff33;border-radius:12px;padding:14px 18px;margin-top:10px;">
      <div style="color:#2962ff;font-size:11px;font-weight:700;text-transform:uppercase;
      letter-spacing:0.12em;margin-bottom:10px;">📐 TRADE IDEA — {report.get('investment_horizon','—')}</div>
      <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;">
        <div style="background:#122017;border:1px solid #26a69a44;border-radius:8px;padding:8px;text-align:center;">
          <div style="color:#6a6e7a;font-size:9px;text-transform:uppercase;">Entry</div>
          <div style="color:#26a69a;font-size:15px;font-weight:900;font-family:monospace;">{entry_p:.2f}</div>
        </div>
        <div style="background:#1a0d0d;border:1px solid #ef535044;border-radius:8px;padding:8px;text-align:center;">
          <div style="color:#6a6e7a;font-size:9px;text-transform:uppercase;">Stop Loss</div>
          <div style="color:#ef5350;font-size:15px;font-weight:900;font-family:monospace;">{sl_p:.2f}</div>
        </div>
        <div style="background:#0d1219;border:1px solid #2962ff44;border-radius:8px;padding:8px;text-align:center;">
          <div style="color:#6a6e7a;font-size:9px;text-transform:uppercase;">Target 1</div>
          <div style="color:#2962ff;font-size:15px;font-weight:900;font-family:monospace;">{t1_p:.2f}</div>
        </div>
        <div style="background:#0d1219;border:1px solid #7986cb44;border-radius:8px;padding:8px;text-align:center;">
          <div style="color:#6a6e7a;font-size:9px;text-transform:uppercase;">Target 2</div>
          <div style="color:#7986cb;font-size:15px;font-weight:900;font-family:monospace;">{t2_p:.2f}</div>
        </div>
        <div style="background:#0d1219;border:1px solid #9c27b044;border-radius:8px;padding:8px;text-align:center;">
          <div style="color:#6a6e7a;font-size:9px;text-transform:uppercase;">Target 3</div>
          <div style="color:#9c27b0;font-size:15px;font-weight:900;font-family:monospace;">{t3_p:.2f}</div>
        </div>
        <div style="background:#1a1500;border:1px solid #f59e0b44;border-radius:8px;padding:8px;text-align:center;">
          <div style="color:#6a6e7a;font-size:9px;text-transform:uppercase;">R:R</div>
          <div style="color:#f59e0b;font-size:15px;font-weight:900;">{ts.get('risk_reward','—')}</div>
          <div style="color:#6a6e7a;font-size:9px;">{ts.get('position_sizing','')}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ══ SECTOR + MACRO + CATALYSTS ═══════════════════════════════════════════
    sm1, sm2, sm3 = st.columns(3)
    with sm1:
        st.markdown(f"""<div style="background:#131722;border:1px solid #2a2e39;
        border-radius:8px;padding:10px 12px;margin-top:8px;height:100%;">
          <div style="color:#f59e0b;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">🌡️ SECTOR CONTEXT</div>
          <div style="font-size:11px;color:#9598a1;line-height:1.6;">{report.get('sector_context','')}</div>
        </div>""", unsafe_allow_html=True)
    with sm2:
        catalysts = report.get("catalyst_events",[])
        st.markdown("""<div style="background:#131722;border:1px solid #2a2e39;
        border-radius:8px;padding:10px 12px;margin-top:8px;height:100%;">
          <div style="color:#fbbf24;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">🎯 CATALYSTS</div>""" +
          "".join([f'<div style="font-size:11px;color:#9598a1;padding:3px 0;border-bottom:1px solid #1a1e2d;">• {c}</div>' for c in catalysts]) +
          "</div>", unsafe_allow_html=True)
    with sm3:
        st.markdown(f"""<div style="background:#131722;border:1px solid #2a2e39;
        border-radius:8px;padding:10px 12px;margin-top:8px;height:100%;">
          <div style="color:#7986cb;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">🌍 MACRO FACTORS</div>
          <div style="font-size:11px;color:#9598a1;line-height:1.6;">{report.get('macro_factors','')}</div>
          <div style="margin-top:8px;">
          <div style="color:#9c27b0;font-size:10px;font-weight:700;margin-bottom:4px;">PEER COMPARISON</div>
          <div style="font-size:11px;color:#9598a1;">{report.get('comparative_analysis','')}</div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ══ ANALYST CONSENSUS ════════════════════════════════════════════════════
    analyst_s = fund.get("analyst_summary",{})
    if analyst_s:
        total = sum(analyst_s.values()) or 1
        st.markdown("""<div style="color:#6a6e7a;font-size:10px;font-weight:700;text-transform:uppercase;
        letter-spacing:0.12em;margin:12px 0 6px;">ANALYST CONSENSUS</div>""", unsafe_allow_html=True)
        ac_cols = st.columns(4)
        ac_data = [
            ("Strong Buy", analyst_s.get("strongBuy",0), "#26a69a"),
            ("Buy", analyst_s.get("buy",0), "#4caf50"),
            ("Hold", analyst_s.get("hold",0), "#f59e0b"),
            ("Sell", analyst_s.get("sell",0), "#ef5350"),
        ]
        for i,(label,count,color) in enumerate(ac_data):
            pct = round(count/total*100)
            with ac_cols[i]:
                st.markdown(f"""<div style="background:#1e222d;border:1px solid {color}44;border-radius:8px;padding:8px;text-align:center;">
                  <div style="color:#6a6e7a;font-size:10px;">{label}</div>
                  <div style="font-size:20px;font-weight:900;color:{color};">{count}</div>
                  <div style="background:#0e1117;border-radius:3px;height:4px;margin:4px 0;">
                    <div style="background:{color};height:4px;border-radius:3px;width:{pct}%;"></div>
                  </div>
                  <div style="font-size:10px;color:{color};">{pct}%</div>
                </div>""", unsafe_allow_html=True)

    # ══ VOICE BRIEF ══════════════════════════════════════════════════════════
    voice_text = report.get("voice_brief","")
    voice_js = json.dumps(voice_text)
    st.markdown(f"""<div style="background:#0d1219;border:1px solid #2962ff33;
    border-radius:8px;padding:10px 14px;margin-top:10px;display:flex;align-items:center;gap:12px;">
      <button onclick="(function(){{
        if('speechSynthesis' in window){{
          window.speechSynthesis.cancel();
          var u=new SpeechSynthesisUtterance({voice_js});
          u.lang='hi-IN';u.rate=0.9;u.pitch=1;
          var v=window.speechSynthesis.getVoices();
          var hv=v.find(function(x){{return x.lang==='hi-IN';}});
          if(hv) u.voice=hv;
          window.speechSynthesis.speak(u);
        }}
      }})()" style="background:#2962ff;border:none;border-radius:50%;width:36px;height:36px;
      color:white;font-size:16px;cursor:pointer;flex-shrink:0;">🔊</button>
      <div>
        <div style="color:#2962ff;font-weight:700;font-size:11px;">SAGE Voice Brief</div>
        <div style="color:#6a6e7a;font-size:10px;">{report.get('investment_horizon','')} · {rat} · Target {pt:.2f}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ══ DISCLAIMER (BNP Paribas style) ═══════════════════════════════════════
    st.markdown(f"""<div style="background:#0a0d12;border:1px solid #1a1e2d;border-radius:8px;
    padding:10px 14px;margin-top:10px;font-size:9.5px;color:#4a5568;line-height:1.6;">
    <b style="color:#6a6e7a;">DISCLAIMER:</b> This research report is prepared by FinSage AI for informational and educational purposes only.
    It does NOT constitute financial advice, investment recommendation, or a solicitation to buy or sell any security.
    All data sourced from public markets (Yahoo Finance) and AI analysis (via {api_used}).
    Past performance does not guarantee future results. Investments in securities are subject to market risk.
    The price target and recommendations are AI-generated estimates and should not be relied upon for actual trading decisions.
    Always consult a SEBI/SEC-registered investment advisor before making investment decisions.
    FinSage AI Research · {datetime.now().strftime('%B %d, %Y')}
    </div>""", unsafe_allow_html=True)

    # Download button
    st.markdown("<br>", unsafe_allow_html=True)
    report_txt = f"""FinSage AI Institutional Research Report
{'='*60}
{name} ({sym}) · {datetime.now().strftime('%B %d, %Y')}
Rating: {rat} | Price Target: {pt:.2f} | Upside: {up:+.1f}%
Current Price: {price:.2f} | via {api_used}

EXECUTIVE SUMMARY
{'-'*40}
{report.get('executive_summary','')}

KEY THESIS
{chr(10).join(['+ ' + t for t in report.get('key_thesis',[])])}

KEY RISKS
{chr(10).join(['- ' + r for r in report.get('key_risks',[])])}

TRADE SETUP
Entry: {entry_p} | Stop: {sl_p} | T1: {t1_p} | T2: {t2_p} | R:R: {ts.get('risk_reward','')}

VALUATION: {report.get('valuation_analysis',{}).get('assessment','')}
SECTOR: {report.get('sector_context','')}
MACRO: {report.get('macro_factors','')}

DISCLAIMER: Educational only. Not financial advice."""

    st.download_button("📥 Download Research Report",
        report_txt, f"finsage_research_{sym.replace('.','_')}_{datetime.now().strftime('%Y%m%d')}.txt",
        "text/plain", key="ir_download")
