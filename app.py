"""
FinSage — Global Financial Intelligence Platform
Free APIs: yfinance + CoinGecko
Auth: Google OAuth + Email/Password
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
from datetime import datetime

from data_fetcher import fetch_stock_data, fetch_crypto_data, fetch_ticker_bar_data
from analyzer import analyze_stock, analyze_crypto, format_number
from auth_page import render_auth_page, render_sidebar_auth, is_logged_in, get_current_user, logout
from admin_panel import render_admin_panel
from ai_assistant import render_ai_assistant
from feedback_dashboard import render_feedback_dashboard
from advanced_features import render_advanced_features
from chart_analyzer import render_chart_analyzer

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="STOX AI — Analyze. Attract. Thrive.",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS — Cyberpunk Holographic 3D Futuristic ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600;700&display=swap');

/* ════════════════════════════════════════════
   HIDE STREAMLIT CHROME
════════════════════════════════════════════ */
#MainMenu,footer,header,
[data-testid="stToolbar"],[data-testid="manage-app-button"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"],
[data-testid="stBottom"],[data-testid="stSidebarCollapsedControl"],
.stDeployButton,.viewerBadge_container__r5tak,
button[kind="header"],.st-emotion-cache-czk5ss,
._link_gzau3_10,.st-emotion-cache-1dp5vir
{ display:none !important; visibility:hidden !important; }

/* ════════════════════════════════════════════
   BASE — DEEP SPACE OBSIDIAN
════════════════════════════════════════════ */
.stApp {
    background: #020609 !important;
    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(0,212,255,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 100%, rgba(110,64,201,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 40% 30% at 50% 50%, rgba(0,80,160,0.04) 0%, transparent 70%);
    color: #c9d1d9;
    font-family: 'Inter', sans-serif;
}

/* ════════════════════════════════════════════
   CYBER GRID BACKGROUND
════════════════════════════════════════════ */
.stApp::before {
    content: "";
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background-image:
        linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none; z-index: 0;
    animation: gridPulse 8s ease-in-out infinite;
}
@keyframes gridPulse {
    0%,100% { opacity:0.4; } 50% { opacity:0.8; }
}

/* ════════════════════════════════════════════
   SCROLLBAR — NEON CYAN
════════════════════════════════════════════ */
::-webkit-scrollbar { width:4px; height:3px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg,#00d4ff,#6e40c9);
    border-radius:4px;
    box-shadow: 0 0 8px rgba(0,212,255,0.6);
}

/* ════════════════════════════════════════════
   NAVBAR — GLASSMORPHISM + HOLOGRAPHIC
════════════════════════════════════════════ */
.stox-navbar {
    background: linear-gradient(135deg,
        rgba(2,6,9,0.92) 0%,
        rgba(10,20,35,0.88) 50%,
        rgba(2,6,9,0.92) 100%);
    border: 1px solid transparent;
    border-image: linear-gradient(90deg,
        rgba(0,212,255,0.4),
        rgba(110,64,201,0.4),
        rgba(0,212,255,0.4)) 1;
    border-radius: 16px;
    padding: 0.8rem 1.3rem;
    margin-bottom: 0.6rem;
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    box-shadow:
        0 0 40px rgba(0,212,255,0.08),
        0 0 80px rgba(110,64,201,0.06),
        inset 0 1px 0 rgba(255,255,255,0.05),
        inset 0 0 40px rgba(0,212,255,0.03);
    position: relative; overflow: hidden;
}
.stox-navbar::before {
    content:"";
    position:absolute; top:-1px; left:0; right:0; height:1px;
    background: linear-gradient(90deg,transparent,rgba(0,212,255,0.6),rgba(110,64,201,0.6),transparent);
    animation: scanLine 4s linear infinite;
}
@keyframes scanLine {
    0% { transform:translateX(-100%); } 100% { transform:translateX(100%); }
}

/* ════════════════════════════════════════════
   BRAND NAME — ORBITRON HOLOGRAPHIC
════════════════════════════════════════════ */
.stox-brand {
    font-family: 'Orbitron', monospace !important;
    font-size: 1.5rem !important; font-weight: 900 !important;
    background: linear-gradient(90deg, #00d4ff, #7b8cde, #a371f7, #00d4ff);
    background-size: 300% 100%;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: holoShift 5s linear infinite;
    letter-spacing: 0.08em;
    filter: drop-shadow(0 0 12px rgba(0,212,255,0.4));
}
@keyframes holoShift {
    0% { background-position:0% 50%; }
    100% { background-position:300% 50%; }
}
.stox-tagline {
    font-size: 0.6rem; color: #4a9eff; letter-spacing: 0.22em;
    font-weight: 600; text-transform: uppercase; opacity: 0.8;
    font-family: 'Orbitron', monospace;
}

/* ════════════════════════════════════════════
   LIVE TICKER BAR — 3D NEON SCROLL
════════════════════════════════════════════ */
.ticker-bar {
    background: linear-gradient(90deg,
        rgba(2,6,9,0.98) 0%,
        rgba(0,20,40,0.95) 50%,
        rgba(2,6,9,0.98) 100%);
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 10px;
    padding: 0.6rem 1.2rem;
    margin-bottom: 1rem;
    overflow-x: auto; white-space: nowrap;
    box-shadow:
        0 0 25px rgba(0,212,255,0.06),
        inset 0 1px 0 rgba(0,212,255,0.08),
        inset 0 -1px 0 rgba(110,64,201,0.08);
    scrollbar-width: none;
    position: relative;
}
.ticker-bar::-webkit-scrollbar { display:none; }
.ticker-sep {
    color: rgba(0,212,255,0.4); margin: 0 0.8rem;
    font-size: 0.75rem;
}
.ticker-live {
    color: #ff4444; font-weight:800; font-size:0.78rem;
    text-shadow: 0 0 8px rgba(255,68,68,0.7);
    animation: livePulse 1.2s ease-in-out infinite;
    font-family: 'Orbitron', monospace;
}
@keyframes livePulse {
    0%,100% { opacity:1; text-shadow:0 0 8px rgba(255,68,68,0.7); }
    50%      { opacity:0.6; text-shadow:0 0 4px rgba(255,68,68,0.3); }
}
.ticker-item {
    display: inline-flex; align-items: center;
    gap: 0.3rem; margin-right: 1.6rem;
    font-size: 0.78rem;
    padding: 0.15rem 0.5rem;
    border-radius: 5px;
    background: rgba(0,212,255,0.03);
    border: 1px solid rgba(0,212,255,0.07);
    transition: all 0.2s;
}
.ticker-item:hover {
    background: rgba(0,212,255,0.08);
    border-color: rgba(0,212,255,0.3);
    box-shadow: 0 0 10px rgba(0,212,255,0.15);
}
.ticker-sym  {
    color: #00d4ff; font-weight:800; font-size:0.75rem;
    letter-spacing:0.05em; font-family:'Orbitron',monospace;
    text-shadow: 0 0 6px rgba(0,212,255,0.5);
}
.ticker-price{ color: #c9d1d9; font-weight:600; font-size:0.75rem; }
.up   {
    color: #00ff88; font-weight:700;
    text-shadow: 0 0 6px rgba(0,255,136,0.5);
}
.down {
    color: #ff4466; font-weight:700;
    text-shadow: 0 0 6px rgba(255,68,102,0.5);
}
.ticker-type-badge {
    font-size:0.58rem; padding:0.05rem 0.25rem; border-radius:3px;
    font-weight:700; letter-spacing:0.05em;
}
.badge-crypto { background:rgba(110,64,201,0.25); color:#a371f7; border:1px solid rgba(110,64,201,0.3); }
.badge-stock  { background:rgba(0,100,200,0.2); color:#4a9eff; border:1px solid rgba(0,100,200,0.3); }
.badge-meme   { background:rgba(255,100,0,0.15); color:#ff8800; border:1px solid rgba(255,100,0,0.3); }

/* ════════════════════════════════════════════
   TABS — 3D HOLOGRAPHIC
════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(2,6,9,0.85);
    border-radius: 14px 14px 0 0;
    border: 1px solid rgba(0,212,255,0.1);
    border-bottom: none;
    gap: 0; padding: 0.35rem 0.35rem 0;
    backdrop-filter: blur(12px);
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: rgba(100,130,160,0.8);
    border-radius: 10px 10px 0 0; font-weight:600;
    font-size: 0.88rem; padding: 0.6rem 1.5rem; border:none;
    transition: all 0.25s ease;
    font-family: 'Inter', sans-serif;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #00d4ff !important;
    text-shadow: 0 0 8px rgba(0,212,255,0.4);
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(180deg,rgba(0,212,255,0.08),rgba(0,212,255,0.04)) !important;
    color: #00d4ff !important;
    border-top: 2px solid #00d4ff !important;
    box-shadow: 0 -6px 20px rgba(0,212,255,0.15) !important;
    text-shadow: 0 0 10px rgba(0,212,255,0.5) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: rgba(2,6,9,0.95);
    border: 1px solid rgba(0,212,255,0.08);
    border-top: none; border-radius: 0 0 14px 14px;
    padding: 1.5rem;
    box-shadow: inset 0 0 60px rgba(0,212,255,0.02);
}

/* ════════════════════════════════════════════
   BUTTONS — GLASSMORPHISM + GLOW
════════════════════════════════════════════ */
.stButton > button {
    background: linear-gradient(135deg,rgba(0,20,40,0.8),rgba(10,25,50,0.8)) !important;
    color: #00d4ff !important;
    border: 1px solid rgba(0,212,255,0.25) !important;
    border-radius: 9px !important;
    font-size: 0.83rem !important; font-weight:600 !important;
    transition: all 0.25s ease !important;
    backdrop-filter: blur(8px);
    box-shadow: 0 0 10px rgba(0,212,255,0.05), inset 0 1px 0 rgba(255,255,255,0.04);
}
.stButton > button:hover {
    background: linear-gradient(135deg,rgba(0,212,255,0.15),rgba(110,64,201,0.15)) !important;
    color: #ffffff !important;
    border-color: rgba(0,212,255,0.6) !important;
    box-shadow: 0 0 25px rgba(0,212,255,0.3), 0 0 50px rgba(0,212,255,0.1) !important;
    transform: translateY(-2px) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,#0066cc,#0044aa,#6e40c9) !important;
    color: white !important;
    border: 1px solid rgba(0,212,255,0.4) !important;
    box-shadow: 0 0 20px rgba(0,100,204,0.4), inset 0 1px 0 rgba(255,255,255,0.1) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg,#0080ff,#6e40c9,#00d4ff) !important;
    box-shadow: 0 0 35px rgba(0,128,255,0.5), 0 0 70px rgba(0,212,255,0.2) !important;
    transform: translateY(-2px) scale(1.01) !important;
}

/* ════════════════════════════════════════════
   INPUTS — GLASS
════════════════════════════════════════════ */
.stTextInput > div > div > input {
    background: rgba(0,10,20,0.8) !important;
    color: #c9d1d9 !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 9px !important;
    backdrop-filter: blur(8px);
}
.stTextInput > div > div > input:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0,212,255,0.25), inset 0 0 10px rgba(0,212,255,0.05) !important;
}
.stSelectbox > div > div,
.stTextArea > div > div > textarea {
    background: rgba(0,10,20,0.8) !important;
    color: #c9d1d9 !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 9px !important;
}

/* ════════════════════════════════════════════
   METRICS — 3D GLASS CARD
════════════════════════════════════════════ */
[data-testid="stMetric"] {
    background: linear-gradient(135deg,rgba(0,20,40,0.8),rgba(0,10,25,0.9)) !important;
    border: 1px solid rgba(0,212,255,0.12) !important;
    border-radius: 12px !important;
    padding: 0.7rem 0.9rem !important;
    backdrop-filter: blur(10px);
    box-shadow:
        0 0 20px rgba(0,212,255,0.05),
        inset 0 1px 0 rgba(255,255,255,0.04),
        inset 0 0 20px rgba(0,212,255,0.02);
    transition: all 0.3s ease;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(0,212,255,0.3) !important;
    box-shadow: 0 0 30px rgba(0,212,255,0.12) !important;
    transform: translateY(-2px);
}
[data-testid="stMetricLabel"] { color: #4a9eff !important; font-size:0.75rem !important; }
[data-testid="stMetricValue"] {
    color: #e6edf3 !important; font-weight:700 !important;
    text-shadow: 0 0 8px rgba(0,212,255,0.2);
}
[data-testid="stMetricDelta"] { font-weight:600 !important; }

/* ════════════════════════════════════════════
   SIDEBAR — DARK GLASS
════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,rgba(2,6,9,0.98),rgba(5,10,20,0.98)) !important;
    border-right: 1px solid rgba(0,212,255,0.1) !important;
    backdrop-filter: blur(20px);
}

/* ════════════════════════════════════════════
   MISC — ALERTS, DISCLAIMERS
════════════════════════════════════════════ */
.meme-warning {
    background: linear-gradient(135deg,rgba(10,0,0,0.9),rgba(30,0,0,0.8));
    border: 1px solid rgba(255,68,68,0.4); border-radius: 10px;
    padding: 0.75rem 0.9rem; color: #ff6680; font-size:0.82rem;
    box-shadow: 0 0 15px rgba(255,68,68,0.08);
}
.disclaimer {
    background: linear-gradient(135deg,rgba(5,10,15,0.9),rgba(10,15,5,0.8));
    border-left: 3px solid rgba(0,212,255,0.4);
    border-radius: 0 10px 10px 0; padding: 0.7rem 0.9rem;
    color: rgba(100,140,180,0.85); font-size: 0.77rem; margin-top: 0.9rem;
}
.user-badge {
    background: rgba(0,212,255,0.08); border: 1px solid rgba(0,212,255,0.25);
    border-radius: 20px; padding: 0.3rem 0.9rem;
    color: #00d4ff; font-size: 0.82rem;
    box-shadow: 0 0 10px rgba(0,212,255,0.1);
}

/* ════════════════════════════════════════════
   HR, HEADINGS
════════════════════════════════════════════ */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg,transparent,rgba(0,212,255,0.3),rgba(110,64,201,0.3),transparent) !important;
    margin: 0.5rem 0 !important;
}
h3, h2 {
    color: #e6edf3 !important;
    text-shadow: 0 0 15px rgba(0,212,255,0.1);
}

/* ════════════════════════════════════════════
   PLOTLY CHARTS — DARK
════════════════════════════════════════════ */
.js-plotly-plot .plotly { background:transparent !important; }

/* ════════════════════════════════════════════
   EXPANDER — GLASS
════════════════════════════════════════════ */
.streamlit-expanderHeader {
    background: rgba(0,10,20,0.7) !important;
    border: 1px solid rgba(0,212,255,0.15) !important;
    border-radius: 8px !important; color: #00d4ff !important;
}

/* ════════════════════════════════════════════
   BACK BUTTON — minimal
════════════════════════════════════════════ */
.back-btn button {
    background: transparent !important;
    color: rgba(0,212,255,0.7) !important;
    border: none !important; padding: 0.2rem 0.5rem !important;
    font-size: 0.8rem !important; width:auto !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session State ───────────────────────────────────────────────────────────── ──────────────────────────────────────────────────────────────
if "active_page" not in st.session_state:
    st.session_state.active_page = "main"

defaults = {
    "user": None,
    "stock_data": None, "stock_report": None,
    "crypto_data": None, "crypto_report": None,
    "meme_data": None, "meme_report": None,
    "ticker_data": [], "last_ticker_refresh": 0,
    "stock_selected": "", "crypto_selected": "", "meme_selected": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Public App — Optional Sidebar Login ──────────────────────────────────────
render_sidebar_auth()
user = get_current_user()

# ── Ticker refresh — every 60s auto ────────────────────────────────────────────
now_ts = time.time()
if now_ts - st.session_state.last_ticker_refresh > 60:
    st.session_state.ticker_data = fetch_ticker_bar_data()
    st.session_state.last_ticker_refresh = now_ts

# Auto-rerun every 60 seconds for live price updates
st_auto = st.empty()
if "last_auto_rerun" not in st.session_state:
    st.session_state.last_auto_rerun = time.time()
if time.time() - st.session_state.last_auto_rerun > 60:
    st.session_state.last_auto_rerun = time.time()
    time.sleep(0.1)
    st.rerun()

# ── Navbar ─────────────────────────────────────────────────────────────────────
nb_left, nb_right = st.columns([6, 1])
with nb_left:
    st.markdown("""
    <div class="stox-navbar" style="display:flex;align-items:center;gap:1rem;">
        <div style="position:relative;">
            <img src="https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"
                 style="height:48px;width:48px;border-radius:12px;object-fit:cover;
                 box-shadow:0 0 20px rgba(0,212,255,0.4),0 0 40px rgba(0,212,255,0.1);
                 border:1px solid rgba(0,212,255,0.3);">
            <div style="position:absolute;top:-2px;right:-2px;width:10px;height:10px;
            background:#00ff88;border-radius:50%;border:2px solid #020609;
            box-shadow:0 0 6px rgba(0,255,136,0.8);animation:livePulse 1.2s infinite;"></div>
        </div>
        <div>
            <div class="stox-brand">STOX AI</div>
            <div class="stox-tagline">Analyze &middot; Attract &middot; Thrive</div>
        </div>
        <div style="margin-left:0.5rem;display:flex;flex-direction:column;gap:0.25rem;">
            <span style="background:linear-gradient(135deg,rgba(0,255,136,0.1),rgba(0,255,136,0.05));
            color:#00ff88;padding:0.15rem 0.6rem;border-radius:20px;font-size:0.65rem;font-weight:700;
            border:1px solid rgba(0,255,136,0.25);letter-spacing:0.08em;
            box-shadow:0 0 10px rgba(0,255,136,0.15);">✅ 100% FREE</span>
            <span style="background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(110,64,201,0.08));
            color:#a371f7;padding:0.12rem 0.5rem;border-radius:20px;font-size:0.6rem;font-weight:600;
            border:1px solid rgba(110,64,201,0.2);letter-spacing:0.05em;">🤖 AI POWERED</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with nb_right:
    st.markdown("<div style='padding-top:0.4rem;'>", unsafe_allow_html=True)
    with st.popover("⋮", use_container_width=True):
        st.markdown("""
        <div style="font-size:0.82rem;font-weight:700;color:#00d4ff;margin-bottom:0.5rem;
        letter-spacing:0.08em;font-family:Orbitron,monospace;text-shadow:0 0 8px rgba(0,212,255,0.5);">
        ⚡ NAVIGATION
        </div>""", unsafe_allow_html=True)
        
        menu_items = {
            "🤖 AI Assistant": "🤖 AI Assistant",
            "📸 Chart Analyzer": "📸 Chart Analyzer",
            "⭐ Community": "⭐ Feedback & Community",
            "🧠 Advanced Intel": "🧠 Advanced Intelligence",
        }
        for label, page_key in menu_items.items():
            if st.button(label, key=f"nav_{label}", use_container_width=True):
                st.session_state.active_page = page_key
                st.rerun()
        
        if user:
            st.markdown("---")
            if st.button("🚪 Logout", key="logout_dot_menu", use_container_width=True):
                logout()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:0.3rem 0 0.7rem;'>", unsafe_allow_html=True)

# ── Live Ticker Bar ────────────────────────────────────────────────────────────
if st.session_state.ticker_data:
    # Separate sections: crypto, stocks, meme
    crypto_items = [i for i in st.session_state.ticker_data if i.get("type") == "crypto"
                    and i["symbol"] not in ["DOGE","SHIB","PEPE","FLOKI","BONK"]]
    meme_items   = [i for i in st.session_state.ticker_data if i["symbol"] in ["DOGE","SHIB","PEPE","FLOKI","BONK"]]
    stock_items  = [i for i in st.session_state.ticker_data if i.get("type") == "stock"]

    def _ticker_item(item):
        chg   = item.get("change", 0) or 0
        p     = item.get("price", 0) or 0
        cls   = "up" if chg >= 0 else "down"
        arrow = "▲" if chg >= 0 else "▼"
        ps    = f"${p:.8f}".rstrip("0") if p < 0.001 else (f"${p:,.4f}" if p < 0.1 else f"${p:,.2f}")
        t     = item.get("type","crypto")
        badge_cls = "badge-meme" if item["symbol"] in ["DOGE","SHIB","PEPE","FLOKI","BONK"] else (
                    "badge-stock" if t == "stock" else "badge-crypto")
        badge_lbl = "MEME" if badge_cls == "badge-meme" else ("STK" if t == "stock" else "DeFi")
        return (f'<span class="ticker-item">' +
                f'<span class="ticker-sym">{item["symbol"]}</span>' +
                f'<span class="ticker-price">{ps}</span>' +
                f'<span class="{cls}">{arrow}{abs(chg):.2f}%</span>' +
                f'<span class="ticker-type-badge {badge_cls}">{badge_lbl}</span>' +
                f'</span>')

    def _sep(label, color):
        return (f'<span class="ticker-sep" style="color:{color};font-size:0.65rem;' +
                f'font-weight:800;letter-spacing:0.1em;font-family:Orbitron,monospace;">{label}</span>')

    ticker_html  = '<div class="ticker-bar">'
    ticker_html += '<span class="ticker-live">◉ LIVE</span>'
    ticker_html += _sep("  CRYPTO", "#00d4ff")
    for it in crypto_items: ticker_html += _ticker_item(it)
    ticker_html += _sep("  STOCKS", "#4a9eff")
    for it in stock_items:  ticker_html += _ticker_item(it)
    ticker_html += _sep("  MEME", "#ff8800")
    for it in meme_items:   ticker_html += _ticker_item(it)
    ticker_html += '</div>'
    st.markdown(ticker_html, unsafe_allow_html=True)


# ── Results Renderer ───────────────────────────────────────────────────────────
def render_results(data, report):
    if not data or not report:
        return

    name = data.get("name", data.get("ticker", ""))
    ticker = data.get("ticker", "")
    price = data.get("current_price", 0) or 0
    change = data.get("change_pct", 0) or 0
    market_cap = data.get("market_cap", 0) or 0
    risk = data.get("risk_score", 5) or 5
    vol = data.get("volatility_annualized", 0) or 0
    currency = data.get("currency", "USD")
    asset_t = data.get("asset_type", "Asset")

    st.markdown(f"### 📊 {name} ({ticker}) — {asset_t}")

    k1, k2, k3, k4, k5 = st.columns(5)
    if price < 0.0001:   price_str = f"${price:.8f}"
    elif price < 0.01:   price_str = f"${price:.6f}"
    else:                price_str = f"{currency} {price:,.2f}"

    with k1: st.metric("💰 Price", price_str)
    with k2: st.metric("📈 24H", f"{change:+.2f}%")
    with k3: st.metric("🏦 Mkt Cap", format_number(market_cap))
    with k4: st.metric("⚡ Volatility", f"{vol:.1f}%")
    with k5: st.metric("🎯 Risk", f"{risk}/10")

    st.markdown("---")
    col_chart, col_info = st.columns([3, 2])

    with col_chart:
        history = data.get("history")
        if history is not None and isinstance(history, pd.DataFrame) and not history.empty:
            st.markdown("#### 📈 30-Day Price Chart")
            close_col = "Close" if "Close" in history.columns else history.columns[0]
            y_data = history[close_col]
            if len(y_data) > 1:
                is_up = float(y_data.iloc[-1]) >= float(y_data.iloc[0])
                color = "#3fb950" if is_up else "#f85149"
                fill_color = "rgba(63,185,80,0.1)" if is_up else "rgba(248,81,73,0.1)"
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=history.index, y=y_data, mode="lines",
                    line=dict(color=color, width=2),
                    fill="tozeroy", fillcolor=fill_color,
                    hovertemplate="<b>%{x}</b><br>%{y:,.6f}<extra></extra>"
                ))
                fig.update_layout(
                    plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                    font=dict(color="#c9d1d9"),
                    xaxis=dict(gridcolor="#21262d"),
                    yaxis=dict(gridcolor="#21262d"),
                    margin=dict(l=0, r=0, t=10, b=0),
                    height=270, showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

    with col_info:
        st.markdown("#### 📋 Key Metrics")
        if data.get("asset_type") == "Stock":
            metrics = [
                ("Sector", data.get("sector", "N/A")),
                ("P/E Ratio", f"{data.get('pe_ratio'):.1f}x" if data.get("pe_ratio") else "N/A"),
                ("EPS", f"{currency} {data.get('eps'):.2f}" if data.get("eps") else "N/A"),
                ("Beta", f"{data.get('beta'):.2f}" if data.get("beta") else "N/A"),
                ("52W High", f"{currency} {data.get('week_52_high'):,.2f}" if data.get("week_52_high") else "N/A"),
                ("52W Low", f"{currency} {data.get('week_52_low'):,.2f}" if data.get("week_52_low") else "N/A"),
                ("Analyst", data.get("recommendation", "N/A")),
            ]
        else:
            metrics = [
                ("Market Rank", f"#{data.get('market_cap_rank', 'N/A')}"),
                ("7D Change", f"{data.get('change_7d', 0):+.2f}%"),
                ("30D Change", f"{data.get('change_30d', 0):+.2f}%"),
                ("ATH", f"${data.get('ath'):,.6f}" if data.get("ath") else "N/A"),
                ("ATH Δ", f"{data.get('ath_change_pct', 0):+.1f}%"),
                ("24H Vol", format_number(data.get("volume_24h", 0))),
                ("Supply", f"{data.get('circulating_supply', 0):,.0f}" if data.get("circulating_supply") else "N/A"),
            ]
        for label, val in metrics:
            ca, cb = st.columns([1, 1])
            ca.markdown(f"<span style='color:#8b949e;font-size:0.82rem;'>{label}</span>", unsafe_allow_html=True)
            cb.markdown(f"<span style='color:#c9d1d9;font-size:0.82rem;font-weight:600;'>{val}</span>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📄 Full Analysis Report")
    st.markdown(report)
    st.download_button(
        label="📥 Download Report (.md)",
        data=report,
        file_name=f"FinSage_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
# ── Page Router ───────────────────────────────────────────────────────────────
def _back_btn(key):
    if st.button("← Back to Dashboard", key=key):
        st.session_state.active_page = "main"
        st.rerun()

_ap = st.session_state.get("active_page", "main")
if _ap == "🤖 AI Assistant":
    _back_btn("back_ai"); render_ai_assistant(); st.stop()
elif _ap == "📸 Chart Analyzer":
    _back_btn("back_ca"); render_chart_analyzer(); st.stop()
elif _ap == "⭐ Feedback & Community":
    _back_btn("back_fb"); render_feedback_dashboard(); st.stop()
elif _ap == "🧠 Advanced Intelligence":
    _back_btn("back_adv"); render_advanced_features(); st.stop()

tab1, tab2, tab3 = st.tabs(["🌍  Global Stocks", "₿  Cryptocurrency", "🎭  Meme Coins"])

# ─── TAB 1: STOCKS ────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 🌍 Global Stock Analysis")
    st.markdown("Real-time data from NSE India, US, UK, Germany, Japan & more.")

    s1, s2 = st.columns([2, 1])
    with s1:
        stock_ticker = st.text_input("Enter Stock Ticker Symbol",
            placeholder="e.g. AAPL, RELIANCE.NS, TCS.NS, TSLA", key="stock_input")
    with s2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🇮🇳 NSE: RELIANCE.NS · TCS.NS · INFY.NS")
        st.caption("🇺🇸 US: AAPL · TSLA · NVDA · MSFT")
        st.caption("🌐 Others: .L (London) · .DE (Germany)")

    st.markdown("**⚡ Quick Pick:**")
    sc = st.columns(8)
    for i, s in enumerate(["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "RELIANCE.NS", "TCS.NS", "INFY.NS"]):
        with sc[i]:
            if st.button(s, key=f"sq_{s}"):
                st.session_state.stock_selected = s
                st.rerun()

    sym = (st.session_state.stock_selected or stock_ticker).strip().upper()

    if st.button("🔍 Analyze Stock", key="btn_stock", type="primary", use_container_width=True):
        if sym:
            with st.spinner(f"Fetching data for **{sym}**..."):
                d = fetch_stock_data(sym)
                if "error" not in d:
                    st.session_state.stock_data = d
                    st.session_state.stock_report = analyze_stock(d)
                    st.session_state.stock_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning("⚠️ Please enter or select a stock ticker.")

    st.markdown("---")
    if st.session_state.stock_data:
        render_results(st.session_state.stock_data, st.session_state.stock_report)
    else:
        st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">🌍</div><p>Enter a ticker symbol above and click <b>Analyze Stock</b>.</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Data from Yahoo Finance (yfinance). For educational purposes only. Not SEBI-registered investment advice.</div>', unsafe_allow_html=True)


# ─── TAB 2: CRYPTO ────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### ₿ Cryptocurrency Analysis")
    st.markdown("Real-time data from CoinGecko — 100+ coins supported.")

    c1, c2 = st.columns([2, 1])
    with c1:
        crypto_ticker = st.text_input("Enter Crypto Symbol",
            placeholder="e.g. BTC, ETH, SOL, BNB, ADA, XRP", key="crypto_input")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Large Cap: BTC · ETH · BNB · SOL")
        st.caption("Mid Cap: ADA · AVAX · DOT · MATIC")

    st.markdown("**⚡ Quick Pick:**")
    cc = st.columns(8)
    for i, c in enumerate(["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT"]):
        with cc[i]:
            if st.button(c, key=f"cq_{c}"):
                st.session_state.crypto_selected = c
                st.rerun()

    csym = (st.session_state.crypto_selected or crypto_ticker).strip().upper()

    if st.button("🔍 Analyze Crypto", key="btn_crypto", type="primary", use_container_width=True):
        if csym:
            with st.spinner(f"Fetching data for **{csym}**..."):
                d = fetch_crypto_data(csym)
                if "error" not in d:
                    st.session_state.crypto_data = d
                    st.session_state.crypto_report = analyze_crypto(d)
                    st.session_state.crypto_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning("⚠️ Please enter or select a crypto symbol.")

    st.markdown("---")
    if st.session_state.crypto_data:
        render_results(st.session_state.crypto_data, st.session_state.crypto_report)
    else:
        st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">₿</div><p>Enter a crypto symbol and click <b>Analyze Crypto</b>.</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Data from CoinGecko. Crypto is highly volatile & unregulated by SEBI. Educational purposes only.</div>', unsafe_allow_html=True)


# ─── TAB 3: MEME COINS ────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 🎭 Meme Coin Analysis")
    st.markdown('<div class="meme-warning">⚠️ <b>HIGH RISK:</b> Meme coins are purely speculative. Prices can crash 80-90% overnight. Only use money you can afford to lose completely.</div>', unsafe_allow_html=True)

    m1, m2 = st.columns([2, 1])
    with m1:
        meme_ticker = st.text_input("Enter Meme Coin Symbol",
            placeholder="e.g. DOGE, SHIB, PEPE, FLOKI, BONK", key="meme_input")
    with m2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Popular: DOGE · SHIB · PEPE · FLOKI")
        st.caption("Trending: BONK · WIF · MEME · TURBO")

    st.markdown("**⚡ Quick Pick:**")
    mc = st.columns(8)
    for i, m in enumerate(["DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME", "TURBO"]):
        with mc[i]:
            if st.button(m, key=f"mq_{m}"):
                st.session_state.meme_selected = m
                st.rerun()

    msym = (st.session_state.meme_selected or meme_ticker).strip().upper()

    if st.button("🔍 Analyze Meme Coin", key="btn_meme", type="primary", use_container_width=True):
        if msym:
            with st.spinner(f"Fetching data for **{msym}**..."):
                d = fetch_crypto_data(msym)
                if "error" not in d:
                    d["asset_type"] = "Meme Coin"
                    st.session_state.meme_data = d
                    st.session_state.meme_report = analyze_crypto(d)
                    st.session_state.meme_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning("⚠️ Please enter or select a meme coin symbol.")

    st.markdown("---")
    if st.session_state.meme_data:
        render_results(st.session_state.meme_data, st.session_state.meme_report)
    else:
        st.markdown('<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">🎭</div><p>Enter a meme coin symbol and click <b>Analyze Meme Coin</b>.</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="disclaimer">⚖️ <b>Disclaimer:</b> Meme coins are unregulated & highly speculative. Not SEBI advice. Never invest borrowed money in meme coins.</div>', unsafe_allow_html=True)



# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("<hr style='border-color:#30363d;margin-top:1.5rem;'>", unsafe_allow_html=True)
f1, f2 = st.columns(2)
with f1:
    st.markdown("<span style='color:#8b949e;font-size:0.75rem;'>📊 <b>FinSage</b> — Global Financial Intelligence Platform</span>", unsafe_allow_html=True)
with f2:
    st.markdown("<span style='color:#6e7681;font-size:0.75rem;display:block;text-align:right;'>Data: Yahoo Finance · CoinGecko &nbsp;|&nbsp; For educational purposes only</span>", unsafe_allow_html=True)
