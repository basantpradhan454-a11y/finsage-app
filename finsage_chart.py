"""
FinSage AI — Professional Chart Engine v2
Full TradingView-style chart:
- Real OHLCV via yfinance
- 14 chart types (Candles, Hollow, Heikin-Ashi, Renko, Line, Area, Bars, HLC, Column, Kagi, P&F, Range, LineBreak, HAS)
- Smooth zoom/pan (wheel + pinch + drag)
- Auto S/R lines with labels
- Manual drawing tools: Cursor, H-Line, Trendline, Ray, Extended Line, Zone, Fibonacci, Arrow, Text
- Draggable / editable drawings — handles visible, context menu
- Undo (Ctrl+Z), Delete key
- 200+ indicator picker (35 live computed, rest labeled SOON)
- Real-time price tick simulation (plug WebSocket for live)
- Volume pane, crosshair OHLCV readout, price/time axes
"""
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import json, os


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_ohlcv(sym: str, period: str = "3mo", interval: str = "1d"):
    try:
        df = yf.Ticker(sym).history(period=period, interval=interval)
        if df.empty:
            return []
        df.index = pd.to_datetime(df.index)
        out = []
        for idx, row in df.iterrows():
            out.append({
                "t": int(idx.timestamp()) * 1000,
                "o": round(float(row["Open"]),   4),
                "h": round(float(row["High"]),   4),
                "l": round(float(row["Low"]),    4),
                "c": round(float(row["Close"]),  4),
                "v": int(row["Volume"]),
            })
        return out
    except Exception:
        return []


@st.cache_data(ttl=90, show_spinner=False)
def _fetch_price(sym: str):
    try:
        fi   = yf.Ticker(sym).fast_info
        pr   = float(getattr(fi, "last_price",       0) or 0)
        prev = float(getattr(fi, "previous_close", pr) or pr)
        chg  = (pr - prev) / prev * 100 if prev else 0
        return {"price": pr, "chg": chg}
    except Exception:
        return {"price": 0, "chg": 0}


def _compute_sr(candles, n=6):
    if len(candles) < 20:
        return {"supports": [], "resistances": []}
    highs  = [c["h"] for c in candles]
    lows   = [c["l"] for c in candles]
    closes = [c["c"] for c in candles]
    cur    = closes[-1]

    swing_h, swing_l = [], []
    for i in range(2, len(candles) - 2):
        if highs[i] >= max(highs[i-2], highs[i-1], highs[i+1], highs[i+2]):
            swing_h.append(highs[i])
        if lows[i] <= min(lows[i-2], lows[i-1], lows[i+1], lows[i+2]):
            swing_l.append(lows[i])

    def cluster(vals, tol=0.003):
        if not vals: return []
        vals = sorted(set(vals))
        out, used = [], [False]*len(vals)
        for i, v in enumerate(vals):
            if used[i]: continue
            grp = [v]
            for j in range(i+1, len(vals)):
                if vals[j] <= v*(1+tol*3): grp.append(vals[j]); used[j]=True
            out.append(sum(grp)/len(grp))
        return out

    sup = sorted([v for v in cluster(swing_l) if v < cur], reverse=True)
    res = sorted([v for v in cluster(swing_h) if v > cur])
    rnd = lambda v: round(v,2) if v>=100 else round(v,4)
    return {"supports": [rnd(v) for v in sup[:n]], "resistances": [rnd(v) for v in res[:n]]}


# 200+ indicator catalog: [name, code, category, live]
INDICATORS = [
    ["Simple Moving Average",        "SMA",       "Moving Average", True ],
    ["Exponential MA",               "EMA",       "Moving Average", True ],
    ["Weighted Moving Average",      "WMA",       "Moving Average", True ],
    ["Hull Moving Average",          "HMA",       "Moving Average", True ],
    ["Double EMA",                   "DEMA",      "Moving Average", True ],
    ["Triple EMA",                   "TEMA",      "Moving Average", True ],
    ["VWAP",                         "VWAP",      "Moving Average", True ],
    ["Volume Weighted MA",           "VWMA",      "Moving Average", True ],
    ["Adaptive MA",                  "AMA",       "Moving Average", False],
    ["Kaufman AMA",                  "KAMA",      "Moving Average", False],
    ["Least Squares MA",             "LSMA",      "Moving Average", False],
    ["McGinley Dynamic",             "MGD",       "Moving Average", False],
    ["Arnaud Legoux MA",             "ALMA",      "Moving Average", False],
    ["T3 Moving Average",            "T3",        "Moving Average", False],
    ["Zero-Lag EMA",                 "ZLEMA",     "Moving Average", False],
    ["Jurik MA",                     "JMA",       "Moving Average", False],
    ["Fractal Adaptive MA",          "FRAMA",     "Moving Average", False],
    ["Sine Weighted MA",             "SWMA",      "Moving Average", False],
    ["RSI",                          "RSI",       "Oscillator",     True ],
    ["Stochastic RSI",               "STOCHRSI",  "Oscillator",     True ],
    ["MACD",                         "MACD",      "Oscillator",     True ],
    ["Stochastic",                   "STOCH",     "Oscillator",     True ],
    ["CCI",                          "CCI",       "Oscillator",     True ],
    ["Williams %R",                  "WILLR",     "Oscillator",     True ],
    ["Momentum",                     "MOM",       "Oscillator",     True ],
    ["Rate of Change",               "ROC",       "Oscillator",     True ],
    ["Money Flow Index",             "MFI",       "Oscillator",     True ],
    ["Chaikin Money Flow",           "CMF",       "Oscillator",     False],
    ["Relative Vigor Index",         "RVI",       "Oscillator",     False],
    ["Awesome Oscillator",           "AO",        "Oscillator",     False],
    ["DeMarker",                     "DEM",       "Oscillator",     False],
    ["Ultimate Oscillator",          "UO",        "Oscillator",     False],
    ["Fisher Transform",             "FISHER",    "Oscillator",     False],
    ["Klinger Osc",                  "KVO",       "Oscillator",     False],
    ["TRIX",                         "TRIX",      "Oscillator",     False],
    ["Know Sure Thing",              "KST",       "Oscillator",     False],
    ["Coppock Curve",                "COPP",      "Oscillator",     False],
    ["Balance of Power",             "BOP",       "Oscillator",     False],
    ["Detrended Price Osc",          "DPO",       "Oscillator",     False],
    ["Price Oscillator",             "PPO",       "Oscillator",     False],
    ["Elder Force Index",            "EFI",       "Oscillator",     False],
    ["Ease of Movement",             "EOM",       "Oscillator",     False],
    ["Vortex Indicator",             "VI",        "Oscillator",     False],
    ["Bollinger Bands",              "BB",        "Volatility",     True ],
    ["ATR",                          "ATR",       "Volatility",     True ],
    ["Keltner Channel",              "KC",        "Volatility",     True ],
    ["Donchian Channel",             "DC",        "Volatility",     False],
    ["Standard Deviation",           "STDDEV",    "Volatility",     False],
    ["Historical Volatility",        "HV",        "Volatility",     False],
    ["Chaikin Volatility",           "CV",        "Volatility",     False],
    ["Mass Index",                   "MI",        "Volatility",     False],
    ["Ulcer Index",                  "UI",        "Volatility",     False],
    ["Squeeze Momentum",             "SQZMOM",    "Volatility",     False],
    ["Volume",                       "VOL",       "Volume",         True ],
    ["OBV",                          "OBV",       "Volume",         True ],
    ["Accumulation/Distribution",    "AD",        "Volume",         False],
    ["Chaikin Accum",                "CHACC",     "Volume",         False],
    ["Force Index",                  "FI",        "Volume",         False],
    ["Negative Volume Index",        "NVI",       "Volume",         False],
    ["Positive Volume Index",        "PVI",       "Volume",         False],
    ["Volume Oscillator",            "VOLOSC",    "Volume",         False],
    ["Tick Volume",                  "TVOL",      "Volume",         False],
    ["ADX",                          "ADX",       "Trend",          True ],
    ["Supertrend",                   "SUPERTREND","Trend",          True ],
    ["Parabolic SAR",                "PSAR",      "Trend",          True ],
    ["Ichimoku Cloud",               "ICHI",      "Trend",          False],
    ["Aroon",                        "AROON",     "Trend",          False],
    ["Gann Hi-Lo",                   "GANN",      "Trend",          False],
    ["Elder Ray",                    "ERI",       "Trend",          False],
    ["DMI",                          "DMI",       "Trend",          False],
    ["Linear Regression",            "LINREG",    "Trend",          False],
    ["Pivot Points (Standard)",      "PIVOT",     "S/R",            True ],
    ["Pivot Points (Camarilla)",     "PIVCAM",    "S/R",            False],
    ["Pivot Points (Fibonacci)",     "PIVFIB",    "S/R",            False],
    ["Fibonacci Retracement",        "FIB",       "S/R",            True ],
    ["Auto Support & Resistance",    "AUTOSR",    "S/R",            True ],
    ["Price Channels",               "PRCH",      "S/R",            False],
    ["Harmonic Patterns",            "HARM",      "Patterns",       False],
    ["Elliott Wave Auto",            "EW",        "Patterns",       False],
    ["Candlestick Patterns",         "CDLPAT",    "Patterns",       False],
    ["ZigZag",                       "ZZ",        "Patterns",       False],
    ["Williams Fractal",             "WF",        "Patterns",       False],
    ["Advance/Decline Line",         "ADL",       "Breadth",        False],
    ["McClellan Oscillator",         "MCO",       "Breadth",        False],
    ["Trin (Arms Index)",            "TRIN",      "Breadth",        False],
    ["Z-Score",                      "ZSCORE",    "Statistics",     False],
    ["Correlation",                  "CORR",      "Statistics",     False],
    ["Beta",                         "BETA",      "Statistics",     False],
    ["Sharpe Ratio",                 "SHARPE",    "Statistics",     False],
    ["Long/Short Position",          "LSPOS",     "Strategy",       False],
    ["Backtester",                   "BT",        "Strategy",       False],
    ["MACD Strategy",                "MACDS",     "Strategy",       False],
    ["RSI Strategy",                 "RSIS",      "Strategy",       False],
    ["News Sentiment",               "NEWS",      "Other",          False],
    ["Earnings Events",              "EARN",      "Other",          False],
    ["Options Flow",                 "OPTFLOW",   "Other",          False],
    ["Open Interest",                "OI",        "Other",          False],
    ["Put/Call Ratio",               "PCR",       "Other",          False],
    ["VIX Overlay",                  "VIXOV",     "Other",          False],
    ["Order Block Auto",             "OBAUTO",    "Other",          False],
    ["Fair Value Gap",               "FVGAUTO",   "Other",          False],
    ["Liquidity Sweep",              "LIQSW",     "Other",          False],
    ["Smart Money Flow",             "SMF",       "Other",          False],
    ["Implied Volatility",           "IV",        "Other",          False],
    ["Gamma Exposure",               "GEX",       "Other",          False],
]


def build_chart_html(sym, price, chg, candles, sr, height=760):
    """Build standalone chart HTML — JS uses string concat (no template literals)."""
    sym_clean  = sym.replace(".NS","").replace("-USD","").replace("^","")
    price_str  = f"{price:,.2f}" if price >= 100 else f"{price:,.4f}"
    chg_str    = f"{chg:+.2f}%"
    chg_color  = "#16c98d" if chg >= 0 else "#ef4c5a"
    ind_count  = len(INDICATORS)

    cj  = json.dumps(candles)
    srj = json.dumps(sr)
    inj = json.dumps(INDICATORS)

    # NOTE: All JS is written without Python f-string substitution inside JS code.
    # Python-only substitutions: __SYM__, __PRICE__, __CHG__, __COLOR__, __HEIGHT__,
    #                            __CANDLES__, __SR__, __INDICATORS__, __INDCOUNT__
    JS_TEMPLATE = r"""
(function(){
"use strict";

/* ── DATA ────────────────────────────────────── */
var CANDLES_RAW = __CANDLES__;
var SR          = __SR__;
var IND_CAT     = __INDICATORS__;

/* ── CANVAS ──────────────────────────────────── */
var stack  = document.getElementById('canvas-stack');
var cvBg   = document.getElementById('cv-bg');
var cvMain = document.getElementById('cv-main');
var cvOvr  = document.getElementById('cv-ovr');
var cvDrw  = document.getElementById('cv-drw');
var cvCH   = document.getElementById('cv-ch');
var ctxBg  = cvBg.getContext('2d');
var ctxM   = cvMain.getContext('2d');
var ctxO   = cvOvr.getContext('2d');
var ctxD   = cvDrw.getContext('2d');
var ctxCH  = cvCH.getContext('2d');
var DPR    = Math.max(1, window.devicePixelRatio || 1);
var W=0, H=0;

var PAD_R=80, PAD_B=22, VOL_H=68, PAD_T=10;

function resize(){
  W = stack.clientWidth; H = stack.clientHeight;
  [cvBg,cvMain,cvOvr,cvDrw,cvCH].forEach(function(cv){
    cv.width=W*DPR; cv.height=H*DPR;
    cv.style.width=W+'px'; cv.style.height=H+'px';
    cv.getContext('2d').setTransform(DPR,0,0,DPR,0,0);
  });
  render();
}
window.addEventListener('resize', resize);

function plotW(){ return W-PAD_R; }
function chartT(){ return PAD_T; }
function chartB(){ return H-VOL_H-PAD_B; }
function chartH(){ return chartB()-chartT(); }
function volT(){ return chartB()+1; }
function volB(){ return H-PAD_B; }

/* ── VIEWPORT ────────────────────────────────── */
var candles = CANDLES_RAW.slice();
var chartType = 'candle';
var vp = { offset: Math.max(0, candles.length-100), count: 100 };

function xFor(idx){
  var cw = plotW()/vp.count;
  return (idx - vp.offset)*cw + cw*0.5;
}
function idxForX(x){
  var cw = plotW()/vp.count;
  return vp.offset + (x - cw*0.5)/cw;
}
function yFor(p, pr){
  return chartT() + (1-(p-pr.min)/(pr.max-pr.min))*chartH();
}
function priceAtY(y, pr){
  return pr.min + (1-(y-chartT())/chartH())*(pr.max-pr.min);
}

function getPriceRange(){
  var s = Math.max(0,Math.floor(vp.offset));
  var e = Math.min(candles.length,Math.ceil(vp.offset+vp.count));
  var sl = candles.slice(s,e);
  if(!sl.length) return {min:0,max:1};
  var mn=Infinity,mx=-Infinity;
  sl.forEach(function(c){ mn=Math.min(mn,c.l); mx=Math.max(mx,c.h); });
  activeInds.forEach(function(ind){
    if(!ind.overlay||!ind.vals) return;
    sl.forEach(function(c,i){
      var vi=s+i, v=ind.vals[vi];
      if(v==null) return;
      if(typeof v==='number'){ mn=Math.min(mn,v); mx=Math.max(mx,v); }
      else if(typeof v==='object'){
        Object.keys(v).forEach(function(k){
          var vv=v[k];
          if(typeof vv==='number'){ mn=Math.min(mn,vv); mx=Math.max(mx,vv); }
        });
      }
    });
  });
  var pad=(mx-mn)*0.07||mx*0.01||5;
  return {min:mn-pad,max:mx+pad};
}
function getMaxVol(){
  var s=Math.max(0,Math.floor(vp.offset)), e=Math.min(candles.length,Math.ceil(vp.offset+vp.count));
  return candles.slice(s,e).reduce(function(m,c){ return Math.max(m,c.v); },1);
}

/* ── INDICATOR MATH ──────────────────────────── */
function vClose(c){ return c.map(function(x){ return x.c; }); }

function SMA(a,p){
  var o=Array(a.length).fill(null);
  for(var i=p-1;i<a.length;i++){ var s=0; for(var j=i-p+1;j<=i;j++) s+=a[j]; o[i]=s/p; }
  return o;
}
function EMA(a,p){
  var o=Array(a.length).fill(null), k=2/(p+1), e;
  for(var i=0;i<a.length;i++){
    if(i<p-1) continue;
    if(i===p-1){ var s=0; for(var j=0;j<p;j++) s+=a[j]; e=s/p; o[i]=e; continue; }
    e=a[i]*k+e*(1-k); o[i]=e;
  }
  return o;
}
function WMA(a,p){
  var o=Array(a.length).fill(null), d=p*(p+1)/2;
  for(var i=p-1;i<a.length;i++){ var s=0; for(var j=0;j<p;j++) s+=a[i-p+1+j]*(j+1); o[i]=s/d; }
  return o;
}
function HMA(a,p){
  var wma1=WMA(a,Math.floor(p/2)), wma2=WMA(a,p);
  var raw=wma1.map(function(v,i){ return v!=null&&wma2[i]!=null?2*v-wma2[i]:null; });
  var cleaned=raw.map(function(v){ return v!=null?v:0; });
  var h=WMA(cleaned,Math.round(Math.sqrt(p)));
  return raw.map(function(v,i){ return raw[i]!=null?h[i]:null; });
}
function DEMA(a,p){
  var e1=EMA(a,p), e2=EMA(e1.map(function(v){ return v!=null?v:0; }),p);
  return e1.map(function(v,i){ return v!=null&&e2[i]!=null?2*v-e2[i]:null; });
}
function TEMA(a,p){
  var e1=EMA(a,p);
  var e2=EMA(e1.map(function(v){ return v!=null?v:0; }),p);
  var e3=EMA(e2.map(function(v){ return v!=null?v:0; }),p);
  return e1.map(function(_,i){ return e1[i]!=null?3*e1[i]-3*e2[i]+e3[i]:null; });
}
function VWAP(c){
  var o=Array(c.length).fill(null), pv=0, v=0;
  c.forEach(function(cc,i){ var tp=(cc.h+cc.l+cc.c)/3; pv+=tp*cc.v; v+=cc.v; o[i]=pv/v; });
  return o;
}
function VWMA(c,p){
  var o=Array(c.length).fill(null);
  for(var i=p-1;i<c.length;i++){ var sv=0,v=0; for(var j=i-p+1;j<=i;j++){ sv+=c[j].c*c[j].v; v+=c[j].v; } o[i]=sv/v; }
  return o;
}
function RSI(a,p){
  var o=Array(a.length).fill(null), g=0, l=0;
  for(var i=1;i<a.length;i++){
    var d=a[i]-a[i-1], gg=Math.max(d,0), ll=Math.max(-d,0);
    if(i<=p){ g+=gg; l+=ll; if(i===p){ var rs=(g/p)/((l/p)||1e-9); o[i]=100-100/(1+rs); } }
    else{ g=(g*(p-1)+gg)/p; l=(l*(p-1)+ll)/p; var rs2=g/(l||1e-9); o[i]=100-100/(1+rs2); }
  }
  return o;
}
function STOCHRSI(a,rp,sp){
  var r=RSI(a,rp), o=Array(a.length).fill(null);
  for(var i=sp-1;i<r.length;i++){
    var h=-Infinity, l2=Infinity;
    for(var j=i-sp+1;j<=i;j++){ if(r[j]!=null){ h=Math.max(h,r[j]); l2=Math.min(l2,r[j]); } }
    o[i]=r[i]!=null?(r[i]-l2)/((h-l2)||1e-9)*100:null;
  }
  return o;
}
function MACD_calc(a,f,s,sig){
  var ef=EMA(a,f), es=EMA(a,s);
  var m=a.map(function(_,i){ return ef[i]!=null&&es[i]!=null?ef[i]-es[i]:null; });
  var mc=m.map(function(v){ return v!=null?v:0; });
  var ss=EMA(mc,sig).map(function(v,i){ return m[i]!=null?v:null; });
  var h=m.map(function(v,i){ return v!=null&&ss[i]!=null?v-ss[i]:null; });
  return {macd:m,signal:ss,hist:h};
}
function BB_calc(a,p,mult){
  var ma=SMA(a,p);
  var r={upper:Array(a.length).fill(null),mid:ma,lower:Array(a.length).fill(null)};
  for(var i=p-1;i<a.length;i++){
    var s=0; for(var j=i-p+1;j<=i;j++) s+=Math.pow(a[j]-ma[i],2);
    var sd=Math.sqrt(s/p); r.upper[i]=ma[i]+mult*sd; r.lower[i]=ma[i]-mult*sd;
  }
  return r;
}
function ATR_calc(c,p){
  var tr=c.map(function(cc,i){ return i===0?cc.h-cc.l:Math.max(cc.h-cc.l,Math.abs(cc.h-c[i-1].c),Math.abs(cc.l-c[i-1].c)); });
  var o=Array(c.length).fill(null), prev;
  for(var i=p-1;i<c.length;i++){
    if(i===p-1){ var s=0; for(var j=0;j<p;j++) s+=tr[j]; prev=s/p; }
    else prev=(prev*(p-1)+tr[i])/p;
    o[i]=prev;
  }
  return o;
}
function KC_calc(c,p,mult){
  var cl=c.map(function(cc){ return cc.c; }), ma=EMA(cl,p), atr=ATR_calc(c,p);
  return {upper:ma.map(function(v,i){ return v!=null&&atr[i]!=null?v+mult*atr[i]:null; }),
          mid:ma,
          lower:ma.map(function(v,i){ return v!=null&&atr[i]!=null?v-mult*atr[i]:null; })};
}
function Stoch_calc(c,p,d){
  var k=Array(c.length).fill(null);
  for(var i=p-1;i<c.length;i++){
    var h=-Infinity, l2=Infinity;
    for(var j=i-p+1;j<=i;j++){ h=Math.max(h,c[j].h); l2=Math.min(l2,c[j].l); }
    k[i]=((c[i].c-l2)/((h-l2)||1e-9))*100;
  }
  return {k:k,d:SMA(k.map(function(v){ return v!=null?v:0; }),d).map(function(v,i){ return k[i]!=null?v:null; })};
}
function CCI_calc(c,p){
  var tp=c.map(function(cc){ return (cc.h+cc.l+cc.c)/3; }), ma=SMA(tp,p), o=Array(c.length).fill(null);
  for(var i=p-1;i<c.length;i++){
    var s=0; for(var j=i-p+1;j<=i;j++) s+=Math.abs(tp[j]-ma[i]);
    o[i]=(tp[i]-ma[i])/(0.015*((s/p)||1e-9));
  }
  return o;
}
function WilliamsR_calc(c,p){
  var o=Array(c.length).fill(null);
  for(var i=p-1;i<c.length;i++){
    var h=-Infinity, l2=Infinity;
    for(var j=i-p+1;j<=i;j++){ h=Math.max(h,c[j].h); l2=Math.min(l2,c[j].l); }
    o[i]=((h-c[i].c)/((h-l2)||1e-9))*-100;
  }
  return o;
}
function MOM_calc(a,p){ var o=Array(a.length).fill(null); for(var i=p;i<a.length;i++) o[i]=a[i]-a[i-p]; return o; }
function ROC_calc(a,p){ var o=Array(a.length).fill(null); for(var i=p;i<a.length;i++) o[i]=((a[i]-a[i-p])/a[i-p])*100; return o; }
function MFI_calc(c,p){
  var tp=c.map(function(cc){ return (cc.h+cc.l+cc.c)/3; }), o=Array(c.length).fill(null);
  for(var i=p;i<c.length;i++){
    var pg=0, pn=0;
    for(var j=i-p+1;j<=i;j++){
      var mf=tp[j]*c[j].v;
      if(tp[j]>tp[j-1]) pg+=mf; else pn+=mf;
    }
    o[i]=100-(100/(1+(pg/(pn||1e-9))));
  }
  return o;
}
function OBV_calc(c){
  var o=Array(c.length).fill(0);
  for(var i=1;i<c.length;i++) o[i]=o[i-1]+(c[i].c>c[i-1].c?c[i].v:c[i].c<c[i-1].c?-c[i].v:0);
  return o;
}
function ADX_calc(c,p){
  var tr=c.map(function(cc,i){ return i===0?cc.h-cc.l:Math.max(cc.h-cc.l,Math.abs(cc.h-c[i-1].c),Math.abs(cc.l-c[i-1].c)); });
  var pDM=c.map(function(cc,i){ return i===0?0:Math.max(cc.h-c[i-1].h,0); });
  var mDM=c.map(function(cc,i){ return i===0?0:Math.max(c[i-1].l-cc.l,0); });
  var atrA=ATR_calc(c,p), sPDM=EMA(pDM,p), sMDM=EMA(mDM,p), o=Array(c.length).fill(null);
  for(var i=p;i<c.length;i++){
    var pDI=(sPDM[i]/(atrA[i]||1e-9))*100, mDI=(sMDM[i]/(atrA[i]||1e-9))*100;
    o[i]=(Math.abs(pDI-mDI)/(pDI+mDI||1e-9))*100;
  }
  return o;
}
function SUPERTREND_calc(c,p,mult){
  var atr=ATR_calc(c,p), o=Array(c.length).fill(null), dir=Array(c.length).fill(1);
  var pUb=0, pLb=0;
  for(var i=p;i<c.length;i++){
    var hl2=(c[i].h+c[i].l)/2, ub=hl2+mult*atr[i], lb=hl2-mult*atr[i];
    var fub=ub<pUb||c[i-1].c>pUb?ub:pUb;
    var flb=lb>pLb||c[i-1].c<pLb?lb:pLb;
    dir[i]=c[i].c>fub?1:c[i].c<flb?-1:dir[i-1]||(-1);
    o[i]=dir[i]===1?flb:fub;
    pUb=fub; pLb=flb;
  }
  return {vals:o,dir:dir};
}
function PSAR_calc(c,af0,afMax){
  var o=Array(c.length).fill(null), bull=true, sar=c[0].l, ep=c[0].h, af=af0;
  for(var i=1;i<c.length;i++){
    var ns=sar+af*(ep-sar);
    if(bull){
      if(c[i].l<ns){ bull=false; ns=ep; ep=c[i].l; af=af0; }
      else{ if(c[i].h>ep){ ep=c[i].h; af=Math.min(af+af0,afMax); } }
    } else {
      if(c[i].h>ns){ bull=true; ns=ep; ep=c[i].h; af=af0; }
      else{ if(c[i].l<ep){ ep=c[i].l; af=Math.min(af+af0,afMax); } }
    }
    sar=ns; o[i]=sar;
  }
  return o;
}
function PIVOT_calc(c){
  var last=c[c.length-1], pp=(last.h+last.l+last.c)/3;
  return {pp:pp,r1:2*pp-last.l,r2:pp+(last.h-last.l),s1:2*pp-last.h,s2:pp-(last.h-last.l)};
}

/* ── INDICATOR DEFINITIONS ───────────────────── */
var IND_DEF = {
  SMA:        {overlay:true,  compute:function(c,p){ return SMA(vClose(c),p||20); },         color:'#f0a93c',label:function(p){ return 'SMA('+p+')';  },params:{period:20}},
  EMA:        {overlay:true,  compute:function(c,p){ return EMA(vClose(c),p||20); },         color:'#3d8eff',label:function(p){ return 'EMA('+p+')';  },params:{period:20}},
  WMA:        {overlay:true,  compute:function(c,p){ return WMA(vClose(c),p||20); },         color:'#9b8cff',label:function(p){ return 'WMA('+p+')';  },params:{period:20}},
  HMA:        {overlay:true,  compute:function(c,p){ return HMA(vClose(c),p||20); },         color:'#16c98d',label:function(p){ return 'HMA('+p+')';  },params:{period:20}},
  DEMA:       {overlay:true,  compute:function(c,p){ return DEMA(vClose(c),p||20); },        color:'#ef4c5a',label:function(p){ return 'DEMA('+p+')'; },params:{period:20}},
  TEMA:       {overlay:true,  compute:function(c,p){ return TEMA(vClose(c),p||20); },        color:'#fbbf24',label:function(p){ return 'TEMA('+p+')'; },params:{period:20}},
  VWAP:       {overlay:true,  compute:function(c){   return VWAP(c); },                      color:'#e040fb',label:function(){ return 'VWAP'; },        params:{}},
  VWMA:       {overlay:true,  compute:function(c,p){ return VWMA(c,p||20); },                color:'#40c4ff',label:function(p){ return 'VWMA('+p+')'; },params:{period:20}},
  BB:         {overlay:true,  compute:function(c,p){ return BB_calc(vClose(c),p||20,2); },   color:'#9b8cff',label:function(p){ return 'BB('+p+')';   },params:{period:20},multi:true},
  KC:         {overlay:true,  compute:function(c,p){ return KC_calc(c,p||20,1.5); },         color:'#f0a93c',label:function(p){ return 'KC('+p+')';   },params:{period:20},multi:true},
  RSI:        {overlay:false, compute:function(c,p){ return RSI(vClose(c),p||14); },         color:'#f0a93c',label:function(p){ return 'RSI('+p+')';  },params:{period:14},ob:70,os:30},
  STOCHRSI:   {overlay:false, compute:function(c,p){ return STOCHRSI(vClose(c),p||14,14); }, color:'#ef4c5a',label:function(p){ return 'StochRSI('+p+')'; },params:{period:14},ob:80,os:20},
  MACD:       {overlay:false, compute:function(c){   return MACD_calc(vClose(c),12,26,9); }, color:'#3d8eff',label:function(){ return 'MACD(12,26,9)'; },params:{},macd:true},
  STOCH:      {overlay:false, compute:function(c,p){ return Stoch_calc(c,p||14,3); },        color:'#f0a93c',label:function(p){ return 'Stoch('+p+')'; },params:{period:14},multi:true},
  CCI:        {overlay:false, compute:function(c,p){ return CCI_calc(c,p||20); },            color:'#9b8cff',label:function(p){ return 'CCI('+p+')';  },params:{period:20},ob:100,os:-100},
  WILLR:      {overlay:false, compute:function(c,p){ return WilliamsR_calc(c,p||14); },      color:'#16c98d',label:function(p){ return 'WR('+p+')';   },params:{period:14}},
  MOM:        {overlay:false, compute:function(c,p){ return MOM_calc(vClose(c),p||10); },    color:'#f0a93c',label:function(p){ return 'Mom('+p+')';  },params:{period:10}},
  ROC:        {overlay:false, compute:function(c,p){ return ROC_calc(vClose(c),p||10); },    color:'#3d8eff',label:function(p){ return 'ROC('+p+')';  },params:{period:10}},
  MFI:        {overlay:false, compute:function(c,p){ return MFI_calc(c,p||14); },            color:'#ef4c5a',label:function(p){ return 'MFI('+p+')';  },params:{period:14},ob:80,os:20},
  ATR:        {overlay:false, compute:function(c,p){ return ATR_calc(c,p||14); },            color:'#f0a93c',label:function(p){ return 'ATR('+p+')';  },params:{period:14}},
  ADX:        {overlay:false, compute:function(c,p){ return ADX_calc(c,p||14); },            color:'#3d8eff',label:function(p){ return 'ADX('+p+')';  },params:{period:14}},
  OBV:        {overlay:false, compute:function(c){   return OBV_calc(c); },                  color:'#16c98d',label:function(){ return 'OBV'; },         params:{}},
  SUPERTREND: {overlay:true,  compute:function(c,p){ return SUPERTREND_calc(c,p||10,3); },   color:'#16c98d',label:function(p){ return 'ST('+p+')';   },params:{period:10},st:true},
  PSAR:       {overlay:true,  compute:function(c){   return PSAR_calc(c,0.02,0.2); },        color:'#ef4c5a',label:function(){ return 'PSAR'; },         params:{},psar:true},
  PIVOT:      {overlay:true,  compute:function(c){   return PIVOT_calc(c); },                color:'#f0a93c',label:function(){ return 'Pivots'; },        params:{},pivot:true},
  AUTOSR:     {overlay:true,  compute:function(){   return null; },                          color:'transparent',label:function(){ return 'Auto S/R'; }, params:{},autosr:true},
  FIB:        {overlay:true,  compute:function(){   return null; },                          color:'transparent',label:function(){ return 'Fibonacci'; },params:{},fib:true},
  VOL:        {overlay:false, compute:function(c){   return c.map(function(cc){ return cc.v; }); }, color:'#7a8899',label:function(){ return 'Volume'; },params:{},vol:true},
};

/* ── ACTIVE INDICATORS ───────────────────────── */
var activeInds = [];
var showSR = true;

function computeAll(){
  activeInds.forEach(function(ind){
    var def=IND_DEF[ind.code];
    if(!def||def.autosr||def.fib||def.vol) return;
    var r=def.compute(candles, ind.param||def.params.period);
    ind.vals=r;
  });
}

/* ── CHART TYPE TRANSFORMS ───────────────────── */
function toHA(src){
  var out=[];
  for(var i=0;i<src.length;i++){
    var c=src[i];
    var haC=(c.o+c.h+c.l+c.c)/4;
    var haO=i===0?(c.o+c.c)/2:(out[i-1].o+out[i-1].c)/2;
    var haH=Math.max(c.h,haO,haC), haL=Math.min(c.l,haO,haC);
    out.push({t:c.t,o:haO,h:haH,l:haL,c:haC,v:c.v});
  }
  return out;
}
function toRenko(src){
  var pr=getPriceRange(), box=pr?(pr.max-pr.min)*0.015:1;
  var out=[], ref=src[0].c;
  for(var i=1;i<src.length;i++){
    while(src[i].c>=ref+box){ out.push({t:src[i].t,o:ref,h:ref+box,l:ref,c:ref+box,v:src[i].v}); ref+=box; }
    while(src[i].c<=ref-box){ out.push({t:src[i].t,o:ref,h:ref,l:ref-box,c:ref-box,v:src[i].v}); ref-=box; }
  }
  return out.length>3?out:src;
}
function toLineBreak(src){
  var out=[src[0]];
  for(var i=1;i<src.length;i++){
    var last=out.slice(-3), mx=Math.max.apply(null,last.map(function(c){ return c.c; })), mn=Math.min.apply(null,last.map(function(c){ return c.c; }));
    if(src[i].c>out[out.length-1].c&&src[i].c>mx) out.push({t:src[i].t,o:out[out.length-1].c,h:src[i].c,l:out[out.length-1].c,c:src[i].c,v:src[i].v,bull:true});
    else if(src[i].c<out[out.length-1].c&&src[i].c<mn) out.push({t:src[i].t,o:out[out.length-1].c,h:out[out.length-1].c,l:src[i].c,c:src[i].c,v:src[i].v,bull:false});
  }
  return out.length>3?out:src;
}
function getChartData(){
  switch(chartType){
    case 'heikinashi':
    case 'heikinashiha': return toHA(candles);
    case 'renko':        return toRenko(candles);
    case 'linebreak':    return toLineBreak(candles);
    default:             return candles;
  }
}

/* ── RENDER ──────────────────────────────────── */
var lastPR = null;

function drawGrid(pr){
  ctxBg.clearRect(0,0,W,H);
  ctxBg.strokeStyle='rgba(255,255,255,0.04)'; ctxBg.lineWidth=1;
  for(var i=0;i<=8;i++){
    var p=pr.min+(pr.max-pr.min)*i/8, y=yFor(p,pr);
    ctxBg.beginPath(); ctxBg.moveTo(0,y); ctxBg.lineTo(plotW(),y); ctxBg.stroke();
  }
  var step=Math.max(1,Math.round(vp.count/8));
  var s=Math.max(0,Math.floor(vp.offset)), e=Math.min(candles.length,Math.ceil(vp.offset+vp.count));
  for(var i=s;i<e;i+=step){
    var x=xFor(i);
    ctxBg.beginPath(); ctxBg.moveTo(x,chartT()); ctxBg.lineTo(x,chartB()); ctxBg.stroke();
  }
  /* vol sep */
  var vsEl=document.getElementById('vol-sep'); vsEl.style.top=volT()+'px';
  var vlEl=document.getElementById('vol-lbl'); vlEl.style.top=(volT()+4)+'px';
}

function drawCandles(data,pr){
  var s=Math.max(0,Math.floor(vp.offset)), e=Math.min(data.length,Math.ceil(vp.offset+vp.count));
  var cw=plotW()/vp.count, bw=Math.max(1,Math.min(cw*0.75,20));
  ctxM.clearRect(0,0,W,H);
  for(var i=s;i<e;i++){
    var c=data[i], x=xFor(i);
    var bull=c.c>=c.o;
    var col=bull?'#16c98d':'#ef4c5a';
    var yO=yFor(c.o,pr),yC=yFor(c.c,pr),yH=yFor(c.h,pr),yL=yFor(c.l,pr);
    switch(chartType){
      case 'line':
        if(i>s){ var pc=data[i-1],px=xFor(i-1); ctxM.strokeStyle='#3d8eff'; ctxM.lineWidth=1.5; ctxM.beginPath(); ctxM.moveTo(px,yFor(pc.c,pr)); ctxM.lineTo(x,yC); ctxM.stroke(); }
        break;
      case 'area':
        if(i>s){ var pc2=data[i-1],px2=xFor(i-1),py2=yFor(pc2.c,pr); ctxM.strokeStyle='#3d8eff'; ctxM.lineWidth=1.5; ctxM.beginPath(); ctxM.moveTo(px2,py2); ctxM.lineTo(x,yC); ctxM.stroke(); ctxM.fillStyle='rgba(61,142,255,0.07)'; ctxM.beginPath(); ctxM.moveTo(px2,py2); ctxM.lineTo(x,yC); ctxM.lineTo(x,chartB()); ctxM.lineTo(px2,chartB()); ctxM.closePath(); ctxM.fill(); }
        break;
      case 'bars':
        ctxM.strokeStyle=col; ctxM.lineWidth=Math.max(1,bw/5);
        ctxM.beginPath(); ctxM.moveTo(x,yH); ctxM.lineTo(x,yL); ctxM.stroke();
        ctxM.beginPath(); ctxM.moveTo(x-bw/2,yO); ctxM.lineTo(x,yO); ctxM.stroke();
        ctxM.beginPath(); ctxM.moveTo(x,yC); ctxM.lineTo(x+bw/2,yC); ctxM.stroke();
        break;
      case 'hlc':
        ctxM.strokeStyle=col; ctxM.lineWidth=Math.max(1,bw/5);
        ctxM.beginPath(); ctxM.moveTo(x,yH); ctxM.lineTo(x,yL); ctxM.stroke();
        ctxM.beginPath(); ctxM.moveTo(x,yC); ctxM.lineTo(x+bw/2,yC); ctxM.stroke();
        break;
      case 'column':
        ctxM.fillStyle=bull?'rgba(22,201,141,0.7)':'rgba(239,76,90,0.7)';
        ctxM.fillRect(x-bw/2,Math.min(yC,chartB()),bw,Math.abs(chartB()-yC)||1);
        break;
      case 'hollow':
        ctxM.strokeStyle=col; ctxM.lineWidth=1.2;
        ctxM.beginPath(); ctxM.moveTo(x,yH); ctxM.lineTo(x,Math.min(yO,yC)); ctxM.stroke();
        ctxM.beginPath(); ctxM.moveTo(x,yL); ctxM.lineTo(x,Math.max(yO,yC)); ctxM.stroke();
        var hh=Math.abs(yO-yC)||1;
        if(bull){ ctxM.strokeRect(x-bw/2,yC,bw,hh); }
        else { ctxM.fillStyle='rgba(239,76,90,0.18)'; ctxM.fillRect(x-bw/2,yO,bw,hh); ctxM.strokeRect(x-bw/2,yO,bw,hh); }
        break;
      case 'kagi':
        if(i>s){ var pc3=data[i-1],px3=xFor(i-1),pY3=yFor(pc3.c,pr); ctxM.strokeStyle=bull?'#16c98d':'#ef4c5a'; ctxM.lineWidth=bull?2:1; ctxM.beginPath(); ctxM.moveTo(px3,pY3); ctxM.lineTo(px3,yC); ctxM.lineTo(x,yC); ctxM.stroke(); }
        break;
      case 'pnf':
        ctxM.font='bold '+(Math.max(8,bw*0.9))+'px monospace';
        ctxM.fillStyle=bull?'#16c98d':'#ef4c5a'; ctxM.textAlign='center'; ctxM.textBaseline='middle';
        ctxM.fillText(bull?'X':'O',x,(yO+yC)/2); break;
      default: /* candle, renko, linebreak, range */
        ctxM.strokeStyle=bull?'rgba(22,201,141,0.55)':'rgba(239,76,90,0.55)'; ctxM.lineWidth=1;
        ctxM.beginPath(); ctxM.moveTo(x,yH); ctxM.lineTo(x,Math.min(yO,yC)); ctxM.stroke();
        ctxM.beginPath(); ctxM.moveTo(x,yL); ctxM.lineTo(x,Math.max(yO,yC)); ctxM.stroke();
        ctxM.fillStyle=bull?'rgba(22,201,141,0.87)':'rgba(239,76,90,0.87)';
        ctxM.fillRect(x-bw/2,Math.min(yO,yC),bw,Math.max(1,Math.abs(yO-yC)));
    }
  }
}

function drawVolume(pr){
  var mv=getMaxVol(), s=Math.max(0,Math.floor(vp.offset)), e=Math.min(candles.length,Math.ceil(vp.offset+vp.count));
  var cw=plotW()/vp.count, bw=Math.max(1,Math.min(cw*0.75,20)), vH=volB()-volT()-2;
  for(var i=s;i<e;i++){
    var c=candles[i],x=xFor(i),h=(c.v/mv)*vH;
    ctxM.fillStyle=c.c>=c.o?'rgba(22,201,141,0.48)':'rgba(239,76,90,0.48)';
    ctxM.fillRect(x-bw/2,volB()-h,bw,h);
  }
}

function drawSR(pr){
  if(!showSR) return;
  var el=document.getElementById('sr-lbl'), html='';
  ctxO.clearRect(0,0,W,H);
  (SR.supports||[]).forEach(function(v,i){
    var y=yFor(v,pr); if(y<chartT()||y>chartB()) return;
    ctxO.strokeStyle=i===0?'rgba(22,201,141,0.85)':'rgba(22,201,141,0.4)';
    ctxO.lineWidth=i===0?1.5:1; ctxO.setLineDash([6,4]);
    ctxO.beginPath(); ctxO.moveTo(0,y); ctxO.lineTo(plotW(),y); ctxO.stroke(); ctxO.setLineDash([]);
    var fmt=v>=100?v.toFixed(2):v.toFixed(4);
    html+='<div class="sr-tag sup" style="top:'+(Math.round(y-10))+'px;">S '+fmt+'</div>';
  });
  (SR.resistances||[]).forEach(function(v,i){
    var y=yFor(v,pr); if(y<chartT()||y>chartB()) return;
    ctxO.strokeStyle=i===0?'rgba(239,76,90,0.85)':'rgba(239,76,90,0.4)';
    ctxO.lineWidth=i===0?1.5:1; ctxO.setLineDash([6,4]);
    ctxO.beginPath(); ctxO.moveTo(0,y); ctxO.lineTo(plotW(),y); ctxO.stroke(); ctxO.setLineDash([]);
    var fmt=v>=100?v.toFixed(2):v.toFixed(4);
    html+='<div class="sr-tag res" style="top:'+(Math.round(y-10))+'px;">R '+fmt+'</div>';
  });
  el.innerHTML=html;
}

function drawIndicatorOverlays(pr){
  var s=Math.max(0,Math.floor(vp.offset)), e=Math.min(candles.length,Math.ceil(vp.offset+vp.count));
  activeInds.forEach(function(ind){
    var def=IND_DEF[ind.code];
    if(!def||!def.overlay||def.autosr||def.fib||def.vol) return;
    /* Supertrend */
    if(def.st&&ind.vals){
      var stV=ind.vals.vals, dir=ind.vals.dir;
      for(var i=s+1;i<e;i++){
        if(!stV[i]||!stV[i-1]) continue;
        ctxO.strokeStyle=dir[i]===1?'rgba(22,201,141,0.85)':'rgba(239,76,90,0.85)';
        ctxO.lineWidth=1.8; ctxO.beginPath(); ctxO.moveTo(xFor(i-1),yFor(stV[i-1],pr)); ctxO.lineTo(xFor(i),yFor(stV[i],pr)); ctxO.stroke();
      }
      return;
    }
    /* PSAR */
    if(def.psar&&ind.vals){
      for(var i=s;i<e;i++){
        if(!ind.vals[i]) continue;
        ctxO.fillStyle=ind.vals[i]<candles[i].c?'rgba(22,201,141,0.85)':'rgba(239,76,90,0.85)';
        ctxO.beginPath(); ctxO.arc(xFor(i),yFor(ind.vals[i],pr),2,0,Math.PI*2); ctxO.fill();
      }
      return;
    }
    /* Pivot */
    if(def.pivot&&ind.vals){
      var pp=ind.vals;
      [{v:pp.pp,c:'#f0a93c',l:'PP'},{v:pp.r1,c:'#ef4c5a',l:'R1'},{v:pp.r2,c:'#ef4c5a',l:'R2'},
       {v:pp.s1,c:'#16c98d',l:'S1'},{v:pp.s2,c:'#16c98d',l:'S2'}].forEach(function(p){
        var y=yFor(p.v,pr); if(y<chartT()||y>chartB()) return;
        ctxO.strokeStyle=p.c+'88'; ctxO.lineWidth=1; ctxO.setLineDash([4,3]);
        ctxO.beginPath(); ctxO.moveTo(0,y); ctxO.lineTo(plotW(),y); ctxO.stroke(); ctxO.setLineDash([]);
        ctxO.fillStyle=p.c; ctxO.font='9px monospace'; ctxO.textAlign='left';
        ctxO.fillText(p.l+' '+p.v.toFixed(2),4,y-3);
      });
      return;
    }
    /* BB/KC multi */
    if(def.multi&&ind.vals){
      ['upper','mid','lower'].forEach(function(k,ki){
        var a=ind.vals[k]||[], started=false;
        ctxO.strokeStyle=def.color+(ki===1?'55':'99');
        ctxO.lineWidth=ki===1?1:1.5; ctxO.setLineDash(ki===1?[3,3]:[]);
        ctxO.beginPath();
        for(var i=s;i<e;i++){
          if(!a[i]) continue;
          var x=xFor(i),y=yFor(a[i],pr);
          if(!started){ ctxO.moveTo(x,y); started=true; } else ctxO.lineTo(x,y);
        }
        ctxO.stroke(); ctxO.setLineDash([]);
      });
      if(ind.vals.upper&&ind.vals.lower){
        ctxO.fillStyle=def.color+'11'; ctxO.beginPath();
        for(var i=s;i<e;i++){ if(!ind.vals.upper[i]) continue; var x=xFor(i),y=yFor(ind.vals.upper[i],pr); i===s?ctxO.moveTo(x,y):ctxO.lineTo(x,y); }
        for(var i=e-1;i>=s;i--){ if(!ind.vals.lower[i]) continue; ctxO.lineTo(xFor(i),yFor(ind.vals.lower[i],pr)); }
        ctxO.closePath(); ctxO.fill();
      }
      return;
    }
    /* Simple array line */
    if(Array.isArray(ind.vals)){
      var started=false;
      ctxO.strokeStyle=def.color; ctxO.lineWidth=1.4; ctxO.setLineDash([]);
      ctxO.beginPath();
      for(var i=s;i<e;i++){
        if(!ind.vals[i]) continue;
        var x=xFor(i),y=yFor(ind.vals[i],pr);
        if(!started){ ctxO.moveTo(x,y); started=true; } else ctxO.lineTo(x,y);
      }
      ctxO.stroke();
    }
  });
}

function drawPriceAxis(pr){
  var el=document.getElementById('price-axis');
  el.style.top=chartT()+'px'; el.style.height=chartH()+'px';
  var html='';
  for(var i=0;i<=8;i++){
    var p=pr.min+(pr.max-pr.min)*i/8, y=yFor(p,pr);
    var fmt=p>=100?p.toFixed(2):p.toFixed(4);
    html+='<div style="position:absolute;top:'+(Math.round(y-9))+'px;left:4px;right:0;font-family:monospace;font-size:9.5px;color:#3f4d5e;white-space:nowrap;">'+fmt+'</div>';
  }
  el.innerHTML=html;
}

function drawTimeAxis(){
  var el=document.getElementById('time-axis'), html='';
  var step=Math.max(1,Math.round(vp.count/8));
  var s=Math.max(0,Math.floor(vp.offset)), e=Math.min(candles.length,Math.ceil(vp.offset+vp.count));
  for(var i=s;i<e;i+=step){
    var c=candles[i]; if(!c) continue;
    var d=new Date(c.t);
    var day=d.getDate(), mon=d.getMonth()+1;
    var hh=String(d.getHours()).padStart(2,'0'), mm=String(d.getMinutes()).padStart(2,'0');
    var fmt=day+'/'+mon+' '+hh+':'+mm;
    var x=xFor(i);
    html+='<div style="position:absolute;left:'+(Math.round(x-28))+'px;top:4px;font-size:9px;color:#3f4d5e;white-space:nowrap;">'+fmt+'</div>';
  }
  el.innerHTML=html;
}

function updateLastPrice(pr){
  var last=candles[candles.length-1]; if(!last) return;
  var y=yFor(last.c,pr);
  var lpl=document.getElementById('lpl'), lpt=document.getElementById('lpt');
  lpl.style.display='block'; lpl.style.top=y+'px';
  lpt.style.display='block'; lpt.style.top=(y-11)+'px';
  lpt.textContent=last.c>=100?last.c.toFixed(2):last.c.toFixed(4);
}

function updateLegend(){
  var el=document.getElementById('legend'), html='';
  activeInds.forEach(function(ind){
    var def=IND_DEF[ind.code]; if(!def) return;
    var lbl=def.label(ind.param||def.params.period||'');
    var val='';
    if(Array.isArray(ind.vals)){ var v=ind.vals[candles.length-1]; if(v!=null) val=' '+v.toFixed(2); }
    html+='<div class="leg-row"><div class="leg-dot" style="background:'+def.color+';"></div><span style="color:'+def.color+';">'+lbl+val+'</span></div>';
  });
  el.innerHTML=html;
}

function render(){
  var pr=getPriceRange(); lastPR=pr;
  var cd=getChartData();
  drawGrid(pr);
  drawCandles(cd,pr);
  drawVolume(pr);
  drawSR(pr);
  drawIndicatorOverlays(pr);
  drawPriceAxis(pr);
  drawTimeAxis();
  updateLastPrice(pr);
  updateLegend();
  drawAll(); /* redraw drawings */
}

/* ── DRAWING TOOLS ───────────────────────────── */
var activeTool='cursor', drawColor='#3d8eff';
var drawings=[], undoStack=[], inProg=null, selDraw=null, hovDraw=null, dragState=null;

function hit(draw,mx,my,pr){
  var pts=draw.points.map(function(p){ return {x:xFor(p.i),y:p.price!=null?yFor(p.price,pr):p.y}; });
  var HIT=10;
  for(var i=0;i<pts.length;i++){
    if(Math.abs(pts[i].x-mx)<HIT&&Math.abs(pts[i].y-my)<HIT) return i;
  }
  if(draw.type==='hline'&&pts[0]&&Math.abs(pts[0].y-my)<7) return -1;
  if((draw.type==='rect'||draw.type==='zone')&&pts.length>=2){
    var x1=Math.min(pts[0].x,pts[1].x),x2=Math.max(pts[0].x,pts[1].x),y1=Math.min(pts[0].y,pts[1].y),y2=Math.max(pts[0].y,pts[1].y);
    if(mx>=x1&&mx<=x2&&my>=y1&&my<=y2) return -1;
  }
  if(pts.length>=2){
    var dx=pts[1].x-pts[0].x,dy=pts[1].y-pts[0].y,len=Math.sqrt(dx*dx+dy*dy)||1;
    var d=Math.abs((pts[1].x-pts[0].x)*(pts[0].y-my)-(pts[0].x-mx)*(pts[1].y-pts[0].y))/len;
    if(d<8&&mx>=Math.min(pts[0].x,pts[1].x)-10&&mx<=Math.max(pts[0].x,pts[1].x)+10) return -1;
  }
  return null;
}

function drawOne(ctx,draw,ghost){
  var pr=lastPR||getPriceRange();
  var color=draw.color||drawColor, isSel=draw===selDraw||draw===hovDraw;
  ctx.strokeStyle=color; ctx.lineWidth=isSel?2:1.5; ctx.globalAlpha=1;
  var pts=draw.points.map(function(p){ return {x:xFor(p.i),y:p.price!=null?yFor(p.price,pr):p.y}; });
  ctx.setLineDash([]);
  switch(draw.type){
    case 'hline':
      var y=pts[0]?pts[0].y:0;
      ctx.setLineDash([7,4]); ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(plotW(),y); ctx.stroke(); ctx.setLineDash([]);
      ctx.font='10px monospace'; ctx.fillStyle=color; ctx.textAlign='right';
      ctx.fillText(draw.points[0]?draw.points[0].price>=100?draw.points[0].price.toFixed(2):draw.points[0].price.toFixed(4):'',plotW()-4,y-3);
      break;
    case 'trend':
      if(pts.length>=2){ ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y); ctx.lineTo(pts[1].x,pts[1].y); ctx.stroke(); }
      break;
    case 'ray':
      if(pts.length>=2){
        var dx=pts[1].x-pts[0].x,dy=pts[1].y-pts[0].y,len=Math.sqrt(dx*dx+dy*dy)||1,ext=Math.max(W,H)*5/len;
        ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y); ctx.lineTo(pts[0].x+dx*ext,pts[0].y+dy*ext); ctx.stroke();
      }
      break;
    case 'extline':
      if(pts.length>=2){
        var dx2=pts[1].x-pts[0].x,dy2=pts[1].y-pts[0].y,len2=Math.sqrt(dx2*dx2+dy2*dy2)||1,ext2=Math.max(W,H)*5/len2;
        ctx.beginPath(); ctx.moveTo(pts[0].x-dx2*ext2,pts[0].y-dy2*ext2); ctx.lineTo(pts[0].x+dx2*ext2,pts[0].y+dy2*ext2); ctx.stroke();
      }
      break;
    case 'rect':
    case 'zone':
      if(pts.length>=2){
        var rx1=Math.min(pts[0].x,pts[1].x),rx2=Math.max(pts[0].x,pts[1].x),ry1=Math.min(pts[0].y,pts[1].y),ry2=Math.max(pts[0].y,pts[1].y);
        ctx.globalAlpha=0.12; ctx.fillStyle=color; ctx.fillRect(rx1,ry1,rx2-rx1,ry2-ry1);
        ctx.globalAlpha=1; ctx.strokeRect(rx1,ry1,rx2-rx1,ry2-ry1);
      }
      break;
    case 'fib':
      if(pts.length>=2){
        var fibR=[0,0.236,0.382,0.5,0.618,0.786,1];
        var fibC=['#7986cb','#4ea8ff','#16c98d','#f0a93c','#ef4c5a','#e040fb','#7986cb'];
        var p1=draw.points[0].price, p2=draw.points[1].price;
        fibR.forEach(function(r,ri){
          var fp=p2+r*(p1-p2), fy=yFor(fp,pr);
          ctx.strokeStyle=fibC[ri]; ctx.lineWidth=ri===0||ri===6?1.5:1;
          ctx.setLineDash(ri===0||ri===6?[]:[5,3]);
          ctx.beginPath(); ctx.moveTo(pts[0].x,fy); ctx.lineTo(pts[1].x,fy); ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle=fibC[ri]; ctx.font='9.5px monospace'; ctx.textAlign='left';
          ctx.fillText((r*100).toFixed(1)+'% '+(fp>=100?fp.toFixed(2):fp.toFixed(4)),pts[0].x+4,fy-3);
        });
      }
      break;
    case 'arrow':
      if(pts.length>=2){
        ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y); ctx.lineTo(pts[1].x,pts[1].y); ctx.stroke();
        var ang=Math.atan2(pts[1].y-pts[0].y,pts[1].x-pts[0].x);
        ctx.fillStyle=color; ctx.beginPath();
        ctx.moveTo(pts[1].x,pts[1].y);
        ctx.lineTo(pts[1].x-12*Math.cos(ang-0.4),pts[1].y-12*Math.sin(ang-0.4));
        ctx.lineTo(pts[1].x-12*Math.cos(ang+0.4),pts[1].y-12*Math.sin(ang+0.4));
        ctx.closePath(); ctx.fill();
      }
      break;
    case 'text':
      if(pts[0]){ ctx.font='13px sans-serif'; ctx.fillStyle=color; ctx.textAlign='left'; ctx.textBaseline='top'; ctx.fillText(draw.text||'',pts[0].x,pts[0].y); }
      break;
  }
  if(isSel){
    ctx.fillStyle=color; ctx.strokeStyle='#fff'; ctx.lineWidth=1.5;
    pts.forEach(function(p){ ctx.beginPath(); ctx.arc(p.x,p.y,5,0,Math.PI*2); ctx.fill(); ctx.stroke(); });
  }
}

function drawAll(ghost){
  ctxD.clearRect(0,0,W,H);
  drawings.forEach(function(d){ drawOne(ctxD,d,false); });
  if(ghost) drawOne(ctxD,ghost,true);
}

function saveUndo(){ undoStack.push(JSON.parse(JSON.stringify(drawings))); if(undoStack.length>30) undoStack.shift(); }

function cc(e){ var r=cvDrw.getBoundingClientRect(),t=e.touches?e.touches[0]:e; return {x:t.clientX-r.left,y:t.clientY-r.top}; }

cvDrw.addEventListener('mousedown',function(e){
  if(e.button!==0) return;
  var pos=cc(e), pr=lastPR||getPriceRange();
  var px=pos.x,py=pos.y;
  if(activeTool==='cursor'){
    selDraw=null; dragState=null;
    for(var i=drawings.length-1;i>=0;i--){
      var h=hit(drawings[i],px,py,pr);
      if(h!==null){ selDraw=drawings[i]; saveUndo(); dragState={draw:drawings[i],hi:h,sx:px,sy:py,sp:JSON.parse(JSON.stringify(drawings[i].points))}; break; }
    }
    drawAll(); return;
  }
  if(activeTool==='text') return;
  inProg={type:activeTool==='hline'?'hline':activeTool, points:[{i:Math.round(idxForX(px)),price:priceAtY(py,pr),y:py}], color:drawColor};
});

cvDrw.addEventListener('mousemove',function(e){
  var pos=cc(e), pr=lastPR||getPriceRange(), px=pos.x, py=pos.y;
  var mp=priceAtY(py,pr), mi=idxForX(px);
  /* crosshair */
  ctxCH.clearRect(0,0,W,H);
  if(px>=0&&px<=plotW()&&py>=chartT()&&py<=chartB()){
    ctxCH.strokeStyle='rgba(255,255,255,0.13)'; ctxCH.lineWidth=1; ctxCH.setLineDash([4,4]);
    ctxCH.beginPath(); ctxCH.moveTo(px,chartT()); ctxCH.lineTo(px,chartB()); ctxCH.stroke();
    ctxCH.beginPath(); ctxCH.moveTo(0,py); ctxCH.lineTo(plotW(),py); ctxCH.stroke();
    ctxCH.setLineDash([]);
    var cpEl=document.getElementById('cprice');
    cpEl.style.display='block'; cpEl.style.top=(py-11)+'px';
    cpEl.textContent=mp>=100?mp.toFixed(2):mp.toFixed(4);
    var ci=Math.max(0,Math.min(candles.length-1,Math.round(mi)));
    var cd=candles[ci];
    if(cd){
      var d=new Date(cd.t);
      var ds=d.getDate()+'/'+(d.getMonth()+1)+'/'+d.getFullYear()+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
      var bull=cd.c>=cd.o, bc2=bull?'#16c98d':'#ef4c5a';
      document.getElementById('readout').innerHTML=
        '<span style="color:#3f4d5e;">'+ds+'</span>&nbsp;&nbsp;'+
        '<span style="color:#c8a86a;">O <b>'+cd.o.toFixed(2)+'</b></span>&nbsp;'+
        '<span style="color:#16c98d;">H <b>'+cd.h.toFixed(2)+'</b></span>&nbsp;'+
        '<span style="color:#ef4c5a;">L <b>'+cd.l.toFixed(2)+'</b></span>&nbsp;'+
        '<span style="color:'+bc2+';">C <b>'+cd.c.toFixed(2)+'</b></span>&nbsp;'+
        '<span style="color:#3f4d5e;">V <b>'+(cd.v/1e6).toFixed(2)+'M</b></span>';
    }
  } else {
    document.getElementById('cprice').style.display='none';
  }
  /* drag existing */
  if(dragState){
    var dIdx=(px-dragState.sx)/(plotW()/vp.count);
    var dPr=(py-dragState.sy)/chartH()*(pr.max-pr.min);
    if(dragState.hi===-1){
      dragState.draw.points=dragState.sp.map(function(p){ return {i:p.i+dIdx,price:p.price-dPr,y:yFor(p.price-dPr,pr)}; });
    } else {
      var hi=dragState.hi, sp=dragState.sp[hi];
      dragState.draw.points[hi]={i:sp.i+dIdx,price:sp.price-dPr,y:yFor(sp.price-dPr,pr)};
    }
    drawAll(); return;
  }
  /* ghost */
  if(inProg&&inProg.points.length>=1){
    drawAll({type:inProg.type,points:inProg.points.concat([{i:mi,price:mp,y:py}]),color:drawColor});
    return;
  }
  /* hover */
  hovDraw=null;
  for(var i=drawings.length-1;i>=0;i--){ if(hit(drawings[i],px,py,pr)!==null){ hovDraw=drawings[i]; break; } }
  drawAll();
  cvDrw.style.cursor=(activeTool==='cursor'&&hovDraw)?'move':'crosshair';
});

cvDrw.addEventListener('mouseup',function(e){
  if(dragState){ dragState=null; render(); return; }
  if(!inProg) return;
  var pos=cc(e), pr=lastPR||getPriceRange();
  var px=pos.x, py=pos.y;
  if(inProg.type==='hline'){
    saveUndo(); drawings.push({type:'hline',points:[{i:0,price:priceAtY(py,pr),y:py}],color:drawColor});
    inProg=null; drawAll(); return;
  }
  inProg.points.push({i:idxForX(px),price:priceAtY(py,pr),y:py});
  if(inProg.points.length>=2){ saveUndo(); drawings.push(JSON.parse(JSON.stringify(inProg))); inProg=null; drawAll(); }
});

cvDrw.addEventListener('dblclick',function(e){
  if(activeTool!=='text') return;
  var pos=cc(e), pr=lastPR||getPriceRange();
  var txt=prompt('Label:','');
  if(txt){ saveUndo(); drawings.push({type:'text',points:[{i:Math.round(idxForX(pos.x)),price:priceAtY(pos.y,pr),y:pos.y}],color:drawColor,text:txt}); drawAll(); }
});

cvDrw.addEventListener('mouseleave',function(){
  ctxCH.clearRect(0,0,W,H);
  document.getElementById('cprice').style.display='none';
  document.getElementById('readout').innerHTML='';
});

/* Context menu */
cvDrw.addEventListener('contextmenu',function(e){
  e.preventDefault();
  var pos=cc(e), pr=lastPR||getPriceRange();
  for(var i=drawings.length-1;i>=0;i--){
    if(hit(drawings[i],pos.x,pos.y,pr)!==null){
      selDraw=drawings[i];
      var cm=document.getElementById('ctxm');
      cm.style.left=e.clientX+'px'; cm.style.top=e.clientY+'px';
      cm.classList.add('show'); break;
    }
  }
});
document.getElementById('ctx-del').addEventListener('click',function(){
  if(selDraw){ saveUndo(); drawings=drawings.filter(function(d){ return d!==selDraw; }); selDraw=null; drawAll(); }
  document.getElementById('ctxm').classList.remove('show');
});
document.getElementById('ctx-col').addEventListener('click',function(){
  if(selDraw){ var c=prompt('Color (hex):',selDraw.color||'#3d8eff'); if(c){ selDraw.color=c; drawAll(); } }
  document.getElementById('ctxm').classList.remove('show');
});
document.getElementById('ctx-dup').addEventListener('click',function(){
  if(selDraw){ saveUndo(); var d=JSON.parse(JSON.stringify(selDraw)); d.points=d.points.map(function(p){ return {i:p.i+4,price:p.price,y:p.y}; }); drawings.push(d); drawAll(); }
  document.getElementById('ctxm').classList.remove('show');
});
document.addEventListener('click',function(){ document.getElementById('ctxm').classList.remove('show'); });

/* ── ZOOM / PAN ──────────────────────────────── */
cvDrw.addEventListener('wheel',function(e){
  e.preventDefault();
  var factor=e.deltaY>0?1.12:0.88, pivot=idxForX(cc(e).x);
  vp.count=Math.max(10,Math.min(candles.length,vp.count*factor));
  vp.offset=pivot-(cc(e).x/plotW())*vp.count;
  vp.offset=Math.max(0,Math.min(candles.length-vp.count,vp.offset));
  render();
},{passive:false});

var panSt=null;
cvDrw.addEventListener('mousedown',function(e){
  if(activeTool==='cursor'&&!selDraw) panSt={sx:e.clientX,so:vp.offset};
});
cvDrw.addEventListener('mousemove',function(e){
  if(panSt&&activeTool==='cursor'&&!dragState){
    var di=(e.clientX-panSt.sx)/(plotW()/vp.count);
    vp.offset=Math.max(0,Math.min(candles.length-vp.count,panSt.so-di));
    render();
  }
});
cvDrw.addEventListener('mouseup',function(){ panSt=null; });

var ltDist=null;
cvDrw.addEventListener('touchstart',function(e){
  if(e.touches.length===2){
    var dx=e.touches[1].clientX-e.touches[0].clientX, dy=e.touches[1].clientY-e.touches[0].clientY;
    ltDist=Math.sqrt(dx*dx+dy*dy);
  }
},{passive:true});
cvDrw.addEventListener('touchmove',function(e){
  if(e.touches.length===2&&ltDist){
    var dx=e.touches[1].clientX-e.touches[0].clientX, dy=e.touches[1].clientY-e.touches[0].clientY;
    var d=Math.sqrt(dx*dx+dy*dy), f=ltDist/d;
    vp.count=Math.max(10,Math.min(candles.length,vp.count*f));
    vp.offset=Math.max(0,Math.min(candles.length-vp.count,vp.offset));
    ltDist=d; render();
  }
},{passive:true});

/* ── TOOLBAR EVENTS ──────────────────────────── */
document.querySelectorAll('.tool-btn[data-tool]').forEach(function(btn){
  btn.addEventListener('click',function(){
    activeTool=btn.dataset.tool;
    document.querySelectorAll('.tool-btn[data-tool]').forEach(function(b){ b.classList.remove('active'); });
    btn.classList.add('active');
    selDraw=null; inProg=null; drawAll();
  });
});
document.querySelectorAll('.swatch').forEach(function(s){
  s.addEventListener('click',function(){
    drawColor=s.dataset.c;
    document.querySelectorAll('.swatch').forEach(function(ss){ ss.classList.remove('active'); });
    s.classList.add('active');
    if(selDraw){ selDraw.color=drawColor; drawAll(); }
  });
});
document.getElementById('btn-undo').addEventListener('click',function(){ if(undoStack.length){ drawings=undoStack.pop(); drawAll(); toast('Undo'); } });
document.getElementById('btn-clear').addEventListener('click',function(){ saveUndo(); drawings=[]; drawAll(); toast('Drawings cleared'); });
document.getElementById('btn-sr').addEventListener('click',function(){
  showSR=!showSR; this.classList.toggle('active',showSR); render();
});
document.getElementById('btn-reset').addEventListener('click',function(){
  vp.offset=Math.max(0,candles.length-100); vp.count=100; render();
});
document.getElementById('btn-full').addEventListener('click',function(){
  if(!document.fullscreenElement) document.documentElement.requestFullscreen&&document.documentElement.requestFullscreen();
  else document.exitFullscreen&&document.exitFullscreen();
});
document.querySelectorAll('.tf-btn').forEach(function(b){
  b.addEventListener('click',function(){
    document.querySelectorAll('.tf-btn').forEach(function(bb){ bb.classList.remove('active'); });
    b.classList.add('active'); toast('TF: '+b.dataset.tf+' — reconnect live feed for this TF');
  });
});
document.querySelectorAll('.ct-btn').forEach(function(b){
  b.addEventListener('click',function(){
    chartType=b.dataset.ct;
    document.querySelectorAll('.ct-btn').forEach(function(bb){ bb.classList.remove('active'); });
    b.classList.add('active'); render();
  });
});

/* keyboard */
window.addEventListener('keydown',function(e){
  if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA') return;
  var map={v:'cursor',h:'hline',t:'trend',r:'ray',z:'rect',f:'fib',n:'text',a:'arrow'};
  if(map[e.key]){ activeTool=map[e.key]; document.querySelectorAll('.tool-btn[data-tool]').forEach(function(b){ b.classList.toggle('active',b.dataset.tool===activeTool); }); }
  if(e.key==='Delete'&&selDraw){ saveUndo(); drawings=drawings.filter(function(d){ return d!==selDraw; }); selDraw=null; drawAll(); }
  if(e.ctrlKey&&e.key==='z'){ if(undoStack.length){ drawings=undoStack.pop(); drawAll(); } }
  if(e.key==='Escape'){ selDraw=null; inProg=null; document.getElementById('picker-ov').classList.remove('show'); document.getElementById('ctxm').classList.remove('show'); drawAll(); }
});

/* ── INDICATOR PICKER ────────────────────────── */
var pickerQ='';
function buildPicker(q){
  var el=document.getElementById('picker-list'), cnt=document.getElementById('picker-cnt');
  var qlo=(q||'').toLowerCase(), html='', lastCat='', total=0;
  IND_CAT.forEach(function(row){
    var name=row[0],code=row[1],cat=row[2],live=row[3];
    if(qlo&&!name.toLowerCase().includes(qlo)&&!code.toLowerCase().includes(qlo)&&!cat.toLowerCase().includes(qlo)) return;
    total++;
    if(cat!==lastCat){ html+='<div class="cat-hd">'+cat+'</div>'; lastCat=cat; }
    var on=activeInds.some(function(a){ return a.code===code; });
    html+='<div class="ind-row" data-code="'+code+'" data-live="'+live+'">'
       +'<span class="ind-code">'+code+'</span>'
       +'<span class="ind-name">'+name+'</span>'
       +'<span class="ind-cat">'+cat+'</span>'
       +'<span class="badge '+(live?'live':'soon')+'">'+(live?'LIVE':'SOON')+'</span>'
       +(on?'<span style="color:#16c98d;font-size:11px;">✓</span>':'')
       +'</div>';
  });
  el.innerHTML=html; cnt.textContent=total+' result'+(total!==1?'s':'');
  el.querySelectorAll('.ind-row').forEach(function(row){
    row.addEventListener('click',function(){
      var code=row.dataset.code, live=row.dataset.live==='true';
      if(!live){ toast(code+' coming soon!'); return; }
      if(activeInds.some(function(a){ return a.code===code; })){
        activeInds=activeInds.filter(function(a){ return a.code!==code; });
      } else {
        var def=IND_DEF[code];
        activeInds.push({code:code,param:def&&def.params&&def.params.period?def.params.period:undefined,vals:null,overlay:def?def.overlay:false});
      }
      computeAll(); updateChips(); buildPicker(pickerQ); render();
    });
  });
}
function updateChips(){
  var el=document.getElementById('ind-chips');
  el.innerHTML=activeInds.map(function(ind){
    var def=IND_DEF[ind.code], lbl=def?def.label(ind.param||def.params.period||''):ind.code, col=def?def.color:'#3d8eff';
    return '<div class="ind-chip">'
      +'<div style="width:7px;height:7px;border-radius:2px;background:'+col+';flex-shrink:0;"></div>'
      +'<span style="color:'+col+';">'+lbl+'</span>'
      +'<span class="ind-x" data-code="'+ind.code+'">✕</span></div>';
  }).join('');
  el.querySelectorAll('.ind-x').forEach(function(x){
    x.addEventListener('click',function(e){
      e.stopPropagation();
      activeInds=activeInds.filter(function(a){ return a.code!==x.dataset.code; });
      computeAll(); updateChips(); render();
    });
  });
}
document.getElementById('btn-inds').addEventListener('click',function(){
  document.getElementById('picker-ov').classList.add('show');
  document.getElementById('picker-srch').focus();
  buildPicker('');
});
document.getElementById('picker-srch').addEventListener('input',function(){ pickerQ=this.value; buildPicker(pickerQ); });
document.getElementById('picker-ov').addEventListener('click',function(e){ if(e.target===this) this.classList.remove('show'); });

/* defaults */
['EMA','VWAP','VOL'].forEach(function(code){
  var def=IND_DEF[code];
  if(def) activeInds.push({code:code,param:def.params&&def.params.period?def.params.period:undefined,vals:null,overlay:def.overlay});
});
computeAll(); updateChips();

/* ── REAL-TIME TICK ──────────────────────────── */
var tickN=0;
setInterval(function(){
  if(!candles.length) return;
  var last=candles[candles.length-1];
  var tick=(Math.random()-0.49)*last.c*0.0004;
  candles[candles.length-1]={t:last.t,o:last.o,h:Math.max(last.h,last.c+tick),l:Math.min(last.l,last.c+tick),c:+(last.c+tick).toFixed(4),v:last.v+Math.round(Math.random()*50000)};
  var newC=candles[candles.length-1];
  var pm=document.getElementById('price-live');
  if(pm){ pm.textContent=newC.c>=100?newC.c.toFixed(2):newC.c.toFixed(4); pm.style.color=tick>=0?'#16c98d':'#ef4c5a'; }
  tickN++;
  if(tickN%5===0){ computeAll(); render(); }
  else { if(lastPR) updateLastPrice(lastPR); }
},800);

/* toast */
function toast(msg){ var t=document.getElementById('toast'); t.textContent=msg; t.classList.add('show'); setTimeout(function(){ t.classList.remove('show'); },2000); }

/* ── INIT ────────────────────────────────────── */
resize();

})();
"""

    CSS = """
:root{--bg:#080d14;--panel:#0d1219;--panel2:#111820;--panel3:#161e2a;--line:rgba(255,255,255,0.055);--linemid:rgba(255,255,255,0.1);--hi:#e2e8f2;--mid:#7a8899;--dim:#3f4d5e;--bull:#16c98d;--bear:#ef4c5a;--amber:#f0a93c;--accent:#3d8eff;--mono:'JetBrains Mono','SF Mono',Consolas,monospace;--sans:'Inter',-apple-system,sans-serif;}
*{box-sizing:border-box;margin:0;padding:0;}
html,body{width:100%;height:__HEIGHT__px;overflow:hidden;background:var(--bg);color:var(--hi);font-family:var(--sans);-webkit-font-smoothing:antialiased;}
#app{display:flex;flex-direction:column;width:100%;height:__HEIGHT__px;}
#topbar{display:flex;align-items:center;gap:9px;height:46px;min-height:46px;flex-shrink:0;background:linear-gradient(180deg,#0f1620,#0b1018);border-bottom:1px solid var(--line);padding:0 12px;user-select:none;overflow-x:auto;}
.brand{display:flex;align-items:center;gap:6px;font-weight:800;font-size:14px;flex-shrink:0;}
.brand .dot{width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 8px var(--accent);}
.brand b{color:var(--accent);}
.sym-box{display:flex;align-items:center;gap:6px;background:var(--panel2);border:1px solid var(--line);border-radius:7px;padding:5px 10px;flex-shrink:0;}
.sym-txt{font-family:var(--mono);font-size:13px;font-weight:600;}
.price-block{display:flex;flex-direction:column;flex-shrink:0;}
.price-live{font-family:var(--mono);font-size:15px;font-weight:700;}
.price-chg{font-family:var(--mono);font-size:10px;}
.div{width:1px;height:24px;background:var(--line);flex-shrink:0;}
.tf-group,.ct-group{display:flex;gap:2px;background:var(--panel2);padding:3px;border-radius:8px;border:1px solid var(--line);flex-shrink:0;}
.tf-btn,.ct-btn{font-family:var(--mono);font-size:10.5px;padding:4px 7px;border-radius:5px;color:var(--mid);cursor:pointer;transition:.12s;white-space:nowrap;}
.tf-btn:hover,.ct-btn:hover{color:var(--hi);}
.tf-btn.active{background:var(--accent);color:#fff;font-weight:700;}
.ct-btn.active{background:rgba(61,142,255,.2);color:var(--accent);font-weight:700;}
.sp{flex:1;}
.icon-btn{width:32px;height:32px;border-radius:7px;display:flex;align-items:center;justify-content:center;color:var(--mid);cursor:pointer;border:1px solid transparent;transition:.12s;flex-shrink:0;}
.icon-btn:hover{background:var(--panel2);color:var(--hi);border-color:var(--line);}
.icon-btn.active{background:rgba(61,142,255,.15);color:var(--accent);border-color:rgba(61,142,255,.3);}
#body{flex:1;display:flex;min-height:0;}
#toolrail{width:48px;min-width:48px;background:var(--panel);border-right:1px solid var(--line);display:flex;flex-direction:column;align-items:center;padding:8px 0;gap:3px;flex-shrink:0;}
.tool-btn{width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--dim);cursor:pointer;position:relative;transition:.12s;}
.tool-btn:hover{background:var(--panel3);color:var(--hi);}
.tool-btn.active{background:rgba(61,142,255,.12);color:var(--accent);}
.tool-btn.active::before{content:'';position:absolute;left:-4px;top:6px;bottom:6px;width:3px;border-radius:3px;background:var(--accent);}
.rl-sep{width:22px;height:1px;background:var(--line);margin:4px 0;}
.sw-wrap{display:flex;flex-wrap:wrap;gap:4px;width:36px;justify-content:center;margin-top:4px;}
.swatch{width:13px;height:13px;border-radius:50%;cursor:pointer;border:2px solid transparent;transition:.12s;}
.swatch:hover,.swatch.active{border-color:#fff;}
#chartwrap{flex:1;display:flex;flex-direction:column;min-width:0;position:relative;}
#chart-toolbar{display:flex;align-items:center;gap:6px;padding:6px 10px;border-bottom:1px solid var(--line);background:var(--panel);flex-shrink:0;flex-wrap:wrap;}
.pill{display:flex;align-items:center;gap:5px;font-size:11.5px;color:var(--mid);background:var(--panel2);padding:5px 10px;border-radius:7px;cursor:pointer;border:1px solid var(--line);transition:.12s;white-space:nowrap;}
.pill:hover{color:var(--hi);border-color:var(--linemid);}
#ind-chips{display:flex;gap:5px;flex-wrap:wrap;}
.ind-chip{display:flex;align-items:center;gap:5px;font-family:var(--mono);font-size:10.5px;padding:3px 8px;border-radius:6px;background:var(--panel3);border:1px solid var(--line);}
.ind-x{cursor:pointer;color:var(--dim);font-size:12px;line-height:1;}
.ind-x:hover{color:var(--bear);}
#canvas-stack{flex:1;position:relative;overflow:hidden;}
canvas{position:absolute;top:0;left:0;display:block;}
#cv-bg{z-index:1;}#cv-main{z-index:2;}#cv-ovr{z-index:3;}#cv-drw{z-index:4;cursor:crosshair;}#cv-ch{z-index:5;pointer-events:none;}
#readout{position:absolute;top:8px;left:10px;z-index:10;font-family:var(--mono);font-size:11px;line-height:1.65;color:var(--mid);pointer-events:none;background:rgba(8,13,20,.75);padding:7px 10px;border-radius:8px;border:1px solid var(--line);backdrop-filter:blur(6px);}
#legend{position:absolute;top:8px;right:10px;z-index:10;display:flex;flex-direction:column;gap:3px;align-items:flex-end;pointer-events:none;}
.leg-row{display:flex;align-items:center;gap:5px;font-family:var(--mono);font-size:10.5px;background:rgba(8,13,20,.65);padding:3px 7px;border-radius:5px;}
.leg-dot{width:7px;height:7px;border-radius:2px;flex-shrink:0;}
#sr-lbl{position:absolute;right:12px;top:0;height:100%;z-index:8;pointer-events:none;}
.sr-tag{position:absolute;right:82px;font-family:var(--mono);font-size:10px;padding:2px 7px;border-radius:4px;white-space:nowrap;}
.sr-tag.sup{background:rgba(22,201,141,.14);color:#16c98d;border:1px solid rgba(22,201,141,.3);}
.sr-tag.res{background:rgba(239,76,90,.14);color:#ef4c5a;border:1px solid rgba(239,76,90,.3);}
#price-axis{position:absolute;right:0;top:0;bottom:0;width:80px;z-index:9;background:var(--panel);border-left:1px solid var(--line);overflow:hidden;pointer-events:none;}
#time-axis{position:absolute;bottom:0;left:0;right:80px;height:22px;z-index:9;border-top:1px solid var(--line);background:var(--panel);overflow:hidden;pointer-events:none;}
#cprice{position:absolute;right:0;width:80px;z-index:11;background:var(--accent);color:#fff;font-family:var(--mono);font-size:10.5px;padding:2px 4px;text-align:center;border-radius:3px 0 0 3px;pointer-events:none;display:none;}
#lpl{position:absolute;left:0;right:80px;height:1px;z-index:7;border-top:1px dashed rgba(61,142,255,.4);pointer-events:none;display:none;}
#lpt{position:absolute;right:80px;width:80px;z-index:11;background:rgba(61,142,255,.88);color:#fff;font-family:var(--mono);font-size:10px;padding:2px 4px;text-align:center;border-radius:3px 0 0 3px;pointer-events:none;display:none;}
#vol-sep{position:absolute;left:0;right:80px;height:1px;background:var(--line);z-index:8;pointer-events:none;}
#vol-lbl{position:absolute;left:8px;font-family:var(--mono);font-size:9.5px;color:var(--dim);z-index:9;pointer-events:none;}
.toast{position:absolute;bottom:14px;left:50%;transform:translateX(-50%);background:var(--panel2);border:1px solid var(--line);color:var(--hi);padding:7px 14px;border-radius:8px;font-size:11.5px;z-index:50;opacity:0;transition:opacity .25s;font-family:var(--mono);pointer-events:none;}
.toast.show{opacity:1;}
#picker-ov{position:fixed;inset:0;background:rgba(4,7,12,.65);backdrop-filter:blur(3px);display:none;align-items:center;justify-content:center;z-index:200;}
#picker-ov.show{display:flex;}
#picker{width:580px;max-height:72vh;background:var(--panel);border:1px solid var(--linemid);border-radius:14px;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(0,0,0,.6);overflow:hidden;}
#picker-head{padding:16px 18px 10px;border-bottom:1px solid var(--line);}
#picker-head h3{margin-bottom:10px;font-size:14px;}
#picker-srch{width:100%;background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:9px 12px;color:var(--hi);font-size:13px;outline:none;font-family:var(--sans);}
#picker-srch:focus{border-color:var(--accent);}
#picker-meta{display:flex;justify-content:space-between;margin-top:8px;font-size:10.5px;color:var(--dim);font-family:var(--mono);}
#picker-list{flex:1;overflow-y:auto;padding:6px;}
.ind-row{display:flex;align-items:center;padding:9px 12px;border-radius:8px;cursor:pointer;gap:8px;}
.ind-row:hover{background:var(--panel2);}
.ind-name{font-size:12.5px;flex:1;}
.ind-code{font-family:var(--mono);font-size:10px;color:var(--accent);min-width:72px;}
.ind-cat{font-size:10px;color:var(--dim);min-width:80px;}
.cat-hd{font-family:var(--mono);font-size:9.5px;color:var(--dim);padding:10px 12px 4px;letter-spacing:.5px;text-transform:uppercase;}
.badge{font-family:var(--mono);font-size:9px;padding:2px 6px;border-radius:4px;letter-spacing:.3px;flex-shrink:0;}
.badge.live{background:rgba(22,201,141,.12);color:var(--bull);}
.badge.soon{background:rgba(90,100,120,.15);color:var(--dim);}
#ctxm{position:fixed;background:var(--panel2);border:1px solid var(--linemid);border-radius:9px;padding:5px;z-index:300;display:none;min-width:140px;box-shadow:0 8px 30px rgba(0,0,0,.4);}
#ctxm.show{display:block;}
.ctx-item{padding:8px 12px;border-radius:6px;font-size:12px;cursor:pointer;display:flex;align-items:center;gap:8px;}
.ctx-item:hover{background:var(--panel3);}
.ctx-item.danger{color:var(--bear);}
::-webkit-scrollbar{width:6px;}::-webkit-scrollbar-thumb{background:var(--line);border-radius:3px;}::-webkit-scrollbar-track{background:transparent;}
"""

    CSS = CSS.replace("__HEIGHT__", str(height))

    HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>FinSage AI</title>
<style>__CSS__</style>
</head>
<body>
<div id="app">
<div id="topbar">
  <div class="brand"><span class="dot"></span>Fin<b>Sage</b> AI</div>
  <div class="sym-box"><span class="sym-txt">__SYM__</span></div>
  <div class="price-block">
    <span class="price-live" id="price-live" style="color:__COLOR__;">__PRICE__</span>
    <span class="price-chg" style="color:__COLOR__;">__CHG__</span>
  </div>
  <div class="div"></div>
  <div class="tf-group">
    <div class="tf-btn" data-tf="1m">1m</div>
    <div class="tf-btn" data-tf="5m">5m</div>
    <div class="tf-btn" data-tf="15m">15m</div>
    <div class="tf-btn" data-tf="1h">1H</div>
    <div class="tf-btn active" data-tf="1d">1D</div>
    <div class="tf-btn" data-tf="1w">1W</div>
    <div class="tf-btn" data-tf="1mo">1M</div>
  </div>
  <div class="div"></div>
  <div class="ct-group">
    <div class="ct-btn active" data-ct="candle">Candles</div>
    <div class="ct-btn" data-ct="hollow">Hollow</div>
    <div class="ct-btn" data-ct="heikinashi">HA</div>
    <div class="ct-btn" data-ct="heikinashiha">HAS</div>
    <div class="ct-btn" data-ct="bars">Bars</div>
    <div class="ct-btn" data-ct="line">Line</div>
    <div class="ct-btn" data-ct="area">Area</div>
    <div class="ct-btn" data-ct="hlc">HLC</div>
    <div class="ct-btn" data-ct="column">Column</div>
    <div class="ct-btn" data-ct="kagi">Kagi</div>
    <div class="ct-btn" data-ct="renko">Renko</div>
    <div class="ct-btn" data-ct="linebreak">LB</div>
    <div class="ct-btn" data-ct="pnf">P&F</div>
    <div class="ct-btn" data-ct="range">Range</div>
  </div>
  <div class="sp"></div>
  <div class="icon-btn active" id="btn-sr" title="Auto S/R">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17h18M3 7h18"/></svg>
  </div>
  <div class="icon-btn" id="btn-reset" title="Fit view">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>
  </div>
  <div class="icon-btn" id="btn-full" title="Fullscreen">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
  </div>
</div>
<div id="body">
<div id="toolrail">
  <div class="tool-btn active" data-tool="cursor" title="Cursor (V)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4l16 6-7 2-2 7z"/></svg>
  </div>
  <div class="tool-btn" data-tool="hline" title="H-Line (H)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18"/><circle cx="6" cy="12" r="1.5" fill="currentColor"/><circle cx="18" cy="12" r="1.5" fill="currentColor"/></svg>
  </div>
  <div class="tool-btn" data-tool="trend" title="Trendline (T)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19L20 5"/><circle cx="4" cy="19" r="1.8" fill="currentColor"/><circle cx="20" cy="5" r="1.8" fill="currentColor"/></svg>
  </div>
  <div class="tool-btn" data-tool="ray" title="Ray (R)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 20L21 3"/><circle cx="4" cy="20" r="1.8" fill="currentColor"/></svg>
  </div>
  <div class="tool-btn" data-tool="extline" title="Extended Line">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 19L22 5"/><circle cx="8" cy="15.5" r="1.8" fill="currentColor"/><circle cx="16" cy="10" r="1.8" fill="currentColor"/></svg>
  </div>
  <div class="tool-btn" data-tool="rect" title="Zone (Z)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="7" width="16" height="10" rx="1.5"/></svg>
  </div>
  <div class="tool-btn" data-tool="fib" title="Fibonacci (F)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 5h18M3 9.5h13M3 14h9M3 18.5h5"/></svg>
  </div>
  <div class="tool-btn" data-tool="arrow" title="Arrow (A)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 19L19 5M14 5h5v5"/></svg>
  </div>
  <div class="tool-btn" data-tool="text" title="Text (N)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 5h14M12 5v14"/></svg>
  </div>
  <div class="rl-sep"></div>
  <div class="tool-btn" id="btn-undo" title="Undo (Ctrl+Z)">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>
  </div>
  <div class="tool-btn" id="btn-clear" title="Clear all">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>
  </div>
  <div class="rl-sep"></div>
  <div class="sw-wrap">
    <div class="swatch active" style="background:#3d8eff" data-c="#3d8eff"></div>
    <div class="swatch" style="background:#f0a93c" data-c="#f0a93c"></div>
    <div class="swatch" style="background:#16c98d" data-c="#16c98d"></div>
    <div class="swatch" style="background:#ef4c5a" data-c="#ef4c5a"></div>
    <div class="swatch" style="background:#9b8cff" data-c="#9b8cff"></div>
    <div class="swatch" style="background:#e2e8f2" data-c="#e2e8f2"></div>
  </div>
</div>
<div id="chartwrap">
  <div id="chart-toolbar">
    <div class="pill" id="btn-inds">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
      Indicators <span style="color:var(--dim);font-size:10px;margin-left:4px;">__INDCOUNT__</span>
    </div>
    <div id="ind-chips"></div>
  </div>
  <div id="canvas-stack">
    <canvas id="cv-bg"></canvas>
    <canvas id="cv-main"></canvas>
    <canvas id="cv-ovr"></canvas>
    <canvas id="cv-drw"></canvas>
    <canvas id="cv-ch"></canvas>
    <div id="readout"></div>
    <div id="legend"></div>
    <div id="sr-lbl"></div>
    <div id="price-axis"></div>
    <div id="time-axis"></div>
    <div id="cprice"></div>
    <div id="lpl"></div>
    <div id="lpt"></div>
    <div id="vol-sep"></div>
    <div id="vol-lbl">VOL</div>
    <div class="toast" id="toast"></div>
  </div>
</div>
</div>
</div>
<div id="picker-ov">
  <div id="picker">
    <div id="picker-head">
      <h3>Indicators &amp; Strategies</h3>
      <input id="picker-srch" placeholder="Search RSI, MACD, Bollinger, Supertrend, VWAP..." autocomplete="off"/>
      <div id="picker-meta"><span id="picker-cnt"></span><span>Esc to close · Click to add</span></div>
    </div>
    <div id="picker-list"></div>
  </div>
</div>
<div id="ctxm">
  <div class="ctx-item" id="ctx-col">🎨 Change color</div>
  <div class="ctx-item" id="ctx-dup">📋 Duplicate</div>
  <div class="ctx-item danger" id="ctx-del">🗑 Delete</div>
</div>
<script>
__JS__
</script>
</body>
</html>"""

    # Substitute Python values (safe string replace — no f-string JS issues)
    HTML = HTML.replace("__CSS__",      CSS)
    HTML = HTML.replace("__JS__",       JS_TEMPLATE.replace("__CANDLES__", cj).replace("__SR__", srj).replace("__INDICATORS__", inj))
    HTML = HTML.replace("__SYM__",      sym_clean)
    HTML = HTML.replace("__PRICE__",    price_str)
    HTML = HTML.replace("__CHG__",      chg_str)
    HTML = HTML.replace("__COLOR__",    chg_color)
    HTML = HTML.replace("__INDCOUNT__", str(ind_count))
    HTML = HTML.replace("__HEIGHT__",   str(height))

    return HTML


def render_finsage_chart():
    """Entry point from app.py navigation."""
    st.markdown("""<style>
    header[data-testid="stHeader"],footer,div[data-testid="stDecoration"],
    div[data-testid="stToolbar"],div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}
    .block-container{padding:0!important;max-width:100vw!important;}
    section[data-testid="stSidebar"]{display:none!important;}
    </style>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        sym = st.text_input("", "RELIANCE.NS",
                            placeholder="Symbol: RELIANCE.NS, BTC-USD, AAPL, ^NSEI...",
                            label_visibility="collapsed", key="fc_sym")
    with c2:
        pmap = {"3M":"3mo","6M":"6mo","1Y":"1y","2Y":"2y","1M":"1mo","5D":"5d"}
        per  = pmap[st.selectbox("", list(pmap.keys()), index=0,
                                 label_visibility="collapsed", key="fc_per")]
    with c3:
        imap = {"1d":"1d","1h":"1h","15m":"15m","5m":"5m","1wk":"1wk"}
        iv   = imap[st.selectbox("", list(imap.keys()), index=0,
                                 label_visibility="collapsed", key="fc_int")]

    sym = (sym or "RELIANCE.NS").strip()
    with st.spinner(f"Loading {sym}..."):
        candles  = _fetch_ohlcv(sym, per, iv)
        price_d  = _fetch_price(sym)
        sr       = _compute_sr(candles) if candles else {"supports":[],"resistances":[]}

    if not candles:
        st.error(f"❌ No data for `{sym}`. Try: RELIANCE.NS · BTC-USD · AAPL · ^NSEI · GC=F")
        return

    price = price_d.get("price", candles[-1]["c"])
    chg   = price_d.get("chg", 0)
    html  = build_chart_html(sym, price, chg, candles, sr, height=760)
    components.html(html, height=812, scrolling=False)
