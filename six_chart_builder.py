"""FinSage — 6-Chart and Order Flow HTML Builders"""
import json as _j
import pandas as pd


def _build_six_chart_html(df, tech, ai, sr_lvls, vp_res, fib_res, patterns, sym, name):
    """6 simultaneous trader-perspective charts in 2x3 grid."""
    cd = []
    if df is not None and not df.empty:
        for idx, row in df.tail(120).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            cd.append({"time":ts,"open":round(float(row["Open"]),4),"high":round(float(row["High"]),4),
                       "low":round(float(row["Low"]),4),"close":round(float(row["Close"]),4),"volume":int(row["Volume"])})

    cj   = _j.dumps(cd)
    supp = _j.dumps([s["price"] for s in sr_lvls.get("support",[]) ][:3])
    res  = _j.dumps([r["price"] for r in sr_lvls.get("resistance",[])][:3])
    poc   = vp_res.poc;  vah = vp_res.vah;  val = vp_res.val;  vwap = vp_res.vwap
    fib382= fib_res.levels.get("0.382", 0)
    fib618= fib_res.levels.get("0.618", 0)
    fib500= fib_res.levels.get("0.5",   0)
    pat_names = _j.dumps([
        {"name": p.name, "signal": p.signal,
         "ts": int(p.timestamp.timestamp() if hasattr(p.timestamp, "timestamp") else 0)}
        for p in patterns[:8]
    ])
    trend   = ai.get("overall_bias", tech.get("trend","NEUTRAL"))
    bias_c  = "#26a69a" if "BULL" in str(trend).upper() else "#ef5350" if "BEAR" in str(trend).upper() else "#f59e0b"
    sym_c   = sym.replace(".NS","").replace("-USD","").replace("^","")

    charts = [
        {"id":"c0","title":"1. Price Action","sub":"S/R · Trendlines · Clean Chart","col":"#3d8eff"},
        {"id":"c1","title":"2. SMC / ICT","sub":"Order Blocks · FVG · Liquidity","col":"#e040fb"},
        {"id":"c2","title":"3. Quant View","sub":"EMA20/50/200 · Bollinger Bands","col":"#f0a93c"},
        {"id":"c3","title":"4. Indicators","sub":"RSI patterns · MACD markers · Candles","col":"#16c98d"},
        {"id":"c4","title":"5. Order Flow","sub":"Vol Profile · POC · VAH/VAL · VWAP","col":"#26a69a"},
        {"id":"c5","title":"6. Elliott Wave","sub":"Fibonacci · Wave Levels · Extensions","col":"#ef5350"},
    ]
    cards_html = "".join(
        f'<div class="cell">'
        f'<div class="cell-hd" style="border-left:3px solid {ch["col"]};">'
        f'<span class="cell-t" style="color:{ch["col"]};">{ch["title"]}</span>'
        f'<span class="cell-s">{ch["sub"]}</span></div>'
        f'<div class="cell-c" id="{ch["id"]}"></div></div>'
        for ch in charts
    )

    # Build HTML via string concat (zero f-string/JS conflict)
    CSS = (
        "*{margin:0;padding:0;box-sizing:border-box;}"
        "html,body{background:#060b14;color:#d1d4dc;font-family:'Inter',-apple-system,sans-serif;"
        "width:100%;height:900px;overflow:hidden;}"
        "#root{width:100%;height:900px;display:flex;flex-direction:column;}"
        "#hdr{height:38px;display:flex;align-items:center;gap:10px;padding:0 14px;"
        "background:#0a1018;border-bottom:1px solid rgba(255,255,255,0.06);flex-shrink:0;}"
        "#hdr .sym{font-family:monospace;font-weight:800;font-size:13px;color:#e2e8f2;}"
        "#hdr .bias{font-size:10px;font-weight:700;padding:2px 10px;border-radius:10px;}"
        "#hdr .sub{font-size:10px;color:#4a5568;margin-left:auto;}"
        "#grid{flex:1;display:grid;grid-template-columns:1fr 1fr 1fr;"
        "grid-template-rows:1fr 1fr;gap:2px;min-height:0;padding:2px;}"
        ".cell{display:flex;flex-direction:column;background:#0a1018;border-radius:6px;overflow:hidden;}"
        ".cell-hd{padding:5px 8px;background:#0d1219;border-bottom:1px solid rgba(255,255,255,0.05);flex-shrink:0;}"
        ".cell-t{font-size:11px;font-weight:800;display:block;}"
        ".cell-s{font-size:9px;color:#4a5568;display:block;margin-top:1px;}"
        ".cell-c{flex:1;min-height:0;}"
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
        "function mk(id){var el=document.getElementById(id);if(!el)return null;"
        "var c=LWC.createChart(el,Object.assign({},BASE,{width:el.clientWidth,height:el.clientHeight}));"
        "window.addEventListener('resize',function(){c.applyOptions({width:el.clientWidth,height:el.clientHeight});});"
        "return c;}"
        "function cs(c){return c.addCandlestickSeries({upColor:'#26a69a',downColor:'#ef5350',"
        "borderUpColor:'#1de9b6',borderDownColor:'#ff5252',"
        "wickUpColor:'rgba(38,200,154,0.65)',wickDownColor:'rgba(239,83,80,0.6)'});}"
        "function sr(s,sup,res){sup.forEach(function(v,i){s.createPriceLine({price:v,color:i===0?'#26a69a':'rgba(38,166,154,0.4)',lineWidth:i===0?1.5:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:i===0,title:i===0?'S':''}); });"
        "res.forEach(function(v,i){s.createPriceLine({price:v,color:i===0?'#ef5350':'rgba(239,83,80,0.4)',lineWidth:i===0?1.5:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:i===0,title:i===0?'R':''}); });}"
        "function ema(d,p){var k=2/(p+1),prev,o=[];d.forEach(function(dd,i){if(i<p-1){o.push(null);return;}if(i===p-1){var s=0;for(var j=0;j<p;j++)s+=d[j].value;prev=s/p;o.push(prev);return;}prev=dd.value*k+prev*(1-k);o.push(prev);});return o;}"
        "(function(){var c=mk('c0');if(!c)return;var s=cs(c);s.setData(CANDLES);sr(s,SUPP,RES);c.timeScale().fitContent();})();"
        "(function(){var c=mk('c1');if(!c)return;var s=cs(c);s.setData(CANDLES);"
        "if(SUPP.length>0)s.createPriceLine({price:SUPP[0],color:'rgba(22,201,141,0.75)',lineWidth:2,lineStyle:LWC.LineStyle.Solid,axisLabelVisible:true,title:'Demand'});"
        "if(RES.length>0) s.createPriceLine({price:RES[0], color:'rgba(239,83,80,0.75)',lineWidth:2,lineStyle:LWC.LineStyle.Solid,axisLabelVisible:true,title:'Supply'});"
        "if(FIB500>0)s.createPriceLine({price:FIB500,color:'rgba(240,169,60,0.5)',lineWidth:1,lineStyle:LWC.LineStyle.Dotted,axisLabelVisible:true,title:'EQ/FVG'});"
        "if(VAH>0)s.createPriceLine({price:VAH,color:'rgba(155,140,255,0.6)',lineWidth:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:true,title:'Liq.'});"
        "c.timeScale().fitContent();})();"
        "(function(){var c=mk('c2');if(!c)return;var s=cs(c);s.setData(CANDLES);"
        "var e20=ema(CLOSE,20),e50=ema(CLOSE,50),e200=ema(CLOSE,Math.min(200,CLOSE.length-1));"
        "function edata(e){var o=[];for(var i=0;i<CLOSE.length;i++)if(e[i]!=null)o.push({time:CLOSE[i].time,value:e[i]});return o;}"
        "var s20=c.addLineSeries({color:'#3d8eff',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "var s50=c.addLineSeries({color:'#f0a93c',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "var s200=c.addLineSeries({color:'#ef5350',lineWidth:1,lineStyle:LWC.LineStyle.Dashed,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "s20.setData(edata(e20));s50.setData(edata(e50));s200.setData(edata(e200));"
        "var sma=[],ssd=[];for(var i2=19;i2<CLOSE.length;i2++){var ss=0;for(var j2=i2-19;j2<=i2;j2++)ss+=CLOSE[j2].value;var mm=ss/20;sma.push({t:CLOSE[i2].time,v:mm});var sv2=0;for(var j3=i2-19;j3<=i2;j3++)sv2+=Math.pow(CLOSE[j3].value-mm,2);ssd.push(Math.sqrt(sv2/20));}"
        "var bbu=c.addLineSeries({color:'rgba(155,140,255,0.5)',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "var bbl=c.addLineSeries({color:'rgba(155,140,255,0.5)',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "bbu.setData(sma.map(function(d,i){return{time:d.t,value:d.v+2*ssd[i]};}));"
        "bbl.setData(sma.map(function(d,i){return{time:d.t,value:d.v-2*ssd[i]};}));"
        "c.timeScale().fitContent();})();"
        "(function(){var c=mk('c3');if(!c)return;var s=cs(c);s.setData(CANDLES);"
        "var mkrs=[];PATS.forEach(function(p){if(!p.ts||p.ts<=0)return;"
        "mkrs.push({time:p.ts,position:p.signal==='BULLISH'?'belowBar':'aboveBar',"
        "color:p.signal==='BULLISH'?'#26a69a':p.signal==='BEARISH'?'#ef5350':'#f59e0b',"
        "shape:p.signal==='BULLISH'?'arrowUp':'arrowDown',text:p.name.slice(0,10)});});"
        "if(mkrs.length>0)s.setMarkers(mkrs);"
        "sr(s,SUPP,RES);c.timeScale().fitContent();})();"
        "(function(){var c=mk('c4');if(!c)return;var s=cs(c);s.setData(CANDLES);"
        "var vs=c.addHistogramSeries({priceScaleId:'vol',scaleMargins:{top:0.7,bottom:0}});"
        "c.priceScale('vol').applyOptions({scaleMargins:{top:0.7,bottom:0}});"
        "vs.setData(CANDLES.map(function(d){return{time:d.time,value:d.volume,color:d.close>=d.open?'rgba(38,166,154,0.55)':'rgba(239,83,80,0.55)'};}));"
        "if(POC>0)s.createPriceLine({price:POC,color:'#f0a93c',lineWidth:2,lineStyle:LWC.LineStyle.Solid,axisLabelVisible:true,title:'POC'});"
        "if(VAH>0)s.createPriceLine({price:VAH,color:'rgba(22,201,141,0.7)',lineWidth:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:true,title:'VAH'});"
        "if(VAL>0)s.createPriceLine({price:VAL,color:'rgba(239,83,80,0.7)',lineWidth:1,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:true,title:'VAL'});"
        "if(VWAP_V>0)s.createPriceLine({price:VWAP_V,color:'#e040fb',lineWidth:1.5,lineStyle:LWC.LineStyle.Dotted,axisLabelVisible:true,title:'VWAP'});"
        "c.timeScale().fitContent();})();"
        "(function(){var c=mk('c5');if(!c)return;var s=cs(c);s.setData(CANDLES);"
        "var fibs=[{p:FIB382,l:'0.382',col:'#26a69a'},{p:FIB500,l:'0.5',col:'#f0a93c'},{p:FIB618,l:'0.618',col:'#ef5350'}];"
        "fibs.forEach(function(f){if(f.p>0)s.createPriceLine({price:f.p,color:f.col,lineWidth:1,lineStyle:LWC.LineStyle.Dotted,axisLabelVisible:true,title:'Fib '+f.l});});"
        "var e20c=ema(CLOSE,20),e20d2=[];for(var i=0;i<CLOSE.length;i++)if(e20c[i]!=null)e20d2.push({time:CLOSE[i].time,value:e20c[i]});"
        "var es=c.addLineSeries({color:'rgba(61,142,255,0.6)',lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});"
        "es.setData(e20d2);"
        "c.timeScale().fitContent();})();"
        "})();"
    )

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>" + CSS + "</style></head><body>"
        "<div id='root'>"
        "<div id='hdr'><span class='sym'>" + sym_c + "</span>"
        "<span class='bias' style='background:" + bias_c + "22;color:" + bias_c + ";border:1px solid " + bias_c + "44;'>" + str(trend) + "</span>"
        "<span class='sub'>6 Trader Views &middot; FinSage AI</span></div>"
        "<div id='grid'>" + cards_html + "</div></div>"
        "<script src='https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js'></script>"
        "<script>" + JS + "</script>"
        "</body></html>"
    )


def _build_order_flow_html(df, tech, vp_res, ai, sym, name):
    """Order flow chart: candlestick + volume histogram + vol profile sidebar."""
    cd = []
    if df is not None and not df.empty:
        for idx, row in df.tail(150).iterrows():
            ts = int(pd.Timestamp(idx).timestamp())
            cd.append({"time":ts,"open":round(float(row["Open"]),4),"high":round(float(row["High"]),4),
                       "low":round(float(row["Low"]),4),"close":round(float(row["Close"]),4),"volume":int(row["Volume"])})
    cj   = _j.dumps(cd)
    prof = _j.dumps(vp_res.profile)
    poc  = vp_res.poc; vah = vp_res.vah; val = vp_res.val; vwap = vp_res.vwap
    sym_c = sym.replace(".NS","").replace("-USD","").replace("^","")
    bias  = ai.get("overall_bias", tech.get("trend","NEUTRAL"))
    bc    = "#26a69a" if "BULL" in str(bias).upper() else "#ef5350" if "BEAR" in str(bias).upper() else "#f59e0b"
    cur   = tech.get("price", cd[-1]["close"] if cd else 0)
    cur_f = f"{cur:,.2f}" if cur >= 100 else f"{cur:,.4f}"
    H = 480

    CSS = (
        "*{margin:0;padding:0;box-sizing:border-box;}"
        "html,body{background:#060b14;color:#d1d4dc;font-family:'Inter',-apple-system,sans-serif;"
        "width:100%;height:" + str(H) + "px;overflow:hidden;}"
        "#root{width:100%;height:" + str(H) + "px;display:flex;flex-direction:column;}"
        "#hdr{height:38px;display:flex;align-items:center;gap:10px;padding:0 14px;"
        "background:#0a1018;border-bottom:1px solid rgba(255,255,255,0.06);flex-shrink:0;}"
        "#body{flex:1;display:flex;min-height:0;}"
        "#chart-div{flex:1;min-width:0;}"
        "#vp-side{width:90px;background:#0a1018;border-left:1px solid rgba(255,255,255,0.05);"
        "display:flex;flex-direction:column;overflow:hidden;}"
        "#vp-hdr{font-size:9px;font-weight:700;color:#4a5568;text-align:center;"
        "padding:4px;border-bottom:1px solid rgba(255,255,255,0.05);flex-shrink:0;letter-spacing:.06em;}"
        "#vp-bars{flex:1;overflow:hidden;display:flex;flex-direction:column-reverse;}"
        ".vp-row{display:flex;align-items:center;flex:1;padding:0 3px;min-height:0;}"
        ".vp-fill{height:55%;border-radius:2px;min-width:2px;}"
        ".vp-lbl{font-size:7px;color:#3f4d5e;margin-left:2px;white-space:nowrap;overflow:hidden;max-width:32px;}"
        "#stats{height:32px;background:#0a1018;border-top:1px solid rgba(255,255,255,0.05);"
        "display:flex;align-items:center;gap:14px;padding:0 14px;font-family:monospace;font-size:11px;flex-shrink:0;}"
        ".st{color:#4a5568;} .sv{font-weight:700;}"
    )

    JS = (
        "(function(){"
        "var CANDLES=" + cj + ";"
        "var PROFILE=" + prof + ";"
        "var POC=" + str(poc) + ";"
        "var VAH=" + str(vah) + ";"
        "var VAL=" + str(val) + ";"
        "var VW=" + str(vwap) + ";"
        "var vpEl=document.getElementById('vp-bars');"
        "PROFILE.forEach(function(p){var row=document.createElement('div');row.className='vp-row';"
        "var fill=document.createElement('div');fill.className='vp-fill';"
        "fill.style.width=Math.max(2,p.volume_pct)+'%';"
        "fill.style.background=p.is_poc?'#f0a93c':p.in_value_area?'rgba(61,142,255,0.5)':'rgba(255,255,255,0.1)';"
        "var lbl=document.createElement('div');lbl.className='vp-lbl';"
        "lbl.textContent=p.price>=100?p.price.toFixed(1):p.price.toFixed(3);"
        "row.appendChild(fill);row.appendChild(lbl);vpEl.appendChild(row);});"
        "var LWC=LightweightCharts;"
        "var el=document.getElementById('chart-div');"
        "var chart=LWC.createChart(el,{width:el.clientWidth,height:el.clientHeight,"
        "layout:{background:{type:'solid',color:'#060b14'},textColor:'#4a5568',fontSize:10,fontFamily:'monospace'},"
        "grid:{vertLines:{color:'rgba(255,255,255,0.02)'},horzLines:{color:'rgba(255,255,255,0.03)'}},"
        "timeScale:{timeVisible:true,borderColor:'rgba(255,255,255,0.04)'},"
        "rightPriceScale:{borderColor:'rgba(255,255,255,0.04)',scaleMargins:{top:0.08,bottom:0.25}},"
        "handleScroll:{mouseWheel:true,pressedMouseMove:true},handleScale:{mouseWheel:true,pinch:true}});"
        "var cs=chart.addCandlestickSeries({upColor:'#26a69a',downColor:'#ef5350',"
        "borderUpColor:'#1de9b6',borderDownColor:'#ff5252',"
        "wickUpColor:'rgba(38,200,154,0.6)',wickDownColor:'rgba(239,83,80,0.55)'});"
        "cs.setData(CANDLES);"
        "var vs=chart.addHistogramSeries({priceScaleId:'vol',scaleMargins:{top:0.75,bottom:0}});"
        "chart.priceScale('vol').applyOptions({scaleMargins:{top:0.75,bottom:0}});"
        "vs.setData(CANDLES.map(function(d){return{time:d.time,value:d.volume,color:d.close>=d.open?'rgba(38,166,154,0.5)':'rgba(239,83,80,0.5)'};}));"
        "if(POC>0)cs.createPriceLine({price:POC,color:'#f0a93c',lineWidth:2,lineStyle:LWC.LineStyle.Solid,axisLabelVisible:true,title:'POC'});"
        "if(VAH>0)cs.createPriceLine({price:VAH,color:'rgba(22,201,141,0.75)',lineWidth:1.5,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:true,title:'VAH'});"
        "if(VAL>0)cs.createPriceLine({price:VAL,color:'rgba(239,83,80,0.75)',lineWidth:1.5,lineStyle:LWC.LineStyle.Dashed,axisLabelVisible:true,title:'VAL'});"
        "if(VW>0) cs.createPriceLine({price:VW,color:'#e040fb',lineWidth:1.5,lineStyle:LWC.LineStyle.Dotted,axisLabelVisible:true,title:'VWAP'});"
        "chart.timeScale().fitContent();"
        "window.addEventListener('resize',function(){chart.applyOptions({width:el.clientWidth,height:el.clientHeight});});"
        "})();"
    )

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>" + CSS + "</style></head><body>"
        "<div id='root'>"
        "<div id='hdr'>"
        "<span style='font-size:12px;font-weight:800;color:#e2e8f2;'>Order Flow — " + sym_c + "</span>"
        "<span style='font-size:10px;color:#4a5568;'>Volume Profile · POC · VAH/VAL · VWAP · Delta</span>"
        "<span style='margin-left:auto;font-size:10px;font-weight:700;color:" + bc + ";background:" + bc + "22;padding:2px 9px;border-radius:10px;'>" + str(bias) + "</span>"
        "</div>"
        "<div id='body'>"
        "<div id='chart-div'></div>"
        "<div id='vp-side'><div id='vp-hdr'>VOL PROFILE</div><div id='vp-bars'></div></div>"
        "</div>"
        "<div id='stats'>"
        "<span class='st'>POC</span><span class='sv' style='color:#f0a93c;'>" + str(poc) + "</span>"
        "<span class='st'>VAH</span><span class='sv' style='color:#26a69a;'>" + str(vah) + "</span>"
        "<span class='st'>VAL</span><span class='sv' style='color:#ef5350;'>" + str(val) + "</span>"
        "<span class='st'>VWAP</span><span class='sv' style='color:#e040fb;'>" + str(vwap) + "</span>"
        "<span class='st'>Curr</span><span class='sv'>" + cur_f + "</span>"
        "</div></div>"
        "<script src='https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js'></script>"
        "<script>" + JS + "</script>"
        "</body></html>"
    )
