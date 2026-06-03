"""
FinSage — Login Page
Google OAuth + Email/Password (Firestore persistent storage)
"""

import streamlit as st
import requests
import json
import os
import hashlib
import time
import urllib.parse
import secrets
from datetime import datetime

# ── Firestore Config ───────────────────────────────────────────────────────────
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "finsage-d6c96")
FIREBASE_API_KEY    = os.environ.get("FIREBASE_API_KEY", "")
FS_BASE = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"
AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"

def _fs_get(collection, doc_id):
    """Get a Firestore document."""
    try:
        url = f"{FS_BASE}/{collection}/{doc_id}?key={FIREBASE_API_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            fields = r.json().get("fields", {})
            return {k: list(v.values())[0] for k, v in fields.items()}
    except:
        pass
    return None

def _fs_set(collection, doc_id, data: dict):
    """Create or update a Firestore document."""
    try:
        fields = {k: {"stringValue": str(v)} for k, v in data.items()}
        url = f"{FS_BASE}/{collection}/{doc_id}?key={FIREBASE_API_KEY}"
        r = requests.patch(url, json={"fields": fields}, timeout=10)
        return r.status_code in (200, 201)
    except:
        return False

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ── User Auth Functions ────────────────────────────────────────────────────────
def register_user(email: str, password: str, name: str):
    email = email.lower().strip()
    doc_id = email.replace("@", "_at_").replace(".", "_")

    # Check if already exists
    existing = _fs_get("users", doc_id)
    if existing:
        return False, "Email already registered. Please login."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    data = {
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat(),
        "provider": "email",
        "last_login": datetime.now().isoformat(),
    }
    ok = _fs_set("users", doc_id, data)
    if ok:
        return True, "Account created successfully!"
    # Fallback to local if Firestore not configured
    return _local_register(email, password, name)

def login_user(email: str, password: str):
    email = email.lower().strip()
    doc_id = email.replace("@", "_at_").replace(".", "_")

    user = _fs_get("users", doc_id)
    if not user:
        # Try local fallback
        return _local_login(email, password)

    if user.get("password_hash") != hash_password(password):
        return False, {"error": "Incorrect password. Please try again."}

    # Update last_login
    user["last_login"] = datetime.now().isoformat()
    _fs_set("users", doc_id, user)

    return True, {"name": user["name"], "email": user["email"], "provider": "email", "picture": None}

def save_google_user(email: str, name: str, picture: str = ""):
    email = email.lower().strip()
    doc_id = email.replace("@", "_at_").replace(".", "_")
    existing = _fs_get("users", doc_id) or {}
    data = {
        "name": name,
        "email": email,
        "password_hash": existing.get("password_hash", ""),
        "created_at": existing.get("created_at", datetime.now().isoformat()),
        "provider": "google",
        "picture": picture,
        "last_login": datetime.now().isoformat(),
    }
    _fs_set("users", doc_id, data)
    return {"name": name, "email": email, "provider": "google", "picture": picture}

# ── Local fallback (if Firestore key not set) ──────────────────────────────────
LOCAL_FILE = "users_local.json"

def _local_load():
    if os.path.exists(LOCAL_FILE):
        try:
            with open(LOCAL_FILE) as f: return json.load(f)
        except: return {}
    return {}

def _local_save(u):
    with open(LOCAL_FILE, "w") as f: json.dump(u, f, indent=2)

def _local_register(email, password, name):
    users = _local_load()
    if email in users: return False, "Email already registered."
    users[email] = {"name": name, "email": email,
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat(), "provider": "email"}
    _local_save(users)
    return True, "Account created!"

def _local_login(email, password):
    users = _local_load()
    if email not in users:
        return False, {"error": "Email not registered. Please create an account."}
    if users[email].get("password_hash") != hash_password(password):
        return False, {"error": "Incorrect password."}
    u = users[email]
    return True, {"name": u["name"], "email": u["email"], "provider": "email", "picture": None}

# ── Google OAuth ───────────────────────────────────────────────────────────────
GOOGLE_AUTH_URL     = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL    = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_redirect_uri():
    return os.environ.get("GOOGLE_REDIRECT_URI",
        "https://finsage-app-mzhu9qcb5eappqtqcpah8kp.streamlit.app/")

def get_google_login_url():
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id: return ""
    state = secrets.token_urlsafe(16)
    st.session_state["oauth_state"] = state
    params = {
        "client_id": client_id,
        "redirect_uri": get_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)

def exchange_code_for_user(code: str):
    client_id     = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    if not client_secret:
        return {"error": "Google Client Secret not configured."}
    try:
        token_resp = requests.post(GOOGLE_TOKEN_URL, data={
            "code": code, "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": get_redirect_uri(),
            "grant_type": "authorization_code",
        }, timeout=15)
        token_data = token_resp.json()
        if "error" in token_data:
            return {"error": token_data.get("error_description", "Token exchange failed.")}
        access_token = token_data.get("access_token")
        user_info = requests.get(GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}, timeout=10).json()
        return save_google_user(
            email=user_info.get("email", ""),
            name=user_info.get("name", user_info.get("email","User").split("@")[0]),
            picture=user_info.get("picture", ""),
        )
    except Exception as e:
        return {"error": f"Google login failed: {str(e)}"}

# ── CSS ────────────────────────────────────────────────────────────────────────
AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

#MainMenu,footer,header,[data-testid="stToolbar"],
[data-testid="manage-app-button"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],.stDeployButton,
.viewerBadge_container__r5tak { visibility:hidden !important; display:none !important; }
section[data-testid="stSidebar"] { display:none !important; }

/* ── Animated deep-space background ── */
body, .stApp {
    background: #020510 !important;
    font-family: 'Inter', sans-serif !important;
    overflow-x: hidden;
}
.stApp::before {
    content:'';
    position:fixed; inset:0; z-index:0;
    background:
        radial-gradient(ellipse 80% 60% at 20% 10%, rgba(88,166,255,0.13) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 80% 80%, rgba(167,139,250,0.12) 0%, transparent 55%),
        radial-gradient(ellipse 50% 40% at 50% 50%, rgba(63,185,80,0.06) 0%, transparent 60%);
    animation: bgpulse 8s ease-in-out infinite alternate;
    pointer-events:none;
}
@keyframes bgpulse {
    0%   { opacity:0.7; transform:scale(1); }
    100% { opacity:1;   transform:scale(1.04); }
}

/* Floating particles */
.particles {
    position:fixed; inset:0; z-index:0; pointer-events:none; overflow:hidden;
}
.particle {
    position:absolute; border-radius:50%;
    background:rgba(88,166,255,0.35);
    animation: float linear infinite;
}
@keyframes float {
    0%   { transform:translateY(100vh) scale(0); opacity:0; }
    10%  { opacity:1; }
    90%  { opacity:0.6; }
    100% { transform:translateY(-10vh) scale(1); opacity:0; }
}

/* ── Main wrapper ── */
.auth-wrapper {
    position:relative; z-index:10;
    min-height:100vh;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding: 2rem 1rem;
}

/* ── Logo area ── */
.auth-logo-area {
    text-align:center;
    margin: 0 0 2rem;
    position:relative;
}
.auth-logo-glow {
    display:inline-block;
    font-size:4.5rem;
    filter: drop-shadow(0 0 24px rgba(88,166,255,0.8)) drop-shadow(0 0 48px rgba(88,166,255,0.4));
    animation: logoFloat 3s ease-in-out infinite;
}
@keyframes logoFloat {
    0%,100% { transform:translateY(0px) rotate(-2deg); }
    50%      { transform:translateY(-10px) rotate(2deg); }
}
.auth-logo-name {
    font-size:3rem; font-weight:900; letter-spacing:-2px;
    background: linear-gradient(135deg, #58a6ff 0%, #a78bfa 50%, #3fb950 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text;
    text-shadow: none;
    margin:0.4rem 0 0;
    animation: gradShift 4s ease-in-out infinite alternate;
    background-size:200% 200%;
}
@keyframes gradShift {
    0%   { background-position:0% 50%; }
    100% { background-position:100% 50%; }
}
.auth-logo-tag {
    color:#8b949e; font-size:0.9rem; margin-top:0.3rem; letter-spacing:0.5px;
}

/* ── Feature pills ── */
.feature-pills { display:flex; justify-content:center; gap:0.5rem; flex-wrap:wrap; margin:1rem 0 0; }
.pill {
    background: linear-gradient(135deg, rgba(63,185,80,0.15), rgba(63,185,80,0.05));
    color:#3fb950; border:1px solid rgba(63,185,80,0.3);
    border-radius:20px; padding:0.25rem 0.8rem; font-size:0.75rem; font-weight:700;
    backdrop-filter:blur(8px);
    transition: all 0.2s;
}
.pill:hover { transform:translateY(-2px); box-shadow:0 4px 12px rgba(63,185,80,0.3); }

/* ── 3D Auth Card ── */
.auth-card-3d {
    background: linear-gradient(145deg,
        rgba(22,27,34,0.95) 0%,
        rgba(13,17,23,0.98) 100%);
    border: 1px solid rgba(88,166,255,0.2);
    border-radius:24px;
    padding:2.2rem 2rem 1.8rem;
    box-shadow:
        0 0 0 1px rgba(88,166,255,0.05),
        0 4px 6px rgba(0,0,0,0.4),
        0 12px 32px rgba(0,0,0,0.5),
        0 32px 64px rgba(0,0,0,0.3),
        inset 0 1px 0 rgba(255,255,255,0.06),
        inset 0 -1px 0 rgba(0,0,0,0.2);
    backdrop-filter:blur(24px);
    transform: perspective(1000px) rotateX(1deg);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    position:relative; overflow:hidden;
    margin-bottom: 0.8rem;
}
.auth-card-3d::before {
    content:'';
    position:absolute; top:0; left:0; right:0; height:1px;
    background: linear-gradient(90deg, transparent, rgba(88,166,255,0.6), rgba(167,139,250,0.6), transparent);
    animation: shimmer 3s ease-in-out infinite;
}
@keyframes shimmer {
    0%,100% { opacity:0.4; } 50% { opacity:1; }
}
.auth-card-3d:hover {
    transform: perspective(1000px) rotateX(0deg) translateY(-4px);
    box-shadow:
        0 0 0 1px rgba(88,166,255,0.15),
        0 8px 16px rgba(0,0,0,0.4),
        0 24px 48px rgba(0,0,0,0.5),
        0 0 80px rgba(88,166,255,0.08),
        inset 0 1px 0 rgba(255,255,255,0.08);
}

.auth-title {
    color:#e6edf3; font-size:1.15rem; font-weight:700;
    text-align:center; margin-bottom:1.5rem; letter-spacing:-0.3px;
}

/* ── Google button ── */
.google-btn-wrap { display:flex; justify-content:center; margin-bottom:0.5rem; }
.google-btn {
    display:inline-flex; align-items:center; justify-content:center; gap:10px;
    background: linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%);
    color:#1f1f1f !important; text-decoration:none !important;
    border-radius:12px; padding:0.8rem 1.5rem; font-size:0.95rem; font-weight:700;
    width:100%; cursor:pointer; letter-spacing:0.2px;
    box-shadow:
        0 1px 3px rgba(0,0,0,0.4),
        0 4px 12px rgba(0,0,0,0.3),
        inset 0 1px 0 rgba(255,255,255,0.9);
    transition: all 0.2s ease;
    border: 1px solid rgba(0,0,0,0.1);
}
.google-btn:hover {
    transform:translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.4), 0 8px 24px rgba(88,166,255,0.15);
    background: linear-gradient(135deg, #ffffff 0%, #eef4ff 100%) !important;
}

/* ── Divider ── */
.divider-row { display:flex; align-items:center; gap:0.8rem; margin:1.2rem 0; color:#484f58; font-size:0.8rem; }
.divider-line { flex:1; height:1px; background:linear-gradient(90deg, transparent, #30363d, transparent); }

/* ── Input overrides ── */
[data-testid="stTextInput"] input {
    background: rgba(13,17,23,0.8) !important;
    border: 1px solid rgba(48,54,61,0.8) !important;
    border-radius:10px !important; color:#e6edf3 !important;
    font-size:0.9rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: rgba(88,166,255,0.6) !important;
    box-shadow: 0 0 0 3px rgba(88,166,255,0.12), 0 0 20px rgba(88,166,255,0.08) !important;
}

/* ── Primary button ── */
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"],
button[kind="primary"] {
    background: linear-gradient(135deg, #1a6bc7 0%, #2563eb 50%, #7c3aed 100%) !important;
    border:none !important; border-radius:12px !important;
    font-weight:700 !important; font-size:0.95rem !important; letter-spacing:0.3px !important;
    box-shadow:
        0 4px 14px rgba(37,99,235,0.4),
        0 0 0 1px rgba(255,255,255,0.05),
        inset 0 1px 0 rgba(255,255,255,0.15) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover,
button[kind="primary"]:hover {
    transform:translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(37,99,235,0.5), 0 0 40px rgba(124,58,237,0.2) !important;
}

/* ── Tabs ── */
[data-baseweb="tab-list"] {
    background:rgba(13,17,23,0.6) !important;
    border-radius:12px !important; padding:4px !important;
    border:1px solid rgba(48,54,61,0.5) !important;
}
[data-baseweb="tab"] {
    border-radius:9px !important; font-weight:600 !important; font-size:0.85rem !important;
    color:#8b949e !important; transition:all 0.2s !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background:linear-gradient(135deg, rgba(88,166,255,0.15), rgba(167,139,250,0.1)) !important;
    color:#e6edf3 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05) !important;
}

/* ── Footer ── */
.auth-footer {
    text-align:center; color:#484f58; font-size:0.73rem;
    margin-top:1.2rem; line-height:1.8;
}
.privacy-link { color:#58a6ff !important; text-decoration:none !important; font-weight:600; }
.privacy-link:hover { text-decoration:underline !important; }

/* ── Checkbox ── */
[data-testid="stCheckbox"] label { color:#8b949e !important; font-size:0.82rem !important; }
</style>

<!-- Animated floating particles -->
<div class="particles">
  <div class="particle" style="left:10%;width:3px;height:3px;animation-duration:12s;animation-delay:0s;"></div>
  <div class="particle" style="left:25%;width:2px;height:2px;animation-duration:18s;animation-delay:3s;background:rgba(167,139,250,0.5);"></div>
  <div class="particle" style="left:40%;width:4px;height:4px;animation-duration:15s;animation-delay:6s;background:rgba(63,185,80,0.4);"></div>
  <div class="particle" style="left:60%;width:2px;height:2px;animation-duration:20s;animation-delay:1s;"></div>
  <div class="particle" style="left:75%;width:3px;height:3px;animation-duration:14s;animation-delay:8s;background:rgba(167,139,250,0.4);"></div>
  <div class="particle" style="left:88%;width:2px;height:2px;animation-duration:16s;animation-delay:4s;background:rgba(63,185,80,0.5);"></div>
  <div class="particle" style="left:50%;width:3px;height:3px;animation-duration:22s;animation-delay:10s;"></div>
  <div class="particle" style="left:33%;width:2px;height:2px;animation-duration:17s;animation-delay:7s;background:rgba(248,113,113,0.4);"></div>
</div>
"""

# ── Main Render ────────────────────────────────────────────────────────────────
def render_auth_page() -> bool:
    # Handle OAuth callback
    params = st.query_params
    if "code" in params and not st.session_state.get("user"):
        with st.spinner("🔄 Completing Google Sign-In..."):
            user = exchange_code_for_user(params["code"])
            st.query_params.clear()
            if "error" not in user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error(f"❌ {user['error']}")

    if st.session_state.get("user"):
        return True

    client_id     = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    google_available = bool(client_id and client_secret)

    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    # Logo
    st.markdown("""
    <div class="auth-logo-area">
        <div class="auth-logo-glow">📊</div>
        <div class="auth-logo-name">FinSage</div>
        <div class="auth-logo-tag">Global Financial Intelligence Platform</div>
        <div class="feature-pills">
            <span class="pill">📈 Stocks</span>
            <span class="pill">₿ Crypto</span>
            <span class="pill">🎭 Meme Coins</span>
            <span class="pill">🆓 100% Free</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2.2, 1])
    with col:
        # Google button
        st.markdown('<div class="auth-card-3d"><div class="auth-title">✨ Sign in to FinSage</div>', unsafe_allow_html=True)
        if google_available:
            google_url = get_google_login_url()
            st.markdown(f"""
            <div class="google-btn-wrap">
                <a href="{google_url}" class="google-btn">
                    <svg width="20" height="20" viewBox="0 0 48 48">
                        <path fill="#EA4335" d="M24 9.5c3.14 0 5.95 1.08 8.17 2.84L38.34 6.1C34.52 2.31 29.53 0 24 0 14.62 0 6.63 5.47 2.63 13.4l7.08 5.5C11.63 13.15 17.35 9.5 24 9.5z"/>
                        <path fill="#4285F4" d="M46.52 24.5c0-1.6-.14-3.14-.4-4.64H24v9.27h12.67c-.55 2.93-2.2 5.41-4.68 7.09l7.27 5.65C43.52 37.96 46.52 31.7 46.52 24.5z"/>
                        <path fill="#FBBC05" d="M9.71 28.62A14.83 14.83 0 0 1 9.5 24c0-1.6.28-3.15.71-4.62L3.13 13.9A23.93 23.93 0 0 0 0 24c0 3.87.92 7.53 2.54 10.77l7.17-6.15z"/>
                        <path fill="#34A853" d="M24 48c5.53 0 10.17-1.82 13.56-4.95l-7.27-5.65c-1.95 1.3-4.45 2.1-6.29 2.1-6.62 0-12.23-4.47-14.25-10.5l-7.17 6.15C6.6 42.58 14.62 48 24 48z"/>
                    </svg>
                    Continue with Google
                </a>
            </div>
            <div class="divider-row"><div class="divider-line"></div><span>or use email</span><div class="divider-line"></div></div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Email tabs
        tab_login, tab_signup = st.tabs(["🔑  Login", "📝  Create Account"])

        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                email    = st.text_input("📧 Email",    placeholder="you@example.com")
                password = st.text_input("🔒 Password", type="password", placeholder="Your password")
                login_btn = st.form_submit_button("Login →", use_container_width=True, type="primary")
                if login_btn:
                    if not email or not password:
                        st.error("Please fill in all fields.")
                    else:
                        ok, result = login_user(email, password)
                        if ok:
                            st.session_state.user = result
                            st.success(f"✅ Welcome back, {result['name']}!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(result.get("error", "Login failed."))

        with tab_signup:
            with st.form("signup_form", clear_on_submit=True):
                name       = st.text_input("👤 Full Name",        placeholder="Your name")
                email_s    = st.text_input("📧 Email",            placeholder="you@example.com", key="se")
                password_s = st.text_input("🔒 Password",         type="password", placeholder="Min 6 characters", key="sp")
                password_c = st.text_input("🔒 Confirm Password", type="password", placeholder="Repeat password",   key="sc")
                agree      = st.checkbox("I agree to the Privacy Policy", key="agree_pp")
                signup_btn = st.form_submit_button("Create Account →", use_container_width=True, type="primary")
                if signup_btn:
                    if not name or not email_s or not password_s:
                        st.error("Please fill in all fields.")
                    elif "@" not in email_s:
                        st.error("Please enter a valid email address.")
                    elif password_s != password_c:
                        st.error("Passwords do not match.")
                    elif not agree:
                        st.error("Please accept the Privacy Policy to continue.")
                    else:
                        ok, msg = register_user(email_s, password_s, name)
                        if ok:
                            _, user_obj = login_user(email_s, password_s)
                            st.session_state.user = user_obj
                            st.success(f"✅ Welcome to FinSage, {name}!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(msg)

        # Footer with Privacy Policy link
        st.markdown("""
        <div class="auth-footer">
            🔒 Passwords are SHA-256 hashed — never stored in plain text.<br>
            By signing up, you agree to our
            <a href="?page=privacy" class="privacy-link" target="_self">Privacy Policy</a>.<br>
            FinSage is for educational purposes only. Not investment advice.
        </div>
        """, unsafe_allow_html=True)

    return False


def is_logged_in() -> bool:
    return bool(st.session_state.get("user"))

def get_current_user() -> dict:
    return st.session_state.get("user", {})

def logout():
    st.session_state.user = None
    st.rerun()

def render_sidebar_auth():
    pass  # kept for import compatibility
