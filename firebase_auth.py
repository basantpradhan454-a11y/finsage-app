"""
FinSage — Firebase Authentication Module
Uses Firebase REST API (no SDK needed — works on Streamlit Cloud).
Handles: Email/Password signup, login, logout, token refresh.
Also uses Firestore REST API for user profiles.
"""

import os
import requests
import streamlit as st
from datetime import datetime

# ── Firebase config from Streamlit secrets / env ──────────────────────────────
def _cfg(key: str) -> str:
    try:
        return st.secrets["firebase"][key]
    except Exception:
        return os.environ.get(key, "")

FIREBASE_API_KEY       = lambda: _cfg("FIREBASE_API_KEY")
FIREBASE_PROJECT_ID    = lambda: _cfg("FIREBASE_PROJECT_ID")

# Firebase Auth REST endpoints
_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"
_FS_BASE   = "https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents"


# ── Low-level Firebase Auth calls ─────────────────────────────────────────────

def _auth_request(endpoint: str, payload: dict) -> dict:
    url = f"{_AUTH_BASE}:{endpoint}?key={FIREBASE_API_KEY()}"
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": {"message": str(e)}}


def firebase_signup(email: str, password: str) -> dict:
    """Create a new Firebase user. Returns {idToken, localId, ...} or {error}."""
    return _auth_request("signUp", {
        "email": email, "password": password, "returnSecureToken": True
    })


def firebase_login(email: str, password: str) -> dict:
    """Sign in existing Firebase user."""
    return _auth_request("signInWithPassword", {
        "email": email, "password": password, "returnSecureToken": True
    })


def firebase_refresh_token(refresh_token: str) -> dict:
    """Refresh an expired idToken."""
    url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY()}"
    try:
        r = requests.post(url, json={
            "grant_type": "refresh_token", "refresh_token": refresh_token
        }, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def firebase_send_reset_email(email: str) -> dict:
    """Send password reset email."""
    return _auth_request("sendOobCode", {
        "requestType": "PASSWORD_RESET", "email": email
    })


# ── Firestore user profile ─────────────────────────────────────────────────────

def _fs_url(uid: str) -> str:
    project = FIREBASE_PROJECT_ID()
    return f"{_FS_BASE.format(project=project)}/users/{uid}"


def save_user_profile(uid: str, id_token: str, data: dict):
    """Create/update user document in Firestore users/{uid}."""
    url = _fs_url(uid)
    # Convert python dict → Firestore fields format
    fields = {}
    for k, v in data.items():
        if isinstance(v, str):
            fields[k] = {"stringValue": v}
        elif isinstance(v, bool):
            fields[k] = {"booleanValue": v}
        elif isinstance(v, int):
            fields[k] = {"integerValue": str(v)}
        elif isinstance(v, float):
            fields[k] = {"doubleValue": v}
    payload = {"fields": fields}
    headers = {"Authorization": f"Bearer {id_token}"}
    try:
        r = requests.patch(url, json=payload, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_user_profile(uid: str, id_token: str) -> dict:
    """Fetch user profile from Firestore."""
    url = _fs_url(uid)
    headers = {"Authorization": f"Bearer {id_token}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        if "fields" not in data:
            return {}
        # Convert Firestore format → plain dict
        out = {}
        for k, v in data["fields"].items():
            for vtype, val in v.items():
                out[k] = val
        return out
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
    """Store Firebase auth result in session_state."""
    st.session_state["fb_token"]   = result.get("idToken", "")
    st.session_state["fb_refresh"] = result.get("refreshToken", "")
    st.session_state["fb_uid"]     = result.get("localId", "")
    st.session_state["fb_user"]    = {
        "uid":   result.get("localId", ""),
        "email": result.get("email", ""),
        "name":  name or result.get("displayName") or result.get("email", "").split("@")[0],
    }


# ── Auth UI ────────────────────────────────────────────────────────────────────

def render_auth_page():
    """Full-screen Login / Signup page with Firebase backend."""
    st.markdown("""
    <style>
    .auth-wrap { max-width:440px; margin:3rem auto 0; }
    .auth-card {
        background:rgba(22,27,34,0.97);
        border:1px solid #30363d; border-radius:18px;
        padding:2.5rem 2.2rem;
        box-shadow:0 12px 48px rgba(0,0,0,0.7);
    }
    .auth-logo  { text-align:center; font-size:2.5rem; margin-bottom:0.2rem; }
    .auth-brand { text-align:center; font-size:1.6rem; font-weight:800;
                  background:linear-gradient(90deg,#58a6ff,#a78bfa);
                  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                  margin-bottom:0.1rem; }
    .auth-sub   { text-align:center; color:#8b949e; font-size:0.83rem; margin-bottom:1.8rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-wrap"><div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-logo">📊</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-brand">FinSage</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Global Financial Intelligence Platform</div>', unsafe_allow_html=True)

    tab_login, tab_signup, tab_reset = st.tabs(["🔑 Login", "✨ Sign Up", "🔓 Forgot Password"])

    # ── LOGIN ─────────────────────────────────────────────────────────────────
    with tab_login:
        email_l = st.text_input("Email", key="l_email", placeholder="you@example.com")
        pass_l  = st.text_input("Password", type="password", key="l_pass", placeholder="••••••••")

        if st.button("Login →", use_container_width=True, type="primary", key="btn_login"):
            if not email_l or not pass_l:
                st.error("Email aur password dono bharo.")
            else:
                with st.spinner("Logging in..."):
                    result = firebase_login(email_l.strip(), pass_l)
                if "idToken" in result:
                    _store_session(result)
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    msg = result.get("error", {}).get("message", "Login failed")
                    err_map = {
                        "EMAIL_NOT_FOUND": "❌ Yeh email registered nahi hai.",
                        "INVALID_PASSWORD": "❌ Password galat hai.",
                        "INVALID_LOGIN_CREDENTIALS": "❌ Email ya password galat hai.",
                        "USER_DISABLED": "❌ Account disable kar diya gaya hai.",
                        "TOO_MANY_ATTEMPTS_TRY_LATER": "⚠️ Bahut zyada attempts. Thodi der baad try karo.",
                    }
                    st.error(err_map.get(msg, f"❌ {msg}"))

    # ── SIGNUP ────────────────────────────────────────────────────────────────
    with tab_signup:
        name_s   = st.text_input("Full Name", key="s_name",    placeholder="Basant Pradhan")
        email_s  = st.text_input("Email",     key="s_email",   placeholder="you@example.com")
        pass_s   = st.text_input("Password",  type="password", key="s_pass",    placeholder="Min 8 characters")
        pass_c   = st.text_input("Confirm",   type="password", key="s_confirm", placeholder="Repeat password")

        plan_s = st.selectbox("Plan", ["🆓 Free Plan", "⭐ Pro Plan (₹299/mo)", "💎 Premium Plan (₹599/mo)"], key="s_plan")

        agree = st.checkbox("Maine **Privacy Policy** padhi aur agree karta/karti hoon ✅", key="s_agree")
        if st.button("📄 Privacy Policy dekho", key="pp_btn_signup", use_container_width=False):
            st.session_state["show_privacy"] = True
            st.rerun()

        if st.button("Create Account →", use_container_width=True, type="primary", key="btn_signup"):
            if not name_s or not email_s or not pass_s:
                st.error("Sab fields bharna zaroori hai.")
            elif "@" not in email_s:
                st.error("Valid email dalo.")
            elif len(pass_s) < 8:
                st.error("Password min 8 characters ka hona chahiye.")
            elif pass_s != pass_c:
                st.error("Passwords match nahi kar rahe.")
            elif not agree:
                st.error("Privacy Policy agree karna zaroori hai.")
            else:
                with st.spinner("Account bana rahe hain..."):
                    result = firebase_signup(email_s.strip(), pass_s)
                if "idToken" in result:
                    _store_session(result, name=name_s.strip())
                    plan_clean = plan_s.split("(")[0].strip()
                    save_user_profile(result["localId"], result["idToken"], {
                        "name": name_s.strip(),
                        "email": email_s.strip(),
                        "plan": plan_clean,
                        "joined": datetime.now().strftime("%Y-%m-%d"),
                        "stripe_customer_id": "",
                    })
                    st.success(f"🎉 Welcome, {name_s.split()[0]}! Account ready hai.")
                    st.balloons()
                    st.rerun()
                else:
                    msg = result.get("error", {}).get("message", "Signup failed")
                    err_map = {
                        "EMAIL_EXISTS": "❌ Yeh email pehle se registered hai. Login karo.",
                        "WEAK_PASSWORD : Password should be at least 6 characters": "❌ Password kam se kam 6 characters ka hona chahiye.",
                        "INVALID_EMAIL": "❌ Valid email address dalo.",
                    }
                    st.error(err_map.get(msg, f"❌ {msg}"))

    # ── FORGOT PASSWORD ───────────────────────────────────────────────────────
    with tab_reset:
        st.markdown("<p style='color:#8b949e;font-size:0.85rem;'>Apna registered email dalo — hum reset link bhejenge.</p>", unsafe_allow_html=True)
        email_r = st.text_input("Email", key="r_email", placeholder="you@example.com")
        if st.button("Send Reset Link 📧", use_container_width=True, type="primary", key="btn_reset"):
            if not email_r or "@" not in email_r:
                st.error("Valid email dalo.")
            else:
                with st.spinner("Email bhej rahe hain..."):
                    result = firebase_send_reset_email(email_r.strip())
                if result.get("email"):
                    st.success(f"✅ Reset link bhej diya: **{email_r}**. Inbox check karo (spam bhi dekho).")
                else:
                    msg = result.get("error", {}).get("message", "Failed")
                    st.error(f"❌ {msg}")

    st.markdown('</div></div>', unsafe_allow_html=True)
