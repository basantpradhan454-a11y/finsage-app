"""
FinSage AI — Footprint Chart + AI Analysis
TradingView-style candlestick chart with AI-drawn levels, volume profile,
pattern detection, multi-timeframe confluence, and voice analysis.
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

# ── Config ────────────────────────────────────────────────────────────────────
def _groq_key():
    try:
        return st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY","")
    except Exception:
        return os.environ.get("GROQ_API_KEY","")

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

CHART_H = 640   # fixed pixel chart height
IFRAME_H = CHART_H + 50  # total iframe height passed to components.html

# ── Data fetch ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _fetch_data(sym: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.Ticker(sym).history(period=period, interval=interval)
        if df.empty: return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()

# ── Indicators ────────────────────────────────────────────────────────────────
def _ema(arr: np.ndarray, n: int) -> np.ndarray:
    s = pd.Series(arr); return s.ewm(span=n, adjust=False).mean().values

def _compute_indicators(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 20: return {}
    c = df["Close"].values.astype(float)
    h = df["High"].values.astype(float)
    l = df["Low"].values.astype(float)
    v = df["Volume"].values.astype(float)
    o = df["Open"].values.astype(float)

    # RSI
    delta = np.diff(c, prepend=c[0])
    up = np.where(delta>0,delta,0); dn = np.where(delta<0,-delta,0)
    avg_up = _ema(up,14); avg_dn = _ema(dn,14)
    rs = np.where(avg_dn==0,100,avg_up/np.where(avg_dn==0,1e-9,avg_dn))
    rsi = float((100 - 100/(1+rs))[-1])

    ema9  = float(_ema(c,9)[-1])
    ema20 = float(_ema(c,20)[-1])
    ema50 = float(_ema(c,50)[-1]) if len(c)>=50 else float(c.mean())
    ema200= float(_ema(c,200)[-1]) if len(c)>=200 else float(c.mean())

    ema12_arr = _ema(c,12); ema26_arr = _ema(c,26)
    macd_arr  = ema12_arr - ema26_arr
    sig_arr   = _ema(macd_arr,9)
    macd_hist = float(macd_arr[-1] - sig_arr[-1])
    macd_val  = float(macd_arr[-1])

    # ATR
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    atr = float(tr[-14:].mean()) if len(tr)>=14 else float(tr.mean()) if len(tr)>0 else 0

    # VWAP
    tp = (h+l+c)/3; n20=min(20,len(tp))
    vwap = float(np.sum(tp[-n20:]*v[-n20:])/np.sum(v[-n20:])) if np.sum(v[-n20:])>0 else float(c[-1])

    avg_vol = float(v[-20:].mean()); cur_vol = float(v[-1])
    vol_ratio = cur_vol/avg_vol if avg_vol>0 else 1.0

    # Bollinger Bands
    sma20 = float(np.mean(c[-20:])); std20 = float(np.std(c[-20:]))
    bb_upper = sma20+2*std20; bb_lower = sma20-2*std20

    # Stoch RSI
    rsi_series=[]
    for i in range(14,len(c)):
        d2=np.diff(c[max(0,i-14):i+1],prepend=c[max(0,i-14)])
        u2=np.where(d2>0,d2,0); d3=np.where(d2<0,-d2,0)
        au=u2.mean(); ad=d3.mean()
        rs2=au/ad if ad>0 else 100
        rsi_series.append(100-100/(1+rs2))
    if len(rsi_series)>=14:
        rm=min(rsi_series[-14:]); rx=max(rsi_series[-14:])
        stoch_rsi=float((rsi_series[-1]-rm)/(rx-rm)*100) if rx!=rm else 50.0
    else: stoch_rsi=50.0

    # Support / Resistance via pivot highs/lows
    window=5
    pivots_s=[]; pivots_r=[]
    for i in range(window,len(c)-window):
        if all(l[i]<=l[i-j] for j in range(1,window+1)) and all(l[i]<=l[i+j] for j in range(1,window+1)):
            pivots_s.append(float(l[i]))
        if all(h[i]>=h[i-j] for j in range(1,window+1)) and all(h[i]>=h[i+j] for j in range(1,window+1)):
            pivots_r.append(float(h[i]))

    supports    = sorted([x for x in pivots_s if x<c[-1]], reverse=True)[:4]
    resistances = sorted([x for x in pivots_r if x>c[-1]])[:4]

    # Trend
    if c[-1]>ema20>ema50: trend="BULLISH"
    elif c[-1]<ema20<ema50: trend="BEARISH"
    else: trend="SIDEWAYS"

    # Fibonacci levels (based on last swing)
    period_high = float(h[-60:].max()) if len(h)>=60 else float(h.max())
    period_low  = float(l[-60:].min()) if len(l)>=60 else float(l.min())
    diff = period_high - period_low
    fib_levels = {
        "0.236": round(period_high - diff*0.236, 4),
        "0.382": round(period_high - diff*0.382, 4),
        "0.500": round(period_high - diff*0.500, 4),
        "0.618": round(period_high - diff*0.618, 4),
        "0.786": round(period_high - diff*0.786, 4),
    }

    return {
        "price":c[-1], "open":o[-1], "high":h[-1], "low":l[-1], "volume":cur_vol,
        "rsi":rsi, "ema9":ema9, "ema20":ema20, "ema50":ema50, "ema200":ema200,
        "macd":macd_val, "macd_hist":macd_hist, "atr":atr, "vwap":vwap,
        "vol_ratio":vol_ratio, "avg_vol":avg_vol, "supports":supports,
        "resistances":resistances, "trend":trend, "bb_upper":bb_upper,
        "bb_lower":bb_lower, "sma20":sma20, "stoch_rsi":stoch_rsi,
        "fib":fib_levels, "period_high":period_high, "period_low":period_low,
    }

# ── Candlestick patterns ───────────────────────────────────────────────────────
def _detect_patterns(df: pd.DataFrame) -> list:
    if df.empty or len(df)<5: return []
    rows = df.tail(15)
    closes=rows["Close"].values.astype(float)
    opens =rows["Open"].values.astype(float)
    highs =rows["High"].values.astype(float)
    lows  =rows["Low"].values.astype(float)
    patterns=[]
    for i in range(2,len(closes)):
        o1,h1,l1,c1=opens[i-1],highs[i-1],lows[i-1],closes[i-1]
        o2,h2,l2,c2=opens[i],  highs[i],  lows[i],  closes[i]
        body1=abs(c1-o1); body2=abs(c2-o2)
        rng2=h2-l2 if h2-l2>0 else 1e-9
        lwick=min(o2,c2)-l2; uwick=h2-max(o2,c2)
        # Doji
        if body2<rng2*0.1:
            patterns.append({"name":"Doji","type":"NEUTRAL","bar":i,"desc":"Indecision — open≈close, wait for confirmation"})
        # Hammer
        elif lwick>body2*2 and uwick<body2*0.5 and c2>l2:
            ptype="BULLISH" if c2>o2 else "NEUTRAL"
            patterns.append({"name":"Hammer","type":ptype,"bar":i,"desc":"Bullish reversal signal — long lower wick shows buyer rejection"})
        # Shooting Star
        elif uwick>body2*2 and lwick<body2*0.5 and c2<h2:
            ptype="BEARISH" if c2<o2 else "NEUTRAL"
            patterns.append({"name":"Shooting Star","type":ptype,"bar":i,"desc":"Bearish reversal — rejected at highs, sellers took control"})
        # Bullish Engulfing
        if c1<o1 and c2>o2 and o2<=c1 and c2>=o1 and body2>body1:
            patterns.append({"name":"Bullish Engulfing","type":"BULLISH","bar":i,"desc":"Strong reversal — bull candle fully engulfs prior bear candle"})
        # Bearish Engulfing
        if c1>o1 and c2<o2 and o2>=c1 and c2<=o1 and body2>body1:
            patterns.append({"name":"Bearish Engulfing","type":"BEARISH","bar":i,"desc":"Strong reversal — bear candle fully engulfs prior bull candle"})
        # Marubozu
        if body2/rng2>0.88 and c2>o2 and uwick<body2*0.05:
            patterns.append({"name":"Bullish Marubozu","type":"BULLISH","bar":i,"desc":"Pure bullish momentum — no wicks, buyers in full control"})
        if body2/rng2>0.88 and c2<o2 and lwick<body2*0.05:
            patterns.append({"name":"Bearish Marubozu","type":"BEARISH","bar":i,"desc":"Pure bearish momentum — no wicks, sellers dominating"})
        # Dragonfly / Gravestone Doji
        if body2<rng2*0.05 and lwick>rng2*0.6:
            patterns.append({"name":"Dragonfly Doji","type":"BULLISH","bar":i,"desc":"Buyers pushed price back up from lows — bullish signal"})
        if body2<rng2*0.05 and uwick>rng2*0.6:
            patterns.append({"name":"Gravestone Doji","type":"BEARISH","bar":i,"desc":"Sellers pushed price back down from highs — bearish signal"})
        # Spinning Top
        if 0.08<body2/rng2<0.28 and lwick>body2*0.6 and uwick>body2*0.6:
            patterns.append({"name":"Spinning Top","type":"NEUTRAL","bar":i,"desc":"Indecision candle — equal wicks, small body"})
        # 3-candle patterns
        if i>=2:
            o0,c0=opens[i-2],closes[i-2]; body0=abs(c0-o0)
            if c0<o0 and body1<body0*0.35 and c2>o2 and c2>=(o0+c0)/2:
                patterns.append({"name":"Morning Star","type":"BULLISH","bar":i,"desc":"3-candle bullish reversal — weakness→indecision→strong bull"})
            if c0>o0 and body1<body0*0.35 and c2<o2 and c2<=(o0+c0)/2:
                patterns.append({"name":"Evening Star","type":"BEARISH","bar":i,"desc":"3-candle bearish reversal — strength→indecision→strong bear"})
            # Three White Soldiers
            if all(closes[j]>opens[j] for j in [i-2,i-1,i]) and \
               closes[i]>closes[i-1]>closes[i-2] and opens[i]>opens[i-1]>opens[i-2]:
                patterns.append({"name":"Three White Soldiers","type":"BULLISH","bar":i,"desc":"3 consecutive strong bull candles — powerful uptrend signal"})
            # Three Black Crows
            if all(closes[j]<opens[j] for j in [i-2,i-1,i]) and \
               closes[i]<closes[i-1]<closes[i-2] and opens[i]<opens[i-1]<opens[i-2]:
                patterns.append({"name":"Three Black Crows","type":"BEARISH","bar":i,"desc":"3 consecutive strong bear candles — powerful downtrend signal"})
    seen=set(); unique=[]
    for p in patterns:
        if p["name"] not in seen: seen.add(p["name"]); unique.append(p)
    return unique[:8]

# ── Volume profile ────────────────────────────────────────────────────────────
def _build_volume_profile(df: pd.DataFrame, bins: int=24) -> list:
    if df.empty: return []
    lo=float(df["Low"].min()); hi=float(df["High"].max())
    if hi<=lo: return []
    bs=(hi-lo)/bins; profile=[]
    for i in range(bins):
        lb=lo+i*bs; hb=lb+bs; mid=(lb+hb)/2
        mask=(df["Low"]<=hb)&(df["High"]>=lb)
        vol=float(df.loc[mask,"Volume"].sum())
        profile.append({"price":round(mid,4),"vol":vol,"low":round(lb,4),"high":round(hb,4)})
    return sorted(profile,key=lambda x:x["vol"],reverse=True)

# ── AI Analysis ───────────────────────────────────────────────────────────────
def _ai_footprint_analysis(sym:str, ind:dict, patterns:list, vp:list) -> dict:
    key=_groq_key()
    if not key: return _rule_based_analysis(sym,ind,patterns)
    top_vp=[f"{v['price']}(vol:{v['vol']/1e6:.1f}M)" for v in vp[:3]]
    pat_names=[p["name"] for p in patterns[:5]]
    p=ind.get("price",0); rsi=ind.get("rsi",50)
    prompt=f"""You are SAGE AI, elite trading analyst. Analyze and return ONLY valid JSON.

Symbol: {sym}
Price: {p:.4f} | RSI: {rsi:.1f} | Trend: {ind.get('trend','?')}
EMA20: {ind.get('ema20',0):.4f} | EMA50: {ind.get('ema50',0):.4f} | EMA200: {ind.get('ema200',0):.4f}
MACD Hist: {ind.get('macd_hist',0):.4f} | ATR: {ind.get('atr',0):.4f} | VWAP: {ind.get('vwap',0):.4f}
Volume Ratio: {ind.get('vol_ratio',1):.2f}x | StochRSI: {ind.get('stoch_rsi',50):.1f}
BB Upper: {ind.get('bb_upper',0):.4f} | BB Lower: {ind.get('bb_lower',0):.4f}
Supports: {ind.get('supports',[])} | Resistances: {ind.get('resistances',[])}
Fib Levels: {ind.get('fib',{})} | Patterns: {pat_names}
High-Volume Zones: {top_vp}

Return JSON only (no markdown):
{{"overall_bias":"BULLISH","bias_color":"#26a69a","confidence":78,
"summary":"2-sentence analysis in simple English",
"entry_zone":{{"price":0,"reason":"exact reason with data"}},"stop_loss":{{"price":0,"reason":"invalidation level"}},
"targets":[{{"price":0,"label":"T1","reason":"resistance reason"}},{{"price":0,"label":"T2","reason":""}}],
"risk_reward":"1:2.5","trade_quality":"GOOD",
"key_observations":["RSI/momentum","Volume/order flow","Support/resistance","Pattern signal"],
"indicator_signals":{{"RSI":"","MACD":"","EMA":"","Volume":"","VWAP":"","BB":"","StochRSI":""}},
"voice_explanation":"20-30 second spoken script explaining the full setup in conversational Hindi+English",
"footprint_insight":"What order flow and volume profile reveal",
"multi_timeframe":{{"daily":"","hourly":"","intraday":""}},
"risk_note":"Key risk"}}"""
    try:
        r=requests.post(GROQ_URL,
            headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
            json={"model":GROQ_MODEL,"messages":[{"role":"user","content":prompt}],
                  "temperature":0.2,"max_tokens":1400},timeout=25)
        raw=r.json()["choices"][0]["message"]["content"].strip()
        if "```json" in raw: raw=raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:   raw=raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)
    except Exception:
        return _rule_based_analysis(sym,ind,patterns)

def _rule_based_analysis(sym:str, ind:dict, patterns:list) -> dict:
    p=ind.get("price",0); rsi=ind.get("rsi",50); trend=ind.get("trend","SIDEWAYS")
    vr=ind.get("vol_ratio",1.0); sup=ind.get("supports",[]); res=ind.get("resistances",[])
    if trend=="BULLISH" and rsi<70: bias="BULLISH"; bc="#26a69a"
    elif trend=="BEARISH" and rsi>30: bias="BEARISH"; bc="#ef5350"
    else: bias="NEUTRAL"; bc="#f59e0b"
    entry=sup[0] if sup else p*0.99; sl=sup[1] if len(sup)>1 else p*0.97
    t1=res[0] if res else p*1.03;   t2=res[1] if len(res)>1 else p*1.06
    rr_val=(t1-entry)/(entry-sl) if entry-sl>0 else 1.0
    tq="EXCELLENT" if rr_val>=2.5 else "GOOD" if rr_val>=1.5 else "AVERAGE" if rr_val>=1.0 else "POOR"
    pat_str=", ".join([x["name"] for x in patterns[:3]]) or "None"
    return {
        "overall_bias":bias,"bias_color":bc,"confidence":65,
        "summary":f"{sym} — {bias} bias. RSI {rsi:.0f}, trend {trend}, volume {vr:.1f}x average.",
        "entry_zone":{"price":round(entry,4),"reason":"Near key support level"},
        "stop_loss":{"price":round(sl,4),"reason":"Below major support — invalidation point"},
        "targets":[{"price":round(t1,4),"label":"T1","reason":"Next resistance"},
                   {"price":round(t2,4),"label":"T2","reason":"Extended resistance"}],
        "risk_reward":f"1:{rr_val:.1f}","trade_quality":tq,
        "key_observations":[
            f"RSI at {rsi:.0f} — {'oversold bounce likely' if rsi<40 else 'overbought — caution' if rsi>70 else 'neutral zone'}",
            f"Volume {vr:.1f}x average — {'high conviction move' if vr>1.5 else 'below avg — weak signal'}",
            f"Trend: {trend} | EMA structure {'aligned bullish' if trend=='BULLISH' else 'aligned bearish' if trend=='BEARISH' else 'mixed'}",
            f"Patterns: {pat_str}"],
        "indicator_signals":{
            "RSI":f"{rsi:.0f} — {'Oversold' if rsi<40 else 'Overbought' if rsi>70 else 'Neutral'}",
            "MACD":"Bullish histogram" if ind.get("macd_hist",0)>0 else "Bearish histogram",
            "EMA":f"Price {'above' if p>ind.get('ema20',p) else 'below'} EMA20/{ind.get('ema20',0):.2f}",
            "Volume":f"{vr:.1f}x avg — {'Strong' if vr>1.2 else 'Weak'}",
            "VWAP":f"{'Above' if p>ind.get('vwap',p) else 'Below'} VWAP {ind.get('vwap',0):.2f}",
            "BB":f"{'Near upper band' if p>ind.get('bb_upper',p)*0.98 else 'Near lower band' if p<ind.get('bb_lower',p)*1.02 else 'Middle of band'}",
            "StochRSI":f"{ind.get('stoch_rsi',50):.0f} — {'Oversold' if ind.get('stoch_rsi',50)<20 else 'Overbought' if ind.get('stoch_rsi',50)>80 else 'Neutral'}"},
        "voice_explanation":f"Main dekh raha hoon {sym} ka chart. RSI {rsi:.0f} hai, trend {trend} dikh raha hai. Volume normal se {vr:.1f} guna zyada hai — yeh ek {'strong' if vr>1.5 else 'moderate'} signal hai. Entry {entry:.2f} ke paas suitable lagti hai, stop loss {sl:.2f} ke neeche rakhna chahiye. Target T1 {t1:.2f} aur T2 {t2:.2f} hai. Risk reward ratio {rr_val:.1f} ka hai.",
        "footprint_insight":f"Highest volume near {sup[0] if sup else p:.2f} — strong demand zone",
        "multi_timeframe":{"daily":f"Daily: {trend}","hourly":"Check 1H chart","intraday":"Check 15m"},
        "risk_note":"Confirm with broader market before entering any trade"
    }

# ══════════════════════════════════════════════════════════════════════════════
# CHART HTML BUILDER — Fixed pixel heights, no vh
# ══════════════════════════════════════════════════════════════════════════════
def _build_footprint_html(df:pd.DataFrame, ind:dict, ai_res:dict,
                           patterns:list, vp:list, sym:str,
                           chart_height:int=CHART_H) -> str:
    candle_data=[]; vol_data=[]; vp_data=[]

    if not df.empty:
        for idx,row in df.tail(150).iterrows():
            ts=int(pd.Timestamp(idx).timestamp())
            o=round(float(row["Open"]),4); h=round(float(row["High"]),4)
            l=round(float(row["Low"]),4);  c=round(float(row["Close"]),4)
            candle_data.append({"time":ts,"open":o,"high":h,"low":l,"close":c})
            is_up=c>=o
            vol_data.append({"time":ts,"value":int(row["Volume"]),
                "color":"rgba(38,166,154,0.45)" if is_up else "rgba(239,83,80,0.45)"})

    for v in vp[:20]:
        vp_data.append({"price":v["price"],"vol":v["vol"]})

    max_vol = max([v["vol"] for v in vp_data],default=1)
    if max_vol==0: max_vol=1

    bc         = ai_res.get("bias_color","#f59e0b")
    entry_p    = ai_res.get("entry_zone",{}).get("price",0)
    sl_p       = ai_res.get("stop_loss",{}).get("price",0)
    targets    = ai_res.get("targets",[])
    t1_p       = targets[0]["price"] if targets else 0
    t2_p       = targets[1]["price"] if len(targets)>1 else 0
    supports   = ind.get("supports",[])
    resistances= ind.get("resistances",[])
    vwap_p     = ind.get("vwap",0)
    ema20_p    = ind.get("ema20",0)
    ema50_p    = ind.get("ema50",0)
    fib        = ind.get("fib",{})
    cur_price  = ind.get("price",0)
    rsi_v      = ind.get("rsi",50)
    macd_up    = ind.get("macd_hist",0)>0
    vol_r      = ind.get("vol_ratio",1)
    atr_v      = ind.get("atr",0)
    bias       = ai_res.get("overall_bias","NEUTRAL")
    conf       = ai_res.get("confidence",65)
    rr         = ai_res.get("risk_reward","—")
    tq         = ai_res.get("trade_quality","—")

    # Voice script
    voice_text = ai_res.get("voice_explanation","")
    voice_json = json.dumps(voice_text)

    # Patterns for JS markers
    pat_markers=[]
    if candle_data:
        for pt in patterns[:5]:
            bar_i = min(pt.get("bar",len(candle_data)-1), len(candle_data)-1)
            if 0<=bar_i<len(candle_data):
                cdl = candle_data[bar_i]
                pcolor={"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#f59e0b"}.get(pt["type"],"#f59e0b")
                pshape="arrowUp" if pt["type"]=="BULLISH" else ("arrowDown" if pt["type"]=="BEARISH" else "circle")
                ppos = "belowBar" if pt["type"]=="BULLISH" else ("aboveBar" if pt["type"]=="BEARISH" else "inBar")
                pat_markers.append({
                    "time":cdl["time"],"position":ppos,"color":pcolor,
                    "shape":pshape,"text":pt["name"][:12]
                })

    # Volume profile HTML bars
    vp_sorted = sorted(vp_data, key=lambda x:x["price"],reverse=True)
    vp_html = ""
    for vp_item in vp_sorted[:20]:
        pct = min(vp_item["vol"]/max_vol*100,100)
        is_poc = (vp_item["vol"]==max_vol)
        color = "rgba(41,98,255,0.7)" if is_poc else "rgba(41,98,255,0.3)"
        vp_html += f'<div class="vp-bar"><div class="vp-fill" style="width:{pct:.0f}%;background:{color};"></div><span class="vp-label">{vp_item["price"]:.1f}</span></div>'

    body_h = chart_height - 30  # footer is 30px
    footer_items = [
        f"RSI: <b style=\"color:{'#26a69a' if rsi_v<50 else '#ef5350'}\">{rsi_v:.0f}</b>",
        f"MACD: <b style=\"color:{'#26a69a' if macd_up else '#ef5350'}\">{'▲ Bull' if macd_up else '▼ Bear'}</b>",
        f"Vol: <b>{vol_r:.1f}x</b>",
        f"ATR: <b>{atr_v:.4f}</b>",
        f"VWAP: <b>{vwap_p:.4f}</b>",
        f"<b style=\"color:{bc}\">{rr} · {tq}</b>",
    ]
    footer_html = " &nbsp;|&nbsp; ".join(footer_items)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#131722;font-family:'Trebuchet MS',sans-serif;
  color:#d1d4dc;width:100%;height:{chart_height}px;overflow:hidden;}}
#root{{display:flex;flex-direction:row;width:100%;height:{chart_height}px;}}
#chart-wrap{{flex:1;position:relative;min-width:0;height:{chart_height}px;display:flex;flex-direction:column;}}
#chart-area{{flex:1;position:relative;}}
#chart-div{{width:100%;height:{body_h}px;}}
#footer{{height:30px;background:#1e222d;border-top:1px solid #2a2e39;
  display:flex;align-items:center;padding:0 12px;gap:0;font-size:11px;flex-shrink:0;}}
#vp-col{{width:68px;background:#0e1117;border-left:1px solid #2a2e39;
  display:flex;flex-direction:column;height:{chart_height}px;overflow:hidden;}}
.vp-bar{{display:flex;align-items:center;flex:1;padding:0 2px 0 4px;
  border-bottom:1px solid rgba(255,255,255,0.02);min-height:0;}}
.vp-fill{{height:55%;border-radius:1px;min-width:2px;}}
.vp-label{{font-size:7.5px;color:#4a5568;margin-left:2px;white-space:nowrap;overflow:hidden;}}
/* Legend */
#legend{{position:absolute;top:8px;left:8px;z-index:20;
  background:rgba(19,23,34,0.93);border:1px solid #2a2e39;
  border-radius:8px;padding:8px 12px;}}
#legend .l-sym{{font-size:13px;font-weight:700;color:#d1d4dc;}}
#legend .l-price{{font-size:20px;font-weight:900;color:{bc};font-family:monospace;margin:2px 0;}}
#legend .l-badge{{display:inline-block;padding:2px 9px;border-radius:10px;font-size:10px;
  font-weight:700;background:{bc}22;color:{bc};border:1px solid {bc}44;}}
/* Levels panel */
#ai-levels{{position:absolute;top:8px;right:4px;z-index:20;
  background:rgba(19,23,34,0.93);border:1px solid #2a2e39;
  border-radius:8px;padding:8px 10px;min-width:145px;}}
#ai-levels .al-h{{font-size:9px;font-weight:700;color:#6a6e7a;text-transform:uppercase;
  letter-spacing:0.1em;margin-bottom:5px;}}
#ai-levels .al-row{{font-size:11px;display:flex;justify-content:space-between;
  align-items:center;gap:8px;padding:2px 0;border-bottom:1px solid #1a1e2d;}}
/* Voice panel */
#voice-panel{{position:absolute;bottom:36px;left:8px;right:76px;z-index:20;
  background:rgba(19,23,34,0.95);border:1px solid #2962ff44;border-radius:8px;
  padding:8px 12px;display:none;max-height:90px;overflow:hidden;}}
#voice-panel.visible{{display:block;}}
#voice-text{{font-size:11px;color:#9598a1;line-height:1.5;}}
/* Voice btn */
#voice-btn{{position:absolute;bottom:36px;right:76px;z-index:21;
  background:#2962ff;border:none;border-radius:50%;width:32px;height:32px;
  cursor:pointer;color:white;font-size:14px;display:flex;align-items:center;
  justify-content:center;box-shadow:0 2px 12px rgba(41,98,255,0.5);}}
#voice-btn:hover{{background:#1e56e8;}}
/* Conf bar */
#conf-bar{{position:absolute;top:8px;left:50%;transform:translateX(-50%);z-index:20;
  background:rgba(19,23,34,0.9);border:1px solid #2a2e39;border-radius:8px;
  padding:5px 10px;display:flex;align-items:center;gap:8px;font-size:11px;}}
</style>
</head>
<body>
<div id="root">
  <div id="chart-wrap">
    <div id="chart-area">
      <div id="chart-div"></div>
      <!-- Legend top-left -->
      <div id="legend">
        <div class="l-sym">{sym}</div>
        <div class="l-price">{cur_price:.4f}</div>
        <div class="l-badge">{bias} · {conf}%</div>
      </div>
      <!-- Confidence bar top-center -->
      <div id="conf-bar">
        <span style="color:#6a6e7a;">SAGE AI</span>
        <div style="width:80px;height:5px;background:#1a1e2d;border-radius:3px;">
          <div style="width:{conf}%;height:5px;background:{bc};border-radius:3px;"></div>
        </div>
        <span style="color:{bc};font-weight:700;">{conf}%</span>
      </div>
      <!-- AI Levels top-right -->
      <div id="ai-levels">
        <div class="al-h">AI Levels</div>
        <div class="al-row"><span style="color:#26a69a;font-weight:600;">Entry</span><span style="color:#26a69a;font-family:monospace;">{entry_p:.4f}</span></div>
        <div class="al-row"><span style="color:#ef5350;font-weight:600;">Stop</span><span style="color:#ef5350;font-family:monospace;">{sl_p:.4f}</span></div>
        {'<div class="al-row"><span style="color:#2962ff;">T1</span><span style="color:#2962ff;font-family:monospace;">'+str(round(t1_p,4))+'</span></div>' if t1_p else ''}
        {'<div class="al-row"><span style="color:#9c27b0;">T2</span><span style="color:#9c27b0;font-family:monospace;">'+str(round(t2_p,4))+'</span></div>' if t2_p else ''}
        <div class="al-row" style="border:none;margin-top:3px;">
          <span style="color:#6a6e7a;font-size:9px;">R:R</span>
          <span style="font-weight:700;font-size:11px;">{rr}</span>
        </div>
      </div>
      <!-- Voice panel bottom -->
      <div id="voice-panel">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
          <span style="color:#2962ff;font-weight:700;font-size:11px;">🔊 SAGE Voice</span>
          <span id="voice-status" style="color:#6a6e7a;font-size:10px;">Click ▶ to hear analysis</span>
        </div>
        <div id="voice-text">{ai_res.get('summary','')}</div>
      </div>
      <button id="voice-btn" onclick="toggleVoice()" title="Voice Analysis">🔊</button>
    </div>
    <!-- Footer stats bar -->
    <div id="footer">{footer_html}</div>
  </div>
  <!-- Volume profile sidebar -->
  <div id="vp-col">
    <div style="font-size:8px;color:#6a6e7a;text-align:center;padding:3px 0;
    border-bottom:1px solid #2a2e39;font-weight:700;letter-spacing:0.05em;">VOL PROFILE</div>
    {vp_html}
  </div>
</div>

<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function() {{
  const CHART_H = {body_h};
  const candles = {json.dumps(candle_data)};
  const vols    = {json.dumps(vol_data)};
  const supp    = {json.dumps(supports)};
  const res     = {json.dumps(resistances)};
  const fib     = {json.dumps(fib)};
  const markers = {json.dumps(pat_markers)};
  const voiceText = {voice_json};

  // Wait for DOM
  window.addEventListener('DOMContentLoaded', function() {{
    initChart();
  }});
  if (document.readyState !== 'loading') {{
    initChart();
  }}

  var chart, cs, speaking=false;

  function initChart() {{
    var container = document.getElementById('chart-div');
    if (!container) return;
    var W = container.parentElement.clientWidth - 68;
    if (W<=0) W = window.innerWidth - 80;

    chart = LightweightCharts.createChart(container, {{
      width: W,
      height: CHART_H,
      layout: {{ background:{{type:'solid',color:'#131722'}}, textColor:'#d1d4dc' }},
      grid:   {{ vertLines:{{color:'rgba(255,255,255,0.04)'}}, horzLines:{{color:'rgba(255,255,255,0.04)'}} }},
      crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
      rightPriceScale: {{ borderColor:'#2a2e39' }},
      timeScale: {{ borderColor:'#2a2e39', timeVisible:true, secondsVisible:false }},
      handleScroll: {{ mouseWheel:true, pressedMouseMove:true }},
      handleScale:  {{ mouseWheel:true, pinch:true }},
    }});

    // Candlestick series
    cs = chart.addCandlestickSeries({{
      upColor:'#26a69a', downColor:'#ef5350',
      borderUpColor:'#26a69a', borderDownColor:'#ef5350',
      wickUpColor:'#26a69a', wickDownColor:'#ef5350',
    }});
    if (candles.length > 0) {{
      cs.setData(candles);
    }}

    // Volume histogram
    var vs = chart.addHistogramSeries({{
      priceScaleId: 'vol',
      scaleMargins: {{ top: 0.78, bottom: 0 }},
    }});
    chart.priceScale('vol').applyOptions({{ scaleMargins: {{ top:0.78, bottom:0 }} }});
    if (vols.length > 0) {{ vs.setData(vols); }}

    // Pattern markers on candlestick series
    if (markers.length > 0) {{
      cs.setMarkers(markers);
    }}

    // Support lines
    supp.forEach(function(s) {{
      cs.createPriceLine({{ price:s, color:'#26a69a', lineWidth:1,
        lineStyle:LightweightCharts.LineStyle.Dashed, axisLabelVisible:true, title:'S' }});
    }});
    // Resistance lines
    res.forEach(function(r) {{
      cs.createPriceLine({{ price:r, color:'#ef5350', lineWidth:1,
        lineStyle:LightweightCharts.LineStyle.Dashed, axisLabelVisible:true, title:'R' }});
    }});
    // Fibonacci levels
    var fibColors={{'0.236':'#7986cb','0.382':'#26a69a','0.500':'#fbbf24','0.618':'#ef5350','0.786':'#e040fb'}};
    Object.keys(fib).forEach(function(k) {{
      if (fib[k]) cs.createPriceLine({{
        price:fib[k], color:fibColors[k]||'#aaa', lineWidth:1,
        lineStyle:LightweightCharts.LineStyle.Dotted, axisLabelVisible:true, title:'Fib '+k
      }});
    }});
    // Entry, SL, T1, T2
    if ({int(bool(entry_p))}) cs.createPriceLine({{ price:{entry_p or 0}, color:'#26a69a', lineWidth:2,
      lineStyle:LightweightCharts.LineStyle.Solid, axisLabelVisible:true, title:'ENTRY' }});
    if ({int(bool(sl_p))}) cs.createPriceLine({{ price:{sl_p or 0}, color:'#ef5350', lineWidth:2,
      lineStyle:LightweightCharts.LineStyle.Solid, axisLabelVisible:true, title:'STOP' }});
    if ({int(bool(t1_p))}) cs.createPriceLine({{ price:{t1_p or 0}, color:'#2962ff', lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dashed, axisLabelVisible:true, title:'T1' }});
    if ({int(bool(t2_p))}) cs.createPriceLine({{ price:{t2_p or 0}, color:'#9c27b0', lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dashed, axisLabelVisible:true, title:'T2' }});
    // VWAP
    if ({int(bool(vwap_p))}) cs.createPriceLine({{ price:{vwap_p or 0}, color:'#fbbf24', lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dotted, axisLabelVisible:true, title:'VWAP' }});
    // EMA20, EMA50
    if ({int(bool(ema20_p))}) cs.createPriceLine({{ price:{ema20_p or 0}, color:'#2196f3', lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Solid, axisLabelVisible:false, title:'EMA20' }});
    if ({int(bool(ema50_p))}) cs.createPriceLine({{ price:{ema50_p or 0}, color:'#ff9800', lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Solid, axisLabelVisible:false, title:'EMA50' }});

    chart.timeScale().fitContent();

    // Resize
    window.addEventListener('resize', function() {{
      var nw = document.getElementById('chart-div').parentElement.clientWidth - 68;
      chart.applyOptions({{ width: nw>0 ? nw : 400, height: CHART_H }});
    }});
  }}

  // Voice
  window.toggleVoice = function() {{
    var panel = document.getElementById('voice-panel');
    var status = document.getElementById('voice-status');
    var textEl = document.getElementById('voice-text');
    if (!panel) return;
    if (!panel.classList.contains('visible')) {{
      panel.classList.add('visible');
      textEl.textContent = voiceText || 'Voice analysis ready';
      if ('speechSynthesis' in window) {{
        window.speechSynthesis.cancel();
        var utt = new SpeechSynthesisUtterance(voiceText || 'Analysis ready');
        utt.lang = 'hi-IN';
        utt.rate = 0.9; utt.pitch = 1;
        var voices = window.speechSynthesis.getVoices();
        var hiVoice = voices.find(function(v){{ return v.lang==='hi-IN'; }});
        var enVoice = voices.find(function(v){{ return v.lang.startsWith('en'); }});
        if (hiVoice) utt.voice=hiVoice; else if(enVoice) utt.voice=enVoice;
        status.textContent='Speaking...';
        utt.onend=function(){{ status.textContent='Done. Tap again to replay.'; }};
        window.speechSynthesis.speak(utt);
      }} else {{
        status.textContent='Web Speech not supported in this browser';
      }}
    }} else {{
      panel.classList.remove('visible');
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    }}
  }};
}})();
</script>
</body>
</html>"""

# ══════════════════════════════════════════════════════════════════════════════
# RIGHT PANEL — TradingView style analysis panel
# ══════════════════════════════════════════════════════════════════════════════
def _render_fp_panel(ind:dict, ai_res:dict, patterns:list, vp:list, sym:str):
    bc = ai_res.get("bias_color","#f59e0b")
    tq_color={"EXCELLENT":"#26a69a","GOOD":"#2962ff","AVERAGE":"#f59e0b","POOR":"#ef5350"}.get(ai_res.get("trade_quality",""),"#6a6e7a")
    conf=ai_res.get("confidence",65); rr=ai_res.get("risk_reward","—"); tq=ai_res.get("trade_quality","—")
    entry_p=ai_res.get("entry_zone",{}).get("price",0); sl_p=ai_res.get("stop_loss",{}).get("price",0)
    targets=ai_res.get("targets",[])

    st.markdown("""<style>
    .fp-row{display:flex;justify-content:space-between;align-items:center;
      padding:4px 0;border-bottom:1px solid #1a1e2d;font-size:12px;}
    .fp-section{color:#6a6e7a;font-size:10px;font-weight:700;text-transform:uppercase;
      letter-spacing:0.08em;margin:10px 0 5px 0;}
    .fp-chip{display:inline-block;padding:3px 8px;border-radius:12px;font-size:10px;
      font-weight:600;margin:2px;}
    .fp-obs{font-size:11px;color:#9598a1;padding:3px 0;border-bottom:1px solid #1a1e2d;line-height:1.4;}
    </style>""", unsafe_allow_html=True)

    # Bias card
    st.markdown(f"""<div style="background:{bc}11;border:1px solid {bc}33;border-radius:8px;
    padding:12px;margin-bottom:8px;text-align:center;">
      <div style="font-size:24px;font-weight:900;color:{bc};">{ai_res.get('overall_bias','NEUTRAL')}</div>
      <div style="color:#6a6e7a;font-size:10px;margin:3px 0;">AI Confidence</div>
      <div style="background:#0e1117;border-radius:100px;height:5px;margin:4px 0;">
        <div style="background:{bc};height:5px;border-radius:100px;width:{conf}%;"></div>
      </div>
      <div style="color:{bc};font-size:11px;font-weight:600;">{conf}%</div>
    </div>""", unsafe_allow_html=True)

    # Summary
    st.markdown(f"""<div style="background:#1e222d;border-left:3px solid {bc};border-radius:0 6px 6px 0;
    padding:7px 10px;margin-bottom:8px;font-size:11px;color:#9598a1;line-height:1.5;">
    {ai_res.get('summary','')[:120]}</div>""", unsafe_allow_html=True)

    # Trade Levels
    st.markdown('<div class="fp-section">TRADE LEVELS</div>', unsafe_allow_html=True)
    levels=[("Entry",entry_p,"#26a69a"),("Stop Loss",sl_p,"#ef5350")]
    for t in targets[:2]: levels.append((t["label"],t["price"],"#2962ff" if t["label"]=="T1" else "#9c27b0"))
    for label,price,color in levels:
        if price: st.markdown(f'<div class="fp-row"><span style="color:{color};font-weight:600;">{label}</span><span style="color:{color};font-family:monospace;font-weight:700;">{price:.4f}</span></div>', unsafe_allow_html=True)
    st.markdown(f"""<div style="background:#1e222d;border-radius:6px;padding:6px 10px;margin:6px 0;
    display:flex;justify-content:space-between;font-size:11px;">
      <span style="color:#6a6e7a;">Risk:Reward</span>
      <span style="color:#d1d4dc;font-weight:700;">{rr}</span>
      <span style="color:{tq_color};font-weight:700;">{tq}</span>
    </div>""", unsafe_allow_html=True)

    # Indicators
    ind_sig=ai_res.get("indicator_signals",{})
    if ind_sig:
        st.markdown('<div class="fp-section">INDICATORS</div>', unsafe_allow_html=True)
        for k,v in ind_sig.items():
            c2="#26a69a" if any(w in str(v).lower() for w in ["bull","above","oversold","confirm","strong","green"]) \
               else "#ef5350" if any(w in str(v).lower() for w in ["bear","below","overbought","sell","weak","red"]) \
               else "#6a6e7a"
            st.markdown(f'<div class="fp-row"><span style="color:#9598a1;">{k}</span><span style="color:{c2};font-size:10px;">{str(v)[:28]}</span></div>', unsafe_allow_html=True)

    # Patterns
    if patterns:
        st.markdown('<div class="fp-section">DETECTED PATTERNS</div>', unsafe_allow_html=True)
        for p in patterns[:6]:
            pc={"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#f59e0b"}.get(p["type"],"#6a6e7a")
            st.markdown(f'<span class="fp-chip" style="background:{pc}22;color:{pc};border:1px solid {pc}44;" title="{p.get("desc","")}">{p["name"]}</span>', unsafe_allow_html=True)

    # Key observations
    obs=ai_res.get("key_observations",[])
    if obs:
        st.markdown('<div class="fp-section">KEY OBSERVATIONS</div>', unsafe_allow_html=True)
        for o in obs[:4]: st.markdown(f'<div class="fp-obs">• {o}</div>', unsafe_allow_html=True)

    # Footprint insight
    fp=ai_res.get("footprint_insight","")
    if fp: st.markdown(f"""<div style="background:#1a1e2d;border-left:3px solid #2962ff;
    border-radius:0 6px 6px 0;padding:7px 10px;margin-top:8px;font-size:11px;color:#9598a1;line-height:1.5;">
    <b style="color:#2962ff;">Order Flow:</b> {fp}</div>""", unsafe_allow_html=True)

    # Multi-timeframe
    mtf=ai_res.get("multi_timeframe",{})
    if mtf:
        st.markdown('<div class="fp-section">MULTI-TIMEFRAME</div>', unsafe_allow_html=True)
        for tf_label,val in mtf.items():
            st.markdown(f'<div class="fp-row"><span style="color:#6a6e7a;">{tf_label.upper()}</span><span style="color:#9598a1;font-size:10px;">{str(val)[:30]}</span></div>', unsafe_allow_html=True)

    # Risk
    rn=ai_res.get("risk_note","")
    if rn: st.markdown(f'<div style="background:#1a1500;border:1px solid #3d2e00;border-radius:6px;padding:6px 10px;margin-top:8px;font-size:10px;color:#8b8070;">⚠️ {rn}</div>', unsafe_allow_html=True)
    st.markdown('<div style="background:#0e1117;border-radius:6px;padding:5px 8px;margin-top:8px;font-size:9px;color:#4a5568;text-align:center;">📊 Educational only · Not financial advice · Past ≠ future</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE RENDERER
# ══════════════════════════════════════════════════════════════════════════════
def render_footprint_chart():
    st.markdown("""<style>
    header[data-testid="stHeader"],footer,
    div[data-testid="stDecoration"],div[data-testid="stToolbar"],
    div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}
    .block-container{padding:0.3rem!important;max-width:100vw!important;}
    .stHorizontalBlock{gap:4px!important;}
    </style>""", unsafe_allow_html=True)

    # ── Top control bar ───────────────────────────────────────────────────────
    c1,c2,c3,c4 = st.columns([4,2,2,1])
    with c1:
        st.markdown("""<div style="background:#1e222d;border:1px solid #2a2e39;border-radius:8px;
        padding:6px 12px;display:flex;align-items:center;gap:8px;">
          <span style="color:#2962ff;font-size:16px;">⬡</span>
          <span style="color:#d1d4dc;font-weight:700;">SAGE Footprint Chart</span>
          <span style="background:#2962ff22;color:#2962ff;font-size:9px;padding:2px 7px;
          border-radius:10px;border:1px solid #2962ff44;font-weight:700;">AI ANALYSIS</span>
        </div>""", unsafe_allow_html=True)
    with c2:
        sym_raw = st.text_input("Symbol","",placeholder="RELIANCE, BTC, AAPL...",
                                 key="fp_sym_in", label_visibility="collapsed")
    with c3:
        tf_choice = st.selectbox("TF",["1D","1H","15m","4H","1W"],
                                  key="fp_tf_sel", label_visibility="collapsed")
    with c4:
        refresh = st.button("🔄",key="fp_ref",use_container_width=True,help="Refresh AI")

    # Quick symbols
    qs=["BTC","ETH","RELIANCE","TCS","AAPL","TSLA","NVDA","NIFTY","INFY","GOLD"]
    qc=st.columns(len(qs))
    for i,q in enumerate(qs):
        with qc[i]:
            if st.button(q,key=f"fpq_{i}",use_container_width=True):
                st.session_state.fp_sym_sel=q; st.rerun()

    sym_input=(st.session_state.get("fp_sym_sel","") or sym_raw or "RELIANCE.NS").strip()
    sym=resolve_ticker(sym_input)

    tf_map={"1D":("1y","1d"),"1H":("1mo","1h"),"15m":("5d","15m"),
            "4H":("3mo","1d"),"1W":("2y","1wk")}
    period,interval=tf_map.get(tf_choice,("1y","1d"))

    # ── Load + compute ────────────────────────────────────────────────────────
    with st.spinner(f"Loading {sym}..."):
        df = _fetch_data(sym,period,interval)

    if df.empty:
        st.error(f"❌ No data for `{sym}`. Try: RELIANCE.NS, AAPL, BTC-USD")
        return

    ind      = _compute_indicators(df)
    patterns = _detect_patterns(df)
    vp       = _build_volume_profile(df)

    cache_key=f"fp_ai_{sym}_{tf_choice}"
    if st.session_state.get(cache_key) is None or refresh:
        with st.spinner("SAGE AI analyzing..."):
            ai_res=_ai_footprint_analysis(sym,ind,patterns,vp)
        st.session_state[cache_key]=ai_res
    else:
        ai_res=st.session_state[cache_key]

    # ── Main layout: chart (3) + analysis panel (1) ──────────────────────────
    chart_col, panel_col = st.columns([3,1], gap="small")

    with chart_col:
        html = _build_footprint_html(df,ind,ai_res,patterns,vp,sym,CHART_H)
        components.html(html, height=IFRAME_H, scrolling=False)

    with panel_col:
        _render_fp_panel(ind,ai_res,patterns,vp,sym)
