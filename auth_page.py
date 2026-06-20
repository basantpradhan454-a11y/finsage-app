"""
FinsageAI — Auth Page
Firebase Firestore for user storage + Google OAuth + Email/Password
Falls back to users.json when Firebase is not configured.
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

# ══════════════════════════════════════════════════════════════
# 0.  FIREBASE HELPER
#     Set FIREBASE_PROJECT_ID + FIREBASE_SERVICE_ACCOUNT_JSON
#     in Streamlit Secrets to enable cloud storage.
#     Without them, falls back to local users.json.
# ══════════════════════════════════════════════════════════════

def _get_secret(key: str, default: str = "") -> str:
    v = os.environ.get(key, "")
    if not v:
        try:
            v = st.secrets.get(key, "")
        except Exception:
            pass
    return v or default

def _firebase_db():
    """Return Firestore client or None."""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        # Already initialised?
        if not firebase_admin._apps:
            sa_json = _get_secret("FIREBASE_SERVICE_ACCOUNT_JSON")
            if not sa_json:
                return None
            sa_dict = json.loads(sa_json)
            cred = credentials.Certificate(sa_dict)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception:
        return None

_FIREBASE_AVAILABLE = None   # cached per-session

def _fb() -> object | None:
    global _FIREBASE_AVAILABLE
    if _FIREBASE_AVAILABLE is None:
        db = _firebase_db()
        _FIREBASE_AVAILABLE = db
    return _FIREBASE_AVAILABLE

def _users_col():
    db = _fb()
    if db is None:
        return None
    return db.collection("finsage_users")

# ── Fallback: local JSON ──────────────────────────────────────
USER_DB_FILE = "users.json"

def load_users() -> dict:
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(users: dict):
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f, indent=2)

# ── Core CRUD (Firebase-first, JSON-fallback) ─────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _read_user(email: str) -> dict | None:
    col = _users_col()
    if col is not None:
        try:
            doc = col.document(email.replace(".", "_")).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception:
            pass
    # fallback
    users = load_users()
    return users.get(email.lower().strip())

def _write_user(email: str, data: dict):
    col = _users_col()
    if col is not None:
        try:
            col.document(email.replace(".", "_")).set(data)
            return
        except Exception:
            pass
    # fallback
    users = load_users()
    users[email.lower().strip()] = data
    save_users(users)

def _update_user(email: str, fields: dict):
    col = _users_col()
    if col is not None:
        try:
            from firebase_admin import firestore
            col.document(email.replace(".", "_")).update(fields)
            return
        except Exception:
            pass
    # fallback
    users = load_users()
    key = email.lower().strip()
    if key in users:
        users[key].update(fields)
        save_users(users)

def _all_users() -> dict:
    """Return all users as {email: data} dict."""
    col = _users_col()
    if col is not None:
        try:
            docs = col.stream()
            return {d.id.replace("_", ".", 1): d.to_dict() for d in docs}
        except Exception:
            pass
    return load_users()

# ══════════════════════════════════════════════════════════════
# SESSION TOKEN  (persistent auto-login)
# ══════════════════════════════════════════════════════════════
SESSION_TOKENS_FILE = "session_tokens.json"

def _load_tokens() -> dict:
    if os.path.exists(SESSION_TOKENS_FILE):
        try:
            with open(SESSION_TOKENS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_tokens(tokens: dict):
    with open(SESSION_TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def _read_token(token: str) -> dict | None:
    """Firebase-first, JSON fallback."""
    col = _users_col()
    if col is not None:
        try:
            doc = col.parent.collection("finsage_session_tokens").document(token).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception:
            pass
    tokens = _load_tokens()
    return tokens.get(token)

def _write_token(token: str, data: dict):
    col = _users_col()
    if col is not None:
        try:
            col.parent.collection("finsage_session_tokens").document(token).set(data)
            return
        except Exception:
            pass
    tokens = _load_tokens()
    tokens[token] = data
    _save_tokens(tokens)

def _delete_token(token: str):
    col = _users_col()
    if col is not None:
        try:
            col.parent.collection("finsage_session_tokens").document(token).delete()
        except Exception:
            pass
    tokens = _load_tokens()
    tokens.pop(token, None)
    _save_tokens(tokens)

def create_session_token(email: str) -> str:
    """Create a persistent session token for the user. Returns token string."""
    import secrets as _sec
    from datetime import datetime, timedelta
    token = _sec.token_urlsafe(32)
    _write_token(token, {
        "email": email.lower().strip(),
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
    })
    return token

def resolve_session_token(token: str) -> dict | None:
    """Given a token string, return user dict if valid, else None."""
    from datetime import datetime
    data = _read_token(token)
    if not data:
        return None
    # Check expiry
    try:
        expires = datetime.fromisoformat(data["expires_at"])
        if datetime.now() > expires:
            _delete_token(token)
            return None
    except Exception:
        pass
    email = data.get("email", "")
    user = _read_user(email)
    if not user:
        return None
    return {"name": user.get("name",""), "email": email,
            "provider": user.get("provider","email"), "picture": user.get("picture")}

def delete_session_token(token: str):
    _delete_token(token)

# ── Public API ────────────────────────────────────────────────
def register_user(email: str, password: str, name: str) -> tuple:
    email = email.lower().strip()
    if _read_user(email):
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
        "user_type": st.session_state.get("user_type", ""),
        "language": st.session_state.get("user_lang", "en"),
    }
    _write_user(email, data)
    return True, "Account created successfully!"

def create_token_for_user(email: str) -> str:
    """Helper: create session token after signup."""
    return create_session_token(email.lower().strip())

def login_user(email: str, password: str) -> tuple:
    email = email.lower().strip()
    user = _read_user(email)
    if not user:
        return False, {"error": "Email not registered. Please create an account."}
    if user.get("password_hash") != hash_password(password):
        return False, {"error": "Incorrect password. Please try again."}
    _update_user(email, {"last_login": datetime.now().isoformat()})
    token = create_session_token(email)
    return True, {
        "name": user["name"],
        "email": user["email"],
        "provider": "email",
        "picture": None,
        "_session_token": token,
    }

def save_google_user(email: str, name: str, picture: str = "") -> dict:
    email = email.lower().strip()
    existing = _read_user(email)
    if not existing:
        data = {
            "name": name,
            "email": email,
            "password_hash": None,
            "created_at": datetime.now().isoformat(),
            "provider": "google",
            "picture": picture,
            "last_login": datetime.now().isoformat(),
            "user_type": st.session_state.get("user_type", ""),
            "language": st.session_state.get("user_lang", "en"),
        }
        _write_user(email, data)
    else:
        upd = {"last_login": datetime.now().isoformat(), "name": name, "picture": picture}
        if st.session_state.get("user_type"):
            upd["user_type"] = st.session_state["user_type"]
        if st.session_state.get("user_lang"):
            upd["language"] = st.session_state["user_lang"]
        _update_user(email, upd)
    token = create_session_token(email)
    return {"name": name, "email": email, "provider": "google",
            "picture": picture, "_session_token": token}

# ══════════════════════════════════════════════════════════════
# 1.  GOOGLE OAUTH
# ══════════════════════════════════════════════════════════════
GOOGLE_AUTH_URL     = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL    = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_google_login_url() -> str:
    client_id = _get_secret("GOOGLE_CLIENT_ID")
    if not client_id:
        return "#"
    redirect_uri = _get_secret(
        "GOOGLE_REDIRECT_URI",
        "https://finsage-app-mzhu9qcb5eappqtqcpah8kp.streamlit.app"
    )
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
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

def exchange_code_for_user(code: str) -> dict:
    client_id     = _get_secret("GOOGLE_CLIENT_ID")
    client_secret = _get_secret("GOOGLE_CLIENT_SECRET")
    redirect_uri  = _get_secret(
        "GOOGLE_REDIRECT_URI",
        "https://finsage-app-mzhu9qcb5eappqtqcpah8kp.streamlit.app"
    )
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
            return {"error": token_data.get("error_description", token_data["error"])}
        access_token = token_data.get("access_token")
        info_resp = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        user_info = info_resp.json()
        email   = user_info.get("email", "")
        name    = user_info.get("name", "User")
        picture = user_info.get("picture", "")
        if not email:
            return {"error": "Could not retrieve email from Google."}
        return save_google_user(email, name, picture)
    except Exception as e:
        return {"error": str(e)}

# ══════════════════════════════════════════════════════════════
# 2.  SESSION HELPERS
# ══════════════════════════════════════════════════════════════
def is_logged_in() -> bool:
    return bool(st.session_state.get("user"))

def get_current_user() -> dict:
    return st.session_state.get("user", {})

def logout():
    st.session_state.user = None
    st.session_state.ob_done = False
    st.session_state.ob_step = "language"
    st.rerun()

# ══════════════════════════════════════════════════════════════
# 3.  PRIVACY POLICY TEXT
# ══════════════════════════════════════════════════════════════
PRIVACY_POLICY_SHORT = """
**Privacy Policy Summary** (full policy below)

By creating an account you agree to the following:

- **Data collected:** name, email address, password (SHA-256 hashed — never stored in plain text), login timestamps, language preference, and user type.
- **Storage:** User data is stored securely in Firebase Firestore (cloud) or locally on the server. We do not sell your data to any third party.
- **Purpose:** Your data is used only to personalise your FinsageAI experience and save your learning progress.
- **Google Sign-In:** If you use Google login, we receive your public Google profile (name, email, profile picture). We do not access your Google Drive, Gmail, or any other Google service.
- **Educational use only:** FinsageAI is not a SEBI-registered advisor. All content is for educational purposes. We are not liable for financial decisions made using this platform.
- **Data deletion:** You may request deletion of your account and all associated data by emailing us.
- **Contact:** support@finsage.ai
"""

PRIVACY_POLICY_FULL = """
# FinsageAI — Privacy Policy

**Last updated: June 2026**

---

## 1. Who We Are

FinsageAI ("we", "our", "the platform") is an educational financial intelligence platform. We are **not** a SEBI-registered investment advisor. All content is strictly for educational and informational purposes.

---

## 2. What Data We Collect

When you create an account, we collect:

| Data | Purpose |
|------|---------|
| Full Name | Personalisation |
| Email Address | Account identity & login |
| Password (SHA-256 hash only) | Authentication — never stored in plain text |
| Login timestamps | Security & session management |
| Language preference | Platform localisation |
| User type (Trader/Investor/Student/Other) | Personalised content |
| Learning progress & quiz scores | Course progress tracking |

If you sign in with **Google**, we additionally receive your Google profile picture from your public Google account. We do **not** access Gmail, Google Drive, contacts, or any other Google service.

---

## 3. How We Use Your Data

- To authenticate you and maintain your session
- To save your course progress, quiz scores, and weak areas
- To personalise AI responses based on your language and user type
- To improve the platform (aggregated, anonymised analytics only)

We **never**:
- Sell your data to third parties
- Use your data for advertising
- Share your data with external financial institutions

---

## 4. Data Storage & Security

- User data is stored in **Firebase Firestore** (Google Cloud, Mumbai/Asia region).
- Passwords are hashed with SHA-256 before storage — the original password is never stored.
- All data transmission is encrypted via HTTPS/TLS.
- Firebase Security Rules restrict access to authorised services only.

---

## 5. Third-Party Services

| Service | Purpose | Policy |
|---------|---------|--------|
| Google OAuth | Social login | [Google Privacy Policy](https://policies.google.com/privacy) |
| Firebase / Google Cloud | Database hosting | [Firebase Privacy](https://firebase.google.com/support/privacy) |
| Groq AI | AI-powered lessons & chat | [Groq Privacy](https://groq.com/privacy-policy/) |
| yFinance / CoinGecko | Market data | Public APIs, no personal data shared |

---

## 6. Data Retention

- Your account data is retained as long as you have an active account.
- You may request deletion at any time (see Section 8).
- Anonymised usage data may be retained for platform improvement.

---

## 7. Your Rights

Under applicable data protection laws, you have the right to:
- **Access** the data we hold about you
- **Correct** inaccurate data
- **Delete** your account and all associated data
- **Withdraw consent** at any time

---

## 8. Contact & Data Deletion Requests

Email: **support@finsage.ai**

For account deletion, email us from your registered address with subject: `DELETE MY ACCOUNT`.

---

## 9. Disclaimer

FinsageAI is an **educational platform only**. We are **not** a SEBI-registered investment advisor. Nothing on this platform constitutes financial advice. Always consult a qualified financial advisor before making investment decisions. Past performance is not indicative of future results.

---

## 10. Changes to This Policy

We may update this policy periodically. Significant changes will be communicated via the platform. Continued use of FinsageAI after changes implies acceptance of the updated policy.

---

*FinsageAI — Empowering Indian investors through education.*
"""

# ══════════════════════════════════════════════════════════════
# 4.  CSS
# ══════════════════════════════════════════════════════════════
AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=Orbitron:wght@700;900&display=swap');

.auth-wrap { background: #020609; min-height: 100vh; font-family: 'Inter', sans-serif; }

.auth-logo-area {
    text-align: center; padding: 3rem 1rem 1.5rem;
}
.auth-logo-icon { font-size: 52px; margin-bottom: 8px; }
.auth-logo-name {
    font-size: 2.2rem; font-weight: 900;
    font-family: 'Orbitron', monospace;
    background: linear-gradient(90deg, #00d4ff, #6e40c9);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 0.06em;
}
.auth-logo-tag { color: #4a9eff; font-size: 0.72rem; letter-spacing: 0.15em; margin-top: 4px; }
.feature-pills { margin-top: 14px; display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; }
.pill {
    background: rgba(0,212,255,0.08); border: 1px solid rgba(0,212,255,0.2);
    color: #7dd3fc; font-size: 0.72rem; padding: 3px 10px; border-radius: 20px;
}

.auth-card {
    background: rgba(7,21,37,0.97); border: 1px solid rgba(0,212,255,0.12);
    border-radius: 16px; padding: 28px 24px; margin-bottom: 1rem;
}
.auth-title { font-size: 1.2rem; font-weight: 800; color: #e0e6f0; margin-bottom: 16px; text-align: center; }

.google-btn-wrap { margin-bottom: 16px; }
.google-btn {
    display: flex; align-items: center; justify-content: center; gap: 10px;
    background: #fff; color: #1f1f1f; text-decoration: none;
    border-radius: 10px; padding: 0.65rem 1.2rem; font-size: 0.9rem; font-weight: 600;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4); transition: box-shadow 0.2s;
}
.google-btn:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.5); }

.divider-row { display: flex; align-items: center; gap: 10px; color: #4a5568; font-size: 0.78rem; margin: 12px 0; }
.divider-line { flex: 1; height: 1px; background: #1a2744; }

.privacy-box {
    background: rgba(0,212,255,0.04); border: 1px solid rgba(0,212,255,0.12);
    border-radius: 10px; padding: 14px 16px; margin: 14px 0;
    font-size: 0.78rem; color: #8899aa; line-height: 1.6;
}
.privacy-box a { color: #4a9eff; }
.privacy-link { color: #4a9eff; cursor: pointer; text-decoration: underline; font-size: 0.78rem; }

.auth-footer {
    text-align: center; padding: 16px; font-size: 0.72rem;
    color: #4a5568; line-height: 1.7;
}
.firebase-badge {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,160,0,0.08); border: 1px solid rgba(255,160,0,0.2);
    border-radius: 20px; padding: 3px 10px; font-size: 0.68rem; color: #fbbf24;
    margin-top: 8px;
}
</style>
"""

# ══════════════════════════════════════════════════════════════
# 5.  PRIVACY POLICY PAGE
# ══════════════════════════════════════════════════════════════
def render_privacy_policy_page():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div style="max-width:780px;margin:0 auto;padding:2rem 1rem;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:2rem;">
            <span style="font-size:2rem;">🔒</span>
            <div>
                <div style="font-size:1.4rem;font-weight:800;color:#e0e6f0;">Privacy Policy</div>
                <div style="font-size:0.78rem;color:#4a9eff;">FinsageAI — Protecting your data</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    _, col, _ = st.columns([0.2, 3, 0.2])
    with col:
        st.markdown(PRIVACY_POLICY_FULL)
        st.markdown("""<div class='auth-footer'>
        🔒 Passwords are SHA-256 hashed. Firebase Firestore secures your data.<br>
        FinsageAI is for educational purposes only — not investment advice.
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 6.  MAIN AUTH PAGE  (used from onboarding step 3)
# ══════════════════════════════════════════════════════════════
def render_auth_page() -> bool:
    """Full-page auth. Returns True if authenticated."""
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

    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div class="auth-logo-area">
        <div class="auth-logo-icon">📊</div>
        <div class="auth-logo-name">FinsageAI</div>
        <div class="auth-logo-tag">STOCK · CRYPTO · FOREX · AI-POWERED</div>
        <div class="feature-pills">
            <span class="pill">✅ Stocks</span>
            <span class="pill">✅ Crypto</span>
            <span class="pill">✅ Meme Coins</span>
            <span class="pill">🎓 AI Learning</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2.2, 1])
    with col:
        _render_auth_card()
    return False

def _render_auth_card(key_prefix: str = "main"):
    """Reusable card: Google + Email login/signup + Privacy."""
    client_id     = _get_secret("GOOGLE_CLIENT_ID")
    client_secret = _get_secret("GOOGLE_CLIENT_SECRET")
    google_ok     = bool(client_id and client_secret)

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">Sign in to FinsageAI</div>', unsafe_allow_html=True)

    if google_ok:
        gurl = get_google_login_url()
        st.markdown(f"""
        <div class="google-btn-wrap">
            <a href="{gurl}" class="google-btn">
                <svg width="18" height="18" viewBox="0 0 48 48">
                    <path fill="#EA4335" d="M24 9.5c3.14 0 5.95 1.08 8.17 2.84L38.34 6.1C34.52 2.31 29.53 0 24 0 14.62 0 6.63 5.47 2.63 13.4l7.08 5.5C11.63 13.15 17.35 9.5 24 9.5z"/>
                    <path fill="#4285F4" d="M46.52 24.5c0-1.6-.14-3.14-.4-4.64H24v9.27h12.67c-.55 2.93-2.2 5.41-4.68 7.09l7.27 5.65C43.52 37.96 46.52 31.7 46.52 24.5z"/>
                    <path fill="#FBBC05" d="M9.71 28.62A14.83 14.83 0 0 1 9.5 24c0-1.6.28-3.15.71-4.62L3.13 13.9A23.93 23.93 0 0 0 0 24c0 3.87.92 7.53 2.54 10.77l7.17-6.15z"/>
                    <path fill="#34A853" d="M24 48c5.53 0 10.17-1.82 13.56-4.95l-7.27-5.65c-1.95 1.3-4.45 2.1-6.29 2.1-6.62 0-12.23-4.47-14.25-10.5l-7.17 6.15C6.6 42.58 14.62 48 24 48z"/>
                </svg>
                Continue with Google
            </a>
        </div>
        <div class="divider-row">
            <div class="divider-line"></div>or use email<div class="divider-line"></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Tabs
    tab_l, tab_s, tab_pp = st.tabs(["🔑 Login", "📝 Sign Up", "🔒 Privacy Policy"])

    with tab_l:
        with st.form(f"{key_prefix}_login", clear_on_submit=False):
            em = st.text_input("Email", placeholder="you@example.com", key=f"{key_prefix}_le")
            pw = st.text_input("Password", type="password", key=f"{key_prefix}_lp")
            if st.form_submit_button("Login →", use_container_width=True, type="primary"):
                if not em or not pw:
                    st.error("Fill in both fields.")
                else:
                    ok, res = login_user(em, pw)
                    if ok:
                        st.session_state.user = res
                        st.session_state.ob_done = True
                        # Store session token in query params so app.py can set cookie
                        _st_tok = res.get("_session_token", "")
                        if _st_tok:
                            st.query_params["fs_token"] = _st_tok
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        st.error(res.get("error", "Login failed."))

    with tab_s:
        with st.form(f"{key_prefix}_signup", clear_on_submit=True):
            nm  = st.text_input("Full Name", placeholder="Your name", key=f"{key_prefix}_nm")
            em2 = st.text_input("Email", placeholder="you@example.com", key=f"{key_prefix}_em2")
            pw2 = st.text_input("Password", type="password",
                                placeholder="Min 6 characters", key=f"{key_prefix}_pw2")
            pc  = st.text_input("Confirm Password", type="password",
                                placeholder="Repeat password", key=f"{key_prefix}_pc")
            agreed = st.checkbox(
                "I have read and agree to the [Privacy Policy](#) and Terms of Use",
                key=f"{key_prefix}_agree"
            )
            if st.form_submit_button("Create Account →", use_container_width=True, type="primary"):
                if not nm or not em2 or not pw2:
                    st.error("Fill in all fields.")
                elif pw2 != pc:
                    st.error("Passwords do not match.")
                elif not agreed:
                    st.error("Please accept the Privacy Policy to continue.")
                else:
                    ok2, msg = register_user(em2, pw2, nm)
                    if ok2:
                        _, res2 = login_user(em2, pw2)
                        st.session_state.user = res2
                        st.session_state.ob_done = True
                        # Store session token in query params so app.py can set cookie
                        _st_tok2 = res2.get("_session_token", "") if res2 else ""
                        if _st_tok2:
                            st.query_params["fs_token"] = _st_tok2
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        st.error(msg)
        # Privacy summary below signup form
        st.markdown(f"""
        <div class="privacy-box">
            🔒 <b>Your privacy matters.</b> We store only your name, email (hashed password),
            language & learning preferences — securely in Firebase Firestore.
            We never sell your data. <br>
            By signing up you agree to our
            <b>Privacy Policy</b> (see the Privacy Policy tab above for full details).<br>
            <span class="firebase-badge">🔥 Secured by Firebase</span>
        </div>
        """, unsafe_allow_html=True)

    with tab_pp:
        st.markdown(PRIVACY_POLICY_FULL)

    st.markdown("""
    <div class="auth-footer">
        🔒 Passwords are SHA-256 hashed — never stored in plain text.<br>
        🔥 User data secured by Firebase Firestore.<br>
        FinsageAI is for educational purposes only. Not investment advice.
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 7.  SIDEBAR AUTH (for main app navbar)
# ══════════════════════════════════════════════════════════════
def render_sidebar_auth():
    """Handles Google OAuth callback + sidebar login when not logged in."""
    params = st.query_params
    if "code" in params and not st.session_state.get("user"):
        with st.spinner("🔄 Signing in with Google..."):
            user = exchange_code_for_user(params["code"])
            st.query_params.clear()
            if "error" not in user:
                st.session_state.user = user
                st.session_state.ob_done = True
                st.rerun()
            else:
                st.sidebar.error(f"❌ {user['error']}")

    if st.session_state.get("user"):
        return

    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:0.6rem 0 0.9rem;">
            <div style="font-size:1.1rem;font-weight:900;color:#00d4ff;font-family:Orbitron,monospace;">
            FinsageAI</div>
            <div style="font-size:0.65rem;color:#4a9eff;letter-spacing:0.12em;margin-top:2px;">
            STOCK · CRYPTO · AI</div>
        </div>
        """, unsafe_allow_html=True)
        _render_auth_card(key_prefix="sb")

# ══════════════════════════════════════════════════════════════
# 8.  LEGACY COMPAT (privacy_policy.py imports these)
# ══════════════════════════════════════════════════════════════
def render_signup_page():
    render_auth_page()

def render_signup_with_privacy():
    render_auth_page()
