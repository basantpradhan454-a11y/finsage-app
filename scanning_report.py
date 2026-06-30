"""
FinSage AI Scanning Report
- White paper with real-time chart embedded as canvas copy
- Candlestick + chart pattern highlights inside white border
- Social media feed (news, text, images)
"""
import json as _j
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import requests


def _fetch_social_news(sym: str, name: str) -> list:
    """Fetch news/social data for the symbol via Yahoo Finance + fallback sources."""
    items = []
    sym_clean = sym.replace(".NS","").replace(".BO","").replace("-USD","").replace("^","")

    # Yahoo Finance news via yfinance
    try:
        import yfinance as yf
        ticker = yf.Ticker(sym)
        news = ticker.news or []
        for n in news[:15]:
            ct = n.get("content", {})
            title = ct.get("title","") if ct else n.get("title","")
            link  = ct.get("canonicalUrl",{}).get("url","") if ct else n.get("link","")
            pub   = n.get("provider","") or (ct.get("provider",{}).get("displayName","") if ct else "")
            ts    = n.get("providerPublishTime","") or (ct.get("pubDate","") if ct else "")
            thumb = ""
            try:
                thumb = (ct.get("thumbnail",{}).get("resolutions",[{}])[0].get("url","") if ct else
                         n.get("thumbnail",{}).get("resolutions",[{}])[0].get("url",""))
            except: pass
            if title:
                items.append({
                    "type":"news","title":title,"url":link,"source":pub,
                    "time":str(ts)[:10],"image":thumb,"text":""
                })
    except Exception as e:
        pass

    # Fallback: generate simulated social sentiment tiles if no news
    if not items:
        items = [
            {"type":"info","title":f"No recent news found for {name}","url":"","source":"FinSage",
             "time":datetime.now().strftime("%Y-%m-%d"),"image":"","text":
             f"Search manually: Twitter/X: ${sym_clean}, Reddit: r/IndianStockMarket or r/stocks, "
             f"Telegram: @NSEIndia, StockTwits: ${sym_clean}"},
        ]
    return items


def _social_feed_html(sym: str, name: str, items: list, bias: str) -> str:
    bias_c = "#3fd0a0" if bias=="bullish" else "#ff5d6c" if bias=="bearish" else "#e8b34d"
    sym_c = sym.replace(".NS","").replace("-USD","").replace("^","")

    cards = ""
    for item in items[:20]:
        img_html = ""
        if item.get("image"):
            img_html = f'<img src="{item["image"]}" style="width:100%;height:80px;object-fit:cover;border-radius:6px;margin-bottom:6px;" onerror="this.style.display=\'none\'" />'
        src_col = "#4a9eff"
        badge = f'<span style="background:{src_col}18;color:{src_col};border:1px solid {src_col}33;font-size:9px;padding:1px 6px;border-radius:8px;font-weight:700;">{item.get("source","News")[:20]}</span>'
        t_col = "#3fd0a0" if "bull" in item["title"].lower() or "rise" in item["title"].lower() or "gain" in item["title"].lower() else "#ff5d6c" if "fall" in item["title"].lower() or "drop" in item["title"].lower() or "crash" in item["title"].lower() else "#d1d4dc"
        url_part = f'<a href="{item["url"]}" target="_blank" style="color:#4a9eff;font-size:10px;text-decoration:none;display:block;margin-top:4px;">Read more →</a>' if item.get("url") else ""
        text_part = f'<div style="font-size:11px;color:#6a7585;margin-top:4px;line-height:1.5;">{item.get("text","")[:120]}</div>' if item.get("text") else ""
        cards += f'''<div style="background:rgba(13,17,28,0.85);border:1px solid rgba(255,255,255,0.07);
border-radius:10px;padding:10px;margin-bottom:8px;transition:border-color .15s;"
onmouseover="this.style.borderColor='rgba(74,158,255,0.3)'" onmouseout="this.style.borderColor='rgba(255,255,255,0.07)'">
{img_html}
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
{badge}
<span style="color:#374151;font-size:9.5px;">{item.get("time","")}</span>
</div>
<div style="font-size:12.5px;font-weight:700;color:{t_col};line-height:1.5;">{item["title"]}</div>
{text_part}{url_part}
</div>'''

    # Social platform quick links
    links = f'''<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">
<a href="https://twitter.com/search?q=%24{sym_c}" target="_blank" style="background:#1da1f218;color:#1da1f2;border:1px solid #1da1f233;padding:4px 10px;border-radius:6px;font-size:11px;text-decoration:none;font-weight:700;">𝕏 Twitter</a>
<a href="https://www.reddit.com/search/?q={sym_c}+stock" target="_blank" style="background:#ff450018;color:#ff4500;border:1px solid #ff450033;padding:4px 10px;border-radius:6px;font-size:11px;text-decoration:none;font-weight:700;">Reddit</a>
<a href="https://stocktwits.com/symbol/{sym_c}" target="_blank" style="background:#3d8eff18;color:#3d8eff;border:1px solid #3d8eff33;padding:4px 10px;border-radius:6px;font-size:11px;text-decoration:none;font-weight:700;">StockTwits</a>
<a href="https://www.youtube.com/results?search_query={sym_c}+stock+analysis" target="_blank" style="background:#ff000018;color:#ff0000;border:1px solid #ff000033;padding:4px 10px;border-radius:6px;font-size:11px;text-decoration:none;font-weight:700;">▶ YouTube</a>
<a href="https://t.me/nse_india" target="_blank" style="background:#2ca5e018;color:#2ca5e0;border:1px solid #2ca5e033;padding:4px 10px;border-radius:6px;font-size:11px;text-decoration:none;font-weight:700;">Telegram</a>
<a href="https://economictimes.indiatimes.com/searchresult.cms?query={sym_c}" target="_blank" style="background:#f0a93c18;color:#f0a93c;border:1px solid #f0a93c33;padding:4px 10px;border-radius:6px;font-size:11px;text-decoration:none;font-weight:700;">ET Markets</a>
</div>'''

    return f'''<div style="padding:10px;">
<div style="font-size:12px;font-weight:800;color:#e2e8f2;margin-bottom:10px;display:flex;align-items:center;gap:8px;">
<span style="background:{bias_c}18;color:{bias_c};border:1px solid {bias_c}33;padding:2px 8px;border-radius:8px;font-size:10px;">{bias.upper()}</span>
{name} ({sym_c}) · Social & News Feed
</div>
{links}
{cards}
</div>'''


def _build_scanning_report_html(candles: list, indicators: list, sr_zones: list,
                                 patterns: list, bias: str, sym: str, name: str,
                                 ai_res: dict) -> str:
    """
    White paper scanning report with:
    1. Embedded LWC chart (copied to canvas for PDF-like rendering)
    2. Candlestick + pattern highlights inside white border
    3. Multi-timeframe summary
    4. Social media links section
    """
    import json as _j

    candle_data = _j.dumps([
        {"time": c["time"][:10], "open": float(c["open"]), "high": float(c["high"]),
         "low": float(c["low"]), "close": float(c["close"]), "volume": float(c["volume"])}
        for c in candles if c.get("time")
    ])
    sma20_d = _j.dumps([{"time":c["time"][:10],"value":float(ind["sma20"])}
        for c,ind in zip(candles,indicators) if ind.get("sma20") and str(ind.get("sma20",""))!="nan"])
    sma50_d = _j.dumps([{"time":c["time"][:10],"value":float(ind["sma50"])}
        for c,ind in zip(candles,indicators) if ind.get("sma50") and str(ind.get("sma50",""))!="nan"])
    rsi_d   = _j.dumps([{"time":c["time"][:10],"value":float(ind["rsi14"])}
        for c,ind in zip(candles,indicators) if ind.get("rsi14") and str(ind.get("rsi14",""))!="nan"])

    sr_lines_js = ""
    for z in sr_zones:
        color = "#3fd0a0" if z["type"]=="support" else "#ff5d6c"
        sr_lines_js += f'mainS.createPriceLine({{price:{z["price"]},color:"{color}",lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:"{"S" if z["type"]=="support" else "R"}"}});'

    markers_js = ""
    if patterns:
        mlist = []
        for p in patterns:
            idx = p["index"]
            if 0 <= idx < len(candles):
                t = candles[idx]["time"][:10]
                color = "#3fd0a0" if p["bias"]=="bullish" else "#ff5d6c" if p["bias"]=="bearish" else "#e8b34d"
                pos = "belowBar" if p["bias"]=="bullish" else "aboveBar" if p["bias"]=="bearish" else "inBar"
                shape = "arrowUp" if p["bias"]=="bullish" else "arrowDown" if p["bias"]=="bearish" else "circle"
                mlist.append({"time":t,"position":pos,"color":color,"shape":shape,"text":p["name"]})
        if mlist:
            markers_js = f"mainS.setMarkers({_j.dumps(mlist)});"

    bias_c = "#3fd0a0" if bias=="bullish" else "#ff5d6c" if bias=="bearish" else "#e8b34d"
    rat = ai_res.get("rating","HOLD"); rc = ai_res.get("rating_color","#f59e0b")
    conf = ai_res.get("confidence",65)
    entry = ai_res.get("entry",0); stop = ai_res.get("stop",0)
    t1 = ai_res.get("t1",0); rr = ai_res.get("rr","—")
    sym_c = sym.replace(".NS","").replace("-USD","").replace("^","")
    n_patterns = len(patterns)
    n_sr = len(sr_zones)

    # Pattern list for white paper
    pat_rows = ""
    for p in list(reversed(patterns))[:20]:
        pc = "#1b5e20" if p["bias"]=="bullish" else "#b71c1c" if p["bias"]=="bearish" else "#555"
        sig = "▲ BULLISH" if p["bias"]=="bullish" else "▼ BEARISH" if p["bias"]=="bearish" else "→ NEUTRAL"
        pat_rows += f'<tr><td style="font-weight:700;">{p["name"]}</td><td style="color:{pc};font-weight:700;">{sig}</td><td style="font-size:12px;color:#555;">{p["definition"][:100]}</td></tr>'

    # SR rows
    sr_rows = ""
    for z in sorted(sr_zones, key=lambda x: -x["price"]):
        zc = "#1b5e20" if z["type"]=="support" else "#b71c1c"
        lab = "SUPPORT" if z["type"]=="support" else "RESISTANCE"
        sr_rows += f'<tr><td style="font-family:monospace;font-weight:700;">{z["price"]}</td><td style="color:{zc};font-weight:700;">{lab}</td><td style="font-weight:700;">{z["strength"]}x</td></tr>'

    now_str = datetime.now().strftime("%B %d, %Y — %H:%M IST")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
/* ── WHITE PAPER FRAME ── */
.wp-page {{
  background: #ffffff;
  color: #1a1a1a;
  font-family: Georgia, 'Times New Roman', serif;
  max-width: 860px;
  margin: 0 auto;
  padding: 32px 40px;
  line-height: 1.8;
  box-shadow: 0 0 0 1px #ddd;
  border-radius: 4px;
}}
/* Everything inside white paper uses dark text */
.wp-page * {{ color: #1a1a1a !important; background: transparent !important; }}
.wp-stripe {{ height: 5px; background: linear-gradient(90deg,#1a237e,#006064,#1b5e20,#b71c1c); margin-bottom: 20px; border-radius: 3px; }}
.wp-page h1 {{ font-size: 26px; font-weight: 900; margin-bottom: 4px; font-family: Arial, sans-serif; }}
.wp-page h2 {{ font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: .12em;
  border-bottom: 2px solid #1a1a1a; padding-bottom: 5px; margin: 22px 0 10px; font-family: Arial, sans-serif; }}
.wp-page p {{ font-size: 13.5px; line-height: 1.8; margin-bottom: 8px; }}
.wp-page table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; margin: 8px 0; }}
.wp-page th {{ background: #1a1a1a !important; color: #fff !important; padding: 7px 9px;
  text-align: left; font-family: Arial, sans-serif; font-size: 10px; text-transform: uppercase; letter-spacing: .06em; }}
.wp-page td {{ padding: 6px 9px; border-bottom: 1px solid #e8e8e8; vertical-align: top; }}
.wp-page tr:nth-child(even) td {{ background: #f9f9f9 !important; }}
/* Chart frame — WHITE BORDER that keeps everything inside */
.chart-frame {{
  border: 3px solid #1a1a1a;
  border-radius: 6px;
  overflow: hidden;
  margin: 14px 0;
  background: #060b14 !important;
}}
.chart-frame * {{ background: transparent !important; }}
#scanChart {{ width: 100%; height: 340px; }}
#scanVol   {{ width: 100%; height: 80px;  border-top: 1px solid rgba(255,255,255,0.06); }}
#scanRsi   {{ width: 100%; height: 70px;  border-top: 1px solid rgba(255,255,255,0.06); }}
.chart-label {{
  background: #0a1018 !important;
  color: #6a7585 !important;
  font-family: monospace;
  font-size: 10px;
  padding: 4px 10px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  display: flex; gap: 12px; align-items: center;
}}
.chart-label * {{ color: #6a7585 !important; background: transparent !important; }}
.chart-label .bias-pill {{
  background: {bias_c}22 !important;
  color: {bias_c} !important;
  border: 1px solid {bias_c}44;
  padding: 1px 8px; border-radius: 8px; font-weight: 700; font-size: 10px;
}}
/* Setup box */
.setup-box {{
  display: grid; grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px; margin: 12px 0;
}}
.setup-cell {{
  border: 1px solid #e0e0e0;
  border-radius: 6px; padding: 10px; text-align: center;
}}
.setup-cell .lbl {{ font-size: 9px; text-transform: uppercase; letter-spacing: .08em; color: #888 !important; }}
.setup-cell .val {{ font-size: 20px; font-weight: 900; font-family: monospace; margin-top: 3px; }}
</style>
</head>
<body style="background:#f4f4f0;padding:20px 0;">
<div class="wp-page">
<div class="wp-stripe"></div>

<!-- HEADER -->
<h1>{name} ({sym_c})</h1>
<p style="font-size:12px;color:#555!important;margin-bottom:2px;font-family:Arial,sans-serif;">
  AI Scanning Report · FinSage · {now_str}
</p>
<p style="font-size:11px;color:#888!important;font-family:Arial,sans-serif;margin-bottom:16px;">
  {len(candles)} candles analyzed · {n_patterns} patterns detected · {n_sr} S/R zones
</p>

<!-- RATING STRIP -->
<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
  <div class="setup-cell" style="border-color:{rc}55;">
    <div class="lbl">Rating</div>
    <div class="val" style="color:{rc}!important;">{rat}</div>
  </div>
  <div class="setup-cell" style="border-color:{bias_c}55;">
    <div class="lbl">Bias</div>
    <div class="val" style="color:{bias_c}!important;">{bias.upper()}</div>
  </div>
  <div class="setup-cell">
    <div class="lbl">Confidence</div>
    <div class="val">{conf}%</div>
  </div>
  <div class="setup-cell">
    <div class="lbl">R:R Ratio</div>
    <div class="val">{rr}</div>
  </div>
</div>

<!-- AI SUMMARY -->
<h2>Executive Summary</h2>
<p>{ai_res.get("summary","AI analysis completed.")}</p>

<!-- ═══ REAL-TIME CHART — inside white border ═══ -->
<h2>Real-Time Price Chart — All Indicators & Patterns</h2>
<p style="font-size:12px;">Chart below is drawn in real-time from live market data.
White border keeps all chart elements (S/R lines, pattern arrows, indicators) contained within the report boundary.</p>

<div class="chart-frame">
  <div class="chart-label">
    <span class="bias-pill">{bias.upper()}</span>
    <span>{sym_c}</span>
    <span>S/R: {"  |  ".join([str(z["price"]) for z in sr_zones[:4]])}</span>
    <span style="margin-left:auto;">{n_patterns} patterns · SMA20/50 · RSI · Volume</span>
  </div>
  <div id="scanChart"></div>
  <div id="scanVol"></div>
  <div id="scanRsi"></div>
</div>

<!-- TRADE SETUP -->
<h2>Trade Setup</h2>
<div class="setup-box">
  <div class="setup-cell"><div class="lbl">Entry</div><div class="val" style="color:#1b5e20!important;font-size:16px;">{entry:.4f}</div></div>
  <div class="setup-cell"><div class="lbl">Stop Loss</div><div class="val" style="color:#b71c1c!important;font-size:16px;">{stop:.4f}</div></div>
  <div class="setup-cell"><div class="lbl">Target 1</div><div class="val" style="color:#1565c0!important;font-size:16px;">{t1:.4f}</div></div>
  <div class="setup-cell"><div class="lbl">Risk : Reward</div><div class="val">{rr}</div></div>
</div>

<!-- S/R ZONES -->
<h2>Support & Resistance Zones</h2>
<table>
  <thead><tr><th>Price Level</th><th>Type</th><th>Strength</th></tr></thead>
  <tbody>{sr_rows}</tbody>
</table>

<!-- PATTERNS -->
<h2>Detected Candlestick & Chart Patterns (White Paper Definitions)</h2>
<table>
  <thead><tr><th>Pattern</th><th>Signal</th><th>Definition</th></tr></thead>
  <tbody>{pat_rows if pat_rows else "<tr><td colspan='3' style='color:#888;'>No significant patterns in this range</td></tr>"}</tbody>
</table>

<!-- PRICE ACTION ANALYSIS -->
<h2>Price Action Analysis</h2>
<p>{ai_res.get("price_action",{}).get("view","AI price action analysis pending.")}</p>

<!-- SMC -->
<h2>Smart Money Concepts (SMC/ICT)</h2>
<p>{ai_res.get("smc",{}).get("view","SMC analysis pending.")}</p>

<!-- QUANT -->
<h2>Quantitative Analysis</h2>
<p>{ai_res.get("quant",{}).get("view","Quantitative analysis pending.")}</p>

<!-- DISCLAIMER -->
<div style="background:#f5f5f5!important;border-radius:4px;padding:14px;margin-top:20px;
font-size:11px;color:#666!important;font-family:Arial,sans-serif;border-left:4px solid #1a1a1a;">
<b>DISCLAIMER:</b> This report is generated by FinSage AI for educational and informational purposes only.
It does not constitute financial advice. Past performance is not indicative of future results.
Always conduct your own research and consult a qualified financial advisor before making investment decisions.
</div>
</div>

<!-- ══ CHART SCRIPT ══ -->
<script>
(function(){{
  var CANDLES = {candle_data};
  var SMA20   = {sma20_d};
  var SMA50   = {sma50_d};
  var RSI     = {rsi_d};
  var LWC = LightweightCharts;
  var BASE = {{
    layout: {{background:{{color:"#060b14"}},textColor:"#5a6475",fontSize:9,fontFamily:"monospace"}},
    grid: {{vertLines:{{color:"rgba(255,255,255,0.02)"}},horzLines:{{color:"rgba(255,255,255,0.03)"}}}},
    timeScale: {{borderColor:"rgba(255,255,255,0.05)",timeVisible:true}},
    rightPriceScale: {{borderColor:"rgba(255,255,255,0.05)",textColor:"#3f4d5e"}},
    handleScroll: {{mouseWheel:true,pressedMouseMove:true}},
    handleScale: {{mouseWheel:true,pinch:true}},
    crosshair: {{mode:LWC.CrosshairMode.Normal}}
  }};

  // Main chart
  var mc = LWC.createChart(document.getElementById("scanChart"),
    Object.assign({{}},BASE,{{width:document.getElementById("scanChart").clientWidth,height:340}}));
  var mainS = mc.addCandlestickSeries({{
    upColor:"#3fd0a0",downColor:"#ff5d6c",
    borderUpColor:"#3fd0a0",borderDownColor:"#ff5d6c",
    wickUpColor:"rgba(63,208,160,0.7)",wickDownColor:"rgba(255,93,108,0.7)"
  }});
  mainS.setData(CANDLES);

  // SMA lines
  var s20 = mc.addLineSeries({{color:"#e8b34d",lineWidth:1,title:"SMA20",lastValueVisible:false,priceLineVisible:false}});
  var s50 = mc.addLineSeries({{color:"#7aa2ff",lineWidth:1,title:"SMA50",lastValueVisible:false,priceLineVisible:false}});
  s20.setData(SMA20); s50.setData(SMA50);

  // S/R lines
  {sr_lines_js}

  // Pattern markers
  {markers_js}
  mc.timeScale().fitContent();

  // Volume chart
  var vc = LWC.createChart(document.getElementById("scanVol"),
    Object.assign({{}},BASE,{{width:document.getElementById("scanVol").clientWidth,height:80,timeScale:{{visible:false}}}}));
  var vs = vc.addHistogramSeries({{priceFormat:{{type:"volume"}}}});
  vs.setData(CANDLES.map(function(c){{return {{time:c.time,value:c.volume,color:c.close>=c.open?"rgba(63,208,160,0.5)":"rgba(255,93,108,0.5)"}}}}));

  // RSI chart
  var rc2 = LWC.createChart(document.getElementById("scanRsi"),
    Object.assign({{}},BASE,{{width:document.getElementById("scanRsi").clientWidth,height:70}}));
  var rs = rc2.addLineSeries({{color:"#c792ea",lineWidth:1.5}});
  rs.setData(RSI);
  if(RSI.length){{
    rc2.addLineSeries({{color:"rgba(255,93,108,0.25)",lineWidth:1,lineStyle:LWC.LineStyle.Dashed,lastValueVisible:false,priceLineVisible:false}})
       .setData(RSI.map(function(d){{return {{time:d.time,value:70}}}}));
    rc2.addLineSeries({{color:"rgba(63,208,160,0.25)",lineWidth:1,lineStyle:LWC.LineStyle.Dashed,lastValueVisible:false,priceLineVisible:false}})
       .setData(RSI.map(function(d){{return {{time:d.time,value:30}}}}));
  }}
  rc2.timeScale().fitContent();

  // Sync timescales
  [mc,vc,rc2].forEach(function(c,i){{
    c.timeScale().subscribeVisibleLogicalRangeChange(function(r){{
      if(!r)return;
      [mc,vc,rc2].forEach(function(other,j){{if(i!==j)try{{other.timeScale().setVisibleLogicalRange(r);}}catch(e){{}}}}); }});
  }});

  // Resize observer
  var ro = new ResizeObserver(function(){{
    mc.applyOptions({{width:document.getElementById("scanChart").clientWidth}});
    vc.applyOptions({{width:document.getElementById("scanVol").clientWidth}});
    rc2.applyOptions({{width:document.getElementById("scanRsi").clientWidth}});
  }});
  ["scanChart","scanVol","scanRsi"].forEach(function(id){{ro.observe(document.getElementById(id));}});
}})();
</script>
</body>
</html>"""


def render_scanning_report(sym: str, name: str, candles: list, indicators: list,
                            sr_zones: list, patterns: list, bias: str, ai_res: dict):
    """Render the full AI Scanning Report in Streamlit."""

    # ── Scanning report HTML (chart + white paper) ──────────────────
    st.markdown("""<div style="background:linear-gradient(90deg,#0d1219,#111820);
    border:1px solid rgba(63,208,160,0.2);border-radius:10px;padding:10px 16px;
    margin:8px 0 6px;display:flex;align-items:center;gap:10px;">
      <span style="color:#3fd0a0;font-size:18px;">📋</span>
      <div>
        <div style="color:#e2e8f2;font-weight:800;font-size:13px;">AI Scanning Report — White Paper</div>
        <div style="color:#6a7585;font-size:11px;">Real-time chart · All patterns highlighted · S/R zones · Price action · Inside white border frame</div>
      </div>
    </div>""", unsafe_allow_html=True)

    report_html = _build_scanning_report_html(candles, indicators, sr_zones, patterns, bias, sym, name, ai_res)
    components.html(report_html, height=1800, scrolling=True)

    # ── Social Media Feed ────────────────────────────────────────────
    st.markdown("""<div style="background:linear-gradient(90deg,#0d1219,#111820);
    border:1px solid rgba(29,161,242,0.2);border-radius:10px;padding:10px 16px;
    margin:10px 0 6px;display:flex;align-items:center;gap:10px;">
      <span style="font-size:18px;">📱</span>
      <div>
        <div style="color:#e2e8f2;font-weight:800;font-size:13px;">Social Media & News Feed</div>
        <div style="color:#6a7585;font-size:11px;">Latest news · Twitter/X · Reddit · YouTube · Telegram · StockTwits</div>
      </div>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Loading social & news feed..."):
        social_items = _fetch_social_news(sym, name)

    social_html = _social_feed_html(sym, name, social_items, bias)

    # Two column layout for social feed
    col_s1, col_s2 = st.columns(2)
    half = len(social_items) // 2
    left_items  = social_items[:half+1] if social_items else []
    right_items = social_items[half+1:] if social_items else []

    with col_s1:
        for item in left_items:
            img_html = f'<img src="{item["image"]}" style="width:100%;height:70px;object-fit:cover;border-radius:6px;margin-bottom:5px;" onerror="this.style.display=\'none\'" />' if item.get("image") else ""
            t_col = "#3fd0a0" if any(w in item["title"].lower() for w in ["rise","gain","bull","up","high","surge","jump"]) else "#ff5d6c" if any(w in item["title"].lower() for w in ["fall","drop","crash","bear","down","loss","plunge"]) else "#d1d4dc"
            st.markdown(f'''<div style="background:rgba(13,17,28,0.85);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:10px;margin-bottom:8px;">
{img_html}<div style="display:flex;justify-content:space-between;margin-bottom:3px;"><span style="background:#4a9eff18;color:#4a9eff;border:1px solid #4a9eff33;font-size:9px;padding:1px 6px;border-radius:8px;">{item.get("source","News")[:20]}</span><span style="color:#374151;font-size:9.5px;">{item.get("time","")}</span></div>
<div style="font-size:12.5px;font-weight:700;color:{t_col};line-height:1.5;">{item["title"]}</div>
{"<a href='"+item["url"]+"' target='_blank' style='color:#4a9eff;font-size:10px;'>Read more →</a>" if item.get("url") else ""}</div>''', unsafe_allow_html=True)

    with col_s2:
        # Social platform buttons
        sym_c = sym.replace(".NS","").replace("-USD","").replace("^","")
        st.markdown(f'''<div style="background:rgba(13,17,28,0.85);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:12px;margin-bottom:8px;">
<div style="font-size:11px;font-weight:800;color:#e2e8f2;margin-bottom:10px;">🔗 Find {name} on Social Media</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
<a href="https://twitter.com/search?q=%24{sym_c}" target="_blank" style="background:#1da1f218;color:#1da1f2;border:1px solid #1da1f233;padding:8px;border-radius:8px;font-size:11px;text-decoration:none;font-weight:700;text-align:center;display:block;">𝕏 Twitter/X<br><span style="font-size:9px;color:#6a7585;">${sym_c} tweets</span></a>
<a href="https://www.reddit.com/search/?q={sym_c}" target="_blank" style="background:#ff450018;color:#ff4500;border:1px solid #ff450033;padding:8px;border-radius:8px;font-size:11px;text-decoration:none;font-weight:700;text-align:center;display:block;">Reddit<br><span style="font-size:9px;color:#6a7585;">r/stocks discussion</span></a>
<a href="https://stocktwits.com/symbol/{sym_c}" target="_blank" style="background:#3d8eff18;color:#3d8eff;border:1px solid #3d8eff33;padding:8px;border-radius:8px;font-size:11px;text-decoration:none;font-weight:700;text-align:center;display:block;">StockTwits<br><span style="font-size:9px;color:#6a7585;">Trader sentiment</span></a>
<a href="https://www.youtube.com/results?search_query={sym_c}+stock+analysis" target="_blank" style="background:#ff000018;color:#ff0000;border:1px solid #ff000033;padding:8px;border-radius:8px;font-size:11px;text-decoration:none;font-weight:700;text-align:center;display:block;">▶ YouTube<br><span style="font-size:9px;color:#6a7585;">Video analysis</span></a>
<a href="https://economictimes.indiatimes.com/searchresult.cms?query={sym_c}" target="_blank" style="background:#f0a93c18;color:#f0a93c;border:1px solid #f0a93c33;padding:8px;border-radius:8px;font-size:11px;text-decoration:none;font-weight:700;text-align:center;display:block;">ET Markets<br><span style="font-size:9px;color:#6a7585;">Indian finance</span></a>
<a href="https://www.moneycontrol.com/stocks/cptmarket/compsearchnew.php?search_data={sym_c}" target="_blank" style="background:#e040fb18;color:#e040fb;border:1px solid #e040fb33;padding:8px;border-radius:8px;font-size:11px;text-decoration:none;font-weight:700;text-align:center;display:block;">MoneyControl<br><span style="font-size:9px;color:#6a7585;">NSE/BSE data</span></a>
</div></div>''', unsafe_allow_html=True)
        for item in right_items:
            img_html = f'<img src="{item["image"]}" style="width:100%;height:70px;object-fit:cover;border-radius:6px;margin-bottom:5px;" onerror="this.style.display=\'none\'" />' if item.get("image") else ""
            t_col = "#3fd0a0" if any(w in item["title"].lower() for w in ["rise","gain","bull","up","high","surge","jump"]) else "#ff5d6c" if any(w in item["title"].lower() for w in ["fall","drop","crash","bear","down","loss","plunge"]) else "#d1d4dc"
            st.markdown(f'''<div style="background:rgba(13,17,28,0.85);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:10px;margin-bottom:8px;">
{img_html}<div style="display:flex;justify-content:space-between;margin-bottom:3px;"><span style="background:#4a9eff18;color:#4a9eff;border:1px solid #4a9eff33;font-size:9px;padding:1px 6px;border-radius:8px;">{item.get("source","News")[:20]}</span><span style="color:#374151;font-size:9.5px;">{item.get("time","")}</span></div>
<div style="font-size:12.5px;font-weight:700;color:{t_col};line-height:1.5;">{item["title"]}</div>
{"<a href='"+item["url"]+"' target='_blank' style='color:#4a9eff;font-size:10px;'>Read more →</a>" if item.get("url") else ""}</div>''', unsafe_allow_html=True)
