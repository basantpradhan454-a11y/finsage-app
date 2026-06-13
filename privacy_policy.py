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
