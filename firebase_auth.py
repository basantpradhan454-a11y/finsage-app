"""
FinSage — Firebase Authentication Module
Supports: Email/Password + Google OAuth via Firebase REST API
Works on Streamlit Cloud (no SDK needed).
"""

import os
import requests
import streamlit as st
from datetime import datetime


# ── Firebase config ────────────────────────────────────────────────────────────
def _cfg(key: str) -> str:
    try:
        return st.secrets["firebase"][key]
    except Exception:
        return os.environ.get(key, "")

FIREBASE_API_KEY    = lambda: _cfg("FIREBASE_API_KEY")
FIREBASE_PROJECT_ID = lambda: _cfg("FIREBASE_PROJECT_ID")

_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"
_FS_BASE   = "https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents"


# ── Firebase Auth REST ─────────────────────────────────────────────────────────

def _auth_request(endpoint: str, payload: dict) -> dict:
    url = f"{_AUTH_BASE}:{endpoint}?key={FIREBASE_API_KEY()}"
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": {"message": str(e)}}


def firebase_signup(email: str, password: str) -> dict:
    return _auth_request("signUp", {
        "email": email, "password": password, "returnSecureToken": True
    })


def firebase_login(email: str, password: str) -> dict:
    return _auth_request("signInWithPassword", {
        "email": email, "password": password, "returnSecureToken": True
    })


def firebase_google_signin(id_token: str) -> dict:
    """Sign in with Google ID token via Firebase."""
    return _auth_request("signInWithIdp", {
        "requestUri": "http://localhost",
        "postBody": f"id_token={id_token}&providerId=google.com",
        "returnSecureToken": True,
        "returnIdpCredential": True,
    })


def firebase_send_reset_email(email: str) -> dict:
    return _auth_request("sendOobCode", {
        "requestType": "PASSWORD_RESET", "email": email
    })


# ── Firestore profile ──────────────────────────────────────────────────────────

def _fs_url(uid: str) -> str:
    return f"{_FS_BASE.format(project=FIREBASE_PROJECT_ID())}/users/{uid}"


def save_user_profile(uid: str, id_token: str, data: dict):
    fields = {}
    for k, v in data.items():
        if isinstance(v, str):   fields[k] = {"stringValue": v}
        elif isinstance(v, bool): fields[k] = {"booleanValue": v}
        elif isinstance(v, int):  fields[k] = {"integerValue": str(v)}
        elif isinstance(v, float):fields[k] = {"doubleValue": v}
    try:
        requests.patch(_fs_url(uid), json={"fields": fields},
                       headers={"Authorization": f"Bearer {id_token}"}, timeout=10)
    except Exception:
        pass


def get_user_profile(uid: str, id_token: str) -> dict:
    try:
        r = requests.get(_fs_url(uid),
                         headers={"Authorization": f"Bearer {id_token}"}, timeout=10)
        data = r.json()
        if "fields" not in data:
            return {}
        return {k: list(v.values())[0] for k, v in data["fields"].items()}
    except Exception:
        return {}


# ── Session helpers ────────────────────────────────────────────────────────────

def is_logged_in() -> bool:
    return bool(st.session_state.get("fb_user"))


def get_current_user() -> dict | None:
    return st.session_state.get("fb_user")


def logout():
    for key in ["fb_user", "fb_token", "fb_refresh", "fb_uid"]:
        st.session_state.pop(key, None)
    st.rerun()


def _store_session(result: dict, name: str = ""):
    st.session_state["fb_token"]   = result.get("idToken", "")
    st.session_state["fb_refresh"] = result.get("refreshToken", "")
    st.session_state["fb_uid"]     = result.get("localId", "")
    st.session_state["fb_user"]    = {
        "uid":   result.get("localId", ""),
        "email": result.get("email", ""),
        "name":  name or result.get("displayName") or result.get("email", "").split("@")[0],
    }


# ── Error message mapping ──────────────────────────────────────────────────────
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


# ── Auth UI ────────────────────────────────────────────────────────────────────

def render_auth_page():
    """Full-screen Login / Signup with Email+Password and Google OAuth."""

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }

    .auth-wrap { max-width: 460px; margin: 2.5rem auto 0; }
    .auth-card {
        background: rgba(22, 27, 34, 0.97);
        border: 1px solid #30363d;
        border-radius: 20px;
        padding: 2.5rem 2.2rem 2rem;
        box-shadow: 0 16px 56px rgba(0,0,0,0.7);
    }
    .auth-logo  { text-align: center; font-size: 2.6rem; margin-bottom: 0.2rem; }
    .auth-brand {
        text-align: center; font-size: 1.7rem; font-weight: 800;
        background: linear-gradient(90deg, #58a6ff, #a78bfa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.15rem;
    }
    .auth-sub { text-align: center; color: #8b949e; font-size: 0.82rem; margin-bottom: 1.6rem; }

    .divider {
        display: flex; align-items: center; gap: 0.8rem;
        color: #484f58; font-size: 0.78rem; margin: 1rem 0;
    }
    .divider::before, .divider::after {
        content: ''; flex: 1; height: 1px; background: #30363d;
    }

    /* Google button */
    .g-btn {
        display: flex; align-items: center; justify-content: center; gap: 0.6rem;
        width: 100%; padding: 0.65rem 1rem;
        background: #fff; color: #3c4043;
        border: 1px solid #dadce0; border-radius: 10px;
        font-size: 0.9rem; font-weight: 600; cursor: pointer;
        transition: box-shadow 0.2s;
        text-decoration: none;
    }
    .g-btn:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.25); }
    .g-btn img { width: 20px; height: 20px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-wrap"><div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-logo">📊</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-brand">FinSage</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Global Financial Intelligence Platform</div>', unsafe_allow_html=True)

    # ── Google Sign-In button ─────────────────────────────────────────────────
    google_client_id = _cfg("GOOGLE_CLIENT_ID")
    auth_domain      = f"finsage-d6c96.firebaseapp.com"
    redirect_uri     = _cfg("REDIRECT_URI") or "https://finsage-app-mzhu9qcb5eappqtqcpah8kp.streamlit.app/"

    # Use Google's OAuth2 endpoint for the popup flow
    google_oauth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={google_client_id}"
        "&response_type=token"
        f"&redirect_uri={redirect_uri}"
        "&scope=openid%20email%20profile"
        "&prompt=select_account"
    ) if google_client_id else ""

    # Simpler: Firebase hosted UI (works without extra setup)
    firebase_ui_url = f"https://{auth_domain}/__/auth/handler"

    st.markdown("""
    <a href="https://accounts.google.com/o/oauth2/v2/auth?response_type=token&scope=openid%20email%20profile&redirect_uri=urn:ietf:wg:oauth:2.0:oob&client_id=placeholder" 
       class="g-btn" style="pointer-events:none;opacity:0.5;" title="Coming soon — enable Google provider in Firebase console first">
        <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" />
        Continue with Google
    </a>
    <p style="text-align:center;color:#484f58;font-size:0.72rem;margin-top:0.4rem;">
        ⚙️ Enable Google provider in Firebase Console → Authentication → Sign-in methods
    </p>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider">or continue with email</div>', unsafe_allow_html=True)

    # ── Tabs: Login / Sign Up / Forgot Password ───────────────────────────────
    tab_login, tab_signup, tab_reset = st.tabs(["Login", "Create Account", "Forgot Password"])

    # LOGIN
    with tab_login:
        email_l = st.text_input("Email address", key="l_email", placeholder="you@example.com")
        pass_l  = st.text_input("Password", type="password", key="l_pass", placeholder="Enter your password")

        if st.button("Sign In →", use_container_width=True, type="primary", key="btn_login"):
            if not email_l or not pass_l:
                st.error("Please enter your email and password.")
            else:
                with st.spinner("Signing in..."):
                    result = firebase_login(email_l.strip(), pass_l)
                if "idToken" in result:
                    _store_session(result)
                    st.success("Welcome back! ✅")
                    st.rerun()
                else:
                    msg = result.get("error", {}).get("message", "Login failed.")
                    st.error(_ERR.get(msg, f"Error: {msg}"))

    # SIGN UP
    with tab_signup:
        name_s  = st.text_input("Full Name",        key="s_name",    placeholder="John Doe")
        email_s = st.text_input("Email address",    key="s_email",   placeholder="you@example.com")
        pass_s  = st.text_input("Password",         type="password", key="s_pass",    placeholder="Minimum 8 characters")
        pass_c  = st.text_input("Confirm Password", type="password", key="s_confirm", placeholder="Repeat your password")

        agree = st.checkbox("I have read and agree to the **Privacy Policy**", key="s_agree")
        if st.button("📄 View Privacy Policy", key="pp_btn_signup"):
            st.session_state["show_privacy"] = True
            st.rerun()

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
            else:
                with st.spinner("Creating your account..."):
                    result = firebase_signup(email_s.strip(), pass_s)
                if "idToken" in result:
                    _store_session(result, name=name_s.strip())
                    save_user_profile(result["localId"], result["idToken"], {
                        "name":  name_s.strip(),
                        "email": email_s.strip(),
                        "plan":  "Free",
                        "joined": datetime.now().strftime("%Y-%m-%d"),
                        "stripe_customer_id": "",
                    })
                    st.success(f"Welcome to FinSage, {name_s.split()[0]}! 🎉")
                    st.balloons()
                    st.rerun()
                else:
                    msg = result.get("error", {}).get("message", "Signup failed.")
                    st.error(_ERR.get(msg, f"Error: {msg}"))

    # FORGOT PASSWORD
    with tab_reset:
        st.markdown("<p style='color:#8b949e;font-size:0.85rem;'>Enter your registered email — we'll send you a reset link.</p>", unsafe_allow_html=True)
        email_r = st.text_input("Email address", key="r_email", placeholder="you@example.com")
        if st.button("Send Reset Link 📧", use_container_width=True, type="primary", key="btn_reset"):
            if not email_r or "@" not in email_r:
                st.error("Please enter a valid email address.")
            else:
                with st.spinner("Sending reset email..."):
                    result = firebase_send_reset_email(email_r.strip())
                if result.get("email"):
                    st.success(f"Reset link sent to **{email_r}**. Check your inbox (and spam folder).")
                else:
                    msg = result.get("error", {}).get("message", "Failed to send reset email.")
                    st.error(f"Error: {msg}")

    st.markdown('</div></div>', unsafe_allow_html=True)
