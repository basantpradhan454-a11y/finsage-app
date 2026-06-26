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
from sage_analyst import render_sage_analyst
from footprint_chart import render_footprint_chart
from cognitive_assistant import render_cognitive_assistant
from tradingview_dashboard import render_tv_dashboard
from institutional_report import render_institutional_report
from market_dashboard import render_market_dashboard
try:
    from pro_chart import render_pro_chart
except Exception:
    render_pro_chart=None
try:
    from user_dashboard import render_user_dashboard
except Exception:
    render_user_dashboard=None
from tradingview_page import render_tradingview_page
from strategy_bot import render_strategy_bot
from i18n import t, get_lang, set_lang, TRANSLATIONS, LANG_NAMES
from ticker_resolver import resolve_ticker
from ai_chat_assistant import render_ai_chat_assistant
from privacy_policy import render_privacy_policy, render_signup_page, render_signup_with_privacy
from config import APP_NAME, APP_TAGLINE, LOGO_URL as CFG_LOGO
from risk_engine import render_risk_dashboard
from advanced_analyzer import render_advanced_analyzer
from screener import render_screener
from backtester import render_backtester
from options_calc import render_options_calc
from library import show_library_page

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
   BASE — MIDNIGHT PROFESSIONAL DARK
   Primary: #050d1f (Midnight Navy)
   Accent:  #00d4ff (Electric Teal/Cyan)
   Success: #00c896 (Mint Green — Profit)
   Alert:   #e05c6e (Muted Red — Loss/Sell)
   Gold:    #ffd700 (Premium Accent)
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

# ── Session State ────────────────────────────────────────────────────────────
if "active_page" not in st.session_state:
    st.session_state.active_page = "🏠 Market Dashboard"

# ══════════════════════════════════════════════════════════════
# SESSION PERSISTENCE — Cookie-based auto-login
# ══════════════════════════════════════════════════════════════
def _set_login_cookie(token: str):
    """Inject JS to set a 30-day cookie with the session token."""
    import streamlit.components.v1 as _comp
    _comp.html(f"""
    <script>
    (function() {{
        var d = new Date();
        d.setTime(d.getTime() + (30*24*60*60*1000));
        document.cookie = "fs_token={token}; expires=" + d.toUTCString() + "; path=/; SameSite=Strict";
        // Also save to localStorage as fallback
        try {{ localStorage.setItem('fs_token', '{token}'); }} catch(e) {{}}
    }})();
    </script>
    """, height=0)

def _get_cookie_token() -> str:
    """Read fs_token from query params (injected by JS below)."""
    return st.query_params.get("fs_token", "")

def _clear_login_cookie():
    """Clear cookie on logout."""
    import streamlit.components.v1 as _comp
    _comp.html("""
    <script>
    document.cookie = "fs_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    try { localStorage.removeItem('fs_token'); } catch(e) {}
    </script>
    """, height=0)

def _inject_cookie_reader():
    """JS that reads cookie/localStorage and appends fs_token to URL so Streamlit can read it."""
    import streamlit.components.v1 as _comp
    _comp.html("""
    <script>
    (function() {
        var token = '';
        // Try localStorage first
        try { token = localStorage.getItem('fs_token') || ''; } catch(e) {}
        // Try cookie fallback
        if (!token) {
            var match = document.cookie.match(/(?:^|; )fs_token=([^;]*)/);
            if (match) token = decodeURIComponent(match[1]);
        }
        if (token) {
            var url = new URL(window.location.href);
            if (url.searchParams.get('fs_token') !== token) {
                url.searchParams.set('fs_token', token);
                window.history.replaceState({}, '', url.toString());
                // Trigger Streamlit re-read
                window.parent.postMessage({type: 'streamlit:setComponentValue', value: token}, '*');
            }
        }
    })();
    </script>
    """, height=0)

_all_defaults = {
    "user":              None,
    "stock_data":        None,  "stock_report":  None,
    "crypto_data":       None,  "crypto_report": None,
    "meme_data":         None,  "meme_report":   None,
    "ticker_data":       [],    "last_ticker_refresh": 0,
    "stock_selected":    "",    "crypto_selected":     "",    "meme_selected": "",
    # onboarding
    "ob_step":           "language",   # language | user_type | signup
    "user_lang":         "en",
    "user_type":         "",
    "ob_done":           False,
}
for _k, _v in _all_defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Auto-login via session token (cookie/localStorage) ────────────────────
if not st.session_state.get("user"):
    _inject_cookie_reader()   # inject JS to read cookie → query param
    _fs_tok = st.query_params.get("fs_token", "")
    if _fs_tok:
        try:
            from auth_page import resolve_session_token as _rst
            _restored = _rst(_fs_tok)
            if _restored:
                st.session_state.user   = _restored
                st.session_state.ob_done = True
                # restore language/user_type
                try:
                    from auth_page import _read_user as _ru2
                    _ud2 = _ru2(_restored.get("email",""))
                    if _ud2:
                        if _ud2.get("user_type"): st.session_state.user_type = _ud2["user_type"]
                        if _ud2.get("language"):  st.session_state.user_lang = _ud2["language"]
                except Exception:
                    pass
        except Exception:
            pass

# ── Google OAuth callback (must run before onboarding gate) ─────────────────
_qp = st.query_params
if "code" in _qp and not st.session_state.get("user"):
    with st.spinner("🔄 Signing in with Google..."):
        from auth_page import exchange_code_for_user
        _gu = exchange_code_for_user(_qp["code"])
        st.query_params.clear()
        if "error" not in _gu:
            st.session_state.user = _gu
            st.session_state.ob_done = True
            _g_tok = _gu.get("_session_token", "")
            if _g_tok:
                st.query_params["fs_token"] = _g_tok
            st.rerun()

# ── If fs_token in query params (fresh login) — set the cookie ──────────────
_fresh_tok = st.query_params.get("fs_token", "")
if _fresh_tok and not st.query_params.get("code"):
    _set_login_cookie(_fresh_tok)
    # Remove from visible URL to keep it clean
    st.session_state["_active_token"] = _fresh_tok

# ── If already logged in → skip onboarding, restore lang/type from DB ────────
render_sidebar_auth()
user = get_current_user()
if user and not st.session_state.get("ob_done"):
    try:
        from auth_page import load_users as _lu
        _udb = _lu()
        _ue  = (user.get("email","")).lower().strip()
        if _ue in _udb:
            _ud = _udb[_ue]
            if _ud.get("user_type"):  st.session_state.user_type = _ud["user_type"]
            if _ud.get("language"):   st.session_state.user_lang = _ud["language"]
    except Exception:
        pass
    st.session_state.ob_done = True

# ════════════════════════════════════════════════════════════════════
# ONBOARDING GATE — nothing renders until wizard is complete
# ════════════════════════════════════════════════════════════════════
def _save_ob_to_db(email: str):
    try:
        from auth_page import load_users, save_users
        _u = load_users()
        if email in _u:
            _u[email]["user_type"] = st.session_state.get("user_type","")
            _u[email]["language"]  = st.session_state.get("user_lang","en")
            save_users(_u)
    except Exception:
        pass

# ── Onboarding CSS ────────────────────────────────────────────────
_OB_CSS = """
<style>
.ob-wrap{max-width:520px;margin:0 auto;padding:1rem 0.5rem;}
.ob-logo{text-align:center;padding:2.5rem 0 1.5rem;}
.ob-logo-name{font-size:2rem;font-weight:900;color:#00d4ff;
  font-family:Orbitron,monospace;letter-spacing:0.07em;
  text-shadow:0 0 25px rgba(0,212,255,0.5);}
.ob-logo-tag{color:#4a9eff;font-size:0.72rem;letter-spacing:0.18em;margin-top:4px;}
.ob-step-title{font-size:1.35rem;font-weight:800;color:#e0e6f0;
  text-align:center;margin:1.2rem 0 0.4rem;}
.ob-step-sub{color:#8899aa;font-size:0.83rem;text-align:center;
  margin-bottom:1.4rem;}
.ob-lang-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:1rem;}
.ob-lang-btn{background:rgba(0,212,255,0.07);border:1px solid rgba(0,212,255,0.2);
  border-radius:10px;padding:10px 6px;text-align:center;cursor:pointer;
  font-size:0.82rem;font-weight:600;color:#c9d1d9;transition:all 0.2s;}
.ob-lang-btn:hover{border-color:#00d4ff;background:rgba(0,212,255,0.15);}
.ob-type-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:1rem;}
.ob-type-card{background:linear-gradient(135deg,#071525,#0d2040);
  border:1px solid rgba(0,212,255,0.18);border-radius:14px;
  padding:22px 16px;text-align:center;cursor:pointer;
  font-size:1.1rem;font-weight:700;color:#e0e6f0;transition:all 0.25s;}
.ob-type-card:hover{border-color:#00d4ff;box-shadow:0 0 20px rgba(0,212,255,0.18);}
.ob-card{background:rgba(7,21,37,0.97);border:1px solid rgba(0,212,255,0.15);
  border-radius:16px;padding:28px 24px;margin-top:0.5rem;}
.ob-divider{display:flex;align-items:center;gap:10px;color:#556;
  font-size:0.78rem;margin:1rem 0;}
.ob-divider-line{flex:1;height:1px;background:#1a2744;}
.ob-progress{display:flex;justify-content:center;gap:8px;margin-bottom:1.5rem;}
.ob-dot{width:8px;height:8px;border-radius:50%;background:#1a2744;transition:all 0.3s;}
.ob-dot.active{background:#00d4ff;box-shadow:0 0 8px #00d4ff;}
.ob-dot.done{background:#00ff88;}
</style>
"""

_OB_LANG_MAP = {
    "🇺🇸 English":"en","🇮🇳 हिंदी":"hi","🇮🇳 తెలుగు":"te",
    "🇮🇳 தமிழ்":"ta","🇮🇳 বাংলা":"bn","🇮🇳 मराठी":"mr",
    "🇮🇳 ਪੰਜਾਬੀ":"pa","🇮🇳 ગુજરાતી":"gu","🇪🇸 Español":"es","🇫🇷 Français":"fr",
}
_OB_TITLES = {
    "en":{"lang":"🌐 Choose Language","lang_sub":"Select the language for the entire platform",
          "type":"Who are you?","type_sub":"We'll personalise your experience",
          "signup":"Create your account","signup_sub":"Save progress, history & preferences",
          "skip":"Enter as Guest (no account needed)","back":"← Back"},
    "hi":{"lang":"🌐 भाषा चुनें","lang_sub":"पूरे प्लेटफ़ॉर्म के लिए भाषा चुनें",
          "type":"आप कौन हैं?","type_sub":"हम आपका अनुभव बेहतर बनाएंगे",
          "signup":"अपना खाता बनाएं","signup_sub":"प्रगति व इतिहास सुरक्षित रखें",
          "skip":"अभी Guest के रूप में जारी रखें","back":"← वापस"},
    "te":{"lang":"🌐 భాష ఎంచుకోండి","lang_sub":"మొత్తం ప్లాట్‌ఫారమ్‌కు భాష ఎంచుకోండి",
          "type":"మీరు ఎవరు?","type_sub":"మీ అనుభవాన్ని మెరుగుపరుస్తాము",
          "signup":"ఖాతా సృష్టించండి","signup_sub":"మీ పురోగతి సేవ్ చేయబడుతుంది",
          "skip":"Guest గా కొనసాగండి","back":"← వెనక్కి"},
    "ta":{"lang":"🌐 மொழி தேர்வு","lang_sub":"முழு தளத்திற்கும் மொழி தேர்ந்தெடுக்கவும்",
          "type":"நீங்கள் யார்?","type_sub":"உங்கள் அனுபவத்தை தனிப்பயனாக்குவோம்",
          "signup":"கணக்கு உருவாக்கவும்","signup_sub":"முன்னேற்றத்தை சேமிக்கவும்",
          "skip":"விருந்தினராக தொடரவும்","back":"← பின்"},
}

_OB_USER_TYPES = [
    ("📈 Trader",    "trader"),
    ("💼 Investor",  "investor"),
    ("🎓 Student",   "student"),
    ("🤔 Other",     "other"),
]

def _ob_ui(key):
    """Use i18n translation system for onboarding UI."""
    return t(key)

def _ob_dots(current_step):
    steps = ["language","user_type","signup"]
    idx   = steps.index(current_step) if current_step in steps else 0
    dots  = ""
    for i in range(3):
        cls = "done" if i < idx else ("active" if i == idx else "")
        dots += f'<div class="ob-dot {cls}"></div>'
    st.markdown(f'<div class="ob-progress">{dots}</div>', unsafe_allow_html=True)

def render_onboarding():
    st.markdown(_OB_CSS, unsafe_allow_html=True)

    # Handle Google OAuth inside onboarding
    _qp2 = st.query_params
    if "code" in _qp2 and not st.session_state.get("user"):
        with st.spinner("🔄 Signing in with Google..."):
            from auth_page import exchange_code_for_user
            _gu2 = exchange_code_for_user(_qp2["code"])
            st.query_params.clear()
            if "error" not in _gu2:
                st.session_state.user = _gu2
                _save_ob_to_db((_gu2.get("email","")).lower())
                st.session_state.ob_done = True
                st.rerun()

    step = st.session_state.get("ob_step","language")

    # Logo
    st.markdown("""
    <div class="ob-logo">
        <img src="https://base44.app/api/apps/6a34884cbcecdd779c9d0281/files/mp/public/6a34884cbcecdd779c9d0281/a07ce8a2c_finsage_new_logo.jpg" style="height:52px;border-radius:10px;
        object-fit:contain;filter:drop-shadow(0 0 12px rgba(0,212,255,0.4));
        margin-bottom:8px;">
        <div class="ob-logo-tag">STOCK · CRYPTO · FOREX · AI-POWERED</div>
    </div>""", unsafe_allow_html=True)

    # Progress dots
    _ob_dots(step)

    _, col, _ = st.columns([0.5, 3, 0.5])
    with col:

        if step == "language":
            st.markdown(f'<div class="ob-step-title">{_ob_ui("lang")}</div>'
                        f'<div class="ob-step-sub">{_ob_ui("lang_sub")}</div>',
                        unsafe_allow_html=True)
            # 5-column language grid
            for row_start in range(0, len(_OB_LANG_MAP), 5):
                row_items = list(_OB_LANG_MAP.items())[row_start:row_start+5]
                cols = st.columns(len(row_items))
                for ci, (label, code) in enumerate(row_items):
                    with cols[ci]:
                        if st.button(label, key=f"ob_lang_{code}",
                                     use_container_width=True):
                            st.session_state.user_lang = code
                            st.session_state.ob_step   = "user_type"
                            st.rerun()

        elif step == "user_type":
            st.markdown(f'<div class="ob-step-title">{_ob_ui("type")}</div>'
                        f'<div class="ob-step-sub">{_ob_ui("type_sub")}</div>',
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            for i, (label, val) in enumerate(_OB_USER_TYPES):
                with (c1 if i % 2 == 0 else c2):
                    if st.button(label, key=f"ob_type_{val}",
                                 use_container_width=True):
                        st.session_state.user_type = val
                        st.session_state.ob_step   = "signup"
                        st.rerun()
            st.write("")
            if st.button(_ob_ui("back"), key="ob_back1"):
                st.session_state.ob_step = "language"; st.rerun()

        elif step == "signup":
            st.markdown(f'<div class="ob-step-title">{_ob_ui("signup")}</div>'
                        f'<div class="ob-step-sub">{_ob_ui("signup_sub")}</div>',
                        unsafe_allow_html=True)

            # Use the unified auth card from auth_page (includes Privacy Policy tab)
            from auth_page import _render_auth_card, AUTH_CSS
            st.markdown(AUTH_CSS, unsafe_allow_html=True)
            _render_auth_card(key_prefix="ob")

            st.write("")
            if st.button(_ob_ui("back"), key="ob_back2"):
                st.session_state.ob_step = "user_type"; st.rerun()

if not st.session_state.get("ob_done"):
    render_onboarding()
    st.stop()

# Ticker refresh handled by @st.fragment(run_every=60) — no manual refresh needed

# ── Auto-rerun guard — safe 60s refresh (only on main page) ─────────────────
# Only refresh ticker on main page, never inside sub-pages
_is_main_page = st.session_state.get("active_page","🏠 Market Dashboard") in ("main","🏠 Market Dashboard")
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
    _tagline = t("tagline")
    st.markdown(f"""
    <div class="stox-navbar" style="display:flex;align-items:center;gap:1rem;">
        <div style="position:relative;">
            <img src="https://base44.app/api/apps/6a34884cbcecdd779c9d0281/files/mp/public/6a34884cbcecdd779c9d0281/a07ce8a2c_finsage_new_logo.jpg"
                 style="height:44px;border-radius:10px;object-fit:contain;
                 box-shadow:0 0 20px rgba(0,212,255,0.4),0 0 40px rgba(0,212,255,0.1);
                 border:1px solid rgba(0,212,255,0.3);">
            <div style="position:absolute;top:-2px;right:-2px;width:10px;height:10px;
            background:#00ff88;border-radius:50%;border:2px solid #020609;
            box-shadow:0 0 6px rgba(0,255,136,0.8);animation:livePulse 1.2s infinite;"></div>
        </div>
        <div>
            <!-- logo already contains brand text -->
            <div class="stox-tagline">{_tagline}</div>
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
        _menu_label = t("menu")
        st.markdown(f"""
        <div style="font-size:0.82rem;font-weight:700;color:#00d4ff;margin-bottom:0.6rem;
        letter-spacing:0.08em;font-family:Orbitron,monospace;
        text-shadow:0 0 8px rgba(0,212,255,0.5);border-bottom:1px solid rgba(0,212,255,0.15);
        padding-bottom:0.4rem;">
        {_menu_label}
        </div>""", unsafe_allow_html=True)

        # ── GROUPED NAVIGATION ────────────────────────────────────────────────
        nav_groups = [
            ("🤖 AI Analyser", [
                ("👤 Personal Dashboard","👤 User Dashboard",    "Favourites · AI auto-draws all levels · 6 trader styles"),
                ("🔬 Pro Chart Studio",  "🔬 Pro Chart Studio",  "Glass UI · 200+ indicators · SMC · Elliott Wave · All trader types"),
                ("🧠 SAGE Analyst",      "🧠 SAGE Analyst",      "Multi-timeframe AI chart analysis"),
                ("🔢 Footprint Chart",   "🔢 Footprint Chart",   "Order flow & volume profile"),
                ("🔬 Pro Analyser",      "🔬 Pro Analyser",      "Advanced AI analysis"),
                ("🧠 Advanced Intel",    "🧠 Advanced Intel",    "Market intelligence"),
                ("🧠 Cognitive Asst.",   "🧠 Cognitive Assistant","MTF · Heatmap · Brief"),
            ]),
            ("🛠️ AI Tools", [
                ("🤖 AI Strategy Bot",   "🤖 AI Strategy Bot",   "AI trading strategy"),
                ("🤖 AI Assistant",      "🤖 AI Assistant",      "General AI assistant"),
                ("📸 Chart Analyzer",    "📸 Chart Analyzer",    "Upload & analyze charts"),
                ("📡 Adv. Analyzer",     "📡 Adv. Analyzer",     "Advanced market analyzer"),
                ("🛡️ Risk Engine",       "🛡️ Risk Engine",       "Position & risk calculator"),
                ("🔍 Screener",          "🔍 Screener",          "Stock screener"),
                ("📊 Backtester",        "📊 Backtester",        "Strategy backtester"),
                ("⚙️ Options Greeks",    "⚙️ Options Greeks",    "Options calculator"),
                ("⭐ Community",         "⭐ Community",         "Community & feedback"),
            ]),
            ("📚 Marketplace", [
                ("📖 Marketplace",       "📖 Marketplace",       "eBooks & resources"),
            ]),
        ]
        # Top always-visible navigation
        if st.button("🏠 Market Dashboard", key="nav_home_top", use_container_width=True, type="primary"):
            st.session_state.active_page = "🏠 Market Dashboard"; st.rerun()
        if st.button("📊 Research Report", key="nav_rr_top", use_container_width=True):
            st.session_state.active_page = "📊 Research Report"; st.rerun()
        st.markdown("<hr style='margin:6px 0;border-color:#2a2e39;'>", unsafe_allow_html=True)

        # Collapsible groups
        for group_label, pages in nav_groups:  # all groups as expanders
            with st.expander(group_label, expanded=False):
                for label, page_key, desc in pages:
                    st.caption(desc)
                    if st.button(label, key=f"nav_{page_key}", use_container_width=True):
                        st.session_state.active_page = page_key
                        st.rerun()

        if user:
            st.markdown("---")
            if st.button(f"🚪 {t('logout')}", key="logout_dot_menu", use_container_width=True):
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

    with k1: st.metric(f"💰 {t('price')}", price_str)
    with k2: st.metric(f"📈 {t('change_24h')}", f"{change:+.2f}%")
    with k3: st.metric(f"🏦 {t('mkt_cap')}", format_number(market_cap))
    with k4: st.metric(f"⚡ {t('volatility')}", f"{vol:.1f}%")
    with k5: st.metric(f"🎯 {t('risk')}", f"{risk}/10")

    st.markdown("---")
    col_chart, col_info = st.columns([3, 2])

    with col_chart:
        history = data.get("history")
        if history is not None and isinstance(history, pd.DataFrame) and not history.empty:
            st.markdown(f"#### \U0001f4c8 {t('price_chart')}")
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
        st.markdown(f"#### \U0001f4cb {t('key_metrics')}")
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
    st.markdown(f"#### \U0001f4c4 {t('full_report')}")
    st.markdown(report)
    st.download_button(
        label=f"\U0001f4e5 {t('download_report')}",
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
        interval = st.selectbox(t("timeframe"),
            ["1 Min","5 Min","15 Min","30 Min","1 Hour","4 Hour","1 Day","1 Week"],
            index=6, key="tc_interval")
    with iv_col2:
        chart_style = st.selectbox(t("chart_type"),
            ["Candlestick","Line","Area","Heikin Ashi"], key="tc_style")
    with iv_col3:
        show_vol = st.checkbox(t("volume"), value=True, key="tc_vol")

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
        if st.button(f"◀ {t('back_dashboard')}", key=key, use_container_width=True):
            st.session_state.active_page = "🏠 Market Dashboard"
            st.rerun()

_ap = st.session_state.get("active_page", "main")
if _ap == "👤 User Dashboard":
    if render_user_dashboard: render_user_dashboard()
    else: st.error("User Dashboard loading...")
elif _ap == "🔬 Pro Chart Studio":
    if render_pro_chart: render_pro_chart()
    else: st.error("Pro Chart loading... refresh in 10s")
elif _ap == "🤖 AI Assistant":
    _back_btn("back_ai"); render_ai_chat_assistant(); st.stop()
elif _ap == "🤖 AI Strategy Bot":
    _back_btn("back_strat"); render_strategy_bot(); st.stop()
elif _ap == "🧠 SAGE Analyst":
    _back_btn("back_sage"); render_sage_analyst(); st.stop()
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

elif _ap in ("📖 Library", "📖 Marketplace"):
    _back_btn("back_lib"); show_library_page(); st.stop()
elif _ap == "🛡️ Risk Engine":
    _back_btn("back_re"); render_risk_dashboard(); st.stop()

elif _ap == "📡 Adv. Analyzer":
    _back_btn("back_aa"); render_advanced_analyzer(); st.stop()

elif _ap == "🔍 Screener":
    _back_btn("back_sc"); render_screener(); st.stop()
elif _ap == "📊 Backtester":
    _back_btn("back_bt"); render_backtester(); st.stop()
elif _ap == "🔢 Footprint Chart":
    _back_btn("back_fp"); render_footprint_chart(); st.stop()
elif _ap == "🏠 Market Dashboard":
    render_market_dashboard(); st.stop()
elif _ap == "📊 Research Report":
    _back_btn("back_ir"); render_institutional_report(); st.stop()
elif _ap == "🧠 Cognitive Assistant":
    _back_btn("back_ca2"); render_cognitive_assistant(); st.stop()
elif _ap == "⚙️ Options Greeks":
    _back_btn("back_oc"); render_options_calc(); st.stop()

elif _ap == "📊 Ticker Chart":
    _back_btn("back_tc")
    _render_ticker_chart()
    st.stop()

tab1, tab2, tab3 = st.tabs([f"🌍  {t('tab_stocks')}", f"₿  {t('tab_crypto')}", f"🎭  {t('tab_meme')}"])

# ─── TAB 1: STOCKS ────────────────────────────────────────────────────────────
with tab1:
    st.markdown(f"### 🌍 {t('stock_title')}")
    st.markdown(t("stock_sub"))

    s1, s2 = st.columns([2, 1])
    with s1:
        stock_ticker = st.text_input(t("stock_input"),
            placeholder=t("stock_placeholder"), key="stock_input")
    with s2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🇮🇳 NSE: RELIANCE.NS · TCS.NS · INFY.NS")
        st.caption("🇺🇸 US: AAPL · TSLA · NVDA · MSFT")
        st.caption("🌐 Others: .L (London) · .DE (Germany)")

    st.markdown(f"**⚡ {t('quick_pick')}**")
    sc = st.columns(8)
    for i, s in enumerate(["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "RELIANCE.NS", "TCS.NS", "INFY.NS"]):
        with sc[i]:
            if st.button(s, key=f"sq_{s}"):
                st.session_state.stock_selected = s
                st.rerun()

    sym = (st.session_state.stock_selected or stock_ticker).strip().upper()

    if st.button(f"🔍 {t('analyze_stock')}", key="btn_stock", type="primary", use_container_width=True):
        if sym:
            _resolved_sym = resolve_ticker(sym)
            if _resolved_sym != sym:
                st.info(f"💡 Did you mean **{_resolved_sym}**? Showing results for {_resolved_sym}")
            with st.spinner(f"{t('fetching')} **{_resolved_sym}**..."):
                d = fetch_stock_data(_resolved_sym)
                if "error" not in d:
                    st.session_state.stock_data = d
                    st.session_state.stock_report = analyze_stock(d)
                    st.session_state.stock_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning(f"⚠️ {t('please_enter')}")

    st.markdown("---")
    if st.session_state.stock_data:
        render_results(st.session_state.stock_data, st.session_state.stock_report)
    else:
        _et = t("enter_ticker")
        st.markdown(f'<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">🌍</div><p>{_et}</p></div>', unsafe_allow_html=True)

    _disc = t("disclaimer")
    st.markdown(f'<div class="disclaimer">⚖️ <b>Disclaimer:</b> {_disc}</div>', unsafe_allow_html=True)


# ─── TAB 2: CRYPTO ────────────────────────────────────────────────────────────
with tab2:
    st.markdown(f"### ₿ {t('crypto_title')}")
    st.markdown(t("crypto_sub"))

    c1, c2 = st.columns([2, 1])
    with c1:
        crypto_ticker = st.text_input(t("crypto_input"),
            placeholder=t("crypto_placeholder"), key="crypto_input")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Large Cap: BTC · ETH · BNB · SOL")
        st.caption("Mid Cap: ADA · AVAX · DOT · MATIC")

    st.markdown(f"**⚡ {t('quick_pick')}**")
    cc = st.columns(8)
    for i, c in enumerate(["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT"]):
        with cc[i]:
            if st.button(c, key=f"cq_{c}"):
                st.session_state.crypto_selected = c
                st.rerun()

    csym = (st.session_state.crypto_selected or crypto_ticker).strip().upper()

    if st.button(f"🔍 {t('analyze_crypto')}", key="btn_crypto", type="primary", use_container_width=True):
        if csym:
            _resolved_csym = resolve_ticker(csym)
            if _resolved_csym != csym:
                st.info(f"💡 Did you mean **{_resolved_csym}**? Showing results for {_resolved_csym}")
            with st.spinner(f"{t('fetching')} **{_resolved_csym}**..."):
                d = fetch_crypto_data(_resolved_csym)
                if "error" not in d:
                    st.session_state.crypto_data = d
                    st.session_state.crypto_report = analyze_crypto(d)
                    st.session_state.crypto_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning(f"⚠️ {t('please_enter')}")

    st.markdown("---")
    if st.session_state.crypto_data:
        render_results(st.session_state.crypto_data, st.session_state.crypto_report)
    else:
        _ec = t("enter_crypto")
        st.markdown(f'<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">₿</div><p>{_ec}</p></div>', unsafe_allow_html=True)

    _disc_c = t("disclaimer_crypto")
    st.markdown(f'<div class="disclaimer">⚖️ <b>Disclaimer:</b> {_disc_c}</div>', unsafe_allow_html=True)


# ─── TAB 3: MEME COINS ────────────────────────────────────────────────────────
with tab3:
    st.markdown(f"### 🎭 {t('meme_title')}")
    st.markdown('<div class="meme-warning">⚠️ <b>HIGH RISK:</b> Meme coins are purely speculative. Prices can crash 80-90% overnight. Only use money you can afford to lose completely.</div>', unsafe_allow_html=True)

    m1, m2 = st.columns([2, 1])
    with m1:
        meme_ticker = st.text_input(t("meme_input"),
            placeholder=t("meme_placeholder"), key="meme_input")
    with m2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Popular: DOGE · SHIB · PEPE · FLOKI")
        st.caption("Trending: BONK · WIF · MEME · TURBO")

    st.markdown(f"**⚡ {t('quick_pick')}**")
    mc = st.columns(8)
    for i, m in enumerate(["DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME", "TURBO"]):
        with mc[i]:
            if st.button(m, key=f"mq_{m}"):
                st.session_state.meme_selected = m
                st.rerun()

    msym = (st.session_state.meme_selected or meme_ticker).strip().upper()

    if st.button(f"🔍 {t('analyze_meme')}", key="btn_meme", type="primary", use_container_width=True):
        if msym:
            _resolved_msym = resolve_ticker(msym)
            if _resolved_msym != msym:
                st.info(f"💡 Did you mean **{_resolved_msym}**? Showing results for {_resolved_msym}")
            with st.spinner(f"{t('fetching')} **{_resolved_msym}**..."):
                d = fetch_crypto_data(_resolved_msym)
                if "error" not in d:
                    d["asset_type"] = "Meme Coin"
                    st.session_state.meme_data = d
                    st.session_state.meme_report = analyze_crypto(d)
                    st.session_state.meme_selected = ""
                else:
                    st.error(f"❌ {d['error']}")
        else:
            st.warning(f"⚠️ {t('please_enter')}")

    st.markdown("---")
    if st.session_state.meme_data:
        render_results(st.session_state.meme_data, st.session_state.meme_report)
    else:
        _em = t("enter_meme")
        st.markdown(f'<div style="text-align:center;padding:2rem;color:#8b949e;"><div style="font-size:2.5rem;">🎭</div><p>{_em}</p></div>', unsafe_allow_html=True)

    _disc_m = t("disclaimer_meme")
    st.markdown(f'<div class="disclaimer">⚖️ <b>Disclaimer:</b> {_disc_m}</div>', unsafe_allow_html=True)



# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("<hr style='border-color:#30363d;margin-top:1.5rem;'>", unsafe_allow_html=True)
f1, f2 = st.columns(2)
with f1:
    _fl = t('footer_left')
    st.markdown(f"<span style='color:#8b949e;font-size:0.75rem;'>{_fl}</span>", unsafe_allow_html=True)
with f2:
    _fr = t('footer_right')
    st.markdown(f"<span style='color:#6e7681;font-size:0.75rem;display:block;text-align:right;'>{_fr}</span>", unsafe_allow_html=True)
