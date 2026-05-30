"""
FinSage — Login Page
Google One-Tap (Client ID only) + Email/Password Authentication
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
        "provider": "email"
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
    return True, {
        "name": user["name"],
        "email": user["email"],
        "provider": "email",
        "picture": None,
    }


# ── Google One-Tap token verify ────────────────────────────────────────────────
def verify_google_token(credential: str) -> dict:
    """Verify Google ID token using Google's tokeninfo endpoint."""
    try:
        resp = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}",
            timeout=10
        )
        info = resp.json()
        if "error" in info:
            return {"error": info.get("error_description", "Invalid token")}
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        if info.get("aud") != client_id:
            return {"error": "Token audience mismatch"}
        return {
            "name": info.get("name", info.get("email", "User").split("@")[0]),
            "email": info.get("email", ""),
            "picture": info.get("picture", ""),
            "provider": "google",
        }
    except Exception as e:
        return {"error": str(e)}


# ── CSS ────────────────────────────────────────────────────────────────────────
AUTH_CSS = """
<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
[data-testid="stToolbar"] { display: none !important; }

body { background: #0d1117; }

.auth-logo-area {
    text-align: center;
    margin: 1.5rem 0 1rem;
}
.auth-logo-icon { font-size: 3.5rem; }
.auth-logo-name {
    font-size: 2.2rem;
    font-weight: 900;
    color: #58a6ff;
    margin: 0.2rem 0 0;
}
.auth-logo-tag {
    color: #8b949e;
    font-size: 0.88rem;
    margin-top: 0.2rem;
}
.feature-pills {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin: 0.8rem 0 0;
}
.pill {
    background: #1a3a1a;
    color: #3fb950;
    border-radius: 20px;
    padding: 0.2rem 0.65rem;
    font-size: 0.75rem;
    font-weight: 600;
}
.auth-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 1.6rem 1.4rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    margin-bottom: 0.5rem;
}
.auth-title {
    color: #c9d1d9;
    font-size: 1.1rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 1.2rem;
}
.divider-row {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin: 1rem 0;
    color: #6e7681;
    font-size: 0.82rem;
}
.divider-line {
    flex: 1; height: 1px;
    background: #30363d;
}
.auth-footer {
    text-align: center;
    color: #6e7681;
    font-size: 0.74rem;
    margin-top: 1rem;
    line-height: 1.6;
}
/* Google One-Tap button container */
#g_id_onload, .g_id_signin {
    display: flex !important;
    justify-content: center !important;
    margin-bottom: 0.5rem;
}
</style>
"""


# ── Main Auth Page Renderer ────────────────────────────────────────────────────
def render_auth_page():
    """Render login page. Returns True if logged in."""

    # Check Google One-Tap callback via query params
    params = st.query_params
    if "credential" in params and not st.session_state.get("user"):
        with st.spinner("Signing in with Google..."):
            user = verify_google_token(params["credential"])
            if "error" not in user:
                st.session_state.user = user
                st.query_params.clear()
                st.rerun()
            else:
                st.error(f"Google sign-in failed: {user['error']}")
                st.query_params.clear()

    if st.session_state.get("user"):
        return True

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")

    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    # Logo
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

    _, col, _ = st.columns([1, 2, 1])
    with col:

        # Google One-Tap Sign-In
        if client_id:
            st.markdown(f"""
            <div class="auth-card">
                <div class="auth-title">Sign in to FinSage</div>

                <!-- Google One-Tap -->
                <script src="https://accounts.google.com/gsi/client" async defer></script>
                <div id="g_id_onload"
                    data-client_id="{client_id}"
                    data-callback="handleGoogleCredential"
                    data-auto_prompt="false">
                </div>
                <div class="g_id_signin"
                    data-type="standard"
                    data-size="large"
                    data-theme="filled_blue"
                    data-text="continue_with"
                    data-shape="rectangular"
                    data-logo_alignment="left"
                    data-width="340">
                </div>
                <script>
                function handleGoogleCredential(response) {{
                    window.location.href = window.location.pathname + '?credential=' + response.credential;
                }}
                </script>

                <div class="divider-row">
                    <div class="divider-line"></div>
                    <span>or use email</span>
                    <div class="divider-line"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="auth-card">
                <div class="auth-title">Sign in to FinSage</div>
                <div class="divider-row">
                    <div class="divider-line"></div>
                    <span>continue with email</span>
                    <div class="divider-line"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Email/Password tabs
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
                            time.sleep(0.6)
                            st.rerun()
                        else:
                            st.error(result.get("error", "Login failed."))

        with tab_signup:
            with st.form("signup_form"):
                name = st.text_input("👤 Full Name", placeholder="Your name")
                email_s = st.text_input("📧 Email", placeholder="you@example.com", key="se")
                password_s = st.text_input("🔒 Password", type="password", placeholder="Min 6 characters", key="sp")
                password_c = st.text_input("🔒 Confirm Password", type="password", placeholder="Repeat password", key="sc")
                submitted_s = st.form_submit_button("Create Account →", use_container_width=True, type="primary")
                if submitted_s:
                    if not name or not email_s or not password_s:
                        st.error("Please fill in all fields.")
                    elif password_s != password_c:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg = register_user(email_s, password_s, name)
                        if ok:
                            _, user = login_user(email_s, password_s)
                            st.session_state.user = user
                            st.success(f"✅ Welcome, {name}!")
                            time.sleep(0.6)
                            st.rerun()
                        else:
                            st.error(msg)

        st.markdown("""
        <div class="auth-footer">
            🔒 Passwords are securely hashed — never stored in plain text.<br>
            For educational use only. Not investment advice.
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
