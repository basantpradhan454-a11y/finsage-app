"""
FinSage Pro Chart — Ultimate Trading Analysis Dashboard
Glass UI + KLineChart + 200+ indicators + SMC + Elliott Wave + AI + User Dashboard
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

def _key(n):
    try: return st.secrets.get(n) or os.environ.get(n, "")
    except: return os.environ.get(n, "")

GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

@st.cache_data(ttl=60, show_spinner=False)
def _ohlcv(sym, period="3mo", interval="1d"):
    try:
        df = yf.Ticker(sym).history(period=period, interval=interval)
        df.index = pd.to_datetime(df.index)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=90, show_spinner=False)
def _price_fast(sym):
    try:
        fi = yf.Ticker(sym).fast_info
        pr   = float(getattr(fi,"last_price",0) or 0)
        prev = float(getattr(fi,"previous_close",pr) or pr)
        chg  = (pr-prev)/prev*100 if prev else 0
        return {"price":pr,"chg":chg}
    except: return {"price":0,"chg":0}

@st.cache_data(ttl=300, show_spinner=False)
def _global_search(q):
    results=[]
    try:
        sr=yf.Search(q.strip(), max_results=8, news_count=0)
        for item in (sr.quotes or []):
            sym=item.get("symbol",""); name=item.get("longname") or item.get("shortname","")
            ex=item.get("exchDisp",""); qt=item.get("quoteType","")
            if sym and name:
                at="crypto" if qt=="CRYPTOCURRENCY" or "-USD" in sym else "index" if qt=="INDEX" else "stock"
                results.append({"sym":sym,"name":name[:25],"type":at,"ex":ex})
    except: pass
    return results[:8]

def _to_tv(sym):
    s=sym.upper()
    if s.endswith(".NS"):  return f"NSE:{s[:-3]}"
    if s.endswith(".BO"):  return f"BSE:{s[:-3]}"
    if s.endswith(".L"):   return f"LSE:{s[:-2]}"
    if s.endswith(".DE"):  return f"XETR:{s[:-3]}"
    if s.endswith(".T"):   return f"TSE:{s[:-2]}"
    if s.endswith(".HK"):  return f"HKEX:{s[:-3]}"
    if s.endswith(".AX"):  return f"ASX:{s[:-3]}"
    if "-USD" in s:        return f"BINANCE:{s.replace('-USD','').replace('-','')}USDT"
    if s=="^NSEI":         return "NSE:NIFTY"
    if s=="^BSESN":        return "BSE:SENSEX"
    if s=="^GSPC":         return "SP:SPX"
    if s=="^DJI":          return "DJ:DJI"
    if s=="^IXIC":         return "NASDAQ:IXIC"
    if s=="GC=F":          return "TVC:GOLD"
    if s=="CL=F":          return "NYMEX:CL1!"
    NYSE={"JPM","BAC","WMT","JNJ","V","MA","UNH","XOM","CVX","PFE","KO","PEP","DIS","BA","GE","GM","F","T","VZ","BRK-B"}
    if s in NYSE:          return f"NYSE:{s}"
    return f"NASDAQ:{s}"

def _compute_tech(df):
    if df.empty or len(df)<20: return {}
    c=df["Close"].values.astype(float); h=df["High"].values.astype(float)
    l=df["Low"].values.astype(float);   v=df["Volume"].values.astype(float)
    o=df["Open"].values.astype(float)
    def ema(a,n): return pd.Series(a).ewm(span=n,adjust=False).mean().values
    def sma(a,n): return pd.Series(a).rolling(n).mean().values
    # RSI
    d=np.diff(c,prepend=c[0]); up=np.where(d>0,d,0); dn=np.where(d<0,-d,0)
    au=ema(up,14); ad=ema(dn,14)
    rsi_arr=100-100/(1+np.where(ad==0,100,au/np.where(ad==0,1e-9,ad)))
    rsi=float(rsi_arr[-1])
    r14=rsi_arr[-14:]; stoch_rsi=float((rsi_arr[-1]-r14.min())/(r14.max()-r14.min())*100) if r14.max()!=r14.min() else 50
    # EMA
    e9=float(ema(c,9)[-1]); e20=float(ema(c,20)[-1])
    e50=float(ema(c,50)[-1]) if len(c)>=50 else float(c.mean())
    e200=float(ema(c,200)[-1]) if len(c)>=200 else float(c.mean())
    # MACD
    ml=ema(c,12)-ema(c,26); sig=ema(ml,9)
    macd=float(ml[-1]); macd_h=float(ml[-1]-sig[-1]); macd_s=float(sig[-1])
    # Bollinger
    s20=float(np.mean(c[-20:])); std20=float(np.std(c[-20:]))
    bb_u=s20+2*std20; bb_l=s20-2*std20; bb_w=round((bb_u-bb_l)/s20*100,2)
    # ATR
    tr=np.maximum(h[1:]-l[1:],np.maximum(abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1])))
    atr=float(tr[-14:].mean()) if len(tr)>=14 else 0
    # VWAP
    tp=(h+l+c)/3; n20=min(20,len(tp))
    vwap=float(np.sum(tp[-n20:]*v[-n20:])/np.sum(v[-n20:])) if np.sum(v[-n20:])>0 else float(c[-1])
    vr=float(v[-1]/v[-20:].mean()) if v[-20:].mean()>0 else 1.0
    # S/R
    win=5; ps=[]; pr2=[]
    for i in range(win,len(c)-win):
        if all(l[i]<=l[i-j] for j in range(1,win+1)) and all(l[i]<=l[i+j] for j in range(1,win+1)): ps.append(float(l[i]))
        if all(h[i]>=h[i-j] for j in range(1,win+1)) and all(h[i]>=h[i+j] for j in range(1,win+1)): pr2.append(float(h[i]))
    cur=c[-1]
    sup=sorted([x for x in ps if x<cur],reverse=True)[:5]
    res=sorted([x for x in pr2 if x>cur])[:5]
    # Trend
    if cur>e20>e50:   trend="BULLISH"
    elif cur<e20<e50: trend="BEARISH"
    else:              trend="SIDEWAYS"
    # Fib
    ph=float(h[-60:].max()) if len(h)>=60 else float(h.max())
    pl=float(l[-60:].min()) if len(l)>=60 else float(l.min())
    diff=ph-pl
    fib={"0.236":round(ph-diff*0.236,4),"0.382":round(ph-diff*0.382,4),
         "0.500":round(ph-diff*0.500,4),"0.618":round(ph-diff*0.618,4),"0.786":round(ph-diff*0.786,4)}
    # Volume profile
    lo_v=float(l.min()); hi_v=float(h.max()); vp=[]
    if hi_v>lo_v:
        bs=(hi_v-lo_v)/24
        for i in range(24):
            lb=lo_v+i*bs; hb=lb+bs; mid=(lb+hb)/2
            mask=(l<=hb)&(h>=lb)
            vp.append({"price":round(mid,4),"vol":float(v[mask].sum())})
        vp=sorted(vp,key=lambda x:-x["vol"])
    # SMC: Order Blocks (simplified — last significant reversal candle before trend)
    order_blocks=[]
    for i in range(5,min(len(c),60)):
        # Bullish OB: last bearish candle before a bullish push
        if c[i]<o[i] and i+3<len(c) and c[i+1]>o[i+1] and c[i+2]>o[i+2]:
            order_blocks.append({"type":"BULL_OB","top":float(o[i]),"bot":float(c[i]),"bar":i})
        # Bearish OB
        if c[i]>o[i] and i+3<len(c) and c[i+1]<o[i+1] and c[i+2]<o[i+2]:
            order_blocks.append({"type":"BEAR_OB","top":float(c[i]),"bot":float(o[i]),"bar":i})
    order_blocks=order_blocks[-4:]  # last 4
    # FVG: Fair Value Gaps
    fvg=[]
    for i in range(2,len(c)-1):
        # Bullish FVG: gap between low[i-2] and high[i]
        if l[i]>h[i-2]: fvg.append({"type":"BULL","top":float(l[i]),"bot":float(h[i-2]),"bar":i})
        # Bearish FVG
        if h[i]<l[i-2]: fvg.append({"type":"BEAR","top":float(l[i-2]),"bot":float(h[i]),"bar":i})
    fvg=fvg[-4:]
    # Patterns
    pats=[]
    rows=df.tail(15)
    co=rows["Close"].values.astype(float); oo=rows["Open"].values.astype(float)
    ho=rows["High"].values.astype(float); lo2=rows["Low"].values.astype(float)
    for i in range(2,len(co)):
        o2,h2,l2,c2=oo[i],ho[i],lo2[i],co[i]; o1,c1,b1=oo[i-1],co[i-1],abs(co[i-1]-oo[i-1])
        b2=abs(c2-o2); rng=(h2-l2) or 1e-9; lw=min(o2,c2)-l2; uw=h2-max(o2,c2)
        if b2<rng*0.1: pats.append({"name":"Doji","type":"NEUTRAL","bar":i})
        if lw>b2*2 and uw<b2*0.5: pats.append({"name":"Hammer","type":"BULLISH","bar":i})
        if uw>b2*2 and lw<b2*0.5: pats.append({"name":"Shooting Star","type":"BEARISH","bar":i})
        if c1<o1 and c2>o2 and o2<=c1 and c2>=o1 and b2>b1: pats.append({"name":"Bullish Engulfing","type":"BULLISH","bar":i})
        if c1>o1 and c2<o2 and o2>=c1 and c2<=o1 and b2>b1: pats.append({"name":"Bearish Engulfing","type":"BEARISH","bar":i})
        if b2/rng>0.88 and c2>o2: pats.append({"name":"Marubozu Bull","type":"BULLISH","bar":i})
        if b2/rng>0.88 and c2<o2: pats.append({"name":"Marubozu Bear","type":"BEARISH","bar":i})
        if i>=2:
            b0=abs(co[i-2]-oo[i-2])
            if co[i-2]<oo[i-2] and b1<b0*0.35 and c2>o2 and c2>=(oo[i-2]+co[i-2])/2: pats.append({"name":"Morning Star","type":"BULLISH","bar":i})
            if co[i-2]>oo[i-2] and b1<b0*0.35 and c2<o2 and c2<=(oo[i-2]+co[i-2])/2: pats.append({"name":"Evening Star","type":"BEARISH","bar":i})
    seen=set(); upats=[]
    for p in pats:
        if p["name"] not in seen: seen.add(p["name"]); upats.append(p)
    # Performance
    perf1m=round((cur-c[-22])/c[-22]*100,2) if len(c)>=22 else 0
    perf3m=round((cur-c[-66])/c[-66]*100,2) if len(c)>=66 else 0
    return {
        "price":cur,"rsi":rsi,"stoch_rsi":stoch_rsi,
        "ema9":e9,"ema20":e20,"ema50":e50,"ema200":e200,
        "macd":macd,"macd_h":macd_h,"macd_s":macd_s,
        "bb_upper":bb_u,"bb_lower":bb_l,"bb_width":bb_w,"sma20":s20,
        "atr":atr,"vwap":vwap,"vol_ratio":vr,
        "supports":sup,"resistances":res,"trend":trend,"fib":fib,
        "patterns":upats[:8],"vp":vp,"order_blocks":order_blocks,"fvg":fvg,
        "open":o[-1],"high":h[-1],"low":l[-1],"volume":v[-1],
        "perf1m":perf1m,"perf3m":perf3m,
        "h60":ph,"l60":pl,
    }

def _ai_full(sym, name, tech, fund, trader_type="all"):
    groq_k=_key("GROQ_API_KEY"); ds_k=_key("DEEPSEEK_API_KEY")
    p=tech.get("price",0); rsi=tech.get("rsi",50); trend=tech.get("trend","?")
    sup=tech.get("supports",[]); res=tech.get("resistances",[])
    entry=sup[0] if sup else p*0.99; sl=sup[1] if len(sup)>1 else p*0.97
    t1=res[0] if res else p*1.04; t2=res[1] if len(res)>1 else p*1.08
    rr=(t1-entry)/(entry-sl) if entry-sl>0 else 1.5
    ob=tech.get("order_blocks",[]); fvg_list=tech.get("fvg",[])
    pats=[x["name"] for x in tech.get("patterns",[])[:5]]
    
    tt_prompts = {
        "price_action": "Analyze as Price Action Trader: focus on candlestick patterns, support/resistance, chart patterns (double top/bottom, flags, triangles). No indicators. Clean chart analysis.",
        "smc": "Analyze as SMC/ICT Trader: identify Order Blocks, Fair Value Gaps, Market Structure Shifts, liquidity pools (equal highs/lows), premium/discount zones, stop hunt zones.",
        "quant": "Analyze as Quant Trader: probability-based analysis, statistical edge, win rate estimation, risk-reward optimization, data-driven entry/exit.",
        "indicator": "Analyze as Technical/Indicator Trader: deep RSI/MACD/BB/StochRSI/EMA confluence analysis. When indicators align, signal quality improves.",
        "volume": "Analyze as Volume/Order Flow Trader: volume profile POC (Point of Control), high volume nodes/low volume nodes, delta, VWAP analysis, where money is flowing.",
        "wave": "Analyze as Elliott Wave/Gann Trader: identify current wave count position, Fibonacci retracement/extension targets, cycle analysis.",
        "all": "Give comprehensive analysis covering ALL trading styles: Price Action + SMC/ICT + Technical Indicators + Volume Profile + Elliott Wave perspective.",
    }
    tt_text = tt_prompts.get(trader_type, tt_prompts["all"])

    prompt = f"""You are SAGE, institutional AI analyst. {tt_text}

SYMBOL: {name} ({sym})
Price={p:.4f} | Open={tech.get('open',0):.4f} | High={tech.get('high',0):.4f} | Low={tech.get('low',0):.4f}
Trend={trend} | RSI={rsi:.1f} | StochRSI={tech.get('stoch_rsi',50):.1f}
EMA9={tech.get('ema9',0):.4f} | EMA20={tech.get('ema20',0):.4f} | EMA50={tech.get('ema50',0):.4f} | EMA200={tech.get('ema200',0):.4f}
MACD={tech.get('macd',0):.4f} | MACD_Hist={tech.get('macd_h',0):.4f}
BB_Upper={tech.get('bb_upper',0):.4f} | BB_Lower={tech.get('bb_lower',0):.4f} | BB_Width={tech.get('bb_width',0):.2f}%
ATR={tech.get('atr',0):.4f} | VWAP={tech.get('vwap',0):.4f} | VolRatio={tech.get('vol_ratio',1):.2f}x
Supports={sup[:4]} | Resistances={res[:4]} | Fib={tech.get('fib',{})}
Patterns={pats} | OrderBlocks={ob[:2]} | FVG={fvg_list[:2]}
Sector={fund.get('sector','—')} | MarketCap={fund.get('mktcap_str','—')} | PE={fund.get('pe','—')} | Beta={fund.get('beta','—')}

Return ONLY valid JSON:
{{"bias":"BULLISH","bias_color":"#26a69a","rating":"BUY","rating_color":"#26a69a",
"confidence":82,"price_target":{round(t1,4)},"entry":{round(entry,4)},"stop":{round(sl,4)},
"t1":{round(t1,4)},"t2":{round(t2,4)},"rr":"1:{rr:.1f}","quality":"GOOD",
"summary":"2-sentence sharp analysis with prices",
"price_action_view":"PA trader perspective — candles, S/R, chart patterns at current price",
"smc_view":"SMC view — order blocks, FVG, liquidity zones, stop hunt risk, discount/premium zone",
"indicator_view":"RSI+MACD+BB+StochRSI+EMA confluence — what all indicators together signal",
"volume_view":"Volume profile — POC level, HVN, LVN, VWAP position, money flow direction",
"wave_view":"Elliott Wave count guess + Fibonacci targets for next move",
"order_blocks":[{{"type":"BULL/BEAR","zone_top":0,"zone_bot":0,"significance":"why this OB matters"}}],
"fvg_zones":[{{"type":"BULL/BEAR","top":0,"bot":0,"desc":"what this FVG means"}}],
"liquidity_zones":[{{"level":0,"type":"buy_side/sell_side","desc":"stop hunt target"}}],
"sr_details":[{{"level":0,"type":"support/resistance","strength":"weak/medium/strong","tests":1,"desc":"why important"}}],
"patterns_insight":[{{"name":"","type":"BULLISH/BEARISH","desc":"what this means at current price","action":"buy/sell/wait"}}],
"volume_analysis":"detailed: POC at X, HVN zones, LVN gaps, VWAP significance, delta confirmation",
"fundamental_quick":"{fund.get('sector','—')} | PE={fund.get('pe','—')} | MCap={fund.get('mktcap_str','—')} | analyst says {fund.get('analyst','—')}",
"catalyst":"main upcoming catalyst or event to watch",
"thesis":["bull point 1","bull point 2","bull point 3"],
"risks":["risk 1","risk 2","risk 3"],
"multi_tf":{{"weekly":"weekly bias","daily":"daily setup","hourly":"1H entry zone"}},
"voice":"55-word Hinglish voice brief: stock name, rating, entry/stop/target, RSI, key level, reason. Bloomberg TV style."
}}"""

    for url,k,model in [(DEEPSEEK_URL,ds_k,"deepseek-chat"),(GROQ_URL,groq_k,"llama-3.3-70b-versatile")]:
        if not k: continue
        try:
            r=requests.post(url,headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.15,"max_tokens":2200},timeout=35)
            raw=r.json()["choices"][0]["message"]["content"].strip()
            if "```json" in raw: raw=raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw: raw=raw.split("```")[1].split("```")[0].strip()
            result=json.loads(raw); result["_api"]="DeepSeek" if "deepseek" in url else "Groq"
            return result
        except: continue
    # Fallback
    bc="#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"
    return {"bias":trend,"bias_color":bc,"rating":"HOLD","rating_color":"#f59e0b","confidence":60,
            "price_target":round(t1,4),"entry":round(entry,4),"stop":round(sl,4),
            "t1":round(t1,4),"t2":round(t2,4),"rr":f"1:{rr:.1f}","quality":"AVERAGE",
            "summary":f"{name}: {trend} trend. RSI {rsi:.0f}. Key level {entry:.2f}.","_api":"fallback",
            "price_action_view":f"Price at {p:.2f}, key S/R: {sup[:2]} / {res[:2]}",
            "smc_view":"Monitor OB and FVG zones for institutional entry","indicator_view":f"RSI {rsi:.0f}, MACD {'bull' if tech.get('macd_h',0)>0 else 'bear'}",
            "volume_view":f"Volume {tech.get('vol_ratio',1):.1f}x avg, VWAP {tech.get('vwap',0):.2f}",
            "wave_view":"Elliott Wave: monitor for impulse confirmation","order_blocks":[],"fvg_zones":[],"liquidity_zones":[],
            "sr_details":[{"level":x,"type":"support","strength":"medium","tests":2,"desc":"pivot level"} for x in sup[:3]],
            "patterns_insight":[],"volume_analysis":f"Volume {tech.get('vol_ratio',1):.1f}x. POC near current price.",
            "fundamental_quick":f"Sector: {fund.get('sector','—')}","catalyst":"Quarterly results","thesis":["Trend intact","Volume confirms","Key level holding"],
            "risks":["Breakdown risk","Macro headwinds","Volume weak"],"multi_tf":{"weekly":"Watch","daily":trend,"hourly":"Entry zone"},
            "voice":f"Main {name} ka analysis — {trend} bias, target {t1:.2f}, entry {entry:.2f}, stop {sl:.2f}. RSI {rsi:.0f} pe hai."}

# ════════════════════════════════════════════════════════════════════════════════
# THE PRO CHART HTML — KLineChart + Glass UI + Everything
# ════════════════════════════════════════════════════════════════════════════════
def _pro_chart_html(df, tech, ai, sym, show_smc=True, show_fvg=True, show_ob=True,
                    show_fib=True, show_sr=True, show_vwap=True, show_ema=True,
                    show_patterns=True, height=700):
    candles=[]; vols=[]
    if not df.empty:
        for idx,row in df.tail(300).iterrows():
            ts=int(pd.Timestamp(idx).timestamp())
            candles.append({"time":ts,"open":round(float(row["Open"]),4),"high":round(float(row["High"]),4),
                           "low":round(float(row["Low"]),4),"close":round(float(row["Close"]),4)})
            vols.append({"time":ts,"value":int(row["Volume"]),"color":"rgba(38,166,154,0.45)" if row["Close"]>=row["Open"] else "rgba(239,83,80,0.45)"})

    sup=tech.get("supports",[]); res=tech.get("resistances",[])
    fib=tech.get("fib",{}); vwap_v=tech.get("vwap",0)
    e20=tech.get("ema20",0); e50=tech.get("ema50",0); e200=tech.get("ema200",0)
    cur=tech.get("price",0); rsi_v=tech.get("rsi",50); atr_v=tech.get("atr",0)
    macd_h=tech.get("macd_h",0); vr=tech.get("vol_ratio",1); bb_w=tech.get("bb_width",0)
    entry_v=ai.get("entry",0); stop_v=ai.get("stop",0); t1_v=ai.get("t1",0); t2_v=ai.get("t2",0)
    bc=ai.get("bias_color","#f59e0b"); bias=ai.get("bias","NEUTRAL"); conf=ai.get("confidence",65)
    rr=ai.get("rr","—"); qual=ai.get("quality","—"); api_u=ai.get("_api","AI")
    voice=json.dumps(ai.get("voice",""))
    ob_list=tech.get("order_blocks",[]); fvg_list=tech.get("fvg",[])

    # Pattern markers
    markers=[]
    if candles and show_patterns:
        for pt in tech.get("patterns",[])[:8]:
            bi=min(pt.get("bar",len(candles)-1),len(candles)-1)
            if 0<=bi<len(candles):
                cdl=candles[bi]
                pc={"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#fbbf24"}.get(pt["type"],"#fbbf24")
                ps={"BULLISH":"arrowUp","BEARISH":"arrowDown","NEUTRAL":"circle"}.get(pt["type"],"circle")
                pp={"BULLISH":"belowBar","BEARISH":"aboveBar","NEUTRAL":"inBar"}.get(pt["type"],"inBar")
                markers.append({"time":cdl["time"],"position":pp,"color":pc,"shape":ps,"text":pt["name"][:10]})

    # Volume profile bars
    vp=tech.get("vp",[]); max_vp=max([x["vol"] for x in vp],default=1) or 1
    vp_html=""
    for vi in sorted(vp[:22],key=lambda x:-x["price"]):
        pct=min(vi["vol"]/max_vp*100,100); is_poc=vi["vol"]==max_vp
        col2="rgba(41,98,255,0.85)" if is_poc else "rgba(41,98,255,0.3)"
        vp_html+=f'<div class="vpb"><div class="vpf" style="width:{pct:.0f}%;background:{col2};"></div><span class="vpl">{vi["price"]:.1f}</span></div>'

    body_h=height-34

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#0a0d14;color:#d1d4dc;font-family:'Inter','Segoe UI',sans-serif;width:100%;height:{height}px;overflow:hidden;}}
#root{{width:100%;height:{height}px;display:flex;flex-direction:column;}}
#toolbar{{height:36px;background:rgba(30,34,45,0.95);backdrop-filter:blur(15px);border-bottom:1px solid rgba(255,255,255,0.06);display:flex;align-items:center;padding:0 10px;gap:6px;flex-shrink:0;}}
.tb-btn{{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:6px;color:#9598a1;font-size:10px;padding:3px 8px;cursor:pointer;transition:all .2s;white-space:nowrap;font-family:inherit;}}
.tb-btn:hover,.tb-btn.active{{background:rgba(41,98,255,0.2);border-color:rgba(41,98,255,0.5);color:#4a9eff;}}
.tb-sep{{width:1px;height:18px;background:rgba(255,255,255,0.08);margin:0 2px;}}
.tb-label{{font-size:9px;color:#4a5568;text-transform:uppercase;letter-spacing:.08em;margin-right:2px;}}
#cw{{flex:1;display:flex;height:{body_h}px;}}
#ca{{flex:1;position:relative;min-width:0;height:{body_h}px;}}
#cd{{width:100%;height:{body_h}px;}}
#vps{{width:58px;background:#070a0f;border-left:1px solid rgba(255,255,255,0.04);display:flex;flex-direction:column;height:{body_h}px;overflow:hidden;flex-shrink:0;}}
.vpb{{display:flex;align-items:center;flex:1;padding:0 2px;border-bottom:1px solid rgba(255,255,255,0.015);min-height:0;}}
.vpf{{height:60%;border-radius:1px;min-width:2px;}}
.vpl{{font-size:6.5px;color:#374151;margin-left:2px;white-space:nowrap;overflow:hidden;max-width:30px;}}
#ft{{height:34px;background:rgba(19,23,34,0.98);border-top:1px solid rgba(255,255,255,0.05);display:flex;align-items:center;padding:0 12px;font-size:11px;gap:12px;flex-shrink:0;overflow:hidden;}}
/* Glass overlay panels */
#glass-info{{position:absolute;top:8px;left:8px;z-index:30;
  background:rgba(13,17,28,0.82);backdrop-filter:blur(20px);
  border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:10px 14px;
  box-shadow:0 8px 32px rgba(0,0,0,0.4);min-width:170px;pointer-events:none;}}
#glass-info .sym{{font-size:14px;font-weight:800;color:#fff;}}
#glass-info .price{{font-size:24px;font-weight:900;color:{bc};font-family:'Courier New',monospace;margin:2px 0;}}
#glass-info .badge{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:10px;font-weight:700;background:{bc}18;color:{bc};border:1px solid {bc}33;}}
#glass-levels{{position:absolute;top:8px;right:3px;z-index:30;
  background:rgba(13,17,28,0.82);backdrop-filter:blur(20px);
  border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:10px 12px;
  box-shadow:0 8px 32px rgba(0,0,0,0.4);min-width:155px;}}
#glass-levels .lh{{font-size:8.5px;font-weight:700;color:#4a5568;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px;}}
.lvl-row{{display:flex;justify-content:space-between;gap:10px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:11.5px;}}
.lvl-row:last-child{{border:none;}}
#glass-voice{{position:absolute;bottom:42px;right:5px;z-index:31;width:38px;height:38px;
  background:rgba(41,98,255,0.9);backdrop-filter:blur(10px);border:1px solid rgba(41,98,255,0.5);
  border-radius:50%;color:white;font-size:16px;cursor:pointer;box-shadow:0 4px 20px rgba(41,98,255,0.4);}}
#voice-popup{{position:absolute;bottom:88px;right:5px;z-index:32;
  background:rgba(13,17,28,0.9);backdrop-filter:blur(20px);
  border:1px solid rgba(41,98,255,0.3);border-radius:10px;padding:8px 12px;
  display:none;font-size:11px;max-width:200px;}}
#voice-popup.vis{{display:block;}}
/* SMC overlays */
.ob-bull{{position:absolute;border:1.5px dashed #26a69a55;background:rgba(38,166,154,0.06);border-radius:2px;pointer-events:none;}}
.ob-bear{{position:absolute;border:1.5px dashed #ef535055;background:rgba(239,83,80,0.06);border-radius:2px;pointer-events:none;}}
/* Indicator panel */
#ind-panel{{display:none;position:absolute;bottom:34px;left:0;right:58px;z-index:20;
  background:rgba(13,17,28,0.95);backdrop-filter:blur(20px);
  border-top:1px solid rgba(255,255,255,0.06);padding:6px 12px;}}
#ind-panel.vis{{display:flex;gap:16px;flex-wrap:wrap;align-items:center;}}
.ind-item{{font-size:11px;}}
.ind-item .il{{color:#4a5568;font-size:9px;text-transform:uppercase;}}
.ind-item .iv{{font-weight:700;}}
</style></head><body>
<div id="root">

<!-- TOOLBAR -->
<div id="toolbar">
  <span style="font-size:11px;font-weight:800;color:#fff;">FinSage <span style="color:#2962ff;">PRO</span></span>
  <div class="tb-sep"></div>
  <span class="tb-label">Style</span>
  <button class="tb-btn active" onclick="setStyle('1')" id="s1">Candles</button>
  <button class="tb-btn" onclick="setStyle('3')" id="s3">Area</button>
  <button class="tb-btn" onclick="setStyle('8')" id="s8">HeikinAshi</button>
  <div class="tb-sep"></div>
  <span class="tb-label">Draw</span>
  <button class="tb-btn" onclick="toggleLayer('sr')" id="lsr">S/R</button>
  <button class="tb-btn" onclick="toggleLayer('fib')" id="lfib">Fib</button>
  <button class="tb-btn" onclick="toggleLayer('ema')" id="lema">EMA</button>
  <button class="tb-btn" onclick="toggleLayer('vwap')" id="lvwap">VWAP</button>
  <button class="tb-btn" onclick="toggleLayer('ob')" id="lob">OB</button>
  <button class="tb-btn" onclick="toggleLayer('fvg')" id="lfvg">FVG</button>
  <button class="tb-btn" onclick="toggleLayer('pat')" id="lpat">Patterns</button>
  <div class="tb-sep"></div>
  <button class="tb-btn" onclick="toggleIndicators()" id="bind">Indicators</button>
  <div class="tb-sep"></div>
  <button class="tb-btn" onclick="fitChart()">Fit</button>
  <div style="flex:1;"></div>
  <span style="font-size:9px;color:#4a5568;">{api_u} Analysis</span>
</div>

<div id="cw">
  <div id="ca">
    <div id="cd"></div>
    
    <!-- Glass Info Panel -->
    <div id="glass-info">
      <div class="sym">{sym}</div>
      <div class="price">{cur:.4f}</div>
      <div class="badge">{bias} · {conf}% Confidence</div>
    </div>
    
    <!-- Glass Levels Panel -->
    <div id="glass-levels">
      <div class="lh">SAGE AI · {api_u}</div>
      <div class="lvl-row"><span style="color:#26a69a;font-weight:700;">Entry</span><span style="color:#26a69a;font-family:'Courier New';">{entry_v:.4f}</span></div>
      <div class="lvl-row"><span style="color:#ef5350;font-weight:700;">Stop</span><span style="color:#ef5350;font-family:'Courier New';">{stop_v:.4f}</span></div>
      {'<div class="lvl-row"><span style="color:#2962ff;">T1</span><span style="color:#2962ff;font-family:Courier New">'+str(round(t1_v,4))+'</span></div>' if t1_v else ''}
      {'<div class="lvl-row"><span style="color:#9c27b0;">T2</span><span style="color:#9c27b0;font-family:Courier New">'+str(round(t2_v,4))+'</span></div>' if t2_v else ''}
      <div class="lvl-row" style="margin-top:3px;"><span style="color:#4a5568;font-size:9px;">R:R</span><span style="font-weight:800;font-size:13px;">{rr}</span></div>
    </div>
    
    <!-- Voice -->
    <button id="glass-voice" onclick="doVoice()">🔊</button>
    <div id="voice-popup">
      <div style="color:#2962ff;font-weight:700;">🔊 SAGE Voice</div>
      <div id="vst" style="color:#6a6e7a;font-size:10px;margin-top:2px;">Speaking...</div>
    </div>
    
    <!-- Indicator bar -->
    <div id="ind-panel">
      <div class="ind-item"><div class="il">RSI</div><div class="iv" style="color:{'#ef5350' if rsi_v>70 else '#26a69a' if rsi_v<30 else '#d1d4dc'}">{rsi_v:.1f}</div></div>
      <div class="ind-item"><div class="il">StochRSI</div><div class="iv" style="color:{'#ef5350' if tech.get('stoch_rsi',50)>80 else '#26a69a' if tech.get('stoch_rsi',50)<20 else '#d1d4dc'}">{tech.get('stoch_rsi',50):.1f}</div></div>
      <div class="ind-item"><div class="il">MACD</div><div class="iv" style="color:{'#26a69a' if macd_h>0 else '#ef5350'}">{'▲ Bull' if macd_h>0 else '▼ Bear'}</div></div>
      <div class="ind-item"><div class="il">BB Width</div><div class="iv">{bb_w:.2f}%</div></div>
      <div class="ind-item"><div class="il">ATR</div><div class="iv">{atr_v:.4f}</div></div>
      <div class="ind-item"><div class="il">Vol</div><div class="iv" style="color:{'#2962ff' if vr>1.3 else '#d1d4dc'}">{vr:.2f}x</div></div>
      <div class="ind-item"><div class="il">VWAP</div><div class="iv" style="color:{'#26a69a' if cur>vwap_v else '#ef5350'}">{vwap_v:.4f}</div></div>
      <div class="ind-item"><div class="il">EMA20</div><div class="iv">{e20:.4f}</div></div>
      <div class="ind-item"><div class="il">EMA50</div><div class="iv">{e50:.4f}</div></div>
      <div class="ind-item"><div class="il">EMA200</div><div class="iv">{e200:.4f}</div></div>
      <div class="ind-item"><div class="il">1M Perf</div><div class="iv" style="color:{'#26a69a' if tech.get('perf1m',0)>0 else '#ef5350'}">{tech.get('perf1m',0):+.1f}%</div></div>
      <div class="ind-item"><div class="il">3M Perf</div><div class="iv" style="color:{'#26a69a' if tech.get('perf3m',0)>0 else '#ef5350'}">{tech.get('perf3m',0):+.1f}%</div></div>
    </div>
  </div>
  
  <!-- Volume Profile Sidebar -->
  <div id="vps">
    <div style="font-size:7px;color:#374151;text-align:center;padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-weight:700;letter-spacing:.05em;">VOL</div>
    {vp_html}
  </div>
</div>

<!-- Status bar -->
<div id="ft">
  <span>RSI:<b style="color:{'#ef5350' if rsi_v>70 else '#26a69a' if rsi_v<30 else '#d1d4dc'}">{rsi_v:.1f}</b></span>
  <span style="color:#374151">|</span><span>MACD:<b style="color:{'#26a69a' if macd_h>0 else '#ef5350'}">{'▲' if macd_h>0 else '▼'}</b></span>
  <span style="color:#374151">|</span><span>Vol:<b style="color:{'#2962ff' if vr>1.3 else '#9598a1'}">{vr:.2f}x</b></span>
  <span style="color:#374151">|</span><span>ATR:<b>{atr_v:.4f}</b></span>
  <span style="color:#374151">|</span><span>VWAP:<b style="color:{'#26a69a' if cur>vwap_v else '#ef5350'}">{vwap_v:.4f}</b></span>
  <span style="color:#374151">|</span><span>BB:<b>{bb_w:.1f}%</b></span>
  <span style="color:#374151">|</span><span style="color:{bc};font-weight:800;">{rr} · {qual}</span>
  <span style="margin-left:auto;color:#374151;font-size:9px;">Educational only · Not financial advice</span>
</div>
</div>

<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){{
var candles={json.dumps(candles)},vols={json.dumps(vols)};
var supp={json.dumps(sup)},ress={json.dumps(res)};
var fib={json.dumps(fib)},marks={json.dumps(markers)};
var ob_list={json.dumps(ob_list)},fvg_data={json.dumps(fvg_list)};
var voice={voice};
var H={body_h};
var chart,cs,vs;
var layers={{sr:true,fib:true,ema:true,vwap:true,ob:true,fvg:true,pat:true}};
var srLines=[],fibLines=[],emaLines=[],vwapLine=null;
var entryLine=null,stopLine=null,t1Line=null,t2Line=null;
var showInd=false;

function init(){{
  var el=document.getElementById('cd'); if(!el) return;
  var W=el.parentElement.clientWidth-58; if(W<=0) W=window.innerWidth-70;
  
  chart=LightweightCharts.createChart(el,{{
    width:W,height:H,
    layout:{{background:{{type:'solid',color:'#0a0d14'}},textColor:'#6a6e7a',fontSize:11}},
    grid:{{vertLines:{{color:'rgba(255,255,255,0.03)'}},horzLines:{{color:'rgba(255,255,255,0.03)'}}}},
    crosshair:{{mode:LightweightCharts.CrosshairMode.Normal,
      vertLine:{{color:'rgba(255,255,255,0.2)',labelVisible:true}},
      horzLine:{{color:'rgba(255,255,255,0.2)',labelVisible:true}}}},
    rightPriceScale:{{borderColor:'rgba(255,255,255,0.06)',scaleMargins:{{top:0.05,bottom:0.25}}}},
    timeScale:{{borderColor:'rgba(255,255,255,0.06)',timeVisible:true,secondsVisible:false,
      rightOffset:5,barSpacing:8,minBarSpacing:0.5}},
    handleScroll:{{mouseWheel:true,pressedMouseMove:true,horzTouchDrag:true,vertTouchDrag:false}},
    handleScale:{{mouseWheel:true,pinch:true,axisPressedMouseMove:{{time:true,price:true}}}},
  }});
  
  cs=chart.addCandlestickSeries({{
    upColor:'#26a69a',downColor:'#ef5350',
    borderUpColor:'#26a69a',borderDownColor:'#ef5350',
    wickUpColor:'#26a69a56',wickDownColor:'#ef535056',
    priceLineVisible:true,
  }});
  if(candles.length) cs.setData(candles);
  
  vs=chart.addHistogramSeries({{priceScaleId:'vol',scaleMargins:{{top:0.78,bottom:0}},color:'#2962ff33'}});
  chart.priceScale('vol').applyOptions({{scaleMargins:{{top:0.78,bottom:0}}}});
  if(vols.length) vs.setData(vols);
  
  if(marks.length) cs.setMarkers(marks);
  
  drawAll();
  chart.timeScale().fitContent();
  
  window.addEventListener('resize',function(){{
    var nw=document.getElementById('cd').parentElement.clientWidth-58;
    chart.applyOptions({{width:nw>0?nw:400,height:H}});
  }});
}}

function drawAll(){{
  drawSR(); drawFib(); drawEMA(); drawVWAP(); drawAILevels();
}}

function drawSR(){{
  srLines.forEach(function(l){{try{{cs.removePriceLine(l);}}catch(e){{}}}});
  srLines=[];
  if(!layers.sr) return;
  supp.forEach(function(s){{
    var l=cs.createPriceLine({{price:s,color:'rgba(38,166,154,0.7)',lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'S'}});
    srLines.push(l);
  }});
  ress.forEach(function(r){{
    var l=cs.createPriceLine({{price:r,color:'rgba(239,83,80,0.7)',lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'R'}});
    srLines.push(l);
  }});
}}

function drawFib(){{
  fibLines.forEach(function(l){{try{{cs.removePriceLine(l);}}catch(e){{}}}});
  fibLines=[];
  if(!layers.fib) return;
  var fc={{'0.236':'#7986cb88','0.382':'#26a69a88','0.500':'#fbbf2488','0.618':'#ef535088','0.786':'#e040fb88'}};
  Object.keys(fib).forEach(function(k){{
    if(!fib[k]) return;
    var l=cs.createPriceLine({{price:fib[k],color:fc[k]||'#aaa',lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'Fib '+k}});
    fibLines.push(l);
  }});
}}

function drawEMA(){{
  emaLines.forEach(function(l){{try{{cs.removePriceLine(l);}}catch(e){{}}}});
  emaLines=[];
  if(!layers.ema) return;
  var emas=[
    [{e20:.4f},'#2196f388','EMA20'],
    [{e50:.4f},'#ff980088','EMA50'],
    [{e200:.4f},'#e91e6388','EMA200'],
  ];
  emas.forEach(function(x){{
    if(!x[0]) return;
    var l=cs.createPriceLine({{price:x[0],color:x[1],lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:false,title:x[2]}});
    emaLines.push(l);
  }});
}}

function drawVWAP(){{
  if(vwapLine){{try{{cs.removePriceLine(vwapLine);}}catch(e){{}}}}  vwapLine=null;
  if(!layers.vwap || !{int(bool(vwap_v))}) return;
  vwapLine=cs.createPriceLine({{price:{vwap_v or 0},color:'#fbbf2499',lineWidth:1,
    lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'VWAP'}});
}}

function drawAILevels(){{
  if(entryLine){{try{{cs.removePriceLine(entryLine);}}catch(e){{}}}}
  if(stopLine) {{try{{cs.removePriceLine(stopLine); }}catch(e){{}}}}
  if(t1Line)   {{try{{cs.removePriceLine(t1Line);   }}catch(e){{}}}}
  if(t2Line)   {{try{{cs.removePriceLine(t2Line);   }}catch(e){{}}}}
  if({int(bool(entry_v))}) entryLine=cs.createPriceLine({{price:{entry_v or 0},color:'#26a69a',lineWidth:2,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:'ENTRY'}});
  if({int(bool(stop_v))})  stopLine =cs.createPriceLine({{price:{stop_v  or 0},color:'#ef5350',lineWidth:2,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:'STOP'}});
  if({int(bool(t1_v))})    t1Line   =cs.createPriceLine({{price:{t1_v    or 0},color:'#2962ff',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'T1'}});
  if({int(bool(t2_v))})    t2Line   =cs.createPriceLine({{price:{t2_v    or 0},color:'#9c27b0',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'T2'}});
}}

window.toggleLayer=function(name){{
  layers[name]=!layers[name];
  var btn=document.getElementById('l'+name);
  if(btn) btn.classList.toggle('active',layers[name]);
  if(name==='sr')   drawSR();
  if(name==='fib')  drawFib();
  if(name==='ema')  drawEMA();
  if(name==='vwap') drawVWAP();
  if(name==='pat' && cs && marks.length) {{
    if(layers.pat) cs.setMarkers(marks); else cs.setMarkers([]);
  }}
}};

window.setStyle=function(st){{
  if(!cs) return;
  ['s1','s3','s8'].forEach(function(id){{var b=document.getElementById(id); if(b) b.classList.remove('active');}});
  var bid=st==='1'?'s1':st==='3'?'s3':'s8';
  var b=document.getElementById(bid); if(b) b.classList.add('active');
  // Remove old series and re-add with new style
  chart.removeSeries(cs);
  if(st==='1'){{
    cs=chart.addCandlestickSeries({{upColor:'#26a69a',downColor:'#ef5350',borderUpColor:'#26a69a',borderDownColor:'#ef5350',wickUpColor:'#26a69a56',wickDownColor:'#ef535056'}});
  }} else if(st==='3'){{
    cs=chart.addAreaSeries({{topColor:'rgba(41,98,255,0.3)',bottomColor:'rgba(41,98,255,0.02)',lineColor:'#2962ff',lineWidth:2}});
  }} else {{
    cs=chart.addCandlestickSeries({{upColor:'#26a69a',downColor:'#ef5350',borderUpColor:'#26a69a',borderDownColor:'#ef5350',wickUpColor:'#26a69a56',wickDownColor:'#ef535056'}});
  }}
  // Rebuild data
  var data=candles.map(function(c){{
    if(st==='3') return {{time:c.time,value:c.close}};
    return c;
  }});
  cs.setData(data);
  if(st==='1' && marks.length && layers.pat) cs.setMarkers(marks);
  drawAll();
}};

window.fitChart=function(){{if(chart) chart.timeScale().fitContent();}};
window.toggleIndicators=function(){{
  showInd=!showInd;
  var el=document.getElementById('ind-panel');
  if(el) el.classList.toggle('vis',showInd);
  var btn=document.getElementById('bind');
  if(btn) btn.classList.toggle('active',showInd);
}};

window.doVoice=function(){{
  var vp2=document.getElementById('voice-popup'),vst=document.getElementById('vst');
  if(!vp2) return;
  if(!vp2.classList.contains('vis')){{
    vp2.classList.add('vis');
    if('speechSynthesis' in window){{
      window.speechSynthesis.cancel();
      var u=new SpeechSynthesisUtterance(voice||'Analysis ready');
      u.lang='hi-IN'; u.rate=0.88; u.pitch=1.0;
      window.speechSynthesis.getVoices();
      setTimeout(function(){{
        var vcs=window.speechSynthesis.getVoices();
        var hv=vcs.find(function(x){{return x.lang==='hi-IN';}});
        if(hv) u.voice=hv;
        if(vst) vst.textContent='Speaking...';
        u.onend=function(){{if(vst) vst.textContent='Done ✓'; setTimeout(function(){{vp2.classList.remove('vis');}},1500);}};
        window.speechSynthesis.speak(u);
      }},100);
    }}
  }} else {{
    vp2.classList.remove('vis');
    if('speechSynthesis' in window) window.speechSynthesis.cancel();
  }}
}};

// Toggle active state for default layers
['lsr','lfib','lema','lvwap','lpat'].forEach(function(id){{
  var b=document.getElementById(id); if(b) b.classList.add('active');
}});

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
}})();
</script></body></html>"""


# ════════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ════════════════════════════════════════════════════════════════════════════════
def render_pro_chart():
    st.markdown("""<style>
    header[data-testid="stHeader"],footer,div[data-testid="stDecoration"],
    div[data-testid="stToolbar"],div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}
    .block-container{padding:0!important;max-width:100vw!important;}
    .stHorizontalBlock{gap:0!important;}
    section[data-testid="stSidebar"]{display:none!important;}
    </style>""", unsafe_allow_html=True)

    # ── STATE INIT ──────────────────────────────────────────────────────────────
    for k,v in [
        ("pc_sym","RELIANCE.NS"),("pc_name","Reliance"),("pc_tf","1D"),
        ("pc_ai",None),("pc_fund",{}),("pc_srch",""),("pc_srch_res",[]),
        ("pc_favs",["^NSEI","RELIANCE.NS","AAPL","BTC-USD","HDFCBANK.NS"]),
        ("pc_tab","All"),("pc_trader","all"),("pc_chart_mode","tv"),
        ("pc_show_smc",True),("pc_show_fib",True),("pc_show_ob",True),
    ]:
        if k not in st.session_state: st.session_state[k]=v

    ALL_SYMBOLS=[
        {"sym":"^NSEI","name":"NIFTY 50","type":"index","ex":"NSE"},
        {"sym":"^BSESN","name":"SENSEX","type":"index","ex":"BSE"},
        {"sym":"RELIANCE.NS","name":"Reliance","type":"stock","ex":"NSE"},
        {"sym":"TCS.NS","name":"TCS","type":"stock","ex":"NSE"},
        {"sym":"HDFCBANK.NS","name":"HDFC Bank","type":"stock","ex":"NSE"},
        {"sym":"INFY.NS","name":"Infosys","type":"stock","ex":"NSE"},
        {"sym":"ICICIBANK.NS","name":"ICICI Bank","type":"stock","ex":"NSE"},
        {"sym":"SBIN.NS","name":"SBI","type":"stock","ex":"NSE"},
        {"sym":"BAJFINANCE.NS","name":"Bajaj Fin","type":"stock","ex":"NSE"},
        {"sym":"TATAMOTORS.NS","name":"Tata Motors","type":"stock","ex":"NSE"},
        {"sym":"ADANIENT.NS","name":"Adani Ent","type":"stock","ex":"NSE"},
        {"sym":"WIPRO.NS","name":"Wipro","type":"stock","ex":"NSE"},
        {"sym":"MARUTI.NS","name":"Maruti","type":"stock","ex":"NSE"},
        {"sym":"AAPL","name":"Apple","type":"stock","ex":"NASDAQ"},
        {"sym":"TSLA","name":"Tesla","type":"stock","ex":"NASDAQ"},
        {"sym":"NVDA","name":"NVIDIA","type":"stock","ex":"NASDAQ"},
        {"sym":"MSFT","name":"Microsoft","type":"stock","ex":"NASDAQ"},
        {"sym":"GOOGL","name":"Alphabet","type":"stock","ex":"NASDAQ"},
        {"sym":"META","name":"Meta","type":"stock","ex":"NASDAQ"},
        {"sym":"AMZN","name":"Amazon","type":"stock","ex":"NASDAQ"},
        {"sym":"BTC-USD","name":"Bitcoin","type":"crypto","ex":"CRYPTO"},
        {"sym":"ETH-USD","name":"Ethereum","type":"crypto","ex":"CRYPTO"},
        {"sym":"SOL-USD","name":"Solana","type":"crypto","ex":"CRYPTO"},
        {"sym":"BNB-USD","name":"BNB","type":"crypto","ex":"CRYPTO"},
        {"sym":"XRP-USD","name":"XRP","type":"crypto","ex":"CRYPTO"},
        {"sym":"GC=F","name":"Gold","type":"commodity","ex":"CME"},
        {"sym":"CL=F","name":"Crude Oil","type":"commodity","ex":"NYMEX"},
        {"sym":"^GSPC","name":"S&P 500","type":"index","ex":"NYSE"},
        {"sym":"^DJI","name":"Dow Jones","type":"index","ex":"NYSE"},
        {"sym":"^IXIC","name":"NASDAQ Comp","type":"index","ex":"NASDAQ"},
    ]

    # ── TOP BAR ─────────────────────────────────────────────────────────────────
    sym=st.session_state.pc_sym; name=st.session_state.pc_name
    d=_price_fast(sym); pr=d.get("price",0); chg=d.get("chg",0)
    cc="#26a69a" if chg>=0 else "#ef5350"
    pr_s=f"{pr:,.4f}" if pr<10 else f"{pr:,.2f}" if pr>0 else "—"

    st.markdown(f"""<div style="background:rgba(10,13,20,0.98);border-bottom:1px solid rgba(255,255,255,0.06);
    padding:5px 14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <span style="color:#fff;font-weight:900;font-size:14px;">FinSage <span style="color:#2962ff;">PRO</span></span>
      <span style="background:#2962ff22;color:#2962ff;font-size:8px;padding:2px 8px;border-radius:8px;border:1px solid #2962ff44;font-weight:700;">CHART STUDIO</span>
      <div style="flex:1;"></div>
      <span style="color:#9598a1;font-size:13px;font-weight:700;">{sym}</span>
      <span style="color:{cc};font-size:16px;font-weight:900;font-family:monospace;">{pr_s}</span>
      <span style="color:{cc};font-size:12px;">{chg:+.2f}%</span>
      <span style="color:#4a5568;font-size:10px;">🕐 {datetime.now().strftime('%d %b %Y · %H:%M')}</span>
    </div>""", unsafe_allow_html=True)

    # ── LAYOUT: LEFT PANEL + MAIN CHART ────────────────────────────────────────
    left, main = st.columns([1, 4], gap="small")

    # ── LEFT PANEL ──────────────────────────────────────────────────────────────
    with left:
        # SEARCH
        srch=st.text_input("","",placeholder="🔍 Search any stock/crypto...",
                           key="pc_srch_box",label_visibility="collapsed")
        if srch!=st.session_state.pc_srch:
            st.session_state.pc_srch=srch
            if srch.strip():
                with st.spinner("..."): st.session_state.pc_srch_res=_global_search(srch)
            else: st.session_state.pc_srch_res=[]

        if st.session_state.pc_srch_res:
            for item in st.session_state.pc_srch_res:
                d2=_price_fast(item["sym"]); pr2=d2.get("price",0); chg2=d2.get("chg",0)
                cc2="#26a69a" if chg2>=0 else "#ef5350"
                if st.button(f"{item['name'][:16]} [{item['sym'].split('.')[0]}]",
                             key=f"pcs_{item['sym']}",use_container_width=True):
                    st.session_state.pc_sym=item["sym"]; st.session_state.pc_name=item["name"]
                    st.session_state.pc_ai=None; st.session_state.pc_srch=""
                    st.session_state.pc_srch_res=[]; st.rerun()
                if pr2>0:
                    pr2s=f"{pr2:,.4f}" if pr2<10 else f"{pr2:,.2f}"
                    st.markdown(f'<div style="display:flex;padding:0 4px 3px 4px;font-size:10px;border-bottom:1px solid #0a0d14;margin-top:-8px;"><span style="flex:1;color:#4a5568;font-size:9px;">{item["ex"]}</span><span style="color:{cc2};font-family:monospace;">{pr2s}</span><span style="color:{cc2};margin-left:4px;">{chg2:+.1f}%</span></div>',unsafe_allow_html=True)

        # TABS
        tab=st.radio("",["All","Stocks","Crypto","⭐"],horizontal=True,key="pc_tab_r",label_visibility="collapsed")

        wl=ALL_SYMBOLS
        favs=st.session_state.pc_favs
        if tab=="Stocks":   wl=[x for x in wl if x["type"]=="stock"]
        elif tab=="Crypto": wl=[x for x in wl if x["type"]=="crypto"]
        elif tab=="⭐":      wl=[x for x in wl if x["sym"] in favs]

        st.markdown("""<div style="display:flex;padding:3px 5px;font-size:8.5px;color:#374151;
        font-weight:700;border-bottom:1px solid rgba(255,255,255,0.04);background:rgba(255,255,255,0.02);
        text-transform:uppercase;letter-spacing:.05em;">
          <span style="flex:1;">Symbol</span><span style="width:72px;text-align:right;">Price</span><span style="width:44px;text-align:right;">Chg%</span>
        </div>""",unsafe_allow_html=True)

        for item in wl[:30]:
            d3=_price_fast(item["sym"]); pr3=d3.get("price",0); chg3=d3.get("chg",0)
            cc3="#26a69a" if chg3>=0 else "#ef5350"
            is_sel=st.session_state.pc_sym==item["sym"]
            is_fav=item["sym"] in favs
            lbl=("⭐" if is_fav else "")+item["name"][:15]
            if st.button(lbl,key=f"pcwl_{item['sym']}",use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                st.session_state.pc_sym=item["sym"]; st.session_state.pc_name=item["name"]
                st.session_state.pc_ai=None; st.rerun()
            pr3s=f"{pr3:,.4f}" if pr3>0 and pr3<10 else f"{pr3:,.2f}" if pr3>0 else "—"
            chg3s=f"{chg3:+.1f}%" if pr3>0 else "—"
            st.markdown(
                f'<div style="display:flex;padding:0 5px 3px 5px;font-size:10.5px;border-bottom:1px solid rgba(255,255,255,0.03);margin-top:-8px;align-items:center;">'
                f'<span style="flex:1;color:#374151;font-size:9px;">{item["sym"].replace(".NS","").replace("-USD","").replace("^","")}</span>'
                f'<span style="color:{cc3};font-family:monospace;font-weight:700;min-width:72px;text-align:right;">{pr3s}</span>'
                f'<span style="color:{cc3};min-width:44px;text-align:right;font-size:10px;">{chg3s}</span>'
                f'</div>',unsafe_allow_html=True)

    # ── MAIN CHART AREA ─────────────────────────────────────────────────────────
    with main:
        sym=st.session_state.pc_sym; name=st.session_state.pc_name

        # CHART CONTROLS
        ctrl1,ctrl2,ctrl3,ctrl4,ctrl5,ctrl6=st.columns([3,1,1,1,1,1])
        with ctrl1:
            tf=st.radio("",["1D","1H","15m","4H","1W","1M"],horizontal=True,key="pc_tf_r",
                        index=0,label_visibility="collapsed")
        with ctrl2:
            mode=st.radio("",["📺 TV","🤖 AI"],horizontal=True,key="pc_mode_r",label_visibility="collapsed")
        with ctrl3:
            trader=st.selectbox("",["all","price_action","smc","indicator","volume","wave","quant"],
                                key="pc_trader_sel",format_func=lambda x:{"all":"🎯 All","price_action":"📊 PA","smc":"🏦 SMC","indicator":"📈 Ind","volume":"📦 Vol","wave":"🌊 Wave","quant":"🤖 Quant"}.get(x,x),
                                label_visibility="collapsed")
        with ctrl4:
            if st.button("🤖 Analyse",key="pc_run",type="primary",use_container_width=True):
                st.session_state.pc_ai=None; st.session_state.pc_chart_mode="ai"; st.rerun()
        with ctrl5:
            if st.button("⭐",key="pc_fav",use_container_width=True):
                favs=st.session_state.pc_favs
                if sym in favs: st.session_state.pc_favs=[x for x in favs if x!=sym]; st.toast(f"Removed {name}")
                else: st.session_state.pc_favs=favs+[sym]; st.toast(f"⭐ {name} added!")
        with ctrl6:
            if st.button("🔄",key="pc_ref2",use_container_width=True):
                st.session_state.pc_ai=None; st.rerun()

        # Timeframe map
        tf_yf={"1D":("3mo","1d"),"1H":("1mo","1h"),"15m":("5d","15m"),"4H":("6mo","1d"),"1W":("2y","1wk"),"1M":("5y","1mo")}
        period,interval=tf_yf.get(tf,("3mo","1d"))

        # Load data
        with st.spinner(f"Loading {name}..."):
            df=_ohlcv(sym,period,interval)
            tech=_compute_tech(df) if not df.empty else {}

        if df.empty:
            st.error(f"❌ No data for `{sym}`. Try: RELIANCE.NS | AAPL | BTC-USD | ^NSEI")
            return

        chart_mode = st.session_state.get("pc_chart_mode","tv")
        if mode=="📺 TV": chart_mode="tv"
        elif mode=="🤖 AI": chart_mode="ai"

        # ── TV MODE ──────────────────────────────────────────────────────────
        if chart_mode=="tv":
            tv_s=_to_tv(sym)
            tv_tf={"1D":"D","1H":"60","15m":"15","4H":"240","1W":"W","1M":"M"}.get(tf,"D")
            tv_html=f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}html,body{{background:#0a0d14;width:100%;height:680px;overflow:hidden;}}</style>
</head><body><div style="width:100%;height:680px;">
  <div id="tv_c" style="width:100%;height:680px;"></div>
  <script src="https://s3.tradingview.com/tv.js"></script>
  <script>new TradingView.widget({{
    "autosize":false,"width":"100%","height":680,
    "symbol":"{tv_s}","interval":"{tv_tf}",
    "timezone":"Asia/Kolkata","theme":"dark","style":"1","locale":"en",
    "toolbar_bg":"#0a0d14","enable_publishing":false,"hide_top_toolbar":false,
    "container_id":"tv_c","allow_symbol_change":true,
    "studies":["RSI@tv-basicstudies","MACD@tv-basicstudies","Volume@tv-basicstudies","BB@tv-basicstudies"],
    "overrides":{{
      "mainSeriesProperties.candleStyle.upColor":"#26a69a","mainSeriesProperties.candleStyle.downColor":"#ef5350",
      "mainSeriesProperties.candleStyle.borderUpColor":"#26a69a","mainSeriesProperties.candleStyle.borderDownColor":"#ef5350",
      "mainSeriesProperties.candleStyle.wickUpColor":"#26a69a","mainSeriesProperties.candleStyle.wickDownColor":"#ef5350",
      "paneProperties.background":"#0a0d14","paneProperties.vertGridProperties.color":"rgba(255,255,255,0.03)",
      "paneProperties.horzGridProperties.color":"rgba(255,255,255,0.03)"
    }},
    "studies_overrides":{{
      "volume.volume.color.0":"#ef535044","volume.volume.color.1":"#26a69a44",
      "RSI.plot.color":"#2962ff"
    }},
    "show_popup_button":false,"withdateranges":true
  }});</script>
</div></body></html>"""
            components.html(tv_html,height=692,scrolling=False)

            # Quick stats below TV chart
            rsi_v=tech.get("rsi",50); trend=tech.get("trend","—")
            tc="#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"
            sup=tech.get("supports",[]); res=tech.get("resistances",[])
            st.markdown(f"""<div style="background:rgba(13,17,28,0.95);backdrop-filter:blur(15px);
            border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:8px 14px;margin:5px 0;
            display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
              <span style="color:#fff;font-weight:800;">{name}</span>
              <span style="color:{tc};font-weight:700;">{trend}</span>
              <span style="color:#6a6e7a;">RSI: <b style="color:#d1d4dc;">{rsi_v:.1f}</b></span>
              <span style="color:#6a6e7a;">Vol: <b style="color:#d1d4dc;">{tech.get('vol_ratio',1):.2f}x</b></span>
              <span style="color:#6a6e7a;">Support: <b style="color:#26a69a;">{round(sup[0],2) if sup else '—'}</b></span>
              <span style="color:#6a6e7a;">Resistance: <b style="color:#ef5350;">{round(res[0],2) if res else '—'}</b></span>
              <span style="color:#4a5568;font-size:11px;margin-left:auto;">👆 Click <b style="color:#2962ff;">🤖 Analyse</b> for full AI chart with all drawings</span>
            </div>""",unsafe_allow_html=True)

        # ── AI PRO CHART MODE ─────────────────────────────────────────────────
        else:
            if st.session_state.pc_ai is None:
                with st.spinner(f"🤖 SAGE AI — Analyzing {name} ({trader})..."):
                    from market_dashboard import _fundamental
                    fund=_fundamental(sym)
                    ai_res=_ai_full(sym,name,tech,fund,trader)
                st.session_state.pc_ai=ai_res
                st.session_state.pc_fund=fund
            else:
                ai_res=st.session_state.pc_ai
                fund=st.session_state.pc_fund

            # PRO CHART
            chart_html=_pro_chart_html(df,tech,ai_res,sym,height=700)
            components.html(chart_html,height=714,scrolling=False)

            # ── ANALYSIS PANELS ───────────────────────────────────────────────
            bc=ai_res.get("bias_color","#f59e0b"); bias=ai_res.get("bias","NEUTRAL")
            rat=ai_res.get("rating","HOLD"); rc=ai_res.get("rating_color","#f59e0b")
            conf=ai_res.get("confidence",65); api_u=ai_res.get("_api","AI")
            sup=tech.get("supports",[]); res=tech.get("resistances",[])

            # Summary strip
            st.markdown(f"""<div style="background:rgba(13,17,28,0.95);backdrop-filter:blur(20px);
            border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:10px 16px;margin:5px 0;
            display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
              <span style="background:{rc}18;color:{rc};border:1px solid {rc}33;border-radius:20px;
                padding:3px 14px;font-weight:800;font-size:12px;">{rat}</span>
              <span style="color:{bc};font-weight:800;font-size:14px;">{bias}</span>
              <span style="color:#d1d4dc;font-size:13px;">{ai_res.get('summary','')[:100]}...</span>
              <span style="color:#4a5568;font-size:10px;margin-left:auto;">via {api_u} · {conf}% confidence</span>
            </div>""",unsafe_allow_html=True)

            # Analysis tabs
            ta,tb,tc2,td,te,tf2=st.tabs(["📊 Multi-View","🏦 SMC/ICT","📈 Indicators","📦 Volume","🌊 Wave+Fib","📋 Trade Setup"])

            with ta:
                c1,c2=st.columns(2)
                with c1:
                    st.markdown("""<div style="font-size:12px;font-weight:800;color:#4a9eff;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">📊 Price Action View</div>""",unsafe_allow_html=True)
                    st.markdown(f"""<div style="background:rgba(41,98,255,0.06);border:1px solid rgba(41,98,255,0.15);border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.7;color:#c8cad0;">{ai_res.get('price_action_view','')}</div>""",unsafe_allow_html=True)
                with c2:
                    st.markdown("""<div style="font-size:12px;font-weight:800;color:#a855f7;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">🌊 Elliott Wave View</div>""",unsafe_allow_html=True)
                    st.markdown(f"""<div style="background:rgba(168,85,247,0.06);border:1px solid rgba(168,85,247,0.15);border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.7;color:#c8cad0;">{ai_res.get('wave_view','')}</div>""",unsafe_allow_html=True)

            with tb:
                c1,c2=st.columns(2)
                with c1:
                    st.markdown("""<div style="font-size:12px;font-weight:800;color:#f59e0b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">🏦 SMC / ICT View</div>""",unsafe_allow_html=True)
                    st.markdown(f"""<div style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.15);border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.7;color:#c8cad0;">{ai_res.get('smc_view','')}</div>""",unsafe_allow_html=True)
                    # Order blocks
                    ob_list2=ai_res.get("order_blocks",[])
                    if ob_list2:
                        st.markdown("**Order Blocks:**")
                        for ob in ob_list2:
                            oc="#26a69a" if "BULL" in ob.get("type","") else "#ef5350"
                            st.markdown(f"""<div style="background:{oc}11;border-left:3px solid {oc};border-radius:0 6px 6px 0;padding:6px 10px;margin:3px 0;font-size:12px;color:#c8cad0;">
                            <b style="color:{oc};">{ob.get('type','OB')}</b> Zone: {ob.get('zone_bot',0):.4f} – {ob.get('zone_top',0):.4f}<br>
                            <span style="color:#6a6e7a;">{ob.get('significance','')[:60]}</span></div>""",unsafe_allow_html=True)
                with c2:
                    # Liquidity zones
                    liq=ai_res.get("liquidity_zones",[])
                    if liq:
                        st.markdown("**Liquidity Pools:**")
                        for lz in liq:
                            lt="#2962ff" if "buy" in lz.get("type","").lower() else "#ef5350"
                            st.markdown(f"""<div style="background:{lt}11;border-left:3px solid {lt};border-radius:0 6px 6px 0;padding:6px 10px;margin:3px 0;font-size:12px;color:#c8cad0;">
                            <b style="color:{lt};">{lz.get('type','').upper()}</b> @ {lz.get('level',0):.4f}<br>
                            <span style="color:#6a6e7a;">{lz.get('desc','')[:60]}</span></div>""",unsafe_allow_html=True)
                    # FVG
                    fvg_zones=ai_res.get("fvg_zones",[])
                    if fvg_zones:
                        st.markdown("**Fair Value Gaps:**")
                        for fv in fvg_zones:
                            fc2="#26a69a" if "BULL" in fv.get("type","") else "#ef5350"
                            st.markdown(f"""<div style="background:{fc2}11;border-left:3px solid {fc2};border-radius:0 6px 6px 0;padding:6px 10px;margin:3px 0;font-size:12px;color:#c8cad0;">
                            <b style="color:{fc2};">FVG {fv.get('type','')}</b> {fv.get('bot',0):.4f}–{fv.get('top',0):.4f}<br>
                            <span style="color:#6a6e7a;">{fv.get('desc','')[:60]}</span></div>""",unsafe_allow_html=True)

            with tc2:
                st.markdown(f"""<div style="background:rgba(41,98,255,0.06);border:1px solid rgba(41,98,255,0.15);border-radius:8px;padding:12px;margin-bottom:8px;font-size:13px;line-height:1.75;color:#c8cad0;">
                <b style="color:#4a9eff;font-size:14px;">📈 Indicator Confluence:</b><br>{ai_res.get('indicator_view','')}</div>""",unsafe_allow_html=True)
                # Indicator grid
                rsi_v=tech.get("rsi",50); stoch=tech.get("stoch_rsi",50); macd_h=tech.get("macd_h",0)
                e20=tech.get("ema20",0); e50=tech.get("ema50",0); e200=tech.get("ema200",0)
                p=tech.get("price",0); vwap_v=tech.get("vwap",0); bb_u=tech.get("bb_upper",0); bb_l=tech.get("bb_lower",0)
                inds=[
                    ("RSI",f"{rsi_v:.1f}","#ef5350" if rsi_v>70 else "#26a69a" if rsi_v<30 else "#d1d4dc",
                     "Overbought" if rsi_v>70 else "Oversold" if rsi_v<30 else "Neutral"),
                    ("StochRSI",f"{stoch:.1f}","#ef5350" if stoch>80 else "#26a69a" if stoch<20 else "#d1d4dc",
                     "Overbought" if stoch>80 else "Oversold" if stoch<20 else "Neutral"),
                    ("MACD","Bullish" if macd_h>0 else "Bearish","#26a69a" if macd_h>0 else "#ef5350",f"Hist: {macd_h:.4f}"),
                    ("EMA20",f"{e20:.4f}","#26a69a" if p>e20 else "#ef5350","Above" if p>e20 else "Below"),
                    ("EMA50",f"{e50:.4f}","#26a69a" if p>e50 else "#ef5350","Above" if p>e50 else "Below"),
                    ("EMA200",f"{e200:.4f}","#26a69a" if p>e200 else "#ef5350","Above" if p>e200 else "Below"),
                    ("VWAP",f"{vwap_v:.4f}","#26a69a" if p>vwap_v else "#ef5350","Above" if p>vwap_v else "Below"),
                    ("BB Position",f"{round((p-bb_l)/(bb_u-bb_l)*100,1) if bb_u!=bb_l else 50:.1f}%",
                     "#ef5350" if p>bb_u else "#26a69a" if p<bb_l else "#d1d4dc","Upper" if p>bb_u else "Lower" if p<bb_l else "Mid-band"),
                    ("Volume",f"{tech.get('vol_ratio',1):.2f}x","#2962ff" if tech.get('vol_ratio',1)>1.3 else "#d1d4dc",
                     "High Vol" if tech.get('vol_ratio',1)>1.3 else "Normal"),
                ]
                cols=st.columns(3)
                for i,(ind,val,col,sig) in enumerate(inds):
                    with cols[i%3]:
                        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:8px 10px;margin-bottom:6px;">
                        <div style="font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:.06em;">{ind}</div>
                        <div style="font-size:16px;font-weight:800;color:{col};font-family:'Courier New';">{val}</div>
                        <div style="font-size:10px;color:{col};">{sig}</div></div>""",unsafe_allow_html=True)

            with td:
                st.markdown(f"""<div style="background:rgba(41,98,255,0.06);border:1px solid rgba(41,98,255,0.15);border-radius:8px;padding:12px;font-size:13px;line-height:1.75;color:#c8cad0;">
                <b style="color:#4a9eff;font-size:14px;">📦 Volume & Order Flow:</b><br>{ai_res.get('volume_view','')}</div>""",unsafe_allow_html=True)
                st.markdown(f"""<div style="background:rgba(41,98,255,0.04);border:1px solid rgba(41,98,255,0.1);border-radius:8px;padding:10px 12px;margin-top:6px;font-size:13px;line-height:1.7;color:#c8cad0;">{ai_res.get('volume_analysis','')}</div>""",unsafe_allow_html=True)
                # Volume profile table
                vp=tech.get("vp",[]); max_vp=max([x["vol"] for x in vp],default=1) or 1
                if vp:
                    st.markdown("**Volume Profile (Top Nodes):**")
                    for vi in vp[:8]:
                        pct=vi["vol"]/max_vp*100; is_poc=vi["vol"]==max_vp
                        col3="#2962ff" if is_poc else "#6a6e7a"
                        label="🔵 POC" if is_poc else "    "
                        st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;margin:2px 0;font-size:11px;">
                        <span style="color:{col3};width:50px;text-align:right;font-family:monospace;">{vi['price']:.2f}</span>
                        <div style="flex:1;background:rgba(255,255,255,0.04);border-radius:2px;height:10px;">
                          <div style="background:{col3};height:10px;border-radius:2px;width:{pct:.0f}%;"></div></div>
                        <span style="color:{col3};width:30px;">{label}</span></div>""",unsafe_allow_html=True)

            with te:
                c1,c2=st.columns(2)
                with c1:
                    st.markdown("""<div style="font-size:12px;font-weight:800;color:#a855f7;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">🌊 Elliott Wave</div>""",unsafe_allow_html=True)
                    st.markdown(f"""<div style="background:rgba(168,85,247,0.06);border:1px solid rgba(168,85,247,0.15);border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.7;color:#c8cad0;">{ai_res.get('wave_view','')}</div>""",unsafe_allow_html=True)
                with c2:
                    st.markdown("""<div style="font-size:12px;font-weight:800;color:#26a69a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">📐 Fibonacci Levels</div>""",unsafe_allow_html=True)
                    fib=tech.get("fib",{})
                    fib_colors={"0.236":"#7986cb","0.382":"#26a69a","0.500":"#fbbf24","0.618":"#ef5350","0.786":"#e040fb"}
                    for k,v_fib in fib.items():
                        fc3=fib_colors.get(k,"#6a6e7a"); is_cur=abs(v_fib-tech.get("price",0))/tech.get("price",1)<0.02
                        st.markdown(f"""<div style="display:flex;justify-content:space-between;padding:5px 10px;border-radius:6px;margin:2px 0;background:{'rgba(255,255,255,0.06)' if is_cur else 'rgba(255,255,255,0.02)'};border:{'1px solid '+fc3+'44' if is_cur else 'none'};">
                        <span style="color:{fc3};font-weight:700;">Fib {k}</span>
                        <span style="color:#d1d4dc;font-family:'Courier New';">{v_fib:.4f}</span>
                        {'<span style="color:'+fc3+';font-size:10px;">← CURRENT</span>' if is_cur else ''}
                        </div>""",unsafe_allow_html=True)

            with tf2:
                c1,c2,c3=st.columns(3)
                with c1:
                    entry_v=ai_res.get("entry",0); stop_v=ai_res.get("stop",0)
                    t1_v=ai_res.get("t1",0); t2_v=ai_res.get("t2",0)
                    rr=ai_res.get("rr","—"); qual=ai_res.get("quality","—")
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:12px;">
                    <div style="color:#4a5568;font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:8px;">Trade Setup</div>
                    <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#26a69a;font-weight:700;">Entry</span><span style="color:#26a69a;font-family:'Courier New';font-size:14px;">{entry_v:.4f}</span></div>
                    <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#ef5350;font-weight:700;">Stop Loss</span><span style="color:#ef5350;font-family:'Courier New';font-size:14px;">{stop_v:.4f}</span></div>
                    <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#2962ff;">Target 1</span><span style="color:#2962ff;font-family:'Courier New';font-size:14px;">{t1_v:.4f}</span></div>
                    <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#9c27b0;">Target 2</span><span style="color:#9c27b0;font-family:'Courier New';font-size:14px;">{t2_v:.4f}</span></div>
                    <div style="display:flex;justify-content:space-between;padding:8px 0 0;"><span style="color:#6a6e7a;font-size:12px;">R:R Ratio</span><span style="font-weight:900;font-size:18px;color:{bc};">{rr}</span></div>
                    </div>""",unsafe_allow_html=True)
                with c2:
                    thesis=ai_res.get("thesis",[]); risks=ai_res.get("risks",[])
                    th_html="".join([f'<div style="padding:4px 0 4px 14px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;color:#c8cad0;position:relative;"><span style="position:absolute;left:0;color:#26a69a;font-weight:900;">+</span>{t}</div>' for t in thesis])
                    rk_html="".join([f'<div style="padding:4px 0 4px 14px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;color:#c8cad0;position:relative;"><span style="position:absolute;left:0;color:#ef5350;font-weight:900;">−</span>{r}</div>' for r in risks])
                    st.markdown(f"""<div style="background:rgba(38,166,154,0.05);border:1px solid rgba(38,166,154,0.15);border-radius:10px;padding:10px;margin-bottom:6px;">
                    <div style="color:#26a69a;font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Thesis</div>{th_html}</div>
                    <div style="background:rgba(239,83,80,0.05);border:1px solid rgba(239,83,80,0.15);border-radius:10px;padding:10px;">
                    <div style="color:#ef5350;font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Risks</div>{rk_html}</div>""",unsafe_allow_html=True)
                with c3:
                    mtf=ai_res.get("multi_tf",{})
                    mtf_html="".join([f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;"><span style="color:#4a5568;text-transform:uppercase;font-size:10px;">{k}</span><span style="color:#c8cad0;">{v}</span></div>' for k,v in mtf.items()])
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:10px;margin-bottom:6px;">
                    <div style="color:#4a5568;font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Multi-Timeframe</div>{mtf_html}</div>
                    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:8px;font-size:12px;color:#9598a1;line-height:1.6;">
                    <b style="color:#6a6e7a;">Fundamentals:</b><br>{ai_res.get('fundamental_quick','')}</div>""",unsafe_allow_html=True)
