"""
FinSage — Login Page
Google OAuth 2.0 (via Google Cloud Console) + Email/Password fallback
"""

import streamlit as st
import os
import time
import hashlib
import json
import requests
import urllib.parse
from datetime import datetime

# ── Google OAuth config ────────────────────────────────────────────────────────
def _get(key):
    try:
        return st.secrets[key]
    except:
        return os.environ.get(key, "")

GOOGLE_CLIENT_ID     = lambda: _get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = lambda: _get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI         = lambda: _get("REDIRECT_URI") or "https://finsage-app-mzhu9qcb5eappqtqcpah8kp.streamlit.app/"

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_INFO_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

# ── Simple local user store (email/password users) ─────────────────────────────
USERS_FILE = "users.json"

def _load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def register_user(email, password, name):
    users = _load_users()
    email = email.lower().strip()
    if email in users:
        return False, "An account with this email already exists. Please log in."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    users[email] = {
        "name": name, "email": email,
        "password_hash": _hash(password),
        "joined": datetime.now().strftime("%Y-%m-%d"),
        "provider": "email"
    }
    _save_users(users)
    return True, "Account created!"

def login_email(email, password):
    users = _load_users()
    email = email.lower().strip()
    if email not in users:
        return False, "No account found with this email."
    if users[email].get("password_hash") != _hash(password):
        return False, "Incorrect password. Please try again."
    u = users[email]
    return True, {"name": u["name"], "email": u["email"], "provider": "email", "picture": None}

# ── Google OAuth helpers ───────────────────────────────────────────────────────
def _google_auth_url():
    state = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
    st.session_state["oauth_state"] = state
    params = {
        "client_id": GOOGLE_CLIENT_ID(),
        "redirect_uri": REDIRECT_URI(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)

def _exchange_code(code):
    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "code": code,
        "client_id": GOOGLE_CLIENT_ID(),
        "client_secret": GOOGLE_CLIENT_SECRET(),
        "redirect_uri": REDIRECT_URI(),
        "grant_type": "authorization_code",
    }, timeout=10)
    return resp.json()

def _get_google_user(access_token):
    resp = requests.get(GOOGLE_INFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    return resp.json()

# ── Session helpers ────────────────────────────────────────────────────────────
def is_logged_in():
    return bool(st.session_state.get("user"))

def get_current_user():
    return st.session_state.get("user")

def logout():
    st.session_state.pop("user", None)
    st.session_state.pop("oauth_state", None)
    st.rerun()

# ── CSS ────────────────────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="manage-app-button"],
.stDeployButton { display: none !important; }
body { background: #0d1117; }

.auth-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 2.4rem 2.2rem 2rem;
    box-shadow: 0 20px 60px rgba(0,0,0,0.7);
    max-width: 420px;
    margin: 2rem auto;
}
.brand-icon { text-align:center; font-size:3rem; margin-bottom:0.2rem; }
.brand-name {
    text-align:center; font-size:1.8rem; font-weight:800;
    background: linear-gradient(135deg,#58a6ff,#a78bfa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:0.15rem;
}
.brand-sub { text-align:center; color:#8b949e; font-size:0.82rem; margin-bottom:1.8rem; }

.g-btn {
    display:flex; align-items:center; justify-content:center; gap:10px;
    width:100%; padding:12px 16px;
    background:#fff; color:#3c4043;
    border:1.5px solid #dadce0; border-radius:10px;
    font-size:0.95rem; font-weight:600;
    cursor:pointer; text-decoration:none;
    transition:box-shadow .2s, background .15s;
    margin-bottom:6px;
}
.g-btn:hover { box-shadow:0 4px 16px rgba(0,0,0,0.35); background:#f8f9fa; }

.or-row {
    display:flex; align-items:center; gap:10px;
    color:#484f58; font-size:0.8rem; margin:16px 0;
}
.or-row::before,.or-row::after { content:''; flex:1; height:1px; background:#30363d; }
</style>
"""

# ── Main renderer ──────────────────────────────────────────────────────────────
def render_auth_page():

    # ── Handle Google OAuth callback ──────────────────────────────────────────
    params = st.query_params
    if "code" in params and not st.session_state.get("user"):
        code  = params["code"]
        state = params.get("state", "")
        if state == st.session_state.get("oauth_state", ""):
            with st.spinner("Signing in with Google..."):
                token_data = _exchange_code(code)
            if "access_token" in token_data:
                user_info = _get_google_user(token_data["access_token"])
                st.session_state["user"] = {
                    "name":    user_info.get("name", user_info.get("email","").split("@")[0]),
                    "email":   user_info.get("email", ""),
                    "picture": user_info.get("picture", ""),
                    "provider": "google",
                }
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Google sign-in failed. Please try again.")
                st.query_params.clear()
        else:
            st.query_params.clear()

    if st.session_state.get("user"):
        return True

    st.markdown(_CSS, unsafe_allow_html=True)

    _, col, _ = st.columns([0.3, 3, 0.3])
    with col:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown('<div class="brand-icon">📊</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-name">FinSage</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-sub">Global Financial Intelligence Platform</div>', unsafe_allow_html=True)

        # ── Google Sign-In Button ─────────────────────────────────────────────
        client_id = GOOGLE_CLIENT_ID()
        if client_id:
            auth_url = _google_auth_url()
            st.markdown(f'''
            <a href="{auth_url}" class="g-btn">
              <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
                   width="20" height="20"/>
              Continue with Google
            </a>''', unsafe_allow_html=True)
        else:
            st.info("⚙️ Add GOOGLE_CLIENT_ID in Streamlit Secrets to enable Google Sign-In.")

        st.markdown('<div class="or-row">or continue with email</div>', unsafe_allow_html=True)

        # ── Email / Password Tabs ─────────────────────────────────────────────
        tab_login, tab_signup, tab_reset = st.tabs(["Login", "Create Account", "Forgot Password"])

        with tab_login:
            email_l = st.text_input("Email address", key="l_email", placeholder="you@example.com")
            pass_l  = st.text_input("Password", type="password", key="l_pass", placeholder="Your password")
            if st.button("Sign In →", use_container_width=True, type="primary", key="btn_login"):
                if not email_l or not pass_l:
                    st.error("Please enter your email and password.")
                else:
                    ok, result = login_email(email_l.strip(), pass_l)
                    if ok:
                        st.session_state["user"] = result
                        st.success(f"Welcome back, {result['name']}! ✅")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(result)

        with tab_signup:
            name_s  = st.text_input("Full Name",        key="s_name",    placeholder="John Doe")
            email_s = st.text_input("Email address",    key="s_email",   placeholder="you@example.com")
            pass_s  = st.text_input("Password",         type="password", key="s_pass",    placeholder="Minimum 6 characters")
            pass_c  = st.text_input("Confirm Password", type="password", key="s_confirm", placeholder="Repeat your password")
            agree   = st.checkbox("I agree to the **Privacy Policy**", key="s_agree")

            if st.button("Create Account →", use_container_width=True, type="primary", key="btn_signup"):
                if not name_s or not email_s or not pass_s:
                    st.error("Please fill in all fields.")
                elif "@" not in email_s:
                    st.error("Please enter a valid email address.")
                elif pass_s != pass_c:
                    st.error("Passwords do not match.")
                elif not agree:
                    st.error("Please accept the Privacy Policy to continue.")
                else:
                    ok, msg = register_user(email_s.strip(), pass_s, name_s.strip())
                    if ok:
                        ok2, user = login_email(email_s.strip(), pass_s)
                        st.session_state["user"] = user
                        st.success(f"Welcome to FinSage, {name_s.split()[0]}! 🎉")
                        st.balloons()
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_reset:
            st.caption("Enter your email — we'll send you a password reset link.")
            st.info("Password reset is available for Google-authenticated accounts only. For email accounts, please create a new account.", icon="ℹ️")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;color:#484f58;font-size:0.72rem;margin-top:1rem;'>
        🔒 Secured · Data: Yahoo Finance & CoinGecko<br>For educational purposes only.
        </div>""", unsafe_allow_html=True)
