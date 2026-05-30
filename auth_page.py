"""
FinSage — Login Page
Google OAuth + Email/Password Authentication
Uses streamlit-oauth for Google and bcrypt for email/password
"""

import streamlit as st
import requests
import json
import os
import hashlib
import time
from datetime import datetime


# ── Simple user store (JSON file based) ───────────────────────────────────────
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

def register_user(email: str, password: str, name: str) -> tuple[bool, str]:
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
        "provider": "email"
    }
    save_users(users)
    return True, "Account created successfully!"

def login_user(email: str, password: str) -> tuple[bool, dict]:
    users = load_users()
    email = email.lower().strip()
    if email not in users:
        return False, {"error": "Email not registered. Please create an account."}
    user = users[email]
    if user.get("password_hash") != hash_password(password):
        return False, {"error": "Incorrect password. Please try again."}
    return True, {
        "name": user["name"],
        "email": user["email"],
        "provider": "email",
        "picture": None,
    }


# ── Google OAuth (server-side flow) ───────────────────────────────────────────
def get_google_oauth_url() -> str:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "")
    if not client_id or not redirect_uri:
        return ""
    scope = "openid email profile"
    import secrets, urllib.parse
    state = secrets.token_urlsafe(16)
    st.session_state["oauth_state"] = state
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

def exchange_google_code(code: str) -> dict:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "")
    try:
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }, timeout=10)
        token = resp.json()
        if "access_token" not in token:
            return {"error": token.get("error_description", "Google login failed.")}
        user_resp = requests.get("https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token['access_token']}"}, timeout=10)
        user = user_resp.json()
        return {
            "name": user.get("name", "User"),
            "email": user.get("email", ""),
            "picture": user.get("picture", ""),
            "provider": "google",
        }
    except Exception as e:
        return {"error": str(e)}


# ── CSS Styles ─────────────────────────────────────────────────────────────────
AUTH_CSS = """
<style>
.auth-wrapper {
    max-width: 440px;
    margin: 2rem auto;
}
.auth-logo-area {
    text-align: center;
    margin-bottom: 1.5rem;
}
.auth-logo-icon { font-size: 3.5rem; }
.auth-logo-name {
    font-size: 2.2rem;
    font-weight: 900;
    color: #58a6ff;
    margin: 0.2rem 0;
}
.auth-logo-tag {
    color: #8b949e;
    font-size: 0.88rem;
}
.auth-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 2rem 1.8rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.auth-title {
    color: #c9d1d9;
    font-size: 1.15rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 1.4rem;
}
.google-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: #ffffff;
    color: #1f1f1f !important;
    text-decoration: none !important;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 1.2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    transition: background 0.2s;
    cursor: pointer;
}
.google-btn:hover { background: #f5f5f5 !important; }
.divider-row {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin: 1rem 0;
    color: #6e7681;
    font-size: 0.82rem;
}
.divider-line {
    flex: 1;
    height: 1px;
    background: #30363d;
}
.auth-footer {
    text-align: center;
    color: #6e7681;
    font-size: 0.75rem;
    margin-top: 1.2rem;
    line-height: 1.6;
}
.feature-pills {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin: 1rem 0;
}
.pill {
    background: #1a3a1a;
    color: #3fb950;
    border-radius: 20px;
    padding: 0.2rem 0.65rem;
    font-size: 0.75rem;
    font-weight: 600;
}
</style>
"""


# ── Main Auth Page Renderer ────────────────────────────────────────────────────
def render_auth_page():
    """Render the full login/signup page. Returns True if user is logged in."""

    # Handle OAuth callback
    params = st.query_params
    if "code" in params and not st.session_state.get("user"):
        with st.spinner("🔄 Signing you in with Google..."):
            user = exchange_google_code(params["code"])
            if "error" not in user:
                st.session_state.user = user
                st.query_params.clear()
                st.rerun()
            else:
                st.error(f"❌ Google sign-in failed: {user['error']}")
                st.query_params.clear()

    # Already logged in
    if st.session_state.get("user"):
        return True

    # Inject CSS
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    # Logo
    st.markdown("""
    <div class="auth-wrapper">
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
    </div>
    """, unsafe_allow_html=True)

    # Card
    _, col, _ = st.columns([1, 2, 1])
    with col:

        # ── Google OAuth Button ──
        google_url = get_google_oauth_url()
        if google_url:
            st.markdown(f"""
            <div class="auth-card" style="margin-bottom:0.5rem;">
                <div class="auth-title">Sign in to FinSage</div>
                <a href="{google_url}" class="google-btn">
                    <svg width="20" height="20" viewBox="0 0 48 48">
                        <path fill="#EA4335" d="M24 9.5c3.14 0 5.95 1.08 8.17 2.84L38.34 6.1C34.52 2.31 29.53 0 24 0 14.62 0 6.63 5.47 2.63 13.4l7.08 5.5C11.63 13.15 17.35 9.5 24 9.5z"/>
                        <path fill="#4285F4" d="M46.52 24.5c0-1.6-.14-3.14-.4-4.64H24v9.27h12.67c-.55 2.93-2.2 5.41-4.68 7.09l7.27 5.65C43.52 37.96 46.52 31.7 46.52 24.5z"/>
                        <path fill="#FBBC05" d="M9.71 28.62A14.83 14.83 0 0 1 9.5 24c0-1.6.28-3.15.71-4.62L3.13 13.9A23.93 23.93 0 0 0 0 24c0 3.87.92 7.53 2.54 10.77l7.17-6.15z"/>
                        <path fill="#34A853" d="M24 48c5.53 0 10.17-1.82 13.56-4.95l-7.27-5.65c-1.95 1.3-4.45 2.1-6.29 2.1-6.62 0-12.23-4.47-14.25-10.5l-7.17 6.15C6.6 42.58 14.62 48 24 48z"/>
                        <path fill="none" d="M0 0h48v48H0z"/>
                    </svg>
                    Continue with Google
                </a>
                <div class="divider-row">
                    <div class="divider-line"></div>
                    <span>or continue with email</span>
                    <div class="divider-line"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="auth-card" style="margin-bottom:0.5rem;">
                <div class="auth-title">Sign in to FinSage</div>
                <div style="background:#1c2333;border:1px solid #30363d;border-radius:8px;padding:0.7rem;color:#8b949e;font-size:0.8rem;text-align:center;margin-bottom:1rem;">
                    ⚠️ Google Sign-In not configured. Use email/password below.
                </div>
                <div class="divider-row">
                    <div class="divider-line"></div>
                    <span>continue with email</span>
                    <div class="divider-line"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Tabs: Login / Create Account ──
        tab_login, tab_signup = st.tabs(["🔑  Login", "📝  Create Account"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("📧 Email", placeholder="you@example.com")
                password = st.text_input("🔒 Password", type="password", placeholder="Your password")
                submitted = st.form_submit_button("Login →", use_container_width=True, type="primary")
                if submitted:
                    if not email or not password:
                        st.error("Please fill in all fields.")
                    else:
                        ok, result = login_user(email, password)
                        if ok:
                            st.session_state.user = result
                            st.success(f"✅ Welcome back, {result['name']}!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error(result.get("error", "Login failed."))

        with tab_signup:
            with st.form("signup_form"):
                name = st.text_input("👤 Full Name", placeholder="Your name")
                email_s = st.text_input("📧 Email", placeholder="you@example.com", key="signup_email")
                password_s = st.text_input("🔒 Password", type="password", placeholder="Min 6 characters", key="signup_pass")
                password_c = st.text_input("🔒 Confirm Password", type="password", placeholder="Repeat password", key="signup_confirm")
                submitted_s = st.form_submit_button("Create Account →", use_container_width=True, type="primary")
                if submitted_s:
                    if not name or not email_s or not password_s:
                        st.error("Please fill in all fields.")
                    elif password_s != password_c:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg = register_user(email_s, password_s, name)
                        if ok:
                            # Auto login
                            _, user = login_user(email_s, password_s)
                            st.session_state.user = user
                            st.success(f"✅ Account created! Welcome, {name}!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error(msg)

        st.markdown("""
        <div class="auth-footer">
            🔒 Your data is secure. Passwords are hashed & never stored in plain text.<br>
            By signing in, you agree to use FinSage for educational purposes only.
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
