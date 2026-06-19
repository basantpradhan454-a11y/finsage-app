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
from tradingview_page import render_tradingview_page
from ai_chat_assistant import render_ai_chat_assistant
from privacy_policy import render_privacy_policy, render_signup_page, render_signup_with_privacy
from config import APP_NAME, APP_TAGLINE, LOGO_URL as CFG_LOGO
from risk_engine import render_risk_dashboard
from finsage_academy import render_finsage_academy
from advanced_analyzer import render_advanced_analyzer
from screener import render_screener
from backtester import render_backtester
from options_calc import render_options_calc
from portfolio_tracker import render_portfolio_tracker
from trading_learning import show_trading_learning

# ── Onboarding helpers ────────────────────────────────────────────────────────
ONBOARD_LANGUAGES = {
    "English": "en", "हिंदी": "hi", "తెలుగు": "te", "தமிழ்": "ta",
    "বাংলা": "bn", "मराठी": "mr", "ਪੰਜਾਬੀ": "pa", "ગુજરાતી": "gu",
    "Español": "es", "Français": "fr",
}
USER_TYPES = {
    "📈 Trader":     "trader",
    "💼 Investor":   "investor",
    "🎓 Student":    "student",
    "🤔 Other":      "other",
}
LANG_UI = {
    "en": {"title": "Welcome to FinsageAI", "sub": "Choose your language",
           "step2": "What best describes you?", "continue": "Continue →",
           "signup": "Create Account", "skip": "Skip for now",
           "market": "Market language", "user_type": "I am a..."},
    "hi": {"title": "FinsageAI में आपका स्वागत है", "sub": "अपनी भाषा चुनें",
           "step2": "आप कौन हैं?", "continue": "आगे बढ़ें →",
           "signup": "खाता बनाएं", "skip": "अभी छोड़ें",
           "market": "बाज़ार भाषा", "user_type": "मैं हूँ..."},
    "te": {"title": "FinsageAI కి స్వాగతం", "sub": "భాష ఎంచుకోండి",
           "step2": "మీరు ఎవరు?", "continue": "కొనసాగించు →",
           "signup": "ఖాతా తయారుచేయండి", "skip": "ఇప్పుడు దాటవేయి",
           "market": "మార్కెట్ భాష", "user_type": "నేను..."},
    "ta": {"title": "FinsageAI க்கு வரவேற்கிறோம்", "sub": "மொழி தேர்ந்தெடுங்கள்",
           "step2": "நீங்கள் யார்?", "continue": "தொடர் →",
           "signup": "கணக்கு உருவாக்கு", "skip": "இப்போது தவிர்",
           "market": "சந்தை மொழி", "user_type": "நான்..."},
}
def _ui(key: str) -> str:
    lang = st.session_state.get("user_lang", "en")
    d = LANG_UI.get(lang, LANG_UI["en"])
    return d.get(key, LANG_UI["en"].get(key, key))

def _save_onboard_to_db(email: str):
    """Persist language + user_type to users.json after onboarding."""
    try:
        from auth_page import load_users, save_users
        users = load_users()
        if email in users:
            users[email]["user_type"] = st.session_state.get("user_type", "")
            users[email]["language"]  = st.session_state.get("user_lang", "en")
            save_users(users)
    except Exception:
        pass

def render_onboarding():
    """Full-screen onboarding wizard: language → user type → signup."""
    ob_step = st.session_state.get("onboard_step", "language")

    # ── Shared header ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:2rem 1rem 1rem;">
        <div style="font-size:2.2rem;font-weight:900;color:#00d4ff;
        font-family:Orbitron,monospace;letter-spacing:0.06em;">FinsageAI</div>
        <div style="color:#4a9eff;font-size:0.8rem;letter-spacing:0.15em;margin-top:4px;">
        STOCK · CRYPTO · FOREX · AI-POWERED</div>
    </div>""", unsafe_allow_html=True)

    if ob_step == "language":
        st.markdown(f"""<div style="text-align:center;margin-bottom:1.5rem;">
        <div style="font-size:1.4rem;font-weight:700;color:#e0e6f0;">🌐 Choose Your Language</div>
        <div style="color:#8899aa;font-size:0.85rem;margin-top:6px;">
        You can change this anytime</div></div>""", unsafe_allow_html=True)

        cols = st.columns(5)
        for i, (name, code) in enumerate(ONBOARD_LANGUAGES.items()):
            with cols[i % 5]:
                if st.button(name, key=f"ob_lang_{code}", use_container_width=True):
                    st.session_state.user_lang = code
                    st.session_state.onboard_step = "user_type"
                    st.rerun()

    elif ob_step == "user_type":
        lang = st.session_state.get("user_lang", "en")
        ui = LANG_UI.get(lang, LANG_UI["en"])
        st.markdown(f"""<div style="text-align:center;margin-bottom:1.5rem;">
        <div style="font-size:1.4rem;font-weight:700;color:#e0e6f0;">{ui['step2']}</div>
        <div style="color:#8899aa;font-size:0.85rem;margin-top:6px;">
        This helps us personalise your experience</div></div>""", unsafe_allow_html=True)

        cols = st.columns(4)
        for i, (label, val) in enumerate(USER_TYPES.items()):
            with cols[i]:
                if st.button(label, key=f"ob_type_{val}", use_container_width=True):
                    st.session_state.user_type = val
                    st.session_state.onboard_step = "signup"
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        _, cb, _ = st.columns([2,1,2])
        with cb:
            if st.button("← Back", key="ob_back_lang"):
                st.session_state.onboard_step = "language"; st.rerun()

    elif ob_step == "signup":
        lang = st.session_state.get("user_lang", "en")
        ui   = LANG_UI.get(lang, LANG_UI["en"])
        utype = st.session_state.get("user_type", "")

        st.markdown(f"""<div style="text-align:center;margin-bottom:1rem;">
        <div style="font-size:1.3rem;font-weight:700;color:#e0e6f0;">
        {ui.get('signup','Create Account')} / Login</div>
        <div style="color:#8899aa;font-size:0.83rem;margin-top:5px;">
        Save your progress, history & preferences</div></div>""", unsafe_allow_html=True)

        from auth_page import render_sidebar_auth as _rsa
        _rsa()

        st.markdown("<br>", unsafe_allow_html=True)
        _, cs, _ = st.columns([1,2,1])
        with cs:
            if st.button(f"⚡ {ui.get('skip','Skip for now')} — Enter as Guest",
                         key="ob_skip", use_container_width=True):
                st.session_state.onboard_done = True
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        _, cb2, _ = st.columns([2,1,2])
        with cb2:
            if st.button("← Back", key="ob_back_type"):
                st.session_state.onboard_step = "user_type"; st.rerun()


# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinsageAI — Stock, Crypto & Meme Coin Analysis",
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

# ── Onboarding defaults ──────────────────────────────────────────────────────
_ob_defaults = {
    "onboard_done":  False,
    "onboard_step":  "language",
    "user_lang":     "en",
    "user_type":     "",
}
for _k, _v in _ob_defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Check if logged-in user already has onboarding data ──────────────────────
render_sidebar_auth()
user = get_current_user()
if user and not st.session_state.get("onboard_done"):
    # User already has an account → mark onboarding done
    try:
        from auth_page import load_users
        _udb = load_users()
        _ue  = (user.get("email","")).lower().strip()
        if _ue in _udb:
            _ud = _udb[_ue]
            if _ud.get("user_type"):
                st.session_state.user_type = _ud["user_type"]
            if _ud.get("language"):
                st.session_state.user_lang = _ud["language"]
    except Exception:
        pass
    st.session_state.onboard_done = True

# ── Onboarding gate — show wizard until done ──────────────────────────────────
if not st.session_state.get("onboard_done"):
    render_onboarding()
    # After signup completes (user is now logged in) → mark done + save
    _new_user = get_current_user()
    if _new_user:
        st.session_state.onboard_done = True
        _save_onboard_to_db((_new_user.get("email","")).lower().strip())
        st.rerun()
    st.stop()

# Ticker refresh handled by @st.fragment(run_every=60) — no manual refresh needed

# ── Auto-rerun guard — safe 60s refresh (only on main page) ─────────────────
# Only refresh ticker on main page, never inside sub-pages
_is_main_page = st.session_state.get("active_page", "main") == "main"
if _is_main_page:
    if "last_auto_rerun" not in st.session_state:
        st.session_state.last_auto_rerun = time.time()
    _since_rerun = time.time() - st.session_state.last_auto_rerun
    if _since_rerun > 62:  # 62s buffer to avoid rapid loop
        st.session_state.last_auto_rerun = time.time()
        st.rerun()

# ── Navbar ─────────────────────────────────────────────────────────────────────
nb_left, nb_right = st.columns([6, 1])
with nb_left:
    st.markdown("""
    <div class="stox-navbar" style="display:flex;align-items:center;gap:1rem;">
        <div style="position:relative;">
            <img src="https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/7386585d4_finsage_logo.jpg"
                 style="height:48px;width:48px;border-radius:12px;object-fit:cover;
                 box-shadow:0 0 20px rgba(0,212,255,0.4),0 0 40px rgba(0,212,255,0.1);
                 border:1px solid rgba(0,212,255,0.3);">
            <div style="position:absolute;top:-2px;right:-2px;width:10px;height:10px;
            background:#00ff88;border-radius:50%;border:2px solid #020609;
            box-shadow:0 0 6px rgba(0,255,136,0.8);animation:livePulse 1.2s infinite;"></div>
        </div>
        <div>
            <div class="stox-brand">FinsageAI</div>
            <div class="stox-tagline">STOCK &middot; CRYPTO &middot; MEME COIN ANALYSIS</div>
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
    with st.popover("⋮  ▾", use_container_width=True):
        st.markdown("""
        <div style="font-size:0.82rem;font-weight:700;color:#00d4ff;margin-bottom:0.6rem;
        letter-spacing:0.08em;font-family:Orbitron,monospace;
        text-shadow:0 0 8px rgba(0,212,255,0.5);border-bottom:1px solid rgba(0,212,255,0.15);
        padding-bottom:0.4rem;">
        ⚡ MENU
        </div>""", unsafe_allow_html=True)

        all_pages = [
            ("🤖 AI Assistant",       "🤖 AI Assistant",       "Ask any trading question"),
            ("🔬 Pro Analyser",       "🔬 Pro Analyser",        "10 deep analysis modules"),
            ("📈 TradingView Charts", "📈 TradingView",         "Live candlestick charts"),
            ("📸 Chart Analyzer",     "📸 Chart Analyzer",      "Upload & analyze screenshots"),
            ("⭐ Community",          "⭐ Community",            "Rate & share real trades"),
            ("🧠 Advanced Intel",     "🧠 Advanced Intel",      "Sentiment, Whale, On-chain"),
            ("🛡️ Risk Engine",         "🛡️ Risk Engine",         "CRO-level capital protection"),
            ("📡 Adv. Analyzer",      "📡 Adv. Analyzer",       "10 indicators + Groq AI signals"),
            ("🎓 Academy",             "🎓 Academy",             "AI Trading School — Learn, Quiz, Earn Badges"),
            ("📚 Learn Trading",      "📚 Learn Trading",       "AI-powered beginner→advanced trading course"),
            ("🔍 Screener",            "🔍 Screener",             "Filter NSE + US + Crypto by signals"),
            ("📊 Backtester",          "📊 Backtester",           "Test RSI/MACD/EMA on real history"),
            ("⚙️ Options Greeks",       "⚙️ Options Greeks",       "Delta Gamma Theta Vega + IV Rank"),
            ("💼 Portfolio",           "💼 Portfolio",            "Live P&L + Price Alerts"),

        ]
        for label, page_key, desc in all_pages:
            st.caption(desc)
            if st.button(label, key=f"nav_{page_key}", use_container_width=True):
                st.session_state.active_page = page_key
                st.rerun()

        if user:
            st.markdown("---")
            if st.button("🚪 Logout", key="logout_dot_menu", use_container_width=True):
                logout()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:0.3rem 0 0.7rem;'>", unsafe_allow_html=True)

# ── Live Ticker Bar — @st.fragment (isolated 60s refresh) ──────────────────────

_MEME_SYMS = {'DOGE','SHIB','PEPE','FLOKI','BONK','WIF'}

def _tk_item(item):
    chg = item.get('change',0) or 0
    p   = item.get('price',0) or 0
    cls = 'up' if chg>=0 else 'down'
    arr = '▲' if chg>=0 else '▼'
    if p<0.0001:   ps=f'${p:.8f}'.rstrip('0')
    elif p<0.01:   ps=f'${p:.6f}'
    elif p<1:      ps=f'${p:.4f}'
    else:          ps=f'${p:,.2f}'
    t  = item.get('type','crypto')
    bc = 'badge-meme' if item['symbol'] in _MEME_SYMS else ('badge-stock' if t=='stock' else 'badge-crypto')
    bl = 'MEME' if bc=='badge-meme' else ('STK' if t=='stock' else 'DeFi')
    return (f'<span class="ticker-item">'
            f'<span class="ticker-sym">{item["symbol"]}</span>'
            f'<span class="ticker-price">{ps}</span>'
            f'<span class="{cls}">{arr}{abs(chg):.2f}%</span>'
            f'<span class="ticker-type-badge {bc}">{bl}</span>'
            '</span>')

def _tk_sep(label, color):
    return (f'<span class="ticker-sep" style="color:{color};font-size:0.65rem;'
            f'font-weight:800;letter-spacing:0.1em;font-family:Orbitron,monospace;">{label}</span>')

@st.fragment(run_every=60)
def render_live_ticker():
    ticker_data = fetch_ticker_bar_data()
    if not ticker_data:
        st.caption('⏳ Loading live prices...')
        return
    crypto_items = [x for x in ticker_data if x.get('type')=='crypto' and x['symbol'] not in _MEME_SYMS]
    meme_items   = [x for x in ticker_data if x['symbol'] in _MEME_SYMS]
    stock_items  = [x for x in ticker_data if x.get('type')=='stock']
    html  = '<div class="ticker-bar">'
    html += '<span class="ticker-live">◉ LIVE</span>'
    html += _tk_sep('  CRYPTO','#00d4ff')
    for it in crypto_items: html += _tk_item(it)
    html += _tk_sep('  STOCKS','#4a9eff')
    for it in stock_items:  html += _tk_item(it)
    html += _tk_sep('  MEME','#ff8800')
    for it in meme_items:   html += _tk_item(it)
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
    with st.expander('📊 Click any asset to open live candlestick chart', expanded=False):
        all_items = (crypto_items[:6]+stock_items[:6]+meme_items[:4])[:10]
        if all_items:
            bc2 = st.columns(len(all_items))
            for idx, item in enumerate(all_items):
                sym   = item['symbol']
                chg   = item.get('change',0) or 0
                price = item.get('price',0) or 0
                ps2   = (f'${price:.4f}' if price<1 else f'${price:,.2f}')
                col2  = '#00ff88' if chg>=0 else '#ff4466'
                arr2  = '▲' if chg>=0 else '▼'
                with bc2[idx]:
                    st.markdown(
                        f'<div style="text-align:center;font-size:0.68rem;color:{col2};'
                        f'font-weight:700;">{arr2}{abs(chg):.1f}%</div>'
                        f'<div style="text-align:center;font-size:0.65rem;color:#8b949e;">{ps2}</div>',
                        unsafe_allow_html=True)
                    if st.button(sym, key=f'tc_btn_{sym}', use_container_width=True):
                        st.session_state.ticker_chart_symbol = sym
                        st.session_state.ticker_chart_type   = item.get('type','crypto')
                        st.session_state.active_page         = '📊 Ticker Chart'
                        st.rerun()

render_live_ticker()

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
# ── Ticker Candlestick Chart (full page) ─────────────────────────────────────
def _render_ticker_chart():
    sym    = st.session_state.get("ticker_chart_symbol", "BTC")
    stype  = st.session_state.get("ticker_chart_type", "crypto")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.95),rgba(0,15,30,0.9));
    border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:1rem 1.5rem;
    margin-bottom:1rem;">
        <div style="font-size:1.1rem;font-weight:800;color:#00d4ff;
        font-family:Orbitron,monospace;">📊 {sym} — Live Chart</div>
        <div style="color:#4a9eff;font-size:0.75rem;">Real-time candlestick • TradingView powered</div>
    </div>
    """, unsafe_allow_html=True)

    import streamlit.components.v1 as components

    # Map symbol to TradingView format
    tv_sym_map = {
        "BTC":"BINANCE:BTCUSDT","ETH":"BINANCE:ETHUSDT","SOL":"BINANCE:SOLUSDT",
        "BNB":"BINANCE:BNBUSDT","XRP":"BINANCE:XRPUSDT","DOGE":"BINANCE:DOGEUSDT",
        "SHIB":"BINANCE:SHIBUSDT","PEPE":"BINANCE:PEPEUSDT","FLOKI":"BINANCE:FLOKIUSDT",
        "BONK":"BINANCE:BONKUSDT","AVAX":"BINANCE:AVAXUSDT","ADA":"BINANCE:ADAUSDT",
        "DOT":"BINANCE:DOTUSDT","LINK":"BINANCE:LINKUSDT","UNI":"BINANCE:UNIUSDT",
        "MATIC":"BINANCE:MATICUSDT","TON":"BINANCE:TONUSDT","NEAR":"BINANCE:NEARUSDT",
        "APT":"BINANCE:APTUSDT",
        "AAPL":"NASDAQ:AAPL","TSLA":"NASDAQ:TSLA","NVDA":"NASDAQ:NVDA",
        "MSFT":"NASDAQ:MSFT","GOOGL":"NASDAQ:GOOGL","AMZN":"NASDAQ:AMZN",
        "META":"NASDAQ:META","AMD":"NASDAQ:AMD",
        "RELIANCE":"NSE:RELIANCE","TCS":"NSE:TCS","INFY":"NSE:INFY",
        "HDFCBANK":"NSE:HDFCBANK","WIPRO":"NSE:WIPRO",
        "BAJFINANCE":"NSE:BAJFINANCE","ICICIBANK":"NSE:ICICIBANK",
        "NIFTY50":"NSE:NIFTY",
    }
    tv_sym = tv_sym_map.get(sym, f"BINANCE:{sym}USDT" if stype=="crypto" else f"NASDAQ:{sym}")

    # Interval selector
    iv_col1, iv_col2, iv_col3 = st.columns([3,2,2])
    with iv_col1:
        interval = st.selectbox("Timeframe",
            ["1 Min","5 Min","15 Min","30 Min","1 Hour","4 Hour","1 Day","1 Week"],
            index=6, key="tc_interval")
    with iv_col2:
        chart_style = st.selectbox("Type",
            ["Candlestick","Line","Area","Heikin Ashi"], key="tc_style")
    with iv_col3:
        show_vol = st.checkbox("Volume", value=True, key="tc_vol")

    iv_map = {"1 Min":"1","5 Min":"5","15 Min":"15","30 Min":"30",
              "1 Hour":"60","4 Hour":"240","1 Day":"D","1 Week":"W"}
    cs_map = {"Candlestick":"1","Line":"2","Area":"3","Heikin Ashi":"8"}

    studies = '["Volume@tv-basicstudies","RSI@tv-basicstudies"]' if show_vol else '["RSI@tv-basicstudies"]'

    tv_html = f"""
    <div style="border-radius:12px;overflow:hidden;border:1px solid rgba(0,212,255,0.15);
    box-shadow:0 0 30px rgba(0,212,255,0.06);">
    <div class="tradingview-widget-container">
      <div id="tv_chart_{sym}"></div>
      <script src="https://s3.tradingview.com/tv.js"></script>
      <script>
      new TradingView.widget({{
        "autosize":true,"height":520,
        "symbol":"{tv_sym}",
        "interval":"{iv_map.get(interval,"D")}",
        "timezone":"Asia/Kolkata",
        "theme":"dark","style":"{cs_map.get(chart_style,"1")}",
        "locale":"en","toolbar_bg":"#020609",
        "backgroundColor":"rgba(2,6,9,1)",
        "gridColor":"rgba(0,212,255,0.04)",
        "enable_publishing":false,"save_image":true,
        "container_id":"tv_chart_{sym}",
        "studies":{studies}
      }});
      </script>
    </div></div>
    """
    components.html(tv_html, height=540, scrolling=False)

    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.5rem 1rem;margin-top:0.5rem;font-size:0.74rem;color:#8b949e;">
    ⚖️ Charts powered by TradingView. For educational purposes only. Not investment advice.
    </div>
    """, unsafe_allow_html=True)


def _back_btn(key):
    col_b, col_t = st.columns([1, 6])
    with col_b:
        if st.button("◀ Dashboard", key=key, use_container_width=True):
            st.session_state.active_page = "main"
            st.rerun()

_ap = st.session_state.get("active_page", "main")
if _ap == "🤖 AI Assistant":
    _back_btn("back_ai"); render_ai_chat_assistant(); st.stop()
elif _ap == "🔬 Pro Analyser":
    _back_btn("back_pro"); render_ai_assistant(); st.stop()
elif _ap == "📈 TradingView":
    _back_btn("back_tv"); render_tradingview_page(); st.stop()
elif _ap == "📸 Chart Analyzer":
    _back_btn("back_ca"); render_chart_analyzer(); st.stop()
elif _ap == "⭐ Community":
    _back_btn("back_fb"); render_feedback_dashboard(); st.stop()
elif _ap == "🧠 Advanced Intel":
    _back_btn("back_adv"); render_advanced_features(); st.stop()
elif _ap == "🔒 Privacy Policy":
    _back_btn("back_pp"); render_privacy_policy(); st.stop()
elif _ap == "📝 Sign Up":
    _back_btn("back_su"); render_signup_with_privacy(); st.stop()
elif _ap == "📚 Learn Trading":
    _back_btn("back_lt"); show_trading_learning(); st.stop()
elif _ap == "🛡️ Risk Engine":
    _back_btn("back_re"); render_risk_dashboard(); st.stop()

elif _ap == "📡 Adv. Analyzer":
    _back_btn("back_aa"); render_advanced_analyzer(); st.stop()
elif _ap == "🎓 Academy":
    _back_btn("back_pb"); render_finsage_academy(); st.stop()
elif _ap == "🔍 Screener":
    _back_btn("back_sc"); render_screener(); st.stop()
elif _ap == "📊 Backtester":
    _back_btn("back_bt"); render_backtester(); st.stop()
elif _ap == "⚙️ Options Greeks":
    _back_btn("back_oc"); render_options_calc(); st.stop()
elif _ap == "💼 Portfolio":
    _back_btn("back_pf"); render_portfolio_tracker(); st.stop()
elif _ap == "📊 Ticker Chart":
    _back_btn("back_tc")
    _render_ticker_chart()
    st.stop()

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
