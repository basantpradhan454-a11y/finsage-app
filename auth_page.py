"""
FinSage — Authentication Page
Firebase Email/Password + Google Sign-In (via Firebase redirect)
All text in English.
"""

import streamlit as st
import requests
import os
import time
from datetime import datetime


# ── Firebase config ────────────────────────────────────────────────────────────
def _cfg(key: str) -> str:
    try:
        return st.secrets["firebase"][key]
    except Exception:
        return os.environ.get(key, "")

FIREBASE_API_KEY    = lambda: _cfg("FIREBASE_API_KEY")
FIREBASE_PROJECT_ID = lambda: _cfg("FIREBASE_PROJECT_ID")
AUTH_DOMAIN         = lambda: f"{FIREBASE_PROJECT_ID()}.firebaseapp.com"

_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"
_FS_BASE   = "https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents"

# ── Error map ─────────────────────────────────────────────────────────────────
_ERR = {
    "EMAIL_NOT_FOUND":            "No account found with this email.",
    "INVALID_PASSWORD":           "Incorrect password. Please try again.",
    "INVALID_LOGIN_CREDENTIALS":  "Invalid email or password.",
    "USER_DISABLED":              "This account has been disabled.",
    "TOO_MANY_ATTEMPTS_TRY_LATER":"Too many attempts. Please try again later.",
    "EMAIL_EXISTS":               "An account with this email already exists. Please log in.",
    "WEAK_PASSWORD : Password should be at least 6 characters": "Password must be at least 6 characters.",
    "INVALID_EMAIL":              "Please enter a valid email address.",
}


# ── Firebase REST calls ────────────────────────────────────────────────────────
def _auth_req(endpoint: str, payload: dict) -> dict:
    url = f"{_AUTH_BASE}:{endpoint}?key={FIREBASE_API_KEY()}"
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": {"message": str(e)}}


def firebase_signup(email: str, password: str) -> dict:
    return _auth_req("signUp", {"email": email, "password": password, "returnSecureToken": True})


def firebase_login(email: str, password: str) -> dict:
    return _auth_req("signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})


def firebase_reset(email: str) -> dict:
    return _auth_req("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email})


def firebase_google_token(id_token: str) -> dict:
    """Exchange Google ID token → Firebase session."""
    return _auth_req("signInWithIdp", {
        "requestUri": "http://localhost",
        "postBody": f"id_token={id_token}&providerId=google.com",
        "returnSecureToken": True,
        "returnIdpCredential": True,
    })


# ── Firestore ─────────────────────────────────────────────────────────────────
def save_user_profile(uid: str, id_token: str, data: dict):
    url = f"{_FS_BASE.format(project=FIREBASE_PROJECT_ID())}/users/{uid}"
    fields = {}
    for k, v in data.items():
        if isinstance(v, str):    fields[k] = {"stringValue": v}
        elif isinstance(v, bool): fields[k] = {"booleanValue": v}
        elif isinstance(v, int):  fields[k] = {"integerValue": str(v)}
    try:
        requests.patch(url, json={"fields": fields},
                       headers={"Authorization": f"Bearer {id_token}"}, timeout=10)
    except Exception:
        pass


# ── Session helpers ────────────────────────────────────────────────────────────
def _store(result: dict, name: str = ""):
    st.session_state["fb_token"]   = result.get("idToken", "")
    st.session_state["fb_refresh"] = result.get("refreshToken", "")
    st.session_state["fb_uid"]     = result.get("localId", "")
    display = name or result.get("displayName") or result.get("email", "").split("@")[0]
    st.session_state["user"] = {
        "uid":   result.get("localId", ""),
        "email": result.get("email", ""),
        "name":  display,
    }


def is_logged_in() -> bool:
    return bool(st.session_state.get("user"))


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def logout():
    for k in ["user", "fb_token", "fb_refresh", "fb_uid"]:
        st.session_state.pop(k, None)
    st.rerun()


# ── CSS ────────────────────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="manage-app-button"], .stDeployButton { display: none !important; }

body { background: #0d1117; }

.auth-shell {
    max-width: 420px;
    margin: 2rem auto 0;
}
.auth-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 2.2rem 2rem 1.8rem;
    box-shadow: 0 16px 48px rgba(0,0,0,0.6);
}
.brand-icon  { text-align:center; font-size:2.8rem; margin-bottom:0.2rem; }
.brand-name  {
    text-align:center; font-size:1.75rem; font-weight:800;
    background: linear-gradient(135deg,#58a6ff,#a78bfa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:0.1rem;
}
.brand-sub   { text-align:center; color:#8b949e; font-size:0.8rem; margin-bottom:1.5rem; }

.g-btn {
    display:flex; align-items:center; justify-content:center; gap:10px;
    width:100%; padding:11px 16px;
    background:#fff; color:#3c4043;
    border:1.5px solid #dadce0; border-radius:10px;
    font-size:0.92rem; font-weight:600;
    cursor:pointer; transition:box-shadow .2s, background .2s;
    text-decoration:none; margin-bottom:4px;
}
.g-btn:hover { box-shadow:0 3px 14px rgba(0,0,0,0.3); background:#f8f9fa; }
.g-icon { width:20px; height:20px; }

.or-row {
    display:flex; align-items:center; gap:10px;
    color:#484f58; font-size:0.78rem; margin:14px 0;
}
.or-row::before,.or-row::after { content:''; flex:1; height:1px; background:#30363d; }
</style>
"""


# ── Main renderer ──────────────────────────────────────────────────────────────
def render_auth_page():

    # Handle Google Sign-In callback (credential in query params)
    params = st.query_params
    if "credential" in params and not st.session_state.get("user"):
        with st.spinner("Signing in with Google..."):
            result = firebase_google_token(params["credential"])
        if "idToken" in result:
            name = result.get("displayName") or result.get("email","").split("@")[0]
            _store(result, name=name)
            save_user_profile(result["localId"], result["idToken"], {
                "name": name, "email": result.get("email",""),
                "plan": "Free", "joined": datetime.now().strftime("%Y-%m-%d"),
                "provider": "google",
            })
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Google sign-in failed. Please try again.")
            st.query_params.clear()

    if st.session_state.get("user"):
        return True

    api_key    = FIREBASE_API_KEY()
    project_id = FIREBASE_PROJECT_ID()
    auth_domain = AUTH_DOMAIN()

    st.markdown(_CSS, unsafe_allow_html=True)

    # Google Sign-In handled via Firebase console redirect

    # ── Layout ─────────────────────────────────────────────────────────────────
    _, col, _ = st.columns([0.5, 3, 0.5])
    with col:
        st.markdown('<div class="auth-shell"><div class="auth-card">', unsafe_allow_html=True)
        st.markdown('<div class="brand-icon">📊</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-name">FinSage</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-sub">Global Financial Intelligence Platform</div>', unsafe_allow_html=True)

        # Google button — coming soon (enable in Firebase Console → Authentication → Google)
        st.markdown("""
        <div style='background:#1c2128;border:1px solid #30363d;border-radius:10px;
                    padding:12px;text-align:center;color:#8b949e;font-size:0.82rem;margin-bottom:4px;'>
            🔒 Google Sign-In — Enable Google provider in Firebase Console to activate
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="or-row">or sign in with email</div>', unsafe_allow_html=True)

        # Tabs
        tab_login, tab_signup, tab_reset = st.tabs(["Login", "Create Account", "Forgot Password"])

        # ── LOGIN ──────────────────────────────────────────────────────────────
        with tab_login:
            email_l = st.text_input("Email address", key="l_email", placeholder="you@example.com")
            pass_l  = st.text_input("Password", type="password", key="l_pass", placeholder="Enter your password")
            if st.button("Sign In →", use_container_width=True, type="primary", key="btn_login"):
                if not email_l or not pass_l:
                    st.error("Please enter your email and password.")
                elif not api_key:
                    st.error("Firebase not configured yet.")
                else:
                    with st.spinner("Signing in..."):
                        res = firebase_login(email_l.strip(), pass_l)
                    if "idToken" in res:
                        _store(res)
                        st.success("Welcome back! ✅")
                        st.rerun()
                    else:
                        msg = res.get("error", {}).get("message", "Login failed.")
                        st.error(_ERR.get(msg, f"Error: {msg}"))

        # ── SIGN UP ────────────────────────────────────────────────────────────
        with tab_signup:
            name_s  = st.text_input("Full Name",        key="s_name",    placeholder="John Doe")
            email_s = st.text_input("Email address",    key="s_email",   placeholder="you@example.com")
            pass_s  = st.text_input("Password",         type="password", key="s_pass",    placeholder="Minimum 8 characters")
            pass_c  = st.text_input("Confirm Password", type="password", key="s_confirm", placeholder="Repeat your password")
            agree   = st.checkbox("I agree to the **Privacy Policy**", key="s_agree")

            if st.button("Create Account →", use_container_width=True, type="primary", key="btn_signup"):
                if not name_s or not email_s or not pass_s:
                    st.error("Please fill in all fields.")
                elif "@" not in email_s:
                    st.error("Please enter a valid email address.")
                elif len(pass_s) < 8:
                    st.error("Password must be at least 8 characters.")
                elif pass_s != pass_c:
                    st.error("Passwords do not match.")
                elif not agree:
                    st.error("Please accept the Privacy Policy to continue.")
                elif not api_key:
                    st.error("Firebase not configured yet.")
                else:
                    with st.spinner("Creating your account..."):
                        res = firebase_signup(email_s.strip(), pass_s)
                    if "idToken" in res:
                        _store(res, name=name_s.strip())
                        save_user_profile(res["localId"], res["idToken"], {
                            "name": name_s.strip(), "email": email_s.strip(),
                            "plan": "Free", "joined": datetime.now().strftime("%Y-%m-%d"),
                            "provider": "email",
                        })
                        st.success(f"Welcome to FinSage, {name_s.split()[0]}! 🎉")
                        st.balloons()
                        st.rerun()
                    else:
                        msg = res.get("error", {}).get("message", "Signup failed.")
                        st.error(_ERR.get(msg, f"Error: {msg}"))

        # ── FORGOT PASSWORD ────────────────────────────────────────────────────
        with tab_reset:
            st.caption("Enter your registered email — we'll send you a password reset link.")
            email_r = st.text_input("Email address", key="r_email", placeholder="you@example.com")
            if st.button("Send Reset Link 📧", use_container_width=True, type="primary", key="btn_reset"):
                if not email_r or "@" not in email_r:
                    st.error("Please enter a valid email address.")
                elif not api_key:
                    st.error("Firebase not configured yet.")
                else:
                    with st.spinner("Sending reset email..."):
                        res = firebase_reset(email_r.strip())
                    if res.get("email"):
                        st.success(f"Reset link sent to **{email_r}**. Check your inbox (and spam folder).")
                    else:
                        msg = res.get("error", {}).get("message", "Failed.")
                        st.error(f"Error: {msg}")

        st.markdown('</div></div>', unsafe_allow_html=True)

        st.markdown("""
        <div style='text-align:center;color:#484f58;font-size:0.72rem;margin-top:1rem;'>
        🔒 Secured by Firebase · Data: Yahoo Finance & CoinGecko<br>
        For educational purposes only — not financial advice.
        </div>
        """, unsafe_allow_html=True)
