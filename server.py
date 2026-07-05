"""
FinSage AI — FastAPI Web Server
Replaces Streamlit. Serves API + static frontend.
Run: uvicorn server:app --host 0.0.0.0 --port 8501
"""

import os, json, traceback
from typing import Optional
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Engine imports (all streamlit-free) ──
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

from data_fetcher import fetch_stock_data, fetch_crypto_data, fetch_ticker_bar_data
from analyzer import analyze_stock, analyze_crypto, format_number
from ticker_resolver import resolve_ticker
from technical_engine import run_technical_engine, fetch_price_history
from fundamental_engine import run_fundamental_engine
from quant_engine import run_quant_engine
from volume_profile_engine import VolumeProfileEngine
from six_chart_builder import _build_six_chart_html, _build_order_flow_html
from sr_engine import SupportResistanceEngine as SREngine
from fib_engine import FibonacciEngine as FibEngine
from candle_pattern_detector import CandlePatternDetector
from json_safe import safe_dumps

# ── Config ──
LOGO_URL = "https://base44.app/api/apps/6a34884cbcecdd779c9d0281/files/mp/public/6a34884cbcecdd779c9d0281/a07ce8a2c_finsage_new_logo.jpg"
PORT = int(os.environ.get("PORT", 8501))

app = FastAPI(title="FinSage AI", version="3.0.0")

# Mount static dir
_static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(_static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


# ═════════════════════════════════════════════════════════════════════════════
#  HELPER: build full tech data dict (replaces market_dashboard _get_tech)
# ═════════════════════════════════════════════════════════════════════════════
def _build_tech(df: pd.DataFrame) -> dict:
    """Compute all technical indicators from OHLCV DataFrame."""
    if df is None or df.empty:
        return {}
    from technical_engine import rsi, macd, bollinger_bands, moving_averages, detect_support_resistance, detect_candlestick_patterns
    c = df["Close"].iloc[-1]
    df = df.copy()
    df["RSI"] = rsi(df["Close"])
    ml, sl, hl = macd(df["Close"])
    df["MACD"], df["MACD_signal"], df["MACD_hist"] = ml, sl, hl
    u, m, l = bollinger_bands(df["Close"])
    df["BB_upper"], df["BB_mid"], df["BB_lower"] = u, m, l
    df = moving_averages(df)
    sup, res = detect_support_resistance(df)
    pats = detect_candlestick_patterns(df)

    ema9 = df["Close"].ewm(span=9, adjust=False).mean().iloc[-1]
    ema20 = df.get("EMA20", df["Close"].ewm(span=20, adjust=False).mean()).iloc[-1]
    ema50 = df["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
    ema200 = df["Close"].ewm(span=200, adjust=False).mean().iloc[-1] if len(df) >= 200 else ema50
    vwap = (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum()
    atr = (df["High"] - df["Low"]).rolling(14).mean().iloc[-1]
    vol_ma = df["Volume"].rolling(20).mean().iloc[-1]
    vol_ratio = df["Volume"].iloc[-1] / vol_ma if vol_ma > 0 else 1.0

    # Performance
    perf1m = ((c / df["Close"].iloc[-22]) - 1) * 100 if len(df) > 22 else 0
    perf3m = ((c / df["Close"].iloc[-66]) - 1) * 100 if len(df) > 66 else 0
    perf6m = ((c / df["Close"].iloc[-132]) - 1) * 100 if len(df) > 132 else 0

    return {
        "price": round(float(c), 4),
        "open": round(float(df["Open"].iloc[-1]), 4),
        "high": round(float(df["High"].iloc[-1]), 4),
        "low": round(float(df["Low"].iloc[-1]), 4),
        "rsi": round(float(df["RSI"].iloc[-1]), 2),
        "macd_h": round(float(hl.iloc[-1]), 4),
        "bb_upper": round(float(u.iloc[-1]), 4),
        "bb_lower": round(float(l.iloc[-1]), 4),
        "ema9": round(float(ema9), 4),
        "ema20": round(float(ema20), 4),
        "ema50": round(float(ema50), 4),
        "ema200": round(float(ema200), 4),
        "vwap": round(float(vwap.iloc[-1]), 4),
        "atr": round(float(atr), 4),
        "vol_ratio": round(float(vol_ratio), 2),
        "supports": [round(float(s), 4) for s in sup],
        "resistances": [round(float(r), 4) for r in res],
        "patterns": [{"name": p[0], "type": p[1]} for p in pats],
        "perf1m": round(float(perf1m), 1),
        "perf3m": round(float(perf3m), 1),
        "perf6m": round(float(perf6m), 1),
        "trend": "Bullish" if c > ema20 > ema50 else "Bearish" if c < ema20 < ema50 else "Neutral",
    }


def _build_fund(ticker: str) -> dict:
    """Fetch fundamental data."""
    try:
        res = run_fundamental_engine(ticker)
        if not res.get("ok"):
            return {}
        d = res.get("data", {})
        score = res.get("score", {})
        info = yf.Ticker(ticker).info or {}
        return {
            "sector": d.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "country": info.get("country", "N/A"),
            "mktcap_str": format_number(d.get("market_cap", 0)),
            "pe": d.get("pe_ratio"),
            "fwd_pe": d.get("forward_pe"),
            "pb": d.get("pb_ratio"),
            "eps": info.get("trailingEps"),
            "fwd_eps": info.get("forwardEps"),
            "roe": d.get("roe"),
            "roa": info.get("returnOnAssets"),
            "de": d.get("debt_to_equity"),
            "cr": d.get("current_ratio"),
            "qr": info.get("quickRatio"),
            "profit_m": d.get("profit_margin"),
            "op_m": info.get("operatingMargins"),
            "gross_m": info.get("grossMargins"),
            "ebitda_m": info.get("ebitdaMargins"),
            "div_y": d.get("dividend_yield"),
            "beta": d.get("beta"),
            "rev_growth": info.get("revenueGrowth"),
            "revenue": info.get("totalRevenue", 0),
            "fcf": info.get("freeCashflow", 0),
            "cash": info.get("totalCash", 0),
            "debt": info.get("totalDebt", 0),
            "analyst": info.get("recommendationKey", "N/A"),
            "target_mean": info.get("targetMeanPrice"),
            "upside": round(((info.get("targetMeanPrice", 0) / c - 1) * 100), 1) if info.get("targetMeanPrice") and (c := d.get("current_price")) else None,
            "pfx": "$",
            "health_score": score.get("health_score"),
            "health_verdict": score.get("verdict"),
            "health_breakdown": score.get("breakdown", {}),
        }
    except Exception:
        return {}


def _build_ai_analysis(sym, name, tech, fund):
    """Call Groq/DeepSeek AI for analysis (replaces _ai_analysis from market_dashboard)."""
    import requests as req
    groq_k = os.environ.get("GROQ_API_KEY") or os.environ.get("groq_api_key", "")
    ds_k = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("deepseek_api_key", "")

    p = tech.get("price", 0)
    rsi = tech.get("rsi", 50)
    sup = tech.get("supports", [])
    res = tech.get("resistances", [])
    entry = sup[0] if sup else p * 0.99
    sl = sup[1] if len(sup) > 1 else p * 0.97
    t1 = res[0] if res else p * 1.04
    t2 = res[1] if len(res) > 1 else p * 1.08
    rr = (t1 - entry) / (entry - sl) if entry - sl > 0 else 1.5

    prompt = f"""You are SAGE, institutional-grade trading analyst. Analyze {name} ({sym}).
Price={p} RSI={rsi} Supports={sup} Resistances={res} Trend={tech.get('trend')}
Return ONLY valid JSON: {{"rating":"BUY/SELL/HOLD","price_target":{t1},"confidence":80,
"bias":"BULLISH/BEARISH/NEUTRAL","entry":{entry},"stop":{sl},"t1":{t1},"t2":{t2},"rr":"1:{rr:.1f}",
"summary":"2 sentence analysis","thesis":["point1","point2","point3"],
"risks":["risk1","risk2"],"voice":"50 word brief"}}"""

    # Try Groq first
    if groq_k:
        try:
            r = req.post("https://api.groq.com/openai/v1/chat/completions",
                json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],
                      "temperature":0.3,"max_tokens":800},
                headers={"Authorization":f"Bearer {groq_k}"}, timeout=30)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"]
                # Extract JSON
                if "```" in txt: txt = txt.split("```")[1].split("```")[0]
                if txt.startswith("json"): txt = txt[4:]
                return json.loads(txt)
        except Exception: pass

    # Fallback to DeepSeek
    if ds_k:
        try:
            r = req.post("https://api.deepseek.com/v1/chat/completions",
                json={"model":"deepseek-chat","messages":[{"role":"user","content":prompt}],
                      "temperature":0.3,"max_tokens":800},
                headers={"Authorization":f"Bearer {ds_k}"}, timeout=30)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"]
                if "```" in txt: txt = txt.split("```")[1].split("```")[0]
                if txt.startswith("json"): txt = txt[4:]
                return json.loads(txt)
        except Exception: pass

    # Final fallback — rule-based
    return {
        "rating": "HOLD", "rating_color": "#f59e0b",
        "price_target": t1, "confidence": 60,
        "bias": "BULLISH" if tech.get("trend") == "Bullish" else "BEARISH" if tech.get("trend") == "Bearish" else "NEUTRAL",
        "bias_color": "#26a69a" if tech.get("trend") == "Bullish" else "#ef5350",
        "entry": round(entry, 4), "stop": round(sl, 4),
        "t1": round(t1, 4), "t2": round(t2, 4),
        "rr": f"1:{rr:.1f}", "quality": "MODERATE",
        "summary": f"{name} trading at {p} with RSI {rsi}. Trend is {tech.get('trend')}.",
        "thesis": [f"RSI at {rsi}", f"Support at {sup[:2]}", f"Resistance at {res[:2]}"],
        "risks": ["Market volatility", "Sector rotation"],
        "voice": f"{name} is currently at {p}, RSI {rsi}, trend {tech.get('trend')}. Rating: HOLD.",
    }


# ═════════════════════════════════════════════════════════════════════════════
#  ROUTES — Frontend
# ═════════════════════════════════════════════════════════════════════════════
@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main SPA."""
    with open(os.path.join(_static_dir, "index.html"), "r") as f:
        return f.read()


# ═════════════════════════════════════════════════════════════════════════════
#  API — Stock data + analysis
# ═════════════════════════════════════════════════════════════════════════════
@app.get("/api/search")
async def search_assets(q: str = Query(..., min_length=1)):
    """Search stocks/crypto by name or ticker."""
    try:
        result = resolve_ticker(q)
        return {"ok": True, "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/quote")
async def get_quote(ticker: str = Query(...)):
    """Get real-time quote for a ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="5d")
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is None and not hist.empty:
            price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
        change = price - prev if prev else 0
        change_pct = (change / prev * 100) if prev else 0
        return {
            "ok": True,
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "price": round(float(price), 4) if price else None,
            "change": round(float(change), 4),
            "change_pct": round(float(change_pct), 2),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", ""),
            "logo": f"https://logo.clearbit.com/{info.get('website','').replace('https://','').replace('http://','').split('/')[0]}" if info.get("website") else None,
            "market_cap": format_number(info.get("marketCap", 0)),
            "pe_ratio": info.get("trailingPE"),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/dashboard/{ticker}")
async def get_dashboard(ticker: str, period: str = "6mo"):
    """Full market dashboard data: tech + fund + AI analysis + chart HTML."""
    try:
        df = fetch_price_history(ticker, period=period)
        if df.empty or len(df) < 20:
            return {"ok": False, "error": "Not enough price history."}

        tech = _build_tech(df)
        fund = _build_fund(ticker)
        name = yf.Ticker(ticker).info.get("shortName", ticker) if yf.Ticker(ticker).info else ticker

        # AI Analysis
        ai = _build_ai_analysis(ticker, name, tech, fund)
        ai["_api"] = "Groq" if os.environ.get("GROQ_API_KEY") else "DeepSeek" if os.environ.get("DEEPSEEK_API_KEY") else "Rule-based"

        # Build chart HTML
        from market_dashboard import _chart_html, _white_paper_html
        chart = _chart_html(df, tech, ai, ticker)
        whitepaper = _white_paper_html(ticker, name, tech, fund, ai)

        return {
            "ok": True,
            "ticker": ticker,
            "name": name,
            "tech": tech,
            "fundamental": fund,
            "ai": ai,
            "chart_html": chart,
            "whitepaper_html": whitepaper,
        }
    except Exception as e:
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


@app.get("/api/user-dashboard/{ticker}")
async def get_user_dashboard(ticker: str, period: str = "6mo"):
    """6-chart grid + order flow for personal dashboard."""
    try:
        df = fetch_price_history(ticker, period=period)
        if df.empty or len(df) < 30:
            return {"ok": False, "error": "Not enough data."}

        tech = _build_tech(df)
        fund = _build_fund(ticker)
        name = yf.Ticker(ticker).info.get("shortName", ticker) if yf.Ticker(ticker).info else ticker

        # S/R levels
        sr_eng = SREngine(df)
        sr_lvls = sr_eng.get_levels()

        # Volume Profile
        vp_eng = VolumeProfileEngine(df, bins=30)
        vp_res = vp_eng.calculate()

        # Fibonacci
        fib_eng = FibEngine(df)
        fib_res = fib_eng.calculate()

        # Candlestick patterns
        pat_eng = CandlePatternDetector(df)
        patterns = pat_eng.detect_all()

        # AI Analysis
        ai = _build_ai_analysis(ticker, name, tech, fund)

        # Build 6-chart HTML
        six_html = _build_six_chart_html(df, tech, ai, sr_lvls, vp_res, fib_res, patterns, ticker, name)
        of_html = _build_order_flow_html(df, tech, vp_res, ai, ticker, name)

        return {
            "ok": True,
            "ticker": ticker,
            "name": name,
            "tech": tech,
            "ai": ai,
            "six_chart_html": six_html,
            "order_flow_html": of_html,
            "sr_levels": safe_dumps([{"price": s.get("price"), "type": s.get("type")} for s in sr_lvls.get("support", []) + sr_lvls.get("resistance", [])]),
            "vp_poc": vp_res.poc,
            "vp_vah": vp_res.vah,
            "vp_val": vp_res.val,
        }
    except Exception as e:
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


@app.get("/api/quant/{ticker}")
async def get_quant(ticker: str, period: str = "1y"):
    """Quantitative analysis: volatility, beta, trend probability."""
    try:
        df = fetch_price_history(ticker, period=period)
        bench = fetch_price_history("^GSPC", period=period)  # S&P 500 benchmark
        result = run_quant_engine(df, bench)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/fundamental/{ticker}")
async def get_fundamental(ticker: str):
    """Fundamental analysis: health score, ratios."""
    try:
        return run_fundamental_engine(ticker)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/technical/{ticker}")
async def get_technical(ticker: str, period: str = "6mo"):
    """Technical analysis: RSI, MACD, BB, patterns."""
    try:
        result = run_technical_engine(ticker, period=period)
        if "df" in result:
            del result["df"]  # Strip non-serializable DataFrame
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/candles/{ticker}")
async def get_candles(ticker: str, period: str = "6mo", interval: str = "1d"):
    """Raw OHLCV candle data."""
    try:
        df = fetch_price_history(ticker, period=period, interval=interval)
        candles = []
        for idx, row in df.iterrows():
            candles.append({
                "time": int(pd.Timestamp(idx).timestamp()),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })
        return {"ok": True, "candles": candles[-300:]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/tradingview/{ticker}")
async def get_tradingview(ticker: str):
    """TradingView embedded widget HTML."""
    tv_symbol = _to_tv(ticker)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:100%;height:100%;background:#020609;overflow:hidden;}}
.tv-container{{width:100%;height:100vh;position:relative;}}
.tradingview-widget-container,.tradingview-widget-container__widget{{width:100%!important;height:100%!important;}}
</style></head><body>
<div class="tv-container">
  <div class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
    {{
      "autosize": true, "symbol": "{tv_symbol}", "interval": "D",
      "timezone": "Asia/Kolkata", "theme": "dark", "style": "1",
      "locale": "en", "toolbar_bg": "#020609",
      "backgroundColor": "rgba(2,6,9,1)", "gridColor": "rgba(0,212,255,0.03)",
      "enable_publishing": false, "allow_symbol_change": true, "save_image": true,
      "calendar": false, "hide_side_toolbar": false, "details": true,
      "hotlist": false, "withdateranges": true,
      "studies": ["RSI@tv-basicstudies","MACD@tv-basicstudies","BB@tv-basicstudies","Volume@tv-basicstudies"],
      "support_host": "https://www.tradingview.com"
    }}
    </script>
  </div>
</div>
</body></html>"""
    return {"ok": True, "html": html}


def _to_tv(sym: str) -> str:
    """Map local ticker to TradingView symbol."""
    m = {
        "RELIANCE.NS":"NSE:RELIANCE","TCS.NS":"NSE:TCS","HDFCBANK.NS":"NSE:HDFCBANK",
        "INFY.NS":"NSE:INFY","ICICIBANK.NS":"NSE:ICICIBANK","SBIN.NS":"NSE:SBIN",
        "WIPRO.NS":"NSE:WIPRO","TATAMOTORS.NS":"NSE:TATAMOTORS","BAJFINANCE.NS":"NSE:BAJFINANCE",
        "ITC.NS":"NSE:ITC","BHARTIARTL.NS":"NSE:BHARTIARTL","KOTAKBANK.NS":"NSE:KOTAKBANK",
        "LT.NS":"NSE:LT","AXISBANK.NS":"NSE:AXISBANK","MARUTI.NS":"NSE:MARUTI",
        "ASIANPAINT.NS":"NSE:ASIANPAINT","HCLTECH.NS":"NSE:HCLTECH","SUNPHARMA.NS":"NSE:SUNPHARMA",
        "TATASTEEL.NS":"NSE:TATASTEEL","ULTRACEMCO.NS":"NSE:ULTRACEMCO","ADANIENT.NS":"NSE:ADANIENT",
        "^NSEI":"NSE:NIFTY","^BSESN":"BSE:SENSEX","^GSPC":"SP:SPX","^DJI":"DJ:DJI",
        "^IXIC":"NASDAQ:IXIC","BTC-USD":"BINANCE:BTCUSDT","ETH-USD":"BINANCE:ETHUSDT",
    }
    if sym in m: return m[sym]
    if sym.endswith(".NS"): return "NSE:" + sym.replace(".NS","")
    if sym.endswith(".BO"): return "BSE:" + sym.replace(".BO","")
    return sym


@app.get("/api/watchlist/popular")
async def get_popular_watchlist():
    """Popular tickers for the watchlist grid."""
    items = [
        {"ticker":"RELIANCE.NS","name":"Reliance","cat":"stock"},
        {"ticker":"TCS.NS","name":"TCS","cat":"stock"},
        {"ticker":"HDFCBANK.NS","name":"HDFC Bank","cat":"stock"},
        {"ticker":"INFY.NS","name":"Infosys","cat":"stock"},
        {"ticker":"ICICIBANK.NS","name":"ICICI Bank","cat":"stock"},
        {"ticker":"SBIN.NS","name":"SBI","cat":"stock"},
        {"ticker":"BTC-USD","name":"Bitcoin","cat":"crypto"},
        {"ticker":"ETH-USD","name":"Ethereum","cat":"crypto"},
        {"ticker":"^NSEI","name":"Nifty 50","cat":"index"},
        {"ticker":"^GSPC","name":"S&P 500","cat":"index"},
        {"ticker":"AAPL","name":"Apple","cat":"stock"},
        {"ticker":"TSLA","name":"Tesla","cat":"stock"},
    ]
    return {"ok": True, "items": items}


# ═════════════════════════════════════════════════════════════════════════════
#  HEALTH
# ═════════════════════════════════════════════════════════════════════════════
@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat(), "version": "3.0.0"}


# ═════════════════════════════════════════════════════════════════════════════
#  STARTUP
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    print(f"\n🚀 FinSage AI starting on http://0.0.0.0:{PORT}\n")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
