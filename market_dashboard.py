"""
FinSage AI — Full-Stack Market Dashboard (HOME PAGE)
TradingView-identical interface + AI Analysis + Research Report
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
    try: return st.secrets.get(n) or os.environ.get(n,"")
    except: return os.environ.get(n,"")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

# ─── WATCHLIST DATA ───────────────────────────────────────────────────────────
DEFAULT_WATCHLIST = [
    {"sym":"RELIANCE.NS","tv":"NSE:RELIANCE","name":"Reliance","type":"stock","ex":"NSE"},
    {"sym":"TCS.NS","tv":"NSE:TCS","name":"TCS","type":"stock","ex":"NSE"},
    {"sym":"HDFCBANK.NS","tv":"NSE:HDFCBANK","name":"HDFC Bank","type":"stock","ex":"NSE"},
    {"sym":"INFY.NS","tv":"NSE:INFY","name":"Infosys","type":"stock","ex":"NSE"},
    {"sym":"ICICIBANK.NS","tv":"NSE:ICICIBANK","name":"ICICI Bank","type":"stock","ex":"NSE"},
    {"sym":"SBIN.NS","tv":"NSE:SBIN","name":"SBI","type":"stock","ex":"NSE"},
    {"sym":"WIPRO.NS","tv":"NSE:WIPRO","name":"Wipro","type":"stock","ex":"NSE"},
    {"sym":"BAJFINANCE.NS","tv":"NSE:BAJFINANCE","name":"Bajaj Finance","type":"stock","ex":"NSE"},
    {"sym":"TATAMOTORS.NS","tv":"NSE:TATAMOTORS","name":"Tata Motors","type":"stock","ex":"NSE"},
    {"sym":"SUNPHARMA.NS","tv":"NSE:SUNPHARMA","name":"Sun Pharma","type":"stock","ex":"NSE"},
    {"sym":"AAPL","tv":"NASDAQ:AAPL","name":"Apple","type":"stock","ex":"NASDAQ"},
    {"sym":"TSLA","tv":"NASDAQ:TSLA","name":"Tesla","type":"stock","ex":"NASDAQ"},
    {"sym":"NVDA","tv":"NASDAQ:NVDA","name":"NVIDIA","type":"stock","ex":"NASDAQ"},
    {"sym":"MSFT","tv":"NASDAQ:MSFT","name":"Microsoft","type":"stock","ex":"NASDAQ"},
    {"sym":"GOOGL","tv":"NASDAQ:GOOGL","name":"Alphabet","type":"stock","ex":"NASDAQ"},
    {"sym":"META","tv":"NASDAQ:META","name":"Meta","type":"stock","ex":"NASDAQ"},
    {"sym":"AMZN","tv":"NASDAQ:AMZN","name":"Amazon","type":"stock","ex":"NASDAQ"},
    {"sym":"BTC-USD","tv":"BINANCE:BTCUSDT","name":"Bitcoin","type":"crypto","ex":"CRYPTO"},
    {"sym":"ETH-USD","tv":"BINANCE:ETHUSDT","name":"Ethereum","type":"crypto","ex":"CRYPTO"},
    {"sym":"SOL-USD","tv":"BINANCE:SOLUSDT","name":"Solana","type":"crypto","ex":"CRYPTO"},
    {"sym":"BNB-USD","tv":"BINANCE:BNBUSDT","name":"BNB","type":"crypto","ex":"CRYPTO"},
    {"sym":"XRP-USD","tv":"BINANCE:XRPUSDT","name":"XRP","type":"crypto","ex":"CRYPTO"},
]

TV_SYM_MAP = {
    "BTC":"BINANCE:BTCUSDT","ETH":"BINANCE:ETHUSDT","SOL":"BINANCE:SOLUSDT",
    "BNB":"BINANCE:BNBUSDT","XRP":"BINANCE:XRPUSDT","ADA":"BINANCE:ADAUSDT",
    "DOGE":"BINANCE:DOGEUSDT","AVAX":"BINANCE:AVAXUSDT","DOT":"BINANCE:DOTUSDT",
    "AAPL":"NASDAQ:AAPL","TSLA":"NASDAQ:TSLA","NVDA":"NASDAQ:NVDA",
    "MSFT":"NASDAQ:MSFT","GOOGL":"NASDAQ:GOOGL","AMZN":"NASDAQ:AMZN",
    "META":"NASDAQ:META","AMD":"NASDAQ:AMD","NFLX":"NASDAQ:NFLX",
    "RELIANCE":"NSE:RELIANCE","TCS":"NSE:TCS","INFY":"NSE:INFY",
    "HDFCBANK":"NSE:HDFCBANK","ICICIBANK":"NSE:ICICIBANK","SBIN":"NSE:SBIN",
    "WIPRO":"NSE:WIPRO","BAJFINANCE":"NSE:BAJFINANCE","TATAMOTORS":"NSE:TATAMOTORS",
}

@st.cache_data(ttl=90, show_spinner=False)
def _price(sym):
    try:
        df = yf.Ticker(sym).history(period="5d", interval="1d")
        if df.empty: return {}
        c = float(df["Close"].iloc[-1])
        p = float(df["Close"].iloc[-2]) if len(df)>1 else c
        v = float(df["Volume"].iloc[-1])
        h = float(df["High"].iloc[-1]); l = float(df["Low"].iloc[-1])
        chg = (c-p)/p*100 if p else 0
        spark = [float(x) for x in df["Close"].values[-7:]]
        return {"price":c,"chg":chg,"vol":v,"high":h,"low":l,"spark":spark}
    except: return {}

@st.cache_data(ttl=300, show_spinner=False)
def _search_symbols(query: str):
    """Search yfinance for matching symbols."""
    q = query.strip().upper()
    if not q: return []
    results = []
    # Try direct + common suffixes
    candidates = [q, q+"-USD", q+".NS", q+".BO", q+".L"]
    for sym in candidates:
        try:
            t = yf.Ticker(sym)
            info = t.info
            name = info.get("longName") or info.get("shortName","")
            price = info.get("currentPrice") or info.get("regularMarketPrice",0)
            sector = info.get("sector","")
            ex = info.get("exchange","")
            if name and price:
                results.append({"sym":sym,"name":name,"price":price,"sector":sector,"ex":ex})
        except: pass
    # Also search by company name via yfinance search
    try:
        import yfinance as yf2
        tickers = yf2.Tickers(q)
        # Try screener suggestions - just use our candidates
    except: pass
    return results[:8]

@st.cache_data(ttl=60, show_spinner=False)
def _ohlcv(sym, period="3mo", interval="1d"):
    try:
        df = yf.Ticker(sym).history(period=period, interval=interval)
        df.index = pd.to_datetime(df.index)
        return df
    except: return pd.DataFrame()

def _compute_tech(df):
    if df.empty or len(df)<20: return {}
    c=df["Close"].values.astype(float); h=df["High"].values.astype(float)
    l=df["Low"].values.astype(float); v=df["Volume"].values.astype(float)
    o=df["Open"].values.astype(float)
    def ema(a,n): return pd.Series(a).ewm(span=n,adjust=False).mean().values
    d=np.diff(c,prepend=c[0]); up=np.where(d>0,d,0); dn=np.where(d<0,-d,0)
    au=ema(up,14); ad=ema(dn,14)
    rsi=float((100-100/(1+np.where(ad==0,100,au/np.where(ad==0,1e-9,ad))))[-1])
    ema9=float(ema(c,9)[-1]); ema20=float(ema(c,20)[-1])
    ema50=float(ema(c,50)[-1]) if len(c)>=50 else float(c.mean())
    ema200=float(ema(c,200)[-1]) if len(c)>=200 else float(c.mean())
    ml=ema(c,12)-ema(c,26); sig=ema(ml,9)
    macd=float(ml[-1]); macd_h=float(ml[-1]-sig[-1]); macd_s=float(sig[-1])
    sma20=float(np.mean(c[-20:])); std20=float(np.std(c[-20:]))
    bb_u=sma20+2*std20; bb_l=sma20-2*std20
    tr=np.maximum(h[1:]-l[1:],np.maximum(abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1])))
    atr=float(tr[-14:].mean()) if len(tr)>=14 else 0
    tp=(h+l+c)/3; n20=min(20,len(tp))
    vwap=float(np.sum(tp[-n20:]*v[-n20:])/np.sum(v[-n20:])) if np.sum(v[-n20:])>0 else float(c[-1])
    vr=float(v[-1]/v[-20:].mean()) if v[-20:].mean()>0 else 1.0
    win=5; ps=[]; pr=[]
    for i in range(win,len(c)-win):
        if all(l[i]<=l[i-j] for j in range(1,win+1)) and all(l[i]<=l[i+j] for j in range(1,win+1)):
            ps.append(float(l[i]))
        if all(h[i]>=h[i-j] for j in range(1,win+1)) and all(h[i]>=h[i+j] for j in range(1,win+1)):
            pr.append(float(h[i]))
    cur=c[-1]
    sup=sorted([x for x in ps if x<cur],reverse=True)[:3]
    res=sorted([x for x in pr if x>cur])[:3]
    if cur>ema20>ema50: trend="BULLISH"
    elif cur<ema20<ema50: trend="BEARISH"
    else: trend="SIDEWAYS"
    ph=float(h[-60:].max()) if len(h)>=60 else float(h.max())
    pl=float(l[-60:].min()) if len(l)>=60 else float(l.min())
    diff=ph-pl
    fib={"0.236":round(ph-diff*0.236,4),"0.382":round(ph-diff*0.382,4),
         "0.500":round(ph-diff*0.500,4),"0.618":round(ph-diff*0.618,4),"0.786":round(ph-diff*0.786,4)}
    # Patterns
    pats=[]
    rows=df.tail(12)
    co=rows["Close"].values.astype(float); oo=rows["Open"].values.astype(float)
    ho=rows["High"].values.astype(float); lo2=rows["Low"].values.astype(float)
    for i in range(2,len(co)):
        o1,h1,l1,c1=oo[i-1],ho[i-1],lo2[i-1],co[i-1]
        o2,h2,l2,c2=oo[i],ho[i],lo2[i],co[i]
        b1=abs(c1-o1); b2=abs(c2-o2); rng=h2-l2 if h2-l2>0 else 1e-9
        lw=min(o2,c2)-l2; uw=h2-max(o2,c2)
        if b2<rng*0.1: pats.append({"name":"Doji","type":"NEUTRAL","bar":i,"desc":f"Indecision at {c2:.2f}"})
        if lw>b2*2 and uw<b2*0.5: pats.append({"name":"Hammer","type":"BULLISH","bar":i,"desc":f"Buyers rejected at {l2:.2f}"})
        if uw>b2*2 and lw<b2*0.5: pats.append({"name":"Shooting Star","type":"BEARISH","bar":i,"desc":f"Sellers at {h2:.2f}"})
        if c1<o1 and c2>o2 and o2<=c1 and c2>=o1 and b2>b1: pats.append({"name":"Bullish Engulfing","type":"BULLISH","bar":i,"desc":f"Bull engulfs bear at {c2:.2f}"})
        if c1>o1 and c2<o2 and o2>=c1 and c2<=o1 and b2>b1: pats.append({"name":"Bearish Engulfing","type":"BEARISH","bar":i,"desc":f"Bear engulfs bull at {c2:.2f}"})
        if b2/rng>0.88 and c2>o2: pats.append({"name":"Bullish Marubozu","type":"BULLISH","bar":i,"desc":f"No wicks at {c2:.2f}"})
        if b2/rng>0.88 and c2<o2: pats.append({"name":"Bearish Marubozu","type":"BEARISH","bar":i,"desc":f"Full bear at {c2:.2f}"})
        if i>=2:
            o0,c0=oo[i-2],co[i-2]; b0=abs(c0-o0)
            if c0<o0 and b1<b0*0.35 and c2>o2 and c2>=(o0+c0)/2:
                pats.append({"name":"Morning Star","type":"BULLISH","bar":i,"desc":"3-candle bullish reversal"})
            if c0>o0 and b1<b0*0.35 and c2<o2 and c2<=(o0+c0)/2:
                pats.append({"name":"Evening Star","type":"BEARISH","bar":i,"desc":"3-candle bearish reversal"})
    seen=set(); upats=[]
    for p in pats:
        if p["name"] not in seen: seen.add(p["name"]); upats.append(p)
    # Volume profile
    lo_v=float(l.min()); hi_v=float(h.max()); bins=20
    vp=[]
    if hi_v>lo_v:
        bs=(hi_v-lo_v)/bins
        for i in range(bins):
            lb=lo_v+i*bs; hb=lb+bs; mid=(lb+hb)/2
            mask=(l<=hb)&(h>=lb)
            vp.append({"price":round(mid,4),"vol":float(v[mask].sum())})
        vp=sorted(vp,key=lambda x:-x["vol"])
    return {"price":cur,"rsi":rsi,"ema9":ema9,"ema20":ema20,"ema50":ema50,"ema200":ema200,
            "macd":macd,"macd_h":macd_h,"macd_s":macd_s,"bb_upper":bb_u,"bb_lower":bb_l,
            "sma20":sma20,"atr":atr,"vwap":vwap,"vol_ratio":vr,"supports":sup,
            "resistances":res,"trend":trend,"fib":fib,"patterns":upats[:6],
            "vp":vp,"open":o[-1],"high":h[-1],"low":l[-1],"volume":v[-1]}

@st.cache_data(ttl=3600, show_spinner=False)
def _fundamental(sym):
    try:
        info = yf.Ticker(sym).info
        mc = info.get("marketCap",0)
        mc_str = f"₹{mc/1e12:.2f}T" if mc>1e12 else f"₹{mc/1e9:.1f}B" if mc>1e9 else f"${mc/1e9:.1f}B"
        price = info.get("currentPrice") or info.get("regularMarketPrice",0)
        h52 = info.get("fiftyTwoWeekHigh",0); l52 = info.get("fiftyTwoWeekLow",0)
        pos = round((price-l52)/(h52-l52)*100,1) if h52>l52 else 50
        tm = info.get("targetMeanPrice",0)
        up = round((tm-price)/price*100,1) if price and tm else None
        return {
            "name":info.get("longName") or info.get("shortName",sym),
            "sector":info.get("sector","—"),"industry":info.get("industry","—"),
            "country":info.get("country","—"),"exchange":info.get("exchange","—"),
            "currency":info.get("currency","INR"),"mktcap_str":mc_str,"price":price,
            "pe":info.get("trailingPE"),"fwd_pe":info.get("forwardPE"),
            "pb":info.get("priceToBook"),"eps":info.get("trailingEps"),
            "fwd_eps":info.get("forwardEps"),"revenue":info.get("totalRevenue",0),
            "gross_m":info.get("grossMargins"),"profit_m":info.get("profitMargins"),
            "roe":info.get("returnOnEquity"),"roa":info.get("returnOnAssets"),
            "de":info.get("debtToEquity"),"cr":info.get("currentRatio"),
            "div_y":info.get("dividendYield"),"beta":info.get("beta"),
            "h52":h52,"l52":l52,"pos52":pos,"analyst":info.get("recommendationKey","—"),
            "target_mean":tm,"upside":up,
            "desc":info.get("longBusinessSummary","")[:500],
            "employees":info.get("fullTimeEmployees",0),
        }
    except: return {}

def _ai_full_analysis(sym, name, tech, fund):
    groq_k=_key("GROQ_API_KEY"); ds_k=_key("DEEPSEEK_API_KEY")
    p=tech.get("price",0); rsi=tech.get("rsi",50); trend=tech.get("trend","?")
    pats=[x["name"] for x in tech.get("patterns",[])[:4]]
    sup=tech.get("supports",[]); res=tech.get("resistances",[])
    entry=sup[0] if sup else p*0.99; sl=sup[1] if len(sup)>1 else p*0.97
    t1=res[0] if res else p*1.04; t2=res[1] if len(res)>1 else p*1.08
    fib=tech.get("fib",{})
    prompt=f"""You are SAGE, elite institutional analyst. Analyze {name} ({sym}).

TECHNICAL: Price={p:.4f} RSI={rsi:.1f} Trend={trend} EMA20={tech.get('ema20',0):.4f} EMA50={tech.get('ema50',0):.4f} EMA200={tech.get('ema200',0):.4f}
MACD_hist={tech.get('macd_h',0):.4f} BB_upper={tech.get('bb_upper',0):.4f} BB_lower={tech.get('bb_lower',0):.4f}
ATR={tech.get('atr',0):.4f} VWAP={tech.get('vwap',0):.4f} VolRatio={tech.get('vol_ratio',1):.2f}x
Supports={sup} Resistances={res} Fib={fib} Patterns={pats}
FUNDAMENTAL: Sector={fund.get('sector','?')} PE={fund.get('pe')} ROE={round((fund.get('roe') or 0)*100,1)}%
ProfitMargin={round((fund.get('profit_m') or 0)*100,1)}% DE={fund.get('de')} Beta={fund.get('beta')} Analyst={fund.get('analyst')}
Target={fund.get('target_mean')} Upside={fund.get('upside')}%

Return ONLY valid JSON:
{{"rating":"BUY","rating_color":"#26a69a","price_target":{t1},"confidence":78,
"bias":"BULLISH","bias_color":"#26a69a",
"entry":{round(entry,4)},"stop":{round(sl,4)},"t1":{round(t1,4)},"t2":{round(t2,4)},
"rr":"1:2.5","quality":"GOOD",
"summary":"2 sentence analysis with specific prices",
"thesis":["point 1 with data","point 2","point 3"],
"risks":["risk 1","risk 2"],
"indicators":{{"RSI":"reading","MACD":"direction","EMA":"structure","BB":"position","Volume":"ratio","VWAP":"above/below","StochRSI":"reading"}},
"patterns_detail":[{{"name":"","significance":"","action":""}}],
"volume_analysis":"what volume tells us",
"sr_analysis":"key S/R levels explanation",
"fundamental_summary":"2-3 sentence fundamental context with specific metrics",
"valuation":"UNDERVALUED/FAIRLY VALUED/OVERVALUED with reason",
"valuation_color":"#26a69a",
"sector_outlook":"sector dynamics",
"catalysts":["catalyst 1","catalyst 2"],
"macro":"macro factors",
"voice":"50-word Hindi+English spoken brief: stock name, rating, target, why, key risk. Bloomberg TV style."
}}"""
    for url,k,model in [(DEEPSEEK_URL,ds_k,"deepseek-chat"),(GROQ_URL,groq_k,"llama-3.3-70b-versatile")]:
        if not k: continue
        try:
            r=requests.post(url,headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.2,"max_tokens":2000},timeout=30)
            raw=r.json()["choices"][0]["message"]["content"].strip()
            if "```json" in raw: raw=raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw: raw=raw.split("```")[1].split("```")[0].strip()
            res2=json.loads(raw); res2["_api"]="DeepSeek" if "deepseek" in url else "Groq"; return res2
        except: continue
    # fallback
    bc="#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"
    bias="BULLISH" if trend=="BULLISH" else "BEARISH" if trend=="BEARISH" else "NEUTRAL"
    rr_val=(t1-entry)/(entry-sl) if entry-sl>0 else 1.5
    return {"rating":"HOLD","rating_color":"#f59e0b","price_target":round(t1,2),"confidence":60,
            "bias":bias,"bias_color":bc,"entry":round(entry,4),"stop":round(sl,4),
            "t1":round(t1,4),"t2":round(t2,4),"rr":f"1:{rr_val:.1f}","quality":"AVERAGE",
            "summary":f"{name} shows {trend} trend. RSI {rsi:.0f}, volume {tech.get('vol_ratio',1):.1f}x avg.",
            "thesis":[f"Trend: {trend}",f"RSI: {rsi:.0f}",f"Vol: {tech.get('vol_ratio',1):.1f}x"],
            "risks":["Market volatility","Stop breach below "+str(round(sl,2))],
            "indicators":{"RSI":f"{rsi:.0f}","MACD":"bullish" if tech.get("macd_h",0)>0 else "bearish",
                "EMA":f"{'above' if p>tech.get('ema20',p) else 'below'} EMA20","BB":"mid","Volume":f"{tech.get('vol_ratio',1):.1f}x","VWAP":f"{'above' if p>tech.get('vwap',p) else 'below'}","StochRSI":"50"},
            "patterns_detail":[{"name":x["name"],"significance":x.get("desc",""),"action":"Monitor"} for x in tech.get("patterns",[])[:3]],
            "volume_analysis":f"Vol {tech.get('vol_ratio',1):.1f}x avg","sr_analysis":f"S:{sup[:2]} R:{res[:2]}",
            "fundamental_summary":f"Sector: {fund.get('sector','?')}. PE:{fund.get('pe')} ROE:{round((fund.get('roe') or 0)*100,1)}%",
            "valuation":"FAIRLY VALUED","valuation_color":"#f59e0b",
            "sector_outlook":"Monitor sector rotation","catalysts":["Earnings","Policy update"],
            "macro":"Global rates, FII flows","voice":f"Main {name} ka analysis kar raha hoon. Trend {trend} hai. Entry {entry:.2f}, stop {sl:.2f}, target {t1:.2f}.",
            "_api":"Rule-based"}

# ─── CHART HTML (LightweightCharts, fixed px) ─────────────────────────────────
CHART_H = 680

def _chart_html(df, tech, ai, sym):
    candles=[]; vols=[]
    if not df.empty:
        for idx,row in df.tail(200).iterrows():
            ts=int(pd.Timestamp(idx).timestamp())
            o=round(float(row["Open"]),4); h=round(float(row["High"]),4)
            l=round(float(row["Low"]),4); c=round(float(row["Close"]),4)
            candles.append({"time":ts,"open":o,"high":h,"low":l,"close":c})
            vols.append({"time":ts,"value":int(row["Volume"]),"color":"rgba(38,166,154,0.5)" if c>=o else "rgba(239,83,80,0.5)"})
    sup=tech.get("supports",[]); res2=tech.get("resistances",[])
    fib=tech.get("fib",{}); vwap=tech.get("vwap",0)
    ema20=tech.get("ema20",0); ema50=tech.get("ema50",0); ema200=tech.get("ema200",0)
    entry=ai.get("entry",0); stop=ai.get("stop",0); t1=ai.get("t1",0); t2=ai.get("t2",0)
    bc=ai.get("bias_color","#f59e0b"); bias=ai.get("bias","NEUTRAL"); conf=ai.get("confidence",65)
    rr=ai.get("rr","—"); qual=ai.get("quality","—"); cur=tech.get("price",0)
    rsi=tech.get("rsi",50); macd_up=tech.get("macd_h",0)>0; vr=tech.get("vol_ratio",1)
    atr=tech.get("atr",0); api_used=ai.get("_api","AI")
    voice=json.dumps(ai.get("voice",""))
    markers=[]
    if candles:
        for pt in tech.get("patterns",[])[:5]:
            bi=min(pt.get("bar",len(candles)-1),len(candles)-1)
            if 0<=bi<len(candles):
                cdl=candles[bi]
                pc={"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#fbbf24"}.get(pt["type"],"#fbbf24")
                ps={"BULLISH":"arrowUp","BEARISH":"arrowDown","NEUTRAL":"circle"}.get(pt["type"],"circle")
                pp={"BULLISH":"belowBar","BEARISH":"aboveBar","NEUTRAL":"inBar"}.get(pt["type"],"inBar")
                markers.append({"time":cdl["time"],"position":pp,"color":pc,"shape":ps,"text":pt["name"][:12]})
    body_h=CHART_H-32
    # Volume profile bars HTML
    vp=tech.get("vp",[]); max_vp=max([x["vol"] for x in vp],default=1)
    if max_vp==0: max_vp=1
    vp_html=""
    for vitem in sorted(vp[:18],key=lambda x:-x["price"]):
        pct=min(vitem["vol"]/max_vp*100,100)
        is_poc=vitem["vol"]==max_vp
        col="rgba(41,98,255,0.7)" if is_poc else "rgba(41,98,255,0.28)"
        vp_html+=f'<div class="vpb"><div class="vpf" style="width:{pct:.0f}%;background:{col};"></div><span class="vpl">{vitem["price"]:.1f}</span></div>'

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#131722;color:#d1d4dc;font-family:'Trebuchet MS',sans-serif;width:100%;height:{CHART_H}px;overflow:hidden;}}
#root{{width:100%;height:{CHART_H}px;display:flex;flex-direction:column;}}
#cw{{flex:1;display:flex;height:{body_h}px;}}
#ca{{flex:1;position:relative;min-width:0;height:{body_h}px;}}
#cd{{width:100%;height:{body_h}px;}}
#vps{{width:66px;background:#0e1117;border-left:1px solid #2a2e39;display:flex;flex-direction:column;height:{body_h}px;overflow:hidden;}}
.vpb{{display:flex;align-items:center;flex:1;padding:0 2px 0 3px;border-bottom:1px solid rgba(255,255,255,0.02);min-height:0;}}
.vpf{{height:55%;border-radius:1px;min-width:2px;}}
.vpl{{font-size:7px;color:#4a5568;margin-left:2px;white-space:nowrap;}}
#ft{{height:32px;background:#1e222d;border-top:1px solid #2a2e39;display:flex;align-items:center;padding:0 10px;font-size:10.5px;flex-shrink:0;gap:0;}}
#lg{{position:absolute;top:8px;left:8px;z-index:20;background:rgba(19,23,34,0.95);border:1px solid #2a2e39;border-radius:8px;padding:7px 11px;}}
#lg .ls{{font-size:12px;font-weight:700;color:#d1d4dc;}}
#lg .lp{{font-size:19px;font-weight:900;color:{bc};font-family:monospace;margin:2px 0;}}
#lg .lb{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:700;background:{bc}22;color:{bc};border:1px solid {bc}44;}}
#lvl{{position:absolute;top:8px;right:4px;z-index:20;background:rgba(19,23,34,0.95);border:1px solid #2a2e39;border-radius:8px;padding:7px 10px;min-width:140px;}}
#lvl .lh{{font-size:9px;font-weight:700;color:#6a6e7a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;}}
#lvl .lr{{font-size:10.5px;display:flex;justify-content:space-between;gap:6px;padding:2px 0;border-bottom:1px solid #1a1e2d;}}
#vb{{position:absolute;bottom:38px;right:4px;z-index:21;width:32px;height:32px;background:#2962ff;border:none;border-radius:50%;color:white;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 12px rgba(41,98,255,0.5);}}
#vb:hover{{background:#1e56e8;}}
#vpc{{position:absolute;bottom:38px;left:8px;right:40px;z-index:20;background:rgba(19,23,34,0.96);border:1px solid #2962ff44;border-radius:8px;padding:8px 12px;display:none;}}
#vpc.vis{{display:block;}}
</style></head><body>
<div id="root">
<div id="cw">
  <div id="ca">
    <div id="cd"></div>
    <div id="lg"><div class="ls">{sym}</div><div class="lp">{cur:.4f}</div><div class="lb">{bias} · {conf}%</div></div>
    <div id="lvl"><div class="lh">AI Levels · {api_used}</div>
      <div class="lr"><span style="color:#26a69a;font-weight:600;">Entry</span><span style="color:#26a69a;font-family:monospace;">{entry:.4f}</span></div>
      <div class="lr"><span style="color:#ef5350;font-weight:600;">Stop</span><span style="color:#ef5350;font-family:monospace;">{stop:.4f}</span></div>
      {'<div class="lr"><span style="color:#2962ff;">T1</span><span style="color:#2962ff;font-family:monospace;">'+str(round(t1,4))+'</span></div>' if t1 else ''}
      {'<div class="lr"><span style="color:#9c27b0;">T2</span><span style="color:#9c27b0;font-family:monospace;">'+str(round(t2,4))+'</span></div>' if t2 else ''}
      <div class="lr" style="border:none;"><span style="color:#6a6e7a;font-size:9px;">R:R</span><span style="font-weight:700;">{rr}</span></div>
    </div>
    <button id="vb" onclick="doVoice()" title="SAGE Voice">🔊</button>
    <div id="vpc"><span style="color:#2962ff;font-weight:700;font-size:11px;">🔊 SAGE Voice</span><span id="vst" style="color:#6a6e7a;font-size:10px;margin-left:6px;">Tap to hear</span></div>
  </div>
  <div id="vps"><div style="font-size:7px;color:#6a6e7a;text-align:center;padding:2px 0;border-bottom:1px solid #2a2e39;font-weight:700;">VOL</div>{vp_html}</div>
</div>
<div id="ft">
  <span>RSI:<b style="color:{'#26a69a' if rsi<50 else '#ef5350'}">{rsi:.0f}</b></span>&nbsp;|&nbsp;
  <span>MACD:<b style="color:{'#26a69a' if macd_up else '#ef5350'}">{'▲' if macd_up else '▼'}</b></span>&nbsp;|&nbsp;
  <span>Vol:<b>{vr:.1f}x</b></span>&nbsp;|&nbsp;<span>ATR:<b>{atr:.4f}</b></span>&nbsp;|&nbsp;
  <span>VWAP:<b>{vwap:.4f}</b></span>&nbsp;|&nbsp;
  <span style="color:{bc};">{rr} · {qual}</span>&nbsp;|&nbsp;
  <span style="color:#4a5568;font-size:9px;">Educational only</span>
</div>
</div>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){{
var H={body_h},candles={json.dumps(candles)},vols={json.dumps(vols)};
var supp={json.dumps(sup)},ress={json.dumps(res2)},fib={json.dumps(fib)},marks={json.dumps(markers)};
var voice={voice};
function init(){{
  var el=document.getElementById('cd'); if(!el) return;
  var W=el.parentElement.clientWidth-66; if(W<=0) W=window.innerWidth-80;
  var chart=LightweightCharts.createChart(el,{{width:W,height:H,
    layout:{{background:{{type:'solid',color:'#131722'}},textColor:'#d1d4dc'}},
    grid:{{vertLines:{{color:'rgba(255,255,255,0.04)'}},horzLines:{{color:'rgba(255,255,255,0.04)'}}}},
    crosshair:{{mode:LightweightCharts.CrosshairMode.Normal}},
    rightPriceScale:{{borderColor:'#2a2e39'}},
    timeScale:{{borderColor:'#2a2e39',timeVisible:true,secondsVisible:false}},
    handleScroll:{{mouseWheel:true,pressedMouseMove:true}},
    handleScale:{{mouseWheel:true,pinch:true}},
  }});
  var cs=chart.addCandlestickSeries({{upColor:'#26a69a',downColor:'#ef5350',borderUpColor:'#26a69a',borderDownColor:'#ef5350',wickUpColor:'#26a69a',wickDownColor:'#ef5350'}});
  if(candles.length) cs.setData(candles);
  var vs=chart.addHistogramSeries({{priceScaleId:'vol',scaleMargins:{{top:0.78,bottom:0}}}});
  chart.priceScale('vol').applyOptions({{scaleMargins:{{top:0.78,bottom:0}}}});
  if(vols.length) vs.setData(vols);
  if(marks.length) cs.setMarkers(marks);
  supp.forEach(function(s){{cs.createPriceLine({{price:s,color:'#26a69a',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'S'}});}});
  ress.forEach(function(r){{cs.createPriceLine({{price:r,color:'#ef5350',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'R'}});}});
  var fc={{'0.236':'#7986cb','0.382':'#26a69a','0.500':'#fbbf24','0.618':'#ef5350','0.786':'#e040fb'}};
  Object.keys(fib).forEach(function(k){{if(fib[k])cs.createPriceLine({{price:fib[k],color:fc[k]||'#aaa',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'Fib '+k}});}});
  if({int(bool(entry))}) cs.createPriceLine({{price:{entry or 0},color:'#26a69a',lineWidth:2,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:'ENTRY'}});
  if({int(bool(stop))}) cs.createPriceLine({{price:{stop or 0},color:'#ef5350',lineWidth:2,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:'STOP'}});
  if({int(bool(t1))}) cs.createPriceLine({{price:{t1 or 0},color:'#2962ff',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'T1'}});
  if({int(bool(t2))}) cs.createPriceLine({{price:{t2 or 0},color:'#9c27b0',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'T2'}});
  if({int(bool(vwap))}) cs.createPriceLine({{price:{vwap or 0},color:'#fbbf24',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'VWAP'}});
  if({int(bool(ema20))}) cs.createPriceLine({{price:{ema20 or 0},color:'#2196f3',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:false,title:'EMA20'}});
  if({int(bool(ema50))}) cs.createPriceLine({{price:{ema50 or 0},color:'#ff9800',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:false,title:'EMA50'}});
  if({int(bool(ema200))}) cs.createPriceLine({{price:{ema200 or 0},color:'#e91e63',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:false,title:'EMA200'}});
  chart.timeScale().fitContent();
  window.addEventListener('resize',function(){{var nw=document.getElementById('cd').parentElement.clientWidth-66;chart.applyOptions({{width:nw>0?nw:400,height:H}});}});
}}
window.doVoice=function(){{
  var vp2=document.getElementById('vpc'),vst=document.getElementById('vst');
  if(!vp2) return;
  if(!vp2.classList.contains('vis')){{
    vp2.classList.add('vis');
    if('speechSynthesis' in window){{
      window.speechSynthesis.cancel();
      var u=new SpeechSynthesisUtterance(voice||'Analysis ready');
      u.lang='hi-IN';u.rate=0.9;u.pitch=1;
      var vs2=window.speechSynthesis.getVoices();
      var hv=vs2.find(function(v){{return v.lang==='hi-IN';}});
      if(hv) u.voice=hv;
      if(vst) vst.textContent='Speaking...';
      u.onend=function(){{if(vst) vst.textContent='Done';vp2.classList.remove('vis');}};
      window.speechSynthesis.speak(u);
    }}
  }} else {{vp2.classList.remove('vis');if('speechSynthesis' in window) window.speechSynthesis.cancel();}}
}};
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
}})();
</script></body></html>"""

# ─── FULL ANALYSIS REPORT RENDERER ───────────────────────────────────────────
def _render_full_report(sym, name, tech, fund, ai):
    bc=ai.get("bias_color","#f59e0b"); bias=ai.get("bias","NEUTRAL")
    rc=ai.get("rating_color","#f59e0b"); rat=ai.get("rating","HOLD")
    conf=ai.get("confidence",65); pt=ai.get("price_target",0)
    price=tech.get("price",0); trend=tech.get("trend","—")
    tc="#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"
    up_pct=round((pt-price)/price*100,1) if price and pt else 0
    api_used=ai.get("_api","AI")

    # ── COVER STRIP ──────────────────────────────────────────────────────────
    st.markdown(f"""<div style="background:linear-gradient(135deg,#0a0e1a,#131722);
    border:2px solid #2a2e39;border-radius:12px;padding:14px 18px;margin:6px 0;
    position:relative;overflow:hidden;">
    <div style="position:absolute;top:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,#2962ff,#26a69a,#f59e0b,#ef5350,#9c27b0);"></div>
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
      <div>
        <div style="font-size:20px;font-weight:900;color:#d1d4dc;">{name}</div>
        <div style="color:#6a6e7a;font-size:11px;">{sym} · {fund.get('exchange','—')} · {fund.get('sector','—')} · {fund.get('country','—')}</div>
        <div style="display:flex;gap:8px;margin-top:6px;flex-wrap:wrap;">
          <span style="background:{rc}22;border:2px solid {rc};border-radius:8px;padding:4px 14px;font-size:13px;font-weight:900;color:{rc};">{rat}</span>
          <span style="background:{bc}11;border:1px solid {bc}33;border-radius:8px;padding:4px 10px;font-size:11px;font-weight:700;color:{bc};">{bias}</span>
          <span style="background:#2a2e39;border-radius:8px;padding:4px 10px;font-size:11px;color:#6a6e7a;">via {api_used}</span>
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:26px;font-weight:900;color:#d1d4dc;font-family:monospace;">{price:.4f}</div>
        <div style="color:#6a6e7a;font-size:11px;">{fund.get('currency','')}</div>
        <div style="color:{tc};font-weight:700;font-size:13px;margin-top:2px;">{trend}</div>
        <div style="margin-top:4px;font-size:11px;">Target: <b style="color:{rc};">{pt:.2f}</b>
        <span style="color:{'#26a69a' if up_pct>0 else '#ef5350'};margin-left:4px;">{up_pct:+.1f}%</span></div>
        <div style="background:#0e1117;border-radius:4px;height:4px;width:100px;margin-top:4px;margin-left:auto;">
          <div style="background:{rc};height:4px;border-radius:4px;width:{conf}%;"></div>
        </div>
        <div style="color:#6a6e7a;font-size:10px;margin-top:2px;">AI Confidence: {conf}%</div>
      </div>
    </div>
    </div>""", unsafe_allow_html=True)

    # ── EXECUTIVE SUMMARY ────────────────────────────────────────────────────
    st.markdown(f"""<div style="background:#131722;border-left:3px solid #2962ff;
    border-radius:0 8px 8px 0;padding:10px 14px;margin:6px 0;font-size:12px;color:#d1d4dc;line-height:1.7;">
    <span style="color:#2962ff;font-weight:700;text-transform:uppercase;font-size:10px;letter-spacing:.1em;">Executive Summary · </span>
    {ai.get('summary','')}</div>""", unsafe_allow_html=True)

    # ── 9 KEY METRICS ─────────────────────────────────────────────────────────
    def mc(lbl,val,col="#d1d4dc"):
        v=str(val) if val is not None else "—"
        return f"""<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:7px;padding:8px;text-align:center;">
        <div style="color:#6a6e7a;font-size:9px;text-transform:uppercase;font-weight:600;">{lbl}</div>
        <div style="font-size:15px;font-weight:900;color:{col};font-family:monospace;margin-top:2px;">{v}</div></div>"""
    pe_v=f"{fund.get('pe'):.1f}" if fund.get('pe') else "—"
    pb_v=f"{fund.get('pb'):.2f}" if fund.get('pb') else "—"
    roe_v=f"{(fund.get('roe') or 0)*100:.1f}%" if fund.get('roe') else "—"
    pm_v=f"{(fund.get('profit_m') or 0)*100:.1f}%" if fund.get('profit_m') else "—"
    de_v=f"{fund.get('de'):.1f}" if fund.get('de') else "—"
    dy_v=f"{(fund.get('div_y') or 0)*100:.2f}%" if fund.get('div_y') else "—"
    beta_v=f"{fund.get('beta'):.2f}" if fund.get('beta') else "—"
    rsi_v=f"{tech.get('rsi',50):.0f}"
    vr_v=f"{tech.get('vol_ratio',1):.1f}x"
    cols9=st.columns(9)
    mets=[("P/E",pe_v,"#2962ff"),("P/B",pb_v,"#7986cb"),("ROE",roe_v,"#26a69a"),
          ("Margin",pm_v,"#26a69a"),("D/E",de_v,"#f59e0b"),("Div",dy_v,"#4caf50"),
          ("Beta",beta_v,"#9c27b0"),("RSI",rsi_v,"#26a69a" if tech.get("rsi",50)<50 else "#ef5350"),
          ("Volume",vr_v,"#2962ff")]
    for i,(lbl,v,c) in enumerate(mets):
        with cols9[i]: st.markdown(mc(lbl,v,c),unsafe_allow_html=True)

    # ── 52W RANGE ─────────────────────────────────────────────────────────────
    h52=fund.get("h52",0); l52=fund.get("l52",0); pos52=fund.get("pos52",50)
    st.markdown(f"""<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:8px;padding:8px 12px;margin:6px 0;">
    <div style="display:flex;justify-content:space-between;font-size:10px;margin-bottom:4px;">
      <span style="color:#ef5350;">52W Low: <b>{l52:.2f}</b></span>
      <span style="color:#6a6e7a;font-weight:700;letter-spacing:.06em;">52-WEEK RANGE</span>
      <span style="color:#26a69a;">52W High: <b>{h52:.2f}</b></span>
    </div>
    <div style="position:relative;background:#0e1117;border-radius:100px;height:7px;">
      <div style="position:absolute;left:0;top:0;height:7px;border-radius:100px;
      background:linear-gradient(90deg,#ef5350,#f59e0b,#26a69a);width:{pos52}%;"></div>
      <div style="position:absolute;top:-4px;left:calc({pos52}% - 7px);width:14px;height:14px;
      background:#fff;border:2px solid #2962ff;border-radius:50%;box-shadow:0 0 6px rgba(41,98,255,0.6);"></div>
    </div>
    <div style="text-align:center;font-size:10px;color:#d1d4dc;margin-top:4px;">
      <b style="font-family:monospace;">{price:.4f}</b> — at <b style="color:#2962ff;">{pos52:.1f}%</b> of 52-week range
    </div></div>""", unsafe_allow_html=True)

    # ── 3-COL: VALUATION + FUNDAMENTAL + TECHNICAL ──────────────────────────
    c1,c2,c3=st.columns(3)
    vc={"UNDERVALUED":"#26a69a","FAIRLY VALUED":"#f59e0b","OVERVALUED":"#ef5350"}.get(ai.get("valuation","FAIRLY VALUED"),"#f59e0b")
    with c1:
        st.markdown(f"""<div style="background:#131722;border:1px solid #2a2e39;border-top:3px solid {vc};border-radius:0 0 8px 8px;padding:10px;min-height:200px;">
        <div style="color:#6a6e7a;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">📐 VALUATION</div>
        <div style="background:{vc}22;border:1px solid {vc}44;border-radius:6px;padding:5px;text-align:center;margin-bottom:8px;">
          <span style="color:{vc};font-weight:900;font-size:13px;">{ai.get('valuation','—')}</span></div>
        <div style="font-size:11px;color:#9598a1;line-height:1.7;">{ai.get('fundamental_summary','')}</div>
        <div style="margin-top:6px;font-size:10px;color:#6a6e7a;">Analyst: <b style="color:#d1d4dc;">{fund.get('analyst','—').upper()}</b></div>
        <div style="font-size:10px;color:#6a6e7a;">Target: <b style="color:#2962ff;">{fund.get('target_mean') or '—'}</b></div>
        </div>""", unsafe_allow_html=True)
    with c2:
        fund_rows=[("Sector",fund.get("sector","—")),("Industry",fund.get("industry","—")[:20]),
                   ("Revenue",f"₹{fund.get('revenue',0)/1e9:.1f}B" if fund.get('revenue') else "—"),
                   ("Gross Margin",f"{(fund.get('gross_m') or 0)*100:.1f}%"),
                   ("ROA",f"{(fund.get('roa') or 0)*100:.1f}%"),
                   ("Current Ratio",str(round(fund.get('cr') or 0,2))),
                   ("Employees",f"{fund.get('employees',0):,}" if fund.get('employees') else "—")]
        rows_html="".join([f'<div style="font-size:10.5px;display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #1a1e2d;"><span style="color:#6a6e7a;">{k}</span><span style="color:#9598a1;">{v}</span></div>' for k,v in fund_rows])
        st.markdown(f"""<div style="background:#131722;border:1px solid #2a2e39;border-top:3px solid #26a69a;border-radius:0 0 8px 8px;padding:10px;min-height:200px;">
        <div style="color:#6a6e7a;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">🏢 FUNDAMENTAL</div>
        {rows_html}</div>""", unsafe_allow_html=True)
    with c3:
        ind_sig=ai.get("indicators",{})
        ind_rows="".join([f'<div style="font-size:10.5px;display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #1a1e2d;"><span style="color:#6a6e7a;">{k}</span><span style="color:{"#26a69a" if any(w in str(v).lower() for w in ["bull","above","oversold","strong"]) else "#ef5350" if any(w in str(v).lower() for w in ["bear","below","overbought","weak"]) else "#9598a1"};font-size:10px;">{str(v)[:28]}</span></div>' for k,v in ind_sig.items()])
        mom=sum([1 if trend=="BULLISH" else -1 if trend=="BEARISH" else 0,
                 1 if tech.get("rsi",50)>50 else -1,
                 1 if tech.get("macd_h",0)>0 else -1]); mom_c="#26a69a" if mom>0 else "#ef5350" if mom<0 else "#f59e0b"
        st.markdown(f"""<div style="background:#131722;border:1px solid #2a2e39;border-top:3px solid #2962ff;border-radius:0 0 8px 8px;padding:10px;min-height:200px;">
        <div style="color:#6a6e7a;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">📊 TECHNICAL INDICATORS</div>
        {ind_rows}</div>""", unsafe_allow_html=True)

    # ── TRADE SETUP ───────────────────────────────────────────────────────────
    entry_p=ai.get("entry",0); stop_p=ai.get("stop",0); t1_p=ai.get("t1",0); t2_p=ai.get("t2",0)
    st.markdown(f"""<div style="background:linear-gradient(135deg,#0d1117,#161b22);border:2px solid #2962ff22;border-radius:10px;padding:12px;margin:6px 0;">
    <div style="color:#2962ff;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px;">📐 TRADE SETUP · {ai.get('quality','—')}</div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;">
      <div style="background:#122017;border:1px solid #26a69a44;border-radius:7px;padding:8px;text-align:center;"><div style="color:#6a6e7a;font-size:9px;">Entry</div><div style="color:#26a69a;font-size:14px;font-weight:900;font-family:monospace;">{entry_p:.4f}</div></div>
      <div style="background:#1a0d0d;border:1px solid #ef535044;border-radius:7px;padding:8px;text-align:center;"><div style="color:#6a6e7a;font-size:9px;">Stop</div><div style="color:#ef5350;font-size:14px;font-weight:900;font-family:monospace;">{stop_p:.4f}</div></div>
      <div style="background:#0d1219;border:1px solid #2962ff44;border-radius:7px;padding:8px;text-align:center;"><div style="color:#6a6e7a;font-size:9px;">Target 1</div><div style="color:#2962ff;font-size:14px;font-weight:900;font-family:monospace;">{t1_p:.4f}</div></div>
      <div style="background:#0d1219;border:1px solid #9c27b044;border-radius:7px;padding:8px;text-align:center;"><div style="color:#6a6e7a;font-size:9px;">Target 2</div><div style="color:#9c27b0;font-size:14px;font-weight:900;font-family:monospace;">{t2_p:.4f}</div></div>
      <div style="background:#1a1500;border:1px solid #f59e0b44;border-radius:7px;padding:8px;text-align:center;"><div style="color:#6a6e7a;font-size:9px;">R:R</div><div style="color:#f59e0b;font-size:16px;font-weight:900;">{ai.get('rr','—')}</div></div>
    </div></div>""", unsafe_allow_html=True)

    # ── THESIS + RISKS + PATTERNS ─────────────────────────────────────────────
    tr1,tr2=st.columns(2)
    with tr1:
        thesis=ai.get("thesis",[]); pats=tech.get("patterns",[])
        th_html="".join([f'<div style="display:flex;gap:6px;padding:3px 0;border-bottom:1px solid #1a3022;font-size:11px;color:#9598a1;"><span style="color:#26a69a;font-weight:700;">+</span><span>{t2}</span></div>' for t2 in thesis])
        st.markdown(f"""<div style="background:#122017;border:1px solid #26a69a33;border-radius:8px;padding:10px;margin:4px 0;">
        <div style="color:#26a69a;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">✅ INVESTMENT THESIS</div>{th_html}</div>""", unsafe_allow_html=True)
        # Patterns
        if pats:
            pat_html="".join([f'<span style="display:inline-block;background:{"#26a69a" if p["type"]=="BULLISH" else "#ef5350" if p["type"]=="BEARISH" else "#f59e0b"}22;color:{"#26a69a" if p["type"]=="BULLISH" else "#ef5350" if p["type"]=="BEARISH" else "#f59e0b"};border:1px solid {"#26a69a" if p["type"]=="BULLISH" else "#ef5350" if p["type"]=="BEARISH" else "#f59e0b"}44;border-radius:12px;padding:3px 9px;font-size:10px;font-weight:600;margin:2px;" title="{p.get("desc","")}">{p["name"]}</span>' for p in pats[:5]])
            st.markdown(f"""<div style="background:#1c1600;border:1px solid #f0883e33;border-radius:8px;padding:8px;margin-top:4px;">
            <div style="color:#f0883e;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:5px;">🕯️ CANDLESTICK PATTERNS</div>{pat_html}</div>""", unsafe_allow_html=True)
    with tr2:
        risks=ai.get("risks",[]); cats=ai.get("catalysts",[])
        rk_html="".join([f'<div style="display:flex;gap:6px;padding:3px 0;border-bottom:1px solid #2d1515;font-size:11px;color:#9598a1;"><span style="color:#ef5350;font-weight:700;">−</span><span>{r}</span></div>' for r in risks])
        ct_html="".join([f'<div style="font-size:10.5px;color:#9598a1;padding:2px 0;border-bottom:1px solid #1a1e2d;">• {c3}</div>' for c3 in cats[:3]])
        st.markdown(f"""<div style="background:#1a0d0d;border:1px solid #ef535033;border-radius:8px;padding:10px;margin:4px 0;">
        <div style="color:#ef5350;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">⚠️ KEY RISKS</div>{rk_html}</div>
        <div style="background:#131722;border:1px solid #fbbf2433;border-radius:8px;padding:8px;margin-top:4px;">
        <div style="color:#fbbf24;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:4px;">🎯 CATALYSTS</div>{ct_html}</div>""", unsafe_allow_html=True)

    # ── VOLUME + S/R + MACRO ──────────────────────────────────────────────────
    v1,v2,v3=st.columns(3)
    with v1:
        st.markdown(f"""<div style="background:#131722;border:1px solid #2962ff33;border-radius:8px;padding:8px 10px;margin:4px 0;">
        <div style="color:#2962ff;font-size:10px;font-weight:700;margin-bottom:4px;">📈 VOLUME ANALYSIS</div>
        <div style="font-size:11px;color:#9598a1;line-height:1.6;">{ai.get('volume_analysis','')}</div></div>""", unsafe_allow_html=True)
    with v2:
        st.markdown(f"""<div style="background:#131722;border:1px solid #26a69a33;border-radius:8px;padding:8px 10px;margin:4px 0;">
        <div style="color:#26a69a;font-size:10px;font-weight:700;margin-bottom:4px;">🎯 SUPPORT / RESISTANCE</div>
        <div style="font-size:11px;color:#9598a1;line-height:1.6;">{ai.get('sr_analysis','')}</div></div>""", unsafe_allow_html=True)
    with v3:
        st.markdown(f"""<div style="background:#131722;border:1px solid #7986cb33;border-radius:8px;padding:8px 10px;margin:4px 0;">
        <div style="color:#7986cb;font-size:10px;font-weight:700;margin-bottom:4px;">🌍 MACRO & SECTOR</div>
        <div style="font-size:11px;color:#9598a1;line-height:1.6;">{ai.get('macro','')} {ai.get('sector_outlook','')}</div></div>""", unsafe_allow_html=True)

    # ── BUSINESS DESCRIPTION ──────────────────────────────────────────────────
    desc=fund.get("desc","")
    if desc:
        st.markdown(f"""<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:10px 14px;margin:6px 0;font-size:11px;color:#9598a1;line-height:1.6;">
        <span style="color:#58a6ff;font-weight:700;">🏢 About {name}: </span>{desc}</div>""", unsafe_allow_html=True)

    # ── DISCLAIMER ────────────────────────────────────────────────────────────
    st.markdown(f"""<div style="background:#0a0d12;border:1px solid #1a1e2d;border-radius:8px;padding:8px 12px;margin:6px 0;font-size:9px;color:#4a5568;line-height:1.6;">
    <b style="color:#6a6e7a;">DISCLAIMER:</b> FinSage AI Research generated on {datetime.now().strftime('%B %d, %Y %H:%M IST')} via {api_used}.
    For educational purposes only. Not financial advice. Investments are subject to market risk.
    Always consult a SEBI/SEC-registered advisor before trading. Past performance ≠ future results.</div>""", unsafe_allow_html=True)

    # Download
    txt=f"""FinSage AI Research — {name} ({sym})
Date: {datetime.now().strftime('%B %d, %Y')} | via {api_used}
Rating: {rat} | Target: {pt:.2f} | Upside: {up_pct:+.1f}%
Price: {price:.4f} | Trend: {trend} | RSI: {tech.get('rsi',50):.0f}

{ai.get('summary','')}

TRADE SETUP: Entry={entry_p} Stop={stop_p} T1={t1_p} T2={t2_p} R:R={ai.get('rr','')}
VALUATION: {ai.get('valuation','')}
THESIS: {chr(10).join(['+ '+t for t in ai.get('thesis',[])])}
RISKS: {chr(10).join(['- '+r for r in ai.get('risks',[])])}

DISCLAIMER: Educational only. Not financial advice."""
    st.download_button("📥 Download Report",txt,f"finsage_{sym.replace('.','_')}_{datetime.now().strftime('%Y%m%d')}.txt","text/plain",key="dl_report_full")

# ═══════════════════════════════════════════════════════════════════
# MAIN DASHBOARD RENDERER
# ═══════════════════════════════════════════════════════════════════
def render_market_dashboard():
    st.markdown("""<style>
    header[data-testid="stHeader"],footer,
    div[data-testid="stDecoration"],div[data-testid="stToolbar"],
    div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}
    .block-container{padding:0!important;max-width:100vw!important;}
    .stHorizontalBlock{gap:0!important;}
    div[data-testid="stVerticalBlock"]{gap:0!important;}
    </style>""", unsafe_allow_html=True)

    # Init state
    for k,v in [("mkt_sel",None),("mkt_search",""),("mkt_search_res",[]),
                ("mkt_tab","All"),("mkt_ai",False),("mkt_ai_res",None),
                ("mkt_tf","1D"),("mkt_favs",[]),("mkt_chart_sym",None)]:
        if k not in st.session_state: st.session_state[k]=v

    # ── TOP BAR ───────────────────────────────────────────────────────────────
    st.markdown(f"""<div style="background:#1e222d;border-bottom:1px solid #2a2e39;
    padding:5px 10px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <img src="{LOGO_URL}" style="height:26px;border-radius:5px;" onerror="this.style.display='none'">
      <span style="color:#d1d4dc;font-weight:900;font-size:14px;">FinSage <span style="color:#2962ff;">AI</span></span>
      <span style="background:#2962ff22;color:#2962ff;font-size:8px;padding:1px 6px;border-radius:8px;border:1px solid #2962ff44;font-weight:700;">AI POWERED</span>
      <div style="flex:1;"></div>
      <span style="color:#6a6e7a;font-size:10px;">🕐 {datetime.now().strftime('%d %b %Y · %H:%M IST')}</span>
    </div>""", unsafe_allow_html=True)

    # ── MAIN LAYOUT ───────────────────────────────────────────────────────────
    left, right = st.columns([1, 3], gap="small")

    # ══ LEFT: WATCHLIST + SEARCH ══════════════════════════════════════════════
    with left:
        # Search
        srch = st.text_input("", placeholder="🔍  Search symbol or company...",
                              key="mkt_srch_inp", label_visibility="collapsed")

        if srch and srch != st.session_state.mkt_search:
            st.session_state.mkt_search = srch
            with st.spinner("Searching..."):
                q = srch.strip().upper()
                # First try exact match in our list
                found = [x for x in DEFAULT_WATCHLIST if q in x["sym"].upper() or q in x["name"].upper()]
                # Also try yfinance
                if not found or len(found)<3:
                    extra_syms = [q, q+"-USD", q+".NS", q+".BO"]
                    for es in extra_syms:
                        try:
                            info = yf.Ticker(es).info
                            nm = info.get("longName") or info.get("shortName","")
                            pr = info.get("currentPrice") or info.get("regularMarketPrice",0)
                            if nm and pr and not any(x["sym"]==es for x in found):
                                tv_s = TV_SYM_MAP.get(q, es)
                                found.append({"sym":es,"tv":tv_s,"name":nm[:20],"type":"crypto" if "USD" in es else "stock","ex":info.get("exchange","")})
                        except: pass
                st.session_state.mkt_search_res = found[:10]

        # Show search results as clickable rows
        if srch and st.session_state.mkt_search_res:
            st.markdown('<div style="background:#1a1e2d;border:1px solid #2962ff44;border-radius:8px;padding:4px;margin-bottom:4px;">', unsafe_allow_html=True)
            for item in st.session_state.mkt_search_res:
                d = _price(item["sym"])
                chg = d.get("chg",0); pr = d.get("price",0)
                cc = "#26a69a" if chg>=0 else "#ef5350"
                if st.button(f"{item['name'][:16]}  {item['sym'].replace('.NS','')}", key=f"sr_{item['sym']}", use_container_width=True):
                    st.session_state.mkt_sel = item
                    st.session_state.mkt_ai = False
                    st.session_state.mkt_ai_res = None
                    st.session_state.mkt_search = ""
                    st.session_state.mkt_search_res = []
                    st.rerun()
                st.markdown(f'<div style="display:flex;padding:0 4px 3px 4px;font-size:10px;border-bottom:1px solid #1a1e2d;margin-top:-8px;"><span style="color:#6a6e7a;flex:1;">{item.get("ex","")}</span><span style="color:{cc};font-family:monospace;">{pr:.2f}</span><span style="color:{cc};margin-left:5px;">{chg:+.1f}%</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        elif srch:
            st.caption("No results found")

        # Category tabs
        tab_opt = st.radio("", ["All","Stocks","Crypto","⭐ Favs"], horizontal=True,
                            key="mkt_tab_r", label_visibility="collapsed")

        # Filter watchlist
        wl = DEFAULT_WATCHLIST
        favs = st.session_state.get("mkt_favs", [])
        if tab_opt=="Stocks": wl=[x for x in wl if x["type"]=="stock"]
        elif tab_opt=="Crypto": wl=[x for x in wl if x["type"]=="crypto"]
        elif tab_opt=="⭐ Favs":
            fav_syms=[f["sym"] for f in favs]
            wl=[x for x in wl if x["sym"] in fav_syms]+[f for f in favs if f["sym"] not in [x["sym"] for x in wl]]

        # Header
        st.markdown("""<div style="display:flex;padding:3px 6px;font-size:9px;color:#6a6e7a;
        font-weight:700;border-bottom:1px solid #2a2e39;background:#1a1e2d;border-radius:5px 5px 0 0;
        text-transform:uppercase;letter-spacing:.06em;">
          <span style="flex:1;">Symbol</span>
          <span style="width:65px;text-align:right;">Price</span>
          <span style="width:50px;text-align:right;">Chg%</span>
        </div>""", unsafe_allow_html=True)

        sel = st.session_state.get("mkt_sel") or DEFAULT_WATCHLIST[0]

        for item in wl[:25]:
            d = _price(item["sym"])
            pr=d.get("price",0); chg=d.get("chg",0)
            cc="#26a69a" if chg>=0 else "#ef5350"
            is_sel = sel["sym"]==item["sym"]
            is_fav = any(f["sym"]==item["sym"] for f in favs)

            # Row button
            if st.button(f"{'⭐ ' if is_fav else ''}{item['name'][:15]}", key=f"wl_{item['sym']}",
                         use_container_width=True, type="primary" if is_sel else "secondary"):
                st.session_state.mkt_sel = item
                st.session_state.mkt_ai = False
                st.session_state.mkt_ai_res = None
                st.rerun()

            # Price row below button
            fav_sym = f"⭐" if is_fav else "☆"
            st.markdown(f"""<div style="display:flex;padding:0 6px 3px 6px;font-size:10px;
            border-bottom:1px solid #1a1e2d;margin-top:-8px;align-items:center;">
              <span style="color:#6a6e7a;font-size:9px;flex:1;">{item['sym'].replace('.NS','').replace('-USD','')}</span>
              <span style="color:{cc};font-family:monospace;font-weight:700;">{pr:.2f}</span>
              <span style="color:{cc};margin-left:5px;">{chg:+.1f}%</span>
            </div>""", unsafe_allow_html=True)

    # ══ RIGHT: CHART + ANALYSIS ═══════════════════════════════════════════════
    with right:
        sym = sel["sym"]; tv_sym = sel.get("tv",""); name = sel["name"]

        # ── CHART TOOLBAR ─────────────────────────────────────────────────────
        tb1,tb2,tb3,tb4,tb5 = st.columns([4,1,1,1,1])
        with tb1:
            tfs=["1D","1H","15m","4H","1W","1M"]
            tf=st.radio("",tfs,horizontal=True,key="mkt_tf_r",index=0,label_visibility="collapsed")
        with tb2:
            ai_clicked=st.button("🤖 AI",key="mkt_ai_btn",type="primary",use_container_width=True,help="Full AI Analysis")
        with tb3:
            chart_only=st.button("📊",key="mkt_co",use_container_width=True,help="Chart only")
        with tb4:
            fav_clicked=st.button("⭐",key="mkt_fav",use_container_width=True,help="Add to Favourites")
        with tb5:
            research_clicked=st.button("📋",key="mkt_rp",use_container_width=True,help="Research Report")

        # Handle buttons
        if ai_clicked:
            st.session_state.mkt_ai=True; st.session_state.mkt_ai_res=None
        if chart_only:
            st.session_state.mkt_ai=False; st.session_state.mkt_ai_res=None
        if fav_clicked:
            favs=st.session_state.get("mkt_favs",[])
            if any(f["sym"]==sym for f in favs):
                st.session_state.mkt_favs=[f for f in favs if f["sym"]!=sym]
                st.toast(f"Removed {name} from favourites")
            else:
                st.session_state.mkt_favs=favs+[sel]
                st.toast(f"⭐ Added {name} to favourites!")

        # Load data
        tf_map={"1D":("3mo","1d"),"1H":("1mo","1h"),"15m":("5d","15m"),
                "4H":("6mo","1d"),"1W":("2y","1wk"),"1M":("5y","1mo")}
        period,interval=tf_map.get(tf,("3mo","1d"))

        with st.spinner(f"Loading {name}..."):
            df=_ohlcv(sym,period,interval)
            tech=_compute_tech(df) if not df.empty else {}

        if df.empty:
            st.error(f"❌ No data for `{sym}`. Try adding .NS for Indian stocks.")
            return

        # ── AI MODE ───────────────────────────────────────────────────────────
        if st.session_state.get("mkt_ai"):
            if st.session_state.get("mkt_ai_res") is None:
                with st.spinner("🤖 SAGE AI analyzing — drawing support, resistance, patterns, indicators..."):
                    fund=_fundamental(sym)
                    ai_res=_ai_full_analysis(sym,name,tech,fund)
                st.session_state.mkt_ai_res=ai_res
                st.session_state.mkt_fund=fund
            else:
                ai_res=st.session_state.mkt_ai_res
                fund=st.session_state.get("mkt_fund",{})

            # Chart with AI drawings
            html=_chart_html(df,tech,ai_res,sym)
            components.html(html,height=CHART_H+10,scrolling=False)

            # Full report
            st.markdown(f"""<div style="background:#1e222d;border:1px solid #2a2e39;
            border-radius:8px;padding:6px 12px;margin:4px 0;display:flex;align-items:center;gap:8px;">
              <span style="color:#2962ff;font-size:14px;">🤖</span>
              <span style="color:#d1d4dc;font-weight:700;font-size:13px;">SAGE AI Analysis — {name}</span>
              <span style="background:#2962ff22;color:#2962ff;font-size:9px;padding:2px 6px;border-radius:8px;font-weight:700;">via {ai_res.get('_api','AI')}</span>
              <div style="flex:1;"></div>
            </div>""", unsafe_allow_html=True)

            _render_full_report(sym,name,tech,fund,ai_res)

            col_r1,col_r2=st.columns(2)
            with col_r1:
                if st.button("🔄 Refresh AI",key="mkt_refresh",type="primary"):
                    st.session_state.mkt_ai_res=None; st.rerun()
            with col_r2:
                if st.button("📊 Chart Only",key="mkt_c_only"):
                    st.session_state.mkt_ai=False; st.rerun()

        elif research_clicked:
            # Quick research report mode
            with st.spinner("Loading research data..."):
                fund=_fundamental(sym)
                ai_res=_ai_full_analysis(sym,name,tech,fund)
            # Chart
            html=_chart_html(df,tech,ai_res,sym)
            components.html(html,height=CHART_H+10,scrolling=False)
            _render_full_report(sym,name,tech,fund,ai_res)

        else:
            # ── TV CHART MODE ─────────────────────────────────────────────────
            tv_tf={"1D":"D","1H":"60","15m":"15","4H":"240","1W":"W","1M":"M"}.get(tf,"D")
            # Make sure tv_sym is valid
            if not tv_sym or tv_sym==sym:
                base=sym.replace(".NS","").replace("-USD","").replace(".BO","")
                tv_sym=TV_SYM_MAP.get(base, ("BINANCE:"+base+"USDT" if "USD" in sym else "NSE:"+base if ".NS" in sym else "NASDAQ:"+base))

            tv_html=f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}html,body{{background:#131722;width:100%;height:{CHART_H}px;overflow:hidden;}}</style>
</head><body>
<div class="tradingview-widget-container" style="width:100%;height:{CHART_H}px;">
  <div id="tv_c" style="width:100%;height:{CHART_H}px;"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({{
    "autosize":false,"width":"100%","height":{CHART_H},
    "symbol":"{tv_sym}","interval":"{tv_tf}",
    "timezone":"Asia/Kolkata","theme":"dark","style":"1","locale":"en",
    "toolbar_bg":"#1e222d","enable_publishing":false,"hide_top_toolbar":false,
    "hide_legend":false,"save_image":true,"container_id":"tv_c",
    "studies":["RSI@tv-basicstudies","MACD@tv-basicstudies","Volume@tv-basicstudies"],
    "overrides":{{"mainSeriesProperties.candleStyle.upColor":"#26a69a","mainSeriesProperties.candleStyle.downColor":"#ef5350"}},
    "show_popup_button":false
  }});
  </script>
</div></body></html>"""
            components.html(tv_html,height=CHART_H+10,scrolling=False)

            st.markdown(f"""<div style="background:#131722;border:1px solid #2962ff22;border-radius:8px;
            padding:6px 12px;margin-top:4px;display:flex;align-items:center;gap:8px;">
              <span style="color:#2962ff;">🤖</span>
              <span style="color:#9598a1;font-size:12px;">Click <b style="color:#2962ff;">🤖 AI</b> to auto-draw support/resistance, patterns, indicators + full research report</span>
              <span style="color:#6a6e7a;font-size:10px;margin-left:auto;">⭐ = Add to Favourites · 📋 = Research Report</span>
            </div>""", unsafe_allow_html=True)
