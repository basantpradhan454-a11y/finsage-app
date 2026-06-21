"""
STOX AI — Admin Panel
View all registered users (admin only)
"""

import streamlit as st
import json
import os
from datetime import datetime

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "basantpradhan454@gmail.com")
USER_DB_FILE = "users.json"

def load_users() -> dict:
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def render_admin_panel():
    """Render admin panel — only visible to admin user."""
    current_user = st.session_state.get("user") or {}
    user_email = (current_user.get("email") or "").lower()

    if user_email != ADMIN_EMAIL.lower():
        return  # Not admin — silently skip

    with st.expander("🔐 Admin Panel — User Database", expanded=False):
        users = load_users()

        if not users:
            st.info("No users registered yet.")
            return

        st.markdown(f"**Total Users: {len(users)}**")
        st.markdown("---")

        # Build table data
        rows = []
        for email, data in users.items():
            rows.append({
                "Name": data.get("name", "N/A"),
                "Email": email,
                "Provider": data.get("provider", "email").upper(),
                "Registered": data.get("created_at", "N/A")[:10] if data.get("created_at") else "N/A",
                "Last Login": data.get("last_login", "N/A")[:16].replace("T", " ") if data.get("last_login") else "N/A",
            })

        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Stats
        col1, col2, col3 = st.columns(3)
        email_users = sum(1 for u in users.values() if u.get("provider") == "email")
        google_users = sum(1 for u in users.values() if u.get("provider") == "google")
        with col1:
            st.metric("📧 Email Users", email_users)
        with col2:
            st.metric("🔵 Google Users", google_users)
        with col3:
            st.metric("👥 Total", len(users))

        # Download user data
        json_str = json.dumps(
            [{k: v for k, v in u.items() if k != "password_hash"} for u in users.values()],
            indent=2, default=str
        )
        st.download_button(
            "📥 Download User Data (JSON)",
            data=json_str,
            file_name=f"finsage_users_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
        )
