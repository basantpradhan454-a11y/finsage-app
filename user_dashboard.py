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
    "win_rate":"{round(55+conf*0.15,0):.0f}%",
    "expected_value":"{round((t1-entry)*0.6-(entry-sl)*0.4,4):.4f}",
    "setup_quality":"A+/A/B/C grade",
    "probability_bullish":"{conf}%",
    "statistical_edge":"describe edge in numbers"
  }},

  "indicator":{{
    "view":"All indicator confluence: RSI+StochRSI+MACD+BB+EMA+VWAP — what they ALL say together. 4-5 sentences.",
    "rsi_read":"RSI {rsi:.0f} — full interpretation with overbought/oversold context",
    "macd_read":"MACD histogram at {tech.get('macd_h',0):.4f} — direction and momentum",
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
    import json

    st.markdown("""<style>
    /* ── HIDE STREAMLIT CHROME ── */
    header[data-testid="stHeader"],footer,
    div[data-testid="stDecoration"],div[data-testid="stToolbar"],
    div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}

    /* ── TRANSPARENT BACKGROUND ── */
    .stApp,[data-testid="stAppViewContainer"],[data-testid="stMainBlockContainer"],
    .main,.block-container,[data-testid="stVerticalBlock"],
    section[data-testid="stMain"]{
        background:transparent!important;
    }
    .block-container{padding:0 0 20px 0!important;max-width:100vw!important;}

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"]{
        gap:4px;background:rgba(13,17,28,0.7);
        backdrop-filter:blur(10px);padding:4px;border-radius:10px;
        border:1px solid rgba(255,255,255,0.06);}
    .stTabs [data-baseweb="tab"]{
        background:transparent;border-radius:8px;
        color:#6a6e7a;font-size:12px;padding:5px 12px;}
    .stTabs [aria-selected="true"]{
        background:rgba(41,98,255,0.2)!important;color:#4a9eff!important;}
    div[data-testid="stVerticalBlock"]{gap:4px!important;}

    /* ── GLASS CARDS (use this class everywhere) ── */
    .g-card{
        background:rgba(13,17,28,0.75)!important;
        backdrop-filter:blur(18px)!important;
        border:1px solid rgba(255,255,255,0.07)!important;
        border-radius:12px!important;}

    /* ── STREAMLIT WIDGETS ── */
    div[data-testid="stTextInput"] input{
        background:rgba(13,17,28,0.7)!important;
        border:1px solid rgba(255,255,255,0.08)!important;
        color:#d1d4dc!important;border-radius:8px!important;}
    div[data-baseweb="select"]{
        background:rgba(13,17,28,0.7)!important;border-radius:8px!important;}
    div[data-baseweb="select"] *{color:#d1d4dc!important;}
    div[data-testid="stRadio"] label{color:#9598a1!important;font-size:12px!important;}
    button[kind="secondary"]{
        background:rgba(255,255,255,0.04)!important;
        border:1px solid rgba(255,255,255,0.08)!important;
        color:#9598a1!important;border-radius:8px!important;}
    button[kind="primary"]{border-radius:8px!important;}
    </style>""", unsafe_allow_html=True)

    # ── STATE INIT ────────────────────────────────────────────────────
    for k, v in [
        ("pd_favs",    list(DEFAULT_FAVS)),
        ("pd_sel",     None),
        ("pd_ai",      None),
        ("pd_fund",    {}),
        ("pd_srch",    ""),
        ("pd_srch_res",[]),
        ("pd_tf",      "1D"),
        ("pd_trader",  "all"),
        ("pd_mode",    "tv"),
        ("pd_view",    "single"),   # "single" or "grid6"
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state.pd_sel is None and st.session_state.pd_favs:
        st.session_state.pd_sel = st.session_state.pd_favs[0]

    favs = st.session_state.pd_favs
    sel  = st.session_state.pd_sel or DEFAULT_FAVS[0]
    sym  = sel["sym"]; name = sel["name"]

    # ── TOP BAR ───────────────────────────────────────────────────────
    d   = _price_fast(sym)
    pr  = d.get("price", 0); chg = d.get("chg", 0)
    cc  = "#26a69a" if chg >= 0 else "#ef5350"
    pr_s= f"{pr:,.4f}" if pr < 10 else f"{pr:,.2f}" if pr > 0 else "—"

    st.markdown(f"""
    <div style="background:rgba(8,11,18,0.92);backdrop-filter:blur(24px);
    border-bottom:1px solid rgba(255,255,255,0.06);padding:8px 18px;
    display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:4px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:36px;height:36px;background:linear-gradient(135deg,#2962ff,#a855f7);
          border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;">👤</div>
        <div>
          <div style="color:#fff;font-weight:900;font-size:15px;">Personal <span style="color:#2962ff;">Dashboard</span></div>
          <div style="color:#374151;font-size:10px;">AI-powered · All 6 trader styles · Auto-draws everything</div>
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

    # ── MAIN LAYOUT ───────────────────────────────────────────────────
    left_col, chart_col = st.columns([1, 4], gap="small")

    # ══════════════════════════════════════════════════════════════════
    # LEFT PANEL
    # ══════════════════════════════════════════════════════════════════
    with left_col:
        # Search
        srch = st.text_input("", "", placeholder="🔍 Search any stock / crypto...",
                             key="pd_srch_inp", label_visibility="collapsed")
        if srch != st.session_state.pd_srch:
            st.session_state.pd_srch = srch
            if srch.strip():
                with st.spinner("..."): st.session_state.pd_srch_res = _srch(srch)
            else: st.session_state.pd_srch_res = []

        for item in st.session_state.pd_srch_res[:6]:
            d2  = _price_fast(item["sym"]); pr2 = d2.get("price", 0); chg2 = d2.get("chg", 0)
            cc2 = "#26a69a" if chg2 >= 0 else "#ef5350"
            c1, c2 = st.columns([3, 1])
            with c1:
                if st.button(f"+ {item['name'][:14]}", key=f"padd_{item['sym']}", use_container_width=True):
                    if not any(f["sym"] == item["sym"] for f in st.session_state.pd_favs):
                        st.session_state.pd_favs.append({"sym":item["sym"],"name":item["name"],"type":item["type"]})
                        st.toast(f"⭐ {item['name']} added!")
                    st.session_state.pd_sel = {"sym":item["sym"],"name":item["name"],"type":item["type"]}
                    st.session_state.pd_ai  = None
                    st.session_state.pd_srch = ""; st.session_state.pd_srch_res = []
                    st.rerun()
            with c2:
                st.markdown(f'<div style="font-size:10px;color:{cc2};text-align:right;padding-top:6px;">{pr2:.2f}</div>', unsafe_allow_html=True)

        # Watchlist header
        st.markdown("""<div style="display:flex;padding:4px 5px;font-size:8px;color:#374151;
        font-weight:700;background:rgba(255,255,255,0.03);border-radius:6px 6px 0 0;
        text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid rgba(255,255,255,0.04);">
          <span style="flex:1;">Favourite</span>
          <span style="width:62px;text-align:right;">Price</span>
          <span style="width:38px;text-align:right;">Chg%</span>
          <span style="width:14px;"></span>
        </div>""", unsafe_allow_html=True)

        to_remove = None
        for item in list(favs):
            d3   = _price_fast(item["sym"]); pr3 = d3.get("price", 0); chg3 = d3.get("chg", 0)
            cc3  = "#26a69a" if chg3 >= 0 else "#ef5350"
            is_s = sel["sym"] == item["sym"]
            pr3s = f"{pr3:,.4f}" if 0 < pr3 < 10 else f"{pr3:,.2f}" if pr3 > 0 else "—"
            chg3s= f"{chg3:+.1f}%" if pr3 > 0 else "—"
            ti   = {"stock":"📈","crypto":"🪙","index":"📊","commodity":"🥇"}.get(item["type"],"📈")
            bc1, bc2 = st.columns([5, 1])
            with bc1:
                if st.button(f"{ti} {item['name'][:13]}", key=f"pfav_{item['sym']}",
                             use_container_width=True, type="primary" if is_s else "secondary"):
                    st.session_state.pd_sel  = item
                    st.session_state.pd_ai   = None; st.rerun()
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
            st.session_state.pd_favs = [f for f in st.session_state.pd_favs if f["sym"] != to_remove]
            if sel["sym"] == to_remove and st.session_state.pd_favs:
                st.session_state.pd_sel = st.session_state.pd_favs[0]
                st.session_state.pd_ai  = None
            st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        # Sector Quick Add
        st.markdown('<div style="font-size:9px;color:#374151;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px;">Quick Add</div>', unsafe_allow_html=True)
        sec = st.selectbox("", list(SECTOR_STOCKS.keys()), key="pd_sec", label_visibility="collapsed")
        for s in SECTOR_STOCKS[sec][:5]:
            d4 = _price_fast(s); pr4 = d4.get("price", 0); chg4 = d4.get("chg", 0)
            cc4 = "#26a69a" if chg4 >= 0 else "#ef5350"
            already = any(f["sym"] == s for f in st.session_state.pd_favs)
            lbl = ("✓ " if already else "+ ") + s.replace(".NS","").replace("-USD","").replace("^","")
            if st.button(lbl, key=f"pqa_{s}", use_container_width=True):
                nm2 = s.replace(".NS","").replace("-USD","").replace("^","")
                if not already:
                    st.session_state.pd_favs.append({"sym":s,"name":nm2,"type":"stock"})
                    st.toast(f"⭐ {nm2} added!")
                st.session_state.pd_sel = {"sym":s,"name":nm2,"type":"stock"}
                st.session_state.pd_ai  = None; st.rerun()
            if pr4 > 0:
                st.markdown(f'<div style="display:flex;font-size:9.5px;padding:0 3px 2px;margin-top:-8px;border-bottom:1px solid rgba(255,255,255,0.03);"><span style="flex:1;color:#374151;font-size:8px;">{s}</span><span style="color:{cc4};font-family:monospace;">{pr4:.2f}</span><span style="color:{cc4};margin-left:4px;">{chg4:+.1f}%</span></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════
    # RIGHT PANEL — CHART + ANALYSIS
    # ══════════════════════════════════════════════════════════════════
    with chart_col:

        # ── VIEW TOGGLE: Single chart OR 6-chart grid ─────────────────
        v1, v2, v3, v4, v5, v6, v7 = st.columns([2, 2, 2, 2, 1, 1, 1])
        with v1:
            view = st.radio("", ["📊 Single", "🔲 6 Charts"],
                            horizontal=True, key="pd_view_r", label_visibility="collapsed")
        with v2:
            tf = st.radio("", ["1D","1H","15m","4H","1W"],
                          horizontal=True, key="pd_tf_r", index=0, label_visibility="collapsed")
        with v3:
            trader = st.selectbox("",
                ["all","price_action","smc","indicator","volume","wave","quant"],
                format_func=lambda x: {
                    "all":"🎯 All","price_action":"📊 PA","smc":"🏦 SMC",
                    "indicator":"📈 Ind","volume":"📦 Vol","wave":"🌊 Wave","quant":"🤖 Quant"}[x],
                key="pd_trader_sel", label_visibility="collapsed")
        with v4:
            mode = st.radio("", ["📺 TV","🤖 AI","🔲 6 Views"],
                            horizontal=True, key="pd_mode_r", label_visibility="collapsed")
        with v5:
            run_ai = st.button("🤖 Analyse", key="pd_run", type="primary", use_container_width=True)
        with v6:
            if st.button("🔄", key="pd_ref", use_container_width=True):
                st.session_state.pd_ai = None; st.rerun()
        with v7:
            if st.button("📺 TV", key="pd_tv_btn", use_container_width=True):
                st.session_state.pd_mode = "tv"; st.rerun()

        if run_ai:
            st.session_state.pd_ai    = None
            st.session_state.pd_trader= trader
            st.session_state.pd_mode  = "ai"
            st.rerun()

        # ════════════════════════════════════════════════════════════
        # 6-CHART GRID VIEW
        # ════════════════════════════════════════════════════════════
        if "6 Charts" in view:
            show_favs = favs[:6] if len(favs) >= 6 else (favs + DEFAULT_FAVS)[:6]
            st.markdown(f"""<div style="background:rgba(13,17,28,0.6);backdrop-filter:blur(14px);
            border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:8px 12px;margin-bottom:6px;
            display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
              <span style="color:#fff;font-weight:800;">📊 Favourite Stocks Overview</span>
              <span style="color:#374151;font-size:11px;">Click any card to open full analysis</span>
            </div>""", unsafe_allow_html=True)

            # 2 rows × 3 cols
            for row in range(2):
                cols = st.columns(3, gap="small")
                for col_idx in range(3):
                    idx = row * 3 + col_idx
                    if idx >= len(show_favs): break
                    item = show_favs[idx]
                    with cols[col_idx]:
                        d5   = _price_fast(item["sym"])
                        pr5  = d5.get("price", 0); chg5 = d5.get("chg", 0)
                        cc5  = "#26a69a" if chg5 >= 0 else "#ef5350"

                        # Load tech for this symbol
                        try:
                            from pro_chart import _ohlcv as _ov2, _compute_tech as _ct2
                            df5   = _ov2(item["sym"], "1mo", "1d")
                            tech5 = _ct2(df5) if df5 is not None and not df5.empty else {}
                        except:
                            tech5 = {}

                        sup5 = tech5.get("supports", [])
                        res5 = tech5.get("resistances", [])
                        trend5 = tech5.get("trend", "—")
                        rsi5   = tech5.get("rsi", 50)

                        # Card header
                        pr5s = f"{pr5:,.2f}" if pr5 >= 1 else f"{pr5:.4f}"
                        tc5  = "#26a69a" if trend5=="BULLISH" else "#ef5350" if trend5=="BEARISH" else "#f59e0b"
                        st.markdown(f"""<div style="background:rgba(13,17,28,0.8);backdrop-filter:blur(14px);
                        border:1px solid rgba(255,255,255,0.07);border-radius:12px;overflow:hidden;
                        cursor:pointer;transition:all .2s;">
                          <div style="padding:8px 10px;display:flex;justify-content:space-between;align-items:flex-start;border-bottom:1px solid rgba(255,255,255,0.04);">
                            <div>
                              <div style="font-size:12px;font-weight:800;color:#fff;">{item['name'][:12]}</div>
                              <div style="font-size:9.5px;color:#374151;">{item['sym'].replace('.NS','').replace('-USD','').replace('^','')}</div>
                            </div>
                            <div style="text-align:right;">
                              <div style="font-size:14px;font-weight:900;color:{cc5};font-family:'Courier New';">{pr5s}</div>
                              <div style="font-size:10px;color:{cc5};">{chg5:+.2f}%</div>
                            </div>
                          </div>
                        </div>""", unsafe_allow_html=True)

                        # Mini chart
                        mini_h = _mini_chart_html(item["sym"], item["name"], pr5, chg5, trend5, sup5, res5, height=190)
                        components.html(mini_h, height=195, scrolling=False)

                        # Stats + open button
                        st.markdown(f"""<div style="background:rgba(13,17,28,0.7);backdrop-filter:blur(10px);
                        border:1px solid rgba(255,255,255,0.05);border-radius:0 0 12px 12px;padding:5px 10px;
                        display:flex;gap:8px;align-items:center;margin-top:-4px;font-size:10px;">
                          <span style="color:#6a6e7a;">RSI <b style="color:#d1d4dc;">{rsi5:.0f}</b></span>
                          <span style="color:{tc5};font-weight:700;font-size:9px;">{trend5[:4]}</span>
                          <span style="flex:1;"></span>
                          <span style="color:#26a69a;font-size:9.5px;">S:{round(sup5[0],1) if sup5 else '—'}</span>
                          <span style="color:#ef5350;font-size:9.5px;">R:{round(res5[0],1) if res5 else '—'}</span>
                        </div>""", unsafe_allow_html=True)

                        if st.button(f"🔍 Full Analysis", key=f"pgrid_{item['sym']}", use_container_width=True):
                            st.session_state.pd_sel  = item
                            st.session_state.pd_ai   = None
                            st.rerun()

            return  # Grid view done — no further analysis below

        # ════════════════════════════════════════════════════════════
        # SINGLE CHART VIEW
        # ════════════════════════════════════════════════════════════
        tf_map = {"1D":("3mo","1d"),"1H":("1mo","1h"),"15m":("5d","15m"),
                  "4H":("6mo","1d"),"1W":("2y","1wk"),"1M":("5y","1mo")}
        period, interval = tf_map.get(tf, ("3mo","1d"))

        with st.spinner(f"Loading {name}..."):
            from pro_chart import _ohlcv, _compute_tech
            df   = _ohlcv(sym, period, interval)
            tech = _compute_tech(df) if df is not None and not df.empty else {}

        if df.empty:
            st.error(f"❌ No data for `{sym}` — try a different symbol"); return

        use_ai   = "🤖 AI"    in mode or st.session_state.pd_mode == "ai"
        use_6v   = "🔲 6 Views" in mode

        # ── TradingView Mode ─────────────────────────────────────────
        if not use_ai:
            tv_s  = _to_tv(sym)
            tv_tf = {"1D":"D","1H":"60","15m":"15","4H":"240","1W":"W","1M":"M"}.get(tf,"D")
            tv_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#080b12;width:100%;height:640px;overflow:hidden;}}
</style></head><body>
<div id="tc" style="width:100%;height:640px;"></div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>
try{{
new TradingView.widget({{
  "autosize":false,"width":"100%","height":640,
  "symbol":"{tv_s}","interval":"{tv_tf}",
  "timezone":"Asia/Kolkata","theme":"dark","style":"1","locale":"en",
  "toolbar_bg":"#080b12","enable_publishing":false,
  "container_id":"tc","allow_symbol_change":true,"withdateranges":true,
  "studies":["RSI@tv-basicstudies","MACD@tv-basicstudies","Volume@tv-basicstudies","BB@tv-basicstudies"],
  "overrides":{{
    "mainSeriesProperties.candleStyle.upColor":"#26a69a",
    "mainSeriesProperties.candleStyle.downColor":"#ef5350",
    "mainSeriesProperties.candleStyle.borderUpColor":"#26a69a",
    "mainSeriesProperties.candleStyle.borderDownColor":"#ef5350",
    "mainSeriesProperties.candleStyle.wickUpColor":"rgba(38,166,154,0.7)",
    "mainSeriesProperties.candleStyle.wickDownColor":"rgba(239,83,80,0.7)",
    "paneProperties.background":"#080b12",
    "paneProperties.backgroundType":"solid",
    "paneProperties.vertGridProperties.color":"rgba(255,255,255,0.025)",
    "paneProperties.horzGridProperties.color":"rgba(255,255,255,0.025)"
  }},
  "studies_overrides":{{
    "volume.volume.color.0":"#ef535044","volume.volume.color.1":"#26a69a44",
    "RSI.plot.color":"#2962ff"
  }}
}});
}}catch(e){{
  document.getElementById('tc').innerHTML=
    '<div style="color:#ef5350;padding:20px;font-family:monospace;">TV Error: '+e.message+'<br>Symbol: {tv_s}</div>';
}}
</script></body></html>"""
            components.html(tv_html, height=654, scrolling=False)

            # Stats bar
            rsi_v  = tech.get("rsi", 50); trend = tech.get("trend","—")
            tc_    = "#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"
            sup    = tech.get("supports",[]); res = tech.get("resistances",[]); vr = tech.get("vol_ratio",1)
            perf1m = tech.get("perf1m",0); atr_v = tech.get("atr",0)
            st.markdown(f"""<div style="background:rgba(13,17,28,0.85);backdrop-filter:blur(18px);
            border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:8px 14px;margin:4px 0;
            display:flex;gap:14px;flex-wrap:wrap;align-items:center;">
              <span style="color:#fff;font-weight:800;font-size:13px;">{name}</span>
              <span style="color:{tc_};background:{tc_}18;padding:2px 10px;border-radius:16px;font-size:11px;font-weight:700;">{trend}</span>
              <span style="color:#6a6e7a;font-size:12px;">RSI <b style="color:#d1d4dc;">{rsi_v:.1f}</b></span>
              <span style="color:#6a6e7a;font-size:12px;">Vol <b style="color:#d1d4dc;">{vr:.2f}x</b></span>
              <span style="color:#6a6e7a;font-size:12px;">ATR <b style="color:#d1d4dc;">{atr_v:.4f}</b></span>
              <span style="color:#6a6e7a;font-size:12px;">Sup <b style="color:#26a69a;">{round(sup[0],2) if sup else '—'}</b></span>
              <span style="color:#6a6e7a;font-size:12px;">Res <b style="color:#ef5350;">{round(res[0],2) if res else '—'}</b></span>
              <span style="color:#6a6e7a;font-size:12px;">1M <b style="color:{'#26a69a' if perf1m>0 else '#ef5350'};">{perf1m:+.1f}%</b></span>
              <span style="margin-left:auto;color:#374151;font-size:11px;">👆 Click <b style="color:#2962ff;">🤖 Analyse</b> for AI chart with drawings</span>
            </div>""", unsafe_allow_html=True)

        # ── 6 Trader Views Grid ──────────────────────────────────────────
        if use_6v:
            if st.session_state.pd_ai is None:
                with st.spinner(f"🤖 SAGE AI: Analysing {name} for all 6 trader views..."):
                    fund   = _fundamental(sym)
                    ai_res = _master_analysis(sym, name, tech, fund)
                st.session_state.pd_ai   = ai_res
                st.session_state.pd_fund = fund
            else:
                ai_res = st.session_state.pd_ai
                fund   = st.session_state.pd_fund

            six_html = _six_trader_charts_html(df, tech, ai_res, sym, height=840)
            components.html(six_html, height=856, scrolling=False)

            # Quick summary below
            bc2 = ai_res.get("bias_color","#f59e0b")
            rat = ai_res.get("rating","HOLD")
            bias2 = ai_res.get("bias","NEUTRAL")
            conf2 = ai_res.get("confidence",65)
            summ2 = ai_res.get("summary","")[:140]
            bar_html = (
                f"<div style='background:rgba(13,17,28,0.85);backdrop-filter:blur(18px);"
                f"border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:8px 14px;"
                f"display:flex;gap:12px;flex-wrap:wrap;align-items:center;font-size:12px;'>"
                f"<span style='background:{bc2}18;color:{bc2};border:1px solid {bc2}33;"
                f"border-radius:16px;padding:3px 12px;font-weight:800;'>{rat}</span>"
                f"<span style='color:{bc2};font-weight:800;'>{bias2} · {conf2}% conf</span>"
                f"<span style='color:#9598a1;'>{summ2}</span>"
                f"<span style='margin-left:auto;font-size:11px;color:#6a6e7a;'>"
                f"<b style='color:#4a9eff;'>1</b>PA "
                f"<b style='color:#ef5350;'>2</b>SMC "
                f"<b style='color:#26a69a;'>3</b>Quant "
                f"<b style='color:#f59e0b;'>4</b>Ind "
                f"<b style='color:#a855f7;'>5</b>Vol "
                f"<b style='color:#26c6da;'>6</b>Wave"
                f"</span></div>"
            )
            st.markdown(bar_html, unsafe_allow_html=True)
            return

        # ── AI Chart Mode ─────────────────────────────────────────────
        else:
            if st.session_state.pd_ai is None:
                with st.spinner(f"🤖 SAGE AI: Analysing {name} — all 6 trader perspectives..."):
                    fund    = _fundamental(sym)
                    ai_res  = _master_analysis(sym, name, tech, fund)
                st.session_state.pd_ai   = ai_res
                st.session_state.pd_fund = fund
            else:
                ai_res = st.session_state.pd_ai
                fund   = st.session_state.pd_fund

            # Chart
            chart_html = _personal_chart_html(df, tech, ai_res, sym, height=660)
            components.html(chart_html, height=674, scrolling=False)

            # Summary bar
            bc2   = ai_res.get("bias_color","#f59e0b"); rat = ai_res.get("rating","HOLD")
            rc2   = ai_res.get("rating_color","#f59e0b"); conf = ai_res.get("confidence",65)
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

            # Analysis Tabs
            tabs = st.tabs(["📊 Price Action","🏦 SMC/ICT","🤖 Quant",
                            "📈 Indicators","📦 Volume","🌊 Wave+Fib","📋 Setup","📄 Full Report"])

            with tabs[0]:
                pa = ai_res.get("price_action", {})
                st.markdown(f"""<div style="background:rgba(26,35,126,0.1);border:1px solid rgba(26,35,126,0.3);border-radius:10px;padding:14px;margin-bottom:10px;">
                <div style="font-size:11px;color:#4a9eff;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">📊 Price Action — Clean Chart · Candles · S/R · Chart Patterns</div>
                <div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{pa.get('view','')}</div></div>""", unsafe_allow_html=True)
                c1,c2,c3 = st.columns(3)
                with c1:
                    pat_name = pa.get('pattern_detected','—'); pat_desc = pa.get('pattern_desc','')
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:8px;padding:10px;text-align:center;">
                    <div style="font-size:10px;color:#374151;text-transform:uppercase;margin-bottom:4px;">Chart Pattern</div>
                    <div style="font-size:14px;font-weight:800;color:#4a9eff;">{pat_name}</div>
                    <div style="font-size:11px;color:#9598a1;margin-top:4px;">{pat_desc[:60]}</div></div>""", unsafe_allow_html=True)
                with c2:
                    sig = pa.get('signal','WAIT'); sc = "#26a69a" if sig=="BUY" else "#ef5350" if sig=="SELL" else "#f59e0b"
                    st.markdown(f"""<div style="background:{sc}11;border:2px solid {sc}44;border-radius:8px;padding:10px;text-align:center;">
                    <div style="font-size:10px;color:#374151;text-transform:uppercase;margin-bottom:4px;">PA Signal</div>
                    <div style="font-size:22px;font-weight:900;color:{sc};">{sig}</div>
                    <div style="font-size:11px;color:{sc};margin-top:3px;">{pa.get('signal_reason','')[:50]}</div></div>""", unsafe_allow_html=True)
                with c3:
                    pats = tech.get("patterns",[])
                    if pats:
                        rows = "".join([f"<div style='font-size:11px;color:{'#26a69a' if p['type']=='BULLISH' else '#ef5350' if p['type']=='BEARISH' else '#f59e0b'};padding:2px 0;'>{'▲' if p['type']=='BULLISH' else '▼' if p['type']=='BEARISH' else '◆'} {p['name']}</div>" for p in pats[:6]])
                        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:8px;padding:10px;">
                        <div style="font-size:10px;color:#374151;text-transform:uppercase;margin-bottom:4px;">Candles Detected</div>{rows}</div>""", unsafe_allow_html=True)

            with tabs[1]:
                smc = ai_res.get("smc", {})
                st.markdown(f"""<div style="background:rgba(183,28,28,0.08);border:1px solid rgba(183,28,28,0.3);border-radius:10px;padding:14px;margin-bottom:10px;">
                <div style="font-size:11px;color:#ef5350;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">🏦 SMC/ICT — Order Blocks · FVG · Liquidity · Market Structure</div>
                <div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{smc.get('view','')}</div></div>""", unsafe_allow_html=True)
                c1,c2 = st.columns(2)
                with c1:
                    ob_items  = smc.get("ob_zones", tech.get("order_blocks",[]))
                    fvg_items = smc.get("fvg_zones", tech.get("fvg",[]))
                    ob_html   = "".join([f"<div style='font-size:11.5px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);color:#c8cad0;'>{'🟢' if 'BULL' in ob.get('type','') else '🔴'} {ob.get('type','OB')} — <span style='font-family:monospace;'>{ob.get('bot',ob.get('zone_bot',0)):.4f}–{ob.get('top',ob.get('zone_top',0)):.4f}</span></div>" for ob in ob_items[:3]])
                    fvg_html  = "".join([f"<div style='font-size:11.5px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04);color:#c8cad0;'>{'🟢' if 'BULL' in fv.get('type','') else '🔴'} FVG — <span style='font-family:monospace;'>{fv.get('bot',0):.4f}–{fv.get('top',0):.4f}</span></div>" for fv in fvg_items[:3]])
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:8px;padding:10px;margin-bottom:6px;">
                    <div style="font-size:10px;color:#ef5350;font-weight:700;text-transform:uppercase;margin-bottom:5px;">Order Blocks</div>{ob_html or '<div style="color:#6a6e7a;font-size:11px;">Toggle OB layer on chart</div>'}</div>
                    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:10px;">
                    <div style="font-size:10px;color:#2962ff;font-weight:700;text-transform:uppercase;margin-bottom:5px;">Fair Value Gaps</div>{fvg_html or '<div style="color:#6a6e7a;font-size:11px;">Toggle FVG layer on chart</div>'}</div>""", unsafe_allow_html=True)
                with c2:
                    liq = smc.get("liquidity_pools",[])
                    liq_html = "".join([f"<div style='font-size:11.5px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);color:#c8cad0;'><span style='color:{'#2962ff' if 'BUY' in lz.get('type','').upper() else '#ef5350'};'>{'🔵' if 'BUY' in lz.get('type','').upper() else '🔴'} {lz.get('type','LIQUIDITY')}</span> @ <span style='font-family:monospace;'>{lz.get('level',0):.4f}</span><br><span style='color:#6a6e7a;font-size:10px;'>{lz.get('desc','')[:50]}</span></div>" for lz in liq[:3]])
                    ms = smc.get('market_structure','—'); pd_z = smc.get('pd_zone','—')
                    sig2 = smc.get('signal','WAIT'); sc2 = "#26a69a" if sig2=="BUY" else "#ef5350" if sig2=="SELL" else "#f59e0b"
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:8px;padding:10px;margin-bottom:6px;">
                    <div style="font-size:10px;color:#f59e0b;font-weight:700;text-transform:uppercase;margin-bottom:5px;">Market Structure · PD Zone · Signal</div>
                    <div style="font-size:13px;font-weight:700;color:#d1d4dc;">{ms}</div>
                    <div style="font-size:12px;color:#9598a1;margin:3px 0;">{pd_z}</div>
                    <span style="background:{sc2}18;color:{sc2};border:1px solid {sc2}33;border-radius:12px;padding:2px 10px;font-weight:700;font-size:12px;">{sig2}</span></div>
                    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:10px;">
                    <div style="font-size:10px;color:#a855f7;font-weight:700;text-transform:uppercase;margin-bottom:5px;">Liquidity Pools</div>
                    {liq_html or '<div style="color:#6a6e7a;font-size:11px;">No major liquidity pools detected</div>'}</div>""", unsafe_allow_html=True)

            with tabs[2]:
                q = ai_res.get("quant", {})
                st.markdown(f"""<div style="background:rgba(27,94,32,0.08);border:1px solid rgba(27,94,32,0.3);border-radius:10px;padding:14px;margin-bottom:10px;">
                <div style="font-size:11px;color:#26a69a;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">🤖 Quant — Probability · Statistical Edge · Expected Value</div>
                <div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{q.get('view','')}</div></div>""", unsafe_allow_html=True)
                cols = st.columns(4)
                for i,(lbl,val,c) in enumerate([
                    ("Win Rate",q.get('win_rate','—'),"#26a69a"),
                    ("Expected Value",str(q.get('expected_value','—')),"#2962ff"),
                    ("Setup Grade",q.get('setup_quality','B'),"#f59e0b"),
                    ("Bull Prob",q.get('probability_bullish','—'),"#26a69a"),
                ]):
                    with cols[i]:
                        st.markdown(f"""<div style="background:{c}0d;border:1px solid {c}33;border-radius:8px;padding:10px;text-align:center;">
                        <div style="font-size:9.5px;color:#374151;text-transform:uppercase;margin-bottom:3px;">{lbl}</div>
                        <div style="font-size:22px;font-weight:900;color:{c};font-family:'Courier New';">{val}</div></div>""", unsafe_allow_html=True)
                st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px;margin-top:8px;font-size:13px;color:#c8cad0;">
                <b style="color:#26a69a;">Statistical Edge:</b> {q.get('statistical_edge','—')}</div>""", unsafe_allow_html=True)

            with tabs[3]:
                ind = ai_res.get("indicator", {})
                st.markdown(f"""<div style="background:rgba(230,81,0,0.08);border:1px solid rgba(230,81,0,0.3);border-radius:10px;padding:14px;margin-bottom:10px;">
                <div style="font-size:11px;color:#f59e0b;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">📈 Indicators — RSI · MACD · BB · EMA · VWAP Confluence</div>
                <div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{ind.get('view','')}</div></div>""", unsafe_allow_html=True)
                rsi_v=tech.get("rsi",50); stoch=tech.get("stoch_rsi",50); macd_h=tech.get("macd_h",0)
                e20=tech.get("ema20",0); e50=tech.get("ema50",0); e200=tech.get("ema200",0)
                p2=tech.get("price",0); vwap_v=tech.get("vwap",0); bb_u=tech.get("bb_upper",0); bb_l=tech.get("bb_lower",0); vr=tech.get("vol_ratio",1)
                inds=[
                    ("RSI 14",f"{rsi_v:.1f}","#ef5350" if rsi_v>70 else "#26a69a" if rsi_v<30 else "#d1d4dc","Overbought⚠️" if rsi_v>70 else "Oversold🎯" if rsi_v<30 else "Neutral"),
                    ("StochRSI",f"{stoch:.1f}","#ef5350" if stoch>80 else "#26a69a" if stoch<20 else "#d1d4dc","OB" if stoch>80 else "OS" if stoch<20 else "Neutral"),
                    ("MACD","Bull" if macd_h>0 else "Bear","#26a69a" if macd_h>0 else "#ef5350",f"{macd_h:.4f}"),
                    ("EMA20",f"{e20:.3f}","#26a69a" if p2>e20 else "#ef5350","Above" if p2>e20 else "Below"),
                    ("EMA50",f"{e50:.3f}","#26a69a" if p2>e50 else "#ef5350","Above" if p2>e50 else "Below"),
                    ("EMA200",f"{e200:.3f}","#26a69a" if p2>e200 else "#ef5350","Above" if p2>e200 else "Below"),
                    ("VWAP",f"{vwap_v:.3f}","#26a69a" if p2>vwap_v else "#ef5350","Above" if p2>vwap_v else "Below"),
                    ("BB%",f"{round((p2-bb_l)/(bb_u-bb_l)*100,1) if bb_u!=bb_l else 50:.0f}%","#ef5350" if p2>bb_u else "#26a69a" if p2<bb_l else "#d1d4dc","Upper" if p2>bb_u else "Lower" if p2<bb_l else "Mid"),
                    ("Volume",f"{vr:.2f}x","#2962ff" if vr>1.5 else "#d1d4dc","High" if vr>1.5 else "Normal"),
                ]
                ic = st.columns(3)
                for i,(nm,val,col,sig) in enumerate(inds):
                    with ic[i%3]:
                        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid {col}22;border-radius:8px;padding:9px;margin-bottom:5px;">
                        <div style="font-size:9.5px;color:#374151;text-transform:uppercase;">{nm}</div>
                        <div style="font-size:18px;font-weight:900;color:{col};font-family:'Courier New';">{val}</div>
                        <div style="font-size:10px;color:{col};">{sig}</div></div>""", unsafe_allow_html=True)

            with tabs[4]:
                v = ai_res.get("volume", {})
                st.markdown(f"""<div style="background:rgba(74,20,140,0.08);border:1px solid rgba(74,20,140,0.3);border-radius:10px;padding:14px;margin-bottom:10px;">
                <div style="font-size:11px;color:#a855f7;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">📦 Volume — POC · HVN · LVN · Delta · Money Flow</div>
                <div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{v.get('view','')}</div></div>""", unsafe_allow_html=True)
                c1,c2 = st.columns(2)
                with c1:
                    poc = v.get('poc_level', tech.get('vwap',0))
                    st.markdown(f"""<div style="background:rgba(41,98,255,0.08);border:1px solid rgba(41,98,255,0.3);border-radius:8px;padding:12px;text-align:center;margin-bottom:6px;">
                    <div style="font-size:10px;color:#2962ff;font-weight:700;text-transform:uppercase;">POC</div>
                    <div style="font-size:24px;font-weight:900;color:#2962ff;font-family:'Courier New';">{poc:.4f}</div>
                    <div style="font-size:11px;color:#9598a1;">{v.get('poc_significance','')[:60]}</div></div>
                    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px;">
                    <div style="font-size:10px;color:#374151;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Delta · Money Flow</div>
                    <div style="font-size:13px;font-weight:700;color:#d1d4dc;">{v.get('volume_delta','—')}</div>
                    <div style="font-size:11px;color:#9598a1;margin-top:4px;">{v.get('money_flow','')[:60]}</div></div>""", unsafe_allow_html=True)
                with c2:
                    vp = tech.get("vp",[]); max_vp = max([x["vol"] for x in vp], default=1) or 1
                    p3 = tech.get("price",0)
                    for vi in vp[:10]:
                        pct = vi["vol"]/max_vp*100; is_poc = vi["vol"]==max_vp
                        vc = "#2962ff" if is_poc else "#26a69a" if vi["price"]<p3 else "#ef5350"
                        st.markdown(f"""<div style="display:flex;align-items:center;gap:6px;margin:2px 0;">
                        <span style="width:55px;font-size:10px;color:{vc};font-family:monospace;font-weight:{'700' if is_poc else '400'};">{vi['price']:.2f}</span>
                        <div style="flex:1;background:rgba(255,255,255,0.04);border-radius:2px;height:11px;">
                          <div style="background:{vc};height:11px;border-radius:2px;width:{pct:.0f}%;opacity:{'1' if is_poc else '0.6'};"></div></div>
                        {'<span style="font-size:9px;color:#2962ff;font-weight:700;">POC</span>' if is_poc else ''}</div>""", unsafe_allow_html=True)

            with tabs[5]:
                w = ai_res.get("wave", {}); fib = tech.get("fib",{}); p4 = tech.get("price",0)
                st.markdown(f"""<div style="background:rgba(0,96,100,0.08);border:1px solid rgba(0,96,100,0.3);border-radius:10px;padding:14px;margin-bottom:10px;">
                <div style="font-size:11px;color:#26c6da;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">🌊 Elliott Wave / Gann — Wave Count · Fibonacci · Cycle</div>
                <div style="font-size:13.5px;color:#c8cad0;line-height:1.8;">{w.get('view','')}</div></div>""", unsafe_allow_html=True)
                c1,c2 = st.columns(2)
                with c1:
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:8px;padding:12px;">
                    <div style="font-size:10px;color:#374151;text-transform:uppercase;font-weight:700;margin-bottom:6px;">Wave Count</div>
                    <div style="font-size:14px;font-weight:800;color:#26c6da;">{w.get('wave_count','—')}</div>
                    <div style="font-size:12px;color:#9598a1;margin:4px 0;">{w.get('cycle_phase','—')}</div>
                    <div style="font-size:12px;color:#d1d4dc;">{w.get('next_move','')[:80]}</div></div>""", unsafe_allow_html=True)
                with c2:
                    fib_c = {"0.236":"#7986cb","0.382":"#26a69a","0.500":"#fbbf24","0.618":"#ef5350","0.786":"#e040fb"}
                    for k,v_fib in fib.items():
                        is_n = abs(v_fib-p4)/p4<0.015 if p4 else False
                        fc = fib_c.get(k,"#6a6e7a"); dist = round((v_fib-p4)/p4*100,2) if p4 else 0
                        st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;padding:5px 10px;border-radius:8px;margin:3px 0;
                        background:{'rgba(255,255,255,0.07)' if is_n else 'rgba(255,255,255,0.02)'};
                        border:{'1.5px solid '+fc if is_n else '1px solid rgba(255,255,255,0.05)'};">
                        <span style="width:55px;color:{fc};font-weight:700;font-size:12px;">Fib {k}</span>
                        <span style="flex:1;font-family:'Courier New';font-size:14px;font-weight:700;color:#d1d4dc;">{v_fib:.4f}</span>
                        <span style="font-size:10px;color:{'#26a69a' if dist<0 else '#ef5350'};">{dist:+.2f}%</span>
                        {'<span style="font-size:9px;color:'+fc+';border:1px solid '+fc+';border-radius:8px;padding:1px 5px;font-weight:700;">◀ NEAR</span>' if is_n else ''}
                        </div>""", unsafe_allow_html=True)

            with tabs[6]:
                c1,c2,c3 = st.columns(3)
                entry_v=ai_res.get("entry",0); stop_v=ai_res.get("stop",0)
                t1_v=ai_res.get("t1",0); t2_v=ai_res.get("t2",0)
                rr=ai_res.get("rr","—"); qual=ai_res.get("quality","—"); bc3=ai_res.get("bias_color","#f59e0b")
                with c1:
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px;">
                    <div style="font-size:11px;color:#374151;text-transform:uppercase;font-weight:700;margin-bottom:10px;">🎯 Trade Setup</div>
                    <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span style="color:#26a69a;font-weight:700;font-size:13px;">Entry</span><span style="color:#26a69a;font-family:'Courier New';font-size:17px;font-weight:900;">{entry_v:.4f}</span></div>
                    <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span style="color:#ef5350;font-weight:700;font-size:13px;">Stop</span><span style="color:#ef5350;font-family:'Courier New';font-size:17px;font-weight:900;">{stop_v:.4f}</span></div>
                    <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span style="color:#2962ff;">Target 1</span><span style="color:#2962ff;font-family:'Courier New';font-size:15px;font-weight:800;">{t1_v:.4f}</span></div>
                    <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span style="color:#9c27b0;">Target 2</span><span style="color:#9c27b0;font-family:'Courier New';font-size:15px;font-weight:800;">{t2_v:.4f}</span></div>
                    <div style="display:flex;justify-content:space-between;padding:10px 0 0;"><span style="color:#374151;font-size:12px;">R:R · Quality</span><span style="font-weight:900;font-size:22px;color:{bc3};">{rr}</span></div>
                    <div style="text-align:right;font-size:11px;color:#374151;">{qual}</div></div>""", unsafe_allow_html=True)
                with c2:
                    th="".join([f'<div style="padding:5px 0 5px 16px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;color:#c8cad0;position:relative;"><span style="position:absolute;left:0;color:#26a69a;font-weight:900;font-size:14px;">+</span>{t}</div>' for t in ai_res.get("thesis",[])])
                    rk="".join([f'<div style="padding:5px 0 5px 16px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;color:#c8cad0;position:relative;"><span style="position:absolute;left:0;color:#ef5350;font-weight:900;font-size:14px;">−</span>{r}</div>' for r in ai_res.get("risks",[])])
                    st.markdown(f"""<div style="background:rgba(38,166,154,0.06);border:1px solid rgba(38,166,154,0.18);border-radius:10px;padding:12px;margin-bottom:6px;">
                    <div style="font-size:11px;color:#26a69a;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Bull Thesis</div>{th}</div>
                    <div style="background:rgba(239,83,80,0.06);border:1px solid rgba(239,83,80,0.18);border-radius:10px;padding:12px;">
                    <div style="font-size:11px;color:#ef5350;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Risk Factors</div>{rk}</div>""", unsafe_allow_html=True)
                with c3:
                    mtf = ai_res.get("multi_tf",{})
                    mtf_h = "".join([f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;"><span style="color:#374151;font-size:10px;font-weight:700;text-transform:uppercase;min-width:50px;">{k}</span><span style="color:#c8cad0;">{vv}</span></div>' for k,vv in mtf.items()])
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:12px;margin-bottom:6px;">
                    <div style="font-size:11px;color:#374151;text-transform:uppercase;font-weight:700;margin-bottom:6px;">Multi-Timeframe</div>{mtf_h}</div>
                    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:10px;padding:10px;font-size:11px;color:#9598a1;line-height:1.7;">
                    <b style="color:#374151;">Catalyst:</b> {ai_res.get('catalyst','—')}<br>
                    <b style="color:#374151;">Macro:</b> {ai_res.get('macro','—')[:60]}</div>""", unsafe_allow_html=True)

            with tabs[7]:
                try:
                    wp = _full_report_html(sym, name, tech, fund, ai_res)
                    components.html(wp, height=4200, scrolling=True)
                except Exception as e:
                    st.error(f"Report error: {e}")
                c1,c2,c3 = st.columns(3)
                with c1:
                    if st.button("🔄 Re-Analyse", key="pd_re2", type="primary"):
                        st.session_state.pd_ai = None; st.rerun()
                with c2:
                    if st.button("📺 Back to TV", key="pd_btv"):
                        st.session_state.pd_mode = "tv"; st.rerun()
                with c3:
                    txt = f"FinSage Personal Dashboard\n{name} ({sym})\n{datetime.now().strftime('%B %d, %Y')}\n\nRating:{ai_res.get('rating')} Bias:{ai_res.get('bias')} Conf:{ai_res.get('confidence')}%\nEntry:{ai_res.get('entry',0):.4f} Stop:{ai_res.get('stop',0):.4f} T1:{ai_res.get('t1',0):.4f}\nR:R:{ai_res.get('rr','—')}\n\n{ai_res.get('summary','')}\n\nDISCLAIMER: Educational only."
                    st.download_button("📥 Download", txt, f"finsage_pd_{sym.replace('.','_').replace('^','')}.txt","text/plain",key="pd_dl")
