"""
FinSage AI — Personal Dashboard
Favourite stocks · AI auto-draws EVERYTHING on inbuilt chart
6 Trader Types: PA · SMC · Quant · Indicator · Volume · Elliott Wave
"""
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import json, os, requests
from datetime import datetime

try:
    from pro_chart import _price_fast, _ohlcv, _compute_tech, _global_search as _srch
except Exception as e:
    st.error(f"Import error: {e}"); st.stop()

try:
    from market_dashboard import _fundamental
except Exception:
    _fundamental = lambda s: {}

def _key(n):
    try: return st.secrets.get(n) or os.environ.get(n,"")
    except: return os.environ.get(n,"")

GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

DEFAULT_FAVS = [
    {"sym":"^NSEI",        "name":"NIFTY 50",  "type":"index"},
    {"sym":"RELIANCE.NS",  "name":"Reliance",  "type":"stock"},
    {"sym":"TCS.NS",       "name":"TCS",       "type":"stock"},
    {"sym":"HDFCBANK.NS",  "name":"HDFC Bank", "type":"stock"},
    {"sym":"AAPL",         "name":"Apple",     "type":"stock"},
    {"sym":"BTC-USD",      "name":"Bitcoin",   "type":"crypto"},
]
SECTOR_STOCKS = {
    "🏦 Banking":["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS"],
    "💻 IT":     ["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS"],
    "⚡ Energy": ["RELIANCE.NS","NTPC.NS","POWERGRID.NS","ADANIGREEN.NS","ONGC.NS"],
    "🏗️ Infra":  ["ADANIENT.NS","LTIM.NS","BAJAJFINSV.NS","MARUTI.NS","TATAMOTORS.NS"],
    "🌐 US Tech":["AAPL","TSLA","NVDA","MSFT","GOOGL","META","AMZN"],
    "🪙 Crypto": ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD"],
}

# ════════════════════════════════════════════════════════════════════════
# MASTER AI ANALYSIS — All 6 trader types in one prompt
# ════════════════════════════════════════════════════════════════════════
def _master_analysis(sym, name, tech, fund):
    groq_k = _key("GROQ_API_KEY"); ds_k = _key("DEEPSEEK_API_KEY")
    p=tech.get("price",0); rsi=tech.get("rsi",50); trend=tech.get("trend","?")
    sup=tech.get("supports",[]); res=tech.get("resistances",[])
    entry=sup[0] if sup else p*0.99; sl=sup[1] if len(sup)>1 else p*0.97
    t1=res[0] if res else p*1.04; t2=res[1] if len(res)>1 else p*1.08
    rr=(t1-entry)/(entry-sl) if entry-sl>0 else 1.5
    pats=[x["name"] for x in tech.get("patterns",[])[:5]]
    ob=tech.get("order_blocks",[]); fvg=tech.get("fvg",[])
    fib=tech.get("fib",{})

    prompt = f"""You are SAGE, the world's best AI trading analyst. Analyze {name} ({sym}) from ALL 6 trader perspectives.

DATA:
Price={p:.4f} | Open={tech.get('open',0):.4f} | High={tech.get('high',0):.4f} | Low={tech.get('low',0):.4f}
RSI={rsi:.1f} | StochRSI={tech.get('stoch_rsi',50):.1f} | MACD_Hist={tech.get('macd_h',0):.4f}
EMA9={tech.get('ema9',0):.4f} | EMA20={tech.get('ema20',0):.4f} | EMA50={tech.get('ema50',0):.4f} | EMA200={tech.get('ema200',0):.4f}
BB_Upper={tech.get('bb_upper',0):.4f} | BB_Lower={tech.get('bb_lower',0):.4f} | BB_Width={tech.get('bb_width',0):.2f}%
ATR={tech.get('atr',0):.4f} | VWAP={tech.get('vwap',0):.4f} | VolRatio={tech.get('vol_ratio',1):.2f}x
Supports={sup[:4]} | Resistances={res[:4]} | Fib={fib}
Patterns={pats} | OrderBlocks={ob[:2]} | FVG={fvg[:2]}
Sector={fund.get('sector','—')} | PE={fund.get('pe','—')} | MarketCap={fund.get('mktcap_str','—')} | Beta={fund.get('beta','—')}

Return ONLY valid JSON (no markdown fences):
{{
  "bias":"BULLISH","bias_color":"#26a69a","rating":"BUY","rating_color":"#26a69a",
  "confidence":82,"price_target":{round(t1,4)},
  "entry":{round(entry,4)},"stop":{round(sl,4)},"t1":{round(t1,4)},"t2":{round(t2,4)},
  "rr":"1:{rr:.1f}","quality":"GOOD",

  "summary":"3-sentence master summary — prices, percentages, key level. Clear and actionable.",

  "price_action":{{
    "view":"Full PA analysis: key candlestick at this price, chart pattern forming (flag/wedge/double-top etc), trend structure, clean S/R levels. What a PA trader sees. 4-5 sentences.",
    "pattern_detected":"main chart pattern name",
    "pattern_desc":"what this pattern means and target",
    "clean_sr":[{{"level":{round(sup[0],4) if sup else 0},"type":"support","strength":"strong","reason":"why"}}],
    "signal":"BUY/SELL/WAIT",
    "signal_reason":"exact reason based on price action only"
  }},

  "smc":{{
    "view":"Full SMC analysis: premium/discount zone, OB quality, FVG fill probability, liquidity sweep targets, MSS confirmation. 4-5 sentences.",
    "market_structure":"BOS/MSS/CHoCH with description",
    "pd_zone":"PREMIUM/DISCOUNT/EQUILIBRIUM with current price position",
    "ob_zones":[{{"type":"BULL_OB/BEAR_OB","top":{round(res[0],4) if res else 0},"bot":{round(entry,4)},"quality":"HIGH/MEDIUM","filled":false}}],
    "fvg_zones":[{{"type":"BULL/BEAR","top":0,"bot":0,"fill_prob":"HIGH/MEDIUM/LOW"}}],
    "liquidity_pools":[{{"level":{round(sl,4)},"type":"BUY_SIDE/SELL_SIDE","desc":"equal lows/highs target"}}],
    "signal":"BUY/SELL/WAIT",
    "signal_reason":"ICT reasoning"
  }},

  "quant":{{
    "view":"Quant perspective: win-rate probability of current setup, expected value, statistical edge, z-score, correlation. 3-4 sentences.",
    "win_rate":"~60%",
    "expected_value":"computed_value",
    "setup_quality":"A+/A/B/C grade",
    "probability_bullish":"65%",
    "statistical_edge":"describe edge in numbers"
  }},

  "indicator":{{
    "view":"All indicator confluence: RSI+StochRSI+MACD+BB+EMA+VWAP — what they ALL say together. 4-5 sentences.",
    "rsi_read":"RSI <value> — full interpretation with overbought/oversold context",
    "macd_read":"MACD histogram at <value> — direction and momentum",
    "bb_read":"BB width {tech.get('bb_width',0):.2f}% — squeeze or expansion, price position",
    "ema_structure":"price vs EMA9/20/50/200 stack — bullish/bearish alignment",
    "vwap_read":"above/below VWAP significance at {tech.get('vwap',0):.4f}",
    "overall_signal":"BULLISH/BEARISH/NEUTRAL confluence",
    "signal_strength":"STRONG/MODERATE/WEAK"
  }},

  "volume":{{
    "view":"Volume & order flow: POC level, HVN/LVN zones, VWAP relationship, delta direction, institutional footprint. 4-5 sentences.",
    "poc_level":{round((p*0.98),4)},
    "poc_significance":"what POC at this level means for next move",
    "hvn_zones":"high volume node levels — price attracted here",
    "lvn_zones":"low volume node levels — price moves fast through",
    "vwap_analysis":"institutional vs retail positioning at current price",
    "volume_delta":"buying/selling pressure direction",
    "money_flow":"net money flow — smart money accumulating/distributing"
  }},

  "wave":{{
    "view":"Elliott Wave + Gann analysis: current wave count, where we are in the cycle, next expected move. 4-5 sentences.",
    "wave_count":"Wave X of 5 — current position (be specific: 'likely in wave 3 of impulse')",
    "wave_target":"next wave target based on Fibonacci extensions",
    "fib_key_levels":{{"0.382":{fib.get('0.382',0)},"0.618":{fib.get('0.618',0)},"1.618":round(p+1.618*(p-sl),4)}},
    "gann_angle":"45-degree Gann angle support/resistance",
    "cycle_phase":"expansion/contraction/reversal",
    "next_move":"expected direction and magnitude"
  }},

  "patterns_detail":[
    {{"name":"pattern","type":"BULLISH/BEARISH/NEUTRAL","desc":"what this means","action":"entry/exit/wait","target":0}}
  ],

  "sr_analysis":[
    {{"level":{round(res[0],4) if res else 0},"type":"resistance","strength":"strong/medium/weak","tests":2,"significance":"why this exact level matters"}},
    {{"level":{round(entry,4)},"type":"support","strength":"strong","tests":3,"significance":"why key"}}
  ],

  "key_levels":{{
    "strong_support":{round(sup[0],4) if sup else 0},
    "major_resistance":{round(res[0],4) if res else 0},
    "fib_618":{fib.get('0.618',round(p*0.99,4))},
    "fib_382":{fib.get('0.382',round(p*1.01,4))},
    "vwap":{round(tech.get('vwap',p),4)},
    "poc":{round(p*0.98,4)}
  }},

  "thesis":["bull point 1 with number","bull point 2","bull point 3"],
  "risks":["risk 1 specific","risk 2","risk 3"],
  "catalyst":"main upcoming catalyst",
  "macro":"macro factor impact",
  "multi_tf":{{"weekly":"weekly bias and setup","daily":"daily setup","hourly":"1H entry zone","15min":"15m trigger"}},
  "fundamental_snap":"PE={fund.get('pe','—')} | MCap={fund.get('mktcap_str','—')} | Sector={fund.get('sector','—')} | Analyst={fund.get('analyst','—')} | Beta={fund.get('beta','—')}",
  "voice":"60-word Hinglish Bloomberg-style brief: {name} ka analysis — rating, entry, stop, target, RSI level, key level aur main reason.",
  "_api":"AI"
}}"""

    for url, k, model in [
        (DEEPSEEK_URL, ds_k, "deepseek-chat"),
        (GROQ_URL, groq_k, "llama-3.3-70b-versatile"),
    ]:
        if not k: continue
        try:
            r = requests.post(url,
                headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.15, "max_tokens": 3000},
                timeout=40)
            raw = r.json()["choices"][0]["message"]["content"].strip()
            if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```"    in raw: raw = raw.split("```")[1].split("```")[0].strip()
            result = json.loads(raw)
            result["_api"] = "DeepSeek" if "deepseek" in url else "Groq"
            return result
        except: continue

    # Rule-based fallback
    bc = "#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"
    return {
        "bias": trend, "bias_color": bc, "rating": "HOLD", "rating_color": "#f59e0b",
        "confidence": 60, "price_target": round(t1,4), "entry": round(entry,4),
        "stop": round(sl,4), "t1": round(t1,4), "t2": round(t2,4),
        "rr": f"1:{rr:.1f}", "quality": "AVERAGE",
        "summary": f"{name}: {trend} trend. RSI {rsi:.0f}. MACD {'bullish' if tech.get('macd_h',0)>0 else 'bearish'}. Key support {round(entry,2)}.",
        "price_action": {"view": f"Price at {p:.4f}. Key S/R: {sup[:2]} / {res[:2]}. Trend: {trend}.","pattern_detected":"Monitor","pattern_desc":"Watch for confirmation","clean_sr":[],"signal":"WAIT","signal_reason":"No clear setup"},
        "smc": {"view": "Monitor OB and FVG zones.","market_structure":"Observing","pd_zone":"EQUILIBRIUM","ob_zones":[],"fvg_zones":[],"liquidity_pools":[],"signal":"WAIT","signal_reason":"Waiting for MSS"},
        "quant": {"view": f"Statistical edge: RSI {rsi:.0f}, Vol {tech.get('vol_ratio',1):.1f}x.","win_rate":"55%","expected_value":str(round(t1-entry,4)),"setup_quality":"B","probability_bullish":"55%","statistical_edge":"Moderate edge"},
        "indicator": {"view": f"RSI {rsi:.0f}, MACD {'bull' if tech.get('macd_h',0)>0 else 'bear'}, Vol {tech.get('vol_ratio',1):.1f}x avg.","rsi_read":f"RSI {rsi:.0f} — neutral","macd_read":"MACD neutral","bb_read":"Mid-band","ema_structure":"Mixed","vwap_read":"Near VWAP","overall_signal":trend,"signal_strength":"MODERATE"},
        "volume": {"view": f"Volume {tech.get('vol_ratio',1):.1f}x avg. VWAP {tech.get('vwap',0):.2f}.","poc_level":round(p*0.98,4),"poc_significance":"Near current price","hvn_zones":"Near support","lvn_zones":"Between S/R","vwap_analysis":"Near VWAP","volume_delta":"Neutral","money_flow":"Mixed"},
        "wave": {"view": "Monitor for impulse confirmation.","wave_count":"Wave structure unclear","wave_target":"Wait for impulse","fib_key_levels":fib,"gann_angle":"Monitor 45°","cycle_phase":"Consolidation","next_move":"Watch for breakout"},
        "patterns_detail": [{"name": x["name"], "type": x["type"], "desc": "Pattern detected", "action": "Monitor", "target": 0} for x in tech.get("patterns",[])[:3]],
        "sr_analysis": [{"level": x, "type":"resistance","strength":"medium","tests":2,"significance":"Pivot level"} for x in res[:2]] + [{"level": x, "type":"support","strength":"medium","tests":2,"significance":"Pivot level"} for x in sup[:2]],
        "key_levels": {"strong_support":round(sup[0],4) if sup else 0,"major_resistance":round(res[0],4) if res else 0,"fib_618":fib.get("0.618",0),"fib_382":fib.get("0.382",0),"vwap":round(tech.get("vwap",p),4),"poc":round(p*0.98,4)},
        "thesis": [f"Trend {trend}", f"RSI {rsi:.0f}", f"Vol {tech.get('vol_ratio',1):.1f}x"],
        "risks": ["Market volatility", "Stop breach", "Macro risk"],
        "catalyst": "Quarterly results", "macro": "Global rate environment",
        "multi_tf": {"weekly": f"Weekly: {trend}","daily": f"RSI {rsi:.0f}","hourly":"Entry zone","15min":"Trigger"},
        "fundamental_snap": f"PE={fund.get('pe','—')} | MCap={fund.get('mktcap_str','—')} | Sector={fund.get('sector','—')}",
        "voice": f"{name} ka analysis — {trend} bias, entry {round(entry,2)}, stop {round(sl,2)}, target {round(t1,2)}. RSI {rsi:.0f} pe hai.",
        "_api": "fallback",
    }


# ════════════════════════════════════════════════════════════════════════
# PERSONAL DASHBOARD CHART — Full AI drawings: ALL 6 trader types visual
# ════════════════════════════════════════════════════════════════════════
def _personal_chart_html(df, tech, ai, sym, height=700):
    candles=[]; vols=[]
    if not df.empty:
        for idx, row in df.tail(300).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            candles.append({"time":ts,"open":round(float(row["Open"]),4),"high":round(float(row["High"]),4),
                            "low":round(float(row["Low"]),4),"close":round(float(row["Close"]),4)})
            vols.append({"time":ts,"value":int(row["Volume"]),
                         "color":"rgba(38,166,154,0.45)" if row["Close"]>=row["Open"] else "rgba(239,83,80,0.45)"})

    sup   = tech.get("supports",[]);     res   = tech.get("resistances",[])
    fib   = tech.get("fib",{});          vwap_v= tech.get("vwap",0)
    e20   = tech.get("ema20",0);         e50   = tech.get("ema50",0); e200 = tech.get("ema200",0)
    cur   = tech.get("price",0);         rsi_v = tech.get("rsi",50)
    macd_h= tech.get("macd_h",0);        vr    = tech.get("vol_ratio",1)
    atr_v = tech.get("atr",0);           bb_w  = tech.get("bb_width",0)
    entry_v=ai.get("entry",0); stop_v=ai.get("stop",0); t1_v=ai.get("t1",0); t2_v=ai.get("t2",0)
    bc    = ai.get("bias_color","#f59e0b"); bias=ai.get("bias","NEUTRAL"); conf=ai.get("confidence",65)
    rr    = ai.get("rr","—"); qual=ai.get("quality","—"); api_u=ai.get("_api","AI")
    voice = json.dumps(ai.get("voice",""))
    kl    = ai.get("key_levels",{})
    poc_v = kl.get("poc",0)
    ob_list= tech.get("order_blocks",[])
    fvg_list=tech.get("fvg",[])

    # Pattern markers
    markers = []
    for pt in tech.get("patterns",[])[:8]:
        bi = min(pt.get("bar", len(candles)-1), len(candles)-1)
        if 0 <= bi < len(candles):
            cdl = candles[bi]
            pc  = {"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#fbbf24"}.get(pt["type"],"#fbbf24")
            ps  = {"BULLISH":"arrowUp","BEARISH":"arrowDown","NEUTRAL":"circle"}.get(pt["type"],"circle")
            pp  = {"BULLISH":"belowBar","BEARISH":"aboveBar","NEUTRAL":"inBar"}.get(pt["type"],"inBar")
            markers.append({"time":cdl["time"],"position":pp,"color":pc,"shape":ps,"text":pt["name"][:10]})

    # Volume profile
    vp = tech.get("vp",[]); max_vp = max([x["vol"] for x in vp], default=1) or 1
    vp_html = ""
    for vi in sorted(vp[:24], key=lambda x: -x["price"]):
        pct = min(vi["vol"]/max_vp*100, 100); is_poc = vi["vol"] == max_vp
        col = "rgba(41,98,255,0.9)" if is_poc else "rgba(41,98,255,0.25)"
        vp_html += f'<div class="vpb"><div class="vpf" style="width:{pct:.0f}%;background:{col};"></div><span class="vpl">{vi["price"]:.1f}</span></div>'

    body_h = height - 36

    # SMC OB zones for JS overlay
    ob_js = json.dumps(ob_list[:4])
    fvg_js = json.dumps(fvg_list[:4])

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#080b12;color:#d1d4dc;font-family:'Inter','Segoe UI',sans-serif;width:100%;height:{height}px;overflow:hidden;}}
#root{{width:100%;height:{height}px;display:flex;flex-direction:column;}}

/* TOOLBAR */
#tb{{height:36px;background:rgba(19,23,34,0.97);backdrop-filter:blur(20px);
  border-bottom:1px solid rgba(255,255,255,0.05);display:flex;align-items:center;
  padding:0 8px;gap:4px;flex-shrink:0;}}
.tb-lbl{{font-size:8.5px;color:#374151;text-transform:uppercase;letter-spacing:.08em;margin:0 2px;}}
.tb-sep{{width:1px;height:18px;background:rgba(255,255,255,0.06);margin:0 3px;}}
.tb-btn{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
  border-radius:5px;color:#6a6e7a;font-size:10px;padding:3px 7px;cursor:pointer;
  transition:all .15s;white-space:nowrap;font-family:inherit;}}
.tb-btn:hover{{background:rgba(41,98,255,0.15);border-color:rgba(41,98,255,0.4);color:#4a9eff;}}
.tb-btn.on{{background:rgba(41,98,255,0.18);border-color:rgba(41,98,255,0.45);color:#4a9eff;}}

/* MAIN */
#cw{{flex:1;display:flex;height:{body_h}px;position:relative;}}
#ca{{flex:1;position:relative;min-width:0;height:{body_h}px;}}
#cd{{width:100%;height:{body_h}px;}}
#vps{{width:56px;background:#050709;border-left:1px solid rgba(255,255,255,0.03);
  display:flex;flex-direction:column;height:{body_h}px;overflow:hidden;flex-shrink:0;}}
.vpb{{display:flex;align-items:center;flex:1;padding:0 2px;min-height:0;border-bottom:1px solid rgba(255,255,255,0.01);}}
.vpf{{height:58%;border-radius:1px;min-width:2px;}}
.vpl{{font-size:6.5px;color:#2d3748;margin-left:2px;white-space:nowrap;overflow:hidden;max-width:28px;}}

/* STATUS BAR */
#sb{{height:36px;background:rgba(13,17,28,0.99);border-top:1px solid rgba(255,255,255,0.04);
  display:flex;align-items:center;padding:0 10px;font-size:11px;gap:10px;flex-shrink:0;overflow:hidden;}}

/* GLASS PANELS */
.glass{{background:rgba(10,13,22,0.85);backdrop-filter:blur(22px);
  border:1px solid rgba(255,255,255,0.08);border-radius:12px;
  box-shadow:0 8px 32px rgba(0,0,0,0.5);}}
#g-info{{position:absolute;top:8px;left:8px;z-index:30;padding:10px 14px;pointer-events:none;min-width:175px;}}
#g-info .sym{{font-size:13px;font-weight:800;color:#fff;}}
#g-info .prc{{font-size:22px;font-weight:900;color:{bc};font-family:'Courier New',monospace;margin:3px 0;}}
#g-info .bge{{display:inline-block;padding:2px 10px;border-radius:16px;font-size:10px;font-weight:700;background:{bc}18;color:{bc};border:1px solid {bc}33;}}
#g-lvl{{position:absolute;top:8px;right:4px;z-index:30;padding:10px 12px;min-width:155px;}}
#g-lvl .lh{{font-size:8.5px;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px;}}
.lr{{display:flex;justify-content:space-between;gap:8px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:11.5px;}}
.lr:last-child{{border:none;}}
#g-ind{{position:absolute;bottom:44px;left:60px;right:62px;z-index:20;padding:5px 10px;display:none;}}
#g-ind.vis{{display:flex;gap:14px;flex-wrap:wrap;align-items:center;}}
.ii{{font-size:10.5px;}} .il{{color:#374151;font-size:8.5px;text-transform:uppercase;}} .iv{{font-weight:700;}}
#vbtn{{position:absolute;bottom:44px;right:5px;z-index:31;width:36px;height:36px;
  background:rgba(41,98,255,0.85);border:1px solid rgba(41,98,255,0.4);border-radius:50%;
  color:#fff;font-size:15px;cursor:pointer;box-shadow:0 4px 18px rgba(41,98,255,0.4);}}
#vpop{{position:absolute;bottom:86px;right:5px;z-index:32;padding:8px 12px;display:none;border-radius:10px;font-size:11px;}}
#vpop.vis{{display:block;}}

/* SMC zone overlays — shown as price lines, so JS handles */
</style></head><body>
<div id="root">

<!-- TOOLBAR -->
<div id="tb">
  <span style="font-size:11px;font-weight:900;color:#fff;">FinSage <span style="color:#2962ff;">PRO</span></span>
  <div class="tb-sep"></div>
  <span class="tb-lbl">Chart</span>
  <button class="tb-btn on" onclick="setStyle('candle')" id="b-c">Candle</button>
  <button class="tb-btn" onclick="setStyle('area')"   id="b-a">Area</button>
  <button class="tb-btn" onclick="setStyle('ha')"     id="b-h">Heikin Ashi</button>
  <div class="tb-sep"></div>
  <span class="tb-lbl">Layers</span>
  <button class="tb-btn on" onclick="tog('sr')"   id="l-sr">S/R</button>
  <button class="tb-btn on" onclick="tog('fib')"  id="l-fib">Fib</button>
  <button class="tb-btn on" onclick="tog('ema')"  id="l-ema">EMA</button>
  <button class="tb-btn on" onclick="tog('vwap')" id="l-vwap">VWAP</button>
  <button class="tb-btn on" onclick="tog('ai')"   id="l-ai">AI Levels</button>
  <button class="tb-btn on" onclick="tog('pat')"  id="l-pat">Patterns</button>
  <button class="tb-btn"    onclick="tog('ob')"   id="l-ob">OB</button>
  <button class="tb-btn"    onclick="tog('fvg')"  id="l-fvg">FVG</button>
  <button class="tb-btn"    onclick="tog('poc')"  id="l-poc">POC</button>
  <div class="tb-sep"></div>
  <button class="tb-btn" onclick="togInd()" id="b-ind">Indicators</button>
  <button class="tb-btn" onclick="fitC()">Fit</button>
  <div style="flex:1;"></div>
  <span style="font-size:9px;color:#374151;">via {api_u}</span>
</div>

<div id="cw">
  <div id="ca">
    <div id="cd"></div>

    <!-- Glass info -->
    <div id="g-info" class="glass">
      <div class="sym">{sym}</div>
      <div class="prc">{cur:.4f}</div>
      <div class="bge">{bias} · {conf}% conf</div>
    </div>

    <!-- Glass AI levels -->
    <div id="g-lvl" class="glass">
      <div class="lh">SAGE AI · {api_u}</div>
      <div class="lr"><span style="color:#26a69a;font-weight:700;">Entry</span><span style="color:#26a69a;font-family:'Courier New';">{entry_v:.4f}</span></div>
      <div class="lr"><span style="color:#ef5350;font-weight:700;">Stop</span> <span style="color:#ef5350;font-family:'Courier New';" >{stop_v:.4f}</span></div>
      {'<div class="lr"><span style="color:#2962ff;">T1</span><span style="color:#2962ff;font-family:Courier New">'+str(round(t1_v,4))+'</span></div>' if t1_v else ''}
      {'<div class="lr"><span style="color:#9c27b0;">T2</span><span style="color:#9c27b0;font-family:Courier New">'+str(round(t2_v,4))+'</span></div>' if t2_v else ''}
      <div class="lr" style="margin-top:3px;"><span style="color:#374151;font-size:9px;">R:R</span><span style="font-weight:900;font-size:14px;color:{bc};">{rr}</span></div>
    </div>

    <!-- Indicator panel -->
    <div id="g-ind" class="glass">
      <div class="ii"><div class="il">RSI</div><div class="iv" style="color:{'#ef5350' if rsi_v>70 else '#26a69a' if rsi_v<30 else '#d1d4dc'}">{rsi_v:.1f}</div></div>
      <div class="ii"><div class="il">MACD</div><div class="iv" style="color:{'#26a69a' if macd_h>0 else '#ef5350'}">{'▲Bull' if macd_h>0 else '▼Bear'}</div></div>
      <div class="ii"><div class="il">BB%</div><div class="iv">{bb_w:.1f}%</div></div>
      <div class="ii"><div class="il">ATR</div><div class="iv">{atr_v:.4f}</div></div>
      <div class="ii"><div class="il">VOL</div><div class="iv" style="color:{'#2962ff' if vr>1.3 else '#d1d4dc'}">{vr:.2f}x</div></div>
      <div class="ii"><div class="il">VWAP</div><div class="iv" style="color:{'#26a69a' if cur>vwap_v else '#ef5350'}">{vwap_v:.4f}</div></div>
      <div class="ii"><div class="il">EMA20</div><div class="iv" style="color:{'#26a69a' if cur>e20 else '#ef5350'}">{e20:.4f}</div></div>
      <div class="ii"><div class="il">EMA50</div><div class="iv" style="color:{'#26a69a' if cur>e50 else '#ef5350'}">{e50:.4f}</div></div>
      <div class="ii"><div class="il">EMA200</div><div class="iv" style="color:{'#26a69a' if cur>e200 else '#ef5350'}">{e200:.4f}</div></div>
    </div>

    <!-- Voice -->
    <button id="vbtn" onclick="doVoice()">🔊</button>
    <div id="vpop" class="glass"><span style="color:#2962ff;font-weight:700;">🔊 SAGE Voice</span> <span id="vst" style="color:#6a6e7a;font-size:10px;">Speaking...</span></div>
  </div>

  <!-- Volume Profile -->
  <div id="vps">
    <div style="font-size:7px;color:#2d3748;text-align:center;padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.03);font-weight:700;">VOL</div>
    {vp_html}
  </div>
</div>

<!-- Status bar -->
<div id="sb">
  <span>RSI:<b style="color:{'#ef5350' if rsi_v>70 else '#26a69a' if rsi_v<30 else '#d1d4dc'}">{rsi_v:.1f}</b></span>
  <span style="color:#1a1e2d">|</span><span>MACD:<b style="color:{'#26a69a' if macd_h>0 else '#ef5350'}">{'▲' if macd_h>0 else '▼'}</b></span>
  <span style="color:#1a1e2d">|</span><span>Vol:<b style="color:{'#2962ff' if vr>1.3 else '#9598a1'}">{vr:.2f}x</b></span>
  <span style="color:#1a1e2d">|</span><span>ATR:<b>{atr_v:.4f}</b></span>
  <span style="color:#1a1e2d">|</span><span>VWAP:<b style="color:{'#26a69a' if cur>vwap_v else '#ef5350'}">{vwap_v:.4f}</b></span>
  <span style="color:#1a1e2d">|</span><span>BB:<b>{bb_w:.1f}%</b></span>
  <span style="color:#1a1e2d">|</span><span style="color:{bc};font-weight:800;">{rr} · {qual}</span>
  <span style="margin-left:auto;color:#2d3748;font-size:9px;">Educational only · Not financial advice</span>
</div>
</div>

<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){{
var candles={json.dumps(candles)}, vols={json.dumps(vols)};
var supp={json.dumps(sup)}, ress={json.dumps(res)};
var fib={json.dumps(fib)};
var marks={json.dumps(markers)};
var ob_list={ob_js}, fvg_list={fvg_js};
var voice={voice};
var H={body_h};
var chart,cs,vs;
var layers={{sr:true,fib:true,ema:true,vwap:true,ai:true,pat:true,ob:false,fvg:false,poc:false}};
var srL=[],fibL=[],emaL=[],vwapL=null,aiL=[],pocL=null,obL=[],fvgL=[];
var showInd=false;

function init(){{
  var el=document.getElementById('cd'); if(!el) return;
  var W=el.parentElement.clientWidth-56; if(W<=0) W=window.innerWidth-68;
  chart=LightweightCharts.createChart(el,{{
    width:W,height:H,
    layout:{{background:{{type:'solid',color:'#080b12'}},textColor:'#5a6070',fontSize:11}},
    grid:{{vertLines:{{color:'rgba(255,255,255,0.025)'}},horzLines:{{color:'rgba(255,255,255,0.025)'}}}},
    crosshair:{{mode:LightweightCharts.CrosshairMode.Normal,
      vertLine:{{color:'rgba(255,255,255,0.15)',labelVisible:true}},
      horzLine:{{color:'rgba(255,255,255,0.15)',labelVisible:true}}}},
    rightPriceScale:{{borderColor:'rgba(255,255,255,0.05)',
      scaleMargins:{{top:0.05,bottom:0.22}}}},
    timeScale:{{borderColor:'rgba(255,255,255,0.05)',timeVisible:true,secondsVisible:false,
      rightOffset:6,barSpacing:9,minBarSpacing:0.4}},
    handleScroll:{{mouseWheel:true,pressedMouseMove:true,horzTouchDrag:true,vertTouchDrag:false}},
    handleScale:{{mouseWheel:true,pinch:true,
      axisPressedMouseMove:{{time:true,price:true}}}},
  }});

  cs=chart.addCandlestickSeries({{
    upColor:'#26a69a',downColor:'#ef5350',
    borderUpColor:'#26a69a',borderDownColor:'#ef5350',
    wickUpColor:'rgba(38,166,154,0.7)',wickDownColor:'rgba(239,83,80,0.7)',
  }});
  cs.setData(candles);

  vs=chart.addHistogramSeries({{priceScaleId:'vol',scaleMargins:{{top:0.8,bottom:0}}}});
  chart.priceScale('vol').applyOptions({{scaleMargins:{{top:0.8,bottom:0}}}});
  vs.setData(vols);

  if(marks.length) cs.setMarkers(marks);

  drawAll();
  chart.timeScale().fitContent();

  window.addEventListener('resize',function(){{
    var nw=document.getElementById('cd').parentElement.clientWidth-56;
    chart.applyOptions({{width:nw>0?nw:400,height:H}});
  }});
}}

function rmLines(arr){{
  arr.forEach(function(l){{try{{cs.removePriceLine(l);}}catch(e){{}}}});
  return [];
}}

function drawAll(){{
  drawSR(); drawFib(); drawEMA(); drawVWAP(); drawAI(); drawOB(); drawFVG(); drawPOC();
}}

// ─── Price Action: Support & Resistance ───────────────────────────
function drawSR(){{
  srL=rmLines(srL); if(!layers.sr) return;
  supp.forEach(function(s,i){{
    var l=cs.createPriceLine({{price:s,color:'rgba(38,166,154,'+(i===0?'0.9':'0.6')+')',lineWidth:i===0?2:1,
      lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,
      title:i===0?'Key Sup':'Sup'}});
    srL.push(l);
  }});
  ress.forEach(function(r,i){{
    var l=cs.createPriceLine({{price:r,color:'rgba(239,83,80,'+(i===0?'0.9':'0.6')+')',lineWidth:i===0?2:1,
      lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,
      title:i===0?'Key Res':'Res'}});
    srL.push(l);
  }});
}}

// ─── Elliott Wave / Gann: Fibonacci ───────────────────────────────
function drawFib(){{
  fibL=rmLines(fibL); if(!layers.fib) return;
  var fc={{'0.236':'rgba(121,134,203,0.8)','0.382':'rgba(38,166,154,0.8)',
           '0.500':'rgba(251,191,36,0.8)','0.618':'rgba(239,83,80,0.8)','0.786':'rgba(224,64,251,0.8)'}};
  Object.keys(fib).forEach(function(k){{
    if(!fib[k]) return;
    var l=cs.createPriceLine({{price:fib[k],color:fc[k]||'#aaa',lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'Fib '+k}});
    fibL.push(l);
  }});
}}

// ─── Indicator: EMA lines ─────────────────────────────────────────
function drawEMA(){{
  emaL=rmLines(emaL); if(!layers.ema) return;
  var emas=[
    [{e20:.6f},'rgba(33,150,243,0.7)','EMA20'],
    [{e50:.6f},'rgba(255,152,0,0.7)','EMA50'],
    [{e200:.6f},'rgba(233,30,99,0.7)','EMA200'],
  ];
  emas.forEach(function(x){{
    if(!x[0]) return;
    emaL.push(cs.createPriceLine({{price:x[0],color:x[1],lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:false,title:x[2]}}));
  }});
}}

// ─── Volume: VWAP ─────────────────────────────────────────────────
function drawVWAP(){{
  if(vwapL){{try{{cs.removePriceLine(vwapL);}}catch(e){{}}}} vwapL=null;
  if(!layers.vwap || !{int(bool(vwap_v))}) return;
  vwapL=cs.createPriceLine({{price:{vwap_v or 0},color:'rgba(251,191,36,0.8)',lineWidth:1,
    lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'VWAP'}});
}}

// ─── AI Trade Levels ──────────────────────────────────────────────
function drawAI(){{
  aiL=rmLines(aiL); if(!layers.ai) return;
  var defs=[
    [{entry_v or 0},'rgba(38,166,154,1)','ENTRY',2,LightweightCharts.LineStyle.Solid],
    [{stop_v  or 0},'rgba(239,83,80,1)', 'STOP', 2,LightweightCharts.LineStyle.Solid],
    [{t1_v    or 0},'rgba(41,98,255,0.9)','T1',  1,LightweightCharts.LineStyle.Dashed],
    [{t2_v    or 0},'rgba(156,39,176,0.9)','T2', 1,LightweightCharts.LineStyle.Dashed],
  ];
  defs.forEach(function(d){{
    if(!d[0]) return;
    aiL.push(cs.createPriceLine({{price:d[0],color:d[1],lineWidth:d[3],lineStyle:d[4],axisLabelVisible:true,title:d[2]}}));
  }});
}}

// ─── SMC: Order Block zones ────────────────────────────────────────
function drawOB(){{
  obL=rmLines(obL); if(!layers.ob) return;
  ob_list.forEach(function(ob,i){{
    var isBull=ob.type&&ob.type.indexOf('BULL')>=0;
    var col=isBull?'rgba(38,166,154,0.75)':'rgba(239,83,80,0.75)';
    var top=ob.zone_top||ob.top||0; var bot=ob.zone_bot||ob.bot||0;
    if(top>0) obL.push(cs.createPriceLine({{price:top,color:col,lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:(isBull?'Bull':'Bear')+' OB Top'}}));
    if(bot>0) obL.push(cs.createPriceLine({{price:bot,color:col,lineWidth:1,
      lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:false,title:(isBull?'Bull':'Bear')+' OB Bot'}}));
  }});
  // AI order blocks
  var aiOB=(window.aiData&&window.aiData.smc&&window.aiData.smc.ob_zones)||[];
  aiOB.forEach(function(ob){{
    var isBull=ob.type&&ob.type.indexOf('BULL')>=0;
    var col=isBull?'rgba(38,166,154,0.8)':'rgba(239,83,80,0.8)';
    if(ob.top) obL.push(cs.createPriceLine({{price:ob.top,color:col,lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'OB Top'}}));
    if(ob.bot) obL.push(cs.createPriceLine({{price:ob.bot,color:col,lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:false,title:'OB Bot'}}));
  }});
}}

// ─── SMC: Fair Value Gaps ─────────────────────────────────────────
function drawFVG(){{
  fvgL=rmLines(fvgL); if(!layers.fvg) return;
  fvg_list.forEach(function(fv){{
    var isBull=fv.type&&fv.type.indexOf('BULL')>=0;
    var col=isBull?'rgba(38,166,154,0.6)':'rgba(239,83,80,0.6)';
    if(fv.top) fvgL.push(cs.createPriceLine({{price:fv.top,color:col,lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'FVG '+(isBull?'Bull':'Bear')}}));
    if(fv.bot) fvgL.push(cs.createPriceLine({{price:fv.bot,color:col,lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:false,title:'FVG bot'}}));
  }});
}}

// ─── Volume: Point of Control ─────────────────────────────────────
function drawPOC(){{
  if(pocL){{try{{cs.removePriceLine(pocL);}}catch(e){{}}}} pocL=null;
  if(!layers.poc || !{int(bool(poc_v))}) return;
  pocL=cs.createPriceLine({{price:{poc_v or 0},color:'rgba(41,98,255,0.85)',lineWidth:2,
    lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:'POC'}});
}}

window.tog=function(name){{
  layers[name]=!layers[name];
  var btn=document.getElementById('l-'+name);
  if(btn) btn.classList.toggle('on',layers[name]);
  if(name==='sr')   drawSR();
  else if(name==='fib')  drawFib();
  else if(name==='ema')  drawEMA();
  else if(name==='vwap') drawVWAP();
  else if(name==='ai')   drawAI();
  else if(name==='poc')  drawPOC();
  else if(name==='ob')   drawOB();
  else if(name==='fvg')  drawFVG();
  else if(name==='pat'){{
    if(cs){{ if(layers.pat) cs.setMarkers(marks); else cs.setMarkers([]); }}
  }}
}};

window.setStyle=function(st){{
  ['b-c','b-a','b-h'].forEach(function(id){{var b=document.getElementById(id);if(b)b.classList.remove('on');}});
  document.getElementById(st==='candle'?'b-c':st==='area'?'b-a':'b-h').classList.add('on');
  chart.removeSeries(cs);
  if(st==='candle'){{
    cs=chart.addCandlestickSeries({{upColor:'#26a69a',downColor:'#ef5350',borderUpColor:'#26a69a',borderDownColor:'#ef5350',wickUpColor:'rgba(38,166,154,0.7)',wickDownColor:'rgba(239,83,80,0.7)'}});
    cs.setData(candles);
    if(marks.length&&layers.pat) cs.setMarkers(marks);
  }} else if(st==='area'){{
    cs=chart.addAreaSeries({{topColor:'rgba(41,98,255,0.28)',bottomColor:'rgba(41,98,255,0.02)',lineColor:'#2962ff',lineWidth:2}});
    cs.setData(candles.map(function(c){{return{{time:c.time,value:c.close}};}}));
  }} else {{
    // Heikin Ashi
    cs=chart.addCandlestickSeries({{upColor:'#26a69a',downColor:'#ef5350',borderUpColor:'#26a69a',borderDownColor:'#ef5350'}});
    var ha=[], prev=null;
    candles.forEach(function(c){{
      var haC=(c.open+c.high+c.low+c.close)/4;
      var haO=prev?((prev.open+prev.close)/2):((c.open+c.close)/2);
      var haH=Math.max(c.high,haO,haC); var haL=Math.min(c.low,haO,haC);
      prev={{open:haO,close:haC}}; ha.push({{time:c.time,open:haO,high:haH,low:haL,close:haC}});
    }});
    cs.setData(ha);
  }}
  drawAll();
}};

window.fitC=function(){{if(chart) chart.timeScale().fitContent();}};
window.togInd=function(){{
  showInd=!showInd;
  var el=document.getElementById('g-ind'); if(el) el.classList.toggle('vis',showInd);
  var btn=document.getElementById('b-ind'); if(btn) btn.classList.toggle('on',showInd);
}};
window.doVoice=function(){{
  var vp2=document.getElementById('vpop'),vst=document.getElementById('vst');
  if(!vp2) return;
  if(!vp2.classList.contains('vis')){{
    vp2.classList.add('vis');
    if('speechSynthesis' in window){{
      window.speechSynthesis.cancel();
      var u=new SpeechSynthesisUtterance(voice||'Analysis ready');
      u.lang='hi-IN'; u.rate=0.88; u.pitch=1.05;
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
    vp2.classList.remove('vis'); if('speechSynthesis' in window) window.speechSynthesis.cancel();
  }}
}};

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
}})();
</script></body></html>"""


# ════════════════════════════════════════════════════════════════════════
# FULL WHITE PAPER REPORT — All 6 trader types on white paper, black text
# ════════════════════════════════════════════════════════════════════════
def _full_report_html(sym, name, tech, fund, ai):
    rat=ai.get("rating","HOLD"); rc=ai.get("rating_color","#555")
    bias=ai.get("bias","NEUTRAL"); bc=ai.get("bias_color","#555")
    conf=ai.get("confidence",60); pt=ai.get("price_target",0)
    p=tech.get("price",0); up_pct=round((pt-p)/p*100,1) if p and pt else 0
    api_u=ai.get("_api","AI"); rr=ai.get("rr","—")
    entry_v=ai.get("entry",0); stop_v=ai.get("stop",0); t1_v=ai.get("t1",0); t2_v=ai.get("t2",0)
    pa=ai.get("price_action",{}); smc=ai.get("smc",{})
    quant=ai.get("quant",{}); ind=ai.get("indicator",{})
    vol=ai.get("volume",{}); wave=ai.get("wave",{})
    kl=ai.get("key_levels",{}); fib=tech.get("fib",{})
    pats=tech.get("patterns",[]); sup=tech.get("supports",[]); res=tech.get("resistances",[])
    rsi_v=tech.get("rsi",50); macd_h=tech.get("macd_h",0); vr=tech.get("vol_ratio",1)
    e20=tech.get("ema20",0); e50=tech.get("ema50",0); e200=tech.get("ema200",0)
    h52=fund.get("h52",0); l52=fund.get("l52",0)
    pfx=fund.get("pfx","$"); perf1m=tech.get("perf1m",0); perf3m=tech.get("perf3m",0)

    thesis_rows="".join([f'<div class="tr-row"><span class="tr-bull">+</span>{t}</div>' for t in ai.get("thesis",[])])
    risk_rows="".join([f'<div class="tr-row"><span class="tr-bear">−</span>{r}</div>' for r in ai.get("risks",[])])
    def _pat_row(p2):
        typ=p2.get("type",""); col="#1b5e20" if "BULL" in typ else "#b71c1c" if "BEAR" in typ else "#555"
        sig="▲ BULLISH" if "BULL" in typ else "▼ BEARISH" if "BEAR" in typ else "→ NEUTRAL"
        return f'<tr><td style="font-weight:700;">{p2.get("name","")}</td><td style="color:{col};">{sig}</td><td>{p2.get("desc","")[:80]}</td><td style="font-weight:700;">{p2.get("action","Monitor")}</td></tr>'
    pat_rows="".join([_pat_row(p2) for p2 in ai.get("patterns_detail",pats[:5])])

    def _sr_row(sr):
        typ=sr.get("type","support"); col="#1b5e20" if typ=="support" else "#b71c1c"
        lab="SUPPORT" if typ=="support" else "RESISTANCE"
        return f'<tr><td style="font-family:monospace;">{sr.get("level",0):.4f}</td><td style="color:{col};font-weight:700;">{lab}</td><td style="font-weight:700;">{sr.get("strength","medium").upper()}</td><td>{sr.get("significance","Key level")}</td></tr>'
    sr_rows="".join([_sr_row(sr) for sr in ai.get("sr_analysis",[])])

    def _fib_row(k,v):
        fc={"0.236":"#7986cb","0.382":"#1b5e20","0.500":"#e65100","0.618":"#b71c1c"}.get(k,"#6a1b9a")
        vc="#1b5e20" if v<p else "#b71c1c"; pos="Below" if v<p else "Above"
        dist=round((v-p)/p*100,2) if p else 0
        return f'<tr><td style="font-weight:700;color:{fc};">Fib {k}</td><td style="font-family:monospace;font-weight:700;">{v:.4f}</td><td style="color:{vc};">{pos} Current</td><td>{dist:+.2f}%</td></tr>'
    fib_rows="".join([_fib_row(k,v) for k,v in fib.items()])

    # Real quant + fundamental block for white paper
    _rq = ai.get("real_quant", {})
    _rfh = ai.get("real_fund_health", {})
    if _rq.get("ok"):
        _qv = _rq.get("volatility",{}); _qt = _rq.get("trend",{}); _qb = _rq.get("beta")
        _pu = _qt.get("prob_up_5d","—") if _qt.get("ok") else "—"
        _pd = _qt.get("prob_down_5d","—") if _qt.get("ok") else "—"
        _av = _qv.get("annualized_volatility_pct","—"); _rv = _qv.get("recent_20d_volatility_pct","—")
        _ta = _qt.get("train_accuracy_pct","—") if _qt.get("ok") else "—"
        _pc = "#1b5e20" if isinstance(_pu,(int,float)) and _pu>=55 else "#b71c1c"
        _pu_sig = "BULLISH" if isinstance(_pu,(int,float)) and _pu>=55 else "BEARISH" if isinstance(_pu,(int,float)) and _pu<=45 else "NEUTRAL"
        _ud_quant_block = (
            "<h2>Quantitative Engine — Real Math Analysis</h2>"
            "<p style='font-size:14px;'>Logistic Regression model trained on " + str(_qt.get('rows_used','N/A') if _qt.get('ok') else 'N/A') + " historical data points. "
            "Statistical pattern frequency — not a prediction guarantee.</p>"
            "<table><thead><tr><th>Metric</th><th>Value</th><th>Signal</th><th>Notes</th></tr></thead><tbody>"
            "<tr><td><b>5-Day Up Probability</b></td><td style='font-family:monospace;font-weight:700;color:" + _pc + ";'>" + str(_pu) + "%</td><td style='color:" + _pc + ";font-weight:700;'>" + _pu_sig + "</td><td>ML model probability</td></tr>"
            "<tr><td><b>5-Day Down Probability</b></td><td style='font-family:monospace;font-weight:700;'>" + str(_pd) + "%</td><td>—</td><td>Inverse of above</td></tr>"
            "<tr><td><b>Annualised Volatility</b></td><td style='font-family:monospace;'>" + str(_av) + "%</td><td>—</td><td>Historical vol (252d)</td></tr>"
            "<tr><td><b>20-Day Volatility</b></td><td style='font-family:monospace;'>" + str(_rv) + "%</td><td>—</td><td>Recent vol regime</td></tr>"
            "<tr><td><b>Beta vs Index</b></td><td style='font-family:monospace;'>" + str(_qb if _qb else '—') + "</td><td>—</td><td>Correlation to benchmark</td></tr>"
            "<tr><td><b>Model Train Accuracy</b></td><td style='font-family:monospace;'>" + str(_ta) + "%</td><td>—</td><td>In-sample accuracy</td></tr>"
            "</tbody></table>"
        )
    else:
        _ud_quant_block = ""
    if _rfh.get("ok"):
        _fhs = _rfh.get("score",{}); _hs = _fhs.get("health_score",0); _verd = _fhs.get("verdict","—")
        _fbd = _fhs.get("breakdown",{}); _hsc = "#1b5e20" if _hs>=75 else "#e65100" if _hs>=50 else "#b71c1c"
        _bdr = "".join(["<tr><td style='font-weight:700;'>" + k + "</td><td style='font-family:monospace;font-weight:700;'>" + str(v) + "/100</td></tr>" for k,v in _fbd.items()])
        _fh_block = (
            "<h2>Fundamental Health Score</h2>"
            "<div style='display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap;'>"
            "<div style='text-align:center;border:1px solid #ccc;border-radius:8px;padding:16px 24px;'>"
            "<div style='font-size:11px;font-family:Arial;text-transform:uppercase;letter-spacing:.08em;'>Health Score</div>"
            "<div style='font-size:48px;font-weight:900;font-family:monospace;color:" + _hsc + ";'>" + str(_hs) + "</div>"
            "<div style='font-size:13px;font-weight:700;color:" + _hsc + ";'>" + _verd + "</div></div>"
            "<table style='flex:1;min-width:220px;'><thead><tr><th>Category</th><th>Score</th></tr></thead>"
            "<tbody>" + _bdr + "</tbody></table></div>"
        )
        _ud_quant_block = _fh_block + _ud_quant_block

        return f"""
<style>
.wp{{background:#ffffff;color:#1a1a1a;font-family:Georgia,'Times New Roman',serif;
  border:1px solid #ccc;border-radius:4px;padding:40px 44px;line-height:1.8;}}
.wp *{{color:#1a1a1a!important;background:transparent!important;}}
.wp-stripe{{height:6px;background:linear-gradient(90deg,#1a237e,#0d47a1,#006064,#1b5e20,#b71c1c,#4a148c);margin-bottom:24px;border-radius:3px;}}
.wp h1{{font-size:28px;font-weight:900;margin-bottom:6px;letter-spacing:.02em;}}
.wp h2{{font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:.14em;
  border-bottom:2.5px solid #1a1a1a;padding-bottom:6px;margin:24px 0 12px;font-family:Arial,sans-serif;}}
.wp h3{{font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.1em;
  color:#444!important;margin:12px 0 6px;font-family:Arial,sans-serif;border-left:4px solid #1a1a1a;padding-left:8px;}}
.wp p{{font-size:14px;line-height:1.8;margin-bottom:8px;}}
.wp table{{width:100%;border-collapse:collapse;font-size:13px;margin:10px 0;}}
.wp table th{{background:#1a1a1a!important;color:#ffffff!important;padding:8px 10px;
  text-align:left;font-family:Arial,sans-serif;font-size:11px;text-transform:uppercase;letter-spacing:.06em;}}
.wp table td{{padding:7px 10px;border-bottom:1px solid #e0e0e0;vertical-align:top;}}
.wp table tr:nth-child(even) td{{background:#f8f8f8!important;}}
.wp .g9{{display:grid;grid-template-columns:repeat(9,1fr);gap:8px;margin:12px 0;}}
.wp .g3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin:12px 0;}}
.wp .g2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:12px 0;}}
.wp .cell{{border:1px solid #ccc;border-radius:4px;padding:10px;text-align:center;}}
.wp .cl{{font-size:10px;text-transform:uppercase;letter-spacing:.06em;font-family:Arial;color:#555!important;margin-bottom:4px;}}
.wp .cv{{font-size:17px;font-weight:900;font-family:'Courier New',monospace;}}
.wp .badge{{display:inline-block;border:2.5px solid #1a1a1a;border-radius:4px;padding:5px 16px;font-size:15px;font-weight:900;margin-right:10px;font-family:Arial;}}
.wp .trader-box{{border:1.5px solid #ddd;border-radius:6px;padding:14px 16px;margin:10px 0;}}
.wp .trader-title{{font-size:13px;font-weight:900;font-family:Arial;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;display:flex;align-items:center;gap:8px;}}
.wp .trader-body{{font-size:13.5px;line-height:1.8;}}
.wp .signal-box{{display:inline-block;border:2px solid;border-radius:4px;padding:3px 12px;font-weight:900;font-size:12px;font-family:Arial;margin-top:6px;}}
.wp .row{{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #eee;font-size:14px;}}
.wp .rl{{font-weight:700;font-family:Arial;color:#333!important;}}
.wp .rv{{font-family:'Courier New',monospace;font-weight:700;font-size:13px;}}
.wp .tr-row{{padding:5px 0 5px 18px;border-bottom:1px solid #eee;font-size:13.5px;position:relative;}}
.wp .tr-bull{{position:absolute;left:2px;color:#1b5e20!important;font-weight:900;font-size:16px;}}
.wp .tr-bear{{position:absolute;left:2px;color:#b71c1c!important;font-weight:900;font-size:16px;}}
.wp .disc{{font-size:11px;color:#666!important;border-top:1px solid #ccc;margin-top:24px;padding-top:12px;font-family:Arial;line-height:1.6;}}
</style>
<div class="wp">
<div class="wp-stripe"></div>

<!-- COVER -->
<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;margin-bottom:22px;">
  <div>
    <h1>{name}</h1>
    <div style="font-size:14px;color:#555!important;margin-bottom:10px;">{sym} · {fund.get('exchange','—')} · {fund.get('sector','—')} · {fund.get('country','—')}</div>
    <div><span class="badge">{rat}</span><span class="badge" style="font-size:13px;">{bias}</span></div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:34px;font-weight:900;font-family:'Courier New',monospace;">{p:.4f}</div>
    <div style="font-size:14px;">{fund.get('currency','')} · {fund.get('mktcap_str','—')}</div>
    <div style="font-size:14px;margin-top:4px;">Target: <b>{pt:.2f}</b> &nbsp;|&nbsp; Upside: <b style="color:{'#1b5e20' if up_pct>0 else '#b71c1c'}!important;">{up_pct:+.1f}%</b></div>
    <div style="font-size:13px;">Confidence: <b>{conf}%</b> &nbsp;|&nbsp; via {api_u}</div>
    <div style="font-size:12px;color:#555!important;margin-top:3px;">{datetime.now().strftime('%B %d, %Y · %H:%M IST')}</div>
  </div>
</div>

<h2>Executive Summary</h2>
<p>{ai.get('summary','')}</p>

<h2>Key Metrics</h2>
<div class="g9">
  <div class="cell"><div class="cl">P/E</div><div class="cv">{fund.get('pe') or '—'}</div></div>
  <div class="cell"><div class="cl">P/B</div><div class="cv">{fund.get('pb') or '—'}</div></div>
  <div class="cell"><div class="cl">RSI 14</div><div class="cv">{rsi_v:.0f}</div></div>
  <div class="cell"><div class="cl">ATR</div><div class="cv" style="font-size:13px;">{tech.get('atr',0):.4f}</div></div>
  <div class="cell"><div class="cl">Vol Ratio</div><div class="cv">{vr:.2f}x</div></div>
  <div class="cell"><div class="cl">MACD</div><div class="cv" style="font-size:14px;">{'▲' if macd_h>0 else '▼'}</div></div>
  <div class="cell"><div class="cl">1M Perf</div><div class="cv" style="font-size:14px;color:{'#1b5e20' if perf1m>0 else '#b71c1c'}!important;">{perf1m:+.1f}%</div></div>
  <div class="cell"><div class="cl">Beta</div><div class="cv">{fund.get('beta') or '—'}</div></div>
  <div class="cell"><div class="cl">R:R</div><div class="cv">{rr}</div></div>
</div>

<h2>Trade Setup</h2>
<div class="g3">
  <div>
    <div class="row"><span class="rl" style="color:#1b5e20!important;">● Entry</span><span class="rv">{entry_v:.4f}</span></div>
    <div class="row"><span class="rl" style="color:#b71c1c!important;">● Stop Loss</span><span class="rv">{stop_v:.4f}</span></div>
    <div class="row"><span class="rl">● Target 1</span><span class="rv">{t1_v:.4f}</span></div>
    <div class="row"><span class="rl">● Target 2</span><span class="rv">{t2_v:.4f}</span></div>
    <div class="row"><span class="rl">R:R Ratio</span><span class="rv" style="font-size:16px;font-weight:900;">{rr}</span></div>
  </div>
  <div>
    <div style="font-size:12px;font-weight:900;font-family:Arial;color:#1b5e20!important;margin-bottom:6px;">BULL THESIS</div>
    {thesis_rows}
  </div>
  <div>
    <div style="font-size:12px;font-weight:900;font-family:Arial;color:#b71c1c!important;margin-bottom:6px;">RISK FACTORS</div>
    {risk_rows}
  </div>
</div>

<!-- ════════ 6 TRADER TYPE ANALYSIS ════════ -->
<h2>Multi-Style Analysis — All 6 Trader Perspectives</h2>

<!-- 1. PRICE ACTION -->
<div class="trader-box" style="border-color:#1a237e;">
  <div class="trader-title" style="color:#1a237e!important;">📊 1. Price Action Trader View
    <span style="background:#1a237e!important;color:#fff!important;font-size:10px;padding:2px 8px;border-radius:12px;font-weight:700;">CLEAN CHART · NO NOISE</span>
  </div>
  <div class="trader-body">{pa.get('view','')}</div>
  <div class="g2" style="margin-top:10px;">
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#1a237e!important;margin-bottom:4px;">Chart Pattern</div>
      <div style="font-size:14px;font-weight:700;">{pa.get('pattern_detected','—')}</div>
      <div style="font-size:12px;color:#444!important;">{pa.get('pattern_desc','')}</div>
    </div>
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#1a237e!important;margin-bottom:4px;">PA Signal</div>
      <span class="signal-box" style="border-color:#1a237e;color:#1a237e!important;">{pa.get('signal','WAIT')}</span>
      <div style="font-size:12px;color:#444!important;margin-top:4px;">{pa.get('signal_reason','')}</div>
    </div>
  </div>
</div>

<!-- 2. SMC / ICT -->
<div class="trader-box" style="border-color:#b71c1c;">
  <div class="trader-title" style="color:#b71c1c!important;">🏦 2. Smart Money Concept (SMC/ICT) View
    <span style="background:#b71c1c!important;color:#fff!important;font-size:10px;padding:2px 8px;border-radius:12px;font-weight:700;">ORDER BLOCKS · LIQUIDITY · FVG</span>
  </div>
  <div class="trader-body">{smc.get('view','')}</div>
  <div class="g3" style="margin-top:10px;">
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#b71c1c!important;margin-bottom:4px;">Market Structure</div>
      <div style="font-size:14px;font-weight:700;">{smc.get('market_structure','—')}</div>
    </div>
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#b71c1c!important;margin-bottom:4px;">PD Zone</div>
      <div style="font-size:14px;font-weight:700;">{smc.get('pd_zone','—')}</div>
    </div>
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#b71c1c!important;margin-bottom:4px;">SMC Signal</div>
      <span class="signal-box" style="border-color:#b71c1c;color:#b71c1c!important;">{smc.get('signal','WAIT')}</span>
      <div style="font-size:12px;color:#444!important;margin-top:4px;">{smc.get('signal_reason','')[:60]}</div>
    </div>
  </div>
  {'<div style="margin-top:8px;"><div style="font-size:11px;font-weight:700;font-family:Arial;margin-bottom:4px;">Order Block Zones:</div>' + "".join([f'<div style="font-size:12px;padding:3px 0;border-bottom:1px solid #eee;">{"🟢 Bull" if "BULL" in ob.get("type","") else "🔴 Bear"} OB — {ob.get("bot",0):.4f}–{ob.get("top",0):.4f} ({ob.get("quality","—")})</div>' for ob in smc.get("ob_zones",[])[:3]]) + '</div>' if smc.get("ob_zones") else ''}
</div>

<!-- 3. QUANT -->
<div class="trader-box" style="border-color:#1b5e20;">
  <div class="trader-title" style="color:#1b5e20!important;">🤖 3. Quant / Algo Trader View
    <span style="background:#1b5e20!important;color:#fff!important;font-size:10px;padding:2px 8px;border-radius:12px;font-weight:700;">PROBABILITY · STATISTICS · EDGE</span>
  </div>
  <div class="trader-body">{quant.get('view','')}</div>
  <div class="g3" style="margin-top:10px;">
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#1b5e20!important;margin-bottom:4px;">Win Rate</div>
      <div style="font-size:22px;font-weight:900;font-family:'Courier New';">{quant.get('win_rate','—')}</div>
    </div>
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#1b5e20!important;margin-bottom:4px;">Expected Value</div>
      <div style="font-size:22px;font-weight:900;font-family:'Courier New';">{quant.get('expected_value','—')}</div>
    </div>
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#1b5e20!important;margin-bottom:4px;">Setup Grade</div>
      <div style="font-size:22px;font-weight:900;font-family:'Courier New';">{quant.get('setup_quality','B')}</div>
      <div style="font-size:12px;color:#444!important;">{quant.get('statistical_edge','')[:60]}</div>
    </div>
  </div>
</div>

<!-- 4. INDICATOR -->
<div class="trader-box" style="border-color:#e65100;">
  <div class="trader-title" style="color:#e65100!important;">📈 4. Technical / Indicator Trader View
    <span style="background:#e65100!important;color:#fff!important;font-size:10px;padding:2px 8px;border-radius:12px;font-weight:700;">RSI · MACD · BB · EMA · VWAP</span>
  </div>
  <div class="trader-body">{ind.get('view','')}</div>
  <table style="margin-top:10px;">
    <tr><th>Indicator</th><th>Reading</th><th>Signal</th></tr>
    <tr><td style="font-weight:700;">RSI 14</td><td>{ind.get('rsi_read','')}</td><td style="color:{'#1b5e20' if rsi_v<50 else '#b71c1c'}!important;font-weight:700;">{'▲ BULLISH' if rsi_v<50 else '▼ BEARISH'}</td></tr>
    <tr><td style="font-weight:700;">MACD</td><td>{ind.get('macd_read','')}</td><td style="color:{'#1b5e20' if macd_h>0 else '#b71c1c'}!important;font-weight:700;">{'▲ BULLISH' if macd_h>0 else '▼ BEARISH'}</td></tr>
    <tr><td style="font-weight:700;">Bollinger Bands</td><td>{ind.get('bb_read','')}</td><td>→ MONITOR</td></tr>
    <tr><td style="font-weight:700;">EMA Structure</td><td>{ind.get('ema_structure','')}</td><td style="font-weight:700;">{ind.get('overall_signal','—')}</td></tr>
    <tr><td style="font-weight:700;">VWAP</td><td>{ind.get('vwap_read','')}</td><td style="color:{'#1b5e20' if tech.get('price',0)>tech.get('vwap',0) else '#b71c1c'}!important;font-weight:700;">{'▲ ABOVE' if tech.get('price',0)>tech.get('vwap',0) else '▼ BELOW'}</td></tr>
  </table>
  <div style="background:#f9f9f9!important;border:1px solid #ddd;border-radius:4px;padding:10px;margin-top:8px;font-size:13px;">
  <b>Overall Signal Strength: {ind.get('signal_strength','MODERATE')}</b></div>
</div>

<!-- 5. VOLUME / ORDER FLOW -->
<div class="trader-box" style="border-color:#4a148c;">
  <div class="trader-title" style="color:#4a148c!important;">📦 5. Volume Profile / Order Flow Trader View
    <span style="background:#4a148c!important;color:#fff!important;font-size:10px;padding:2px 8px;border-radius:12px;font-weight:700;">POC · HVN · LVN · DELTA · VWAP</span>
  </div>
  <div class="trader-body">{vol.get('view','')}</div>
  <div class="g3" style="margin-top:10px;">
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#4a148c!important;margin-bottom:4px;">POC Level</div>
      <div style="font-size:18px;font-weight:900;font-family:'Courier New';">{vol.get('poc_level',tech.get('vwap',0)):.4f}</div>
      <div style="font-size:12px;color:#444!important;">{vol.get('poc_significance','')[:60]}</div>
    </div>
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#4a148c!important;margin-bottom:4px;">Volume Delta</div>
      <div style="font-size:14px;font-weight:700;">{vol.get('volume_delta','—')}</div>
      <div style="font-size:12px;color:#444!important;margin-top:3px;">HVN: {vol.get('hvn_zones','—')[:40]}</div>
      <div style="font-size:12px;color:#444!important;">LVN: {vol.get('lvn_zones','—')[:40]}</div>
    </div>
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#4a148c!important;margin-bottom:4px;">Money Flow</div>
      <div style="font-size:14px;font-weight:700;">{vol.get('money_flow','—')}</div>
      <div style="font-size:12px;color:#444!important;margin-top:3px;">Vol: <b>{vr:.2f}x</b> average<br>{vol.get('vwap_analysis','')[:50]}</div>
    </div>
  </div>
</div>

<!-- 6. ELLIOTT WAVE / GANN -->
<div class="trader-box" style="border-color:#006064;">
  <div class="trader-title" style="color:#006064!important;">🌊 6. Elliott Wave / Gann Trader View
    <span style="background:#006064!important;color:#fff!important;font-size:10px;padding:2px 8px;border-radius:12px;font-weight:700;">WAVE COUNT · FIBONACCI · CYCLE</span>
  </div>
  <div class="trader-body">{wave.get('view','')}</div>
  <div class="g3" style="margin-top:10px;">
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#006064!important;margin-bottom:4px;">Wave Count</div>
      <div style="font-size:14px;font-weight:700;">{wave.get('wave_count','—')}</div>
      <div style="font-size:12px;color:#444!important;margin-top:3px;">{wave.get('cycle_phase','—')}</div>
    </div>
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#006064!important;margin-bottom:4px;">Next Move Target</div>
      <div style="font-size:14px;font-weight:700;">{wave.get('next_move','—')}</div>
      <div style="font-size:12px;color:#444!important;margin-top:3px;">{wave.get('wave_target','')[:60]}</div>
    </div>
    <div>
      <div style="font-size:11px;font-weight:700;font-family:Arial;color:#006064!important;margin-bottom:4px;">Fibonacci Targets</div>
      {''.join([f'<div style="font-size:12px;padding:2px 0;"><b>Fib {k}:</b> <span style="font-family:monospace;">{v:.4f}</span></div>' for k,v in (wave.get('fib_key_levels') or fib).items()][:4])}
    </div>
  </div>
</div>

<!-- SUPPORT / RESISTANCE TABLE -->
<h2>Support & Resistance Levels</h2>
{'<table><tr><th>Level</th><th>Type</th><th>Strength</th><th>Significance</th></tr>' + sr_rows + '</table>' if sr_rows else f'<div style="font-size:13px;">Supports: {sup[:4]} | Resistances: {res[:4]}</div>'}

<!-- FIBONACCI TABLE -->
<h2>Fibonacci Retracement Levels</h2>
<table><tr><th>Level</th><th>Price</th><th>Position vs Current</th><th>Distance</th></tr>{fib_rows}</table>

<!-- CANDLESTICK PATTERNS -->
<h2>Candlestick & Chart Patterns Detected</h2>
{'<table><tr><th>Pattern</th><th>Signal</th><th>Description</th><th>Action</th></tr>' + pat_rows + '</table>' if pat_rows else '<p>No clear patterns detected — clean chart.</p>'}

<!-- MULTI-TIMEFRAME -->
<h2>Multi-Timeframe Analysis</h2>
<table>
  <tr><th>Timeframe</th><th>Analysis</th></tr>
  {''.join([f"<tr><td style='font-weight:700;text-transform:uppercase;'>{k}</td><td>{v}</td></tr>" for k,v in ai.get('multi_tf',{}).items()])}
</table>

<!-- FUNDAMENTAL SNAPSHOT -->
<h2>Fundamental Snapshot</h2>
<div class="g3">
  <div>
    <div class="row"><span class="rl">Sector</span><span class="rv">{fund.get('sector','—')}</span></div>
    <div class="row"><span class="rl">Market Cap</span><span class="rv">{fund.get('mktcap_str','—')}</span></div>
    <div class="row"><span class="rl">P/E Ratio</span><span class="rv">{fund.get('pe') or '—'}</span></div>
    <div class="row"><span class="rl">P/B Ratio</span><span class="rv">{fund.get('pb') or '—'}</span></div>
    <div class="row"><span class="rl">EPS TTM</span><span class="rv">{fund.get('eps') or '—'}</span></div>
  </div>
  <div>
    <div class="row"><span class="rl">Revenue</span><span class="rv">{pfx}{fund.get('revenue',0)/1e9:.2f}B</span></div>
    <div class="row"><span class="rl">Net Margin</span><span class="rv">{round((fund.get('profit_m') or 0)*100,1)}%</span></div>
    <div class="row"><span class="rl">ROE</span><span class="rv">{round((fund.get('roe') or 0)*100,1)}%</span></div>
    <div class="row"><span class="rl">D/E Ratio</span><span class="rv">{fund.get('de') or '—'}</span></div>
    <div class="row"><span class="rl">Beta</span><span class="rv">{fund.get('beta') or '—'}</span></div>
  </div>
  <div>
    <div class="row"><span class="rl">Analyst Rating</span><span class="rv">{str(fund.get('analyst','—')).upper()}</span></div>
    <div class="row"><span class="rl">Target Price</span><span class="rv">{fund.get('target_mean') or '—'}</span></div>
    <div class="row"><span class="rl">Dividend Yield</span><span class="rv">{round((fund.get('div_y') or 0)*100,2)}%</span></div>
    <div class="row"><span class="rl">52W High</span><span class="rv">{fund.get('h52',0):.2f}</span></div>
    <div class="row"><span class="rl">52W Low</span><span class="rv">{fund.get('l52',0):.2f}</span></div>
  </div>
</div>

<!-- CATALYST & MACRO -->
<h2>Catalyst & Macro</h2>
<div class="g2">
  <div><div style="font-size:12px;font-weight:700;font-family:Arial;margin-bottom:6px;">KEY CATALYST</div><p>{ai.get('catalyst','—')}</p></div>
  <div><div style="font-size:12px;font-weight:700;font-family:Arial;margin-bottom:6px;">MACRO FACTORS</div><p>{ai.get('macro','—')}</p></div>
</div>

<div class="disc">
<b>DISCLAIMER:</b> This report is prepared by FinSage AI for educational and informational purposes only.
It does NOT constitute financial advice, investment recommendation, or solicitation to buy/sell any security.
Data from Yahoo Finance. AI analysis via {api_u} on {datetime.now().strftime('%B %d, %Y')}.
Past performance does not guarantee future results. Consult a SEBI/SEC-registered advisor before trading.
FinSage AI · Personal Dashboard · For educational use only.
</div>
</div>"""


# ════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ════════════════════════════════════════════════════════════════════════


def _render_inbuilt_chart(sym, name, tech, df, tf="1D", period="3mo"):
    """
    FinSage Inbuilt Pro Chart — 3D candlestick, indicators, fullscreen, drawing tools.
    Uses Lightweight Charts v4 (self-hosted CDN) — no TradingView dependency.
    """
    import json as _json

    # Build OHLCV data
    candle_data, vol_data = [], []
    if df is not None and not df.empty:
        for idx, row in df.tail(300).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            o  = round(float(row["Open"]),  4)
            h  = round(float(row["High"]),  4)
            l  = round(float(row["Low"]),   4)
            c  = round(float(row["Close"]), 4)
            v  = int(row["Volume"])
            candle_data.append({"time":ts,"open":o,"high":h,"low":l,"close":c})
            vol_data.append({"time":ts,"value":v,
                "color":"rgba(38,166,154,0.55)" if c>=o else "rgba(239,83,80,0.55)"})

    # S/R levels
    sup = tech.get("supports",   [])
    res = tech.get("resistances",[])
    fib = tech.get("fib", {})

    # Key levels from tech
    vwap_p  = tech.get("vwap", 0)
    ema20_p = tech.get("ema20",0)
    ema50_p = tech.get("ema50",0)
    ema200_p= tech.get("ema200",0) or tech.get("ema_200",0)
    cur_p   = tech.get("price",  candle_data[-1]["close"] if candle_data else 0)
    rsi_v   = tech.get("rsi",   50)
    trend   = tech.get("trend", "NEUTRAL")
    tc      = "#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"
    atr_v   = tech.get("atr",   0)
    vol_r   = tech.get("vol_ratio",1)

    cj  = _json.dumps(candle_data)
    vj  = _json.dumps(vol_data)
    sj  = _json.dumps(sup[:4])
    rj  = _json.dumps(res[:4])
    fj  = _json.dumps(fib)
    CHT = 660

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
html,body{background:#060b14;font-family:'Inter',-apple-system,sans-serif;color:#d1d4dc;width:100%;height:__CHT__px;overflow:hidden;}
#root{display:flex;flex-direction:column;width:100%;height:__CHT__px;position:relative;}

/* TOOLBAR */
#toolbar{
  display:flex;align-items:center;gap:7px;padding:0 12px;height:42px;min-height:42px;flex-shrink:0;
  background:linear-gradient(180deg,#0e1520 0%,#0a1018 100%);
  border-bottom:1px solid rgba(255,255,255,0.06);
  overflow-x:auto;
}
#toolbar::-webkit-scrollbar{display:none;}
.brand{font-weight:800;font-size:13px;color:#d1d4dc;flex-shrink:0;letter-spacing:.2px;}
.brand b{color:#3d8eff;}
.sym-lbl{font-family:monospace;font-size:13px;font-weight:700;color:#e2e8f2;background:rgba(255,255,255,0.06);padding:4px 10px;border-radius:6px;flex-shrink:0;}
.price-disp{font-family:monospace;font-size:14px;font-weight:800;flex-shrink:0;}
.tf-row{display:flex;gap:2px;background:rgba(255,255,255,0.04);padding:2px;border-radius:7px;flex-shrink:0;}
.tf-b{font-family:monospace;font-size:10.5px;padding:4px 8px;border-radius:5px;color:#6a7585;cursor:pointer;transition:.12s;white-space:nowrap;}
.tf-b:hover{color:#e2e8f2;}
.tf-b.on{background:#3d8eff;color:#fff;font-weight:700;}
.ct-row{display:flex;gap:2px;background:rgba(255,255,255,0.04);padding:2px;border-radius:7px;flex-shrink:0;}
.ct-b{font-family:monospace;font-size:10px;padding:3px 7px;border-radius:5px;color:#6a7585;cursor:pointer;transition:.12s;white-space:nowrap;}
.ct-b:hover{color:#e2e8f2;}
.ct-b.on{background:rgba(61,142,255,.22);color:#3d8eff;font-weight:700;}
.sp{flex:1;}
.icon-b{width:30px;height:30px;border-radius:7px;display:flex;align-items:center;justify-content:center;cursor:pointer;color:#6a7585;border:1px solid transparent;transition:.12s;flex-shrink:0;}
.icon-b:hover{background:rgba(255,255,255,0.07);color:#e2e8f2;border-color:rgba(255,255,255,0.1);}
.icon-b.on{background:rgba(61,142,255,.15);color:#3d8eff;border-color:rgba(61,142,255,.3);}
.ind-tog{font-family:monospace;font-size:10px;padding:4px 9px;border-radius:6px;cursor:pointer;background:rgba(255,255,255,0.05);color:#6a7585;border:1px solid rgba(255,255,255,0.07);transition:.12s;white-space:nowrap;}
.ind-tog:hover{color:#e2e8f2;border-color:rgba(255,255,255,0.15);}
.ind-tog.on{background:rgba(61,142,255,.15);color:#3d8eff;border-color:rgba(61,142,255,.35);}

/* CHART AREA */
#chart-area{flex:1;position:relative;min-height:0;}
#chart-div{width:100%;height:100%;}

/* CROSSHAIR READOUT */
#ohlcv-bar{
  position:absolute;top:7px;left:8px;z-index:20;
  font-family:monospace;font-size:11px;line-height:1.6;
  background:rgba(6,11,20,.82);padding:6px 10px;border-radius:8px;
  border:1px solid rgba(255,255,255,0.07);backdrop-filter:blur(8px);
  pointer-events:none;min-width:280px;
}
#ohlcv-bar span{color:#6a7585;}
#ohlcv-bar b{color:#e2e8f2;}
#ohlcv-bar .bu{color:#26a69a;} #ohlcv-bar .be{color:#ef5350;}

/* LEGEND TOP-RIGHT */
#legend{position:absolute;top:7px;right:8px;z-index:20;display:flex;flex-direction:column;gap:3px;align-items:flex-end;pointer-events:none;}
.leg-r{display:flex;align-items:center;gap:5px;font-family:monospace;font-size:10.5px;background:rgba(6,11,20,.72);padding:3px 8px;border-radius:5px;}
.leg-dot{width:7px;height:7px;border-radius:2px;flex-shrink:0;}

/* STATS FOOTER */
#stats-bar{
  display:flex;align-items:center;gap:12px;padding:0 12px;height:34px;flex-shrink:0;
  background:#0a1018;border-top:1px solid rgba(255,255,255,0.05);
  font-family:monospace;font-size:11px;overflow-x:auto;
}
#stats-bar::-webkit-scrollbar{display:none;}
.stat-item{display:flex;align-items:center;gap:5px;white-space:nowrap;flex-shrink:0;}
.stat-lbl{color:#3f4d5e;}
.stat-val{font-weight:700;}

/* DRAWING TOOL RAIL */
#tool-rail{
  position:absolute;left:6px;top:50%;transform:translateY(-50%);z-index:30;
  display:flex;flex-direction:column;gap:4px;
  background:rgba(10,16,24,.92);border:1px solid rgba(255,255,255,0.08);
  border-radius:10px;padding:6px 4px;
}
.drw-b{width:30px;height:30px;border-radius:7px;display:flex;align-items:center;justify-content:center;cursor:pointer;color:#4a5568;transition:.12s;font-size:14px;}
.drw-b:hover{background:rgba(255,255,255,0.07);color:#e2e8f2;}
.drw-b.on{background:rgba(61,142,255,.15);color:#3d8eff;}
.drw-sep{width:22px;height:1px;background:rgba(255,255,255,0.06);margin:3px auto;}

/* FULLSCREEN */
:fullscreen #root{height:100vh!important;}
:fullscreen #chart-area{flex:1;}

/* 3D GLOW effect on container */
#chart-area::before{
  content:'';position:absolute;inset:0;pointer-events:none;z-index:1;
  background:
    radial-gradient(ellipse 60% 30% at 50% 0%, rgba(61,142,255,0.04) 0%, transparent 70%),
    radial-gradient(ellipse 40% 20% at 50% 100%, rgba(38,166,154,0.03) 0%, transparent 60%);
}
</style>
</head>
<body>
<div id="root">

<!-- TOOLBAR -->
<div id="toolbar">
  <div class="brand">Fin<b>Sage</b></div>
  <div class="sym-lbl" id="sym-lbl">__SYM__</div>
  <div class="price-disp" id="price-disp" style="color:__TC__;">__PRICE__</div>

  <div class="tf-row" id="tf-row">
    <div class="tf-b" data-tf="1D" data-p="3mo" data-i="1d">1D</div>
    <div class="tf-b on" data-tf="1W" data-p="1y" data-i="1wk">1W</div>
    <div class="tf-b" data-tf="1M" data-p="2y" data-i="1mo">1M</div>
    <div class="tf-b" data-tf="1H" data-p="5d" data-i="1h">1H</div>
    <div class="tf-b" data-tf="15m" data-p="1mo" data-i="15m">15m</div>
  </div>

  <div class="ct-row" id="ct-row">
    <div class="ct-b on" data-ct="candle">Candles</div>
    <div class="ct-b" data-ct="hollow">Hollow</div>
    <div class="ct-b" data-ct="heikinashi">HA</div>
    <div class="ct-b" data-ct="bar">Bars</div>
    <div class="ct-b" data-ct="line">Line</div>
    <div class="ct-b" data-ct="area">Area</div>
    <div class="ct-b" data-ct="baseline">Baseline</div>
  </div>

  <!-- Indicator toggles -->
  <div class="ind-tog on" id="tog-ema" data-ind="ema">EMA</div>
  <div class="ind-tog on" id="tog-vwap" data-ind="vwap">VWAP</div>
  <div class="ind-tog" id="tog-bb" data-ind="bb">BB</div>
  <div class="ind-tog" id="tog-vol" data-ind="vol">Vol%</div>
  <div class="ind-tog on" id="tog-sr" data-ind="sr">S/R</div>
  <div class="ind-tog" id="tog-fib" data-ind="fib">Fib</div>

  <div class="sp"></div>

  <!-- Right icons -->
  <div class="icon-b on" id="btn-sr" title="Auto S/R">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7h18M3 17h18"/></svg>
  </div>
  <div class="icon-b" id="btn-reset" title="Fit view">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>
  </div>
  <div class="icon-b" id="btn-screenshot" title="Snapshot">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
  </div>
  <div class="icon-b" id="btn-full" title="Fullscreen (F)">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
  </div>
</div>

<!-- CHART -->
<div id="chart-area">
  <div id="chart-div"></div>

  <!-- OHLCV readout -->
  <div id="ohlcv-bar">
    <span>Open</span> <b id="r-o">—</b>&nbsp;
    <span>High</span> <b class="bu" id="r-h">—</b>&nbsp;
    <span>Low</span>  <b class="be" id="r-l">—</b>&nbsp;
    <span>Close</span><b id="r-c">—</b>&nbsp;
    <span>Vol</span>  <b id="r-v">—</b>&nbsp;
    <span id="r-chg" style="margin-left:4px;"></span>
  </div>

  <!-- Legend -->
  <div id="legend"></div>

  <!-- Drawing tool rail -->
  <div id="tool-rail">
    <div class="drw-b on" data-drw="cursor" title="Cursor">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4l16 6-7 2-2 7z"/></svg>
    </div>
    <div class="drw-b" data-drw="hline" title="H-Line (H)">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18"/></svg>
    </div>
    <div class="drw-b" data-drw="trend" title="Trendline (T)">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19L20 5"/></svg>
    </div>
    <div class="drw-b" data-drw="fib" title="Fibonacci">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 5h18M3 10h13M3 15h9"/></svg>
    </div>
    <div class="drw-sep"></div>
    <div class="drw-b" data-drw="undo" title="Undo (Z)" id="drw-undo">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>
    </div>
    <div class="drw-b" data-drw="clear" title="Clear">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>
    </div>
  </div>
</div>

<!-- STATS BAR -->
<div id="stats-bar">
  <div class="stat-item"><span class="stat-lbl">RSI</span><span class="stat-val" style="color:__RSIC__;">__RSI__</span></div>
  <div class="stat-item"><span class="stat-lbl">Trend</span><span class="stat-val" style="color:__TC__;">__TREND__</span></div>
  <div class="stat-item"><span class="stat-lbl">Vol</span><span class="stat-val">__VOLR__x</span></div>
  <div class="stat-item"><span class="stat-lbl">ATR</span><span class="stat-val">__ATR__</span></div>
  <div class="stat-item"><span class="stat-lbl">Support</span><span class="stat-val" style="color:#26a69a;">__SUP__</span></div>
  <div class="stat-item"><span class="stat-lbl">Resist</span><span class="stat-val" style="color:#ef5350;">__RES__</span></div>
  <div class="stat-item"><span class="stat-lbl">VWAP</span><span class="stat-val">__VWAP__</span></div>
  <div style="margin-left:auto;font-size:10px;color:#2a3244;">Drag to pan · Scroll to zoom · F = fullscreen</div>
</div>

</div><!-- /root -->

<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){
'use strict';

var CANDLES = __CANDLES__;
var VOLS    = __VOLS__;
var SUPP    = __SUPP__;
var RES     = __RES__;
var FIBS    = __FIBS__;

var EMA20_P  = __EMA20P__;
var EMA50_P  = __EMA50P__;
var EMA200_P = __EMA200P__;
var VWAP_P   = __VWAPP__;

var showSR   = true;
var showFib  = false;
var showEMA  = true;
var showVWAP = true;
var showBB   = false;
var chartType = 'candle';

/* ── CHART INIT ────────────────────────────── */
var container = document.getElementById('chart-div');
var W = container.clientWidth  || window.innerWidth;
var H = container.clientHeight || (window.innerHeight - 76);

var chart = LightweightCharts.createChart(container, {
  width:  W,
  height: H,
  layout: {
    background:  { type:'solid', color:'#060b14' },
    textColor:   '#6a7585',
    fontSize:    11,
    fontFamily:  'monospace',
  },
  grid: {
    vertLines:  { color:'rgba(255,255,255,0.03)', style:0 },
    horzLines:  { color:'rgba(255,255,255,0.04)', style:0 },
  },
  crosshair: {
    mode:         LightweightCharts.CrosshairMode.Normal,
    vertLine:     { color:'rgba(61,142,255,0.5)', labelBackgroundColor:'#3d8eff', width:1, style:3 },
    horzLine:     { color:'rgba(61,142,255,0.5)', labelBackgroundColor:'#3d8eff', width:1, style:3 },
  },
  rightPriceScale: {
    borderColor:    'rgba(255,255,255,0.06)',
    textColor:      '#4a5568',
    scaleMargins:   { top:0.08, bottom:0.25 },
  },
  timeScale: {
    borderColor:    'rgba(255,255,255,0.06)',
    textColor:      '#4a5568',
    timeVisible:    true,
    secondsVisible: false,
    fixLeftEdge:    false,
    fixRightEdge:   false,
  },
  handleScroll: { mouseWheel:true, pressedMouseMove:true, horzTouchDrag:true },
  handleScale:  { mouseWheel:true, pinch:true, axisPressedMouseMove:true },
  localization: { priceFormatter: function(p){ return p>=1000 ? p.toFixed(2) : p.toFixed(4); } },
});

/* ── SERIES ────────────────────────────────── */
var mainSeries = null;

function makeCandles(){
  return chart.addCandlestickSeries({
    upColor:         '#26a69a',
    downColor:       '#ef5350',
    borderUpColor:   '#26a69a',
    borderDownColor: '#ef5350',
    wickUpColor:     'rgba(38,166,154,0.75)',
    wickDownColor:   'rgba(239,83,80,0.75)',
    wickVisible:     true,
    borderVisible:   true,
    // 3D shadow effect via per-bar color overrides below
  });
}
function makeHollow(){
  return chart.addCandlestickSeries({
    upColor:         'transparent',
    downColor:       'rgba(239,83,80,0.25)',
    borderUpColor:   '#26a69a',
    borderDownColor: '#ef5350',
    wickUpColor:     'rgba(38,166,154,0.75)',
    wickDownColor:   'rgba(239,83,80,0.75)',
  });
}
function makeHA(){
  // Compute Heikin-Ashi
  var ha = [];
  for(var i=0;i<CANDLES.length;i++){
    var c=CANDLES[i];
    var haC=(c.open+c.high+c.low+c.close)/4;
    var haO=i===0?(c.open+c.close)/2:(ha[i-1].open+ha[i-1].close)/2;
    var haH=Math.max(c.high,haO,haC), haL=Math.min(c.low,haO,haC);
    ha.push({time:c.time,open:haO,high:haH,low:haL,close:haC});
  }
  var s=chart.addCandlestickSeries({upColor:'#26a69a',downColor:'#ef5350',borderUpColor:'#26a69a',borderDownColor:'#ef5350',wickUpColor:'rgba(38,166,154,0.75)',wickDownColor:'rgba(239,83,80,0.75)'});
  s.setData(ha); return s;
}
function makeBar(){
  return chart.addBarSeries({upColor:'#26a69a',downColor:'#ef5350'});
}
function makeLine(){
  return chart.addLineSeries({color:'#3d8eff',lineWidth:2,crosshairMarkerVisible:true,crosshairMarkerRadius:4,crosshairMarkerBackgroundColor:'#3d8eff'});
}
function makeArea(){
  return chart.addAreaSeries({topColor:'rgba(61,142,255,0.25)',bottomColor:'rgba(61,142,255,0.02)',lineColor:'#3d8eff',lineWidth:2});
}
function makeBaseline(){
  var mid=CANDLES.length?((CANDLES[0].close+CANDLES[CANDLES.length-1].close)/2):0;
  return chart.addBaselineSeries({baseValue:{type:'price',price:mid},topLineColor:'#26a69a',topFillColor1:'rgba(38,166,154,0.25)',topFillColor2:'rgba(38,166,154,0.02)',bottomLineColor:'#ef5350',bottomFillColor1:'rgba(239,83,80,0.02)',bottomFillColor2:'rgba(239,83,80,0.25)',lineWidth:2});
}

function buildMain(type){
  if(mainSeries) chart.removeSeries(mainSeries);
  switch(type){
    case 'hollow':     mainSeries=makeHollow();   break;
    case 'heikinashi': mainSeries=makeHA();        return; // HA sets own data
    case 'bar':        mainSeries=makeBar();       break;
    case 'line':       mainSeries=makeLine();      break;
    case 'area':       mainSeries=makeArea();      break;
    case 'baseline':   mainSeries=makeBaseline();  break;
    default:           mainSeries=makeCandles();   break;
  }
  if(type==='line'||type==='area'||type==='baseline'){
    mainSeries.setData(CANDLES.map(function(c){ return {time:c.time,value:c.close}; }));
  } else {
    mainSeries.setData(CANDLES);
  }

  // 3D candlestick glow — add shadow-like lighter wick color for up candles
  if(type==='candle'){
    var coloredData = CANDLES.map(function(c){
      var bull = c.close >= c.open;
      return {
        time:  c.time,
        open:  c.open,
        high:  c.high,
        low:   c.low,
        close: c.close,
        color:          bull ? '#26a69a' : '#ef5350',
        wickColor:      bull ? 'rgba(38,200,154,0.6)' : 'rgba(239,83,80,0.5)',
        borderColor:    bull ? '#1de9b6' : '#ff5252',
      };
    });
    mainSeries.setData(coloredData);
  }
}

/* ── VOLUME ────────────────────────────────── */
var volSeries = chart.addHistogramSeries({
  priceScaleId:  'vol',
  scaleMargins:  { top:0.78, bottom:0 },
});
chart.priceScale('vol').applyOptions({ scaleMargins:{top:0.78,bottom:0} });
if(VOLS.length) volSeries.setData(VOLS);

/* ── INDICATORS ────────────────────────────── */
var emaSeries=null, ema50Series=null, ema200Series=null, vwapSeries=null, bbU=null, bbL=null, bbM=null;

function calcEMA(data,period){
  var k=2/(period+1),prev,out=[];
  data.forEach(function(d,i){
    if(i<period-1){out.push({time:d.time,value:null});return;}
    if(i===period-1){var s=0;for(var j=0;j<period;j++)s+=data[j].value;prev=s/period;out.push({time:d.time,value:prev});return;}
    prev=d.value*k+prev*(1-k);out.push({time:d.time,value:prev});
  });
  return out.filter(function(d){return d.value!=null;});
}
function calcBB(data,period,mult){
  var sma=[],sd=[];
  for(var i=period-1;i<data.length;i++){
    var s=0;for(var j=i-period+1;j<=i;j++)s+=data[j].value;var m=s/period;sma.push({t:data[i].time,v:m});
    var v2=0;for(var j2=i-period+1;j2<=i;j2++)v2+=Math.pow(data[j2].value-m,2);sd.push(Math.sqrt(v2/period));
  }
  return {upper:sma.map(function(d,i){return{time:d.t,value:d.v+mult*sd[i]};}),
          mid:sma.map(function(d){return{time:d.t,value:d.v};}),
          lower:sma.map(function(d,i){return{time:d.t,value:d.v-mult*sd[i]};})};
}

var closeData = CANDLES.map(function(c){return{time:c.time,value:c.close};});

function buildIndicators(){
  // EMA 20
  if(showEMA){
    if(!emaSeries){ emaSeries=chart.addLineSeries({color:'#3d8eff',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false}); }
    emaSeries.setData(calcEMA(closeData,20));
    if(!ema50Series){ ema50Series=chart.addLineSeries({color:'#f0a93c',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false}); }
    ema50Series.setData(calcEMA(closeData,50));
    if(!ema200Series){ ema200Series=chart.addLineSeries({color:'#ef5350',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false}); }
    ema200Series.setData(calcEMA(closeData,200));
  } else {
    if(emaSeries){try{chart.removeSeries(emaSeries);}catch(e){}emaSeries=null;}
    if(ema50Series){try{chart.removeSeries(ema50Series);}catch(e){}ema50Series=null;}
    if(ema200Series){try{chart.removeSeries(ema200Series);}catch(e){}ema200Series=null;}
  }
  // VWAP
  if(showVWAP){
    if(!vwapSeries){ vwapSeries=chart.addLineSeries({color:'#e040fb',lineWidth:1.5,lineStyle:LightweightCharts.LineStyle.Dashed,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false}); }
    var pv=0,v2=0, vwD=[];
    CANDLES.forEach(function(c){ var tp=(c.high+c.low+c.close)/3; pv+=tp*VOLS.find(function(vv){return vv.time===c.time;}).value; v2+=VOLS.find(function(vv){return vv.time===c.time;}).value; vwD.push({time:c.time,value:pv/v2}); });
    vwapSeries.setData(vwD);
  } else {
    if(vwapSeries){try{chart.removeSeries(vwapSeries);}catch(e){}vwapSeries=null;}
  }
  // BB
  if(showBB){
    var bb=calcBB(closeData,20,2);
    if(!bbU){ bbU=chart.addLineSeries({color:'rgba(155,140,255,0.6)',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false}); }
    if(!bbM){ bbM=chart.addLineSeries({color:'rgba(155,140,255,0.3)',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false}); }
    if(!bbL){ bbL=chart.addLineSeries({color:'rgba(155,140,255,0.6)',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false}); }
    bbU.setData(bb.upper); bbM.setData(bb.mid); bbL.setData(bb.lower);
  } else {
    [bbU,bbM,bbL].forEach(function(s){if(s){try{chart.removeSeries(s);}catch(e){}}}); bbU=bbM=bbL=null;
  }
}

/* ── S/R PRICE LINES ───────────────────────── */
var srLines=[];
function buildSR(){
  srLines.forEach(function(l){try{mainSeries.removePriceLine(l);}catch(e){}});
  srLines=[];
  if(!showSR||!mainSeries) return;
  SUPP.forEach(function(s,i){
    srLines.push(mainSeries.createPriceLine({price:s,color:i===0?'#26a69a':'rgba(38,166,154,0.45)',lineWidth:i===0?1.5:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'S '+s.toFixed(2)}));
  });
  RES.forEach(function(r,i){
    srLines.push(mainSeries.createPriceLine({price:r,color:i===0?'#ef5350':'rgba(239,83,80,0.45)',lineWidth:i===0?1.5:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:'R '+r.toFixed(2)}));
  });
}

/* ── FIBONACCI PRICE LINES ─────────────────── */
var fibLines=[];
function buildFib(){
  fibLines.forEach(function(l){try{mainSeries.removePriceLine(l);}catch(e){}});
  fibLines=[];
  if(!showFib||!mainSeries) return;
  var fibColors={'0.236':'#7986cb','0.382':'#26a69a','0.500':'#fbbf24','0.618':'#ef5350','0.786':'#e040fb'};
  Object.keys(FIBS).forEach(function(k){
    if(!FIBS[k]) return;
    fibLines.push(mainSeries.createPriceLine({price:FIBS[k],color:fibColors[k]||'#aaa',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'Fib '+k}));
  });
}

/* ── LEGEND ────────────────────────────────── */
function updateLegend(){
  var el=document.getElementById('legend'), html='';
  if(showEMA){ html+='<div class="leg-r"><div class="leg-dot" style="background:#3d8eff;"></div><span style="color:#3d8eff;">EMA20</span></div>'; html+='<div class="leg-r"><div class="leg-dot" style="background:#f0a93c;"></div><span style="color:#f0a93c;">EMA50</span></div>'; }
  if(showVWAP){ html+='<div class="leg-r"><div class="leg-dot" style="background:#e040fb;"></div><span style="color:#e040fb;">VWAP</span></div>'; }
  if(showBB){ html+='<div class="leg-r"><div class="leg-dot" style="background:#9b8cff;"></div><span style="color:#9b8cff;">BB(20)</span></div>'; }
  el.innerHTML=html;
}

/* ── CROSSHAIR READOUT ─────────────────────── */
chart.subscribeCrosshairMove(function(param){
  if(!param.time) return;
  var d=param.seriesData.get(mainSeries);
  if(!d) return;
  var o=d.open||d.value, h=d.high||d.value, l=d.low||d.value, c=d.close||d.value;
  var v=0; if(param.seriesData.get(volSeries)) v=param.seriesData.get(volSeries).value;
  var bull=c>=o, chgPct=o?((c-o)/o*100):0;
  document.getElementById('r-o').textContent = o>=100?o.toFixed(2):o.toFixed(4);
  document.getElementById('r-h').textContent = h>=100?h.toFixed(2):h.toFixed(4);
  document.getElementById('r-l').textContent = l>=100?l.toFixed(2):l.toFixed(4);
  document.getElementById('r-c').textContent = c>=100?c.toFixed(2):c.toFixed(4);
  document.getElementById('r-c').style.color  = bull?'#26a69a':'#ef5350';
  document.getElementById('r-v').textContent  = (v/1e6).toFixed(2)+'M';
  var chgEl=document.getElementById('r-chg');
  chgEl.textContent = (chgPct>=0?'+':'')+chgPct.toFixed(2)+'%';
  chgEl.style.color = bull?'#26a69a':'#ef5350';
});

/* ── TOOLBAR EVENTS ────────────────────────── */
document.querySelectorAll('.tf-b').forEach(function(b){
  b.addEventListener('click',function(){
    document.querySelectorAll('.tf-b').forEach(function(x){x.classList.remove('on');});
    b.classList.add('on');
    // TF change note
    showToast('TF: '+b.dataset.tf+' — loading live data...');
    // In production: fetch new OHLCV via postMessage to parent Streamlit
    if(window.parent && window.parent.postMessage){
      window.parent.postMessage({type:'chart_tf',tf:b.dataset.tf,period:b.dataset.p,interval:b.dataset.i},'*');
    }
  });
});
document.querySelectorAll('.ct-b').forEach(function(b){
  b.addEventListener('click',function(){
    document.querySelectorAll('.ct-b').forEach(function(x){x.classList.remove('on');});
    b.classList.add('on');
    chartType=b.dataset.ct; buildMain(chartType);
    buildSR(); buildFib(); buildIndicators(); updateLegend();
    chart.timeScale().fitContent();
  });
});
document.querySelectorAll('.ind-tog').forEach(function(b){
  b.addEventListener('click',function(){
    var ind=b.dataset.ind;
    b.classList.toggle('on');
    if(ind==='ema')  showEMA  =b.classList.contains('on');
    if(ind==='vwap') showVWAP =b.classList.contains('on');
    if(ind==='bb')   showBB   =b.classList.contains('on');
    if(ind==='sr')   { showSR  =b.classList.contains('on'); buildSR(); }
    if(ind==='fib')  { showFib =b.classList.contains('on'); buildFib(); }
    if(ind!=='sr'&&ind!=='fib') buildIndicators();
    updateLegend();
  });
});
document.getElementById('btn-reset').addEventListener('click',function(){ chart.timeScale().fitContent(); });
document.getElementById('btn-full').addEventListener('click',function(){
  var el=document.getElementById('root');
  if(!document.fullscreenElement){ el.requestFullscreen&&el.requestFullscreen(); }
  else { document.exitFullscreen&&document.exitFullscreen(); }
});
document.getElementById('btn-sr').addEventListener('click',function(){
  showSR=!showSR; this.classList.toggle('on',showSR); buildSR();
});

/* ── DRAWING TOOLS ─────────────────────────── */
var activeDrw='cursor', drawLines=[], undoStack=[], inProgLine=null, drwColor='#3d8eff';
document.querySelectorAll('.drw-b[data-drw]').forEach(function(b){
  b.addEventListener('click',function(){
    var d=b.dataset.drw;
    if(d==='undo'){ if(undoStack.length){ var l=undoStack.pop(); try{chart.removeSeries(l);}catch(e){} } return; }
    if(d==='clear'){ drawLines.forEach(function(l){try{chart.removeSeries(l);}catch(e){}});drawLines=[];undoStack=[];return; }
    activeDrw=d;
    document.querySelectorAll('.drw-b[data-drw]').forEach(function(x){x.classList.remove('on');});
    b.classList.add('on');
    showToast(d==='hline'?'Click to place horizontal line':d==='trend'?'Click 2 points for trendline':d==='fib'?'Click 2 points for Fibonacci':'Cursor mode');
  });
});

var drwPts=[];
container.addEventListener('click',function(e){
  if(activeDrw==='cursor') return;
  var rect=container.getBoundingClientRect(), x=e.clientX-rect.left, y=e.clientY-rect.top;
  var p=chart.coordsToPrice(y);
  if(isNaN(p)||p==null) return;
  if(activeDrw==='hline'){
    var hl=mainSeries.createPriceLine({price:p,color:drwColor,lineWidth:1.5,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:p>=100?p.toFixed(2):p.toFixed(4)});
    undoStack.push({type:'priceline',line:hl,series:mainSeries});
    showToast('H-Line at '+(p>=100?p.toFixed(2):p.toFixed(4)));
    return;
  }
  if(activeDrw==='trend'||activeDrw==='fib'){
    drwPts.push({x:x,y:y,p:p});
    if(drwPts.length===2){
      var t=chart.coordsToTime(drwPts[0].x);
      var ls=chart.addLineSeries({color:drwColor,lineWidth:1.5,lastValueVisible:false,priceLineVisible:false});
      ls.setData([{time:t||CANDLES[0].time,value:drwPts[0].p},{time:chart.coordsToTime(drwPts[1].x)||CANDLES[CANDLES.length-1].time,value:drwPts[1].p}]);
      drawLines.push(ls); undoStack.push({type:'series',series:ls});
      if(activeDrw==='fib'){
        var p1=drwPts[0].p, p2=drwPts[1].p, fibR=[0.236,0.382,0.5,0.618,0.786], fibC=['#7986cb','#26a69a','#fbbf24','#ef5350','#e040fb'];
        fibR.forEach(function(r,ri){
          var fp=p2+r*(p1-p2);
          var fl=mainSeries.createPriceLine({price:fp,color:fibC[ri],lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:'Fib '+(r*100).toFixed(1)+'%'});
          undoStack.push({type:'priceline',line:fl,series:mainSeries});
        });
      }
      drwPts=[];
    } else {
      showToast('Click second point...');
    }
  }
});

/* Keyboard */
window.addEventListener('keydown',function(e){
  if(e.key==='f'||e.key==='F'){ var el2=document.getElementById('root'); if(!document.fullscreenElement) el2.requestFullscreen&&el2.requestFullscreen(); else document.exitFullscreen&&document.exitFullscreen(); }
  if(e.key==='h'||e.key==='H') document.querySelector('.drw-b[data-drw="hline"]').click();
  if(e.key==='t'||e.key==='T') document.querySelector('.drw-b[data-drw="trend"]').click();
  if(e.key==='z'||e.key==='Z'){ if(undoStack.length){ var it=undoStack.pop(); if(it.type==='priceline'){try{it.series.removePriceLine(it.line);}catch(ex){}}else{try{chart.removeSeries(it.series);}catch(ex){}}}}
  if(e.key==='Escape') document.querySelector('.drw-b[data-drw="cursor"]').click();
});

/* Toast */
function showToast(msg){ var t=document.getElementById('toast-el'); if(!t){t=document.createElement('div');t.id='toast-el';t.style.cssText='position:fixed;bottom:50px;left:50%;transform:translateX(-50%);background:#1e2533;border:1px solid rgba(255,255,255,0.12);color:#e2e8f2;padding:7px 16px;border-radius:8px;font-size:11.5px;z-index:999;font-family:monospace;pointer-events:none;transition:opacity .25s;';document.body.appendChild(t);} t.textContent=msg;t.style.opacity='1';clearTimeout(t._tid);t._tid=setTimeout(function(){t.style.opacity='0';},2000); }

/* ── RESIZE ────────────────────────────────── */
window.addEventListener('resize',function(){ chart.applyOptions({width:container.clientWidth,height:container.clientHeight}); });
document.addEventListener('fullscreenchange',function(){ setTimeout(function(){ chart.applyOptions({width:container.clientWidth,height:container.clientHeight}); chart.timeScale().fitContent(); },100); });

/* ── INIT ──────────────────────────────────── */
buildMain('candle');
buildIndicators();
buildSR();
buildFib();
updateLegend();
chart.timeScale().fitContent();

})();
</script>
</body>
</html>"""

    # String substitutions — safe, no f-string confusion
    html = html.replace("__CHT__",    str(CHT))
    html = html.replace("__SYM__",    sym.replace(".NS","").replace("-USD","").replace("^",""))
    html = html.replace("__PRICE__",  f"{cur_p:,.2f}" if cur_p>=100 else f"{cur_p:,.4f}")
    html = html.replace("__TC__",     tc)
    html = html.replace("__RSIC__",   "#ef5350" if rsi_v>70 else "#26a69a" if rsi_v<30 else "#d1d4dc")
    html = html.replace("__RSI__",    f"{rsi_v:.1f}")
    html = html.replace("__TREND__",  trend)
    html = html.replace("__VOLR__",   f"{vol_r:.2f}")
    html = html.replace("__ATR__",    f"{atr_v:.4f}" if atr_v else "—")
    html = html.replace("__SUP__",    f"{round(sup[0],2)}" if sup else "—")
    html = html.replace("__RES__",    f"{round(res[0],2)}" if res else "—")
    html = html.replace("__VWAP__",   f"{vwap_p:.2f}" if vwap_p else "—")
    html = html.replace("__CANDLES__",cj)
    html = html.replace("__VOLS__",   vj)
    html = html.replace("__SUPP__",   sj)
    html = html.replace("__RES__",    rj)   # overwrite second __RES__
    html = html.replace("__FIBS__",   fj)
    html = html.replace("__EMA20P__", str(ema20_p or 0))
    html = html.replace("__EMA50P__", str(ema50_p or 0))
    html = html.replace("__EMA200P__",str(ema200_p or 0))
    html = html.replace("__VWAPP__",  str(vwap_p or 0))

    components.html(html, height=CHT+16, scrolling=False)

def _mini_chart_html(sym, name, price, chg, trend, sup, res, height=180):
    """6-mini-chart: small LightweightCharts candle chart for watchlist overview"""
    from pro_chart import _ohlcv
    import json
    try:
        df = _ohlcv(sym, "1mo", "1d")
    except:
        df = None
    candles = []
    if df is not None and not df.empty:
        import pandas as pd
        for idx, row in df.tail(60).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            candles.append({"time": ts, "open": round(float(row["Open"]), 4),
                            "high": round(float(row["High"]), 4),
                            "low":  round(float(row["Low"]),  4),
                            "close":round(float(row["Close"]),4)})
    cc = "#26a69a" if chg >= 0 else "#ef5350"
    tc = "#26a69a" if trend == "BULLISH" else "#ef5350" if trend == "BEARISH" else "#f59e0b"
    pr_s = f"{price:,.2f}" if price >= 1 else f"{price:.4f}"
    chg_s = f"{chg:+.2f}%"
    sup_v = round(sup[0], 2) if sup else 0
    res_v = round(res[0], 2) if res else 0
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:transparent;width:100%;height:{height}px;overflow:hidden;}}
#h{{display:flex;align-items:center;justify-content:space-between;padding:5px 8px 3px;}}
#nm{{font-size:11px;font-weight:800;color:#fff;font-family:Inter,sans-serif;}}
#pr{{font-size:13px;font-weight:900;color:{cc};font-family:'Courier New',monospace;}}
#ch{{font-size:10px;color:{cc};}}
#cd{{width:100%;height:{height-50}px;}}
#ft{{display:flex;justify-content:space-between;padding:2px 8px;font-size:9px;font-family:Inter,sans-serif;}}
</style></head><body>
<div id="h"><span id="nm">{name[:12]}</span><div style="text-align:right;"><div id="pr">{pr_s}</div><div id="ch">{chg_s}</div></div></div>
<div id="cd"></div>
<div id="ft">
  <span style="color:#26a69a;">S:{sup_v or '—'}</span>
  <span style="color:{tc};font-weight:700;">{trend[:4]}</span>
  <span style="color:#ef5350;">R:{res_v or '—'}</span>
</div>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){{
var candles={json.dumps(candles)};
var el=document.getElementById('cd'); if(!el||!candles.length) return;
var chart=LightweightCharts.createChart(el,{{
  width:el.clientWidth||200,height:{height-50},
  layout:{{background:{{type:'solid',color:'transparent'}},textColor:'#5a6070',fontSize:9}},
  grid:{{vertLines:{{color:'rgba(255,255,255,0.02)'}},horzLines:{{color:'rgba(255,255,255,0.02)'}}}},
  rightPriceScale:{{borderColor:'rgba(255,255,255,0.04)',scaleMargins:{{top:0.05,bottom:0.05}},textColor:'#374151'}},
  timeScale:{{borderColor:'rgba(255,255,255,0.04)',visible:false}},
  crosshair:{{vertLine:{{visible:false}},horzLine:{{visible:false}}}},
  handleScroll:false,handleScale:false,
}});
var cs=chart.addCandlestickSeries({{
  upColor:'#26a69a',downColor:'#ef5350',
  borderUpColor:'#26a69a',borderDownColor:'#ef5350',
  wickUpColor:'rgba(38,166,154,0.6)',wickDownColor:'rgba(239,83,80,0.6)',
}});
cs.setData(candles);
{f"cs.createPriceLine({{price:{sup_v},color:'rgba(38,166,154,0.6)',lineWidth:1,lineStyle:1,axisLabelVisible:false,title:'S'}});" if sup_v else ""}
{f"cs.createPriceLine({{price:{res_v},color:'rgba(239,83,80,0.6)',lineWidth:1,lineStyle:1,axisLabelVisible:false,title:'R'}});" if res_v else ""}
chart.timeScale().fitContent();
window.addEventListener('resize',function(){{chart.applyOptions({{width:el.clientWidth||200}});}});
}})();
</script></body></html>"""



# ════════════════════════════════════════════════════════════════════════
# 6-TRADER CHART GRID — Ek stock, 6 alag trader styles, ek screen
# ════════════════════════════════════════════════════════════════════════
def _six_trader_charts_html(df, tech, ai, sym, height=820):
    """
    6 charts of the SAME stock, each styled for a different trader type:
    1. Price Action  — clean candles, S/R, trendlines, pattern arrows
    2. SMC / ICT     — candles + OB zones + FVG + Liquidity levels
    3. Quant         — Heikin-Ashi + EMA ribbon (9/20/50/200)
    4. Indicator     — candles + RSI band + BB bands + VWAP + MACD color
    5. Volume/Flow   — candles + Volume bars large + POC + VWAP
    6. Elliott Wave  — candles + Fibonacci levels + Wave labels
    """
    # ── Prepare data ───────────────────────────────────────────────────
    candles = []; ha_candles = []; vols = []
    if df is not None and not df.empty:
        prev_ha = None
        for idx, row in df.tail(120).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            o,h,l,c,v = float(row["Open"]),float(row["High"]),float(row["Low"]),float(row["Close"]),int(row["Volume"])
            candles.append({"time":ts,"open":round(o,4),"high":round(h,4),"low":round(l,4),"close":round(c,4)})
            vols.append({"time":ts,"value":v,"color":"rgba(38,166,154,0.5)" if c>=o else "rgba(239,83,80,0.5)"})
            ha_c = (o+h+l+c)/4
            ha_o = ((prev_ha["open"]+prev_ha["close"])/2) if prev_ha else (o+c)/2
            ha_h = max(h,ha_o,ha_c); ha_l = min(l,ha_o,ha_c)
            ha_candles.append({"time":ts,"open":round(ha_o,4),"high":round(ha_h,4),"low":round(ha_l,4),"close":round(ha_c,4)})
            prev_ha = {"open":ha_o,"close":ha_c}

    sup   = tech.get("supports",[]);    res   = tech.get("resistances",[])
    fib   = tech.get("fib",{});         vwap_v= tech.get("vwap",0)
    e9    = tech.get("ema9",0);         e20   = tech.get("ema20",0)
    e50   = tech.get("ema50",0);        e200  = tech.get("ema200",0)
    bb_u  = tech.get("bb_upper",0);     bb_l  = tech.get("bb_lower",0)
    cur   = tech.get("price",0);        rsi_v = tech.get("rsi",50)
    macd_h= tech.get("macd_h",0)
    ob_list = tech.get("order_blocks",[])[:4]
    fvg_list= tech.get("fvg",[])[:4]
    poc_v = ai.get("key_levels",{}).get("poc", vwap_v)
    entry_v= ai.get("entry",0); stop_v = ai.get("stop",0)
    t1_v  = ai.get("t1",0);    t2_v   = ai.get("t2",0)
    bias  = ai.get("bias","NEUTRAL"); bc = ai.get("bias_color","#f59e0b")
    conf  = ai.get("confidence",65)

    # Pattern markers
    markers = []
    for pt in tech.get("patterns",[])[:6]:
        bi = min(pt.get("bar",len(candles)-1),len(candles)-1)
        if 0 <= bi < len(candles):
            cdl = candles[bi]
            pc  = {"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#fbbf24"}.get(pt["type"],"#fbbf24")
            ps  = {"BULLISH":"arrowUp","BEARISH":"arrowDown","NEUTRAL":"circle"}.get(pt["type"],"circle")
            pp  = {"BULLISH":"belowBar","BEARISH":"aboveBar","NEUTRAL":"inBar"}.get(pt["type"],"inBar")
            markers.append({"time":cdl["time"],"position":pp,"color":pc,"shape":ps,"text":pt["name"][:8]})

    import json as _json
    cj  = _json.dumps(candles)
    haj = _json.dumps(ha_candles)
    vj  = _json.dumps(vols)
    mj  = _json.dumps(markers)
    sj  = _json.dumps(sup[:4])
    rj  = _json.dumps(res[:4])
    fj  = _json.dumps(fib)
    obj = _json.dumps(ob_list)
    fvj = _json.dumps(fvg_list)

    chart_h = (height - 60) // 2   # each chart height
    card_h  = chart_h + 46          # chart + title + stats bar

    # PA analysis text
    pa   = ai.get("price_action",{}); smc_d = ai.get("smc",{}); q = ai.get("quant",{})
    ind  = ai.get("indicator",{});    vol_d = ai.get("volume",{}); wave_d = ai.get("wave",{})

    styles = [
        ("📊 Price Action", "#1a237e", "#4a9eff",
         pa.get("signal","—"), pa.get("signal_reason","S/R + Clean candles")[:55]),
        ("🏦 SMC / ICT",    "#b71c1c", "#ef5350",
         smc_d.get("signal","—"), smc_d.get("signal_reason","OB + Liquidity zones")[:55]),
        ("🤖 Quant / Algo", "#1b5e20", "#26a69a",
         f"{q.get('win_rate','—')} WR", q.get("statistical_edge","EMA ribbon + HA")[:55]),
        ("📈 Indicators",   "#e65100", "#f59e0b",
         f"RSI {rsi_v:.0f}", ind.get("overall_signal","RSI+MACD+BB+VWAP")[:55]),
        ("📦 Volume Flow",  "#4a148c", "#a855f7",
         f"Vol {tech.get('vol_ratio',1):.1f}x", vol_d.get("volume_delta","POC + VWAP")[:55]),
        ("🌊 Elliott Wave", "#006064", "#26c6da",
         wave_d.get("wave_count","—")[:20], wave_d.get("cycle_phase","Fib + Wave count")[:55]),
    ]

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#060911;color:#d1d4dc;font-family:'Inter','Segoe UI',sans-serif;
  width:100%;height:{height}px;overflow:hidden;}}

/* HEADER */
#hdr{{height:44px;background:rgba(13,17,28,0.97);backdrop-filter:blur(20px);
  border-bottom:1px solid rgba(255,255,255,0.06);display:flex;align-items:center;
  padding:0 14px;gap:10px;flex-shrink:0;}}
.hdr-sym{{font-size:14px;font-weight:900;color:#fff;}}
.hdr-pr{{font-size:18px;font-weight:900;color:{bc};font-family:'Courier New',monospace;}}
.hdr-bias{{padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;
  background:{bc}18;color:{bc};border:1px solid {bc}33;}}
.hdr-sub{{font-size:10px;color:#374151;}}
.hdr-conf{{font-size:11px;color:#374151;margin-left:auto;}}

/* GRID */
#grid{{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,1fr);
  gap:3px;padding:3px;flex:1;background:#060911;height:{height-47}px;}}

/* CHART CARD */
.cc{{display:flex;flex-direction:column;background:#080b12;border-radius:8px;
  border:1px solid rgba(255,255,255,0.05);overflow:hidden;position:relative;}}
.cc-title{{height:28px;display:flex;align-items:center;padding:0 8px;gap:6px;flex-shrink:0;
  border-bottom:1px solid rgba(255,255,255,0.04);}}
.cc-icon{{font-size:12px;}}
.cc-name{{font-size:10.5px;font-weight:800;letter-spacing:.02em;}}
.cc-sig{{margin-left:auto;font-size:9.5px;font-weight:700;padding:1px 7px;
  border-radius:8px;border:1px solid;}}
.cc-chart{{flex:1;position:relative;min-height:0;}}
.cc-bar{{height:18px;display:flex;align-items:center;padding:0 8px;gap:8px;
  background:rgba(0,0,0,0.3);border-top:1px solid rgba(255,255,255,0.03);flex-shrink:0;}}
.cc-stat{{font-size:9px;color:#374151;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.cc-stat b{{color:#9598a1;}}
</style></head><body>

<!-- HEADER -->
<div id="hdr">
  <div class="hdr-sym">{sym.replace(".NS","").replace("-USD","").replace("^","")}</div>
  <div class="hdr-pr">{cur:.4f if cur<100 else f"{cur:,.2f}"}</div>
  <div class="hdr-bias">{bias}</div>
  <div class="hdr-sub">6 Trader Views · Same Stock · Same Candles</div>
  <div class="hdr-conf">{conf}% confidence · FinSage AI</div>
</div>

<!-- 6-CHART GRID -->
<div id="grid">
  <!-- 1: Price Action -->
  <div class="cc" id="c0">
    <div class="cc-title" style="background:rgba(26,35,126,0.15);border-bottom-color:rgba(26,35,126,0.3);">
      <span class="cc-icon">📊</span>
      <span class="cc-name" style="color:#4a9eff;">Price Action</span>
      <span class="cc-sig" style="color:{('#26a69a' if styles[0][3]=='BUY' else '#ef5350' if styles[0][3]=='SELL' else '#f59e0b')};border-color:rgba(255,255,255,0.15);">{styles[0][3]}</span>
    </div>
    <div class="cc-chart" id="ch0"></div>
    <div class="cc-bar"><span class="cc-stat">{styles[0][4]}</span></div>
  </div>

  <!-- 2: SMC/ICT -->
  <div class="cc" id="c1">
    <div class="cc-title" style="background:rgba(183,28,28,0.15);border-bottom-color:rgba(183,28,28,0.3);">
      <span class="cc-icon">🏦</span>
      <span class="cc-name" style="color:#ef5350;">SMC / ICT</span>
      <span class="cc-sig" style="color:{('#26a69a' if styles[1][3]=='BUY' else '#ef5350' if styles[1][3]=='SELL' else '#f59e0b')};border-color:rgba(255,255,255,0.15);">{styles[1][3]}</span>
    </div>
    <div class="cc-chart" id="ch1"></div>
    <div class="cc-bar"><span class="cc-stat">{styles[1][4]}</span></div>
  </div>

  <!-- 3: Quant -->
  <div class="cc" id="c2">
    <div class="cc-title" style="background:rgba(27,94,32,0.15);border-bottom-color:rgba(27,94,32,0.3);">
      <span class="cc-icon">🤖</span>
      <span class="cc-name" style="color:#26a69a;">Quant / Algo</span>
      <span class="cc-sig" style="color:#26a69a;border-color:rgba(255,255,255,0.15);">{styles[2][3]}</span>
    </div>
    <div class="cc-chart" id="ch2"></div>
    <div class="cc-bar"><span class="cc-stat">{styles[2][4]}</span></div>
  </div>

  <!-- 4: Indicators -->
  <div class="cc" id="c3">
    <div class="cc-title" style="background:rgba(230,81,0,0.15);border-bottom-color:rgba(230,81,0,0.3);">
      <span class="cc-icon">📈</span>
      <span class="cc-name" style="color:#f59e0b;">Indicators</span>
      <span class="cc-sig" style="color:#f59e0b;border-color:rgba(255,255,255,0.15);">{styles[3][3]}</span>
    </div>
    <div class="cc-chart" id="ch3"></div>
    <div class="cc-bar"><span class="cc-stat">{styles[3][4]}</span></div>
  </div>

  <!-- 5: Volume -->
  <div class="cc" id="c4">
    <div class="cc-title" style="background:rgba(74,20,140,0.15);border-bottom-color:rgba(74,20,140,0.3);">
      <span class="cc-icon">📦</span>
      <span class="cc-name" style="color:#a855f7;">Volume Flow</span>
      <span class="cc-sig" style="color:#a855f7;border-color:rgba(255,255,255,0.15);">{styles[4][3]}</span>
    </div>
    <div class="cc-chart" id="ch4"></div>
    <div class="cc-bar"><span class="cc-stat">{styles[4][4]}</span></div>
  </div>

  <!-- 6: Elliott Wave -->
  <div class="cc" id="c5">
    <div class="cc-title" style="background:rgba(0,96,100,0.15);border-bottom-color:rgba(0,96,100,0.3);">
      <span class="cc-icon">🌊</span>
      <span class="cc-name" style="color:#26c6da;">Elliott Wave</span>
      <span class="cc-sig" style="color:#26c6da;border-color:rgba(255,255,255,0.15);">{styles[5][3]}</span>
    </div>
    <div class="cc-chart" id="ch5"></div>
    <div class="cc-bar"><span class="cc-stat">{styles[5][4]}</span></div>
  </div>
</div>

<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){{
var LWC = LightweightCharts;
var candles={cj}, ha={haj}, vols={vj}, marks={mj};
var sup={sj}, res={rj}, fib={fj};
var ob_list={obj}, fvg_list={fvj};
var e9={e9 or 0},e20={e20 or 0},e50={e50 or 0},e200={e200 or 0};
var bb_u={bb_u or 0},bb_l={bb_l or 0},vwap_v={vwap_v or 0},poc_v={poc_v or 0};
var entry_v={entry_v or 0},stop_v={stop_v or 0},t1_v={t1_v or 0},t2_v={t2_v or 0};
var rsi_v={rsi_v:.1f},macd_h={macd_h:.6f};

/* ── CHART FACTORY ─────────────────────────────────────── */
function makeChart(elId){{
  var el=document.getElementById(elId);
  if(!el) return null;
  var w=el.clientWidth||300, h=el.clientHeight||200;
  var c=LWC.createChart(el,{{
    width:w, height:h,
    layout:{{background:{{type:'solid',color:'#080b12'}},textColor:'#4a5060',fontSize:9}},
    grid:{{vertLines:{{color:'rgba(255,255,255,0.02)'}},horzLines:{{color:'rgba(255,255,255,0.02)'}}}},
    rightPriceScale:{{borderColor:'rgba(255,255,255,0.04)',scaleMargins:{{top:0.06,bottom:0.04}}}},
    timeScale:{{borderColor:'rgba(255,255,255,0.04)',timeVisible:false,
      rightOffset:3,barSpacing:5,minBarSpacing:0.3}},
    crosshair:{{mode:LWC.CrosshairMode.Normal,
      vertLine:{{color:'rgba(255,255,255,0.12)',labelVisible:false}},
      horzLine:{{color:'rgba(255,255,255,0.12)',labelVisible:true}}}},
    handleScroll:{{mouseWheel:true,pressedMouseMove:true}},
    handleScale:{{mouseWheel:true,pinch:true}},
  }});
  window.addEventListener('resize',function(){{
    var nw=el.clientWidth||300,nh=el.clientHeight||200;
    c.applyOptions({{width:nw,height:nh}});
  }});
  return c;
}}

function addCandle(chart, data, opts){{
  opts=opts||{{}};
  var s=chart.addCandlestickSeries({{
    upColor:opts.up||'#26a69a',downColor:opts.dn||'#ef5350',
    borderUpColor:opts.up||'#26a69a',borderDownColor:opts.dn||'#ef5350',
    wickUpColor:opts.wup||'rgba(38,166,154,0.6)',wickDownColor:opts.wdn||'rgba(239,83,80,0.6)',
  }});
  s.setData(data); return s;
}}

function addVol(chart){{
  chart.priceScale('vol').applyOptions({{scaleMargins:{{top:0.82,bottom:0}}}});
  var v=chart.addHistogramSeries({{priceScaleId:'vol',scaleMargins:{{top:0.82,bottom:0}}}});
  v.setData(vols); return v;
}}

function priceLine(s,price,color,style,title,width){{
  if(!price) return;
  return s.createPriceLine({{price:price,color:color,lineWidth:width||1,
    lineStyle:style||LWC.LineStyle.Dashed,axisLabelVisible:true,title:title||''}});
}}

/* ─────────────────────────────────────────────────────────
   CHART 0: PRICE ACTION
   Clean candles | S/R | Trendlines | Pattern arrows
   No indicators — price tells everything
───────────────────────────────────────────────────────── */
(function(){{
  var c=makeChart('ch0'); if(!c) return;
  var s=addCandle(c,candles);
  if(marks.length) s.setMarkers(marks);
  // Strong S/R only — clean look
  sup.forEach(function(v,i){{priceLine(s,v,'rgba(38,166,154,'+(i===0?'0.85':'0.5')+')',
    LWC.LineStyle.Dashed,i===0?'Key S':'S',i===0?2:1);}});
  res.forEach(function(v,i){{priceLine(s,v,'rgba(239,83,80,'+(i===0?'0.85':'0.5')+')',
    LWC.LineStyle.Dashed,i===0?'Key R':'R',i===0?2:1);}});
  // Entry/Stop/Target — the PA trader's levels
  priceLine(s,entry_v,'rgba(38,166,154,0.9)',LWC.LineStyle.Solid,'Entry',2);
  priceLine(s,stop_v,'rgba(239,83,80,0.9)',LWC.LineStyle.Solid,'Stop',2);
  priceLine(s,t1_v,'rgba(41,98,255,0.8)',LWC.LineStyle.Dashed,'T1',1);
  c.timeScale().fitContent();
}})();

/* ─────────────────────────────────────────────────────────
   CHART 1: SMC / ICT
   Candles | Order Blocks | FVG | Liquidity | OB zones
───────────────────────────────────────────────────────── */
(function(){{
  var c=makeChart('ch1'); if(!c) return;
  var s=addCandle(c,candles);
  // S/R (subtle for SMC — focus on OB)
  sup.slice(0,2).forEach(function(v){{priceLine(s,v,'rgba(38,166,154,0.35)',LWC.LineStyle.Dotted,'',1);}});
  res.slice(0,2).forEach(function(v){{priceLine(s,v,'rgba(239,83,80,0.35)',LWC.LineStyle.Dotted,'',1);}});
  // Order Blocks
  ob_list.forEach(function(ob){{
    var isBull=ob.type&&ob.type.indexOf('BULL')>=0;
    var col=isBull?'rgba(38,166,154,0.85)':'rgba(239,83,80,0.85)';
    var top=ob.zone_top||ob.top||0, bot=ob.zone_bot||ob.bot||0;
    priceLine(s,top,col,LWC.LineStyle.Solid,(isBull?'Bull':'Bear')+' OB▲',1);
    priceLine(s,bot,col,LWC.LineStyle.Solid,(isBull?'Bull':'Bear')+' OB▼',1);
  }});
  // FVG zones
  fvg_list.forEach(function(fv){{
    var isBull=fv.type&&fv.type.indexOf('BULL')>=0;
    var col=isBull?'rgba(38,166,154,0.6)':'rgba(239,83,80,0.6)';
    if(fv.top) priceLine(s,fv.top,col,LWC.LineStyle.Dotted,'FVG'+(isBull?'▲':'▼'),1);
    if(fv.bot) priceLine(s,fv.bot,col,LWC.LineStyle.Dotted,'',1);
  }});
  // Premium/Discount midline
  if(sup.length&&res.length){{
    var mid=(sup[0]+res[0])/2;
    priceLine(s,mid,'rgba(251,191,36,0.5)',LWC.LineStyle.Dotted,'EQ',1);
  }}
  c.timeScale().fitContent();
}})();

/* ─────────────────────────────────────────────────────────
   CHART 2: QUANT / ALGO
   Heikin-Ashi candles | EMA 9/20/50/200 ribbon
   Statistical lens — smooth trend, no noise
───────────────────────────────────────────────────────── */
(function(){{
  var c=makeChart('ch2'); if(!c) return;
  // HA candles (smoother for quant)
  var s=addCandle(c,ha,{{up:'#26a69a',dn:'#ef5350',wup:'rgba(38,166,154,0.4)',wdn:'rgba(239,83,80,0.4)'}});
  // EMA ribbon — the quant's core tool
  var emas=[
    [e9, 'rgba(255,255,255,0.5)','EMA9'],
    [e20,'rgba(33,150,243,0.8)', 'EMA20'],
    [e50,'rgba(255,152,0,0.8)',  'EMA50'],
    [e200,'rgba(233,30,99,0.8)','EMA200'],
  ];
  emas.forEach(function(e){{
    if(e[0]) priceLine(s,e[0],e[1],LWC.LineStyle.Solid,e[2],1);
  }});
  // Key statistical level
  priceLine(s,entry_v,'rgba(38,166,154,0.7)',LWC.LineStyle.Dashed,'Entry',1);
  c.timeScale().fitContent();
}})();

/* ─────────────────────────────────────────────────────────
   CHART 3: INDICATOR TRADER
   Candles | BB Bands | VWAP | RSI color overlay | MACD signal
───────────────────────────────────────────────────────── */
(function(){{
  var c=makeChart('ch3'); if(!c) return;
  var s=addCandle(c,candles);
  // Bollinger Bands
  if(bb_u) priceLine(s,bb_u,'rgba(156,39,176,0.75)',LWC.LineStyle.Solid,'BB+',1);
  if(bb_l) priceLine(s,bb_l,'rgba(156,39,176,0.75)',LWC.LineStyle.Solid,'BB-',1);
  var bbMid=bb_u&&bb_l?(bb_u+bb_l)/2:0;
  if(bbMid) priceLine(s,bbMid,'rgba(156,39,176,0.35)',LWC.LineStyle.Dotted,'BB Mid',1);
  // VWAP
  if(vwap_v) priceLine(s,vwap_v,'rgba(251,191,36,0.85)',LWC.LineStyle.Solid,'VWAP',2);
  // EMA20/50
  if(e20) priceLine(s,e20,'rgba(33,150,243,0.7)',LWC.LineStyle.Dashed,'EMA20',1);
  if(e50) priceLine(s,e50,'rgba(255,152,0,0.7)',LWC.LineStyle.Dashed,'EMA50',1);
  // RSI overbought/oversold zones as price context
  var rsiCol=rsi_v>70?'rgba(239,83,80,0.6)':rsi_v<30?'rgba(38,166,154,0.6)':'rgba(251,191,36,0.4)';
  if(entry_v) priceLine(s,entry_v,rsiCol,LWC.LineStyle.Solid,'RSI '+(rsi_v>70?'OB':rsi_v<30?'OS':'Ntrl'),1);
  c.timeScale().fitContent();
}})();

/* ─────────────────────────────────────────────────────────
   CHART 4: VOLUME / ORDER FLOW
   Candles | Large volume bars | POC | VWAP | S/R
   Money flow perspective — volume tells truth
───────────────────────────────────────────────────────── */
(function(){{
  var c=makeChart('ch4'); if(!c) return;
  var s=addCandle(c,candles);
  // POC — Point of Control (most traded price)
  if(poc_v) priceLine(s,poc_v,'rgba(41,98,255,0.9)',LWC.LineStyle.Solid,'POC',2);
  // VWAP
  if(vwap_v) priceLine(s,vwap_v,'rgba(251,191,36,0.8)',LWC.LineStyle.Dotted,'VWAP',1);
  // Volume profile levels
  sup.slice(0,2).forEach(function(v){{priceLine(s,v,'rgba(38,166,154,0.6)',LWC.LineStyle.Dashed,'HVN S',1);}});
  res.slice(0,2).forEach(function(v){{priceLine(s,v,'rgba(239,83,80,0.6)',LWC.LineStyle.Dashed,'HVN R',1);}});
  // Large volume bars
  c.priceScale('vol').applyOptions({{scaleMargins:{{top:0.75,bottom:0}}}});
  var vs=c.addHistogramSeries({{priceScaleId:'vol',scaleMargins:{{top:0.75,bottom:0}}}});
  vs.setData(vols);
  c.timeScale().fitContent();
}})();

/* ─────────────────────────────────────────────────────────
   CHART 5: ELLIOTT WAVE / GANN
   Candles | Fibonacci levels | Wave zones
   Cycle & ratio perspective
───────────────────────────────────────────────────────── */
(function(){{
  var c=makeChart('ch5'); if(!c) return;
  var s=addCandle(c,candles);
  // Fibonacci levels — the wave trader's key tool
  var fibColors={{
    '0.236':'rgba(121,134,203,0.85)',
    '0.382':'rgba(38,166,154,0.85)',
    '0.500':'rgba(251,191,36,0.85)',
    '0.618':'rgba(239,83,80,0.85)',
    '0.786':'rgba(224,64,251,0.85)',
  }};
  Object.keys(fib).forEach(function(k){{
    var v=fib[k]; if(!v) return;
    var col=fibColors[k]||'rgba(200,200,200,0.6)';
    priceLine(s,v,col,LWC.LineStyle.Dotted,'Fib '+k,1);
  }});
  // Key S/R with wave label
  if(sup[0]) priceLine(s,sup[0],'rgba(38,166,154,0.8)',LWC.LineStyle.Dashed,'W-Sup',1);
  if(res[0]) priceLine(s,res[0],'rgba(239,83,80,0.8)',LWC.LineStyle.Dashed,'W-Res',1);
  // Wave extension target
  if(t1_v) priceLine(s,t1_v,'rgba(41,98,255,0.7)',LWC.LineStyle.Solid,'Wave Tgt',1);
  c.timeScale().fitContent();
}})();

}})(); // end IIFE
</script></body></html>"""



def _to_tv(sym):
    """TV symbol converter — covers NSE/BSE/crypto/US/indices"""
    s = sym.upper()
    if s.endswith(".NS"):  return f"NSE:{s[:-3]}"
    if s.endswith(".BO"):  return f"BSE:{s[:-3]}"
    if s.endswith(".L"):   return f"LSE:{s[:-2]}"
    if s.endswith(".DE"):  return f"XETR:{s[:-3]}"
    if s.endswith(".T"):   return f"TSE:{s[:-2]}"
    if s.endswith(".HK"):  return f"HKEX:{s[:-3]}"
    if s.endswith(".AX"):  return f"ASX:{s[:-3]}"
    # Crypto
    if s.endswith("-USD"):
        base = s[:-4].replace("-","")
        return f"BINANCE:{base}USDT"
    if s.endswith("-USDT"): return f"BINANCE:{s[:-5]}USDT"
    if s.endswith("-BTC"):  return f"BINANCE:{s[:-4]}BTC"
    # Indices
    index_map = {
        "^NSEI":"NSE:NIFTY","^BSESN":"BSE:SENSEX","^GSPC":"SP:SPX",
        "^DJI":"DJ:DJI","^IXIC":"NASDAQ:IXIC","^VIX":"CBOE:VIX",
        "^NSEBANK":"NSE:BANKNIFTY","^CNXIT":"NSE:CNXIT",
        "^FTSE":"SPREADEX:FTSE","^N225":"TVC:NI225","^HSI":"TVC:HSI",
    }
    if s in index_map: return index_map[s]
    # Commodities/Futures
    comm_map = {"GC=F":"TVC:GOLD","SI=F":"TVC:SILVER","CL=F":"NYMEX:CL1!",
                "NG=F":"NYMEX:NG1!","BZ=F":"TVC:UKOIL","HG=F":"COMEX:HG1!"}
    if s in comm_map: return comm_map[s]
    # Forex
    if s in {"EURUSD=X","GBPUSD=X","USDINR=X","USDJPY=X","AUDUSD=X"}:
        return "FX:" + s.replace("=X","")
    # NYSE large caps
    NYSE = {"JPM","BAC","WMT","JNJ","V","MA","UNH","XOM","CVX","PFE","KO",
            "PEP","DIS","BA","GE","GM","F","T","VZ","BRK-B","C","GS","MS"}
    if s in NYSE: return f"NYSE:{s}"
    return f"NASDAQ:{s}"



def render_user_dashboard():
    import json, yfinance as _yf

    st.markdown("""<style>
    header[data-testid="stHeader"],footer,
    div[data-testid="stDecoration"],div[data-testid="stToolbar"],
    div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}
    .stApp,[data-testid="stAppViewContainer"],[data-testid="stMainBlockContainer"],
    .main,.block-container,[data-testid="stVerticalBlock"],
    section[data-testid="stMain"]{background:transparent!important;}
    .block-container{padding:0 0 20px 0!important;max-width:100vw!important;}
    .stTabs [data-baseweb="tab-list"]{gap:4px;background:rgba(13,17,28,0.7);
        backdrop-filter:blur(10px);padding:4px;border-radius:10px;
        border:1px solid rgba(255,255,255,0.06);}
    .stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px;
        color:#6a6e7a;font-size:12px;padding:5px 12px;}
    .stTabs [aria-selected="true"]{background:rgba(41,98,255,0.2)!important;color:#4a9eff!important;}
    div[data-testid="stVerticalBlock"]{gap:4px!important;}
    div[data-testid="stTextInput"] input{background:rgba(13,17,28,0.7)!important;
        border:1px solid rgba(255,255,255,0.08)!important;color:#d1d4dc!important;border-radius:8px!important;}
    div[data-baseweb="select"]{background:rgba(13,17,28,0.7)!important;border-radius:8px!important;}
    div[data-baseweb="select"] *{color:#d1d4dc!important;}
    button[kind="secondary"]{background:rgba(255,255,255,0.04)!important;
        border:1px solid rgba(255,255,255,0.08)!important;color:#9598a1!important;border-radius:8px!important;}
    button[kind="primary"]{border-radius:8px!important;}
    </style>""", unsafe_allow_html=True)

    # ── STATE ─────────────────────────────────────────────────────────────
    defaults = [
        ("pd_favs",    list(DEFAULT_FAVS)),
        ("pd_sel",     None),
        ("pd_ai",      None),
        ("pd_fund",    {}),
        ("pd_srch",    ""),
        ("pd_srch_res",[]),
        ("pd_tf",      "1D"),
        ("pd_mode",    "chart"),
        ("pd_fullscreen", False),
        ("pd_analysis_data", None),
    ]
    for k, v in defaults:
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state.pd_sel is None and st.session_state.pd_favs:
        st.session_state.pd_sel = st.session_state.pd_favs[0]

    favs = st.session_state.pd_favs
    sel  = st.session_state.pd_sel or DEFAULT_FAVS[0]
    sym  = sel["sym"]; name = sel["name"]

    # ── TOP BAR ───────────────────────────────────────────────────────────
    d   = _price_fast(sym)
    pr  = d.get("price", 0); chg = d.get("chg", 0)
    cc  = "#26a69a" if chg >= 0 else "#ef5350"
    pr_s= f"{pr:,.4f}" if 0 < pr < 10 else f"{pr:,.2f}" if pr > 0 else "—"

    st.markdown(f"""<div style="background:rgba(8,11,18,0.92);backdrop-filter:blur(24px);
    border-bottom:1px solid rgba(255,255,255,0.06);padding:8px 18px;
    display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:4px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:36px;height:36px;background:linear-gradient(135deg,#2962ff,#a855f7);
          border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;">📊</div>
        <div>
          <div style="color:#fff;font-weight:900;font-size:15px;">Personal <span style="color:#2962ff;">Dashboard</span></div>
          <div style="color:#374151;font-size:10px;">Free Auto Chart Analyzer · S/R · Patterns · AI Analysis</div>
        </div>
      </div>
      <div style="flex:1;"></div>
      <div style="text-align:right;">
        <div style="color:#9598a1;font-size:12px;font-weight:700;">{name}
          <span style="color:{cc};font-family:monospace;font-size:17px;font-weight:900;margin-left:6px;">{pr_s}</span>
          <span style="color:{cc};font-size:11px;margin-left:4px;">{chg:+.2f}%</span>
        </div>
        <div style="color:#374151;font-size:10px;">🕐 {datetime.now().strftime('%a, %d %b · %H:%M IST')}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── LAYOUT ────────────────────────────────────────────────────────────
    left_col, chart_col = st.columns([1, 4], gap="small")

    # ══════════════════════════════════════════════════════════════════════
    # LEFT PANEL — Watchlist
    # ══════════════════════════════════════════════════════════════════════
    with left_col:
        srch = st.text_input("", "", placeholder="🔍 Search stock / crypto...",
                             key="pd_srch_inp", label_visibility="collapsed")
        if srch != st.session_state.pd_srch:
            st.session_state.pd_srch = srch
            if srch.strip():
                with st.spinner("..."): st.session_state.pd_srch_res = _srch(srch)
            else: st.session_state.pd_srch_res = []

        for item in st.session_state.pd_srch_res[:6]:
            d2 = _price_fast(item["sym"]); pr2 = d2.get("price", 0); cc2 = "#26a69a" if d2.get("chg",0)>=0 else "#ef5350"
            c1, c2 = st.columns([3, 1])
            with c1:
                if st.button(f"+ {item['name'][:14]}", key=f"padd_{item['sym']}", use_container_width=True):
                    if not any(f["sym"]==item["sym"] for f in st.session_state.pd_favs):
                        st.session_state.pd_favs.append({"sym":item["sym"],"name":item["name"],"type":item["type"]})
                        st.toast(f"⭐ {item['name']} added!")
                    st.session_state.pd_sel = {"sym":item["sym"],"name":item["name"],"type":item["type"]}
                    st.session_state.pd_ai = None; st.session_state.pd_analysis_data = None
                    st.session_state.pd_srch = ""; st.session_state.pd_srch_res = []; st.rerun()
            with c2:
                st.markdown(f'<div style="font-size:10px;color:{cc2};text-align:right;padding-top:6px;">{pr2:.2f}</div>', unsafe_allow_html=True)

        # Watchlist
        st.markdown("""<div style="display:flex;padding:4px 5px;font-size:8px;color:#374151;font-weight:700;
        background:rgba(255,255,255,0.03);border-radius:6px 6px 0 0;text-transform:uppercase;
        letter-spacing:.05em;border-bottom:1px solid rgba(255,255,255,0.04);">
          <span style="flex:1;">Symbol</span>
          <span style="width:62px;text-align:right;">Price</span>
          <span style="width:38px;text-align:right;">Chg%</span>
          <span style="width:14px;"></span>
        </div>""", unsafe_allow_html=True)

        to_remove = None
        for item in list(favs):
            d3 = _price_fast(item["sym"]); pr3=d3.get("price",0); chg3=d3.get("chg",0)
            cc3 = "#26a69a" if chg3>=0 else "#ef5350"
            is_s = sel["sym"]==item["sym"]
            pr3s = f"{pr3:,.4f}" if 0<pr3<10 else f"{pr3:,.2f}" if pr3>0 else "—"
            chg3s= f"{chg3:+.1f}%" if pr3>0 else "—"
            ti = {"stock":"📈","crypto":"🪙","index":"📊","commodity":"🥇"}.get(item["type"],"📈")
            # Logo display
            logo_url = _get_logo_url(item["sym"])
            logo_html = f'<img src="{logo_url}" style="width:14px;height:14px;border-radius:3px;object-fit:contain;margin-right:4px;vertical-align:middle;" onerror="this.style.display=\'none\'" />' if logo_url else f'{ti} '
            bc1, bc2 = st.columns([5,1])
            with bc1:
                if st.button(f"{ti} {item['name'][:13]}", key=f"pfav_{item['sym']}",
                             use_container_width=True, type="primary" if is_s else "secondary"):
                    st.session_state.pd_sel = item; st.session_state.pd_ai = None
                    st.session_state.pd_analysis_data = None; st.rerun()
            with bc2:
                if st.button("✕", key=f"prem_{item['sym']}", use_container_width=True):
                    to_remove = item["sym"]
            st.markdown(
                f'<div style="display:flex;padding:0 5px 3px 5px;font-size:10px;'
                f'border-bottom:1px solid rgba(255,255,255,0.03);margin-top:-8px;">'
                f'<span style="flex:1;color:#374151;font-size:8.5px;">'
                f'{item["sym"].replace(".NS","").replace("-USD","").replace("^","")}</span>'
                f'<span style="color:{cc3};font-family:monospace;font-weight:700;min-width:62px;text-align:right;">{pr3s}</span>'
                f'<span style="color:{cc3};min-width:38px;text-align:right;font-size:9.5px;">{chg3s}</span>'
                f'<span style="width:14px;"></span></div>', unsafe_allow_html=True)

        if to_remove:
            st.session_state.pd_favs = [f for f in st.session_state.pd_favs if f["sym"]!=to_remove]
            if sel["sym"]==to_remove and st.session_state.pd_favs:
                st.session_state.pd_sel=st.session_state.pd_favs[0]; st.session_state.pd_ai=None; st.session_state.pd_analysis_data=None
            st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:9px;color:#374151;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px;">Quick Add</div>', unsafe_allow_html=True)
        sec = st.selectbox("", list(SECTOR_STOCKS.keys()), key="pd_sec", label_visibility="collapsed")
        for s in SECTOR_STOCKS[sec][:5]:
            d4=_price_fast(s); pr4=d4.get("price",0); chg4=d4.get("chg",0); cc4="#26a69a" if chg4>=0 else "#ef5350"
            already=any(f["sym"]==s for f in st.session_state.pd_favs)
            lbl=("✓ " if already else "+ ")+s.replace(".NS","").replace("-USD","").replace("^","")
            if st.button(lbl, key=f"pqa_{s}", use_container_width=True):
                nm2=s.replace(".NS","").replace("-USD","").replace("^","")
                if not already:
                    st.session_state.pd_favs.append({"sym":s,"name":nm2,"type":"stock"}); st.toast(f"⭐ {nm2} added!")
                st.session_state.pd_sel={"sym":s,"name":nm2,"type":"stock"}; st.session_state.pd_ai=None; st.session_state.pd_analysis_data=None; st.rerun()
            if pr4>0:
                st.markdown(f'<div style="display:flex;font-size:9.5px;padding:0 3px 2px;margin-top:-8px;border-bottom:1px solid rgba(255,255,255,0.03);"><span style="flex:1;color:#374151;font-size:8px;">{s}</span><span style="color:{cc4};font-family:monospace;">{pr4:.2f}</span><span style="color:{cc4};margin-left:4px;">{chg4:+.1f}%</span></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # RIGHT PANEL — Free Auto Chart Analyzer
    # ══════════════════════════════════════════════════════════════════════
    with chart_col:

        # ── TOOLBAR ───────────────────────────────────────────────────────
        tc1,tc2,tc3,tc4,tc5,tc6 = st.columns([2,2,2,1,1,1])
        with tc1:
            period_sel = st.selectbox("", ["3mo","6mo","1y","2y"],
                index=1, key="pd_period_sel",
                format_func=lambda x: {"3mo":"3 Months","6mo":"6 Months","1y":"1 Year","2y":"2 Years"}[x],
                label_visibility="collapsed")
        with tc2:
            interval_sel = st.selectbox("", ["1d","1wk"],
                index=0, key="pd_interval_sel",
                format_func=lambda x: {"1d":"Daily","1wk":"Weekly"}[x],
                label_visibility="collapsed")
        with tc3:
            mode_sel = st.radio("", ["📊 Chart","🤖 AI Analysis","📋 Full Report"],
                horizontal=True, key="pd_mode_r2", label_visibility="collapsed")
        with tc4:
            analyze_btn = st.button("🔍 Analyze", key="pd_analyze", type="primary", use_container_width=True)
        with tc5:
            if st.button("🔄 Refresh", key="pd_ref2", use_container_width=True):
                st.session_state.pd_analysis_data=None; st.session_state.pd_ai=None; st.rerun()
        with tc6:
            fullscreen_btn = st.button("⛶ Full", key="pd_fs_btn", use_container_width=True)

        # ── FETCH DATA ────────────────────────────────────────────────────
        if analyze_btn or st.session_state.pd_analysis_data is None:
            with st.spinner(f"Fetching & analyzing {name} ({sym})..."):
                try:
                    raw = _yf.download(sym, interval=interval_sel, period=period_sel, progress=False, auto_adjust=True)
                    if raw is not None and not raw.empty:
                        if isinstance(raw.columns, __import__('pandas').MultiIndex):
                            raw.columns = [c[0] for c in raw.columns]
                        df = raw.reset_index()
                        time_col = "Date" if "Date" in df.columns else "Datetime"
                        df = df.rename(columns={time_col:"time","Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
                        df["time"] = df["time"].astype(str)
                        df = df[["time","open","high","low","close","volume"]].dropna()
                        if len(df) >= 10:
                            from chart_analysis_engine import full_analysis
                            result = full_analysis(df, sym)
                            st.session_state.pd_analysis_data = result
                        else:
                            st.error("Not enough candle data"); return
                    else:
                        st.error(f"No data for {sym}"); return
                except Exception as e:
                    st.error(f"Data error: {e}"); return

        data = st.session_state.pd_analysis_data
        if not data:
            st.info("Click Analyze to load chart data"); return

        candles = data["candles"]
        indicators = data["indicators"]
        sr_zones = data["support_resistance"]
        patterns = data["patterns"]
        bias = data["overall_bias"]
        glossary = data["glossary"]

        n_candles = len(candles)
        n_patterns = len(patterns)
        bias_col = "#3fd0a0" if bias=="bullish" else "#ff5d6c" if bias=="bearish" else "#e8b34d"

        # ── STATUS BAR ────────────────────────────────────────────────────
        st.markdown(f"""<div style="background:rgba(13,17,28,0.8);backdrop-filter:blur(12px);
        border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:6px 14px;margin-bottom:4px;
        display:flex;gap:16px;align-items:center;flex-wrap:wrap;font-size:12px;">
          <span style="color:{bias_col};font-weight:800;text-transform:uppercase;
          background:{bias_col}18;border:1px solid {bias_col}44;padding:2px 10px;border-radius:12px;">
          {'📈' if bias=='bullish' else '📉' if bias=='bearish' else '➖'} {bias.upper()}</span>
          <span style="color:#6a6e7a;">{n_candles} candles</span>
          <span style="color:#6a6e7a;">{n_patterns} patterns detected</span>
          <span style="color:#6a6e7a;">{len(sr_zones)} S/R zones</span>
          <span style="margin-left:auto;color:#374151;font-size:10px;">{sym} · {period_sel} · {interval_sel}</span>
        </div>""", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════════
        # CHART MODE — LWC Chart Analyzer (like the HTML you gave)
        # ══════════════════════════════════════════════════════════════════
        if "Chart" in mode_sel and "Report" not in mode_sel:
            chart_html = _build_lwc_analyzer_html(candles, indicators, sr_zones, patterns, bias, sym, name, fullscreen=st.session_state.get("pd_fullscreen", False))
            components.html(chart_html, height=820 if not st.session_state.get("pd_fullscreen",False) else 1100, scrolling=False)

            if fullscreen_btn:
                st.session_state.pd_fullscreen = not st.session_state.get("pd_fullscreen", False); st.rerun()

            # Below chart: S/R + Patterns side by side
            side1, side2 = st.columns([1,1])
            with side1:
                st.markdown('<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6a6e7a;margin-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:4px;">Support / Resistance Zones</div>', unsafe_allow_html=True)
                for z in sorted(sr_zones, key=lambda x: -x["price"])[:10]:
                    zc = "#3fd0a0" if z["type"]=="support" else "#ff5d6c"
                    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 10px;border-radius:6px;margin-bottom:4px;background:{zc}0d;border-left:3px solid {zc};"><span style="color:#d1d4dc;font-family:monospace;font-size:12.5px;">{"Support" if z["type"]=="support" else "Resistance"} — ₹{z["price"]}</span><span style="color:#6a6e7a;font-size:11px;">touched {z["strength"]}x</span></div>', unsafe_allow_html=True)

            with side2:
                st.markdown('<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6a6e7a;margin-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:4px;">Detected Candlestick Patterns — White Paper</div>', unsafe_allow_html=True)
                recent_patterns = list(reversed(patterns))[:15]
                for p in recent_patterns:
                    pc = "#3fd0a0" if p["bias"]=="bullish" else "#ff5d6c" if p["bias"]=="bearish" else "#e8b34d"
                    st.markdown(f'<div style="background:rgba(13,17,28,0.7);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:8px 10px;margin-bottom:6px;"><div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-weight:700;font-size:12.5px;">{p["name"]}</span><span style="background:{pc}22;color:{pc};border:1px solid {pc}55;font-size:10px;padding:1px 7px;border-radius:10px;font-weight:700;">{p["bias"].upper()}</span></div><div style="font-size:11.5px;color:#8893a3;line-height:1.5;">{p["definition"]}</div></div>', unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════════
        # AI ANALYSIS MODE
        # ══════════════════════════════════════════════════════════════════
        elif "AI Analysis" in mode_sel:
            if st.session_state.pd_ai is None:
                with st.spinner(f"🤖 SAGE AI: Analysing {name}..."):
                    try:
                        from pro_chart import _ohlcv, _compute_tech
                        tf_map = {"1d":"1D","1wk":"1W"}
                        _df = _ohlcv(sym, period_sel, interval_sel)
                        tech = _compute_tech(_df) if _df is not None and not _df.empty else {}
                    except:
                        tech = {}
                    fund = _fundamental(sym)
                    try:
                        from quant_engine import run_quant_engine
                        from fundamental_engine import run_fundamental_engine
                        import yfinance as _yf_q
                        _bdf = _yf_q.Ticker("^NSEI" if ".NS" in sym else "^GSPC").history(period="6mo",interval="1d")
                        fund["quant_real"] = run_quant_engine(_df if _df is not None and not _df.empty else None, _bdf if not _bdf.empty else None)
                        fund["fund_health"] = run_fundamental_engine(sym)
                    except:
                        fund["quant_real"] = {}; fund["fund_health"] = {}
                    ai_res = _master_analysis(sym, name, tech, fund)
                st.session_state.pd_ai = ai_res; st.session_state.pd_fund = fund
            else:
                ai_res = st.session_state.pd_ai; fund = st.session_state.pd_fund

            bc2 = ai_res.get("bias_color","#f59e0b"); rat = ai_res.get("rating","HOLD")
            rc2 = ai_res.get("rating_color","#f59e0b"); conf = ai_res.get("confidence",65)
            api_u = ai_res.get("_api","AI")
            st.markdown(f"""<div style="background:rgba(13,17,28,0.85);backdrop-filter:blur(18px);
            border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:10px 16px;margin:4px 0;
            display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
              <span style="background:{rc2}18;color:{rc2};border:1px solid {rc2}33;border-radius:20px;
                padding:4px 14px;font-weight:800;font-size:13px;">{rat}</span>
              <span style="color:{bc2};font-weight:800;font-size:15px;">{ai_res.get('bias','NEUTRAL')}</span>
              <span style="color:#9598a1;font-size:12px;">{ai_res.get('summary','')[:130]}</span>
              <span style="margin-left:auto;color:#374151;font-size:10px;">via {api_u} · {conf}% conf</span>
            </div>""", unsafe_allow_html=True)

            tabs = st.tabs(["📊 Price Action","🏦 SMC/ICT","🤖 Quant","📈 Indicators","📦 Volume","🌊 Wave+Fib","📋 Setup","📄 Full Report"])

            with tabs[0]:
                pa = ai_res.get("price_action", {})
                st.markdown(f'<div style="background:rgba(26,35,126,0.1);border:1px solid rgba(26,35,126,0.3);border-radius:10px;padding:14px;"><div style="font-size:11px;color:#4a9eff;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Price Action</div><div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{pa.get("view","")}</div></div>', unsafe_allow_html=True)
                c1,c2,c3 = st.columns(3)
                pat_name=pa.get("pattern_detected","—"); sig=pa.get("signal","WAIT")
                sc="#26a69a" if sig=="BUY" else "#ef5350" if sig=="SELL" else "#f59e0b"
                with c1: st.markdown(f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:8px;padding:10px;text-align:center;"><div style="font-size:10px;color:#374151;text-transform:uppercase;margin-bottom:4px;">Chart Pattern</div><div style="font-size:14px;font-weight:800;color:#4a9eff;">{pat_name}</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div style="background:{sc}11;border:2px solid {sc}44;border-radius:8px;padding:10px;text-align:center;"><div style="font-size:10px;color:#374151;text-transform:uppercase;margin-bottom:4px;">PA Signal</div><div style="font-size:22px;font-weight:900;color:{sc};">{sig}</div></div>', unsafe_allow_html=True)
                with c3:
                    pats = data.get("patterns",[])
                    rows = "".join([f'<div style="font-size:11px;color:{"#26a69a" if p["bias"]=="bullish" else "#ef5350" if p["bias"]=="bearish" else "#e8b34d"};padding:2px 0;">{"▲" if p["bias"]=="bullish" else "▼" if p["bias"]=="bearish" else "◆"} {p["name"]}</div>' for p in pats[-6:]])
                    st.markdown(f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:8px;padding:10px;"><div style="font-size:10px;color:#374151;text-transform:uppercase;margin-bottom:4px;">Detected Patterns</div>{rows}</div>', unsafe_allow_html=True)

            with tabs[1]:
                smc = ai_res.get("smc",{})
                st.markdown(f'<div style="background:rgba(183,28,28,0.08);border:1px solid rgba(183,28,28,0.3);border-radius:10px;padding:14px;"><div style="font-size:11px;color:#ef5350;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">SMC/ICT</div><div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{smc.get("view","")}</div></div>', unsafe_allow_html=True)

            with tabs[2]:
                q = ai_res.get("quant",{})
                st.markdown(f'<div style="background:rgba(27,94,32,0.08);border:1px solid rgba(27,94,32,0.3);border-radius:10px;padding:14px;margin-bottom:8px;"><div style="font-size:11px;color:#26a69a;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Quant Analysis</div><div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{q.get("view","")}</div></div>', unsafe_allow_html=True)
                cols = st.columns(4)
                for i,(lbl,val,c) in enumerate([("Win Rate",q.get("win_rate","—"),"#26a69a"),("Expected Value",str(q.get("expected_value","—")),"#2962ff"),("Setup Grade",q.get("setup_quality","B"),"#f59e0b"),("Bull Prob",q.get("probability_bullish","—"),"#26a69a")]):
                    with cols[i]: st.markdown(f'<div style="background:{c}0d;border:1px solid {c}33;border-radius:8px;padding:10px;text-align:center;"><div style="font-size:9.5px;color:#374151;text-transform:uppercase;margin-bottom:3px;">{lbl}</div><div style="font-size:22px;font-weight:900;color:{c};font-family:monospace;">{val}</div></div>', unsafe_allow_html=True)
                qr = fund.get("quant_real",{})
                if qr.get("ok"):
                    qv2=qr.get("volatility",{}); qt2=qr.get("trend",{}); qb2=qr.get("beta")
                    pu=qt2.get("prob_up_5d","—") if qt2.get("ok") else "—"; av=qv2.get("annualized_volatility_pct","—")
                    st.markdown("---"); st.caption("**Real Quant Engine (Logistic Regression)**")
                    cq1,cq2,cq3,cq4 = st.columns(4)
                    for col,lbl,val,c in [(cq1,"5D Up Prob",f"{pu}%","#26a69a"),(cq2,"Ann. Vol",f"{av}%","#f59e0b"),(cq3,"Beta",str(qb2) if qb2 else "—","#2962ff"),(cq4,"Model Acc",f'{qt2.get("train_accuracy_pct","—")}%',"#a855f7")]:
                        col.markdown(f'<div style="background:{c}0d;border:1px solid {c}33;border-radius:8px;padding:8px;text-align:center;"><div style="font-size:9px;color:#374151;text-transform:uppercase;">{lbl}</div><div style="font-size:18px;font-weight:900;color:{c};font-family:monospace;">{val}</div></div>', unsafe_allow_html=True)

            with tabs[3]:
                ind = ai_res.get("indicator",{})
                st.markdown(f'<div style="background:rgba(230,81,0,0.08);border:1px solid rgba(230,81,0,0.3);border-radius:10px;padding:14px;"><div style="font-size:11px;color:#f59e0b;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Indicators</div><div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{ind.get("view","")}</div></div>', unsafe_allow_html=True)

            with tabs[4]:
                v = ai_res.get("volume",{})
                st.markdown(f'<div style="background:rgba(74,20,140,0.08);border:1px solid rgba(74,20,140,0.3);border-radius:10px;padding:14px;"><div style="font-size:11px;color:#a855f7;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Volume Analysis</div><div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{v.get("view","")}</div></div>', unsafe_allow_html=True)

            with tabs[5]:
                w = ai_res.get("wave",{}); fib = data["indicators"][-1] if data["indicators"] else {}
                st.markdown(f'<div style="background:rgba(0,96,100,0.08);border:1px solid rgba(0,96,100,0.3);border-radius:10px;padding:14px;"><div style="font-size:11px;color:#26c6da;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Elliott Wave / Fibonacci</div><div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{w.get("view","")}</div></div>', unsafe_allow_html=True)

            with tabs[6]:
                c1,c2,c3 = st.columns(3)
                entry_v=ai_res.get("entry",0); stop_v=ai_res.get("stop",0); t1_v=ai_res.get("t1",0); t2_v=ai_res.get("t2",0)
                rr=ai_res.get("rr","—"); bc3=ai_res.get("bias_color","#f59e0b")
                with c1: st.markdown(f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px;"><div style="font-size:11px;color:#374151;text-transform:uppercase;font-weight:700;margin-bottom:10px;">Trade Setup</div><div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span style="color:#26a69a;font-weight:700;">Entry</span><span style="color:#26a69a;font-family:monospace;font-size:17px;font-weight:900;">{entry_v:.4f}</span></div><div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span style="color:#ef5350;font-weight:700;">Stop</span><span style="color:#ef5350;font-family:monospace;font-size:17px;font-weight:900;">{stop_v:.4f}</span></div><div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span style="color:#2962ff;">Target 1</span><span style="color:#2962ff;font-family:monospace;font-size:15px;font-weight:800;">{t1_v:.4f}</span></div><div style="display:flex;justify-content:space-between;padding:7px 0;"><span style="color:#374151;font-size:12px;">R:R</span><span style="font-weight:900;font-size:22px;color:{bc3};">{rr}</span></div></div>', unsafe_allow_html=True)
                with c2:
                    th="".join([f'<div style="padding:5px 0 5px 16px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;color:#c8cad0;position:relative;"><span style="position:absolute;left:0;color:#26a69a;font-weight:900;">+</span>{t}</div>' for t in ai_res.get("thesis",[])])
                    rk="".join([f'<div style="padding:5px 0 5px 16px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;color:#c8cad0;position:relative;"><span style="position:absolute;left:0;color:#ef5350;font-weight:900;">−</span>{r}</div>' for r in ai_res.get("risks",[])])
                    st.markdown(f'<div style="background:rgba(38,166,154,0.06);border:1px solid rgba(38,166,154,0.18);border-radius:10px;padding:12px;margin-bottom:6px;"><div style="font-size:11px;color:#26a69a;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Bull Thesis</div>{th}</div><div style="background:rgba(239,83,80,0.06);border:1px solid rgba(239,83,80,0.18);border-radius:10px;padding:12px;"><div style="font-size:11px;color:#ef5350;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Risk Factors</div>{rk}</div>', unsafe_allow_html=True)

            with tabs[7]:
                try:
                    qr2=fund.get("quant_real",{}); fh2=fund.get("fund_health",{})
                    ai_aug=dict(ai_res)
                    if qr2.get("ok"): ai_aug["real_quant"]=qr2
                    if fh2.get("ok"): ai_aug["real_fund_health"]=fh2
                    wp = _full_report_html(sym, name, {}, fund, ai_aug)
                    components.html(wp, height=4400, scrolling=True)
                except Exception as e:
                    st.error(f"Report error: {e}")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("🔄 Re-Analyse", key="pd_re2", type="primary"): st.session_state.pd_ai=None; st.rerun()
                with c2:
                    txt = f"FinSage Personal Dashboard\n{name} ({sym})\n{datetime.now().strftime('%B %d, %Y')}\nRating:{ai_res.get('rating')} Bias:{ai_res.get('bias')} Conf:{ai_res.get('confidence')}%\nEntry:{entry_v:.4f} Stop:{stop_v:.4f} T1:{t1_v:.4f}\nR:R:{rr}\n{ai_res.get('summary','')}\nDISCLAIMER: Educational only."
                    st.download_button("📥 Download", txt, f"finsage_{sym.replace('.','_').replace('^','')}.txt","text/plain",key="pd_dl")

                # ── AI SCANNING REPORT + SOCIAL ──
                st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.06);margin:14px 0;'/>", unsafe_allow_html=True)
                try:
                    from scanning_report import render_scanning_report
                    _sr_data = st.session_state.get("pd_analysis_data")
                    if _sr_data:
                        render_scanning_report(sym, name, _sr_data["candles"], _sr_data["indicators"],
                            _sr_data["support_resistance"], _sr_data["patterns"],
                            _sr_data["overall_bias"], ai_res)
                except Exception as _sre:
                    st.warning(f"Scanning report: {_sre}")

        # ══════════════════════════════════════════════════════════════════
        # FULL REPORT MODE
        # ══════════════════════════════════════════════════════════════════
        elif "Full Report" in mode_sel:
            if st.session_state.pd_ai is None:
                with st.spinner(f"🤖 Generating full report for {name}..."):
                    try:
                        from pro_chart import _ohlcv, _compute_tech
                        _df2 = _ohlcv(sym, period_sel, interval_sel)
                        tech2 = _compute_tech(_df2) if _df2 is not None and not _df2.empty else {}
                    except: tech2 = {}
                    fund2 = _fundamental(sym)
                    try:
                        from quant_engine import run_quant_engine
                        from fundamental_engine import run_fundamental_engine
                        import yfinance as _yf_q3
                        _bdf3 = _yf_q3.Ticker("^NSEI" if ".NS" in sym else "^GSPC").history(period="6mo",interval="1d")
                        fund2["quant_real"] = run_quant_engine(_df2 if _df2 is not None and not _df2.empty else None, _bdf3 if not _bdf3.empty else None)
                        fund2["fund_health"] = run_fundamental_engine(sym)
                    except: fund2["quant_real"]={};fund2["fund_health"]={}
                    ai_res2 = _master_analysis(sym, name, tech2, fund2)
                st.session_state.pd_ai=ai_res2; st.session_state.pd_fund=fund2
            else:
                ai_res2=st.session_state.pd_ai; fund2=st.session_state.pd_fund

            # Full Screen Report
            col_rep, col_ctrl = st.columns([5,1])
            with col_ctrl:
                if st.button("🔄 Re-generate", key="pd_regen", type="primary", use_container_width=True):
                    st.session_state.pd_ai=None; st.rerun()
                ai_aug2=dict(ai_res2)
                if fund2.get("quant_real",{}).get("ok"): ai_aug2["real_quant"]=fund2["quant_real"]
                if fund2.get("fund_health",{}).get("ok"): ai_aug2["real_fund_health"]=fund2["fund_health"]
                txt2 = f"FinSage Full Report\n{name} ({sym})\n{datetime.now().strftime('%B %d, %Y')}\nRating:{ai_res2.get('rating')} Bias:{ai_res2.get('bias')} Conf:{ai_res2.get('confidence')}%\nEntry:{ai_res2.get('entry',0):.4f} Stop:{ai_res2.get('stop',0):.4f}\nR:R:{ai_res2.get('rr','—')}\n{ai_res2.get('summary','')}\nDISCLAIMER: Educational only."
                st.download_button("📥 Download", txt2, f"finsage_report_{sym.replace('.','_').replace('^','')}.txt","text/plain",key="pd_dl2")
            with col_rep:
                try:
                    wp2 = _full_report_html(sym, name, tech2, fund2, ai_aug2)
                    components.html(wp2, height=4800, scrolling=True)
                except Exception as e:
                    st.error(f"Report error: {e}"); import traceback; st.code(traceback.format_exc())

                # Scanning Report + Social below full report
                st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.06);margin:14px 0;'/>", unsafe_allow_html=True)
                try:
                    from scanning_report import render_scanning_report
                    _sr2_data = st.session_state.get("pd_analysis_data")
                    if _sr2_data:
                        render_scanning_report(sym, name, _sr2_data["candles"], _sr2_data["indicators"],
                            _sr2_data["support_resistance"], _sr2_data["patterns"],
                            _sr2_data["overall_bias"], ai_res2)
                    else:
                        from chart_analysis_engine import full_analysis as _cae2
                        import yfinance as _yf_s2, pandas as _pd_s2
                        _r2 = _yf_s2.download(sym, interval=interval_sel, period=period_sel, progress=False, auto_adjust=True)
                        if _r2 is not None and not _r2.empty:
                            if isinstance(_r2.columns, _pd_s2.MultiIndex): _r2.columns=[c[0] for c in _r2.columns]
                            _df_s2 = _r2.reset_index()
                            _tc2 = "Date" if "Date" in _df_s2.columns else "Datetime"
                            _df_s2 = _df_s2.rename(columns={_tc2:"time","Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
                            _df_s2["time"] = _df_s2["time"].astype(str)
                            _df_s2 = _df_s2[["time","open","high","low","close","volume"]].dropna()
                            if len(_df_s2)>=10:
                                _sd2 = _cae2(_df_s2, sym)
                                render_scanning_report(sym, name, _sd2["candles"], _sd2["indicators"],
                                    _sd2["support_resistance"], _sd2["patterns"], _sd2["overall_bias"], ai_res2)
                except Exception as _sre2:
                    st.warning(f"Scanning report: {_sre2}")



def _get_logo_url(sym: str) -> str:
    """Get logo URL for any symbol — with dynamic clearbit fallback"""
    # Static map for common ones
    LOGOS = {
        "RELIANCE.NS":"https://logo.clearbit.com/ril.com",
        "TCS.NS":"https://logo.clearbit.com/tcs.com",
        "HDFCBANK.NS":"https://logo.clearbit.com/hdfcbank.com",
        "INFY.NS":"https://logo.clearbit.com/infosys.com",
        "ICICIBANK.NS":"https://logo.clearbit.com/icicibank.com",
        "SBIN.NS":"https://logo.clearbit.com/onlinesbi.com",
        "WIPRO.NS":"https://logo.clearbit.com/wipro.com",
        "TATAMOTORS.NS":"https://logo.clearbit.com/tatamotors.com",
        "BAJFINANCE.NS":"https://logo.clearbit.com/bajajfinserv.in",
        "ADANIENT.NS":"https://logo.clearbit.com/adani.com",
        "HINDUNILVR.NS":"https://logo.clearbit.com/hul.co.in",
        "KOTAKBANK.NS":"https://logo.clearbit.com/kotak.com",
        "AXISBANK.NS":"https://logo.clearbit.com/axisbank.com",
        "LT.NS":"https://logo.clearbit.com/larsentoubro.com",
        "MARUTI.NS":"https://logo.clearbit.com/marutisuzuki.com",
        "SUNPHARMA.NS":"https://logo.clearbit.com/sunpharma.com",
        "TITAN.NS":"https://logo.clearbit.com/tanishq.co.in",
        "NESTLEIND.NS":"https://logo.clearbit.com/nestle.in",
        "ASIANPAINT.NS":"https://logo.clearbit.com/asianpaints.com",
        "ULTRACEMCO.NS":"https://logo.clearbit.com/ultratechcement.com",
        "AAPL":"https://logo.clearbit.com/apple.com",
        "TSLA":"https://logo.clearbit.com/tesla.com",
        "NVDA":"https://logo.clearbit.com/nvidia.com",
        "MSFT":"https://logo.clearbit.com/microsoft.com",
        "GOOGL":"https://logo.clearbit.com/google.com",
        "GOOG":"https://logo.clearbit.com/google.com",
        "META":"https://logo.clearbit.com/meta.com",
        "AMZN":"https://logo.clearbit.com/amazon.com",
        "NFLX":"https://logo.clearbit.com/netflix.com",
        "JPM":"https://logo.clearbit.com/jpmorganchase.com",
        "UBER":"https://logo.clearbit.com/uber.com",
        "SNAP":"https://logo.clearbit.com/snapchat.com",
        "SPOT":"https://logo.clearbit.com/spotify.com",
        "PYPL":"https://logo.clearbit.com/paypal.com",
        "AMD":"https://logo.clearbit.com/amd.com",
        "INTC":"https://logo.clearbit.com/intel.com",
        "BTC-USD":"https://assets.coingecko.com/coins/images/1/large/bitcoin.png",
        "ETH-USD":"https://assets.coingecko.com/coins/images/279/large/ethereum.png",
        "SOL-USD":"https://assets.coingecko.com/coins/images/4128/large/solana.png",
        "BNB-USD":"https://assets.coingecko.com/coins/images/825/large/binance-coin-logo.png",
        "XRP-USD":"https://assets.coingecko.com/coins/images/44/large/xrp-symbol-white-128.png",
        "DOGE-USD":"https://assets.coingecko.com/coins/images/5/large/dogecoin.png",
    }
    if sym in LOGOS:
        return LOGOS[sym]
    # Dynamic: clearbit with domain guess
    s = sym.upper().replace(".NS","").replace(".BO","").replace("-USD","").replace("^","").replace("=F","")
    # Try some common Indian companies
    domain_map = {
        "BAJAJ-AUTO":"bajaj-auto.com","BAJAJFINSV":"bajajfinserv.in","BPCL":"bharatpetroleum.com",
        "COALINDIA":"coalindia.in","DIVISLAB":"divislaboratories.com","DRREDDY":"drreddys.com",
        "EICHERMOT":"eicher.in","GRASIM":"grasim.com","HCLTECH":"hcltech.com",
        "HEROMOTOCO":"heromotocorp.com","HINDALCO":"hindalco.com","IOC":"iocl.com",
        "ITC":"itcportal.com","JSWSTEEL":"jsw.in","M&M":"mahindra.com",
        "NTPC":"ntpc.co.in","ONGC":"ongcindia.com","POWERGRID":"powergridindia.com",
        "SBILIFE":"sbilife.co.in","SHREECEM":"shreecement.com","TATASTEEL":"tatasteel.com",
        "TECHM":"techm.com","TRENT":"trent.in","UPL":"upl-ltd.com",
    }
    if s in domain_map:
        return f"https://logo.clearbit.com/{domain_map[s]}"
    return ""


def _build_lwc_analyzer_html(candles, indicators, sr_zones, patterns, bias, sym, name, fullscreen=False):
    """Build the Free Auto Chart Analyzer HTML with LWC — TradingView style"""
    import json as _json

    candle_data = _json.dumps([
        {"time": c["time"][:10], "open": float(c["open"]), "high": float(c["high"]),
         "low": float(c["low"]), "close": float(c["close"])}
        for c in candles if c.get("time")
    ])
    volume_data = _json.dumps([
        {"time": c["time"][:10], "value": float(c["volume"]),
         "color": "rgba(63,208,160,0.5)" if float(c["close"])>=float(c["open"]) else "rgba(255,93,108,0.5)"}
        for c in candles if c.get("time")
    ])
    sma20_data = _json.dumps([
        {"time": c["time"][:10], "value": float(i["sma20"])}
        for c,i in zip(candles, indicators)
        if c.get("time") and i.get("sma20") is not None and str(i.get("sma20",""))!="nan"
    ])
    sma50_data = _json.dumps([
        {"time": c["time"][:10], "value": float(i["sma50"])}
        for c,i in zip(candles, indicators)
        if c.get("time") and i.get("sma50") is not None and str(i.get("sma50",""))!="nan"
    ])
    rsi_data = _json.dumps([
        {"time": c["time"][:10], "value": float(i["rsi14"])}
        for c,i in zip(candles, indicators)
        if c.get("time") and i.get("rsi14") is not None and str(i.get("rsi14",""))!="nan"
    ])
    macd_data = _json.dumps([
        {"time": c["time"][:10], "value": float(i["macd_hist"])}
        for c,i in zip(candles, indicators)
        if c.get("time") and i.get("macd_hist") is not None and str(i.get("macd_hist",""))!="nan"
    ])
    bb_upper_data = _json.dumps([
        {"time": c["time"][:10], "value": float(i["bb_upper"])}
        for c,i in zip(candles, indicators)
        if c.get("time") and i.get("bb_upper") is not None and str(i.get("bb_upper",""))!="nan"
    ])
    bb_lower_data = _json.dumps([
        {"time": c["time"][:10], "value": float(i["bb_lower"])}
        for c,i in zip(candles, indicators)
        if c.get("time") and i.get("bb_lower") is not None and str(i.get("bb_lower",""))!="nan"
    ])

    sr_lines_js = ""
    for z in sr_zones:
        color = "#3fd0a0" if z["type"]=="support" else "#ff5d6c"
        label = f"{'S' if z['type']=='support' else 'R'} ({z['strength']}x)"
        sr_lines_js += f"""
        mainSeries.createPriceLine({{
            price: {z['price']},
            color: '{color}',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: '{label}',
        }});"""

    markers_js = ""
    if patterns:
        marker_list = []
        for p in patterns:
            idx = p["index"]
            if 0 <= idx < len(candles):
                t = candles[idx]["time"][:10]
                color = "#3fd0a0" if p["bias"]=="bullish" else "#ff5d6c" if p["bias"]=="bearish" else "#e8b34d"
                pos = "belowBar" if p["bias"]=="bullish" else "aboveBar" if p["bias"]=="bearish" else "inBar"
                shape = "arrowUp" if p["bias"]=="bullish" else "arrowDown" if p["bias"]=="bearish" else "circle"
                marker_list.append({"time":t,"position":pos,"color":color,"shape":shape,"text":p["name"]})
        if marker_list:
            markers_js = f"mainSeries.setMarkers({_json.dumps(marker_list)});"

    bias_class = "bullish" if bias=="bullish" else "bearish" if bias=="bearish" else "neutral"
    bias_label = "📈 Overall Bias: Bullish" if bias=="bullish" else "📉 Overall Bias: Bearish" if bias=="bearish" else "➖ Overall Bias: Neutral"
    chart_height = "calc(100vh - 80px)" if fullscreen else "480px"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{{--bg:#0b0e14;--panel:#11151c;--panel-2:#161b24;--border:#232a36;--text:#e7ecf3;--muted:#8893a3;--accent:#3fd0a0;--accent-2:#ff5d6c;--gold:#e8b34d;--mono:'Courier New',monospace;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,Segoe UI,sans-serif;}}
.header{{display:flex;align-items:center;gap:10px;padding:8px 14px;border-bottom:1px solid var(--border);background:var(--panel);flex-wrap:wrap;}}
.header-title{{font-size:14px;font-weight:700;display:flex;align-items:center;gap:6px;}}
.dot{{width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 6px var(--accent);}}
.controls{{display:flex;gap:6px;margin-left:auto;flex-wrap:wrap;align-items:center;}}
.ctrl-btn{{background:rgba(63,208,160,0.15);color:var(--accent);border:1px solid var(--accent)44;padding:4px 10px;border-radius:5px;font-size:11px;cursor:pointer;font-family:var(--mono);transition:all .15s;}}
.ctrl-btn:hover{{background:rgba(63,208,160,0.25);}}
.ctrl-btn.active{{background:rgba(63,208,160,0.25);border-color:var(--accent);}}
.chart-wrap{{position:relative;width:100%;height:{chart_height};}}
#mainChart{{position:absolute;inset:0;}}
.vol-wrap{{height:80px;border-top:1px solid var(--border);position:relative;}}
#volChart{{position:absolute;inset:0;}}
.rsi-wrap{{height:70px;border-top:1px solid var(--border);position:relative;}}
#rsiChart{{position:absolute;inset:0;}}
.macd-wrap{{height:70px;border-top:1px solid var(--border);position:relative;display:none;}}
#macdChart{{position:absolute;inset:0;}}
.bias-strip{{padding:6px 14px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--border);font-size:12px;}}
.bias-bullish{{color:var(--accent);background:rgba(63,208,160,0.08);}}
.bias-bearish{{color:var(--accent-2);background:rgba(255,93,108,0.08);}}
.bias-neutral{{color:var(--gold);background:rgba(232,179,77,0.08);}}
.legend{{position:absolute;top:8px;left:10px;z-index:10;background:rgba(11,14,20,0.75);padding:4px 8px;border-radius:5px;font-size:11px;font-family:var(--mono);display:flex;gap:10px;flex-wrap:wrap;pointer-events:none;}}
.leg-item{{display:flex;align-items:center;gap:4px;}}
.leg-dot{{width:8px;height:2px;border-radius:1px;}}
</style>
</head>
<body>
<div class="header">
  <div class="header-title"><span class="dot"></span>{name} ({sym})</div>
  <div class="controls">
    <button class="ctrl-btn active" id="btnSMA" onclick="toggleLayer('sma')">SMA 20/50</button>
    <button class="ctrl-btn" id="btnBB" onclick="toggleLayer('bb')">Bollinger</button>
    <button class="ctrl-btn active" id="btnSR" onclick="toggleLayer('sr')">S/R Lines</button>
    <button class="ctrl-btn active" id="btnPat" onclick="toggleLayer('pat')">Patterns</button>
    <button class="ctrl-btn" id="btnMACD" onclick="toggleLayer('macd')">MACD</button>
    <button class="ctrl-btn" onclick="fitAll()">Fit</button>
  </div>
</div>
<div class="bias-strip bias-{bias_class}"><b>{bias_label}</b><span style="color:var(--muted);margin-left:auto;font-size:11px;">{len(sr_zones)} S/R zones · {len(patterns)} patterns</span></div>
<div class="chart-wrap" id="chartWrap">
  <div id="mainChart"></div>
  <div class="legend" id="legend">
    <div class="leg-item"><div class="leg-dot" style="background:#e8b34d;height:2px;width:12px;"></div><span>SMA20</span></div>
    <div class="leg-item"><div class="leg-dot" style="background:#7aa2ff;height:2px;width:12px;"></div><span>SMA50</span></div>
    <div class="leg-item"><div class="leg-dot" style="background:rgba(63,208,160,0.4);height:6px;width:12px;border-radius:1px;"></div><span>BB</span></div>
  </div>
</div>
<div class="vol-wrap" id="volWrap"><div id="volChart"></div></div>
<div class="rsi-wrap" id="rsiWrap"><div id="rsiChart"></div></div>
<div class="macd-wrap" id="macdWrap"><div id="macdChart"></div></div>

<script>
const CO = {{layout:{{background:{{color:"transparent"}},textColor:"#8893a3"}},grid:{{vertLines:{{color:"#1a2029"}},horzLines:{{color:"#1a2029"}}}},timeScale:{{borderColor:"#232a36"}},rightPriceScale:{{borderColor:"#232a36"}},crosshair:{{mode:LightweightCharts.CrosshairMode.Normal}}}};

const mainChart = LightweightCharts.createChart(document.getElementById("mainChart"), CO);
const mainSeries = mainChart.addCandlestickSeries({{upColor:"#3fd0a0",downColor:"#ff5d6c",borderUpColor:"#3fd0a0",borderDownColor:"#ff5d6c",wickUpColor:"#3fd0a0",wickDownColor:"#ff5d6c"}});
const sma20Series = mainChart.addLineSeries({{color:"#e8b34d",lineWidth:1,title:"SMA20"}});
const sma50Series = mainChart.addLineSeries({{color:"#7aa2ff",lineWidth:1,title:"SMA50"}});
const bbUpperSeries = mainChart.addLineSeries({{color:"rgba(63,208,160,0.35)",lineWidth:1,lineStyle:2,title:"BB+"}});
const bbLowerSeries = mainChart.addLineSeries({{color:"rgba(63,208,160,0.35)",lineWidth:1,lineStyle:2,title:"BB-"}});

const volChart = LightweightCharts.createChart(document.getElementById("volChart"),{{...CO,timeScale:{{visible:false}}}});
const volSeries = volChart.addHistogramSeries({{priceFormat:{{type:"volume"}}}});

const rsiChart = LightweightCharts.createChart(document.getElementById("rsiChart"),{{...CO,timeScale:{{borderColor:"#232a36"}}}});
const rsiSeries = rsiChart.addLineSeries({{color:"#c792ea",lineWidth:1.5}});
rsiChart.addLineSeries({{color:"rgba(255,93,108,0.35)",lineWidth:1,lineStyle:2}}).setData([]);
const rsi70 = rsiChart.addLineSeries({{color:"rgba(255,93,108,0.25)",lineWidth:1,lineStyle:2}});
const rsi30 = rsiChart.addLineSeries({{color:"rgba(63,208,160,0.25)",lineWidth:1,lineStyle:2}});

const macdChart = LightweightCharts.createChart(document.getElementById("macdChart"),{{...CO,timeScale:{{visible:false}}}});
const macdSeries = macdChart.addHistogramSeries({{priceFormat:{{type:"price"}}}});

// Data
mainSeries.setData({candle_data});
volSeries.setData({volume_data});
sma20Series.setData({sma20_data});
sma50Series.setData({sma50_data});
rsiSeries.setData({rsi_data});
macdSeries.setData({macd_data});
bbUpperSeries.setData({bb_upper_data});
bbLowerSeries.setData({bb_lower_data});

// RSI level lines (need data range)
const rsiD = {rsi_data};
if(rsiD.length){{
  rsi70.setData(rsiD.map(d=>({{time:d.time,value:70}})));
  rsi30.setData(rsiD.map(d=>({{time:d.time,value:30}})));
}}

// S/R Lines
{sr_lines_js}

// Pattern Markers
{markers_js}

// Sync timescales
function syncTS(charts){{
  charts.forEach((c,i)=>{{
    c.timeScale().subscribeVisibleLogicalRangeChange(r=>{{
      if(!r)return;
      charts.forEach((other,j)=>{{ if(i!==j) try{{other.timeScale().setVisibleLogicalRange(r);}}catch(e){{}} }});
    }});
  }});
}}
const allCharts = [mainChart,volChart,rsiChart,macdChart];
syncTS(allCharts);

// Resize
function resizeAll(){{
  const cw=document.getElementById("chartWrap"),vw=document.getElementById("volWrap"),rw=document.getElementById("rsiWrap"),mw=document.getElementById("macdWrap");
  mainChart.resize(cw.clientWidth,cw.clientHeight);
  volChart.resize(vw.clientWidth,80);
  rsiChart.resize(rw.clientWidth,70);
  macdChart.resize(mw.clientWidth,70);
}}
window.addEventListener("resize",resizeAll);
setTimeout(resizeAll,100);

// Toggle layers
let layers = {{sma:true,bb:false,sr:true,pat:true,macd:false}};
function toggleLayer(l){{
  layers[l]=!layers[l];
  document.getElementById("btn"+l.charAt(0).toUpperCase()+l.slice(1)).classList.toggle("active",layers[l]);
  if(l==='sma'){{sma20Series.applyOptions({{visible:layers[l]}});sma50Series.applyOptions({{visible:layers[l]}});}}
  if(l==='bb'){{bbUpperSeries.applyOptions({{visible:layers[l]}});bbLowerSeries.applyOptions({{visible:layers[l]}});}}
  if(l==='macd'){{document.getElementById("macdWrap").style.display=layers[l]?"block":"none";setTimeout(resizeAll,50);}}
  if(l==='pat'){{ mainSeries.setMarkers(layers[l] ? {_json.dumps([{"time":candles[p["index"]]["time"][:10],"position":"belowBar" if p["bias"]=="bullish" else "aboveBar" if p["bias"]=="bearish" else "inBar","color":"#3fd0a0" if p["bias"]=="bullish" else "#ff5d6c" if p["bias"]=="bearish" else "#e8b34d","shape":"arrowUp" if p["bias"]=="bullish" else "arrowDown" if p["bias"]=="bearish" else "circle","text":p["name"]} for p in patterns if 0<=p["index"]<len(candles)]) if patterns else "[]"} : []); }}
}}
// Hide BB by default
bbUpperSeries.applyOptions({{visible:false}});bbLowerSeries.applyOptions({{visible:false}});

function fitAll(){{allCharts.forEach(c=>c.timeScale().fitContent());}}
fitAll();
</script>
</body>
</html>"""

