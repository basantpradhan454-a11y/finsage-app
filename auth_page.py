"""
FinSage — Login Page
Google OAuth (proper redirect flow) + Email/Password
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

# ── User Store ─────────────────────────────────────────────────────────────────
USER_DB_FILE = "users.json"

def load_users() -> dict:
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users: dict):
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f, indent=2)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(email: str, password: str, name: str) -> tuple:
    users = load_users()
    email = email.lower().strip()
    if email in users:
        return False, "Email already registered. Please login."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    users[email] = {
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat(),
        "provider": "email",
        "last_login": datetime.now().isoformat(),
    }
    save_users(users)
    return True, "Account created successfully!"

def login_user(email: str, password: str) -> tuple:
    users = load_users()
    email = email.lower().strip()
    if email not in users:
        return False, {"error": "Email not registered. Please create an account."}
    user = users[email]
    if user.get("password_hash") != hash_password(password):
        return False, {"error": "Incorrect password. Please try again."}
    # Update last login
    users[email]["last_login"] = datetime.now().isoformat()
    save_users(users)
    return True, {
        "name": user["name"],
        "email": user["email"],
        "provider": "email",
        "picture": None,
    }

def save_google_user(email: str, name: str, picture: str = "") -> dict:
    """Save or update a Google-authenticated user."""
    users = load_users()
    email = email.lower().strip()
    if email not in users:
        users[email] = {
            "name": name,
            "email": email,
            "password_hash": None,
            "created_at": datetime.now().isoformat(),
            "provider": "google",
            "picture": picture,
            "last_login": datetime.now().isoformat(),
        }
    else:
        users[email]["last_login"] = datetime.now().isoformat()
        users[email]["name"] = name
        users[email]["picture"] = picture
    save_users(users)
    return {"name": name, "email": email, "provider": "google", "picture": picture}


# ── Google OAuth (Proper Authorization Code Flow) ──────────────────────────────
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_google_login_url() -> str:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", get_redirect_uri())
    if not client_id:
        return ""
    state = secrets.token_urlsafe(16)
    st.session_state["oauth_state"] = state
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)

def get_redirect_uri() -> str:
    """Auto-detect redirect URI from Streamlit."""
    try:
        import streamlit.web.server.websocket_headers as wh
        pass
    except:
        pass
    return os.environ.get("GOOGLE_REDIRECT_URI", "https://finsage-app-mzhu9qcb5eappqtqcpah8kp.streamlit.app/")

def exchange_code_for_user(code: str) -> dict:
    """Exchange OAuth code for user info."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", get_redirect_uri())

    if not client_secret:
        return {"error": "Google Client Secret not configured. Please use email/password login."}

    try:
        token_resp = requests.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }, timeout=15)
        token_data = token_resp.json()

        if "error" in token_data:
            return {"error": token_data.get("error_description", "Token exchange failed.")}

        access_token = token_data.get("access_token")
        user_resp = requests.get(GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        user_info = user_resp.json()

        return save_google_user(
            email=user_info.get("email", ""),
            name=user_info.get("name", user_info.get("email", "User").split("@")[0]),
            picture=user_info.get("picture", ""),
        )
    except Exception as e:
        return {"error": f"Google login failed: {str(e)}"}


# ── CSS ────────────────────────────────────────────────────────────────────────
AUTH_CSS = """
<style>
/* Hide Streamlit chrome completely */
#MainMenu { visibility: hidden !important; }
footer { visibility: hidden !important; }
header { visibility: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="manage-app-button"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
.stDeployButton { display: none !important; }
.viewerBadge_container__r5tak { display: none !important; }
iframe[title="streamlit_google_auth.streamlit_google_auth"] { display: none; }
div[class*="streamlit-footer"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

body { background: #0d1117; }

.auth-logo-area {
    text-align: center;
    margin: 2rem 0 1.2rem;
}
.auth-logo-icon { font-size: 3.8rem; }
.auth-logo-name {
    font-size: 2.4rem;
    font-weight: 900;
    color: #58a6ff;
    margin: 0.3rem 0 0;
    letter-spacing: -1px;
}
.auth-logo-tag {
    color: #8b949e;
    font-size: 0.88rem;
    margin-top: 0.25rem;
}
.feature-pills {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin: 0.9rem 0 0;
}
.pill {
    background: #1a3a1a;
    color: #3fb950;
    border-radius: 20px;
    padding: 0.22rem 0.7rem;
    font-size: 0.76rem;
    font-weight: 600;
}
.auth-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 1.8rem 1.6rem 1.4rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    margin-bottom: 0.5rem;
}
.auth-title {
    color: #c9d1d9;
    font-size: 1.1rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 1.3rem;
}
.google-btn-wrap {
    display: flex;
    justify-content: center;
    margin-bottom: 0.4rem;
}
.google-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: #ffffff;
    color: #1f1f1f !important;
    text-decoration: none !important;
    border-radius: 8px;
    padding: 0.72rem 1.5rem;
    font-size: 0.95rem;
    font-weight: 600;
    width: 100%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.35);
    transition: background 0.15s;
    cursor: pointer;
    border: none;
}
.google-btn:hover { background: #f0f0f0 !important; }
.divider-row {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin: 1.1rem 0;
    color: #6e7681;
    font-size: 0.82rem;
}
.divider-line { flex: 1; height: 1px; background: #30363d; }
.auth-footer {
    text-align: center;
    color: #6e7681;
    font-size: 0.74rem;
    margin-top: 1.1rem;
    line-height: 1.65;
}
</style>
"""


# ── Main Render ────────────────────────────────────────────────────────────────
def render_auth_page() -> bool:
    """Returns True if user is authenticated."""

    # Handle OAuth callback (Google redirects back with ?code=...)
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

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    google_available = bool(client_id and client_secret)

    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    # Logo area
    st.markdown("""
    <div class="auth-logo-area">
        <div class="auth-logo-icon">📊</div>
        <div class="auth-logo-name">FinSage</div>
        <div class="auth-logo-tag">Global Financial Intelligence Platform</div>
        <div class="feature-pills">
            <span class="pill">✅ Stocks</span>
            <span class="pill">✅ Crypto</span>
            <span class="pill">✅ Meme Coins</span>
            <span class="pill">🆓 100% Free</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2.2, 1])
    with col:

        # Google button
        if google_available:
            google_url = get_google_login_url()
            st.markdown(f"""
            <div class="auth-card">
                <div class="auth-title">Sign in to FinSage</div>
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
                <div class="divider-row">
                    <div class="divider-line"></div><span>or use email</span><div class="divider-line"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="auth-card">
                <div class="auth-title">Sign in to FinSage</div>
                <div style="background:#1c2333;border:1px solid #30363d;border-radius:8px;
                    padding:0.65rem 0.9rem;color:#8b949e;font-size:0.8rem;text-align:center;margin-bottom:1rem;">
                    🔵 Google Sign-In — configure <code>GOOGLE_CLIENT_SECRET</code> in Streamlit Secrets to enable
                </div>
                <div class="divider-row">
                    <div class="divider-line"></div><span>continue with email</span><div class="divider-line"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Email / Password tabs
        tab_login, tab_signup = st.tabs(["🔑  Login", "📝  Create Account"])

        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("📧 Email", placeholder="you@example.com")
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
                name = st.text_input("👤 Full Name", placeholder="Your name")
                email_s = st.text_input("📧 Email", placeholder="you@example.com", key="se")
                password_s = st.text_input("🔒 Password", type="password", placeholder="Min 6 characters", key="sp")
                password_c = st.text_input("🔒 Confirm Password", type="password", placeholder="Repeat password", key="sc")
                signup_btn = st.form_submit_button("Create Account →", use_container_width=True, type="primary")
                if signup_btn:
                    if not name or not email_s or not password_s:
                        st.error("Please fill in all fields.")
                    elif password_s != password_c:
                        st.error("Passwords do not match.")
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

        st.markdown("""
        <div class="auth-footer">
            🔒 Passwords are SHA-256 hashed — never stored in plain text.<br>
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


# ── Sidebar Auth (for public app) ─────────────────────────────────────────────
def render_sidebar_auth():
    """Show login/signup in sidebar for public app."""

    # Handle Google OAuth callback
    params = st.query_params
    if "code" in params and not st.session_state.get("user"):
        with st.spinner("🔄 Signing in with Google..."):
            user = exchange_code_for_user(params["code"])
            st.query_params.clear()
            if "error" not in user:
                st.session_state.user = user
                st.rerun()
            else:
                st.sidebar.error(f"❌ {user['error']}")

    if st.session_state.get("user"):
        return  # Already logged in — sidebar handled in main navbar

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    google_available = bool(client_id and client_secret)

    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:0.5rem 0 0.8rem;">
            <div style="font-size:1.6rem;">📊</div>
            <div style="font-size:1.1rem;font-weight:800;color:#58a6ff;">FinSage</div>
            <div style="font-size:0.75rem;color:#8b949e;">Sign in to save preferences</div>
        </div>
        """, unsafe_allow_html=True)

        # Google button
        if google_available:
            google_url = get_google_login_url()
            st.markdown(f"""
            <a href="{google_url}" style="
                display:flex;align-items:center;justify-content:center;gap:8px;
                background:#fff;color:#1f1f1f;text-decoration:none;
                border-radius:8px;padding:0.6rem 1rem;font-size:0.88rem;
                font-weight:600;box-shadow:0 2px 6px rgba(0,0,0,0.3);
                margin-bottom:0.8rem;">
                <svg width="17" height="17" viewBox="0 0 48 48">
                    <path fill="#EA4335" d="M24 9.5c3.14 0 5.95 1.08 8.17 2.84L38.34 6.1C34.52 2.31 29.53 0 24 0 14.62 0 6.63 5.47 2.63 13.4l7.08 5.5C11.63 13.15 17.35 9.5 24 9.5z"/>
                    <path fill="#4285F4" d="M46.52 24.5c0-1.6-.14-3.14-.4-4.64H24v9.27h12.67c-.55 2.93-2.2 5.41-4.68 7.09l7.27 5.65C43.52 37.96 46.52 31.7 46.52 24.5z"/>
                    <path fill="#FBBC05" d="M9.71 28.62A14.83 14.83 0 0 1 9.5 24c0-1.6.28-3.15.71-4.62L3.13 13.9A23.93 23.93 0 0 0 0 24c0 3.87.92 7.53 2.54 10.77l7.17-6.15z"/>
                    <path fill="#34A853" d="M24 48c5.53 0 10.17-1.82 13.56-4.95l-7.27-5.65c-1.95 1.3-4.45 2.1-6.29 2.1-6.62 0-12.23-4.47-14.25-10.5l-7.17 6.15C6.6 42.58 14.62 48 24 48z"/>
                </svg>
                Continue with Google
            </a>
            <div style="display:flex;align-items:center;gap:0.5rem;margin:0.5rem 0;color:#6e7681;font-size:0.78rem;">
                <div style="flex:1;height:1px;background:#30363d;"></div>or<div style="flex:1;height:1px;background:#30363d;"></div>
            </div>
            """, unsafe_allow_html=True)

        # Email tabs
        tab_l, tab_s = st.tabs(["🔑 Login", "📝 Sign Up"])

        with tab_l:
            with st.form("sb_login", clear_on_submit=False):
                email = st.text_input("Email", placeholder="you@example.com", key="sb_le")
                password = st.text_input("Password", type="password", key="sb_lp")
                if st.form_submit_button("Login →", use_container_width=True, type="primary"):
                    if not email or not password:
                        st.error("Fill in all fields.")
                    else:
                        ok, result = login_user(email, password)
                        if ok:
                            st.session_state.user = result
                            st.success(f"✅ Welcome, {result['name']}!")
                            time.sleep(0.4)
                            st.rerun()
                        else:
                            st.error(result.get("error", "Login failed."))

        with tab_s:
            with st.form("sb_signup", clear_on_submit=True):
                name = st.text_input("Full Name", placeholder="Your name", key="sb_sn")
                email_s = st.text_input("Email", placeholder="you@example.com", key="sb_se")
                pass_s = st.text_input("Password", type="password", placeholder="Min 6 chars", key="sb_sp")
                pass_c = st.text_input("Confirm Password", type="password", key="sb_sc")
                if st.form_submit_button("Create Account →", use_container_width=True, type="primary"):
                    if not name or not email_s or not pass_s:
                        st.error("Fill in all fields.")
                    elif pass_s != pass_c:
                        st.error("Passwords don't match.")
                    else:
                        ok, msg = register_user(email_s, pass_s, name)
                        if ok:
                            _, user_obj = login_user(email_s, pass_s)
                            st.session_state.user = user_obj
                            st.success(f"✅ Welcome, {name}!")
                            time.sleep(0.4)
                            st.rerun()
                        else:
                            st.error(msg)

        st.markdown("""
        <div style="color:#6e7681;font-size:0.72rem;text-align:center;margin-top:0.8rem;">
            🔒 Passwords hashed — never stored plain text
        </div>
        """, unsafe_allow_html=True)
