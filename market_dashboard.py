"""
FinSage AI — Market Dashboard (HOME PAGE)
Global search · LightweightCharts with AI drawings · White-paper research report
"""
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import json, os, requests
from datetime import datetime

try:
    from ticker_resolver import resolve_ticker
except ImportError:
    def resolve_ticker(x): return x

LOGO_URL = "https://base44.app/api/apps/6a34884cbcecdd779c9d0281/files/mp/public/6a34884cbcecdd779c9d0281/a07ce8a2c_finsage_new_logo.jpg"

def _key(n):
    try: return st.secrets.get(n) or os.environ.get(n, "")
    except: return os.environ.get(n, "")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
CHART_H = 650

# ─── DEFAULT WATCHLIST ────────────────────────────────────────────
DEFAULT_WL = [
    {"sym": "^NSEI",        "name": "NIFTY 50",     "type": "index",  "ex": "NSE"},
    {"sym": "^BSESN",       "name": "SENSEX",       "type": "index",  "ex": "BSE"},
    {"sym": "RELIANCE.NS",  "name": "Reliance",     "type": "stock",  "ex": "NSE"},
    {"sym": "TCS.NS",       "name": "TCS",          "type": "stock",  "ex": "NSE"},
    {"sym": "HDFCBANK.NS",  "name": "HDFC Bank",    "type": "stock",  "ex": "NSE"},
    {"sym": "INFY.NS",      "name": "Infosys",      "type": "stock",  "ex": "NSE"},
    {"sym": "ICICIBANK.NS", "name": "ICICI Bank",   "type": "stock",  "ex": "NSE"},
    {"sym": "SBIN.NS",      "name": "SBI",          "type": "stock",  "ex": "NSE"},
    {"sym": "BAJFINANCE.NS","name": "Bajaj Fin",    "type": "stock",  "ex": "NSE"},
    {"sym": "WIPRO.NS",     "name": "Wipro",        "type": "stock",  "ex": "NSE"},
    {"sym": "TATAMOTORS.NS","name": "Tata Motors",  "type": "stock",  "ex": "NSE"},
    {"sym": "ADANIENT.NS",  "name": "Adani Ent",    "type": "stock",  "ex": "NSE"},
    {"sym": "AAPL",         "name": "Apple",        "type": "stock",  "ex": "NASDAQ"},
    {"sym": "TSLA",         "name": "Tesla",        "type": "stock",  "ex": "NASDAQ"},
    {"sym": "NVDA",         "name": "NVIDIA",       "type": "stock",  "ex": "NASDAQ"},
    {"sym": "MSFT",         "name": "Microsoft",    "type": "stock",  "ex": "NASDAQ"},
    {"sym": "GOOGL",        "name": "Alphabet",     "type": "stock",  "ex": "NASDAQ"},
    {"sym": "META",         "name": "Meta",         "type": "stock",  "ex": "NASDAQ"},
    {"sym": "AMZN",         "name": "Amazon",       "type": "stock",  "ex": "NASDAQ"},
    {"sym": "BTC-USD",      "name": "Bitcoin",      "type": "crypto", "ex": "CRYPTO"},
    {"sym": "ETH-USD",      "name": "Ethereum",     "type": "crypto", "ex": "CRYPTO"},
    {"sym": "SOL-USD",      "name": "Solana",       "type": "crypto", "ex": "CRYPTO"},
    {"sym": "BNB-USD",      "name": "BNB",          "type": "crypto", "ex": "CRYPTO"},
    {"sym": "XRP-USD",      "name": "XRP",          "type": "crypto", "ex": "CRYPTO"},
    {"sym": "ADA-USD",      "name": "Cardano",      "type": "crypto", "ex": "CRYPTO"},
]

def _to_tv(sym: str) -> str:
    """Convert ANY yfinance symbol to TradingView format."""
    s = sym.upper().strip()
    if s.endswith(".NS"):   return f"NSE:{s[:-3]}"
    if s.endswith(".BO"):   return f"BSE:{s[:-3]}"
    if s.endswith(".L"):    return f"LSE:{s[:-2]}"
    if s.endswith(".DE"):   return f"XETR:{s[:-3]}"
    if s.endswith(".T"):    return f"TSE:{s[:-2]}"
    if s.endswith(".HK"):   return f"HKEX:{s[:-3]}"
    if s.endswith(".AX"):   return f"ASX:{s[:-3]}"
    if s.endswith(".KS"):   return f"KRX:{s[:-3]}"
    if s.endswith(".SS"):   return f"SSE:{s[:-3]}"
    if s.endswith(".SZ"):   return f"SZSE:{s[:-3]}"
    if "-USD" in s:         return f"BINANCE:{s.replace('-USD','').replace('-','')}USDT"
    if "-USDT" in s:        return f"BINANCE:{s.replace('-','')}"
    if s in ("^NSEI",):     return "NSE:NIFTY"
    if s in ("^BSESN",):    return "BSE:SENSEX"
    if s in ("^GSPC",):     return "SP:SPX"
    if s in ("^DJI",):      return "DJ:DJI"
    if s in ("^IXIC",):     return "NASDAQ:IXIC"
    if s in ("^VIX",):      return "CBOE:VIX"
    if s in ("GC=F",):      return "TVC:GOLD"
    if s in ("CL=F",):      return "NYMEX:CL1!"
    if s in ("SI=F",):      return "TVC:SILVER"
    if s in ("NG=F",):      return "NYMEX:NG1!"
    NYSE = {"BRK-B","BRK-A","JPM","BAC","WMT","JNJ","V","MA","UNH","XOM","CVX",
            "PFE","KO","PEP","DIS","BA","GE","GM","F","T","VZ"}
    if s in NYSE:           return f"NYSE:{s}"
    return f"NASDAQ:{s}"  # default US

# ─── GLOBAL SEARCH ────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _global_search(query: str):
    q = query.strip()
    if not q: return []
    results = []
    try:
        sr = yf.Search(q, max_results=10, news_count=0)
        for item in (sr.quotes or []):
            sym = item.get("symbol", "")
            name = item.get("longname") or item.get("shortname", "")
            ex = item.get("exchDisp", "")
            qtype = item.get("quoteType", "")
            if sym and name:
                atype = "crypto" if qtype == "CRYPTOCURRENCY" or "-USD" in sym else \
                        "index" if qtype == "INDEX" else "stock"
                results.append({"sym": sym, "name": name[:28], "type": atype, "ex": ex})
    except Exception:
        pass
    if not results:
        for c in [q, q+"-USD", q+".NS", q+".BO"]:
            try:
                fi = yf.Ticker(c).fast_info
                pr = getattr(fi, "last_price", 0)
                if pr and pr > 0:
                    results.append({"sym": c, "name": c, "type": "stock", "ex": ""})
                    break
            except Exception:
                pass
    return results[:10]

# ─── PRICE (fast) ─────────────────────────────────────────────────
@st.cache_data(ttl=90, show_spinner=False)
def _price(sym: str) -> dict:
    try:
        fi = yf.Ticker(sym).fast_info
        pr = float(getattr(fi, "last_price", 0) or 0)
        prev = float(getattr(fi, "previous_close", pr) or pr)
        chg = (pr - prev) / prev * 100 if prev else 0
        return {"price": pr, "chg": chg}
    except Exception:
        return {"price": 0.0, "chg": 0.0}

# ─── OHLCV ────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _ohlcv(sym: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.Ticker(sym).history(period=period, interval=interval)
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()

# ─── TECHNICAL ANALYSIS ───────────────────────────────────────────
def _compute_tech(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 20:
        return {}
    c = df["Close"].values.astype(float)
    h = df["High"].values.astype(float)
    l = df["Low"].values.astype(float)
    v = df["Volume"].values.astype(float)
    o = df["Open"].values.astype(float)

    def ema(a, n): return pd.Series(a).ewm(span=n, adjust=False).mean().values

    # RSI
    d = np.diff(c, prepend=c[0])
    up = np.where(d > 0, d, 0); dn = np.where(d < 0, -d, 0)
    au = ema(up, 14); ad = ema(dn, 14)
    rsi_arr = 100 - 100 / (1 + np.where(ad == 0, 100, au / np.where(ad == 0, 1e-9, ad)))
    rsi = float(rsi_arr[-1])
    # StochRSI
    r14 = rsi_arr[-14:]
    stoch_rsi = float((rsi_arr[-1] - r14.min()) / (r14.max() - r14.min()) * 100) if r14.max() != r14.min() else 50.0

    ema9  = float(ema(c,  9)[-1])
    ema20 = float(ema(c, 20)[-1])
    ema50 = float(ema(c, 50)[-1]) if len(c) >= 50 else float(c.mean())
    ema200= float(ema(c,200)[-1]) if len(c) >= 200 else float(c.mean())

    # MACD
    ml = ema(c, 12) - ema(c, 26)
    sig = ema(ml, 9)
    macd_h = float(ml[-1] - sig[-1])

    # Bollinger
    sma20 = float(np.mean(c[-20:])); std20 = float(np.std(c[-20:]))
    bb_u = sma20 + 2 * std20; bb_l = sma20 - 2 * std20

    # ATR
    tr = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
    atr = float(tr[-14:].mean()) if len(tr) >= 14 else float(tr.mean()) if len(tr) > 0 else 0

    # VWAP
    tp = (h + l + c) / 3
    n20 = min(20, len(tp))
    vwap = float(np.sum(tp[-n20:] * v[-n20:]) / np.sum(v[-n20:])) if np.sum(v[-n20:]) > 0 else float(c[-1])

    vr = float(v[-1] / v[-20:].mean()) if v[-20:].mean() > 0 else 1.0

    # Support / Resistance via pivot
    win = 5; ps = []; pr2 = []
    for i in range(win, len(c) - win):
        if all(l[i] <= l[i-j] for j in range(1, win+1)) and all(l[i] <= l[i+j] for j in range(1, win+1)):
            ps.append(float(l[i]))
        if all(h[i] >= h[i-j] for j in range(1, win+1)) and all(h[i] >= h[i+j] for j in range(1, win+1)):
            pr2.append(float(h[i]))
    cur = c[-1]
    sup = sorted([x for x in ps  if x < cur], reverse=True)[:4]
    res = sorted([x for x in pr2 if x > cur])[:4]

    # Trend
    if cur > ema20 > ema50:   trend = "BULLISH"
    elif cur < ema20 < ema50: trend = "BEARISH"
    else:                      trend = "SIDEWAYS"

    # Fibonacci (last 60 bars)
    ph = float(h[-60:].max()) if len(h) >= 60 else float(h.max())
    pl = float(l[-60:].min()) if len(l) >= 60 else float(l.min())
    diff = ph - pl
    fib = {
        "0.236": round(ph - diff * 0.236, 4),
        "0.382": round(ph - diff * 0.382, 4),
        "0.500": round(ph - diff * 0.500, 4),
        "0.618": round(ph - diff * 0.618, 4),
        "0.786": round(ph - diff * 0.786, 4),
    }

    # Candlestick patterns
    pats = []
    rows = df.tail(15)
    co = rows["Close"].values.astype(float); oo = rows["Open"].values.astype(float)
    ho = rows["High"].values.astype(float);  lo2= rows["Low"].values.astype(float)
    for i in range(2, len(co)):
        o1,h1,l1,c1 = oo[i-1],ho[i-1],lo2[i-1],co[i-1]
        o2,h2,l2,c2 = oo[i],  ho[i],  lo2[i],  co[i]
        b2 = abs(c2-o2); rng = (h2-l2) or 1e-9
        lw = min(o2,c2)-l2; uw = h2-max(o2,c2)
        b1 = abs(c1-o1); b0 = abs(co[i-2]-oo[i-2]) if i>=2 else b1
        if b2 < rng*0.1:
            pats.append({"name":"Doji","type":"NEUTRAL","bar":i,"desc":f"Open≈Close at {c2:.2f} — indecision, breakout possible"})
        if lw > b2*2 and uw < b2*0.5:
            pats.append({"name":"Hammer","type":"BULLISH","bar":i,"desc":f"Buyers rejected sellers at low {l2:.2f} — reversal signal"})
        if uw > b2*2 and lw < b2*0.5:
            pats.append({"name":"Shooting Star","type":"BEARISH","bar":i,"desc":f"Sellers rejected buyers at high {h2:.2f} — reversal signal"})
        if c1<o1 and c2>o2 and o2<=c1 and c2>=o1 and b2>b1:
            pats.append({"name":"Bullish Engulfing","type":"BULLISH","bar":i,"desc":"Bull candle fully engulfs bear — strong reversal"})
        if c1>o1 and c2<o2 and o2>=c1 and c2<=o1 and b2>b1:
            pats.append({"name":"Bearish Engulfing","type":"BEARISH","bar":i,"desc":"Bear candle fully engulfs bull — strong reversal"})
        if b2/rng > 0.88 and c2>o2:
            pats.append({"name":"Bullish Marubozu","type":"BULLISH","bar":i,"desc":"No wicks — buyers fully in control"})
        if b2/rng > 0.88 and c2<o2:
            pats.append({"name":"Bearish Marubozu","type":"BEARISH","bar":i,"desc":"No wicks — sellers fully in control"})
        if b2 < rng*0.05 and lw > rng*0.6:
            pats.append({"name":"Dragonfly Doji","type":"BULLISH","bar":i,"desc":f"Buyers pushed price back from low {l2:.2f}"})
        if b2 < rng*0.05 and uw > rng*0.6:
            pats.append({"name":"Gravestone Doji","type":"BEARISH","bar":i,"desc":f"Sellers pushed back from high {h2:.2f}"})
        if i >= 2:
            if co[i-2]<oo[i-2] and b1<b0*0.35 and c2>o2 and c2>=(oo[i-2]+co[i-2])/2:
                pats.append({"name":"Morning Star","type":"BULLISH","bar":i,"desc":"3-candle reversal: exhaustion → indecision → bull"})
            if co[i-2]>oo[i-2] and b1<b0*0.35 and c2<o2 and c2<=(oo[i-2]+co[i-2])/2:
                pats.append({"name":"Evening Star","type":"BEARISH","bar":i,"desc":"3-candle reversal: exhaustion → indecision → bear"})
        if i>=2 and all(co[j]>oo[j] for j in [i-2,i-1,i]) and co[i]>co[i-1]>co[i-2]:
            pats.append({"name":"3 White Soldiers","type":"BULLISH","bar":i,"desc":"3 strong bull candles — powerful uptrend signal"})
        if i>=2 and all(co[j]<oo[j] for j in [i-2,i-1,i]) and co[i]<co[i-1]<co[i-2]:
            pats.append({"name":"3 Black Crows","type":"BEARISH","bar":i,"desc":"3 strong bear candles — powerful downtrend signal"})
    seen = set(); upats = []
    for p in pats:
        if p["name"] not in seen: seen.add(p["name"]); upats.append(p)

    # Volume profile
    lo_v = float(l.min()); hi_v = float(h.max()); vp = []
    if hi_v > lo_v:
        bs = (hi_v - lo_v) / 20
        for i in range(20):
            lb = lo_v + i*bs; hb = lb + bs; mid = (lb+hb)/2
            mask = (l <= hb) & (h >= lb)
            vp.append({"price": round(mid, 4), "vol": float(v[mask].sum())})
        vp = sorted(vp, key=lambda x: -x["vol"])

    # Performance
    perf1m = round((cur - c[-22]) / c[-22] * 100, 2) if len(c) >= 22 else 0
    perf3m = round((cur - c[-66]) / c[-66] * 100, 2) if len(c) >= 66 else 0
    perf6m = round((cur - c[0]) / c[0] * 100, 2)

    return {
        "price": cur, "rsi": rsi, "stoch_rsi": stoch_rsi,
        "ema9": ema9, "ema20": ema20, "ema50": ema50, "ema200": ema200,
        "macd_h": macd_h, "bb_upper": bb_u, "bb_lower": bb_l, "sma20": sma20,
        "atr": atr, "vwap": vwap, "vol_ratio": vr,
        "supports": sup, "resistances": res, "trend": trend, "fib": fib,
        "patterns": upats[:8], "vp": vp,
        "open": o[-1], "high": h[-1], "low": l[-1], "volume": v[-1],
        "perf1m": perf1m, "perf3m": perf3m, "perf6m": perf6m,
    }

# ─── FUNDAMENTAL ──────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _fundamental(sym: str) -> dict:
    try:
        t = yf.Ticker(sym)
        info = t.info
        mc = info.get("marketCap", 0)
        cur_sym = info.get("currency", "INR")
        pfx = "₹" if cur_sym in ("INR",) else "$"
        mc_str = (f"{pfx}{mc/1e12:.2f}T" if mc > 1e12 else f"{pfx}{mc/1e9:.1f}B" if mc > 1e9 else f"{pfx}{mc/1e6:.0f}M") if mc else "N/A"
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0) or 0
        h52 = info.get("fiftyTwoWeekHigh", 0); l52 = info.get("fiftyTwoWeekLow", 0)
        pos52 = round((price - l52) / (h52 - l52) * 100, 1) if h52 > l52 else 50
        tm = info.get("targetMeanPrice", 0)
        up = round((tm - price) / price * 100, 1) if price and tm else None
        rev_growth = None
        try:
            fin = t.financials
            if fin is not None and not fin.empty and len(fin.columns) >= 2:
                r1 = fin.loc["Total Revenue", fin.columns[0]] if "Total Revenue" in fin.index else None
                r2 = fin.loc["Total Revenue", fin.columns[1]] if "Total Revenue" in fin.index else None
                if r1 and r2 and r2 != 0: rev_growth = round((r1-r2)/abs(r2)*100, 2)
        except Exception: pass
        analyst_s = {}
        try:
            rec = t.recommendations
            if rec is not None and not rec.empty:
                lt = rec.tail(5)
                analyst_s = {
                    "strongBuy": int(lt.get("strongBuy", pd.Series([0])).iloc[-1]) if "strongBuy" in lt else 0,
                    "buy":       int(lt.get("buy",       pd.Series([0])).iloc[-1]) if "buy"       in lt else 0,
                    "hold":      int(lt.get("hold",      pd.Series([0])).iloc[-1]) if "hold"      in lt else 0,
                    "sell":      int(lt.get("sell",      pd.Series([0])).iloc[-1]) if "sell"      in lt else 0,
                }
        except Exception: pass
        return {
            "name":        info.get("longName") or info.get("shortName", sym),
            "sector":      info.get("sector", "—"),
            "industry":    info.get("industry", "—"),
            "country":     info.get("country", "—"),
            "exchange":    info.get("exchange", "—"),
            "currency":    cur_sym,
            "mktcap_str":  mc_str,
            "price":       price,
            "pe":          info.get("trailingPE"),
            "fwd_pe":      info.get("forwardPE"),
            "pb":          info.get("priceToBook"),
            "ps":          info.get("priceToSalesTrailing12Months"),
            "ev_ebitda":   info.get("enterpriseToEbitda"),
            "eps":         info.get("trailingEps"),
            "fwd_eps":     info.get("forwardEps"),
            "revenue":     info.get("totalRevenue", 0),
            "gross_m":     info.get("grossMargins"),
            "ebitda_m":    info.get("ebitdaMargins"),
            "profit_m":    info.get("profitMargins"),
            "op_m":        info.get("operatingMargins"),
            "roe":         info.get("returnOnEquity"),
            "roa":         info.get("returnOnAssets"),
            "de":          info.get("debtToEquity"),
            "cr":          info.get("currentRatio"),
            "qr":          info.get("quickRatio"),
            "div_y":       info.get("dividendYield"),
            "payout":      info.get("payoutRatio"),
            "beta":        info.get("beta"),
            "h52": h52, "l52": l52, "pos52": pos52,
            "analyst":     info.get("recommendationKey", "—"),
            "target_mean": tm,
            "target_high": info.get("targetHighPrice", 0),
            "target_low":  info.get("targetLowPrice", 0),
            "upside":      up,
            "desc":        info.get("longBusinessSummary", "")[:900],
            "employees":   info.get("fullTimeEmployees", 0),
            "website":     info.get("website", ""),
            "rev_growth":  rev_growth,
            "analyst_s":   analyst_s,
            "shares_out":  info.get("sharesOutstanding", 0),
            "cash":        info.get("totalCash", 0),
            "debt":        info.get("totalDebt", 0),
            "fcf":         info.get("freeCashflow", 0),
            "short_ratio": info.get("shortRatio", 0),
            "book_val":    info.get("bookValue", 0),
            "pfx":         pfx,
        }
    except Exception:
        return {"name": sym, "sector": "—", "industry": "—", "country": "—",
                "exchange": "—", "currency": "—", "mktcap_str": "—", "price": 0, "pfx": "$"}

# ─── AI ANALYSIS ──────────────────────────────────────────────────
def _ai_analysis(sym, name, tech, fund):
    groq_k = _key("GROQ_API_KEY"); ds_k = _key("DEEPSEEK_API_KEY")
    p = tech.get("price", 0); rsi = tech.get("rsi", 50); trend = tech.get("trend", "?")
    pats = [x["name"] for x in tech.get("patterns", [])[:5]]
    sup = tech.get("supports", []); res = tech.get("resistances", [])
    entry = sup[0] if sup else p * 0.99
    sl    = sup[1] if len(sup) > 1 else p * 0.97
    t1    = res[0] if res else p * 1.04
    t2    = res[1] if len(res) > 1 else p * 1.08
    rr    = (t1 - entry) / (entry - sl) if entry - sl > 0 else 1.5
    pfx   = fund.get("pfx", "$")

    prompt = f"""You are SAGE, institutional-grade trading analyst. Full analysis of {name} ({sym}).

TECHNICAL:
Price={p:.4f} | Open={tech.get('open',0):.4f} | High={tech.get('high',0):.4f} | Low={tech.get('low',0):.4f}
RSI={rsi:.1f} | StochRSI={tech.get('stoch_rsi',50):.1f} | Trend={trend}
EMA9={tech.get('ema9',0):.4f} EMA20={tech.get('ema20',0):.4f} EMA50={tech.get('ema50',0):.4f} EMA200={tech.get('ema200',0):.4f}
MACD_Hist={tech.get('macd_h',0):.4f} | BB_Upper={tech.get('bb_upper',0):.4f} BB_Lower={tech.get('bb_lower',0):.4f}
ATR={tech.get('atr',0):.4f} | VWAP={tech.get('vwap',0):.4f} | VolRatio={tech.get('vol_ratio',1):.2f}x
Supports={sup} | Resistances={res} | Fib={tech.get('fib',{})} | Patterns={pats}
Perf: 1M={tech.get('perf1m',0):+.1f}% 3M={tech.get('perf3m',0):+.1f}% 6M={tech.get('perf6m',0):+.1f}%

FUNDAMENTAL:
Sector={fund.get('sector')} | Industry={fund.get('industry')} | Country={fund.get('country')} | MarketCap={fund.get('mktcap_str')}
P/E={fund.get('pe')} | FwdPE={fund.get('fwd_pe')} | P/B={fund.get('pb')} | P/S={fund.get('ps')} | EV/EBITDA={fund.get('ev_ebitda')}
EPS={fund.get('eps')} | FwdEPS={fund.get('fwd_eps')} | Revenue={pfx}{fund.get('revenue',0)/1e9:.2f}B
GrossMargin={round((fund.get('gross_m') or 0)*100,1)}% | EBITDAMargin={round((fund.get('ebitda_m') or 0)*100,1)}%
NetMargin={round((fund.get('profit_m') or 0)*100,1)}% | OpMargin={round((fund.get('op_m') or 0)*100,1)}%
ROE={round((fund.get('roe') or 0)*100,1)}% | ROA={round((fund.get('roa') or 0)*100,1)}%
D/E={fund.get('de')} | CurrentRatio={fund.get('cr')} | QuickRatio={fund.get('qr')}
DivYield={round((fund.get('div_y') or 0)*100,2)}% | Beta={fund.get('beta')}
Analyst={fund.get('analyst')} | TargetMean={fund.get('target_mean')} | Upside={fund.get('upside')}%
FCF={pfx}{fund.get('fcf',0)/1e9:.2f}B | Cash={pfx}{fund.get('cash',0)/1e9:.2f}B | Debt={pfx}{fund.get('debt',0)/1e9:.2f}B
RevGrowth={fund.get('rev_growth')}%

Return ONLY valid JSON (no markdown):
{{"rating":"BUY","rating_color":"#26a69a","price_target":{round(t1,4)},"confidence":82,
"bias":"BULLISH","bias_color":"#26a69a","entry":{round(entry,4)},"stop":{round(sl,4)},
"t1":{round(t1,4)},"t2":{round(t2,4)},"rr":"1:{rr:.1f}","quality":"GOOD",
"summary":"2-sentence analysis with specific prices and percentages",
"thesis":["point 1 with data","point 2 with data","point 3 with data"],
"risks":["risk 1 specific","risk 2","risk 3"],
"indicators":{{
  "RSI":"{rsi:.0f} — explain reading",
  "StochRSI":"{tech.get('stoch_rsi',50):.0f} — explain",
  "MACD":"direction and hist reading",
  "EMA_Structure":"price vs EMA9/20/50/200",
  "Bollinger_Bands":"position, squeeze or expansion",
  "Volume":"ratio and what it means",
  "VWAP":"above/below and significance"
}},
"indicator_summary":"3-sentence combined reading of all indicators together — clear language, what they collectively signal",
"candlestick_summary":"what recent candle patterns reveal about buyer/seller pressure",
"volume_analysis":"where volume is highest, what it means for next move, POC level",
"liquidity_analysis":"where stop hunts likely, where institutional orders sit, liquidity pools",
"sr_analysis":"explain each S/R level, why it matters, strength (weak/medium/strong)",
"fundamental_analysis":{{
  "valuation_verdict":"UNDERVALUED/FAIRLY VALUED/OVERVALUED with PE/PB justification",
  "valuation_color":"#26a69a",
  "revenue_analysis":"revenue size and growth quality",
  "margin_analysis":"gross/EBITDA/net margin trend",
  "profitability":"ROE/ROA — return quality",
  "balance_sheet":"debt load, cash cushion, liquidity",
  "dividend":"yield and sustainability",
  "growth_outlook":"forward EPS and revenue growth expectation",
  "competitive_moat":"what defends this business",
  "sector_dynamics":"sector tailwinds or headwinds",
  "management_quality":"brief assessment from financials"
}},
"patterns_detail":[{{"name":"","significance":"why this matters at current price","action":"buy/sell/hold/watch"}}],
"catalyst_events":["catalyst 1","catalyst 2","catalyst 3"],
"macro_factors":"macro impact on this stock",
"comparative":"vs sector peers briefly",
"multi_tf":{{"weekly":"weekly view","daily":"daily view","hourly":"hourly entry view"}},
"voice":"55-word Hindi+English spoken brief: stock name, rating, price target, RSI level, key level, and main reason. Bloomberg TV style."
}}"""

    for url, k, model in [
        (DEEPSEEK_URL, ds_k, "deepseek-chat"),
        (GROQ_URL, groq_k, "llama-3.3-70b-versatile"),
    ]:
        if not k: continue
        try:
            r = requests.post(
                url,
                headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.2, "max_tokens": 2500},
                timeout=35,
            )
            raw = r.json()["choices"][0]["message"]["content"].strip()
            if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:   raw = raw.split("```")[1].split("```")[0].strip()
            result = json.loads(raw)
            result["_api"] = "DeepSeek" if "deepseek" in url else "Groq"
            return result
        except Exception:
            continue

    # Rule-based fallback
    bc = "#26a69a" if trend == "BULLISH" else "#ef5350" if trend == "BEARISH" else "#f59e0b"
    bias = "BULLISH" if trend == "BULLISH" else "BEARISH" if trend == "BEARISH" else "NEUTRAL"
    return {
        "rating": "HOLD", "rating_color": "#f59e0b", "price_target": round(t1, 2),
        "confidence": 60, "bias": bias, "bias_color": bc,
        "entry": round(entry, 4), "stop": round(sl, 4),
        "t1": round(t1, 4), "t2": round(t2, 4), "rr": f"1:{rr:.1f}", "quality": "AVERAGE",
        "summary": f"{name}: {trend} trend. RSI {rsi:.0f}, EMA20={tech.get('ema20',0):.2f}, volume {tech.get('vol_ratio',1):.1f}x avg.",
        "thesis": [f"Trend: {trend}", f"RSI {rsi:.0f}", f"Volume {tech.get('vol_ratio',1):.1f}x avg"],
        "risks": ["Market volatility", "Stop breach", "Macro uncertainty"],
        "indicators": {
            "RSI": f"{rsi:.0f} — {'oversold bounce likely' if rsi<40 else 'overbought caution' if rsi>70 else 'neutral momentum'}",
            "StochRSI": f"{tech.get('stoch_rsi',50):.0f}",
            "MACD": "Bullish" if tech.get("macd_h", 0) > 0 else "Bearish",
            "EMA_Structure": f"Price {'above' if p > tech.get('ema20',p) else 'below'} EMA20",
            "Bollinger_Bands": "Mid-band",
            "Volume": f"{tech.get('vol_ratio',1):.1f}x average",
            "VWAP": f"Price {'above' if p > tech.get('vwap',p) else 'below'} VWAP",
        },
        "indicator_summary": f"Indicators collectively show {bias} bias. RSI at {rsi:.0f}, MACD {'positive' if tech.get('macd_h',0)>0 else 'negative'}. Volume {tech.get('vol_ratio',1):.1f}x confirms {'interest' if tech.get('vol_ratio',1)>1.2 else 'weak conviction'}.",
        "candlestick_summary": "Recent candles show mixed signals — wait for next session confirmation.",
        "volume_analysis": f"Volume {tech.get('vol_ratio',1):.1f}x average. High volume zone near {sup[0] if sup else p:.2f}.",
        "liquidity_analysis": f"Liquidity pool near {sl:.2f}. Institutional support likely at {sup[0] if sup else p:.2f}.",
        "sr_analysis": f"Key support: {str([round(x,2) for x in sup[:3]])}. Resistance: {str([round(x,2) for x in res[:3]])}.",
        "fundamental_analysis": {
            "valuation_verdict": f"P/E {fund.get('pe') or '—'} — valuation context needed",
            "valuation_color": "#f59e0b",
            "revenue_analysis": f"Revenue {pfx}{fund.get('revenue',0)/1e9:.1f}B",
            "margin_analysis": f"Net margin {round((fund.get('profit_m') or 0)*100,1)}%",
            "profitability": f"ROE {round((fund.get('roe') or 0)*100,1)}%",
            "balance_sheet": f"D/E {fund.get('de') or '—'}, Cash {pfx}{fund.get('cash',0)/1e9:.1f}B",
            "dividend": f"Yield {round((fund.get('div_y') or 0)*100,2)}%",
            "growth_outlook": f"Fwd EPS {fund.get('fwd_eps') or '—'}",
            "competitive_moat": "Monitor competitive positioning",
            "sector_dynamics": f"Sector: {fund.get('sector','—')}",
            "management_quality": "Review latest annual report",
        },
        "patterns_detail": [{"name": x["name"], "significance": x.get("desc", ""), "action": "Monitor"} for x in tech.get("patterns", [])[:3]],
        "catalyst_events": ["Quarterly earnings", "Sector policy", "Macro data"],
        "macro_factors": "Global rates, FII flows, USD/INR, oil prices.",
        "comparative": "Compare with sector peers.",
        "multi_tf": {"weekly": f"Weekly: {trend}", "daily": f"Daily: RSI {rsi:.0f}", "hourly": "Check 1H for entry"},
        "voice": f"Main {name} ka analysis kar raha hoon. Rating {bias} hai, target {t1:.2f}. RSI {rsi:.0f} pe hai, trend {trend}. Key support {entry:.2f}. ",
        "_api": "Rule-based",
    }

# ─── LIGHTWEIGHT CHART HTML (AI draws everything) ─────────────────
def _chart_html(df, tech, ai, sym):
    candles = []; vols = []
    if not df.empty:
        for idx, row in df.tail(200).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            o_ = round(float(row["Open"]),  4)
            h_ = round(float(row["High"]),  4)
            l_ = round(float(row["Low"]),   4)
            c_ = round(float(row["Close"]), 4)
            candles.append({"time": ts, "open": o_, "high": h_, "low": l_, "close": c_})
            vols.append({"time": ts, "value": int(row["Volume"]),
                         "color": "rgba(38,166,154,0.5)" if c_ >= o_ else "rgba(239,83,80,0.5)"})

    sup  = tech.get("supports",    [])
    res  = tech.get("resistances", [])
    fib  = tech.get("fib",         {})
    vwap_v  = tech.get("vwap",   0)
    ema20_v = tech.get("ema20",  0)
    ema50_v = tech.get("ema50",  0)
    ema200_v= tech.get("ema200", 0)
    entry_v = ai.get("entry", 0); stop_v = ai.get("stop", 0)
    t1_v    = ai.get("t1",    0); t2_v   = ai.get("t2",   0)
    bc      = ai.get("bias_color", "#f59e0b")
    bias    = ai.get("bias",       "NEUTRAL")
    conf    = ai.get("confidence", 65)
    rr      = ai.get("rr",  "—")
    qual    = ai.get("quality", "—")
    cur     = tech.get("price", 0)
    rsi_v   = tech.get("rsi", 50)
    macd_up = tech.get("macd_h", 0) > 0
    vr      = tech.get("vol_ratio", 1)
    atr_v   = tech.get("atr", 0)
    api_u   = ai.get("_api", "AI")
    voice   = json.dumps(ai.get("voice", ""))

    # Pattern markers on candles
    markers = []
    if candles:
        for pt in tech.get("patterns", [])[:6]:
            bi = min(pt.get("bar", len(candles)-1), len(candles)-1)
            if 0 <= bi < len(candles):
                cdl = candles[bi]
                pc = {"BULLISH": "#26a69a", "BEARISH": "#ef5350", "NEUTRAL": "#fbbf24"}.get(pt["type"], "#fbbf24")
                ps = {"BULLISH": "arrowUp",  "BEARISH": "arrowDown", "NEUTRAL": "circle"}.get(pt["type"], "circle")
                pp = {"BULLISH": "belowBar", "BEARISH": "aboveBar",  "NEUTRAL": "inBar"}.get(pt["type"], "inBar")
                markers.append({"time": cdl["time"], "position": pp, "color": pc, "shape": ps, "text": pt["name"][:12]})

    body_h = CHART_H - 32
    # Volume profile sidebar
    vp = tech.get("vp", [])
    max_vp = max([x["vol"] for x in vp], default=1) or 1
    vp_html = ""
    for vi in sorted(vp[:18], key=lambda x: -x["price"]):
        pct = min(vi["vol"] / max_vp * 100, 100)
        is_poc = vi["vol"] == max(x["vol"] for x in vp) if vp else False
        col2 = "rgba(41,98,255,0.8)" if is_poc else "rgba(41,98,255,0.3)"
        vp_html += f'<div class="vpb"><div class="vpf" style="width:{pct:.0f}%;background:{col2};"></div><span class="vpl">{vi["price"]:.1f}</span></div>'

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#131722;color:#d1d4dc;font-family:'Trebuchet MS',sans-serif;width:100%;height:{CHART_H}px;overflow:hidden;}}
#root{{width:100%;height:{CHART_H}px;display:flex;flex-direction:column;}}
#cw{{flex:1;display:flex;height:{body_h}px;}}
#ca{{flex:1;position:relative;min-width:0;height:{body_h}px;}}
#cd{{width:100%;height:{body_h}px;}}
#vps{{width:62px;background:#0e1117;border-left:1px solid #2a2e39;display:flex;flex-direction:column;height:{body_h}px;overflow:hidden;flex-shrink:0;}}
.vpb{{display:flex;align-items:center;flex:1;padding:0 2px;border-bottom:1px solid rgba(255,255,255,0.02);min-height:0;}}
.vpf{{height:55%;border-radius:1px;min-width:2px;}}
.vpl{{font-size:7px;color:#4a5568;margin-left:2px;white-space:nowrap;overflow:hidden;max-width:32px;}}
#ft{{height:32px;background:#1e222d;border-top:1px solid #2a2e39;display:flex;align-items:center;padding:0 10px;font-size:11.5px;flex-shrink:0;gap:10px;flex-wrap:nowrap;overflow:hidden;}}
#lg{{position:absolute;top:7px;left:7px;z-index:20;background:rgba(19,23,34,0.95);border:1px solid #2a2e39;border-radius:8px;padding:7px 12px;pointer-events:none;}}
#lg .ls{{font-size:13px;font-weight:700;color:#d1d4dc;}}
#lg .lp{{font-size:22px;font-weight:900;color:{bc};font-family:monospace;margin:2px 0;}}
#lg .lb{{display:inline-block;padding:2px 10px;border-radius:10px;font-size:10px;font-weight:700;background:{bc}22;color:{bc};border:1px solid {bc}44;}}
#lvl{{position:absolute;top:7px;right:3px;z-index:20;background:rgba(19,23,34,0.95);border:1px solid #2a2e39;border-radius:8px;padding:7px 10px;min-width:148px;}}
#lvl .lh{{font-size:9px;font-weight:700;color:#6a6e7a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;}}
#lvl .lr{{font-size:12px;display:flex;justify-content:space-between;gap:7px;padding:3px 0;border-bottom:1px solid #1a1e2d;}}
#vb{{position:absolute;bottom:40px;right:4px;z-index:21;width:34px;height:34px;background:#2962ff;border:none;border-radius:50%;color:white;font-size:15px;cursor:pointer;box-shadow:0 2px 12px rgba(41,98,255,0.5);}}
#vpc{{position:absolute;bottom:40px;left:8px;right:44px;z-index:20;background:rgba(19,23,34,0.96);border:1px solid #2962ff44;border-radius:8px;padding:7px 12px;display:none;}}
#vpc.vis{{display:block;}}
</style></head><body>
<div id="root">
<div id="cw">
  <div id="ca">
    <div id="cd"></div>
    <div id="lg">
      <div class="ls">{sym}</div>
      <div class="lp">{cur:.4f}</div>
      <div class="lb">{bias} · {conf}% Confidence</div>
    </div>
    <div id="lvl">
      <div class="lh">SAGE AI Levels · {api_u}</div>
      <div class="lr"><span style="color:#26a69a;font-weight:700;">Entry</span><span style="color:#26a69a;font-family:monospace;">{entry_v:.4f}</span></div>
      <div class="lr"><span style="color:#ef5350;font-weight:700;">Stop</span><span style="color:#ef5350;font-family:monospace;">{stop_v:.4f}</span></div>
      {'<div class="lr"><span style="color:#2962ff;">T1</span><span style="color:#2962ff;font-family:monospace;">' + str(round(t1_v,4)) + '</span></div>' if t1_v else ''}
      {'<div class="lr"><span style="color:#9c27b0;">T2</span><span style="color:#9c27b0;font-family:monospace;">' + str(round(t2_v,4)) + '</span></div>' if t2_v else ''}
      <div class="lr" style="border:none;margin-top:2px;"><span style="color:#6a6e7a;font-size:9px;">R:R</span><span style="font-weight:700;">{rr}</span></div>
    </div>
    <button id="vb" onclick="doVoice()" title="SAGE Voice Brief">🔊</button>
    <div id="vpc">
      <span style="color:#2962ff;font-weight:700;font-size:11px;">🔊 SAGE Voice</span>
      <span id="vst" style="color:#6a6e7a;font-size:10px;margin-left:6px;">Speaking...</span>
    </div>
  </div>
  <div id="vps">
    <div style="font-size:7px;color:#6a6e7a;text-align:center;padding:2px 0;border-bottom:1px solid #2a2e39;font-weight:700;letter-spacing:.05em;">VOL</div>
    {vp_html}
  </div>
</div>
<div id="ft">
  <span>RSI: <b style="color:{'#ef5350' if rsi_v>70 else '#26a69a' if rsi_v<30 else '#d1d4dc'}">{rsi_v:.0f}</b></span>
  <span style="color:#2a2e39;">|</span>
  <span>MACD: <b style="color:{'#26a69a' if macd_up else '#ef5350'}">{'▲ Bull' if macd_up else '▼ Bear'}</b></span>
  <span style="color:#2a2e39;">|</span>
  <span>Vol: <b style="color:{'#2962ff' if vr>1.3 else '#d1d4dc'}">{vr:.1f}x</b></span>
  <span style="color:#2a2e39;">|</span>
  <span>ATR: <b>{atr_v:.4f}</b></span>
  <span style="color:#2a2e39;">|</span>
  <span>VWAP: <b>{vwap_v:.4f}</b></span>
  <span style="color:#2a2e39;">|</span>
  <span style="color:{bc};font-weight:700;">{rr} · {qual}</span>
  <span style="color:#2a2e39;">|</span>
  <span style="color:#4a5568;font-size:9px;margin-left:auto;">For educational use only</span>
</div>
</div>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){{
var H={body_h};
var candles={json.dumps(candles)};
var vols={json.dumps(vols)};
var supp={json.dumps(sup)};
var ress={json.dumps(res)};
var fib={json.dumps(fib)};
var marks={json.dumps(markers)};
var voice={voice};
function init(){{
  var el=document.getElementById('cd'); if(!el)return;
  var W=el.parentElement.clientWidth-62; if(W<=0) W=window.innerWidth-80;
  var chart=LightweightCharts.createChart(el,{{
    width:W, height:H,
    layout:{{background:{{type:'solid',color:'#131722'}},textColor:'#d1d4dc',fontSize:12}},
    grid:{{vertLines:{{color:'rgba(255,255,255,0.04)'}},horzLines:{{color:'rgba(255,255,255,0.04)'}}}},
    crosshair:{{mode:LightweightCharts.CrosshairMode.Normal}},
    rightPriceScale:{{borderColor:'#2a2e39'}},
    timeScale:{{borderColor:'#2a2e39',timeVisible:true,secondsVisible:false}},
    handleScroll:{{mouseWheel:true,pressedMouseMove:true}},
    handleScale:{{mouseWheel:true,pinch:true}},
  }});
  var cs=chart.addCandlestickSeries({{
    upColor:'#26a69a',downColor:'#ef5350',
    borderUpColor:'#26a69a',borderDownColor:'#ef5350',
    wickUpColor:'#26a69a',wickDownColor:'#ef5350'
  }});
  if(candles.length) cs.setData(candles);
  var vs=chart.addHistogramSeries({{priceScaleId:'vol',scaleMargins:{{top:0.78,bottom:0}}}});
  chart.priceScale('vol').applyOptions({{scaleMargins:{{top:0.78,bottom:0}}}});
  if(vols.length) vs.setData(vols);
  if(marks.length) cs.setMarkers(marks);
  // Support lines
  supp.forEach(function(s){{
    cs.createPriceLine({{price:s,color:'rgba(38,166,154,0.85)',lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'Support'}});
  }});
  // Resistance lines
  ress.forEach(function(r){{
    cs.createPriceLine({{price:r,color:'rgba(239,83,80,0.85)',lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'Resistance'}});
  }});
  // Fibonacci
  var fc={{'0.236':'#7986cb','0.382':'#26a69a','0.500':'#fbbf24','0.618':'#ef5350','0.786':'#e040fb'}};
  Object.keys(fib).forEach(function(k){{
    if(fib[k]) cs.createPriceLine({{price:fib[k],color:fc[k]||'#aaa',lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'Fib '+k}});
  }});
  // AI levels
  if({int(bool(entry_v))}) cs.createPriceLine({{price:{entry_v or 0},color:'#26a69a',lineWidth:2,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:'ENTRY'}});
  if({int(bool(stop_v))})  cs.createPriceLine({{price:{stop_v  or 0},color:'#ef5350',lineWidth:2,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:'STOP'}});
  if({int(bool(t1_v))})    cs.createPriceLine({{price:{t1_v    or 0},color:'#2962ff',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'T1'}});
  if({int(bool(t2_v))})    cs.createPriceLine({{price:{t2_v    or 0},color:'#9c27b0',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'T2'}});
  // Indicators
  if({int(bool(vwap_v))})   cs.createPriceLine({{price:{vwap_v   or 0},color:'#fbbf24',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'VWAP'}});
  if({int(bool(ema20_v))})  cs.createPriceLine({{price:{ema20_v  or 0},color:'#2196f3',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Solid, axisLabelVisible:false,title:'EMA20'}});
  if({int(bool(ema50_v))})  cs.createPriceLine({{price:{ema50_v  or 0},color:'#ff9800',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Solid, axisLabelVisible:false,title:'EMA50'}});
  if({int(bool(ema200_v))}) cs.createPriceLine({{price:{ema200_v or 0},color:'#e91e63',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:false,title:'EMA200'}});
  chart.timeScale().fitContent();
  window.addEventListener('resize',function(){{
    var nw=document.getElementById('cd').parentElement.clientWidth-62;
    chart.applyOptions({{width:nw>0?nw:400,height:H}});
  }});
}}
window.doVoice=function(){{
  var vp2=document.getElementById('vpc'),vst=document.getElementById('vst');
  if(!vp2) return;
  if(!vp2.classList.contains('vis')){{
    vp2.classList.add('vis');
    if('speechSynthesis' in window){{
      window.speechSynthesis.cancel();
      var u=new SpeechSynthesisUtterance(voice||'Analysis ready');
      u.lang='hi-IN'; u.rate=0.9; u.pitch=1;
      var vs2=window.speechSynthesis.getVoices();
      var hv=vs2.find(function(x){{return x.lang==='hi-IN';}});
      if(hv) u.voice=hv;
      if(vst) vst.textContent='Speaking...';
      u.onend=function(){{if(vst) vst.textContent='Done ✓'; vp2.classList.remove('vis');}};
      window.speechSynthesis.speak(u);
    }}
  }} else {{
    vp2.classList.remove('vis');
    if('speechSynthesis' in window) window.speechSynthesis.cancel();
  }}
}};
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
}})();
</script></body></html>"""

# ─── WHITE PAPER REPORT ───────────────────────────────────────────
def _white_paper_html(sym, name, tech, fund, ai):
    rc   = ai.get("rating_color", "#1a1a2e"); rat  = ai.get("rating", "HOLD")
    bc   = ai.get("bias_color",   "#1a1a2e"); bias = ai.get("bias",   "NEUTRAL")
    conf = ai.get("confidence", 65); pt = ai.get("price_target", 0)
    price = tech.get("price", 0); trend = tech.get("trend", "—")
    up_pct = round((pt - price) / price * 100, 1) if price and pt else 0
    api_u  = ai.get("_api", "AI")
    fa     = ai.get("fundamental_analysis", {})
    p1 = tech.get("perf1m", 0); p3 = tech.get("perf3m", 0); p6 = tech.get("perf6m", 0)
    h52 = fund.get("h52", 0); l52 = fund.get("l52", 0); pos52 = fund.get("pos52", 50)
    pfx = fund.get("pfx", "$")
    analyst_s = fund.get("analyst_s", {}); total_an = sum(analyst_s.values()) or 1
    pats = tech.get("patterns", [])

    def sv(v, fmt=".2f", sfx="", pfx_="", na="N/A"):
        if v is None or v == 0: return na
        try: return f"{pfx_}{v:{fmt}}{sfx}"
        except: return str(v)

    ind_sig = ai.get("indicators", {})
    ind_rows = ""
    for k, v in ind_sig.items():
        is_bull = any(w in str(v).lower() for w in ["bull","above","oversold","confirm","strong","positive"])
        is_bear = any(w in str(v).lower() for w in ["bear","below","overbought","weak","negative"])
        sig_col  = "#1b5e20" if is_bull else "#b71c1c" if is_bear else "#555555"
        sig_text = "▲ BULLISH" if is_bull else "▼ BEARISH" if is_bear else "→ NEUTRAL"
        ind_rows += f"""<tr>
          <td style="font-weight:700;font-family:Arial,sans-serif;">{k.replace('_',' ')}</td>
          <td>{str(v)[:50]}</td>
          <td style="color:{sig_col};font-weight:800;">{sig_text}</td>
        </tr>"""

    pat_rows = ""
    for p in ai.get("patterns_detail", pats[:4]):
        nm  = p.get("name","") or p.get("name","")
        sig = p.get("significance","") or p.get("desc","")
        act = p.get("action","Monitor")
        ptype = p.get("type","NEUTRAL") if "type" in p else "NEUTRAL"
        col = "#1b5e20" if "BULL" in ptype.upper() else "#b71c1c" if "BEAR" in ptype.upper() else "#555"
        pat_rows += f"<tr><td style='font-weight:700;'>{nm}</td><td style='color:{col};font-weight:800;'>{'▲ BULLISH' if 'BULL' in ptype.upper() else '▼ BEARISH' if 'BEAR' in ptype.upper() else '→ NEUTRAL'}</td><td>{sig[:80]}</td><td>{act}</td></tr>"

    an_rows = ""
    for lbl, cnt, col in [("Strong Buy",analyst_s.get("strongBuy",0),"#1b5e20"),
                           ("Buy",       analyst_s.get("buy",0),      "#388e3c"),
                           ("Hold",      analyst_s.get("hold",0),     "#e65100"),
                           ("Sell",      analyst_s.get("sell",0),     "#b71c1c")]:
        pct = round(cnt / total_an * 100)
        bar = f'<div style="background:#e0e0e0;border-radius:3px;height:6px;margin-top:2px;"><div style="background:{col};height:6px;border-radius:3px;width:{pct}%;"></div></div>'
        an_rows += f'<tr><td style="font-weight:700;color:{col};">{lbl}</td><td>{cnt} analysts</td><td>{pct}%{bar}</td></tr>'

    thesis_rows  = "".join([f'<div style="padding:5px 0 5px 18px;border-bottom:1px solid #eee;font-size:14px;position:relative;"><span style="position:absolute;left:2px;color:#1b5e20;font-weight:900;font-size:16px;">+</span>{t}</div>' for t in ai.get("thesis", [])])
    risk_rows    = "".join([f'<div style="padding:5px 0 5px 18px;border-bottom:1px solid #eee;font-size:14px;position:relative;"><span style="position:absolute;left:2px;color:#b71c1c;font-weight:900;font-size:16px;">−</span>{r}</div>' for r in ai.get("risks", [])])
    catalyst_rows= "".join([f'<div style="padding:4px 0 4px 14px;border-bottom:1px solid #eee;font-size:14px;position:relative;"><span style="position:absolute;left:2px;">•</span>{c}</div>' for c in ai.get("catalyst_events", [])])
    pat_tags     = "".join([f'<span style="display:inline-block;border:1.5px solid #1a1a1a;border-radius:3px;padding:2px 8px;font-size:12px;font-weight:700;margin:2px;font-family:Arial,sans-serif;">{p["name"]}</span>' for p in pats[:6]])

    html = f"""
<style>
.wp{{background:#ffffff;color:#1a1a1a;font-family:Georgia,'Times New Roman',serif;
  border:1px solid #cccccc;border-radius:4px;padding:36px 40px;line-height:1.75;}}
.wp *{{color:#1a1a1a!important;background:transparent!important;}}
.wp-stripe{{height:5px;background:linear-gradient(90deg,#1a237e,#0d47a1,#006064,#1b5e20,#e65100,#b71c1c);margin-bottom:22px;border-radius:2px;}}
.wp h1{{font-size:26px;font-weight:900;margin-bottom:4px;letter-spacing:.02em;}}
.wp h2{{font-size:14px;font-weight:900;text-transform:uppercase;letter-spacing:.12em;border-bottom:2px solid #1a1a1a;padding-bottom:5px;margin:22px 0 12px;font-family:Arial,sans-serif;}}
.wp p,.wp div.txt{{font-size:14px;line-height:1.8;margin-bottom:8px;}}
.wp table{{width:100%;border-collapse:collapse;font-size:13px;margin:10px 0;}}
.wp table th{{background:#1a1a1a!important;color:#ffffff!important;padding:8px 10px;text-align:left;font-family:Arial,sans-serif;font-size:12px;text-transform:uppercase;letter-spacing:.05em;}}
.wp table td{{padding:7px 10px;border-bottom:1px solid #e0e0e0;vertical-align:top;}}
.wp table tr:nth-child(even) td{{background:#f8f8f8!important;}}
.wp .grid9{{display:grid;grid-template-columns:repeat(9,1fr);gap:8px;margin:12px 0;}}
.wp .grid3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin:12px 0;}}
.wp .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:12px 0;}}
.wp .cell{{border:1px solid #cccccc;border-radius:4px;padding:10px;text-align:center;}}
.wp .cl{{font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-family:Arial,sans-serif;color:#555!important;margin-bottom:4px;}}
.wp .cv{{font-size:18px;font-weight:900;font-family:'Courier New',monospace;}}
.wp .badge{{display:inline-block;border:2.5px solid #1a1a1a;border-radius:4px;padding:5px 16px;font-size:15px;font-weight:900;margin-right:10px;font-family:Arial,sans-serif;}}
.wp .row{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #eeeeee;font-size:14px;}}
.wp .rl{{font-weight:700;font-family:Arial,sans-serif;color:#333!important;}}
.wp .rv{{font-family:'Courier New',monospace;font-weight:700;font-size:13px;}}
.wp .disclaimer{{font-size:11px;color:#666!important;border-top:1px solid #cccccc;margin-top:20px;padding-top:12px;font-family:Arial,sans-serif;line-height:1.6;}}
</style>
<div class="wp">
<div class="wp-stripe"></div>

<!-- COVER -->
<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;margin-bottom:20px;">
  <div>
    <h1>{name}</h1>
    <div style="font-size:14px;color:#444!important;margin-bottom:10px;">{sym} · {fund.get('exchange','—')} · {fund.get('sector','—')} · {fund.get('industry','—')} · {fund.get('country','—')}</div>
    <div><span class="badge">{rat}</span><span class="badge" style="font-size:13px;">{bias}</span></div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:32px;font-weight:900;font-family:'Courier New',monospace;">{price:.4f}</div>
    <div style="font-size:14px;">{fund.get('currency','')} · {fund.get('mktcap_str','—')}</div>
    <div style="font-size:14px;margin-top:3px;">Price Target: <b>{pt:.2f}</b> &nbsp; Upside: <b style="color:{'#1b5e20' if up_pct>0 else '#b71c1c'}!important;">{up_pct:+.1f}%</b></div>
    <div style="font-size:13px;">AI Confidence: <b>{conf}%</b> · via {api_u}</div>
    <div style="font-size:12px;margin-top:3px;">{datetime.now().strftime('%B %d, %Y · %H:%M IST')}</div>
  </div>
</div>

<h2>Executive Summary</h2>
<p class="txt">{ai.get('summary','')}</p>

<h2>Key Valuation Metrics</h2>
<div class="grid9">
  <div class="cell"><div class="cl">P/E</div><div class="cv">{sv(fund.get('pe'),'.1f','x')}</div></div>
  <div class="cell"><div class="cl">Fwd P/E</div><div class="cv">{sv(fund.get('fwd_pe'),'.1f','x')}</div></div>
  <div class="cell"><div class="cl">P/B</div><div class="cv">{sv(fund.get('pb'),'.2f','x')}</div></div>
  <div class="cell"><div class="cl">P/S</div><div class="cv">{sv(fund.get('ps'),'.2f','x')}</div></div>
  <div class="cell"><div class="cl">EV/EBITDA</div><div class="cv">{sv(fund.get('ev_ebitda'),'.1f','x')}</div></div>
  <div class="cell"><div class="cl">ROE</div><div class="cv">{sv((fund.get('roe') or 0)*100,'.1f','%')}</div></div>
  <div class="cell"><div class="cl">Net Margin</div><div class="cv">{sv((fund.get('profit_m') or 0)*100,'.1f','%')}</div></div>
  <div class="cell"><div class="cl">D/E</div><div class="cv">{sv(fund.get('de'),'.2f')}</div></div>
  <div class="cell"><div class="cl">Beta</div><div class="cv">{sv(fund.get('beta'),'.2f')}</div></div>
</div>

<h2>52-Week Price Range & Performance</h2>
<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;">
  <span>52W Low: <b>{l52:.2f}</b></span>
  <span>Current: <b>{price:.2f}</b> ({pos52:.1f}% of range)</span>
  <span>52W High: <b>{h52:.2f}</b></span>
</div>
<div style="background:#e0e0e0;border-radius:4px;height:10px;position:relative;margin-bottom:10px;">
  <div style="background:linear-gradient(90deg,#b71c1c,#e65100,#1b5e20);height:10px;border-radius:4px;width:{pos52}%;"></div>
  <div style="position:absolute;top:-4px;left:calc({pos52}% - 9px);width:18px;height:18px;background:#1a1a1a;border-radius:50%;"></div>
</div>
<div style="display:flex;gap:30px;font-size:14px;flex-wrap:wrap;margin-bottom:8px;">
  <span>1 Month: <b style="color:{'#1b5e20' if p1>0 else '#b71c1c'}!important;">{p1:+.1f}%</b></span>
  <span>3 Months: <b style="color:{'#1b5e20' if p3>0 else '#b71c1c'}!important;">{p3:+.1f}%</b></span>
  <span>6 Months: <b style="color:{'#1b5e20' if p6>0 else '#b71c1c'}!important;">{p6:+.1f}%</b></span>
  <span>vs 52W High: <b style="color:#b71c1c!important;">{round((price-h52)/h52*100,1) if h52 else 0:+.1f}%</b></span>
  <span>vs 52W Low: <b style="color:#1b5e20!important;">{round((price-l52)/l52*100,1) if l52 else 0:+.1f}%</b></span>
</div>

<h2>Fundamental Analysis</h2>
<div class="grid3">
  <div>
    <div style="font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:.08em;font-family:Arial;margin-bottom:8px;border-bottom:1px solid #ccc;padding-bottom:4px;">Income Statement</div>
    <div class="row"><span class="rl">Revenue</span><span class="rv">{pfx}{fund.get('revenue',0)/1e9:.2f}B</span></div>
    <div class="row"><span class="rl">Revenue Growth</span><span class="rv">{sv(fund.get('rev_growth'),'.1f','%')}</span></div>
    <div class="row"><span class="rl">Gross Margin</span><span class="rv">{sv((fund.get('gross_m') or 0)*100,'.1f','%')}</span></div>
    <div class="row"><span class="rl">EBITDA Margin</span><span class="rv">{sv((fund.get('ebitda_m') or 0)*100,'.1f','%')}</span></div>
    <div class="row"><span class="rl">Operating Margin</span><span class="rv">{sv((fund.get('op_m') or 0)*100,'.1f','%')}</span></div>
    <div class="row"><span class="rl">Net Margin</span><span class="rv">{sv((fund.get('profit_m') or 0)*100,'.1f','%')}</span></div>
    <div class="row"><span class="rl">EPS (TTM)</span><span class="rv">{sv(fund.get('eps'),'.2f')}</span></div>
    <div class="row"><span class="rl">Forward EPS</span><span class="rv">{sv(fund.get('fwd_eps'),'.2f')}</span></div>
    <div class="row"><span class="rl">Dividend Yield</span><span class="rv">{sv((fund.get('div_y') or 0)*100,'.2f','%')}</span></div>
    <div class="row"><span class="rl">Payout Ratio</span><span class="rv">{sv((fund.get('payout') or 0)*100,'.1f','%')}</span></div>
  </div>
  <div>
    <div style="font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:.08em;font-family:Arial;margin-bottom:8px;border-bottom:1px solid #ccc;padding-bottom:4px;">Balance Sheet & Ratios</div>
    <div class="row"><span class="rl">ROE</span><span class="rv">{sv((fund.get('roe') or 0)*100,'.1f','%')}</span></div>
    <div class="row"><span class="rl">ROA</span><span class="rv">{sv((fund.get('roa') or 0)*100,'.1f','%')}</span></div>
    <div class="row"><span class="rl">Debt / Equity</span><span class="rv">{sv(fund.get('de'),'.2f')}</span></div>
    <div class="row"><span class="rl">Current Ratio</span><span class="rv">{sv(fund.get('cr'),'.2f')}</span></div>
    <div class="row"><span class="rl">Quick Ratio</span><span class="rv">{sv(fund.get('qr'),'.2f')}</span></div>
    <div class="row"><span class="rl">Total Cash</span><span class="rv">{pfx}{fund.get('cash',0)/1e9:.2f}B</span></div>
    <div class="row"><span class="rl">Total Debt</span><span class="rv">{pfx}{fund.get('debt',0)/1e9:.2f}B</span></div>
    <div class="row"><span class="rl">Free Cash Flow</span><span class="rv">{pfx}{fund.get('fcf',0)/1e9:.2f}B</span></div>
    <div class="row"><span class="rl">Short Ratio</span><span class="rv">{sv(fund.get('short_ratio'),'.2f')}</span></div>
    <div class="row"><span class="rl">Book Value/Sh</span><span class="rv">{sv(fund.get('book_val'),'.2f')}</span></div>
  </div>
  <div>
    <div style="font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:.08em;font-family:Arial;margin-bottom:8px;border-bottom:1px solid #ccc;padding-bottom:4px;">Analyst Consensus</div>
    <table style="margin-bottom:8px;">{an_rows}</table>
    <div class="row"><span class="rl">Consensus</span><span class="rv">{fund.get('analyst','—').upper()}</span></div>
    <div class="row"><span class="rl">Target Mean</span><span class="rv">{sv(fund.get('target_mean'),'.2f')}</span></div>
    <div class="row"><span class="rl">Target High</span><span class="rv">{sv(fund.get('target_high'),'.2f')}</span></div>
    <div class="row"><span class="rl">Target Low</span><span class="rv">{sv(fund.get('target_low'),'.2f')}</span></div>
    <div class="row"><span class="rl">Upside</span><span class="rv">{sv(fund.get('upside'),'.1f','%')}</span></div>
    <div class="row"><span class="rl">Employees</span><span class="rv">{fund.get('employees',0):,}</span></div>
  </div>
</div>
<div style="font-size:14px;line-height:1.8;background:#f9f9f9!important;border:1px solid #ddd;border-radius:4px;padding:12px 16px;margin-top:4px;">
  <b>AI Fundamental View:</b> {fa.get('valuation_verdict','')} &nbsp;|&nbsp;
  {fa.get('revenue_analysis','')} &nbsp;|&nbsp; {fa.get('margin_analysis','')} &nbsp;|&nbsp;
  {fa.get('balance_sheet','')} &nbsp;|&nbsp; {fa.get('growth_outlook','')}
</div>
<div style="font-size:14px;line-height:1.8;margin-top:8px;">
  <b>Competitive Moat:</b> {fa.get('competitive_moat','')} &nbsp;·&nbsp;
  <b>Sector:</b> {fa.get('sector_dynamics','')} &nbsp;·&nbsp;
  <b>Mgmt:</b> {fa.get('management_quality','')}
</div>

<h2>Technical Indicator Analysis</h2>
<p class="txt" style="font-size:15px;font-weight:700;border-left:4px solid #1a1a1a;padding-left:12px;">{ai.get('indicator_summary','')}</p>
<table>
  <tr><th>Indicator</th><th>Reading</th><th>Signal</th></tr>
  {ind_rows}
</table>

<h2>Volume & Liquidity Analysis</h2>
<div class="grid2">
  <div>
    <div style="font-size:13px;font-weight:900;font-family:Arial;margin-bottom:6px;">Volume Analysis</div>
    <p class="txt">{ai.get('volume_analysis','')}</p>
  </div>
  <div>
    <div style="font-size:13px;font-weight:900;font-family:Arial;margin-bottom:6px;">Liquidity & Order Flow</div>
    <p class="txt">{ai.get('liquidity_analysis','')}</p>
  </div>
</div>

<h2>Support & Resistance Levels</h2>
<p class="txt">{ai.get('sr_analysis','')}</p>
<div style="display:flex;gap:30px;font-size:14px;flex-wrap:wrap;">
  <span><b>Supports:</b> {', '.join([str(round(x,4)) for x in tech.get('supports',[])[:4]])}</span>
  <span><b>Resistances:</b> {', '.join([str(round(x,4)) for x in tech.get('resistances',[])[:4]])}</span>
  <span><b>Fib 0.618:</b> {tech.get('fib',{{}}).get('0.618','—')}</span>
  <span><b>Fib 0.382:</b> {tech.get('fib',{{}}).get('0.382','—')}</span>
  <span><b>VWAP:</b> {tech.get('vwap',0):.4f}</span>
</div>

<h2>Candlestick Pattern Analysis</h2>
<p class="txt">{ai.get('candlestick_summary','')}</p>
<div style="margin:8px 0;">{pat_tags}</div>
{'<table><tr><th>Pattern</th><th>Type</th><th>Significance</th><th>Action</th></tr>' + pat_rows + '</table>' if pat_rows else ''}

<h2>Investment Thesis & Risks</h2>
<div class="grid2">
  <div>
    <div style="font-size:13px;font-weight:900;font-family:Arial;margin-bottom:6px;color:#1b5e20!important;">INVESTMENT THESIS</div>
    {thesis_rows}
  </div>
  <div>
    <div style="font-size:13px;font-weight:900;font-family:Arial;margin-bottom:6px;color:#b71c1c!important;">KEY RISKS</div>
    {risk_rows}
  </div>
</div>

<h2>Trade Setup</h2>
<div class="grid9">
  <div class="cell"><div class="cl">Entry</div><div class="cv" style="font-size:14px;">{ai.get('entry',0):.4f}</div></div>
  <div class="cell"><div class="cl">Stop Loss</div><div class="cv" style="font-size:14px;color:#b71c1c!important;">{ai.get('stop',0):.4f}</div></div>
  <div class="cell"><div class="cl">Target 1</div><div class="cv" style="font-size:14px;color:#1b5e20!important;">{ai.get('t1',0):.4f}</div></div>
  <div class="cell"><div class="cl">Target 2</div><div class="cv" style="font-size:14px;">{ai.get('t2',0):.4f}</div></div>
  <div class="cell"><div class="cl">R:R Ratio</div><div class="cv" style="font-size:16px;">{ai.get('rr','—')}</div></div>
  <div class="cell"><div class="cl">Quality</div><div class="cv" style="font-size:13px;">{ai.get('quality','—')}</div></div>
  <div class="cell"><div class="cl">RSI</div><div class="cv" style="font-size:15px;">{tech.get('rsi',50):.0f}</div></div>
  <div class="cell"><div class="cl">Trend</div><div class="cv" style="font-size:12px;">{trend}</div></div>
  <div class="cell"><div class="cl">Confidence</div><div class="cv" style="font-size:15px;">{conf}%</div></div>
</div>

<h2>Catalysts, Macro & Multi-Timeframe</h2>
<div class="grid3">
  <div>
    <div style="font-size:13px;font-weight:900;font-family:Arial;margin-bottom:6px;">Upcoming Catalysts</div>
    {catalyst_rows}
  </div>
  <div>
    <div style="font-size:13px;font-weight:900;font-family:Arial;margin-bottom:6px;">Macro Factors</div>
    <p class="txt">{ai.get('macro_factors','')}</p>
    <p class="txt">{ai.get('comparative','')}</p>
  </div>
  <div>
    <div style="font-size:13px;font-weight:900;font-family:Arial;margin-bottom:6px;">Multi-Timeframe View</div>
    {''.join([f'<div class="row"><span class="rl">{k.upper()}</span><span style="font-size:13px;">{v}</span></div>' for k,v in ai.get('multi_tf',{{}}).items()])}
  </div>
</div>

{'<h2>About ' + name + '</h2><p class="txt">' + fund.get("desc","") + '</p>' if fund.get("desc") else ''}

<div class="disclaimer">
<b>DISCLAIMER:</b> This report is prepared by FinSage AI for educational and informational purposes only.
It does NOT constitute financial advice, investment recommendation, or solicitation to buy or sell any security.
Data sourced from Yahoo Finance. AI analysis generated via {api_u} on {datetime.now().strftime('%B %d, %Y')}.
Past performance does not guarantee future results. All investments are subject to market risk.
Please consult a SEBI/SEC-registered investment advisor before making any trading or investment decisions.
FinSage AI Research · finsage.streamlit.app
</div>
</div>"""
    return html

# ═══════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════════════
def render_market_dashboard():
    st.markdown("""<style>
    header[data-testid="stHeader"],footer,div[data-testid="stDecoration"],
    div[data-testid="stToolbar"],div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}
    .block-container{padding:0!important;max-width:100vw!important;}
    </style>""", unsafe_allow_html=True)

    # Init state
    for k, v in [
        ("mkt_sel",     None), ("mkt_search",   ""),
        ("mkt_res",     []),   ("mkt_tab",       "All"),
        ("mkt_ai",      False),("mkt_ai_res",    None),
        ("mkt_fund",    {}),   ("mkt_favs",      []),
        ("mkt_tf",      "1D"), ("mkt_report_html",""),
    ]:
        if k not in st.session_state: st.session_state[k] = v

    # TOP BAR
    st.markdown(f"""<div style="background:#1e222d;border-bottom:1px solid #2a2e39;
    padding:5px 14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <img src="{LOGO_URL}" style="height:26px;border-radius:5px;" onerror="this.style.display='none'">
      <span style="color:#d1d4dc;font-weight:900;font-size:14px;">FinSage <span style="color:#2962ff;">AI</span></span>
      <span style="background:#2962ff22;color:#2962ff;font-size:8px;padding:1px 7px;border-radius:8px;border:1px solid #2962ff44;font-weight:700;">MARKET DASHBOARD</span>
      <div style="flex:1;"></div>
      <span style="color:#6a6e7a;font-size:10px;">🕐 {datetime.now().strftime('%d %b %Y · %H:%M IST')}</span>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns([1, 3], gap="small")

    # ══ LEFT PANEL ════════════════════════════════════════════════════════════
    with left:
        # Global search
        srch = st.text_input(
            "", placeholder="🔍  Search any stock/crypto worldwide...",
            key="mkt_srch_input", label_visibility="collapsed"
        )
        if srch != st.session_state.mkt_search:
            st.session_state.mkt_search = srch
            if srch.strip():
                with st.spinner("Searching..."):
                    st.session_state.mkt_res = _global_search(srch)
            else:
                st.session_state.mkt_res = []

        # Search results
        if st.session_state.mkt_res:
            st.markdown('<div style="background:#1a1e2d;border:1px solid #2962ff33;border-radius:8px;padding:4px;margin-bottom:6px;">', unsafe_allow_html=True)
            for item in st.session_state.mkt_res:
                d = _price(item["sym"])
                pr = d.get("price", 0); chg = d.get("chg", 0)
                cc = "#26a69a" if chg >= 0 else "#ef5350"
                lbl = f"{item['name'][:18]}  [{item['sym'].split('.')[0]}]"
                if st.button(lbl, key=f"sr_{item['sym']}", use_container_width=True):
                    st.session_state.mkt_sel    = item
                    st.session_state.mkt_ai     = False
                    st.session_state.mkt_ai_res = None
                    st.session_state.mkt_search = ""
                    st.session_state.mkt_res    = []
                    st.rerun()
                if pr > 0:
                    pr_str = f"{pr:,.4f}" if pr < 10 else f"{pr:,.2f}"
                    st.markdown(f'<div style="display:flex;padding:0 5px 4px 5px;font-size:10.5px;border-bottom:1px solid #1a1e2d;margin-top:-8px;"><span style="color:#6a6e7a;flex:1;font-size:9px;">{item.get("ex","")}</span><span style="color:{cc};font-family:monospace;font-weight:700;">{pr_str}</span><span style="color:{cc};margin-left:6px;">{chg:+.1f}%</span></div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        elif srch.strip() and not st.session_state.mkt_res:
            st.caption("No results — try: AAPL, BTC, Reliance, TSLA, HDFC...")

        # Tabs
        tab_opt = st.radio("", ["All", "Stocks", "Crypto", "⭐ Favs"],
                            horizontal=True, key="mkt_tab_r", label_visibility="collapsed")
        wl = DEFAULT_WL
        favs = st.session_state.get("mkt_favs", [])
        if tab_opt == "Stocks":
            wl = [x for x in wl if x["type"] == "stock"]
        elif tab_opt == "Crypto":
            wl = [x for x in wl if x["type"] == "crypto"]
        elif tab_opt == "⭐ Favs":
            fav_syms = [f["sym"] for f in favs]
            wl = [x for x in wl if x["sym"] in fav_syms] + \
                 [f for f in favs if f["sym"] not in [x["sym"] for x in wl]]

        # Header row
        st.markdown("""<div style="display:flex;padding:4px 6px;font-size:9px;color:#6a6e7a;
        font-weight:700;border-bottom:1px solid #2a2e39;background:#1a1e2d;
        border-radius:4px 4px 0 0;text-transform:uppercase;letter-spacing:.06em;">
          <span style="flex:1;">Name</span>
          <span style="width:70px;text-align:right;">Price</span>
          <span style="width:48px;text-align:right;">Chg%</span>
        </div>""", unsafe_allow_html=True)

        sel = st.session_state.get("mkt_sel") or DEFAULT_WL[0]

        for item in wl[:28]:
            d  = _price(item["sym"])
            pr = d.get("price", 0)
            chg= d.get("chg",   0)
            cc = "#26a69a" if chg >= 0 else "#ef5350"
            is_sel = sel["sym"] == item["sym"]
            is_fav = any(f["sym"] == item["sym"] for f in favs)
            btn_lbl = ("⭐" if is_fav else "") + item["name"][:16]

            # Button
            if st.button(btn_lbl, key=f"wl_{item['sym']}", use_container_width=True,
                          type="primary" if is_sel else "secondary"):
                st.session_state.mkt_sel    = item
                st.session_state.mkt_ai     = False
                st.session_state.mkt_ai_res = None
                st.rerun()

            # Price display (always visible, fixed width)
            pr_str = f"{pr:,.4f}" if pr > 0 and pr < 10 else f"{pr:,.2f}" if pr > 0 else "—"
            chg_str = f"{chg:+.1f}%" if pr > 0 else "—"
            st.markdown(
                f'<div style="display:flex;padding:0 6px 4px 6px;font-size:11px;'
                f'border-bottom:1px solid #1a1e2d;margin-top:-8px;align-items:center;">'
                f'<span style="color:#6a6e7a;font-size:9px;flex:1;">{item["sym"].replace(".NS","").replace("-USD","").replace("^","")}</span>'
                f'<span style="color:{cc};font-family:monospace;font-weight:700;min-width:70px;text-align:right;">{pr_str}</span>'
                f'<span style="color:{cc};min-width:48px;text-align:right;font-weight:600;">{chg_str}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    # ══ RIGHT PANEL ═══════════════════════════════════════════════════════════
    with right:
        sym  = sel["sym"]; name = sel["name"]
        tv_s = _to_tv(sym)

        # Toolbar
        tb1, tb2, tb3, tb4, tb5 = st.columns([4, 1, 1, 1, 1])
        with tb1:
            tf = st.radio("", ["1D","1H","15m","4H","1W","1M"],
                           horizontal=True, key="mkt_tf_r", index=0, label_visibility="collapsed")
        with tb2:
            if st.button("🤖 AI", key="mkt_ai_btn", type="primary", use_container_width=True):
                st.session_state.mkt_ai     = True
                st.session_state.mkt_ai_res = None
        with tb3:
            if st.button("📊", key="mkt_co", use_container_width=True, help="Chart only"):
                st.session_state.mkt_ai     = False
                st.session_state.mkt_ai_res = None
        with tb4:
            if st.button("⭐", key="mkt_fav_btn", use_container_width=True, help="Favourite"):
                favs = st.session_state.get("mkt_favs", [])
                if any(f["sym"] == sym for f in favs):
                    st.session_state.mkt_favs = [f for f in favs if f["sym"] != sym]
                    st.toast(f"Removed {name}")
                else:
                    st.session_state.mkt_favs = favs + [sel]
                    st.toast(f"⭐ {name} added to favourites!")
        with tb5:
            if st.button("🔄", key="mkt_ref", use_container_width=True, help="Refresh"):
                st.session_state.mkt_ai_res = None
                st.rerun()

        # Load OHLCV
        tf_map = {"1D":("3mo","1d"), "1H":("1mo","1h"), "15m":("5d","15m"),
                  "4H":("6mo","1d"), "1W":("2y","1wk"), "1M":("5y","1mo")}
        period, interval = tf_map.get(tf, ("3mo","1d"))
        with st.spinner(f"Loading {name}..."):
            df   = _ohlcv(sym, period, interval)
            tech = _compute_tech(df) if not df.empty else {}

        if df.empty:
            st.error(f"❌ No chart data for `{sym}`. Try: RELIANCE.NS (NSE), AAPL (NASDAQ), BTC-USD (Crypto)")
            return

        # ── AI MODE (LightweightCharts with all drawings) ─────────────────────
        if st.session_state.get("mkt_ai"):
            if st.session_state.get("mkt_ai_res") is None:
                with st.spinner("🤖 SAGE AI: Analyzing fundamentals, drawing Support/Resistance, Fibonacci, Patterns..."):
                    fund   = _fundamental(sym)
                    ai_res = _ai_analysis(sym, name, tech, fund)
                    wp     = _white_paper_html(sym, name, tech, fund, ai_res)
                st.session_state.mkt_ai_res      = ai_res
                st.session_state.mkt_fund        = fund
                st.session_state.mkt_report_html = wp
            else:
                ai_res = st.session_state.mkt_ai_res
                fund   = st.session_state.get("mkt_fund", {})
                wp     = st.session_state.get("mkt_report_html", "")

            # LightweightCharts with AI drawings
            chart_html = _chart_html(df, tech, ai_res, sym)
            components.html(chart_html, height=CHART_H + 12, scrolling=False)

            # Report header
            st.markdown(f"""<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:8px;
            padding:7px 14px;margin:5px 0;display:flex;align-items:center;gap:10px;">
              <span style="color:#2962ff;font-size:15px;">📄</span>
              <span style="color:#d1d4dc;font-weight:700;font-size:14px;">SAGE AI Research — {name} ({sym})</span>
              <span style="background:#2962ff22;color:#2962ff;font-size:9px;padding:2px 7px;border-radius:8px;font-weight:700;">via {ai_res.get('_api','AI')}</span>
            </div>""", unsafe_allow_html=True)

            # White paper report
            if wp:
                components.html(wp, height=3500, scrolling=True)

            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                if st.button("🔄 Refresh Analysis", key="mkt_ref2", type="primary"):
                    st.session_state.mkt_ai_res = None; st.rerun()
            with col_r2:
                if st.button("📊 Chart Only", key="mkt_c2"):
                    st.session_state.mkt_ai = False; st.rerun()
            with col_r3:
                report_txt = f"FinSage AI Research\n{name} ({sym})\n{datetime.now().strftime('%B %d, %Y')}\n\nRating: {ai_res.get('rating','—')} | Target: {ai_res.get('price_target',0):.2f} | via {ai_res.get('_api','AI')}\n\n{ai_res.get('summary','')}\n\nEntry: {ai_res.get('entry',0):.4f} | Stop: {ai_res.get('stop',0):.4f} | T1: {ai_res.get('t1',0):.4f}\n\nDISCLAIMER: Educational only. Not financial advice."
                st.download_button("📥 Download", report_txt,
                                   f"finsage_{sym.replace('.','_').replace('^','')}.txt",
                                   "text/plain", key="dl_wp")

        else:
            # ── TV CHART MODE ─────────────────────────────────────────────────
            tv_tf = {"1D":"D","1H":"60","15m":"15","4H":"240","1W":"W","1M":"M"}.get(tf,"D")
            tv_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#131722;width:100%;height:{CHART_H}px;overflow:hidden;}}</style>
</head><body>
<div style="width:100%;height:{CHART_H}px;">
  <div id="tv_c" style="width:100%;height:{CHART_H}px;"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({{
    "autosize": false, "width": "100%", "height": {CHART_H},
    "symbol": "{tv_s}", "interval": "{tv_tf}",
    "timezone": "Asia/Kolkata", "theme": "dark", "style": "1",
    "locale": "en", "toolbar_bg": "#1e222d",
    "enable_publishing": false, "hide_top_toolbar": false,
    "hide_legend": false, "save_image": true,
    "container_id": "tv_c",
    "studies": ["RSI@tv-basicstudies","MACD@tv-basicstudies","Volume@tv-basicstudies"],
    "overrides": {{
      "mainSeriesProperties.candleStyle.upColor":     "#26a69a",
      "mainSeriesProperties.candleStyle.downColor":   "#ef5350",
      "mainSeriesProperties.candleStyle.borderUpColor":   "#26a69a",
      "mainSeriesProperties.candleStyle.borderDownColor": "#ef5350",
      "mainSeriesProperties.candleStyle.wickUpColor":   "#26a69a",
      "mainSeriesProperties.candleStyle.wickDownColor": "#ef5350"
    }},
    "show_popup_button": false,
    "withdateranges": true,
    "allow_symbol_change": true
  }});
  </script>
</div></body></html>"""
            components.html(tv_html, height=CHART_H + 12, scrolling=False)

            # Hint bar
            rsi_v  = tech.get("rsi",  50)
            trend  = tech.get("trend","—")
            tc = "#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"
            vr = tech.get("vol_ratio", 1)
            st.markdown(f"""<div style="background:#1e222d;border:1px solid #2962ff22;border-radius:8px;
            padding:7px 14px;margin-top:5px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
              <span style="color:#d1d4dc;font-weight:700;">📈 {name}</span>
              <span style="color:{tc};font-weight:700;">{trend}</span>
              <span style="color:#6a6e7a;">RSI: <b style="color:#d1d4dc;">{rsi_v:.0f}</b></span>
              <span style="color:#6a6e7a;">Vol: <b style="color:#d1d4dc;">{vr:.1f}x</b></span>
              <span style="color:#6a6e7a;font-size:11px;margin-left:auto;">👆 Click <b style="color:#2962ff;">🤖 AI</b> to auto-draw S/R, Fibonacci, Patterns + Full Research Report</span>
            </div>""", unsafe_allow_html=True)
