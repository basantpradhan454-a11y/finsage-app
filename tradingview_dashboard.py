"""
FinSage AI — TradingView-Style Full Dashboard
Splash screen → Watchlist → Chart → AI Analysis (DeepSeek)
"""
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import json, os, requests, time, base64
from datetime import datetime, timedelta

try:
    from ticker_resolver import resolve_ticker
except ImportError:
    def resolve_ticker(x): return x

# ── API Keys ──────────────────────────────────────────────────────────────────
def _get_key(name):
    try: return st.secrets.get(name) or os.environ.get(name,"")
    except: return os.environ.get(name,"")

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
# DeepSeek free API (openai-compatible)
DEEPSEEK_URL   = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

LOGO_URL = "https://base44.app/api/apps/6a34884cbcecdd779c9d0281/files/mp/public/6a34884cbcecdd779c9d0281/a07ce8a2c_finsage_new_logo.jpg"

# ── Default Watchlist ─────────────────────────────────────────────────────────
WATCHLIST = [
    {"sym":"RELIANCE.NS","tv":"NSE:RELIANCE","name":"Reliance Industries","ex":"NSE","type":"stock"},
    {"sym":"TCS.NS",      "tv":"NSE:TCS",     "name":"Tata Consultancy","ex":"NSE","type":"stock"},
    {"sym":"INFY.NS",     "tv":"NSE:INFY",    "name":"Infosys","ex":"NSE","type":"stock"},
    {"sym":"HDFCBANK.NS", "tv":"NSE:HDFCBANK","name":"HDFC Bank","ex":"NSE","type":"stock"},
    {"sym":"ICICIBANK.NS","tv":"NSE:ICICIBANK","name":"ICICI Bank","ex":"NSE","type":"stock"},
    {"sym":"SBIN.NS",     "tv":"NSE:SBIN",    "name":"State Bank India","ex":"NSE","type":"stock"},
    {"sym":"WIPRO.NS",    "tv":"NSE:WIPRO",   "name":"Wipro","ex":"NSE","type":"stock"},
    {"sym":"TATAMOTORS.NS","tv":"NSE:TATAMOTORS","name":"Tata Motors","ex":"NSE","type":"stock"},
    {"sym":"ADANIPORTS.NS","tv":"NSE:ADANIPORTS","name":"Adani Ports","ex":"NSE","type":"stock"},
    {"sym":"SUNPHARMA.NS","tv":"NSE:SUNPHARMA","name":"Sun Pharma","ex":"NSE","type":"stock"},
    {"sym":"AAPL",  "tv":"NASDAQ:AAPL", "name":"Apple Inc","ex":"NASDAQ","type":"stock"},
    {"sym":"TSLA",  "tv":"NASDAQ:TSLA", "name":"Tesla","ex":"NASDAQ","type":"stock"},
    {"sym":"NVDA",  "tv":"NASDAQ:NVDA", "name":"NVIDIA","ex":"NASDAQ","type":"stock"},
    {"sym":"MSFT",  "tv":"NASDAQ:MSFT", "name":"Microsoft","ex":"NASDAQ","type":"stock"},
    {"sym":"GOOGL", "tv":"NASDAQ:GOOGL","name":"Alphabet","ex":"NASDAQ","type":"stock"},
    {"sym":"BTC-USD","tv":"BINANCE:BTCUSDT","name":"Bitcoin","ex":"CRYPTO","type":"crypto"},
    {"sym":"ETH-USD","tv":"BINANCE:ETHUSDT","name":"Ethereum","ex":"CRYPTO","type":"crypto"},
    {"sym":"SOL-USD","tv":"BINANCE:SOLUSDT","name":"Solana","ex":"CRYPTO","type":"crypto"},
    {"sym":"BNB-USD","tv":"BINANCE:BNBUSDT","name":"BNB","ex":"CRYPTO","type":"crypto"},
    {"sym":"XRP-USD","tv":"BINANCE:XRPUSDT","name":"XRP","ex":"CRYPTO","type":"crypto"},
]

# ── Data helpers ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=90, show_spinner=False)
def _price_data(sym:str) -> dict:
    try:
        t=yf.Ticker(sym)
        df=t.history(period="5d",interval="1d")
        if df.empty: return {}
        c=float(df["Close"].iloc[-1])
        pc=float(df["Close"].iloc[-2]) if len(df)>1 else c
        v=float(df["Volume"].iloc[-1])
        h=float(df["High"].iloc[-1]); l=float(df["Low"].iloc[-1])
        chg=(c-pc)/pc*100 if pc else 0
        sparkline=[float(x) for x in df["Close"].values[-7:]]
        return {"price":c,"prev_close":pc,"chg":chg,"volume":v,"high":h,"low":l,
                "sparkline":sparkline,"mktcap":t.info.get("marketCap",0)}
    except: return {}

@st.cache_data(ttl=60, show_spinner=False)
def _ohlcv(sym:str, period:str="3mo", interval:str="1d") -> pd.DataFrame:
    try:
        df=yf.Ticker(sym).history(period=period,interval=interval)
        if df.empty: return pd.DataFrame()
        df.index=pd.to_datetime(df.index)
        return df
    except: return pd.DataFrame()

# ── Technical Analysis Engine ─────────────────────────────────────────────────
def _compute_all(df:pd.DataFrame) -> dict:
    if df.empty or len(df)<20: return {}
    c=df["Close"].values.astype(float)
    h=df["High"].values.astype(float)
    l=df["Low"].values.astype(float)
    o=df["Open"].values.astype(float)
    v=df["Volume"].values.astype(float)

    def ema(arr,n): return pd.Series(arr).ewm(span=n,adjust=False).mean().values

    # RSI
    d=np.diff(c,prepend=c[0])
    up=np.where(d>0,d,0); dn=np.where(d<0,-d,0)
    au=ema(up,14); ad=ema(dn,14)
    rsi=float((100-100/(1+np.where(ad==0,100,au/np.where(ad==0,1e-9,ad))))[-1])

    ema9_arr=ema(c,9); ema20_arr=ema(c,20); ema50_arr=ema(c,50)
    ema200_arr=ema(c,200) if len(c)>=200 else np.full_like(c,c.mean())
    ema9=float(ema9_arr[-1]); ema20=float(ema20_arr[-1])
    ema50=float(ema50_arr[-1]); ema200=float(ema200_arr[-1])

    macd_line=ema(c,12)-ema(c,26); signal=ema(macd_line,9)
    macd_val=float(macd_line[-1]); macd_hist=float(macd_line[-1]-signal[-1])
    macd_signal=float(signal[-1])

    # Bollinger
    sma20=float(np.mean(c[-20:])); std20=float(np.std(c[-20:]))
    bb_u=sma20+2*std20; bb_l=sma20-2*std20; bb_mid=sma20

    # ATR
    tr=np.maximum(h[1:]-l[1:],np.maximum(abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1])))
    atr=float(tr[-14:].mean()) if len(tr)>=14 else float(tr.mean()) if len(tr)>0 else 0

    # VWAP
    tp=(h+l+c)/3; n20=min(20,len(tp))
    vwap=float(np.sum(tp[-n20:]*v[-n20:])/np.sum(v[-n20:])) if np.sum(v[-n20:])>0 else float(c[-1])

    vol_ratio=float(v[-1]/v[-20:].mean()) if v[-20:].mean()>0 else 1.0

    # S/R via pivot method
    window=5; pivots_s=[]; pivots_r=[]
    for i in range(window,len(c)-window):
        if all(l[i]<=l[i-j] for j in range(1,window+1)) and all(l[i]<=l[i+j] for j in range(1,window+1)):
            pivots_s.append(float(l[i]))
        if all(h[i]>=h[i-j] for j in range(1,window+1)) and all(h[i]>=h[i+j] for j in range(1,window+1)):
            pivots_r.append(float(h[i]))
    cur=c[-1]
    supports=sorted([x for x in pivots_s if x<cur],reverse=True)[:3]
    resistances=sorted([x for x in pivots_r if x>cur])[:3]

    # Fibonacci
    ph=float(h[-60:].max()) if len(h)>=60 else float(h.max())
    pl=float(l[-60:].min()) if len(l)>=60 else float(l.min())
    diff=ph-pl
    fib={"0.236":round(ph-diff*0.236,4),"0.382":round(ph-diff*0.382,4),
         "0.500":round(ph-diff*0.500,4),"0.618":round(ph-diff*0.618,4),
         "0.786":round(ph-diff*0.786,4)}

    # Trend
    if cur>ema20>ema50: trend="BULLISH"
    elif cur<ema20<ema50: trend="BEARISH"
    else: trend="SIDEWAYS"

    # Stoch RSI
    rsi_arr=[]
    for i in range(14,len(c)):
        d2=np.diff(c[max(0,i-14):i+1],prepend=c[max(0,i-14)])
        u2=np.where(d2>0,d2,0); d3=np.where(d2<0,-d2,0)
        au2=u2.mean(); ad2=d3.mean()
        rsi_arr.append(100-100/(1+(au2/ad2 if ad2>0 else 100)))
    if len(rsi_arr)>=14:
        rm=min(rsi_arr[-14:]); rx=max(rsi_arr[-14:])
        stoch_rsi=float((rsi_arr[-1]-rm)/(rx-rm)*100) if rx!=rm else 50.0
    else: stoch_rsi=50.0

    # Volume profile
    lo=float(l.min()); hi=float(h.max()); bins=20
    if hi>lo:
        bs=(hi-lo)/bins; vp=[]
        for i in range(bins):
            lb=lo+i*bs; hb=lb+bs; mid=(lb+hb)/2
            mask=(l<=hb)&(h>=lb)
            vp.append({"price":round(mid,4),"vol":float(v[mask].sum())})
        vp=sorted(vp,key=lambda x:-x["vol"])
    else: vp=[]

    # Candlestick patterns
    patterns=_detect_patterns_full(df)

    return {
        "price":cur,"open":o[-1],"high":h[-1],"low":l[-1],"volume":v[-1],
        "rsi":rsi,"ema9":ema9,"ema20":ema20,"ema50":ema50,"ema200":ema200,
        "ema9_arr":ema9_arr.tolist(),"ema20_arr":ema20_arr.tolist(),
        "ema50_arr":ema50_arr.tolist(),
        "macd":macd_val,"macd_hist":macd_hist,"macd_signal":macd_signal,
        "bb_upper":bb_u,"bb_lower":bb_l,"bb_mid":bb_mid,
        "atr":atr,"vwap":vwap,"vol_ratio":vol_ratio,
        "supports":supports,"resistances":resistances,"fib":fib,
        "trend":trend,"stoch_rsi":stoch_rsi,"vp":vp,"patterns":patterns,
        "period_high":ph,"period_low":pl,
    }

def _detect_patterns_full(df:pd.DataFrame) -> list:
    if df.empty or len(df)<5: return []
    rows=df.tail(15)
    c=rows["Close"].values.astype(float); o=rows["Open"].values.astype(float)
    h=rows["High"].values.astype(float);  l=rows["Low"].values.astype(float)
    pats=[]
    for i in range(2,len(c)):
        o1,h1,l1,c1=o[i-1],h[i-1],l[i-1],c[i-1]
        o2,h2,l2,c2=o[i],h[i],l[i],c[i]
        b1=abs(c1-o1); b2=abs(c2-o2); rng=h2-l2 if h2-l2>0 else 1e-9
        lw=min(o2,c2)-l2; uw=h2-max(o2,c2)
        if b2<rng*0.1: pats.append({"name":"Doji","type":"NEUTRAL","bar":i,"desc":f"Indecision at {c2:.2f} — open≈close, no clear direction"})
        if lw>b2*2 and uw<b2*0.5 and c2>l2: pats.append({"name":"Hammer","type":"BULLISH","bar":i,"desc":f"Bullish reversal at {c2:.2f} — buyers rejected price at {l2:.2f}"})
        if uw>b2*2 and lw<b2*0.5 and c2<h2: pats.append({"name":"Shooting Star","type":"BEARISH","bar":i,"desc":f"Bearish reversal at {c2:.2f} — sellers rejected price at {h2:.2f}"})
        if c1<o1 and c2>o2 and o2<=c1 and c2>=o1 and b2>b1: pats.append({"name":"Bullish Engulfing","type":"BULLISH","bar":i,"desc":f"Bullish reversal — {c2:.2f} candle engulfs prior {c1:.2f} bear candle with {b2/b1:.1f}x body"})
        if c1>o1 and c2<o2 and o2>=c1 and c2<=o1 and b2>b1: pats.append({"name":"Bearish Engulfing","type":"BEARISH","bar":i,"desc":f"Bearish reversal — {c2:.2f} candle engulfs prior bull candle, sellers took over"})
        if b2/rng>0.88 and c2>o2: pats.append({"name":"Bullish Marubozu","type":"BULLISH","bar":i,"desc":f"Pure bullish momentum at {c2:.2f} — no wicks, buyers in full control"})
        if b2/rng>0.88 and c2<o2: pats.append({"name":"Bearish Marubozu","type":"BEARISH","bar":i,"desc":f"Pure bearish momentum at {c2:.2f} — sellers dominated entire session"})
        if b2<rng*0.05 and lw>rng*0.6: pats.append({"name":"Dragonfly Doji","type":"BULLISH","bar":i,"desc":f"Bullish signal at {c2:.2f} — buyers pushed back from lows of {l2:.2f}"})
        if b2<rng*0.05 and uw>rng*0.6: pats.append({"name":"Gravestone Doji","type":"BEARISH","bar":i,"desc":f"Bearish signal at {c2:.2f} — rejected from highs of {h2:.2f}"})
        if i>=2:
            o0,c0=o[i-2],c[i-2]; b0=abs(c0-o0)
            if c0<o0 and b1<b0*0.35 and c2>o2 and c2>=(o0+c0)/2: pats.append({"name":"Morning Star","type":"BULLISH","bar":i,"desc":"3-candle bullish reversal — bear exhaustion followed by strong bull"})
            if c0>o0 and b1<b0*0.35 and c2<o2 and c2<=(o0+c0)/2: pats.append({"name":"Evening Star","type":"BEARISH","bar":i,"desc":"3-candle bearish reversal — bull exhaustion followed by strong bear"})
    seen=set(); unique=[]
    for p in pats:
        if p["name"] not in seen: seen.add(p["name"]); unique.append(p)
    return unique[:8]

# ── DeepSeek AI Analysis ──────────────────────────────────────────────────────
def _deepseek_analysis(sym:str, name:str, ind:dict) -> dict:
    ds_key=_get_key("DEEPSEEK_API_KEY")
    groq_key=_get_key("GROQ_API_KEY")

    p=ind.get("price",0); rsi=ind.get("rsi",50); trend=ind.get("trend","?")
    pats=[x["name"] for x in ind.get("patterns",[])[:5]]
    vp_top=sorted(ind.get("vp",[])[:3],key=lambda x:-x["vol"])

    prompt=f"""You are SAGE, an elite AI trading analyst. Analyze {name} ({sym}) comprehensively.

TECHNICAL DATA:
Price: {p:.4f} | Open: {ind.get('open',0):.4f} | High: {ind.get('high',0):.4f} | Low: {ind.get('low',0):.4f}
RSI(14): {rsi:.1f} | StochRSI: {ind.get('stoch_rsi',50):.1f} | Trend: {trend}
EMA9: {ind.get('ema9',0):.4f} | EMA20: {ind.get('ema20',0):.4f} | EMA50: {ind.get('ema50',0):.4f} | EMA200: {ind.get('ema200',0):.4f}
MACD: {ind.get('macd',0):.4f} | Signal: {ind.get('macd_signal',0):.4f} | Histogram: {ind.get('macd_hist',0):.4f}
BB Upper: {ind.get('bb_upper',0):.4f} | BB Mid: {ind.get('bb_mid',0):.4f} | BB Lower: {ind.get('bb_lower',0):.4f}
ATR(14): {ind.get('atr',0):.4f} | VWAP: {ind.get('vwap',0):.4f} | Volume Ratio: {ind.get('vol_ratio',1):.2f}x
Support Levels: {ind.get('supports',[])} | Resistance Levels: {ind.get('resistances',[])}
Fibonacci Levels: {ind.get('fib',{})}
Candlestick Patterns Detected: {pats}
High Volume Price Zones: {[(v['price'],round(v['vol']/1e6,1)) for v in vp_top]}

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "overall_bias": "BULLISH",
  "bias_color": "#26a69a",
  "confidence": 78,
  "summary": "2-sentence clear analysis",
  "entry_zone": {{"price": 0, "reason": "specific data-backed reason with actual price"}},
  "stop_loss": {{"price": 0, "reason": "below key support / invalidation level"}},
  "targets": [{{"price": 0, "label": "T1", "reason": "next resistance at X"}}, {{"price": 0, "label": "T2", "reason": ""}}],
  "risk_reward": "1:2.5",
  "trade_quality": "EXCELLENT",
  "ai_drawings": [
    {{"type": "support_zone", "price": 0, "price2": 0, "color": "#26a69a", "label": "Key Support", "reason": "price bounced 3 times from this zone with above-avg volume"}},
    {{"type": "resistance_zone", "price": 0, "price2": 0, "color": "#ef5350", "label": "Key Resistance", "reason": "price rejected here twice in last month"}},
    {{"type": "trendline", "start_price": 0, "end_price": 0, "color": "#2962ff", "label": "Uptrend Line", "reason": "connecting higher lows since X date"}},
    {{"type": "pattern_zone", "price": 0, "price2": 0, "color": "#9c27b0", "label": "Pattern Name", "reason": "why this pattern is significant here"}}
  ],
  "indicator_signals": {{
    "RSI": "value and what it means",
    "MACD": "bullish/bearish + histogram direction",
    "EMA_Cross": "price vs EMA relationship",
    "BB": "position within Bollinger Bands",
    "Volume": "ratio and conviction",
    "VWAP": "above/below and significance",
    "StochRSI": "overbought/oversold reading"
  }},
  "candlestick_analysis": [
    {{"pattern": "pattern name", "significance": "why this matters at this price level", "action": "what trader should do"}}
  ],
  "volume_analysis": "detailed volume profile analysis — what HVN/LVN zones tell us",
  "support_resistance_analysis": "detailed explanation of each S/R level and why it matters",
  "voice_script": "60-80 word spoken analysis in conversational Hindi+English: mention specific prices, why each level was drawn, what the setup means. Sound like expert trader explaining to a student.",
  "fundamental_summary": "2-3 sentence business/sector context for this stock",
  "ai_report_html": "HTML snippet (no full page, just content div) showing a colourful book-page style analysis report. Use inline styles. Include: price action, indicator readings, pattern analysis, S/R levels, trade setup. Make it visually rich with colored sections, tables, and data. No JavaScript.",
  "multi_timeframe": {{"daily": "", "hourly": "", "intraday": ""}},
  "risk_note": "specific risk to watch"
}}"""

    # Try DeepSeek first, then Groq fallback
    for api_url, api_key, model in [
        (DEEPSEEK_URL, ds_key, DEEPSEEK_MODEL),
        (GROQ_URL, groq_key, GROQ_MODEL),
    ]:
        if not api_key: continue
        try:
            r=requests.post(api_url,
                headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"user","content":prompt}],
                      "temperature":0.2,"max_tokens":2000},timeout=30)
            raw=r.json()["choices"][0]["message"]["content"].strip()
            if "```json" in raw: raw=raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw: raw=raw.split("```")[1].split("```")[0].strip()
            result=json.loads(raw)
            result["_api_used"]=("DeepSeek" if api_url==DEEPSEEK_URL else "Groq")
            return result
        except Exception as e:
            continue
    return _rule_based_analysis(sym,name,ind)

def _rule_based_analysis(sym:str, name:str, ind:dict) -> dict:
    p=ind.get("price",0); rsi=ind.get("rsi",50); trend=ind.get("trend","SIDEWAYS")
    vr=ind.get("vol_ratio",1.0); sup=ind.get("supports",[]); res=ind.get("resistances",[])
    if trend=="BULLISH" and rsi<70: bias="BULLISH"; bc="#26a69a"
    elif trend=="BEARISH" and rsi>30: bias="BEARISH"; bc="#ef5350"
    else: bias="NEUTRAL"; bc="#f59e0b"
    entry=sup[0] if sup else p*0.99; sl=sup[1] if len(sup)>1 else p*0.97
    t1=res[0] if res else p*1.03; t2=res[1] if len(res)>1 else p*1.06
    rr=(t1-entry)/(entry-sl) if entry-sl>0 else 1.5
    tq="GOOD" if rr>=1.5 else "AVERAGE"
    pats=ind.get("patterns",[])
    pat_str=", ".join([x["name"] for x in pats[:3]]) or "None detected"
    report_html=f"""<div style="font-family:Georgia,serif;padding:16px;background:linear-gradient(135deg,#0d1117,#161b22);border-radius:12px;color:#e6edf3;">
<h2 style="color:#58a6ff;border-bottom:2px solid #21262d;padding-bottom:8px;">📊 {name} — AI Analysis Report</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0;">
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;">
<div style="color:#7d8590;font-size:11px;text-transform:uppercase;font-weight:700;">Current Price</div>
<div style="font-size:24px;font-weight:900;color:{bc};">{p:.4f}</div>
<div style="color:{bc};font-size:12px;font-weight:700;">{bias}</div>
</div>
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;">
<div style="color:#7d8590;font-size:11px;text-transform:uppercase;font-weight:700;">Indicators</div>
<div style="font-size:12px;line-height:1.8;color:#e6edf3;">RSI: <b style="color:{'#26a69a' if rsi<40 else '#ef5350' if rsi>60 else '#f59e0b'};">{rsi:.0f}</b> · Vol: <b>{vr:.1f}x</b><br>Trend: <b style="color:{bc};">{trend}</b></div>
</div>
</div>
<table style="width:100%;border-collapse:collapse;margin:8px 0;">
<tr style="background:#21262d;"><th style="padding:6px 10px;text-align:left;color:#58a6ff;font-size:11px;">LEVEL</th><th style="padding:6px 10px;color:#58a6ff;font-size:11px;">PRICE</th><th style="padding:6px 10px;color:#58a6ff;font-size:11px;">SIGNIFICANCE</th></tr>
<tr style="border-bottom:1px solid #21262d;"><td style="padding:5px 10px;color:#26a69a;font-weight:600;">Entry Zone</td><td style="padding:5px 10px;font-family:monospace;">{entry:.4f}</td><td style="padding:5px 10px;color:#8b949e;font-size:11px;">Near key support</td></tr>
<tr style="border-bottom:1px solid #21262d;"><td style="padding:5px 10px;color:#ef5350;font-weight:600;">Stop Loss</td><td style="padding:5px 10px;font-family:monospace;">{sl:.4f}</td><td style="padding:5px 10px;color:#8b949e;font-size:11px;">Below support — invalidation</td></tr>
<tr style="border-bottom:1px solid #21262d;"><td style="padding:5px 10px;color:#2962ff;font-weight:600;">Target 1</td><td style="padding:5px 10px;font-family:monospace;">{t1:.4f}</td><td style="padding:5px 10px;color:#8b949e;font-size:11px;">Next resistance</td></tr>
<tr><td style="padding:5px 10px;color:#9c27b0;font-weight:600;">Target 2</td><td style="padding:5px 10px;font-family:monospace;">{t2:.4f}</td><td style="padding:5px 10px;color:#8b949e;font-size:11px;">Extended target</td></tr>
</table>
<div style="background:#1c2128;border:1px solid #30363d;border-radius:8px;padding:10px;margin-top:8px;">
<div style="color:#f0883e;font-weight:700;font-size:11px;margin-bottom:6px;">🕯️ PATTERNS DETECTED</div>
<div style="color:#e6edf3;font-size:12px;">{pat_str}</div>
</div>
<div style="background:#122017;border:1px solid #1a3022;border-radius:8px;padding:8px;margin-top:8px;font-size:10px;color:#7d8590;">⚠️ Educational purposes only. Not financial advice. All trading involves risk.</div>
</div>"""
    return {
        "overall_bias":bias,"bias_color":bc,"confidence":62,
        "summary":f"{name} shows {bias} bias. RSI {rsi:.0f}, trend {trend}, volume {vr:.1f}x average.",
        "entry_zone":{"price":round(entry,4),"reason":"Near key support level"},
        "stop_loss":{"price":round(sl,4),"reason":"Below major support"},
        "targets":[{"price":round(t1,4),"label":"T1","reason":"Next resistance"},
                   {"price":round(t2,4),"label":"T2","reason":"Extended target"}],
        "risk_reward":f"1:{rr:.1f}","trade_quality":tq,
        "ai_drawings":[
            {"type":"support_zone","price":round(sup[0],4) if sup else round(p*0.98,4),
             "price2":round((sup[0])*0.995,4) if sup else round(p*0.975,4),
             "color":"#26a69a","label":"Support Zone","reason":"Pivot low — price bounced here"},
            {"type":"resistance_zone","price":round(res[0],4) if res else round(p*1.02,4),
             "price2":round((res[0])*1.005,4) if res else round(p*1.025,4),
             "color":"#ef5350","label":"Resistance Zone","reason":"Pivot high — price rejected here"},
        ],
        "indicator_signals":{
            "RSI":f"{rsi:.0f} — {'Oversold' if rsi<40 else 'Overbought' if rsi>70 else 'Neutral'}",
            "MACD":"Bullish" if ind.get("macd_hist",0)>0 else "Bearish",
            "EMA_Cross":f"Price {'above' if p>ind.get('ema20',p) else 'below'} EMA20",
            "BB":f"{'Near upper' if p>ind.get('bb_upper',p)*0.99 else 'Near lower' if p<ind.get('bb_lower',p)*1.01 else 'Mid-band'}",
            "Volume":f"{vr:.1f}x avg","VWAP":f"{'Above' if p>ind.get('vwap',p) else 'Below'} VWAP",
            "StochRSI":f"{ind.get('stoch_rsi',50):.0f}"},
        "candlestick_analysis":[{"pattern":x["name"],"significance":x.get("desc",""),"action":"Monitor for confirmation"} for x in pats[:3]],
        "volume_analysis":f"Highest volume near {sup[0] if sup else p:.2f} — strong demand zone",
        "support_resistance_analysis":f"Support at {', '.join([str(round(x,2)) for x in sup[:2]])}, Resistance at {', '.join([str(round(x,2)) for x in res[:2]])}",
        "voice_script":f"Main {name} ka chart dekh raha hoon. Current price {p:.2f} hai. RSI {rsi:.0f} — {'oversold zone mein hai' if rsi<40 else 'overbought zone mein hai' if rsi>70 else 'neutral zone mein hai'}. Trend {trend} dikh raha hai. Volume average se {vr:.1f} guna hai. Entry {entry:.2f} ke paas hai, stop loss {sl:.2f} pe. Target ek {t1:.2f} aur target do {t2:.2f} hai.",
        "fundamental_summary":f"{name} is a major company in its sector with active market participation.",
        "ai_report_html":report_html,
        "multi_timeframe":{"daily":f"Daily: {trend}","hourly":"See 1H chart","intraday":"See 15m"},
        "risk_note":"Confirm with broader market conditions","_api_used":"Rule-based"
    }

# ══════════════════════════════════════════════════════════════════════════════
# CHART HTML with AI drawings overlay
# ══════════════════════════════════════════════════════════════════════════════
CHART_H=720

def _build_ai_chart_html(df:pd.DataFrame, ind:dict, ai:dict, sym:str, name:str) -> str:
    candle_data=[]; vol_data=[]
    if not df.empty:
        for idx,row in df.tail(200).iterrows():
            ts=int(pd.Timestamp(idx).timestamp())
            o=round(float(row["Open"]),4); h=round(float(row["High"]),4)
            l=round(float(row["Low"]),4);  c=round(float(row["Close"]),4)
            candle_data.append({"time":ts,"open":o,"high":h,"low":l,"close":c})
            vol_data.append({"time":ts,"value":int(row["Volume"]),
                "color":"rgba(38,166,154,0.5)" if c>=o else "rgba(239,83,80,0.5)"})

    bc=ai.get("bias_color","#f59e0b")
    entry_p=ai.get("entry_zone",{}).get("price",0)
    sl_p=ai.get("stop_loss",{}).get("price",0)
    tgts=ai.get("targets",[])
    t1_p=tgts[0]["price"] if tgts else 0
    t2_p=tgts[1]["price"] if len(tgts)>1 else 0
    supp=ind.get("supports",[]); res=ind.get("resistances",[])
    vwap=ind.get("vwap",0); ema20=ind.get("ema20",0); ema50=ind.get("ema50",0)
    ema200=ind.get("ema200",0); fib=ind.get("fib",{})
    cur=ind.get("price",0); rsi=ind.get("rsi",50)
    macd_up=ind.get("macd_hist",0)>0; vol_r=ind.get("vol_ratio",1)
    atr=ind.get("atr",0); bias=ai.get("overall_bias","NEUTRAL")
    conf=ai.get("confidence",65); rr=ai.get("risk_reward","—"); tq=ai.get("trade_quality","—")
    voice=json.dumps(ai.get("voice_script",""))
    api_used=ai.get("_api_used","AI")

    # Pattern markers
    markers=[]
    if candle_data:
        for pt in ind.get("patterns",[])[:6]:
            bi=min(pt.get("bar",len(candle_data)-1),len(candle_data)-1)
            if 0<=bi<len(candle_data):
                cdl=candle_data[bi]
                pc2={"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#f59e0b"}.get(pt["type"],"#f59e0b")
                ps={"BULLISH":"arrowUp","BEARISH":"arrowDown","NEUTRAL":"circle"}.get(pt["type"],"circle")
                pp={"BULLISH":"belowBar","BEARISH":"aboveBar","NEUTRAL":"inBar"}.get(pt["type"],"inBar")
                markers.append({"time":cdl["time"],"position":pp,"color":pc2,"shape":ps,"text":pt["name"][:14]})

    footer_h=32; body_h=CHART_H-footer_h

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#131722;color:#d1d4dc;font-family:'Trebuchet MS',sans-serif;
  width:100%;height:{CHART_H}px;overflow:hidden;}}
#root{{width:100%;height:{CHART_H}px;display:flex;flex-direction:column;}}
#chart-wrap{{position:relative;flex:1;height:{body_h}px;}}
#chart-div{{width:100%;height:{body_h}px;}}
#footer{{height:{footer_h}px;background:#1e222d;border-top:1px solid #2a2e39;
  display:flex;align-items:center;padding:0 12px;gap:0;font-size:11px;flex-shrink:0;}}
/* Overlay legend */
#legend{{position:absolute;top:8px;left:8px;z-index:20;
  background:rgba(19,23,34,0.94);border:1px solid #2a2e39;border-radius:8px;padding:8px 12px;}}
#legend .ls{{font-size:13px;font-weight:700;color:#d1d4dc;}}
#legend .lp{{font-size:20px;font-weight:900;color:{bc};font-family:monospace;margin:2px 0;}}
#legend .lb{{display:inline-block;padding:2px 9px;border-radius:10px;font-size:10px;font-weight:700;
  background:{bc}22;color:{bc};border:1px solid {bc}44;}}
/* AI Levels panel */
#lvls{{position:absolute;top:8px;right:8px;z-index:20;
  background:rgba(19,23,34,0.94);border:1px solid #2a2e39;border-radius:8px;padding:8px 12px;min-width:150px;}}
#lvls .lh{{font-size:9px;font-weight:700;color:#6a6e7a;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;}}
#lvls .lr{{font-size:11px;display:flex;justify-content:space-between;gap:8px;padding:2px 0;border-bottom:1px solid #1a1e2d;}}
/* API badge */
#api-badge{{position:absolute;top:8px;left:50%;transform:translateX(-50%);z-index:20;
  background:rgba(19,23,34,0.9);border:1px solid #2a2e39;border-radius:8px;padding:4px 10px;
  font-size:10px;color:#6a6e7a;}}
/* Voice panel */
#vp{{position:absolute;bottom:{footer_h+6}px;left:8px;right:8px;z-index:20;
  background:rgba(19,23,34,0.96);border:1px solid #2962ff44;border-radius:8px;
  padding:10px 14px;display:none;max-height:80px;overflow:hidden;}}
#vp.vis{{display:block;}}
#vp-text{{font-size:11px;color:#9598a1;line-height:1.5;}}
#vbtn{{position:absolute;bottom:{footer_h+6}px;right:8px;z-index:21;
  width:34px;height:34px;background:#2962ff;border:none;border-radius:50%;
  color:white;font-size:15px;cursor:pointer;display:flex;align-items:center;justify-content:center;
  box-shadow:0 2px 14px rgba(41,98,255,0.5);}}
#vbtn:hover{{background:#1e56e8;}}
</style>
</head><body>
<div id="root">
  <div id="chart-wrap">
    <div id="chart-div"></div>
    <div id="legend">
      <div class="ls">{sym}</div>
      <div class="lp">{cur:.4f}</div>
      <div class="lb">{bias} · {conf}%</div>
    </div>
    <div id="api-badge">⬡ SAGE AI · {api_used}</div>
    <div id="lvls">
      <div class="lh">AI Levels</div>
      <div class="lr"><span style="color:#26a69a;font-weight:600;">Entry</span><span style="color:#26a69a;font-family:monospace;">{entry_p:.4f}</span></div>
      <div class="lr"><span style="color:#ef5350;font-weight:600;">Stop</span><span style="color:#ef5350;font-family:monospace;">{sl_p:.4f}</span></div>
      {'<div class="lr"><span style="color:#2962ff;">T1</span><span style="color:#2962ff;font-family:monospace;">'+str(round(t1_p,4))+'</span></div>' if t1_p else ''}
      {'<div class="lr"><span style="color:#9c27b0;">T2</span><span style="color:#9c27b0;font-family:monospace;">'+str(round(t2_p,4))+'</span></div>' if t2_p else ''}
      <div class="lr" style="border:none;"><span style="color:#6a6e7a;font-size:9px;">R:R</span><span style="font-weight:700;">{rr}</span></div>
    </div>
    <div id="vp"><div style="display:flex;align-items:center;gap:6px;"><span style="color:#2962ff;font-weight:700;font-size:11px;">🔊 SAGE Voice Analysis</span><span id="vst" style="color:#6a6e7a;font-size:10px;margin-left:4px;">Tap to hear</span></div></div>
    <button id="vbtn" onclick="doVoice()" title="AI Voice Analysis">🔊</button>
  </div>
  <div id="footer">
    <span>RSI: <b style="color:{'#26a69a' if rsi<50 else '#ef5350'}">{rsi:.0f}</b></span>&nbsp;|&nbsp;
    <span>MACD: <b style="color:{'#26a69a' if macd_up else '#ef5350'}">{'▲' if macd_up else '▼'}</b></span>&nbsp;|&nbsp;
    <span>Vol: <b>{vol_r:.1f}x</b></span>&nbsp;|&nbsp;
    <span>ATR: <b>{atr:.4f}</b></span>&nbsp;|&nbsp;
    <span>VWAP: <b>{vwap:.4f}</b></span>&nbsp;|&nbsp;
    <span style="color:{bc};">R:R {rr} · {tq}</span>&nbsp;|&nbsp;
    <span style="color:#4a5568;font-size:10px;">📊 Educational · Not financial advice</span>
  </div>
</div>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){{
  var H={body_h}, W;
  var candles={json.dumps(candle_data)};
  var vols={json.dumps(vol_data)};
  var supp={json.dumps(supp)};
  var ress={json.dumps(res)};
  var fib={json.dumps(fib)};
  var markers={json.dumps(markers)};
  var voice={voice};

  function init(){{
    var el=document.getElementById('chart-div');
    if(!el) return;
    W=el.clientWidth||window.innerWidth;
    var chart=LightweightCharts.createChart(el,{{
      width:W, height:H,
      layout:{{background:{{type:'solid',color:'#131722'}},textColor:'#d1d4dc'}},
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
      wickUpColor:'#26a69a',wickDownColor:'#ef5350',
    }});
    if(candles.length) cs.setData(candles);
    var vs=chart.addHistogramSeries({{priceScaleId:'vol',scaleMargins:{{top:0.78,bottom:0}}}});
    chart.priceScale('vol').applyOptions({{scaleMargins:{{top:0.78,bottom:0}}}});
    if(vols.length) vs.setData(vols);
    if(markers.length) cs.setMarkers(markers);
    // Support lines (green dashed)
    supp.forEach(function(s){{cs.createPriceLine({{price:s,color:'#26a69a',lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'S'}});}});
    // Resistance lines (red dashed)
    ress.forEach(function(r){{cs.createPriceLine({{price:r,color:'#ef5350',lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'R'}});}});
    // Fibonacci
    var fc={{'0.236':'#7986cb','0.382':'#26a69a','0.500':'#fbbf24','0.618':'#ef5350','0.786':'#e040fb'}};
    Object.keys(fib).forEach(function(k){{if(fib[k])cs.createPriceLine({{price:fib[k],color:fc[k]||'#aaa',lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'Fib '+k}});}});
    // Entry/SL/T1/T2
    if({int(bool(entry_p))}) cs.createPriceLine({{price:{entry_p or 0},color:'#26a69a',lineWidth:2,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:'ENTRY'}});
    if({int(bool(sl_p))}) cs.createPriceLine({{price:{sl_p or 0},color:'#ef5350',lineWidth:2,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:'STOP'}});
    if({int(bool(t1_p))}) cs.createPriceLine({{price:{t1_p or 0},color:'#2962ff',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'T1'}});
    if({int(bool(t2_p))}) cs.createPriceLine({{price:{t2_p or 0},color:'#9c27b0',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'T2'}});
    if({int(bool(vwap))}) cs.createPriceLine({{price:{vwap or 0},color:'#fbbf24',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'VWAP'}});
    if({int(bool(ema20))}) cs.createPriceLine({{price:{ema20 or 0},color:'#2196f3',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:false,title:'EMA20'}});
    if({int(bool(ema50))}) cs.createPriceLine({{price:{ema50 or 0},color:'#ff9800',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:false,title:'EMA50'}});
    if({int(bool(ema200))}) cs.createPriceLine({{price:{ema200 or 0},color:'#e91e63',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:false,title:'EMA200'}});
    chart.timeScale().fitContent();
    window.addEventListener('resize',function(){{
      var nw=document.getElementById('chart-div').clientWidth||window.innerWidth;
      chart.applyOptions({{width:nw,height:H}});
    }});
  }}

  window.doVoice=function(){{
    var vp=document.getElementById('vp');
    var vst2=document.getElementById('vst');
    if(!vp) return;
    if(!vp.classList.contains('vis')){{
      vp.classList.add('vis');
      if(vst2) vst2.textContent='Speaking...';
      if('speechSynthesis' in window){{
        window.speechSynthesis.cancel();
        var u=new SpeechSynthesisUtterance(voice||'Analysis ready');
        u.lang='hi-IN'; u.rate=0.9; u.pitch=1;
        var voices=window.speechSynthesis.getVoices();
        var hv=voices.find(function(v){{return v.lang==='hi-IN';}});
        var ev=voices.find(function(v){{return v.lang.startsWith('en');}});
        if(hv) u.voice=hv; else if(ev) u.voice=ev;
        window.speechSynthesis.speak(u);
      }}
    }} else {{
      vp.classList.remove('vis');
      if('speechSynthesis' in window) window.speechSynthesis.cancel();
    }}
  }};

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);
  else init();
}})();
</script>
</body></html>"""

# ══════════════════════════════════════════════════════════════════════════════
# AI ANALYSIS REPORT (colorful book-page style)
# ══════════════════════════════════════════════════════════════════════════════
def _render_ai_report(ai:dict, ind:dict, name:str):
    """Render colorful book-page style AI analysis report."""
    bc=ai.get("bias_color","#f59e0b")
    bias=ai.get("overall_bias","NEUTRAL"); conf=ai.get("confidence",65)
    rr=ai.get("risk_reward","—"); tq=ai.get("trade_quality","—")
    tq_c={"EXCELLENT":"#26a69a","GOOD":"#2962ff","AVERAGE":"#f59e0b","POOR":"#ef5350"}.get(tq,"#6a6e7a")

    # If AI returned HTML report, use it
    report_html=ai.get("ai_report_html","")
    if report_html and len(report_html)>200:
        st.markdown(report_html, unsafe_allow_html=True)
        return

    # Build our own colorful report
    entry_p=ai.get("entry_zone",{}).get("price",0)
    entry_r=ai.get("entry_zone",{}).get("reason","")
    sl_p=ai.get("stop_loss",{}).get("price",0)
    sl_r=ai.get("stop_loss",{}).get("reason","")
    tgts=ai.get("targets",[])
    ind_sig=ai.get("indicator_signals",{})
    cs_analysis=ai.get("candlestick_analysis",[])
    patterns=ind.get("patterns",[])
    mtf=ai.get("multi_timeframe",{})
    vol_note=ai.get("volume_analysis","")
    sr_note=ai.get("support_resistance_analysis","")
    fund=ai.get("fundamental_summary","")
    risk=ai.get("risk_note","")
    api_used=ai.get("_api_used","AI")

    # Big bias card
    st.markdown(f"""<div style="background:linear-gradient(135deg,{bc}22,{bc}08);
    border:2px solid {bc}44;border-radius:12px;padding:14px 16px;margin-bottom:10px;
    display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
      <div>
        <div style="font-size:28px;font-weight:900;color:{bc};">{bias}</div>
        <div style="color:#6a6e7a;font-size:10px;">AI Confidence</div>
        <div style="background:#0e1117;border-radius:100px;height:6px;width:100px;margin-top:3px;">
          <div style="background:{bc};height:6px;border-radius:100px;width:{conf}%;"></div>
        </div>
      </div>
      <div style="flex:1;">
        <div style="font-size:12px;color:#9598a1;line-height:1.6;">{ai.get('summary','')}</div>
      </div>
      <div style="text-align:right;">
        <div style="color:#6a6e7a;font-size:10px;">Risk:Reward</div>
        <div style="font-size:18px;font-weight:900;color:#d1d4dc;">{rr}</div>
        <div style="font-size:11px;color:{tq_c};font-weight:700;">{tq}</div>
        <div style="font-size:9px;color:#6a6e7a;margin-top:2px;">via {api_used}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # 2-col layout: Trade Setup + Indicators
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""<div style="color:#26a69a;font-size:11px;font-weight:700;
        text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">
        📐 TRADE SETUP</div>""", unsafe_allow_html=True)
        rows=[("Entry",entry_p,"#26a69a",entry_r),("Stop Loss",sl_p,"#ef5350",sl_r)]
        for t in tgts[:2]: rows.append((t["label"],t["price"],"#2962ff" if t["label"]=="T1" else "#9c27b0",t.get("reason","")))
        for label,price,color,reason in rows:
            if price: st.markdown(f"""<div style="background:{color}11;border:1px solid {color}33;
            border-radius:6px;padding:7px 10px;margin:4px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="color:{color};font-weight:700;font-size:12px;">{label}</span>
              <span style="color:{color};font-family:monospace;font-size:14px;font-weight:900;">{price:.4f}</span>
            </div>
            <div style="color:#6a6e7a;font-size:10px;margin-top:2px;">{reason[:60]}</div>
            </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("""<div style="color:#2962ff;font-size:11px;font-weight:700;
        text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">
        📊 INDICATOR SIGNALS</div>""", unsafe_allow_html=True)
        for k,v in ind_sig.items():
            ic="#26a69a" if any(w in str(v).lower() for w in ["bull","above","oversold","strong","confirm"]) \
               else "#ef5350" if any(w in str(v).lower() for w in ["bear","below","overbought","weak"]) \
               else "#f59e0b"
            st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;
            padding:4px 8px;border-bottom:1px solid #1a1e2d;font-size:11px;">
            <span style="color:#6a6e7a;font-weight:600;">{k}</span>
            <span style="color:{ic};font-size:10px;">{str(v)[:35]}</span></div>""", unsafe_allow_html=True)

    # Volume + S/R Analysis
    if vol_note or sr_note:
        vc1,vc2=st.columns(2)
        with vc1:
            if vol_note:
                st.markdown(f"""<div style="background:#1a1e2d;border-left:3px solid #2962ff;
                border-radius:0 8px 8px 0;padding:10px 12px;margin-top:8px;">
                <div style="color:#2962ff;font-size:11px;font-weight:700;margin-bottom:4px;">📈 VOLUME ANALYSIS</div>
                <div style="color:#9598a1;font-size:11px;line-height:1.6;">{vol_note[:200]}</div></div>""", unsafe_allow_html=True)
        with vc2:
            if sr_note:
                st.markdown(f"""<div style="background:#1a1e2d;border-left:3px solid #26a69a;
                border-radius:0 8px 8px 0;padding:10px 12px;margin-top:8px;">
                <div style="color:#26a69a;font-size:11px;font-weight:700;margin-bottom:4px;">🎯 SUPPORT / RESISTANCE</div>
                <div style="color:#9598a1;font-size:11px;line-height:1.6;">{sr_note[:200]}</div></div>""", unsafe_allow_html=True)

    # Candlestick pattern deep-dive
    if cs_analysis or patterns:
        st.markdown("""<div style="color:#f0883e;font-size:11px;font-weight:700;
        text-transform:uppercase;letter-spacing:0.08em;margin:10px 0 6px;">
        🕯️ CANDLESTICK PATTERN ANALYSIS</div>""", unsafe_allow_html=True)
        pcs=st.columns(min(len(cs_analysis)+len(patterns),4))
        shown=0
        for item in cs_analysis[:2]:
            with pcs[shown%len(pcs)]:
                st.markdown(f"""<div style="background:#1c1600;border:1px solid #f0883e33;
                border-radius:8px;padding:8px 10px;height:100%;">
                <div style="color:#f0883e;font-weight:700;font-size:11px;">{item.get('pattern','')}</div>
                <div style="color:#9598a1;font-size:10px;margin-top:3px;line-height:1.4;">{item.get('significance','')[:80]}</div>
                <div style="color:#26a69a;font-size:10px;margin-top:4px;font-weight:600;">→ {item.get('action','')[:40]}</div>
                </div>""", unsafe_allow_html=True)
            shown+=1
        for pat in patterns[:2]:
            if shown>=len(pcs): break
            pc={"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#f59e0b"}.get(pat["type"],"#6a6e7a")
            with pcs[shown%len(pcs)]:
                st.markdown(f"""<div style="background:{pc}11;border:1px solid {pc}33;
                border-radius:8px;padding:8px 10px;height:100%;">
                <div style="color:{pc};font-weight:700;font-size:11px;">{pat['name']}</div>
                <div style="color:#9598a1;font-size:10px;margin-top:3px;line-height:1.4;">{pat.get('desc','')[:80]}</div>
                </div>""", unsafe_allow_html=True)
            shown+=1

    # Multi-timeframe
    if mtf:
        st.markdown("""<div style="color:#9c27b0;font-size:11px;font-weight:700;
        text-transform:uppercase;letter-spacing:0.08em;margin:10px 0 6px;">
        ⏱️ MULTI-TIMEFRAME CONFLUENCE</div>""", unsafe_allow_html=True)
        mc=st.columns(3)
        for i,(tf_k,tf_v) in enumerate(mtf.items()):
            with mc[i%3]:
                st.markdown(f"""<div style="background:#1a0d2e;border:1px solid #9c27b033;
                border-radius:8px;padding:8px 10px;text-align:center;">
                <div style="color:#9c27b0;font-size:10px;font-weight:700;">{tf_k.upper()}</div>
                <div style="color:#9598a1;font-size:11px;margin-top:4px;">{str(tf_v)[:50]}</div>
                </div>""", unsafe_allow_html=True)

    # Fundamental summary
    if fund:
        st.markdown(f"""<div style="background:#0d1117;border:1px solid #30363d;
        border-radius:8px;padding:10px 14px;margin-top:8px;font-size:11px;color:#9598a1;line-height:1.6;">
        <span style="color:#58a6ff;font-weight:700;">🏢 Fundamental Context: </span>{fund}</div>""", unsafe_allow_html=True)

    # Risk note
    if risk:
        st.markdown(f"""<div style="background:#1a1500;border:1px solid #3d2e00;border-radius:8px;
        padding:8px 14px;margin-top:8px;font-size:11px;color:#8b8070;">
        ⚠️ <b>Risk Note:</b> {risk}</div>""", unsafe_allow_html=True)

    # Disclaimer
    st.markdown("""<div style="background:#0e1117;border-radius:8px;padding:6px 10px;
    margin-top:8px;font-size:9px;color:#4a5568;text-align:center;">
    📊 Demo / Paper Trading Only — No Real Money · Past performance ≠ future results ·
    This is AI-generated educational content, not financial advice · Always use stop-loss
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SPLASH SCREEN
# ══════════════════════════════════════════════════════════════════════════════
def _render_splash():
    st.markdown(f"""<style>
    header,footer,section[data-testid="stSidebar"],
    div[data-testid="stDecoration"],div[data-testid="stToolbar"],
    .stDeployButton{{display:none!important;}}
    .block-container{{padding:0!important;max-width:100vw!important;}}
    </style>
    <div id="splash" style="position:fixed;top:0;left:0;width:100vw;height:100vh;
    background:linear-gradient(135deg,#0a0e1a,#131722,#0a0e1a);
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    z-index:9999;animation:fadeIn 0.5s ease;">
      <style>
        @keyframes fadeIn{{from{{opacity:0;transform:scale(0.95)}}to{{opacity:1;transform:scale(1)}}}}
        @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}
        @keyframes spin{{from{{transform:rotate(0)}}to{{transform:rotate(360deg)}}}}
      </style>
      <img src="{LOGO_URL}" style="height:80px;border-radius:16px;
        box-shadow:0 0 40px rgba(41,98,255,0.5);margin-bottom:20px;
        animation:fadeIn 0.8s ease;" onerror="this.style.display='none'">
      <div style="font-size:28px;font-weight:900;color:#d1d4dc;letter-spacing:0.05em;margin-bottom:4px;">
        FinSage <span style="color:#2962ff;">AI</span>
      </div>
      <div style="color:#6a6e7a;font-size:12px;letter-spacing:0.2em;margin-bottom:30px;">
        STOCK · CRYPTO · FOREX · AI-POWERED
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <div style="width:16px;height:16px;border:2px solid #2962ff;border-top-color:transparent;
          border-radius:50%;animation:spin 0.8s linear infinite;"></div>
        <span style="color:#6a6e7a;font-size:11px;">Loading market data...</span>
      </div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN TV-STYLE DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def render_tv_dashboard():
    """Main TradingView-style dashboard: Watchlist + Chart + AI Analysis."""

    st.markdown("""<style>
    header[data-testid="stHeader"],footer,
    div[data-testid="stDecoration"],div[data-testid="stToolbar"],
    div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}
    .block-container{padding:0.2rem 0.3rem!important;max-width:100vw!important;}
    .stHorizontalBlock{gap:0!important;}
    </style>""", unsafe_allow_html=True)

    # Init state
    if "tv_selected" not in st.session_state:
        st.session_state.tv_selected = WATCHLIST[0]
    if "tv_ai_mode" not in st.session_state:
        st.session_state.tv_ai_mode = False
    if "tv_ai_result" not in st.session_state:
        st.session_state.tv_ai_result = None
    if "tv_search" not in st.session_state:
        st.session_state.tv_search = ""
    if "tv_tab" not in st.session_state:
        st.session_state.tv_tab = "stocks"

    sel = st.session_state.tv_selected

    # ── TOP BAR (TradingView style) ───────────────────────────────────────────
    st.markdown(f"""<div style="background:#1e222d;border-bottom:1px solid #2a2e39;
    padding:6px 12px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      <img src="{LOGO_URL}" style="height:28px;border-radius:6px;"
        onerror="this.style.display='none'">
      <span style="color:#d1d4dc;font-weight:800;font-size:14px;">FinSage <span style="color:#2962ff;">AI</span></span>
      <span style="background:#2962ff22;color:#2962ff;font-size:8px;padding:1px 6px;
      border-radius:8px;border:1px solid #2962ff44;font-weight:700;">AI POWERED</span>
      <div style="flex:1;"></div>
      <span style="color:#6a6e7a;font-size:10px;">🕐 {datetime.now().strftime('%H:%M IST')}</span>
    </div>""", unsafe_allow_html=True)

    # ── MAIN LAYOUT: Watchlist (left) + Chart+Analysis (right) ────────────────
    left_col, right_col = st.columns([1, 3], gap="small")

    # ── LEFT: WATCHLIST ───────────────────────────────────────────────────────
    with left_col:
        # Search bar
        search = st.text_input("🔍", placeholder="Search symbol...",
                               key="tv_search_input", label_visibility="collapsed")
        if search != st.session_state.tv_search:
            st.session_state.tv_search = search

        # Category tabs
        tab_opts = ["All","Stocks","Crypto"]
        tc = st.radio("",tab_opts, horizontal=True, key="tv_tab_radio", label_visibility="collapsed")

        # Filter watchlist
        wl = WATCHLIST
        if tc == "Stocks": wl = [x for x in WATCHLIST if x["type"]=="stock"]
        elif tc == "Crypto": wl = [x for x in WATCHLIST if x["type"]=="crypto"]
        if search:
            q=search.upper()
            wl=[x for x in wl if q in x["sym"].upper() or q in x["name"].upper()]

        # Header row
        st.markdown("""<div style="display:flex;padding:4px 8px;font-size:10px;color:#6a6e7a;
        font-weight:700;border-bottom:1px solid #2a2e39;text-transform:uppercase;
        letter-spacing:0.06em;background:#1a1e2d;border-radius:6px 6px 0 0;">
          <span style="flex:1;">Symbol</span>
          <span style="width:70px;text-align:right;">Price</span>
          <span style="width:55px;text-align:right;">Chg%</span>
        </div>""", unsafe_allow_html=True)

        # Watchlist rows
        for item in wl[:20]:
            d = _price_data(item["sym"])
            price = d.get("price",0); chg = d.get("chg",0)
            cc="#26a69a" if chg>=0 else "#ef5350"
            is_sel = sel["sym"]==item["sym"]
            bg="#1e3a2e" if is_sel else "transparent"
            border_l="3px solid #2962ff" if is_sel else "3px solid transparent"

            if st.button(
                f"{item['name'][:16]}",
                key=f"wl_{item['sym']}",
                use_container_width=True,
                help=f"{item['sym']} • {item['ex']}"
            ):
                st.session_state.tv_selected = item
                st.session_state.tv_ai_mode = False
                st.session_state.tv_ai_result = None
                st.rerun()

            # Price overlay (can't do in button, use markdown)
            st.markdown(f"""<div style="display:flex;padding:0 6px 4px 6px;font-size:11px;
            border-bottom:1px solid #1a1e2d;margin-top:-8px;">
              <span style="color:#6a6e7a;font-size:10px;flex:1;">{item['sym'].replace('.NS','')}</span>
              <span style="color:{cc};font-family:monospace;font-weight:700;">{price:.2f}</span>
              <span style="color:{cc};margin-left:6px;">{chg:+.1f}%</span>
            </div>""", unsafe_allow_html=True)

    # ── RIGHT: CHART + ANALYSIS ───────────────────────────────────────────────
    with right_col:
        sym=sel["sym"]; tv_sym=sel["tv"]; name=sel["name"]

        # Timeframe selector
        tf_c1,tf_c2,tf_c3=st.columns([4,2,1])
        with tf_c1:
            tfs=["1D","1H","15m","4H","1W","1M"]
            tf_sel=st.radio("",tfs,horizontal=True,key="tv_tf_sel",
                             index=0,label_visibility="collapsed")
        with tf_c2:
            if st.button("🤖 AI Analysis",key="tv_ai_btn",type="primary",use_container_width=True):
                st.session_state.tv_ai_mode=True
                st.session_state.tv_ai_result=None
        with tf_c3:
            if st.button("📊",key="tv_chart_btn",use_container_width=True,help="Chart only"):
                st.session_state.tv_ai_mode=False
                st.session_state.tv_ai_result=None

        tf_map={"1D":("3mo","1d"),"1H":("1mo","1h"),"15m":("5d","15m"),
                "4H":("6mo","1d"),"1W":("2y","1wk"),"1M":("5y","1mo")}
        period,interval=tf_map.get(tf_sel,("3mo","1d"))

        # Load data
        with st.spinner(f"Loading {name}..."):
            df=_ohlcv(sym,period,interval)
            ind=_compute_all(df) if not df.empty else {}

        if df.empty:
            st.error(f"❌ No data for {sym}")
            return

        # ── AI ANALYSIS MODE ──────────────────────────────────────────────────
        if st.session_state.get("tv_ai_mode"):
            # Run AI analysis if not already done
            if st.session_state.get("tv_ai_result") is None:
                with st.spinner("🤖 SAGE AI analyzing chart — drawing support/resistance, patterns, indicators..."):
                    ai_result=_deepseek_analysis(sym,name,ind)
                st.session_state.tv_ai_result=ai_result
            else:
                ai_result=st.session_state.tv_ai_result

            # Chart with AI drawings
            chart_html=_build_ai_chart_html(df,ind,ai_result,sym,name)
            components.html(chart_html,height=CHART_H+10,scrolling=False)

            # AI Analysis Report (colorful book-page)
            st.markdown(f"""<div style="background:#1e222d;border:1px solid #2a2e39;
            border-radius:8px;padding:8px 14px;margin:6px 0;display:flex;align-items:center;gap:10px;">
              <span style="color:#2962ff;font-size:14px;">🤖</span>
              <span style="color:#d1d4dc;font-weight:700;font-size:13px;">AI Analysis Report — {name}</span>
              <span style="background:#2962ff22;color:#2962ff;font-size:9px;padding:2px 7px;
              border-radius:10px;font-weight:700;">via {ai_result.get('_api_used','AI')}</span>
            </div>""", unsafe_allow_html=True)
            _render_ai_report(ai_result,ind,name)

            # Action buttons
            bc1,bc2,bc3=st.columns(3)
            with bc1:
                if st.button("🔄 Refresh AI",key="tv_ai_refresh",type="primary"):
                    st.session_state.tv_ai_result=None; st.rerun()
            with bc2:
                if st.button("📊 Chart Only",key="tv_chart_only"):
                    st.session_state.tv_ai_mode=False; st.rerun()
            with bc3:
                if ai_result:
                    report_text=f"""FinSage AI Analysis — {name} ({sym})
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}
Via: {ai_result.get('_api_used','AI')}

BIAS: {ai_result.get('overall_bias','—')} ({ai_result.get('confidence',0)}% confidence)
{ai_result.get('summary','')}

TRADE SETUP:
Entry: {ai_result.get('entry_zone',{}).get('price','—')} — {ai_result.get('entry_zone',{}).get('reason','')}
Stop Loss: {ai_result.get('stop_loss',{}).get('price','—')} — {ai_result.get('stop_loss',{}).get('reason','')}
R:R: {ai_result.get('risk_reward','—')} | Quality: {ai_result.get('trade_quality','—')}

INDICATORS:
{chr(10).join([f'{k}: {v}' for k,v in ai_result.get('indicator_signals',{}).items()])}

DISCLAIMER: Educational only. Not financial advice."""
                    st.download_button("📥 Save Report",report_text,
                        f"finsage_{sym}_{datetime.now().strftime('%Y%m%d')}.txt",
                        "text/plain",key="tv_dl_report")

        else:
            # ── PLAIN CHART MODE (TradingView widget) ─────────────────────────
            tv_tf={"1D":"D","1H":"60","15m":"15","4H":"240","1W":"W","1M":"M"}.get(tf_sel,"D")
            tv_widget=f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#131722;width:100%;height:{CHART_H}px;overflow:hidden;}}</style>
</head><body>
<div class="tradingview-widget-container" style="width:100%;height:{CHART_H}px;">
  <div id="tv_chart" style="width:100%;height:{CHART_H}px;"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({{
    "autosize": false, "width": "100%", "height": {CHART_H},
    "symbol": "{tv_sym}",
    "interval": "{tv_tf}",
    "timezone": "Asia/Kolkata",
    "theme": "dark",
    "style": "1",
    "locale": "en",
    "toolbar_bg": "#1e222d",
    "enable_publishing": false,
    "hide_top_toolbar": false,
    "hide_legend": false,
    "save_image": false,
    "container_id": "tv_chart",
    "studies": ["RSI@tv-basicstudies","MACD@tv-basicstudies","Volume@tv-basicstudies"],
    "show_popup_button": false,
    "popup_width": "1000",
    "popup_height": "650"
  }});
  </script>
</div>
</body></html>"""
            components.html(tv_widget, height=CHART_H+10, scrolling=False)

            # Click AI Analysis prompt
            st.markdown(f"""<div style="background:#1a1e2d;border:1px solid #2962ff33;border-radius:8px;
            padding:8px 14px;margin-top:6px;display:flex;align-items:center;gap:10px;">
              <span style="color:#2962ff;font-size:16px;">🤖</span>
              <span style="color:#9598a1;font-size:12px;">Click <b style="color:#2962ff;">AI Analysis</b> to automatically detect Support/Resistance, Patterns, Indicators, and get voice explanation</span>
            </div>""", unsafe_allow_html=True)
