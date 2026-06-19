"""
FinsageAI — Privacy Policy & Signup Page
"""
import streamlit as st
from config import LOGO_URL, APP_NAME

def render_privacy_policy():
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.95),rgba(0,15,30,0.9));
    border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1.2rem;">
        <div style="display:flex;align-items:center;gap:0.9rem;">
            <img src="{LOGO_URL}" style="height:48px;border-radius:10px;">
            <div>
                <div style="font-size:1.15rem;font-weight:800;color:#00d4ff;
                font-family:Orbitron,monospace;">🔒 Privacy Policy</div>
                <div style="color:#4a9eff;font-size:0.75rem;">
                {APP_NAME} — Effective June 2026
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
## Privacy Policy — {APP_NAME}

**Last Updated:** June 13, 2026 | **Version:** 1.0

---

### 1. Introduction
Welcome to **{APP_NAME}** ("we", "our", "the platform"). This Privacy Policy explains how we collect,
use, and protect your information when you use our financial intelligence platform.

By using {APP_NAME}, you agree to the collection and use of information as described in this policy.

---

### 2. Information We Collect

**2.1 Information You Provide**
- **Account Registration:** Email address, display name (optional)
- **Google OAuth:** If you sign in with Google, we receive your Google profile name and email
- **Community Reviews:** Any ratings or comments you voluntarily submit
- **Trade Sharing:** Profit/loss data you voluntarily share with the community

**2.2 Automatically Collected Data**
- Usage analytics (pages visited, features used)
- Session timestamps
- Device type (mobile/desktop) — for UI optimization only
- No IP addresses stored permanently

**2.3 What We Do NOT Collect**
- ❌ Passwords (stored as salted hashes if using email auth)
- ❌ Financial account details or brokerage credentials
- ❌ Payment information
- ❌ Location data
- ❌ Personal identification numbers (PAN, Aadhaar, SSN)

---

### 3. How We Use Your Information

| Purpose | Data Used | Basis |
|---------|-----------|-------|
| Account authentication | Email | Contractual |
| Personalized analysis history | Session data | Legitimate interest |
| Community features (ratings) | Name, review text | Consent |
| Platform improvements | Anonymous usage stats | Legitimate interest |
| Admin moderation | Email | Legitimate interest |

---

### 4. Data Sharing & Third Parties

**We DO NOT sell your personal data.**

We use the following third-party services:
- **Google OAuth** (authentication) — Google Privacy Policy applies
- **Yahoo Finance / yfinance** (market data) — data is publicly available
- **CoinGecko API** (crypto data) — no personal data shared
- **TradingView** (charts) — embedded widgets, TradingView's policy applies
- **Streamlit Cloud** (hosting) — Streamlit's privacy policy applies

---

### 5. Data Security

- All data transmission is encrypted via HTTPS/TLS
- Authentication tokens are stored in secure, httpOnly session cookies
- We apply principle of least privilege for all data access
- Regular security reviews of third-party integrations

---

### 6. Your Rights

You have the right to:
- ✅ **Access** your personal data
- ✅ **Correct** inaccurate information
- ✅ **Delete** your account and associated data
- ✅ **Withdraw consent** at any time
- ✅ **Data portability** — export your data on request

To exercise these rights, contact: **basantpradhan454@gmail.com**

---

### 7. Cookies & Local Storage

We use minimal cookies for:
- Session management (essential — cannot be disabled)
- User preferences (UI theme, layout)

We do NOT use tracking cookies or advertising cookies.

---

### 8. Financial Data Disclaimer

> ⚠️ {APP_NAME} provides market data and analysis for **educational purposes only**.
> We are NOT a SEBI-registered investment advisor. No content on this platform
> constitutes investment advice, a recommendation to buy or sell securities,
> or a guarantee of financial returns.
>
> All analysis is generated from publicly available data (Yahoo Finance, CoinGecko).
> Past performance is not indicative of future results.
> Trade sharing features display user-reported data — not verified by {APP_NAME}.

---

### 9. Children's Privacy

{APP_NAME} is not intended for users under 18 years of age. We do not knowingly collect
data from minors. If you believe a minor has provided us data, contact us immediately.

---

### 10. Changes to This Policy

We may update this policy periodically. Significant changes will be notified via:
- In-app banner notification
- Email to registered users

Continued use after changes constitutes acceptance.

---

### 11. Contact Us

**{APP_NAME} Support**
📧 basantpradhan454@gmail.com
🌐 Platform: FinsageAI Dashboard

---

*This privacy policy was last reviewed on June 13, 2026.*
    """)

    st.markdown("""
    <div style="background:rgba(0,20,40,0.7);border:1px solid rgba(0,212,255,0.15);
    border-radius:8px;padding:0.8rem 1rem;margin-top:1rem;font-size:0.78rem;color:#8b949e;">
    By continuing to use FinsageAI, you acknowledge that you have read and understood this Privacy Policy.
    </div>
    """, unsafe_allow_html=True)


def render_signup_page():
    """Standalone signup/register page."""
    from auth_page import render_sidebar_auth
    st.markdown(f"""
    <div style="max-width:480px;margin:2rem auto;">
    <div style="text-align:center;margin-bottom:1.5rem;">
        <img src="{LOGO_URL}" style="height:90px;border-radius:16px;
        box-shadow:0 0 30px rgba(0,212,255,0.3);margin-bottom:1rem;">
        <div style="font-size:1.6rem;font-weight:900;color:#00d4ff;
        font-family:Orbitron,monospace;letter-spacing:0.05em;">FinsageAI</div>
        <div style="color:#4a9eff;font-size:0.85rem;margin-top:0.3rem;">
        STOCK · CRYPTO · MEME COIN ANALYSIS
        </div>
        <div style="color:#8b949e;font-size:0.8rem;margin-top:0.5rem;">
        Create your free account to save analysis history and join the community
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    render_sidebar_auth()

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;font-size:0.78rem;color:#8b949e;">
    By creating an account you agree to our
    <span style="color:#4a9eff;">Terms of Service</span> and
    <span style="color:#4a9eff;">Privacy Policy</span>.
    <br>FinsageAI is for educational purposes only. Not financial advice.
    </div>
    """, unsafe_allow_html=True)


def render_signup_with_privacy():
    """
    New combined Sign Up page — shows signup form on the left and
    Privacy Policy on the right. Accessible from the 3-dots menu.
    """
    from auth_page import render_sidebar_auth

    # ── Page Header ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,15,30,0.93));
    border:1px solid rgba(0,212,255,0.22);border-radius:16px;
    padding:1.4rem 1.8rem;margin-bottom:1.5rem;
    box-shadow:0 0 40px rgba(0,212,255,0.07),inset 0 1px 0 rgba(255,255,255,0.04);">
        <div style="display:flex;align-items:center;gap:1rem;">
            <img src="{LOGO_URL}" style="height:60px;border-radius:12px;
            box-shadow:0 0 20px rgba(0,212,255,0.35);">
            <div>
                <div style="font-size:1.35rem;font-weight:900;color:#00d4ff;
                font-family:Orbitron,monospace;letter-spacing:0.06em;">
                📝 Create Your Free Account
                </div>
                <div style="color:#4a9eff;font-size:0.78rem;margin-top:0.2rem;
                letter-spacing:0.1em;font-family:Orbitron,monospace;">
                {APP_NAME} — FREE · AI-POWERED · NO CREDIT CARD
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Two-column layout ──────────────────────────────────────────────────
    col_signup, col_privacy = st.columns([1, 1], gap="large")

    with col_signup:
        # Signup form card
        st.markdown("""
        <div style="background:linear-gradient(160deg,rgba(0,20,45,0.85),rgba(5,12,30,0.9));
        border:1px solid rgba(0,212,255,0.18);border-radius:14px;padding:1.4rem 1.6rem;
        box-shadow:0 0 30px rgba(0,212,255,0.06);">
        <div style="font-size:1rem;font-weight:700;color:#00d4ff;margin-bottom:0.8rem;
        font-family:Orbitron,monospace;letter-spacing:0.06em;">⚡ SIGN UP / LOGIN</div>
        </div>""", unsafe_allow_html=True)

        render_sidebar_auth()

        st.markdown("""
        <div style="background:rgba(0,30,60,0.5);border:1px solid rgba(0,212,255,0.1);
        border-radius:10px;padding:0.9rem 1.1rem;margin-top:1rem;">
            <div style="font-size:0.78rem;color:#8b949e;line-height:1.6;">
            ✅ <strong style="color:#c9d1d9;">100% Free</strong> — No hidden charges<br>
            ✅ <strong style="color:#c9d1d9;">Save History</strong> — Analysis saved across sessions<br>
            ✅ <strong style="color:#c9d1d9;">Community</strong> — Share trades &amp; ratings<br>
            ✅ <strong style="color:#c9d1d9;">AI Features</strong> — Full access to AI assistant<br>
            <br>
            <span style="font-size:0.72rem;color:#6e7681;">
            By signing up you agree to our Privacy Policy shown on the right.
            FinsageAI is for educational purposes only — not financial advice.
            </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_privacy:
        st.markdown("""
        <div style="background:linear-gradient(160deg,rgba(0,10,25,0.88),rgba(5,8,20,0.92));
        border:1px solid rgba(110,64,201,0.2);border-radius:14px;padding:1.4rem 1.6rem;
        box-shadow:0 0 30px rgba(110,64,201,0.05);max-height:700px;overflow-y:auto;">
        <div style="font-size:1rem;font-weight:700;color:#a371f7;margin-bottom:0.8rem;
        font-family:Orbitron,monospace;letter-spacing:0.06em;">🔒 PRIVACY POLICY</div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
<div style="font-size:0.8rem;color:#c9d1d9;line-height:1.7;">

<strong style="color:#00d4ff;">Last Updated:</strong> June 13, 2026 &nbsp;|&nbsp; <strong style="color:#00d4ff;">Version:</strong> 1.0

---

**1. Introduction**
{APP_NAME} explains how we collect, use, and protect your information.
By using the platform, you agree to this policy.

---

**2. What We Collect**
- Email address (for account creation)
- Google profile name & email (if Google OAuth used)
- Community reviews & voluntarily shared trade data
- Anonymous usage analytics & session timestamps

**What we DON'T collect:**
❌ Passwords in plain text &nbsp; ❌ Financial credentials
❌ Payment info &nbsp; ❌ Location data &nbsp; ❌ PAN / Aadhaar / SSN

---

**3. How We Use It**

| Purpose | Basis |
|---------|-------|
| Authentication | Contractual |
| Analysis history | Legitimate interest |
| Community features | Consent |
| Platform improvements | Legitimate interest |

---

**4. Third-Party Services**
We do NOT sell your data. We use:
- Google OAuth (auth) · Yahoo Finance (market data)
- CoinGecko (crypto data) · TradingView (charts)
- Streamlit Cloud (hosting)

---

**5. Security**
- HTTPS/TLS encryption on all data
- Secure httpOnly session cookies
- Principle of least privilege applied

---

**6. Your Rights**
✅ Access · Correct · Delete · Portability · Withdraw consent
Contact: **basantpradhan454@gmail.com**

---

**7. Financial Disclaimer**
> ⚠️ {APP_NAME} is for **educational purposes only**.
> Not SEBI-registered. Not investment advice.
> Past performance ≠ future results.

---

**8. Children**
Not intended for users under 18. We don't knowingly collect minor data.

---

**9. Contact**
📧 basantpradhan454@gmail.com

*Reviewed: June 13, 2026*

</div>
        """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
