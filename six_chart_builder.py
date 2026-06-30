"""FinSage — 6-Chart Builder with Per-Chart Fullscreen & Order Flow"""
import json as _j
import pandas as pd


def _build_six_chart_html(df, tech, ai, sr_lvls, vp_res, fib_res, patterns, sym, name):
    """6 simultaneous trader-perspective charts with fullscreen toggle per chart."""
    cd = []
    if df is not None and not df.empty:
        for idx, row in df.tail(200).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            try:
                cd.append({"time":ts,"open":round(float(row["Open"]),4),"high":round(float(row["High"]),4),
                           "low":round(float(row["Low"]),4),"close":round(float(row["Close"]),4),"volume":int(row["Volume"])})
            except: pass

    cj   = _j.dumps(cd)
    supp = _j.dumps([s["price"] for s in sr_lvls.get("support",[]) ][:5])
    res  = _j.dumps([r["price"] for r in sr_lvls.get("resistance",[])][:5])
    poc   = vp_res.poc if hasattr(vp_res,'poc') else 0
    vah   = vp_res.vah if hasattr(vp_res,'vah') else 0
    val   = vp_res.val if hasattr(vp_res,'val') else 0
    vwap  = vp_res.vwap if hasattr(vp_res,'vwap') else 0
    fib382= fib_res.levels.get("0.382",0) if hasattr(fib_res,'levels') else 0
    fib618= fib_res.levels.get("0.618",0) if hasattr(fib_res,'levels') else 0
    fib500= fib_res.levels.get("0.5",  0) if hasattr(fib_res,'levels') else 0
    pat_names = _j.dumps([
        {"name": p.name, "signal": p.signal,
         "ts": int(p.timestamp.timestamp() if hasattr(p.timestamp,"timestamp") else 0)}
        for p in patterns[:12]
    ])
    trend  = ai.get("overall_bias", tech.get("trend","NEUTRAL"))
    bias_c = "#26a69a" if "BULL" in str(trend).upper() else "#ef5350" if "BEAR" in str(trend).upper() else "#f59e0b"
    sym_c  = sym.replace(".NS","").replace("-USD","").replace("^","")
    cur_p  = cd[-1]["close"] if cd else 0
    cur_f  = f"{cur_p:,.4f}" if 0<cur_p<100 else f"{cur_p:,.2f}" if cur_p>0 else "—"

    charts = [
        {"id":"c0","title":"1. Price Action",  "sub":"S/R · Trendlines · Clean Chart","col":"#3d8eff"},
        {"id":"c1","title":"2. SMC / ICT",     "sub":"Order Blocks · FVG · Liquidity","col":"#e040fb"},
        {"id":"c2","title":"3. Quant View",    "sub":"EMA20/50/200 · Bollinger Bands","col":"#f0a93c"},
        {"id":"c3","title":"4. Indicators",    "sub":"RSI patterns · MACD markers · Candles","col":"#16c98d"},
        {"id":"c4","title":"5. Order Flow",    "sub":"Vol Profile · POC · VAH/VAL · VWAP","col":"#26a69a"},
        {"id":"c5","title":"6. Elliott Wave",  "sub":"Fibonacci · Wave Levels · Extensions","col":"#ef5350"},
    ]

    cards_html = ""
    for ch in charts:
        cards_html += (
            f'<div class="cell" id="cell_{ch["id"]}">'
            f'<div class="cell-hd" style="border-left:3px solid {ch["col"]};">'
            f'<span class="cell-t" style="color:{ch["col"]};">{ch["title"]}</span>'
            f'<span class="cell-s">{ch["sub"]}</span>'
            f'<button class="fs-btn" onclick="toggleFS(\'{ch["id"]}\')" title="Fullscreen">⛶</button>'
            f'</div>'
            f'<div class="cell-c" id="{ch["id"]}"></div>'
            f'</div>'
        )

    CSS = (
        "*{margin:0;padding:0;box-sizing:border-box;}"
        "html,body{background:#060b14;color:#d1d4dc;"
        "font-family:'Inter',-apple-system,sans-serif;width:100%;overflow:hidden;}"
        "#root{width:100%;height:900px;display:flex;flex-direction:column;}"
        "#hdr{height:38px;display:flex;align-items:center;gap:10px;padding:0 14px;"
        "background:#0a1018;border-bottom:1px solid rgba(255,255,255,0.06);flex-shrink:0;}"
        "#hdr .sym{font-family:monospace;font-weight:800;font-size:13px;color:#e2e8f2;}"
        "#hdr .bias{font-size:10px;font-weight:700;padding:2px 10px;border-radius:10px;}"
        "#hdr .sub{font-size:10px;color:#4a5568;margin-left:auto;}"
        "#grid{flex:1;display:grid;grid-template-columns:1fr 1fr 1fr;"
        "grid-template-rows:1fr 1fr;gap:2px;min-height:0;padding:2px;}"
        ".cell{display:flex;flex-direction:column;background:#0a1018;border-radius:6px;"
        "overflow:hidden;transition:all .2s;}"
        ".cell-hd{padding:5px 8px;background:#0d1219;border-bottom:1px solid rgba(255,255,255,0.05);"
        "flex-shrink:0;display:flex;align-items:center;gap:6px;}"
        ".cell-t{font-size:11px;font-weight:800;}"
        ".cell-s{font-size:9px;color:#4a5568;flex:1;}"
        ".cell-c{flex:1;min-height:0;}"
        ".fs-btn{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);"
        "color:#6a7585;font-size:11px;padding:1px 5px;border-radius:4px;cursor:pointer;"
        "transition:all .15s;flex-shrink:0;}"
        ".fs-btn:hover{background:rgba(41,98,255,0.2);color:#4a9eff;border-color:#2962ff55;}"
        "#fs-overlay{display:none;position:fixed;inset:0;z-index:9999;"
        "background:#060b14;flex-direction:column;}"
        "#fs-overlay.active{display:flex;}"
        "#fs-hdr{height:42px;display:flex;align-items:center;gap:10px;padding:0 16px;"
        "background:#0a1018;border-bottom:1px solid rgba(255,255,255,0.08);flex-shrink:0;}"
        "#fs-title{font-size:13px;font-weight:800;color:#e2e8f2;}"
        "#fs-sub{font-size:11px;color:#4a5568;flex:1;}"
        "#fs-close{background:rgba(239,83,80,0.15);border:1px solid #ef535044;color:#ef5350;"
        "padding:4px 12px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:700;}"
        "#fs-chart{flex:1;min-height:0;}"
        "#fs-info{height:36px;display:flex;align-items:center;gap:16px;padding:0 16px;"
        "background:#0a1018;border-top:1px solid rgba(255,255,255,0.06);flex-shrink:0;"
        "font-size:11px;color:#6a7585;font-family:monospace;}"
    )

    JS = (
        "(function(){"
        "var CANDLES=" + cj + ";"
        "var SUPP=" + supp + ";"
        "var RES=" + res + ";"
        "var POC=" + str(poc) + ";"
        "var VAH=" + str(vah) + ";"
        "var VAL=" + str(val) + ";"
        "var VWAP_V=" + str(vwap) + ";"
        "var FIB382=" + str(fib382) + ";"
        "var FIB618=" + str(fib618) + ";"
        "var FIB500=" + str(fib500) + ";"
        "var PATS=" + pat_names + ";"
        "var CLOSE=CANDLES.map(function(c){return{time:c.time,value:c.close};});"
        "var LWC=LightweightCharts;"
        "var BASE={layout:{background:{type:'solid',color:'#060b14'},textColor:'#4a5568',fontSize:9,fontFamily:'monospace'},"
        "grid:{vertLines:{color:'rgba(255,255,255,0.02)'},horzLines:{color:'rgba(255,255,255,0.03)'}},"
        "timeScale:{timeVisible:false,borderColor:'rgba(255,255,255,0.04)'},"
        "rightPriceScale:{borderColor:'rgba(255,255,255,0.04)',textColor:'#3f4d5e',scaleMargins:{top:0.08,bottom:0.08}},"
        "handleScroll:{mouseWheel:true,pressedMouseMove:true},handleScale:{mouseWheel:true,pinch:true},"
        "crosshair:{mode:LWC.CrosshairMode.Normal}};"
        # Chart instances stored globally for fullscreen
        "var CHARTS={};"
        "function mk(id,el){"
        "var c=LWC.createChart(el,Object.assign({},BASE,{width:el.clientWidth,height:el.clientHeight}));"
        "window.addEventListener('resize',function(){c.applyOptions({width:el.clientWidth,height:el.clientHeight});});"
        "return c;}"
        "function cs(c){return c.addCandlestickSeries({upColor:'#26a69a',downColor:'#ef5350',"
        "borderUpColor:'#1de9b6',borderDownColor:'#ff5252',"
        "wickUpColor:'rgba(38,200,154,0.65)',wickDownColor:'rgba(239,83,80,0.6)'});}"
        "function addSR(s,sup,res){"
        "sup.forEach(function(v,i){s.createPriceLine({price:v,color:i===0?'#26a69a':'rgba(38,166,154,0.4)',"
        "lineWidth:i===0?1.5:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:i===0,title:i===0?'S':''});});"
        "res.forEach(function(v,i){s.createPriceLine({price:v,color:i===0?'#ef5350':'rgba(239,83,80,0.4)',"
        "lineWidth:i===0?1.5:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:i===0,title:i===0?'R':''});});}"
        "function ema(d,p){var k=2/(p+1),prev,o=[];"
        "d.forEach(function(dd,i){if(i<p-1){o.push(null);return;}"
        "if(i===p-1){var s=0;for(var j=0;j<p;j++)s+=d[j].value;prev=s/p;o.push(prev);return;}"
        "prev=dd.value*k+prev*(1-k);o.push(prev);});return o;}"
        "function edata(e){var o=[];for(var i=0;i<CLOSE.length;i++)if(e[i]!=null)o.push({time:CLOSE[i].time,value:e[i]});return o;}"
        # Build functions per chart type — returns the series for fullscreen reuse
        "function buildPA(c){var s=cs(c);s.setData(CANDLES);addSR(s,SUPP,RES);c.timeScale().fitContent();return s;}"
        "function buildSMC(c){var s=cs(c);s.setData(CANDLES);"
        "if(SUPP.length>0)s.createPriceLine({price:SUPP[0],color:'rgba(22,201,141,0.75)',lineWidth:2,lineStyle:LWC.LineStyle.Solid,axisLabelVisible:true,title:'Demand'});"
        "if(RES.length>0)s.createPriceLine({price:RES[0],color:'rgba(239,83,80,0.75)',lineWidth:2,lineStyle:LWC.LineStyle.Solid,axisLabelVisible:true,title:'Supply'});"
        "if(FIB500>0)s.createPriceLine({price:FIB500,color:'rgba(240,169,60,0.5)',lineWidth:1,lineStyle:LWC.LineStyle.Dotted,axisLabelVisible:true,title:'EQ'});"
        "if(VAH>0)s.createPriceLine({price:VAH,color:'rgba(155,140,255,0.6)',lineWidth:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:true,title:'Liq.'});"
        "c.timeScale().fitContent();return s;}"
        "function buildQuant(c){var s=cs(c);s.setData(CANDLES);"
        "var e20=ema(CLOSE,20),e50=ema(CLOSE,50),e200=ema(CLOSE,Math.min(200,CLOSE.length-1));"
        "var s20=c.addLineSeries({color:'#3d8eff',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "var s50=c.addLineSeries({color:'#f0a93c',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "var s200=c.addLineSeries({color:'#ef5350',lineWidth:1,lineStyle:LWC.LineStyle.Dashed,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "s20.setData(edata(e20));s50.setData(edata(e50));s200.setData(edata(e200));"
        "var sma=[],ssd=[];for(var i2=19;i2<CLOSE.length;i2++){var ss=0;for(var j2=i2-19;j2<=i2;j2++)ss+=CLOSE[j2].value;"
        "var mm=ss/20;sma.push({t:CLOSE[i2].time,v:mm});var sv2=0;for(var j3=i2-19;j3<=i2;j3++)sv2+=Math.pow(CLOSE[j3].value-mm,2);ssd.push(Math.sqrt(sv2/20));}"
        "var bbu=c.addLineSeries({color:'rgba(155,140,255,0.5)',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "var bbl=c.addLineSeries({color:'rgba(155,140,255,0.5)',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "bbu.setData(sma.map(function(d,i){return{time:d.t,value:d.v+2*ssd[i]};}));"
        "bbl.setData(sma.map(function(d,i){return{time:d.t,value:d.v-2*ssd[i]};}));"
        "c.timeScale().fitContent();return s;}"
        "function buildIndicators(c){var s=cs(c);s.setData(CANDLES);"
        "var mkrs=[];PATS.forEach(function(p){if(!p.ts||p.ts<=0)return;"
        "mkrs.push({time:p.ts,position:p.signal==='BULLISH'?'belowBar':'aboveBar',"
        "color:p.signal==='BULLISH'?'#26a69a':p.signal==='BEARISH'?'#ef5350':'#f59e0b',"
        "shape:p.signal==='BULLISH'?'arrowUp':'arrowDown',text:p.name.slice(0,10)});});"
        "if(mkrs.length>0)s.setMarkers(mkrs);"
        "addSR(s,SUPP,RES);c.timeScale().fitContent();return s;}"
        "function buildOrderFlow(c){var s=cs(c);s.setData(CANDLES);"
        "var vs=c.addHistogramSeries({priceScaleId:'vol',scaleMargins:{top:0.7,bottom:0}});"
        "c.priceScale('vol').applyOptions({scaleMargins:{top:0.7,bottom:0}});"
        "vs.setData(CANDLES.map(function(d){return{time:d.time,value:d.volume,"
        "color:d.close>=d.open?'rgba(38,166,154,0.55)':'rgba(239,83,80,0.55)'};}));"
        "if(POC>0)s.createPriceLine({price:POC,color:'#f0a93c',lineWidth:2,lineStyle:LWC.LineStyle.Solid,axisLabelVisible:true,title:'POC'});"
        "if(VAH>0)s.createPriceLine({price:VAH,color:'rgba(22,201,141,0.7)',lineWidth:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:true,title:'VAH'});"
        "if(VAL>0)s.createPriceLine({price:VAL,color:'rgba(239,83,80,0.7)',lineWidth:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:true,title:'VAL'});"
        "if(VWAP_V>0)s.createPriceLine({price:VWAP_V,color:'#e040fb',lineWidth:1.5,lineStyle:LWC.LineStyle.Dotted,axisLabelVisible:true,title:'VWAP'});"
        "c.timeScale().fitContent();return s;}"
        "function buildWave(c){var s=cs(c);s.setData(CANDLES);"
        "var fibs=[{p:FIB382,l:'0.382',col:'#26a69a'},{p:FIB500,l:'0.5',col:'#f0a93c'},{p:FIB618,l:'0.618',col:'#ef5350'}];"
        "fibs.forEach(function(f){if(f.p>0)s.createPriceLine({price:f.p,color:f.col,lineWidth:1,lineStyle:LWC.LineStyle.Dotted,axisLabelVisible:true,title:'Fib '+f.l});});"
        "var e20c=ema(CLOSE,20),e20d2=[];for(var i=0;i<CLOSE.length;i++)if(e20c[i]!=null)e20d2.push({time:CLOSE[i].time,value:e20c[i]});"
        "var es=c.addLineSeries({color:'rgba(61,142,255,0.6)',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "es.setData(e20d2);c.timeScale().fitContent();return s;}"
        # Build all 6 grid charts
        "var BUILDERS=[buildPA,buildSMC,buildQuant,buildIndicators,buildOrderFlow,buildWave];"
        "var IDS=['c0','c1','c2','c3','c4','c5'];"
        "IDS.forEach(function(id,i){"
        "var el=document.getElementById(id);if(!el)return;"
        "var c=mk(id,el);CHARTS[id]={chart:c,builderIdx:i};BUILDERS[i](c);});"
        # Fullscreen logic
        "var FS_CHART=null;var FS_ID=null;"
        "var FS_TITLES=["
        "'1. Price Action|S/R · Trendlines · Support & Resistance zones|#3d8eff',"
        "'2. SMC / ICT|Order Blocks · FVG · Smart Money Concepts|#e040fb',"
        "'3. Quant View|EMA20/50/200 · Bollinger Bands · Statistical overlays|#f0a93c',"
        "'4. Indicators|Candlestick patterns · RSI markers · MACD signals|#16c98d',"
        "'5. Order Flow|Vol Profile · POC · VAH/VAL · VWAP distribution|#26a69a',"
        "'6. Elliott Wave|Fibonacci · Wave counts · Extension levels|#ef5350'"
        "];"
        "window.toggleFS=function(id){"
        "var ov=document.getElementById('fs-overlay');"
        "if(FS_ID===id&&ov.classList.contains('active')){closeFS();return;}"
        "var idx=IDS.indexOf(id);if(idx<0)return;"
        "var parts=FS_TITLES[idx].split('|');"
        "document.getElementById('fs-title').textContent=parts[0];"
        "document.getElementById('fs-title').style.color=parts[2]||'#e2e8f2';"
        "document.getElementById('fs-sub').textContent=parts[1]||'';"
        "ov.classList.add('active');"
        "FS_ID=id;"
        # Destroy previous FS chart, create new one
        "var fsEl=document.getElementById('fs-chart');"
        "fsEl.innerHTML='';"
        "var fsC=LWC.createChart(fsEl,Object.assign({},BASE,"
        "{width:fsEl.clientWidth,height:fsEl.clientHeight,"
        "layout:Object.assign({},BASE.layout,{fontSize:11}),"
        "timeScale:Object.assign({},BASE.timeScale,{timeVisible:true})}));"
        "FS_CHART=fsC;"
        "BUILDERS[idx](fsC);"
        "var rz=new ResizeObserver(function(){fsC.applyOptions({width:fsEl.clientWidth,height:fsEl.clientHeight});fsC.timeScale().fitContent();});"
        "rz.observe(fsEl);"
        # Price info update
        "var last=CANDLES[CANDLES.length-1]||{};"
        "var fi=document.getElementById('fs-info');"
        "fi.innerHTML='<span>O: <b>'+last.open+'</b></span><span>H: <b style=color:#26a69a>'+last.high+'</b></span><span>L: <b style=color:#ef5350>'+last.low+'</b></span><span>C: <b>'+last.close+'</b></span><span style=margin-left:auto;color:#374151>'+CANDLES.length+' candles</span>';"
        "};"
        "window.closeFS=function(){"
        "var ov=document.getElementById('fs-overlay');"
        "ov.classList.remove('active');"
        "if(FS_CHART){FS_CHART.remove();FS_CHART=null;}FS_ID=null;"
        "};"
        "document.addEventListener('keydown',function(e){if(e.key==='Escape')closeFS();});"
        "})();"
    )

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>" + CSS + "</style></head><body>"
        "<div id='root'>"
        "<div id='hdr'>"
        "<span class='sym'>" + sym_c + "</span>"
        "<span class='bias' style='background:" + bias_c + "22;color:" + bias_c + ";border:1px solid " + bias_c + "44;'>" + str(trend).upper()[:12] + "</span>"
        "<span class='st' style='font-size:10px;color:#374151;font-family:monospace;margin-left:6px;'>Curr: " + cur_f + "</span>"
        "<span class='sub'>6 Trader Views · Click ⛶ for fullscreen</span>"
        "</div>"
        "<div id='grid'>" + cards_html + "</div>"
        "</div>"
        # Fullscreen overlay
        "<div id='fs-overlay'>"
        "<div id='fs-hdr'>"
        "<span id='fs-title' style='font-size:13px;font-weight:800;'></span>"
        "<span id='fs-sub' style='font-size:11px;color:#4a5568;flex:1;margin-left:10px;'></span>"
        "<button id='fs-close' onclick='closeFS()'>✕ Close</button>"
        "</div>"
        "<div id='fs-chart'></div>"
        "<div id='fs-info'></div>"
        "</div>"
        "<script src='https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js'></script>"
        "<script>" + JS + "</script>"
        "</body></html>"
    )


def _build_order_flow_html(df, tech, vp_res, ai, sym, name):
    """Order Flow + Volume Profile chart."""
    cd = []
    if df is not None and not df.empty:
        for idx, row in df.tail(200).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            try:
                cd.append({"time":ts,"open":round(float(row["Open"]),4),"high":round(float(row["High"]),4),
                           "low":round(float(row["Low"]),4),"close":round(float(row["Close"]),4),"volume":int(row["Volume"])})
            except: pass

    cj   = _j.dumps(cd)
    poc  = vp_res.poc  if hasattr(vp_res,'poc')  else 0
    vah  = vp_res.vah  if hasattr(vp_res,'vah')  else 0
    val  = vp_res.val  if hasattr(vp_res,'val')  else 0
    vwap = vp_res.vwap if hasattr(vp_res,'vwap') else 0
    sym_c = sym.replace(".NS","").replace("-USD","").replace("^","")
    cur_p = cd[-1]["close"] if cd else 0
    cur_f = f"{cur_p:,.4f}" if 0<cur_p<100 else f"{cur_p:,.2f}" if cur_p>0 else "—"

    CSS = (
        "*{margin:0;padding:0;box-sizing:border-box;}"
        "html,body{background:#060b14;color:#d1d4dc;font-family:'Inter',-apple-system,sans-serif;width:100%;}"
        "#root{width:100%;height:520px;display:flex;flex-direction:column;}"
        "#hdr2{height:36px;display:flex;align-items:center;gap:10px;padding:0 14px;"
        "background:#0a1018;border-bottom:1px solid rgba(255,255,255,0.06);flex-shrink:0;}"
        "#hdr2 .sym{font-family:monospace;font-weight:800;font-size:13px;color:#26a69a;}"
        "#hdr2 .sub{font-size:10px;color:#4a5568;margin-left:auto;}"
        "#body2{flex:1;display:flex;gap:2px;min-height:0;padding:2px;}"
        "#chart2{flex:3;position:relative;background:#0a1018;border-radius:6px;overflow:hidden;}"
        "#vpanel{flex:1;background:#0a1018;border-radius:6px;padding:10px;overflow-y:auto;}"
        ".vp-row{display:flex;align-items:center;gap:6px;margin-bottom:3px;font-size:10px;}"
        ".vp-bar{height:10px;border-radius:2px;min-width:2px;}"
        ".vp-price{font-family:monospace;color:#6a7585;width:60px;text-align:right;}"
        ".vp-vol{color:#374151;width:40px;text-align:right;}"
        ".stats-hdr{font-size:9px;text-transform:uppercase;letter-spacing:.06em;color:#374151;"
        "font-weight:700;margin-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.04);padding-bottom:4px;}"
        ".stat-row{display:flex;justify-content:space-between;font-size:10px;padding:3px 0;"
        "border-bottom:1px solid rgba(255,255,255,0.03);}"
        ".st{color:#4a5568;}.sv{font-family:monospace;font-weight:700;}"
    )

    JS = (
        "(function(){"
        "var CANDLES=" + cj + ";"
        "var POC=" + str(poc) + ";"
        "var VAH=" + str(vah) + ";"
        "var VAL=" + str(val) + ";"
        "var VWAP_V=" + str(vwap) + ";"
        "var LWC=LightweightCharts;"
        "var el=document.getElementById('chart2');if(!el)return;"
        "var c=LWC.createChart(el,{"
        "layout:{background:{type:'solid',color:'#060b14'},textColor:'#4a5568',fontSize:9,fontFamily:'monospace'},"
        "grid:{vertLines:{color:'rgba(255,255,255,0.02)'},horzLines:{color:'rgba(255,255,255,0.03)'}},"
        "timeScale:{timeVisible:true,borderColor:'rgba(255,255,255,0.04)'},"
        "rightPriceScale:{borderColor:'rgba(255,255,255,0.04)',textColor:'#3f4d5e'},"
        "width:el.clientWidth,height:el.clientHeight,"
        "handleScroll:{mouseWheel:true,pressedMouseMove:true},handleScale:{mouseWheel:true,pinch:true},"
        "crosshair:{mode:LWC.CrosshairMode.Normal}});"
        "window.addEventListener('resize',function(){c.applyOptions({width:el.clientWidth,height:el.clientHeight});});"
        "var s=c.addCandlestickSeries({upColor:'#26a69a',downColor:'#ef5350',"
        "borderUpColor:'#1de9b6',borderDownColor:'#ff5252',"
        "wickUpColor:'rgba(38,200,154,0.65)',wickDownColor:'rgba(239,83,80,0.6)'});"
        "s.setData(CANDLES);"
        "var vs=c.addHistogramSeries({priceScaleId:'vol',scaleMargins:{top:0.7,bottom:0}});"
        "c.priceScale('vol').applyOptions({scaleMargins:{top:0.7,bottom:0}});"
        "vs.setData(CANDLES.map(function(d){return{time:d.time,value:d.volume,"
        "color:d.close>=d.open?'rgba(38,166,154,0.45)':'rgba(239,83,80,0.45)'};}));"
        "if(POC>0)s.createPriceLine({price:POC,color:'#f0a93c',lineWidth:2,lineStyle:LWC.LineStyle.Solid,axisLabelVisible:true,title:'POC'});"
        "if(VAH>0)s.createPriceLine({price:VAH,color:'rgba(22,201,141,0.7)',lineWidth:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:true,title:'VAH'});"
        "if(VAL>0)s.createPriceLine({price:VAL,color:'rgba(239,83,80,0.7)',lineWidth:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:true,title:'VAL'});"
        "if(VWAP_V>0)s.createPriceLine({price:VWAP_V,color:'#e040fb',lineWidth:1.5,lineStyle:LWC.LineStyle.Dotted,axisLabelVisible:true,title:'VWAP'});"
        "c.timeScale().fitContent();"
        "})();"
    )

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>" + CSS + "</style></head><body>"
        "<div id='root'>"
        "<div id='hdr2'>"
        "<span class='sym'>Order Flow — " + sym_c + "</span>"
        "<span class='st'>POC</span><span class='sv' style='color:#f0a93c;margin-left:4px;'>" + str(poc) + "</span>"
        "<span class='st' style='margin-left:8px;'>VAH</span><span class='sv' style='color:#26a69a;margin-left:4px;'>" + str(vah) + "</span>"
        "<span class='st' style='margin-left:8px;'>VAL</span><span class='sv' style='color:#ef5350;margin-left:4px;'>" + str(val) + "</span>"
        "<span class='st' style='margin-left:8px;'>VWAP</span><span class='sv' style='color:#e040fb;margin-left:4px;'>" + str(vwap) + "</span>"
        "<span class='st' style='margin-left:8px;'>Curr</span><span class='sv' style='margin-left:4px;'>" + cur_f + "</span>"
        "<span class='sub'>Order Flow · Volume Distribution · Smart Money</span>"
        "</div>"
        "<div id='body2'>"
        "<div id='chart2'></div>"
        "<div id='vpanel'>"
        "<div class='stats-hdr'>Volume Profile</div>"
        "<div class='stat-row'><span class='st'>POC (Point of Control)</span><span class='sv' style='color:#f0a93c;'>" + str(poc) + "</span></div>"
        "<div class='stat-row'><span class='st'>VAH (Value Area High)</span><span class='sv' style='color:#26a69a;'>" + str(vah) + "</span></div>"
        "<div class='stat-row'><span class='st'>VAL (Value Area Low)</span><span class='sv' style='color:#ef5350;'>" + str(val) + "</span></div>"
        "<div class='stat-row'><span class='st'>VWAP</span><span class='sv' style='color:#e040fb;'>" + str(vwap) + "</span></div>"
        "</div>"
        "</div>"
        "</div>"
        "<script src='https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js'></script>"
        "<script>" + JS + "</script>"
        "</body></html>"
    )
