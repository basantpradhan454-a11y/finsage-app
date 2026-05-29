"""
FinSage — Stripe Payments Module
Handles subscription plan checkout via Stripe Checkout Sessions.
Uses Stripe REST API directly (no SDK — works on Streamlit Cloud).
"""

import os
import requests
import streamlit as st


def _stripe_key() -> str:
    try:
        return st.secrets["stripe"]["STRIPE_SECRET_KEY"]
    except Exception:
        return os.environ.get("STRIPE_SECRET_KEY", "")


def _stripe_pub_key() -> str:
    try:
        return st.secrets["stripe"]["STRIPE_PUBLISHABLE_KEY"]
    except Exception:
        return os.environ.get("STRIPE_PUBLISHABLE_KEY", "")


# ── Plan definitions ──────────────────────────────────────────────────────────
PLANS = {
    "free": {
        "name": "🆓 Free Plan",
        "price_inr": 0,
        "price_display": "₹0/month",
        "features": [
            "✅ 5 analyses per day",
            "✅ Stocks + Crypto + Meme data",
            "✅ Basic AI Insight",
            "❌ No candlestick charts",
            "❌ No Trading Signals",
            "❌ No PDF export",
        ],
        "price_id": None,  # No Stripe needed
        "color": "#30363d",
        "badge": "",
    },
    "pro": {
        "name": "⭐ Pro Plan",
        "price_inr": 299,
        "price_display": "₹299/month",
        "features": [
            "✅ Unlimited analyses",
            "✅ Stocks + Crypto + Meme data",
            "✅ Advanced AI Insight (News-powered)",
            "✅ Candlestick Charts",
            "✅ Trading Signals (Entry/SL/Target)",
            "✅ PDF Report Export",
            "❌ No portfolio tracking",
        ],
        "price_id": "STRIPE_PRO_PRICE_ID",   # Replace with real Stripe Price ID
        "color": "#1f3a5f",
        "badge": "🔥 Popular",
    },
    "premium": {
        "name": "💎 Premium Plan",
        "price_inr": 599,
        "price_display": "₹599/month",
        "features": [
            "✅ Everything in Pro",
            "✅ Portfolio Tracker",
            "✅ Watchlist with alerts",
            "✅ Priority AI analysis",
            "✅ Early access to new features",
            "✅ Email support",
        ],
        "price_id": "STRIPE_PREMIUM_PRICE_ID",  # Replace with real Stripe Price ID
        "color": "#2d1f5f",
        "badge": "👑 Best Value",
    },
}


# ── Stripe Checkout Session ────────────────────────────────────────────────────

def create_checkout_session(price_id: str, customer_email: str,
                             success_url: str, cancel_url: str) -> dict:
    """Create a Stripe Checkout Session. Returns {url: ...} or {error: ...}."""
    sk = _stripe_key()
    if not sk or sk.startswith("STRIPE_"):
        return {"error": "Stripe keys configure nahi hain. Streamlit secrets mein add karo."}

    url = "https://api.stripe.com/v1/checkout/sessions"
    payload = {
        "mode": "subscription",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "customer_email": customer_email,
        "success_url": success_url + "?payment=success",
        "cancel_url": cancel_url + "?payment=cancelled",
        "allow_promotion_codes": "true",
        "billing_address_collection": "auto",
        "locale": "auto",
    }
    try:
        r = requests.post(url, data=payload, auth=(sk, ""), timeout=15)
        data = r.json()
        if "url" in data:
            return {"url": data["url"], "session_id": data.get("id", "")}
        return {"error": data.get("error", {}).get("message", "Stripe error")}
    except Exception as e:
        return {"error": str(e)}


def get_subscription_status(customer_email: str) -> str:
    """Check if customer has active subscription. Returns plan name or 'free'."""
    sk = _stripe_key()
    if not sk or sk.startswith("STRIPE_"):
        return "free"
    try:
        r = requests.get(
            "https://api.stripe.com/v1/customers",
            params={"email": customer_email, "limit": 1},
            auth=(sk, ""), timeout=10
        )
        customers = r.json().get("data", [])
        if not customers:
            return "free"
        cust_id = customers[0]["id"]

        subs = requests.get(
            "https://api.stripe.com/v1/subscriptions",
            params={"customer": cust_id, "status": "active", "limit": 1},
            auth=(sk, ""), timeout=10
        ).json().get("data", [])

        if not subs:
            return "free"

        price_id = subs[0]["items"]["data"][0]["price"]["id"]
        if price_id == PLANS["premium"]["price_id"]:
            return "premium"
        elif price_id == PLANS["pro"]["price_id"]:
            return "pro"
        return "free"
    except Exception:
        return "free"


# ── Pricing UI ────────────────────────────────────────────────────────────────

def render_pricing_page():
    """Beautiful pricing page with 3 plans."""
    if st.button("← Back to FinSage", key="back_pricing"):
        st.session_state["show_pricing"] = False
        st.rerun()

    st.markdown("""
    <h1 style='text-align:center;background:linear-gradient(90deg,#58a6ff,#a78bfa);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:0.3rem;'>
    Choose Your Plan</h1>
    <p style='text-align:center;color:#8b949e;margin-bottom:2rem;'>
    Smart investing starts with smart tools. Upgrade anytime.</p>
    """, unsafe_allow_html=True)

    cols = st.columns(3)
    app_url = "https://finsage-app-mzhu9qcb5eappqtqcpah8kp.streamlit.app/"
    user = st.session_state.get("fb_user", {})
    email = user.get("email", "")

    for i, (plan_key, plan) in enumerate(PLANS.items()):
        with cols[i]:
            badge_html = f"<span style='background:#f85149;color:white;border-radius:12px;padding:0.15rem 0.6rem;font-size:0.72rem;font-weight:700;'>{plan['badge']}</span>" if plan["badge"] else "&nbsp;"
            st.markdown(f"""
            <div style='background:{plan["color"]};border:1px solid #30363d;border-radius:16px;
            padding:1.5rem 1.2rem;min-height:380px;'>
            <div style='text-align:center;font-size:1.1rem;font-weight:700;color:#e6edf3;
            margin-bottom:0.3rem;'>{plan["name"]}</div>
            <div style='text-align:center;margin-bottom:0.5rem;'>{badge_html}</div>
            <div style='text-align:center;font-size:1.8rem;font-weight:800;
            background:linear-gradient(90deg,#58a6ff,#a78bfa);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            margin-bottom:1rem;'>{plan["price_display"]}</div>
            {"".join(f"<div style='color:#c9d1d9;font-size:0.82rem;margin-bottom:0.4rem;'>{f}</div>" for f in plan["features"])}
            </div>
            """, unsafe_allow_html=True)

            if plan_key == "free":
                st.button("Current Plan ✓", key=f"plan_free", disabled=True, use_container_width=True)
            else:
                if st.button(f"Upgrade to {plan['name'].split()[1]} →",
                             key=f"plan_{plan_key}", use_container_width=True, type="primary"):
                    if not email:
                        st.error("Pehle login karo.")
                    elif not _stripe_key() or _stripe_key().startswith("STRIPE_"):
                        st.warning("⚙️ Stripe keys abhi configure nahi hain. Admin se contact karo.")
                    else:
                        with st.spinner("Checkout page prepare kar rahe hain..."):
                            result = create_checkout_session(
                                price_id=plan["price_id"],
                                customer_email=email,
                                success_url=app_url,
                                cancel_url=app_url,
                            )
                        if "url" in result:
                            checkout_url = result["url"]
                            st.markdown(f"<meta http-equiv='refresh' content='0;url={checkout_url}'>", unsafe_allow_html=True)
                            st.markdown(f"[➡️ Yahan click karo Stripe par jaane ke liye]({checkout_url})")
                        else:
                            st.error(f"❌ {result.get('error', 'Checkout failed')}")

    st.markdown("---")
    st.markdown("""
    <div style='text-align:center;color:#8b949e;font-size:0.8rem;'>
    🔒 Secure payments via <b>Stripe</b> · ₹ INR · Cancel anytime · No hidden charges<br>
    GST extra as applicable. Refund policy: 7 days no-questions-asked.
    </div>
    """, unsafe_allow_html=True)
