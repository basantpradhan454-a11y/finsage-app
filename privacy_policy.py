"""
FinSage — Privacy Policy Page
"""
import streamlit as st


def render_privacy_policy():
    if st.button("← Back to FinSage", key="back_privacy_btn"):
        st.session_state["show_privacy"] = False
        st.rerun()

    st.markdown("""
## 🔒 Privacy Policy — FinSage

**Last Updated:** May 2026 &nbsp;|&nbsp; Version 1.0

---

### 1. Introduction
FinSage ("we", "us", "our") is a financial intelligence platform providing real-time market data, AI-powered analysis, and educational insights. This Privacy Policy explains how we collect, use, store, and protect your information when you use FinSage.

By creating an account or using FinSage, you agree to this Privacy Policy.

---

### 2. Information We Collect

**Account Information:**
- Full name, email address (via Firebase Authentication)
- Encrypted password (Firebase handles this — we never see plain-text passwords)
- Account creation date, selected subscription plan

**Usage Data:**
- Assets analyzed (ticker symbols searched)
- Features used, pages visited
- Time and frequency of usage

**Device & Technical Info:**
- Browser type and version
- Operating system
- IP address (for security and fraud prevention)

**Payment Information (Stripe):**
- Billing name, email, card last 4 digits
- Transaction history
- We **never** store full card numbers — Stripe handles all payment data securely

---

### 3. How We Use Your Information

- **Account Management:** To create, maintain, and secure your account
- **Service Delivery:** To provide market data, analysis, and AI insights
- **Billing:** To process subscription payments via Stripe
- **Security:** To detect and prevent fraudulent activity
- **Improvement:** To analyze usage patterns and improve the platform
- **Communication:** Important account/service updates only (no spam)

---

### 4. Data Security

- **Authentication:** Powered by **Google Firebase** — industry-standard OAuth 2.0
- **Passwords:** SHA-256 hashed by Firebase — never stored as plain text
- **Payments:** Processed by **Stripe** — PCI DSS Level 1 certified
- **Data Transit:** All connections use HTTPS/TLS encryption
- **Database:** Firebase Firestore with security rules limiting access to account owners only

---

### 5. Third-Party Services

| Service | Purpose | Privacy Policy |
|---------|---------|----------------|
| **Google Firebase** | Authentication + Database | [firebase.google.com/support/privacy](https://firebase.google.com/support/privacy) |
| **Stripe** | Payment processing | [stripe.com/privacy](https://stripe.com/privacy) |
| **Yahoo Finance (yfinance)** | Stock market data | Public API, no personal data shared |
| **CoinGecko** | Cryptocurrency data | Public API, no personal data shared |
| **Groq API** | AI-powered insights | No personal data sent — only market data |
| **Google News RSS** | News headlines | Public RSS feed, no personal data |

---

### 6. Data Retention

- Account data is retained while your account is active
- You can request deletion at any time
- Payment records are retained for 7 years as required by Indian financial regulations
- Usage logs are retained for 90 days

---

### 7. Cookies & Sessions

- FinSage uses **session-only cookies** to maintain your login state
- No tracking, advertising, or third-party analytics cookies
- Sessions expire when you close the browser or click Logout

---

### 8. Your Rights (GDPR & IT Act 2000)

You have the right to:
- ✅ **Access** your personal data
- ✅ **Correct** inaccurate information
- ✅ **Delete** your account and all associated data
- ✅ **Export** your data in machine-readable format
- ✅ **Opt out** of all marketing communications
- ✅ **Withdraw consent** at any time

To exercise these rights, contact: **support@finsage.app**

---

### 9. Subscription & Refunds

- Subscriptions are billed monthly via Stripe
- **7-day no-questions-asked refund policy** for first-time subscribers
- Cancel anytime — access continues until end of billing period
- No hidden charges; GST extra as applicable

---

### 10. Disclaimer

> FinSage is an **educational and informational platform only**. Nothing on this platform constitutes financial advice, investment recommendation, or solicitation to buy or sell any security. Past performance is not indicative of future results. Always consult a **SEBI-registered investment advisor** before making any investment decisions. FinSage is **not** a SEBI-registered investment advisor.

---

### 11. Changes to This Policy

We may update this policy from time to time. Significant changes will be notified via email. Continued use of FinSage after changes constitutes acceptance.

---

### 12. Contact Us

📧 **Email:** support@finsage.app  
🌐 **Website:** finsage-app-mzhu9qcb5eappqtqcpah8kp.streamlit.app  
📍 **Jurisdiction:** India (governed by Indian IT Act 2000 & applicable laws)

---
*FinSage — Global Financial Intelligence Platform | © 2026 FinSage. All rights reserved.*
""")
