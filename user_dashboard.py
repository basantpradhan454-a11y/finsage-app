"""
FinSage AI — User Dashboard
Favourite stocks · Inbuilt FinSage Pro Chart · Full AI auto-analysis
"""
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import json, os, requests
from datetime import datetime

# ── shared imports ──────────────────────────────────────────────────
try:
    from pro_chart import (
        _price_fast, _ohlcv, _compute_tech, _ai_full,
        _pro_chart_html, _to_tv, _global_search as _srch
    )
except Exception as e:
    st.error(f"pro_chart import error: {e}"); st.stop()

try:
    from market_dashboard import _fundamental, _white_paper_html
except Exception as e:
    _fundamental = lambda s: {}
    _white_paper_html = lambda *a, **kw: ""

def _key(n):
    try: return st.secrets.get(n) or os.environ.get(n,"")
    except: return os.environ.get(n,"")

# ── default favourites ───────────────────────────────────────────────
DEFAULT_FAVS = [
    {"sym":"^NSEI",        "name":"NIFTY 50",   "type":"index"},
    {"sym":"RELIANCE.NS",  "name":"Reliance",   "type":"stock"},
    {"sym":"TCS.NS",       "name":"TCS",        "type":"stock"},
    {"sym":"HDFCBANK.NS",  "name":"HDFC Bank",  "type":"stock"},
    {"sym":"AAPL",         "name":"Apple",      "type":"stock"},
    {"sym":"BTC-USD",      "name":"Bitcoin",    "type":"crypto"},
]

SECTOR_STOCKS = {
    "🏦 Banking": ["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS"],
    "💻 IT":      ["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS"],
    "⚡ Energy":  ["RELIANCE.NS","NTPC.NS","POWERGRID.NS","ADANIGREEN.NS","ONGC.NS"],
    "🏗️ Infra":   ["ADANIENT.NS","LTIM.NS","BAJAJFINSV.NS","MARUTI.NS","TATAMOTORS.NS"],
    "🌐 US Tech": ["AAPL","TSLA","NVDA","MSFT","GOOGL","META","AMZN"],
    "🪙 Crypto":  ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD"],
}

# ════════════════════════════════════════════════════════════════════
def render_user_dashboard():
    # ── page CSS ──────────────────────────────────────────────────────
    st.markdown("""<style>
    header[data-testid="stHeader"],footer,div[data-testid="stDecoration"],
    div[data-testid="stToolbar"],div[data-testid="stStatusWidget"],.stDeployButton{display:none!important;}
    .block-container{padding:0 0 20px 0!important;max-width:100vw!important;}
    .stTabs [data-baseweb="tab-list"]{gap:4px;background:rgba(13,17,28,0.8);padding:4px;border-radius:10px;}
    .stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px;color:#6a6e7a;font-size:12px;padding:5px 12px;}
    .stTabs [aria-selected="true"]{background:rgba(41,98,255,0.2)!important;color:#4a9eff!important;}
    div[data-testid="stVerticalBlock"]{gap:4px;}
    </style>""", unsafe_allow_html=True)

    # ── init state ───────────────────────────────────────────────────
    if "ud_favs" not in st.session_state:
        st.session_state.ud_favs = list(DEFAULT_FAVS)
    if "ud_sel"  not in st.session_state:
        st.session_state.ud_sel  = st.session_state.ud_favs[0]
    if "ud_ai"   not in st.session_state:
        st.session_state.ud_ai   = None
    if "ud_fund" not in st.session_state:
        st.session_state.ud_fund = {}
    if "ud_srch"     not in st.session_state: st.session_state.ud_srch=""
    if "ud_srch_res" not in st.session_state: st.session_state.ud_srch_res=[]
    if "ud_tf"       not in st.session_state: st.session_state.ud_tf="1D"
    if "ud_trader"   not in st.session_state: st.session_state.ud_trader="all"
    if "ud_mode"     not in st.session_state: st.session_state.ud_mode="chart"
    if "ud_notifs"   not in st.session_state:
        st.session_state.ud_notifs=[
            {"msg":"RELIANCE.NS hit key resistance 1350 — watch for breakout","time":"09:18","type":"warn"},
            {"msg":"NIFTY50 bullish engulfing on daily — momentum confirmed","time":"08:45","type":"bull"},
            {"msg":"BTC-USD near 61,800 FVG zone — high probability bounce","time":"07:30","type":"bull"},
        ]

    favs   = st.session_state.ud_favs
    sel    = st.session_state.ud_sel
    sym    = sel["sym"]; name = sel["name"]

    # ════ TOP BAR ═════════════════════════════════════════════════════
    d    = _price_fast(sym)
    pr   = d.get("price",0); chg = d.get("chg",0)
    cc   = "#26a69a" if chg>=0 else "#ef5350"
    pr_s = f"{pr:,.4f}" if pr<10 else f"{pr:,.2f}" if pr>0 else "—"

    st.markdown(f"""
    <div style="background:rgba(10,13,20,0.98);backdrop-filter:blur(20px);
    border-bottom:1px solid rgba(255,255,255,0.06);padding:8px 18px;
    display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      <div style="display:flex;align-items:center;gap:8px;">
        <div style="width:36px;height:36px;background:linear-gradient(135deg,#2962ff,#a855f7);
          border-radius:10px;display:flex;align-items:center;justify-content:center;
          font-size:18px;">👤</div>
        <div>
          <div style="color:#fff;font-weight:900;font-size:15px;">FinSage <span style="color:#2962ff;">Dashboard</span></div>
          <div style="color:#4a5568;font-size:10px;">Your personal trading command center</div>
        </div>
      </div>
      <div style="flex:1;"></div>
      <div style="text-align:right;">
        <div style="color:#9598a1;font-size:12px;font-weight:600;">{name} &nbsp;
          <span style="color:{cc};font-family:monospace;font-size:16px;font-weight:900;">{pr_s}</span>
          &nbsp;<span style="color:{cc};">{chg:+.2f}%</span>
        </div>
        <div style="color:#374151;font-size:10px;">🕐 {datetime.now().strftime('%a, %d %b %Y · %H:%M IST')}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ════ MAIN LAYOUT ═════════════════════════════════════════════════
    left_col, chart_col = st.columns([1, 4], gap="small")

    # ════ LEFT PANEL ══════════════════════════════════════════════════
    with left_col:

        # ── Notification strip ─────────────────────────────────────────
        notif_colors={"bull":"#26a69a","bear":"#ef5350","warn":"#f59e0b","info":"#2962ff"}
        for n in st.session_state.ud_notifs[:2]:
            nc=notif_colors.get(n["type"],"#6a6e7a")
            st.markdown(f"""<div style="background:{nc}0d;border-left:3px solid {nc};
            border-radius:0 6px 6px 0;padding:5px 8px;margin-bottom:3px;font-size:10px;color:#c8cad0;">
            <span style="color:{nc};font-size:9px;font-weight:700;">● {n['time']}</span><br>{n['msg'][:55]}...</div>""",
            unsafe_allow_html=True)

        st.markdown("<div style='height:4px;'></div>",unsafe_allow_html=True)

        # ── Search ─────────────────────────────────────────────────────
        srch=st.text_input("","",placeholder="🔍 Add stock / crypto...",
                           key="ud_srch_inp",label_visibility="collapsed")
        if srch!=st.session_state.ud_srch:
            st.session_state.ud_srch=srch
            if srch.strip():
                with st.spinner("..."): st.session_state.ud_srch_res=_srch(srch)
            else: st.session_state.ud_srch_res=[]

        for item in st.session_state.ud_srch_res:
            d2=_price_fast(item["sym"]); pr2=d2.get("price",0); chg2=d2.get("chg",0)
            cc2="#26a69a" if chg2>=0 else "#ef5350"
            col1a,col1b=st.columns([3,1])
            with col1a:
                if st.button(f"+ {item['name'][:14]}",key=f"uadd_{item['sym']}",use_container_width=True):
                    if not any(f["sym"]==item["sym"] for f in st.session_state.ud_favs):
                        st.session_state.ud_favs.append({"sym":item["sym"],"name":item["name"],"type":item["type"]})
                        st.toast(f"⭐ {item['name']} added!")
                    st.session_state.ud_sel={"sym":item["sym"],"name":item["name"],"type":item["type"]}
                    st.session_state.ud_ai=None; st.session_state.ud_srch=""
                    st.session_state.ud_srch_res=[]; st.rerun()
            with col1b:
                pr2s=f"{pr2:.2f}" if pr2>0 else "—"
                st.markdown(f'<div style="font-size:10px;color:{cc2};text-align:right;padding-top:4px;">{pr2s}</div>',unsafe_allow_html=True)

        # ── Watchlist header ───────────────────────────────────────────
        st.markdown("""<div style="display:flex;padding:4px 6px;font-size:8.5px;color:#374151;
        font-weight:700;background:rgba(255,255,255,0.02);border-radius:6px 6px 0 0;
        text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid rgba(255,255,255,0.04);">
          <span style="flex:1;">Stock</span>
          <span style="width:68px;text-align:right;">Price</span>
          <span style="width:42px;text-align:right;">Chg%</span>
          <span style="width:16px;"></span>
        </div>""",unsafe_allow_html=True)

        # ── Watchlist items ────────────────────────────────────────────
        to_remove=None
        for item in list(favs):
            d3=_price_fast(item["sym"]); pr3=d3.get("price",0); chg3=d3.get("chg",0)
            cc3="#26a69a" if chg3>=0 else "#ef5350"
            is_sel=st.session_state.ud_sel["sym"]==item["sym"]
            pr3s=f"{pr3:,.4f}" if pr3>0 and pr3<10 else f"{pr3:,.2f}" if pr3>0 else "—"
            chg3s=f"{chg3:+.1f}%" if pr3>0 else "—"

            btn_col,del_col=st.columns([5,1])
            with btn_col:
                lbl_icon={"stock":"📈","crypto":"🪙","index":"📊","commodity":"🥇"}.get(item["type"],"📈")
                if st.button(f"{lbl_icon} {item['name'][:13]}",
                             key=f"udwl_{item['sym']}",use_container_width=True,
                             type="primary" if is_sel else "secondary"):
                    st.session_state.ud_sel=item
                    st.session_state.ud_ai=None; st.rerun()
            with del_col:
                if st.button("✕",key=f"uddel_{item['sym']}",use_container_width=True):
                    to_remove=item["sym"]

            # Price row
            st.markdown(
                f'<div style="display:flex;padding:0 6px 3px 6px;font-size:10.5px;'
                f'border-bottom:1px solid rgba(255,255,255,0.03);margin-top:-8px;">'
                f'<span style="flex:1;color:#374151;font-size:9px;">{item["sym"].replace(".NS","").replace("-USD","").replace("^","")}</span>'
                f'<span style="color:{cc3};font-family:monospace;font-weight:700;min-width:68px;text-align:right;">{pr3s}</span>'
                f'<span style="color:{cc3};min-width:42px;text-align:right;font-size:10px;">{chg3s}</span>'
                f'<span style="width:16px;"></span></div>',
                unsafe_allow_html=True)

        if to_remove:
            st.session_state.ud_favs=[f for f in st.session_state.ud_favs if f["sym"]!=to_remove]
            if st.session_state.ud_sel["sym"]==to_remove and st.session_state.ud_favs:
                st.session_state.ud_sel=st.session_state.ud_favs[0]; st.session_state.ud_ai=None
            st.rerun()

        st.markdown("<div style='height:6px'></div>",unsafe_allow_html=True)

        # ── Quick add sector ───────────────────────────────────────────
        st.markdown('<div style="font-size:10px;color:#374151;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px;">Quick Add by Sector</div>',unsafe_allow_html=True)
        sec=st.selectbox("",list(SECTOR_STOCKS.keys()),key="ud_sec",label_visibility="collapsed")
        for s in SECTOR_STOCKS[sec][:5]:
            d4=_price_fast(s); pr4=d4.get("price",0); chg4=d4.get("chg",0)
            cc4="#26a69a" if chg4>=0 else "#ef5350"
            already=any(f["sym"]==s for f in st.session_state.ud_favs)
            lbl=("✓ " if already else "+ ")+s.replace(".NS","").replace("-USD","")
            if st.button(lbl,key=f"uqadd_{s}",use_container_width=True):
                if not already:
                    nm=s.replace(".NS","").replace("-USD","").replace("^","")
                    st.session_state.ud_favs.append({"sym":s,"name":nm,"type":"stock"})
                    st.toast(f"⭐ {nm} added!")
                st.session_state.ud_sel={"sym":s,"name":s.replace(".NS","").replace("-USD","").replace("^",""),"type":"stock"}
                st.session_state.ud_ai=None; st.rerun()
            if pr4>0:
                st.markdown(f'<div style="display:flex;font-size:10px;padding:0 3px 2px 3px;margin-top:-8px;border-bottom:1px solid rgba(255,255,255,0.03);"><span style="flex:1;color:#374151;font-size:9px;">{s}</span><span style="color:{cc4};font-family:monospace;">{pr4:.2f}</span><span style="color:{cc4};margin-left:5px;">{chg4:+.1f}%</span></div>',unsafe_allow_html=True)

    # ════ CHART PANEL ═════════════════════════════════════════════════
    with chart_col:

        # ── Chart toolbar ─────────────────────────────────────────────
        t1,t2,t3,t4,t5,t6=st.columns([3,2,2,1,1,1])
        with t1:
            tf=st.radio("",["1D","1H","15m","4H","1W","1M"],
                        horizontal=True,key="ud_tf_r",index=0,label_visibility="collapsed")
        with t2:
            trader=st.selectbox("",["all","price_action","smc","indicator","volume","wave","quant"],
                format_func=lambda x:{"all":"🎯 All Styles","price_action":"📊 Price Action",
                    "smc":"🏦 SMC/ICT","indicator":"📈 Indicators",
                    "volume":"📦 Volume Flow","wave":"🌊 Elliott Wave","quant":"🤖 Quant"}[x],
                key="ud_trader_sel",label_visibility="collapsed")
        with t3:
            mode_sel=st.radio("",["📺 TradingView","🤖 AI Chart"],
                              horizontal=True,key="ud_mode_r",label_visibility="collapsed")
        with t4:
            run_ai=st.button("🤖 Analyse",key="ud_run",type="primary",use_container_width=True)
        with t5:
            if st.button("🔄",key="ud_ref",use_container_width=True):
                st.session_state.ud_ai=None; st.rerun()
        with t6:
            refresh_all=st.button("📊",key="ud_dash",use_container_width=True,help="Full dashboard view")

        if run_ai:
            st.session_state.ud_ai=None
            st.session_state.ud_trader=trader
            st.session_state.ud_mode="ai"
            st.rerun()

        # ── Load data ──────────────────────────────────────────────────
        tf_map={"1D":("3mo","1d"),"1H":("1mo","1h"),"15m":("5d","15m"),
                "4H":("6mo","1d"),"1W":("2y","1wk"),"1M":("5y","1mo")}
        period,interval=tf_map.get(tf,("3mo","1d"))
        with st.spinner(f"Loading {name}..."):
            df=_ohlcv(sym,period,interval)
            tech=_compute_tech(df) if not df.empty else {}

        if df.empty:
            st.error(f"❌ No data for `{sym}`"); return

        use_ai_chart="🤖 AI Chart" in mode_sel or st.session_state.ud_mode=="ai"

        # ══════════════════════════════════════════════════════════════
        # TradingView MODE
        # ══════════════════════════════════════════════════════════════
        if not use_ai_chart:
            tv_s=_to_tv(sym)
            tv_tf={"1D":"D","1H":"60","15m":"15","4H":"240","1W":"W","1M":"M"}.get(tf,"D")
            tv_html=f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#0a0d14;width:100%;height:620px;overflow:hidden;}}</style>
</head><body><div id="tc" style="width:100%;height:620px;"></div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>new TradingView.widget({{
  "autosize":false,"width":"100%","height":620,
  "symbol":"{tv_s}","interval":"{tv_tf}","timezone":"Asia/Kolkata",
  "theme":"dark","style":"1","locale":"en","toolbar_bg":"#0a0d14",
  "enable_publishing":false,"container_id":"tc","allow_symbol_change":true,
  "studies":["RSI@tv-basicstudies","MACD@tv-basicstudies","Volume@tv-basicstudies","BB@tv-basicstudies"],
  "overrides":{{
    "mainSeriesProperties.candleStyle.upColor":"#26a69a","mainSeriesProperties.candleStyle.downColor":"#ef5350",
    "mainSeriesProperties.candleStyle.borderUpColor":"#26a69a","mainSeriesProperties.candleStyle.borderDownColor":"#ef5350",
    "mainSeriesProperties.candleStyle.wickUpColor":"#26a69a","mainSeriesProperties.candleStyle.wickDownColor":"#ef5350",
    "paneProperties.background":"#0a0d14","paneProperties.vertGridProperties.color":"rgba(255,255,255,0.03)",
    "paneProperties.horzGridProperties.color":"rgba(255,255,255,0.03)"
  }},
  "studies_overrides":{{"volume.volume.color.0":"#ef535044","volume.volume.color.1":"#26a69a44"}}
}});</script></body></html>"""
            components.html(tv_html,height=634,scrolling=False)

            # Quick stats below TV chart
            rsi_v=tech.get("rsi",50); trend=tech.get("trend","—")
            tc_="#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"
            sup=tech.get("supports",[]); res=tech.get("resistances",[])
            vr=tech.get("vol_ratio",1); atr_v=tech.get("atr",0)
            perf1m=tech.get("perf1m",0); perf3m=tech.get("perf3m",0)
            st.markdown(f"""<div style="background:rgba(13,17,28,0.95);backdrop-filter:blur(15px);
            border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:8px 16px;
            margin:5px 0;display:flex;gap:16px;flex-wrap:wrap;align-items:center;">
              <span style="color:#fff;font-weight:800;">{name}</span>
              <span style="color:{tc_};font-weight:700;background:{tc_}18;padding:2px 10px;border-radius:20px;">{trend}</span>
              <span style="color:#6a6e7a;font-size:12px;">RSI <b style="color:#d1d4dc;">{rsi_v:.1f}</b></span>
              <span style="color:#6a6e7a;font-size:12px;">Vol <b style="color:#d1d4dc;">{vr:.2f}x</b></span>
              <span style="color:#6a6e7a;font-size:12px;">ATR <b style="color:#d1d4dc;">{atr_v:.4f}</b></span>
              <span style="color:#6a6e7a;font-size:12px;">Supp <b style="color:#26a69a;">{round(sup[0],2) if sup else '—'}</b></span>
              <span style="color:#6a6e7a;font-size:12px;">Res <b style="color:#ef5350;">{round(res[0],2) if res else '—'}</b></span>
              <span style="color:#6a6e7a;font-size:12px;">1M <b style="color:{'#26a69a' if perf1m>0 else '#ef5350'};">{perf1m:+.1f}%</b></span>
              <span style="color:#6a6e7a;font-size:12px;">3M <b style="color:{'#26a69a' if perf3m>0 else '#ef5350'};">{perf3m:+.1f}%</b></span>
              <span style="margin-left:auto;color:#4a5568;font-size:11px;">👆 Click <b style="color:#2962ff;">🤖 Analyse</b> for AI chart</span>
            </div>""",unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════
        # AI CHART MODE — FinSage inbuilt chart with full drawings
        # ══════════════════════════════════════════════════════════════
        else:
            if st.session_state.ud_ai is None:
                trader_choice=st.session_state.get("ud_trader","all")
                with st.spinner(f"🤖 SAGE AI: Analysing {name} — drawing S/R, Fibonacci, Patterns, SMC, Volume Profile..."):
                    fund=_fundamental(sym)
                    ai_res=_ai_full(sym,name,tech,fund,trader_choice)
                st.session_state.ud_ai=ai_res
                st.session_state.ud_fund=fund
            else:
                ai_res=st.session_state.ud_ai
                fund=st.session_state.ud_fund

            # FinSage Inbuilt Pro Chart
            chart_html=_pro_chart_html(df,tech,ai_res,sym,height=640)
            components.html(chart_html,height=655,scrolling=False)

            # ── ANALYSIS SUMMARY ──────────────────────────────────────
            bc=ai_res.get("bias_color","#f59e0b"); bias=ai_res.get("bias","NEUTRAL")
            rat=ai_res.get("rating","HOLD"); rc2=ai_res.get("rating_color","#f59e0b")
            conf=ai_res.get("confidence",65); api_u=ai_res.get("_api","AI")
            entry_v=ai_res.get("entry",0); stop_v=ai_res.get("stop",0)
            t1_v=ai_res.get("t1",0); t2_v=ai_res.get("t2",0)
            rr=ai_res.get("rr","—"); qual=ai_res.get("quality","—")
            rsi_v=tech.get("rsi",50); trend=tech.get("trend","—")
            sup=tech.get("supports",[]); res_=tech.get("resistances",[])
            vr=tech.get("vol_ratio",1); atr_v=tech.get("atr",0)
            tc_="#26a69a" if trend=="BULLISH" else "#ef5350" if trend=="BEARISH" else "#f59e0b"

            # Summary bar
            st.markdown(f"""<div style="background:rgba(13,17,28,0.95);backdrop-filter:blur(20px);
            border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:10px 16px;margin:5px 0;
            display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
              <span style="background:{rc2}18;color:{rc2};border:1px solid {rc2}33;border-radius:20px;
                padding:4px 14px;font-weight:800;font-size:13px;">{rat}</span>
              <span style="color:{bc};font-weight:800;font-size:15px;">{bias}</span>
              <span style="color:#9598a1;font-size:12px;">{ai_res.get('summary','')[:120]}</span>
              <span style="margin-left:auto;color:#4a5568;font-size:10px;">via {api_u} · {conf}% confidence</span>
            </div>""",unsafe_allow_html=True)

            # ── Tabbed analysis ───────────────────────────────────────
            tabs=st.tabs(["📊 Summary","📈 Indicators","🏦 SMC","📦 Volume","🌊 Wave+Fib","📋 Setup","📄 Report"])

            # ── TAB 1: SUMMARY ────────────────────────────────────────
            with tabs[0]:
                c1,c2,c3=st.columns(3)
                with c1:
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                    border-radius:10px;padding:12px;">
                    <div style="font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">📊 Price Action</div>
                    <div style="font-size:12px;color:#c8cad0;line-height:1.7;">{ai_res.get('price_action_view','—')}</div>
                    </div>""",unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                    border-radius:10px;padding:12px;">
                    <div style="font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">🏦 SMC View</div>
                    <div style="font-size:12px;color:#c8cad0;line-height:1.7;">{ai_res.get('smc_view','—')[:200]}</div>
                    </div>""",unsafe_allow_html=True)
                with c3:
                    # S/R levels visual
                    sup_disp=tech.get("supports",[]); res_disp=tech.get("resistances",[])
                    sr_html="<div style='font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;'>🎯 Key Levels</div>"
                    for r in res_disp[:3]:
                        dist=round((r-pr)/pr*100,1) if pr else 0
                        sr_html+=f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.03);font-size:11px;"><span style="color:#ef5350;">Res</span><span style="font-family:monospace;color:#d1d4dc;">{r:.4f}</span><span style="color:#ef5350;font-size:10px;">+{dist:.1f}%</span></div>'
                    for s in sup_disp[:3]:
                        dist=round((pr-s)/pr*100,1) if pr else 0
                        sr_html+=f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.03);font-size:11px;"><span style="color:#26a69a;">Sup</span><span style="font-family:monospace;color:#d1d4dc;">{s:.4f}</span><span style="color:#26a69a;font-size:10px;">-{dist:.1f}%</span></div>'
                    st.markdown(f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:12px;">{sr_html}</div>',unsafe_allow_html=True)

                # Patterns detected
                pats=tech.get("patterns",[])
                if pats:
                    st.markdown("**Candlestick Patterns Detected:**")
                    pat_cols=st.columns(min(len(pats),4))
                    for i,p in enumerate(pats[:4]):
                        with pat_cols[i]:
                            pc="#26a69a" if p["type"]=="BULLISH" else "#ef5350" if p["type"]=="BEARISH" else "#f59e0b"
                            icon="▲" if p["type"]=="BULLISH" else "▼" if p["type"]=="BEARISH" else "◆"
                            st.markdown(f"""<div style="background:{pc}11;border:1px solid {pc}33;border-radius:8px;
                            padding:8px;text-align:center;">
                            <div style="color:{pc};font-size:18px;font-weight:900;">{icon}</div>
                            <div style="font-size:11px;font-weight:700;color:#d1d4dc;">{p['name']}</div>
                            <div style="font-size:9px;color:{pc};">{p['type']}</div>
                            </div>""",unsafe_allow_html=True)

            # ── TAB 2: INDICATORS ─────────────────────────────────────
            with tabs[1]:
                st.markdown(f"""<div style="background:rgba(41,98,255,0.06);border:1px solid rgba(41,98,255,0.15);
                border-radius:8px;padding:10px 14px;margin-bottom:10px;font-size:13px;color:#c8cad0;line-height:1.75;">
                <b style="color:#4a9eff;">Indicator Confluence Summary:</b><br>{ai_res.get('indicator_view','')}</div>""",unsafe_allow_html=True)

                p=tech.get("price",0); e20=tech.get("ema20",0); e50=tech.get("ema50",0)
                e200=tech.get("ema200",0); vwap_v=tech.get("vwap",0)
                bb_u=tech.get("bb_upper",0); bb_l=tech.get("bb_lower",0)
                stoch=tech.get("stoch_rsi",50); macd_h=tech.get("macd_h",0)
                inds=[
                    ("RSI 14",f"{rsi_v:.1f}","#ef5350" if rsi_v>70 else "#26a69a" if rsi_v<30 else "#d1d4dc",
                     "Overbought — watch for reversal" if rsi_v>70 else "Oversold — bounce likely" if rsi_v<30 else "Neutral zone"),
                    ("Stoch RSI",f"{stoch:.1f}","#ef5350" if stoch>80 else "#26a69a" if stoch<20 else "#d1d4dc",
                     "Overbought" if stoch>80 else "Oversold" if stoch<20 else "Neutral"),
                    ("MACD Hist",f"{macd_h:.4f}","#26a69a" if macd_h>0 else "#ef5350",
                     "Bullish — momentum up" if macd_h>0 else "Bearish — momentum down"),
                    ("vs EMA 20",f"{e20:.4f}","#26a69a" if p>e20 else "#ef5350",
                     f"Price {'above' if p>e20 else 'below'} EMA20 — {'bullish' if p>e20 else 'bearish'} signal"),
                    ("vs EMA 50",f"{e50:.4f}","#26a69a" if p>e50 else "#ef5350",
                     f"Price {'above' if p>e50 else 'below'} EMA50 — {'trend intact' if p>e50 else 'trend weak'}"),
                    ("vs EMA 200",f"{e200:.4f}","#26a69a" if p>e200 else "#ef5350",
                     f"{'Above' if p>e200 else 'Below'} long-term average"),
                    ("vs VWAP",f"{vwap_v:.4f}","#26a69a" if p>vwap_v else "#ef5350",
                     f"Price {'above' if p>vwap_v else 'below'} VWAP — {'institutional buy zone' if p>vwap_v else 'selling pressure'}"),
                    ("BB Position",f"{round((p-bb_l)/(bb_u-bb_l)*100,1) if bb_u!=bb_l else 50:.1f}%",
                     "#ef5350" if p>bb_u else "#26a69a" if p<bb_l else "#d1d4dc",
                     "Upper band — overbought" if p>bb_u else "Lower band — oversold" if p<bb_l else "Mid-band — range"),
                    ("Volume",f"{vr:.2f}x","#2962ff" if vr>1.5 else "#26a69a" if vr>1 else "#d1d4dc",
                     f"{'High conviction move' if vr>1.5 else 'Above average' if vr>1 else 'Below average — weak'} ({vr:.2f}x avg)"),
                ]
                ic=st.columns(3)
                for i,(ind,val,col,desc) in enumerate(inds):
                    with ic[i%3]:
                        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                        border-radius:8px;padding:10px;margin-bottom:6px;">
                        <div style="font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:.06em;">{ind}</div>
                        <div style="font-size:18px;font-weight:900;color:{col};font-family:'Courier New';">{val}</div>
                        <div style="font-size:10px;color:{col};line-height:1.4;">{desc}</div>
                        </div>""",unsafe_allow_html=True)

                # Fibonacci
                st.markdown("**Fibonacci Retracement Levels:**")
                fib=tech.get("fib",{})
                fib_cols=st.columns(5)
                fib_c={"0.236":"#7986cb","0.382":"#26a69a","0.500":"#fbbf24","0.618":"#ef5350","0.786":"#e040fb"}
                for i,(k,v_fib) in enumerate(fib.items()):
                    with fib_cols[i]:
                        is_near=abs(v_fib-pr)/pr<0.015 if pr else False
                        fc3=fib_c.get(k,"#6a6e7a")
                        st.markdown(f"""<div style="background:{fc3}11;border:{'2px solid '+fc3 if is_near else '1px solid '+fc3+'33'};
                        border-radius:8px;padding:8px;text-align:center;">
                        <div style="font-size:11px;color:{fc3};font-weight:700;">{k}</div>
                        <div style="font-size:14px;font-weight:900;color:#d1d4dc;font-family:'Courier New';">{v_fib:.4f}</div>
                        {'<div style="font-size:9px;color:'+fc3+';font-weight:700;">← NEAR</div>' if is_near else ''}
                        </div>""",unsafe_allow_html=True)

            # ── TAB 3: SMC ────────────────────────────────────────────
            with tabs[2]:
                st.markdown(f"""<div style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.15);
                border-radius:8px;padding:10px 14px;margin-bottom:10px;font-size:13px;color:#c8cad0;line-height:1.75;">
                <b style="color:#f59e0b;">SMC / ICT Analysis:</b><br>{ai_res.get('smc_view','')}</div>""",unsafe_allow_html=True)

                c1,c2,c3=st.columns(3)
                with c1:
                    st.markdown('<div style="font-size:11px;color:#f59e0b;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Order Blocks</div>',unsafe_allow_html=True)
                    ob_list2=ai_res.get("order_blocks",tech.get("order_blocks",[]))
                    if ob_list2:
                        for ob in ob_list2[:4]:
                            oc="#26a69a" if "BULL" in ob.get("type","") else "#ef5350"
                            st.markdown(f"""<div style="background:{oc}0d;border-left:3px solid {oc};
                            border-radius:0 8px 8px 0;padding:8px 10px;margin:4px 0;font-size:11px;color:#c8cad0;">
                            <b style="color:{oc};">{'🟢' if 'BULL' in ob.get('type','') else '🔴'} {ob.get('type','OB')}</b><br>
                            Zone: <span style="font-family:monospace;">{ob.get('zone_bot',0):.4f} – {ob.get('zone_top',0):.4f}</span><br>
                            <span style="color:#6a6e7a;font-size:10px;">{ob.get('significance','Monitor for reaction')[:55]}</span>
                            </div>""",unsafe_allow_html=True)
                    else:
                        ob_raw=tech.get("order_blocks",[])
                        for ob in ob_raw[:3]:
                            oc="#26a69a" if "BULL" in ob.get("type","") else "#ef5350"
                            st.markdown(f"""<div style="background:{oc}0d;border-left:3px solid {oc};
                            border-radius:0 8px 8px 0;padding:8px 10px;margin:4px 0;font-size:11px;">
                            <b style="color:{oc};">{ob.get('type','OB')}</b> &nbsp;
                            <span style="font-family:monospace;color:#d1d4dc;">{ob.get('bot',ob.get('zone_bot',0)):.4f} – {ob.get('top',ob.get('zone_top',0)):.4f}</span>
                            </div>""",unsafe_allow_html=True)
                with c2:
                    st.markdown('<div style="font-size:11px;color:#2962ff;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Fair Value Gaps</div>',unsafe_allow_html=True)
                    fvg_zones=ai_res.get("fvg_zones",tech.get("fvg",[]))
                    for fv in fvg_zones[:4]:
                        fc2="#26a69a" if "BULL" in fv.get("type","") else "#ef5350"
                        st.markdown(f"""<div style="background:{fc2}0d;border-left:3px solid {fc2};
                        border-radius:0 8px 8px 0;padding:8px 10px;margin:4px 0;font-size:11px;color:#c8cad0;">
                        <b style="color:{fc2};">{'🟢' if 'BULL' in fv.get('type','') else '🔴'} FVG {fv.get('type','')}</b><br>
                        <span style="font-family:monospace;">{fv.get('bot',0):.4f} – {fv.get('top',0):.4f}</span><br>
                        <span style="color:#6a6e7a;font-size:10px;">{fv.get('desc','Fair value gap zone')[:55]}</span>
                        </div>""",unsafe_allow_html=True)
                with c3:
                    st.markdown('<div style="font-size:11px;color:#a855f7;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Liquidity Pools</div>',unsafe_allow_html=True)
                    liq=ai_res.get("liquidity_zones",[])
                    if liq:
                        for lz in liq[:4]:
                            lt="#2962ff" if "buy" in lz.get("type","").lower() else "#ef5350"
                            st.markdown(f"""<div style="background:{lt}0d;border-left:3px solid {lt};
                            border-radius:0 8px 8px 0;padding:8px 10px;margin:4px 0;font-size:11px;color:#c8cad0;">
                            <b style="color:{lt};">{lz.get('type','LIQUIDITY').upper()}</b><br>
                            Level: <span style="font-family:monospace;">{lz.get('level',0):.4f}</span><br>
                            <span style="color:#6a6e7a;font-size:10px;">{lz.get('desc','Stop hunt zone')[:55]}</span>
                            </div>""",unsafe_allow_html=True)
                    else:
                        sup2=tech.get("supports",[]); res2=tech.get("resistances",[])
                        st.markdown(f"""<div style="background:rgba(41,98,255,0.05);border:1px solid rgba(41,98,255,0.15);border-radius:8px;padding:8px;font-size:11px;color:#c8cad0;">
                        <b style="color:#2962ff;">Equal Highs:</b> {round(res2[0],4) if res2 else '—'}<br>
                        <b style="color:#2962ff;">Equal Lows:</b> {round(sup2[-1],4) if sup2 else '—'}<br>
                        <span style="color:#6a6e7a;font-size:10px;">Smart money targets these zones for stop hunts before reversing</span>
                        </div>""",unsafe_allow_html=True)

            # ── TAB 4: VOLUME ─────────────────────────────────────────
            with tabs[3]:
                st.markdown(f"""<div style="background:rgba(41,98,255,0.06);border:1px solid rgba(41,98,255,0.15);
                border-radius:8px;padding:10px 14px;margin-bottom:8px;font-size:13px;color:#c8cad0;line-height:1.75;">
                <b style="color:#4a9eff;">Volume & Order Flow Analysis:</b><br>
                {ai_res.get('volume_view','')} <br><br>
                {ai_res.get('volume_analysis','')}</div>""",unsafe_allow_html=True)

                vp=tech.get("vp",[]); max_vp=max([x["vol"] for x in vp],default=1) or 1
                if vp:
                    st.markdown("**Volume Profile — Price × Volume (Top 12 Nodes):**")
                    for vi in vp[:12]:
                        pct=vi["vol"]/max_vp*100; is_poc=vi["vol"]==max_vp
                        vc="#2962ff" if is_poc else "#26a69a" if vi["price"]<pr else "#ef5350"
                        label=f"🔵 POC @ {vi['price']:.2f}" if is_poc else f"{'🟢' if vi['price']<pr else '🔴'} {vi['price']:.2f}"
                        st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;margin:2px 0;font-size:11px;">
                        <span style="width:100px;color:{vc};font-weight:{'700' if is_poc else '400'};">{label}</span>
                        <div style="flex:1;background:rgba(255,255,255,0.04);border-radius:2px;height:12px;">
                          <div style="background:{vc};opacity:{'1' if is_poc else '0.6'};height:12px;border-radius:2px;width:{pct:.0f}%;"></div>
                        </div>
                        <span style="width:45px;color:{vc};text-align:right;">{pct:.0f}%</span>
                        </div>""",unsafe_allow_html=True)

            # ── TAB 5: WAVE + FIB ─────────────────────────────────────
            with tabs[4]:
                c1,c2=st.columns(2)
                with c1:
                    st.markdown(f"""<div style="background:rgba(168,85,247,0.06);border:1px solid rgba(168,85,247,0.15);
                    border-radius:10px;padding:12px;font-size:13px;color:#c8cad0;line-height:1.75;">
                    <b style="color:#a855f7;font-size:14px;">🌊 Elliott Wave Analysis:</b><br><br>
                    {ai_res.get('wave_view','')}</div>""",unsafe_allow_html=True)
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                    border-radius:8px;padding:10px;margin-top:8px;font-size:12px;color:#c8cad0;line-height:1.6;">
                    <b style="color:#6a6e7a;">MULTI-TIMEFRAME:</b><br>
                    {''.join([f"<div style='padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.03);'><b style='color:#4a5568;font-size:10px;text-transform:uppercase;'>{k}</b> — {v}</div>" for k,v in ai_res.get('multi_tf',{}).items()])}</div>""",unsafe_allow_html=True)
                with c2:
                    st.markdown('<b style="color:#26a69a;font-size:13px;">📐 Fibonacci Levels</b>',unsafe_allow_html=True)
                    fib=tech.get("fib",{})
                    fib_c2={"0.236":"#7986cb","0.382":"#26a69a","0.500":"#fbbf24","0.618":"#ef5350","0.786":"#e040fb"}
                    for k,v_fib in fib.items():
                        is_near=abs(v_fib-pr)/pr<0.015 if pr else False
                        fc4=fib_c2.get(k,"#6a6e7a"); dist=round((v_fib-pr)/pr*100,2) if pr else 0
                        st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;padding:7px 10px;
                        border-radius:8px;margin:3px 0;background:{'rgba(255,255,255,0.06)' if is_near else 'rgba(255,255,255,0.02)'};
                        border:{'1.5px solid '+fc4 if is_near else '1px solid rgba(255,255,255,0.05)'};">
                        <span style="width:50px;color:{fc4};font-weight:700;font-size:12px;">Fib {k}</span>
                        <span style="flex:1;font-family:monospace;font-size:14px;font-weight:700;color:#d1d4dc;">{v_fib:.4f}</span>
                        <span style="font-size:10px;color:{'#26a69a' if dist<0 else '#ef5350'};">{dist:+.2f}%</span>
                        {'<span style="font-size:9px;color:'+fc4+';font-weight:700;border:1px solid '+fc4+';border-radius:10px;padding:1px 6px;">NEAR</span>' if is_near else ''}
                        </div>""",unsafe_allow_html=True)
                    # H/L
                    h60=tech.get("h60",0); l60=tech.get("l60",0)
                    if h60 and l60:
                        st.markdown(f"""<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);
                        border-radius:8px;padding:8px 10px;margin-top:8px;font-size:11px;color:#9598a1;">
                        <b>60-bar High:</b> {h60:.4f} &nbsp; <b>60-bar Low:</b> {l60:.4f}<br>
                        <b>Range:</b> {round(h60-l60,4):.4f} &nbsp; <b>Position:</b> {round((pr-l60)/(h60-l60)*100,1) if h60!=l60 else 50:.1f}% of range
                        </div>""",unsafe_allow_html=True)

            # ── TAB 6: SETUP ──────────────────────────────────────────
            with tabs[5]:
                c1,c2,c3=st.columns([1,1,1])
                with c1:
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
                    border-radius:12px;padding:14px;">
                    <div style="font-size:11px;color:#4a5568;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px;font-weight:700;">🎯 Trade Setup</div>
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                      <span style="color:#26a69a;font-weight:700;font-size:13px;">Entry</span>
                      <span style="color:#26a69a;font-family:'Courier New';font-size:16px;font-weight:900;">{entry_v:.4f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                      <span style="color:#ef5350;font-weight:700;font-size:13px;">Stop Loss</span>
                      <span style="color:#ef5350;font-family:'Courier New';font-size:16px;font-weight:900;">{stop_v:.4f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                      <span style="color:#2962ff;font-weight:600;">Target 1</span>
                      <span style="color:#2962ff;font-family:'Courier New';font-size:15px;font-weight:800;">{t1_v:.4f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                      <span style="color:#9c27b0;font-weight:600;">Target 2</span>
                      <span style="color:#9c27b0;font-family:'Courier New';font-size:15px;font-weight:800;">{t2_v:.4f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:10px 0 4px;">
                      <span style="color:#6a6e7a;font-size:12px;">R:R &nbsp; Quality</span>
                      <span style="font-weight:900;font-size:20px;color:{bc};">{rr}</span>
                    </div>
                    <div style="text-align:right;font-size:11px;color:#4a5568;">{qual}</div>
                    </div>""",unsafe_allow_html=True)
                with c2:
                    th_html="".join([f'<div style="padding:5px 0 5px 16px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;color:#c8cad0;position:relative;line-height:1.5;"><span style="position:absolute;left:0;color:#26a69a;font-weight:900;font-size:14px;">+</span>{t}</div>' for t in ai_res.get("thesis",[])])
                    rk_html="".join([f'<div style="padding:5px 0 5px 16px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;color:#c8cad0;position:relative;line-height:1.5;"><span style="position:absolute;left:0;color:#ef5350;font-weight:900;font-size:14px;">−</span>{r}</div>' for r in ai_res.get("risks",[])])
                    st.markdown(f"""<div style="background:rgba(38,166,154,0.05);border:1px solid rgba(38,166,154,0.15);border-radius:10px;padding:12px;margin-bottom:8px;">
                    <div style="font-size:11px;color:#26a69a;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Bull Thesis</div>{th_html}</div>
                    <div style="background:rgba(239,83,80,0.05);border:1px solid rgba(239,83,80,0.15);border-radius:10px;padding:12px;">
                    <div style="font-size:11px;color:#ef5350;font-weight:700;text-transform:uppercase;margin-bottom:6px;">Risk Factors</div>{rk_html}</div>""",unsafe_allow_html=True)
                with c3:
                    mtf=ai_res.get("multi_tf",{})
                    mtf_html="".join([f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;"><span style="color:#4a5568;text-transform:uppercase;font-size:10px;font-weight:700;">{k}</span><span style="color:#c8cad0;line-height:1.4;">{v}</span></div>' for k,v in mtf.items()])
                    catalyst=ai_res.get("catalyst","")
                    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:12px;margin-bottom:8px;">
                    <div style="font-size:11px;color:#4a5568;text-transform:uppercase;font-weight:700;margin-bottom:6px;">Multi-Timeframe</div>{mtf_html}</div>
                    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:10px;padding:10px;">
                    <div style="font-size:11px;color:#4a5568;text-transform:uppercase;font-weight:700;margin-bottom:4px;">Key Catalyst</div>
                    <div style="font-size:12px;color:#c8cad0;">{catalyst}</div>
                    <hr style="border-color:rgba(255,255,255,0.04);margin:8px 0;">
                    <div style="font-size:11px;color:#6a6e7a;">{ai_res.get('fundamental_quick','')}</div>
                    </div>""",unsafe_allow_html=True)

            # ── TAB 7: FULL REPORT ────────────────────────────────────
            with tabs[6]:
                st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                border-radius:10px;padding:10px 14px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
                <span style="color:#2962ff;font-size:15px;">📄</span>
                <span style="color:#d1d4dc;font-weight:700;">Full Institutional Report — {name} ({sym})</span>
                <span style="background:#2962ff22;color:#2962ff;font-size:9px;padding:2px 8px;border-radius:8px;">via {api_u}</span>
                </div>""",unsafe_allow_html=True)
                try:
                    wp=_white_paper_html(sym,name,tech,fund,ai_res)
                    if wp: components.html(wp,height=3600,scrolling=True)
                except Exception as e:
                    st.warning(f"Report loading... {e}")

            # Refresh button
            colx1,colx2,colx3=st.columns(3)
            with colx1:
                if st.button("🔄 Refresh Analysis",key="ud_re2",type="primary"):
                    st.session_state.ud_ai=None; st.rerun()
            with colx2:
                if st.button("📺 Switch to TradingView",key="ud_tv"):
                    st.session_state.ud_mode="tv"; st.session_state.ud_ai=None; st.rerun()
            with colx3:
                rep_txt=f"FinSage User Dashboard Analysis\n{name} ({sym})\n{datetime.now().strftime('%B %d, %Y')}\n\nRating: {rat} | Bias: {bias} | Confidence: {conf}%\nEntry: {entry_v:.4f} | Stop: {stop_v:.4f} | T1: {t1_v:.4f} | T2: {t2_v:.4f}\nR:R: {rr}\n\n{ai_res.get('summary','')}\n\nDISCLAIMER: Educational only. Not financial advice."
                st.download_button("📥 Download Report",rep_txt,
                                   f"finsage_{sym.replace('.','_').replace('^','')}_dashboard.txt",
                                   "text/plain",key="ud_dl")
