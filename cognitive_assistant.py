"""
FinSage AI — Cognitive Trading Assistant
MODULE 1: Multi-Timeframe Confluence Engine
MODULE 2: Smart Watchlist + AI Filtering
MODULE 3: Sector Heatmap
MODULE 4: Pre-Market Daily Brief
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

def _groq_key():
    try:
        return st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY","")
    except:
        return os.environ.get("GROQ_API_KEY","")

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ════════════════════════════════════════════════════════
# SECTOR MAP
# ════════════════════════════════════════════════════════
SECTOR_STOCKS = {
    "🏦 Banking":     ["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","KOTAKBANK.NS","AXISBANK.NS","BANKBARODA.NS"],
    "💻 IT":          ["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS","LTI.NS"],
    "⛽ Energy":      ["RELIANCE.NS","ONGC.NS","BPCL.NS","IOC.NS","NTPC.NS","POWERGRID.NS"],
    "💊 Pharma":      ["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","BIOCON.NS"],
    "🚗 Auto":        ["TATAMOTORS.NS","MARUTI.NS","BAJAJ-AUTO.NS","EICHERMOT.NS","HEROMOTOCO.NS"],
    "🏗️ Infra":       ["ULTRACEMCO.NS","GRASIM.NS","ADANIPORTS.NS","DLF.NS","LARSEN.NS"],
    "📡 Telecom":     ["BHARTIARTL.NS","VBL.NS","IDEA.NS"],
    "🛒 FMCG":        ["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS","DABUR.NS"],
    "₿ Crypto":      ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","ADA-USD"],
    "📈 US Tech":     ["AAPL","TSLA","NVDA","MSFT","GOOGL","META","AMZN"],
}

WATCHLIST_DEFAULT = [
    ("RELIANCE.NS","NSE:RELIANCE"),("TCS.NS","NSE:TCS"),("INFY.NS","NSE:INFY"),
    ("HDFCBANK.NS","NSE:HDFCBANK"),("ICICIBANK.NS","NSE:ICICIBANK"),
    ("AAPL","NASDAQ:AAPL"),("TSLA","NASDAQ:TSLA"),("NVDA","NASDAQ:NVDA"),
    ("BTC-USD","BINANCE:BTCUSDT"),("ETH-USD","BINANCE:ETHUSDT"),
]

# ════════════════════════════════════════════════════════
# DATA HELPERS
# ════════════════════════════════════════════════════════
@st.cache_data(ttl=120, show_spinner=False)
def _quick_data(sym:str, period:str="5d", interval:str="1d") -> dict:
    try:
        t=yf.Ticker(sym)
        df=t.history(period=period,interval=interval)
        if df.empty: return {}
        c=float(df["Close"].iloc[-1])
        o=float(df["Open"].iloc[-1])
        pc=float(df["Close"].iloc[-2]) if len(df)>1 else o
        v=float(df["Volume"].iloc[-1])
        av=float(df["Volume"].mean()) if len(df)>1 else v
        chg=(c-pc)/pc*100 if pc else 0
        # RSI quick
        closes=df["Close"].values.astype(float)
        d=np.diff(closes,prepend=closes[0])
        up=np.where(d>0,d,0); dn=np.where(d<0,-d,0)
        au=up[-14:].mean() if len(up)>=14 else up.mean()
        ad=dn[-14:].mean() if len(dn)>=14 else dn.mean()
        rsi=float(100-100/(1+(au/ad if ad>0 else 100)))
        # EMA
        ema20=float(pd.Series(closes).ewm(span=20,adjust=False).mean().iloc[-1]) if len(closes)>=20 else c
        # ATR
        h=df["High"].values.astype(float); l=df["Low"].values.astype(float)
        tr=np.maximum(h[1:]-l[1:],np.maximum(abs(h[1:]-closes[:-1]),abs(l[1:]-closes[:-1])))
        atr=float(tr[-14:].mean()) if len(tr)>=14 else float(tr.mean()) if len(tr)>0 else 0
        near_supp=c<ema20*1.02 and c>ema20*0.99
        return {"sym":sym,"price":c,"chg":chg,"rsi":rsi,"ema20":ema20,"atr":atr,
                "vol":v,"avg_vol":av,"vol_ratio":v/av if av>0 else 1.0,
                "near_support":near_supp,"trend":"BULL" if c>ema20 else "BEAR",
                "high":float(df["High"].max()),"low":float(df["Low"].min())}
    except:
        return {}

@st.cache_data(ttl=60, show_spinner=False)
def _multi_tf_data(sym:str) -> dict:
    """Fetch Daily, Hourly, 15-min data for confluence."""
    result={}
    configs=[("daily","6mo","1d"),("hourly","1mo","1h"),("m15","5d","15m")]
    for label,period,interval in configs:
        try:
            df=yf.Ticker(sym).history(period=period,interval=interval)
            if df.empty: continue
            closes=df["Close"].values.astype(float)
            h=df["High"].values.astype(float); l=df["Low"].values.astype(float)
            ema20=float(pd.Series(closes).ewm(span=20,adjust=False).mean().iloc[-1]) if len(closes)>=20 else closes[-1]
            ema50=float(pd.Series(closes).ewm(span=50,adjust=False).mean().iloc[-1]) if len(closes)>=50 else closes[-1]
            # RSI
            d=np.diff(closes,prepend=closes[0]); up=np.where(d>0,d,0); dn=np.where(d<0,-d,0)
            au=up[-14:].mean() if len(up)>=14 else up.mean(); ad=dn[-14:].mean() if len(dn)>=14 else dn.mean()
            rsi=float(100-100/(1+(au/ad if ad>0 else 100)))
            # Support/resistance pivots
            window=5; pivots_s=[]; pivots_r=[]
            for i in range(window,len(l)-window):
                if all(l[i]<=l[i-j] for j in range(1,window+1)) and all(l[i]<=l[i+j] for j in range(1,window+1)):
                    pivots_s.append(float(l[i]))
                if all(h[i]>=h[i-j] for j in range(1,window+1)) and all(h[i]>=h[i+j] for j in range(1,window+1)):
                    pivots_r.append(float(h[i]))
            cur=closes[-1]
            supports=sorted([x for x in pivots_s if x<cur],reverse=True)[:2]
            resistances=sorted([x for x in pivots_r if x>cur])[:2]
            trend="BULL" if cur>ema20>ema50 else "BEAR" if cur<ema20<ema50 else "NEUTRAL"
            result[label]={"price":cur,"rsi":rsi,"ema20":ema20,"ema50":ema50,
                           "supports":supports,"resistances":resistances,"trend":trend}
        except:
            pass
    return result

def _confluence_score(mtf:dict) -> dict:
    """Multi-TF confluence: Daily=50%, Hourly=30%, 15m=20%."""
    weights={"daily":0.5,"hourly":0.3,"m15":0.2}
    bull_score=0.0; bear_score=0.0; details=[]
    for tf,w in weights.items():
        d=mtf.get(tf,{})
        if not d: continue
        trend=d.get("trend","NEUTRAL"); rsi=d.get("rsi",50)
        if trend=="BULL": bull_score+=w; details.append(f"{tf.upper()}: BULL")
        elif trend=="BEAR": bear_score+=w; details.append(f"{tf.upper()}: BEAR")
        else: details.append(f"{tf.upper()}: NEUTRAL")
        if rsi<40: bull_score+=w*0.3
        elif rsi>60: bear_score+=w*0.3
    total=bull_score+bear_score
    if total>0: bias="BULLISH" if bull_score>bear_score else "BEARISH"
    else: bias="NEUTRAL"
    strength=round(max(bull_score,bear_score)*100,0)
    return {"bias":bias,"strength":strength,"bull_score":bull_score,
            "bear_score":bear_score,"details":details}

# ════════════════════════════════════════════════════════
# MODULE 1: MULTI-TIMEFRAME VIEW
# ════════════════════════════════════════════════════════
def render_multi_timeframe(sym:str="RELIANCE.NS"):
    st.markdown("""<style>
    .mtf-card{background:#1e222d;border:1px solid #2a2e39;border-radius:8px;padding:10px 14px;margin:4px 0;}
    .mtf-tf-badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;margin-right:6px;}
    </style>""", unsafe_allow_html=True)

    st.markdown(f"""<div style="background:#131722;border:1px solid #2a2e39;border-radius:8px;
    padding:8px 14px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
      <span style="color:#2962ff;font-size:16px;">⬡</span>
      <span style="color:#d1d4dc;font-weight:700;font-size:14px;">Multi-Timeframe Confluence — {sym}</span>
      <span style="background:#2962ff22;color:#2962ff;font-size:9px;padding:2px 7px;
      border-radius:10px;border:1px solid #2962ff44;font-weight:700;">DAILY 50% · HOURLY 30% · 15M 20%</span>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Loading multi-timeframe data..."):
        mtf=_multi_tf_data(sym)
    if not mtf:
        st.error("Could not load data"); return

    score=_confluence_score(mtf)
    bias=score["bias"]; strength=score["strength"]
    bc={"BULLISH":"#26a69a","BEARISH":"#ef5350","NEUTRAL":"#f59e0b"}.get(bias,"#f59e0b")

    # Confluence score display
    sc1,sc2,sc3=st.columns([2,1,1])
    with sc1:
        st.markdown(f"""<div class="mtf-card">
          <div style="font-size:11px;color:#6a6e7a;margin-bottom:4px;">CONFLUENCE SCORE</div>
          <div style="display:flex;align-items:center;gap:12px;">
            <div style="font-size:28px;font-weight:900;color:{bc};">{bias}</div>
            <div>
              <div style="background:#0e1117;border-radius:4px;height:8px;width:140px;margin-bottom:4px;">
                <div style="background:{bc};height:8px;border-radius:4px;width:{min(strength,100):.0f}%;"></div>
              </div>
              <div style="font-size:11px;color:{bc};">Strength: {strength:.0f}%</div>
            </div>
          </div>
          <div style="font-size:10px;color:#6a6e7a;margin-top:6px;">{' · '.join(score['details'])}</div>
        </div>""", unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""<div class="mtf-card" style="text-align:center;">
          <div style="font-size:10px;color:#6a6e7a;">BULL SCORE</div>
          <div style="font-size:22px;font-weight:900;color:#26a69a;">{score['bull_score']*100:.0f}%</div>
        </div>""", unsafe_allow_html=True)
    with sc3:
        st.markdown(f"""<div class="mtf-card" style="text-align:center;">
          <div style="font-size:10px;color:#6a6e7a;">BEAR SCORE</div>
          <div style="font-size:22px;font-weight:900;color:#ef5350;">{score['bear_score']*100:.0f}%</div>
        </div>""", unsafe_allow_html=True)

    # Per-TF breakdown
    tf_labels={"daily":"📅 Daily (50% weight)","hourly":"⏱️ Hourly (30% weight)","m15":"⚡ 15-Min (20% weight)"}
    tf_cols=st.columns(3)
    for i,(tf_key,tf_label) in enumerate(tf_labels.items()):
        d=mtf.get(tf_key,{})
        with tf_cols[i]:
            if not d:
                st.markdown(f'<div class="mtf-card"><div style="color:#6a6e7a;font-size:11px;">{tf_label}</div><div style="color:#4a5568;margin-top:4px;">No data</div></div>', unsafe_allow_html=True)
                continue
            trend=d.get("trend","NEUTRAL"); rsi=d.get("rsi",50)
            tc={"BULL":"#26a69a","BEAR":"#ef5350","NEUTRAL":"#f59e0b"}.get(trend,"#f59e0b")
            sup_str=" / ".join([f"{x:.2f}" for x in d.get("supports",[])[:2]]) or "—"
            res_str=" / ".join([f"{x:.2f}" for x in d.get("resistances",[])[:2]]) or "—"
            st.markdown(f"""<div class="mtf-card">
              <div style="font-size:10px;color:#6a6e7a;margin-bottom:5px;">{tf_label}</div>
              <div style="font-size:18px;font-weight:900;color:{tc};">{trend}</div>
              <div style="font-size:11px;margin-top:4px;color:#9598a1;">RSI: <b>{rsi:.0f}</b> · EMA20: <b>{d.get('ema20',0):.2f}</b></div>
              <div style="font-size:10px;margin-top:3px;color:#26a69a;">S: {sup_str}</div>
              <div style="font-size:10px;margin-top:1px;color:#ef5350;">R: {res_str}</div>
            </div>""", unsafe_allow_html=True)

    # Aligned S/R zones (appear on 2+ timeframes)
    all_sup=[]; all_res=[]
    for tf_data in mtf.values():
        all_sup.extend(tf_data.get("supports",[])); all_res.extend(tf_data.get("resistances",[]))

    price=mtf.get("daily",{}).get("price",0)
    if price>0:
        tol=price*0.015  # 1.5% tolerance
        def cluster(levels,tol):
            levels=sorted(levels); clusters=[]; used=set()
            for i,l in enumerate(levels):
                if i in used: continue
                grp=[l]; used.add(i)
                for j,l2 in enumerate(levels[i+1:],i+1):
                    if l2-l<=tol: grp.append(l2); used.add(j)
                if len(grp)>=2: clusters.append((round(sum(grp)/len(grp),2),len(grp)))
            return sorted(clusters,key=lambda x:-x[1])
        strong_sup=cluster(all_sup,tol)[:3]; strong_res=cluster(all_res,tol)[:3]
        if strong_sup or strong_res:
            st.markdown("**🎯 Confluence Zones (2+ Timeframes Aligned)**")
            zc1,zc2=st.columns(2)
            with zc1:
                st.markdown('<div style="color:#26a69a;font-size:11px;font-weight:700;margin-bottom:4px;">STRONG SUPPORT ZONES</div>', unsafe_allow_html=True)
                for price_z,count in strong_sup:
                    st.markdown(f"""<div style="background:#26a69a11;border:1px solid #26a69a33;border-radius:6px;
                    padding:6px 10px;margin:3px 0;display:flex;justify-content:space-between;">
                    <span style="color:#26a69a;font-family:monospace;font-weight:700;">{price_z:.2f}</span>
                    <span style="color:#4a9e8a;font-size:10px;">{count} TF aligned 🔥</span></div>""", unsafe_allow_html=True)
            with zc2:
                st.markdown('<div style="color:#ef5350;font-size:11px;font-weight:700;margin-bottom:4px;">STRONG RESISTANCE ZONES</div>', unsafe_allow_html=True)
                for price_z,count in strong_res:
                    st.markdown(f"""<div style="background:#ef535011;border:1px solid #ef535033;border-radius:6px;
                    padding:6px 10px;margin:3px 0;display:flex;justify-content:space-between;">
                    <span style="color:#ef5350;font-family:monospace;font-weight:700;">{price_z:.2f}</span>
                    <span style="color:#c05050;font-size:10px;">{count} TF aligned 🔥</span></div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# MODULE 3: SECTOR HEATMAP
# ════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def _fetch_sector_data() -> dict:
    sector_scores={}
    for sector, stocks in SECTOR_STOCKS.items():
        changes=[]; rsis=[]; vols=[]
        for sym in stocks[:4]:
            d=_quick_data(sym,"5d","1d")
            if d:
                changes.append(d.get("chg",0))
                rsis.append(d.get("rsi",50))
                vols.append(d.get("vol_ratio",1.0))
        if changes:
            avg_chg=float(np.mean(changes))
            avg_rsi=float(np.mean(rsis))
            avg_vol=float(np.mean(vols))
            adv=sum(1 for c in changes if c>0); dec=len(changes)-adv
            momentum=avg_chg*0.5+(avg_rsi-50)*0.02+(avg_vol-1)*0.1
            sector_scores[sector]={"avg_chg":round(avg_chg,2),"avg_rsi":round(avg_rsi,1),
                "avg_vol":round(avg_vol,2),"advance":adv,"decline":dec,"momentum":round(momentum,2)}
    return sector_scores

def render_sector_heatmap():
    st.markdown("""<style>
    .heat-cell{border-radius:8px;padding:12px 10px;text-align:center;cursor:pointer;
      transition:transform 0.1s;min-height:85px;display:flex;flex-direction:column;
      justify-content:center;align-items:center;}
    .heat-cell:hover{transform:scale(1.02);}
    </style>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#131722;border:1px solid #2a2e39;border-radius:8px;
    padding:8px 14px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
      <span style="color:#fbbf24;font-size:16px;">🌡️</span>
      <span style="color:#d1d4dc;font-weight:700;font-size:14px;">Sector Heatmap</span>
      <span style="color:#6a6e7a;font-size:11px;margin-left:6px;">Real-time sector momentum · NSE + Crypto + US</span>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Scanning sectors..."):
        data=_fetch_sector_data()

    if not data:
        st.warning("Sector data loading..."); return

    sorted_sectors=sorted(data.items(),key=lambda x:-x[1]["momentum"])

    # Top / Bottom performers
    tc1,tc2=st.columns(2)
    with tc1:
        st.markdown("""<div style="background:#26a69a11;border:1px solid #26a69a33;border-radius:8px;
        padding:8px 12px;margin-bottom:8px;">
          <div style="color:#26a69a;font-size:11px;font-weight:700;margin-bottom:4px;">🚀 STRONGEST SECTORS TODAY</div>""", unsafe_allow_html=True)
        for sec,d in sorted_sectors[:3]:
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:12px;"><span>{sec}</span><span style="color:#26a69a;font-weight:700;">{d["avg_chg"]:+.2f}%</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with tc2:
        st.markdown("""<div style="background:#ef535011;border:1px solid #ef535033;border-radius:8px;
        padding:8px 12px;margin-bottom:8px;">
          <div style="color:#ef5350;font-size:11px;font-weight:700;margin-bottom:4px;">📉 WEAKEST SECTORS TODAY</div>""", unsafe_allow_html=True)
        for sec,d in sorted_sectors[-3:]:
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:12px;"><span>{sec}</span><span style="color:#ef5350;font-weight:700;">{d["avg_chg"]:+.2f}%</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Heatmap grid
    cols_per_row=4
    row_items=[sorted_sectors[i:i+cols_per_row] for i in range(0,len(sorted_sectors),cols_per_row)]
    for row in row_items:
        cols=st.columns(cols_per_row)
        for i,(sec,d) in enumerate(row):
            with cols[i]:
                chg=d["avg_chg"]; rsi=d["avg_rsi"]; vol=d["avg_vol"]
                adv=d["advance"]; dec=d["decline"]
                intensity=min(abs(chg)/3.0,1.0)
                if chg>0:
                    r=int(26+intensity*80); g=int(166-intensity*30); b=int(154-intensity*50)
                    bg=f"rgba({r},{g},{b},{0.15+intensity*0.35})"
                    border=f"rgba({r},{g},{b},0.5)"
                    color=f"rgb({r},{g},{b})"
                    arrow="▲"
                else:
                    r=int(239-intensity*30); g=int(83+intensity*30); b=int(80+intensity*20)
                    bg=f"rgba({r},{g},{b},{0.15+intensity*0.35})"
                    border=f"rgba({r},{g},{b},0.5)"
                    color=f"rgb({r},{g},{b})"
                    arrow="▼"
                st.markdown(f"""<div class="heat-cell"
                style="background:{bg};border:1px solid {border};">
                  <div style="font-size:13px;font-weight:700;color:#d1d4dc;margin-bottom:3px;">{sec}</div>
                  <div style="font-size:20px;font-weight:900;color:{color};">{arrow} {abs(chg):.2f}%</div>
                  <div style="font-size:10px;color:#9598a1;margin-top:3px;">
                    RSI {rsi:.0f} · Vol {vol:.1f}x<br>
                    <span style="color:#26a69a;">▲{adv}</span>/<span style="color:#ef5350;">▼{dec}</span>
                  </div>
                </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# MODULE 2: SMART WATCHLIST
# ════════════════════════════════════════════════════════
def render_smart_watchlist():
    st.markdown("""<style>
    .wl-row{background:#1e222d;border:1px solid #2a2e39;border-radius:8px;padding:10px 14px;
      margin:4px 0;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
    .wl-sym{font-size:13px;font-weight:700;color:#d1d4dc;min-width:100px;}
    .wl-price{font-size:15px;font-weight:700;font-family:monospace;min-width:90px;}
    .wl-badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;margin-left:auto;}
    .wl-setup{display:inline-block;background:#26a69a22;color:#26a69a;border:1px solid #26a69a44;
      padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;}
    </style>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#131722;border:1px solid #2a2e39;border-radius:8px;
    padding:8px 14px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
      <span style="color:#2962ff;font-size:16px;">⬡</span>
      <span style="color:#d1d4dc;font-weight:700;font-size:14px;">Smart Watchlist</span>
      <span style="color:#6a6e7a;font-size:11px;">AI-filtered setups · Real-time prices</span>
    </div>""", unsafe_allow_html=True)

    # Filter builder
    with st.expander("⚙️ AI Filter Builder", expanded=False):
        fc1,fc2,fc3=st.columns(3)
        with fc1:
            rsi_min=st.slider("RSI Min",10,90,30,key="wl_rsi_min")
            rsi_max=st.slider("RSI Max",10,90,70,key="wl_rsi_max")
        with fc2:
            min_vol=st.slider("Min Volume Ratio",0.5,5.0,1.0,0.1,key="wl_vol")
            near_supp=st.checkbox("Near Support",value=True,key="wl_supp")
        with fc3:
            trend_filter=st.selectbox("Trend",["Any","BULL","BEAR"],key="wl_trend")
            min_rr=st.slider("Min R:R",0.5,5.0,1.5,0.1,key="wl_rr")

    # Custom symbol input
    custom=st.text_input("Add symbols (comma-separated)","",placeholder="WIPRO.NS, ADANIENT.NS, AMZN",key="wl_custom")
    symbols=list(WATCHLIST_DEFAULT)
    if custom:
        for s in custom.split(","):
            s=s.strip().upper()
            if s: symbols.append((resolve_ticker(s),""))

    # Fetch and filter
    if st.button("🔍 Scan & Filter",key="wl_scan",type="primary"):
        st.session_state.wl_data=None

    if st.session_state.get("wl_data") is None:
        with st.spinner(f"Scanning {len(symbols)} symbols..."):
            results=[]
            for sym,_ in symbols[:15]:
                d=_quick_data(sym,"10d","1d")
                if not d: continue
                d["sym"]=sym
                results.append(d)
            st.session_state.wl_data=results

    results=st.session_state.get("wl_data",[])
    rsi_min_v=st.session_state.get("wl_rsi_min",30)
    rsi_max_v=st.session_state.get("wl_rsi_max",70)
    vol_v=st.session_state.get("wl_vol",1.0)
    supp_v=st.session_state.get("wl_supp",True)
    trend_v=st.session_state.get("wl_trend","Any")

    filtered=[d for d in results if
        rsi_min_v<=d.get("rsi",50)<=rsi_max_v and
        d.get("vol_ratio",0)>=vol_v and
        (not supp_v or d.get("near_support",False)) and
        (trend_v=="Any" or d.get("trend","")==trend_v)]

    # Sort by volume ratio desc
    filtered=sorted(filtered,key=lambda x:-x.get("vol_ratio",0))

    st.markdown(f"**{len(filtered)} setups match your filter** (out of {len(results)} scanned)")

    if not filtered:
        st.info("No matches. Try relaxing filters.")

    # Top 5 Setup Alerts
    top5=filtered[:5]
    if top5:
        st.markdown("### 🎯 Top Setup Alerts")
        for d in top5:
            sym=d["sym"]; price=d["price"]; chg=d["chg"]
            rsi=d["rsi"]; vr=d["vol_ratio"]; trend=d.get("trend","?")
            chg_color="#26a69a" if chg>=0 else "#ef5350"
            trend_color="#26a69a" if trend=="BULL" else "#ef5350"
            setup_tags=[]
            if rsi<35: setup_tags.append("Oversold RSI")
            if rsi>65: setup_tags.append("Overbought RSI")
            if vr>1.5: setup_tags.append(f"High Vol {vr:.1f}x")
            if d.get("near_support"): setup_tags.append("Near Support")
            tags_html=" ".join([f'<span class="wl-setup">{t}</span>' for t in setup_tags[:3]])
            st.markdown(f"""<div class="wl-row">
              <div class="wl-sym">{sym}</div>
              <div class="wl-price" style="color:{chg_color};">{price:.2f}</div>
              <div style="color:{chg_color};font-weight:700;min-width:60px;">{chg:+.2f}%</div>
              <div style="color:#9598a1;font-size:11px;">RSI <b>{rsi:.0f}</b></div>
              <div style="color:#9598a1;font-size:11px;">Vol <b>{vr:.1f}x</b></div>
              <div style="color:{trend_color};font-size:11px;font-weight:700;">{trend}</div>
              <div style="margin-left:auto;">{tags_html}</div>
            </div>""", unsafe_allow_html=True)

    # Full watchlist table
    st.markdown("### 📋 Full Watchlist")
    cols_h=st.columns([3,2,2,1,1,1])
    for label in ["Symbol","Price","Chg%","RSI","Vol","Trend"]:
        cols_h[["Symbol","Price","Chg%","RSI","Vol","Trend"].index(label)].markdown(f"**{label}**")

    for d in results[:20]:
        sym=d["sym"]; price=d["price"]; chg=d["chg"]
        rsi=d["rsi"]; vr=d["vol_ratio"]; trend=d.get("trend","?")
        cc="#26a69a" if chg>=0 else "#ef5350"
        tc="#26a69a" if trend=="BULL" else "#ef5350"
        rc="#26a69a" if rsi<40 else "#ef5350" if rsi>60 else "#f59e0b"
        vc="#26a69a" if vr>1.5 else "#6a6e7a"
        is_top="⭐ " if d in top5 else ""
        row_cols=st.columns([3,2,2,1,1,1])
        row_cols[0].markdown(f"**{is_top}{sym}**")
        row_cols[1].markdown(f'<span style="color:{cc};font-family:monospace;font-weight:700;">{price:.2f}</span>', unsafe_allow_html=True)
        row_cols[2].markdown(f'<span style="color:{cc};font-weight:700;">{chg:+.2f}%</span>', unsafe_allow_html=True)
        row_cols[3].markdown(f'<span style="color:{rc};">{rsi:.0f}</span>', unsafe_allow_html=True)
        row_cols[4].markdown(f'<span style="color:{vc};">{vr:.1f}x</span>', unsafe_allow_html=True)
        row_cols[5].markdown(f'<span style="color:{tc};font-weight:700;">{trend}</span>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# MODULE 4: PRE-MARKET DAILY BRIEF
# ════════════════════════════════════════════════════════
def _generate_brief(watchlist_data:list, sector_data:dict) -> str:
    key=_groq_key()
    if not key:
        return _rule_based_brief(watchlist_data, sector_data)

    top5=sorted(watchlist_data,key=lambda x:-abs(x.get("chg",0)))[:5]
    near_supp=[d["sym"] for d in watchlist_data if d.get("near_support") and d.get("chg",0)>-2][:3]
    high_vol=[d["sym"] for d in watchlist_data if d.get("vol_ratio",0)>1.5][:3]
    top_sector=max(sector_data.items(),key=lambda x:x[1]["momentum"],default=(None,{}))[0] if sector_data else "N/A"
    bot_sector=min(sector_data.items(),key=lambda x:x[1]["momentum"],default=(None,{}))[0] if sector_data else "N/A"
    today=datetime.now().strftime("%B %d, %Y")
    prompt=f"""You are SAGE AI, generating a pre-market trading brief for {today}.

Data:
- Top movers: {[(d['sym'],f"{d['chg']:+.2f}%") for d in top5]}
- Near support: {near_supp}
- High volume: {high_vol}
- Strongest sector: {top_sector}
- Weakest sector: {bot_sector}
- Market data: {[(d['sym'],f"RSI:{d.get('rsi',50):.0f}",f"Vol:{d.get('vol_ratio',1):.1f}x") for d in top5]}

Write a professional pre-market brief with these exact sections:
1. Market Overview (2 lines)
2. Stocks at Critical S/R (mention actual prices)
3. Breakout Candidates (with reason)
4. Sector Momentum
5. Risk Watch
6. Today's Action Plan (3 bullet points)

Keep it concise, data-backed, no generic statements. Use actual numbers from the data.
Format as clean text with section headers."""

    try:
        r=requests.post(GROQ_URL,
            headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
            json={"model":GROQ_MODEL,"messages":[{"role":"user","content":prompt}],
                  "temperature":0.3,"max_tokens":900},timeout=25)
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return _rule_based_brief(watchlist_data,sector_data)

def _rule_based_brief(watchlist_data:list, sector_data:dict) -> str:
    top5=sorted(watchlist_data,key=lambda x:-abs(x.get("chg",0)))[:5]
    near=", ".join([d["sym"] for d in watchlist_data if d.get("near_support")][:3]) or "None"
    hvol=", ".join([d["sym"] for d in watchlist_data if d.get("vol_ratio",0)>1.5][:3]) or "None"
    top_sec=max(sector_data.items(),key=lambda x:x[1]["momentum"],default=("N/A",{}))[0] if sector_data else "N/A"
    today=datetime.now().strftime("%B %d, %Y")
    lines=["="*50, f"SAGE AI PRE-MARKET BRIEF — {today}", "="*50,"",
           "📊 MARKET OVERVIEW",""]
    for d in top5:
        arrow="▲" if d["chg"]>=0 else "▼"
        lines.append(f"  {arrow} {d['sym']}: {d['price']:.2f} ({d['chg']:+.2f}%) | RSI {d.get('rsi',50):.0f}")
    lines.extend(["","📐 NEAR SUPPORT","",f"  {near} — potential bounce setups","",
                  "🚀 HIGH VOLUME MOVERS","",f"  {hvol} — conviction confirmed by volume","",
                  "🌡️ SECTOR MOMENTUM","",f"  Strongest: {top_sec}","",
                  "📋 ACTION PLAN","",
                  "  • Review near-support stocks for entry with tight stop-loss",
                  "  • High-volume movers — check for breakout confirmation",
                  "  • Avoid trades against strong sector trends","",
                  "⚠️ DISCLAIMER: Educational only. Not financial advice. Always use stop-loss."])
    return "\n".join(lines)

def render_daily_brief():
    st.markdown("""<div style="background:#131722;border:1px solid #2a2e39;border-radius:8px;
    padding:8px 14px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
      <span style="color:#fbbf24;font-size:16px;">📋</span>
      <span style="color:#d1d4dc;font-weight:700;font-size:14px;">AI Pre-Market Daily Brief</span>
      <span style="background:#fbbf2422;color:#fbbf24;font-size:9px;padding:2px 7px;
      border-radius:10px;border:1px solid #fbbf2444;font-weight:700;">AUTO GENERATED</span>
    </div>""", unsafe_allow_html=True)

    now=datetime.now()
    st.markdown(f"""<div style="background:#1a1e2d;border:1px solid #2a2e39;border-radius:8px;
    padding:8px 14px;margin-bottom:8px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      <span style="color:#6a6e7a;font-size:11px;">🕐 Generated at {now.strftime('%H:%M IST')} · {now.strftime('%B %d, %Y')}</span>
      <span style="background:#26a69a22;color:#26a69a;font-size:10px;padding:2px 8px;border-radius:10px;">GROQ LLAMA AI</span>
    </div>""", unsafe_allow_html=True)

    col1,col2=st.columns([2,1])
    with col1:
        if st.button("🔄 Generate Fresh Brief",key="brief_gen",type="primary",use_container_width=True):
            st.session_state.daily_brief=None
            st.session_state.wl_data=None
    with col2:
        if st.button("📥 Download Brief",key="brief_dl",use_container_width=True):
            brief_text=st.session_state.get("daily_brief","")
            if brief_text:
                st.download_button("Save as TXT",brief_text,"finsage_brief.txt","text/plain",key="brief_dl2")

    with st.spinner("SAGE AI generating market brief..."):
        if st.session_state.get("daily_brief") is None:
            wl=[]; sdata={}
            for sym,_ in WATCHLIST_DEFAULT[:10]:
                d=_quick_data(sym,"5d","1d")
                if d: d["sym"]=sym; wl.append(d)
            sdata=_fetch_sector_data()
            brief=_generate_brief(wl,sdata)
            st.session_state.daily_brief=brief
            st.session_state.brief_wl=wl
            st.session_state.brief_sdata=sdata

    brief=st.session_state.get("daily_brief","")
    wl=st.session_state.get("brief_wl",[])
    sdata=st.session_state.get("brief_sdata",{})

    # Metric cards
    if wl:
        bulls=sum(1 for d in wl if d.get("chg",0)>0)
        bears=len(wl)-bulls
        avg_chg=np.mean([d.get("chg",0) for d in wl])
        near_sup_count=sum(1 for d in wl if d.get("near_support"))
        m1,m2,m3,m4=st.columns(4)
        mc="#26a69a" if avg_chg>=0 else "#ef5350"
        m1.metric("Market Breadth",f"▲{bulls}/▼{bears}")
        m2.metric("Avg Change",f"{avg_chg:+.2f}%")
        m3.metric("Near Support",f"{near_sup_count} stocks")
        if sdata:
            top_s=max(sdata.items(),key=lambda x:x[1]["momentum"],default=("—",{}))[0]
            m4.metric("Top Sector",top_s.split()[-1] if top_s!="—" else "—")

    # Brief text
    if brief:
        st.markdown(f"""<div style="background:#131722;border:1px solid #2a2e39;border-radius:10px;
        padding:16px 20px;font-family:'Courier New',monospace;font-size:12.5px;
        color:#d1d4dc;line-height:1.8;white-space:pre-wrap;">{brief}</div>""", unsafe_allow_html=True)

    # Disclaimer
    st.markdown("""<div style="background:#1a1500;border:1px solid #3d2e00;border-radius:8px;
    padding:8px 14px;margin-top:12px;font-size:11px;color:#8b8070;">
    ⚠️ <b>Disclaimer:</b> This AI-generated brief is for educational and informational purposes only.
    It does NOT constitute financial advice, investment recommendations, or guaranteed predictions.
    Backtested results do not guarantee future performance. All trade decisions and their consequences
    are solely the responsibility of the user. Always consult a SEBI-registered advisor before trading.
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# MAIN COGNITIVE ASSISTANT PAGE
# ════════════════════════════════════════════════════════
def render_cognitive_assistant():
    st.markdown("""<style>
    .block-container{padding-top:0.4rem!important;}
    header[data-testid="stHeader"],footer,
    div[data-testid="stDecoration"],div[data-testid="stToolbar"],
    div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}
    </style>""", unsafe_allow_html=True)

    # Header
    _now_str = datetime.now().strftime("%H:%M")
    st.markdown(f"""<div style="background:linear-gradient(135deg,#131722,#1a1f2e);
    border:1px solid #2a2e39;border-radius:12px;padding:12px 18px;margin-bottom:10px;">
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
        <div>
          <span style="font-size:15px;font-weight:800;color:#d1d4dc;">
            ⬡ SAGE Cognitive Assistant
          </span>
          <span style="background:#2962ff22;color:#2962ff;font-size:9px;padding:2px 7px;
          border-radius:10px;border:1px solid #2962ff44;font-weight:700;margin-left:8px;">AI POWERED</span>
          <div style="color:#6a6e7a;font-size:11px;margin-top:2px;">
          Multi-Timeframe · Sector Heatmap · Smart Watchlist · Pre-Market Brief
          </div>
        </div>
        <div style="margin-left:auto;color:#6a6e7a;font-size:11px;">
          🕐 {_now_str} IST · Reduce 50 charts → 5 actionable setups
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Navigation tabs
    tab1,tab2,tab3,tab4 = st.tabs([
        "📊 Multi-Timeframe",
        "🌡️ Sector Heatmap",
        "⭐ Smart Watchlist",
        "📋 Pre-Market Brief"
    ])

    with tab1:
        sym_input=st.text_input("Symbol for MTF Analysis","RELIANCE.NS",
            placeholder="RELIANCE.NS, AAPL, BTC-USD",key="ca_mtf_sym")
        sym=resolve_ticker(sym_input.strip() or "RELIANCE.NS")
        render_multi_timeframe(sym)

    with tab2:
        render_sector_heatmap()

    with tab3:
        render_smart_watchlist()

    with tab4:
        render_daily_brief()
