"""
FinSage — Search History Page
Shows user's past searches with timestamps
"""

import streamlit as st
import json
import os
from datetime import datetime


HISTORY_FILE = "search_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            return []
    return []

def save_search(user_email: str, asset_type: str, symbol: str, name: str = ""):
    """Call this whenever a user searches for an asset."""
    history = load_history()
    entry = {
        "email":      user_email,
        "asset_type": asset_type,   # Stock / Crypto / Meme
        "symbol":     symbol.upper(),
        "name":       name,
        "searched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    history.insert(0, entry)  # newest first
    # Keep max 500 records total
    history = history[:500]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def get_user_history(user_email: str):
    return [h for h in load_history() if h.get("email") == user_email]

def clear_user_history(user_email: str):
    history = [h for h in load_history() if h.get("email") != user_email]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ── Render ─────────────────────────────────────────────────────────────────────
def render_history_page(user: dict):
    email = user.get("email", "")
    name  = user.get("name", "User")
    history = get_user_history(email)

    st.markdown("""
    <style>
    .hist-header {
        font-size: 1.5rem; font-weight: 800;
        background: linear-gradient(135deg,#58a6ff,#a78bfa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hist-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.55rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        transition: border-color 0.2s;
    }
    .hist-card:hover { border-color: #58a6ff; }
    .hist-badge-stock  { background:#1a3a5c; color:#58a6ff; border-radius:6px; padding:3px 9px; font-size:0.72rem; font-weight:700; }
    .hist-badge-crypto { background:#2a1f3d; color:#a78bfa; border-radius:6px; padding:3px 9px; font-size:0.72rem; font-weight:700; }
    .hist-badge-meme   { background:#3d2a1a; color:#f0883e; border-radius:6px; padding:3px 9px; font-size:0.72rem; font-weight:700; }
    .hist-symbol { font-size:1.05rem; font-weight:700; color:#c9d1d9; }
    .hist-name   { font-size:0.8rem; color:#8b949e; }
    .hist-time   { font-size:0.75rem; color:#6e7681; margin-left:auto; white-space:nowrap; }
    .empty-state { text-align:center; padding:3rem 1rem; color:#8b949e; }
    </style>
    """, unsafe_allow_html=True)

    # Header
    col_h, col_btn = st.columns([3, 1])
    with col_h:
        st.markdown(f'<div class="hist-header">🕐 Search History</div>', unsafe_allow_html=True)
        st.markdown(f"<span style='color:#8b949e;font-size:0.85rem;'>All searches by {name}</span>", unsafe_allow_html=True)
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if history and st.button("🗑️ Clear History", use_container_width=True):
            clear_user_history(email)
            st.success("History cleared!")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    if not history:
        st.markdown("""
        <div class="empty-state">
            <div style="font-size:3rem;">📭</div>
            <p style="font-size:1rem;font-weight:600;color:#c9d1d9;">No searches yet</p>
            <p>Go analyze a stock or crypto — it'll show up here!</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Stats row
    stock_count  = sum(1 for h in history if h["asset_type"] == "Stock")
    crypto_count = sum(1 for h in history if h["asset_type"] == "Crypto")
    meme_count   = sum(1 for h in history if h["asset_type"] == "Meme")

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("📊 Total Searches", len(history))
    s2.metric("🌍 Stocks", stock_count)
    s3.metric("₿ Crypto", crypto_count)
    s4.metric("🎭 Meme Coins", meme_count)

    st.markdown("---")

    # Filter
    filter_col, _ = st.columns([2, 3])
    with filter_col:
        filter_type = st.selectbox("Filter by type", ["All", "Stock", "Crypto", "Meme"], key="hist_filter")

    filtered = history if filter_type == "All" else [h for h in history if h["asset_type"] == filter_type]

    st.markdown(f"<span style='color:#8b949e;font-size:0.8rem;'>Showing {len(filtered)} result(s)</span><br><br>", unsafe_allow_html=True)

    for h in filtered:
        atype  = h.get("asset_type", "Stock")
        symbol = h.get("symbol", "")
        name_h = h.get("name", "")
        ts     = h.get("searched_at", "")

        badge_class = {
            "Stock": "hist-badge-stock",
            "Crypto": "hist-badge-crypto",
            "Meme":  "hist-badge-meme",
        }.get(atype, "hist-badge-stock")

        icon = {"Stock": "🌍", "Crypto": "₿", "Meme": "🎭"}.get(atype, "📊")

        # Format timestamp nicely
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            time_str = dt.strftime("%d %b %Y · %I:%M %p")
        except:
            time_str = ts

        st.markdown(f"""
        <div class="hist-card">
            <span class="{badge_class}">{icon} {atype}</span>
            <div>
                <div class="hist-symbol">{symbol}</div>
                {"<div class='hist-name'>" + name_h + "</div>" if name_h else ""}
            </div>
            <div class="hist-time">🕐 {time_str}</div>
        </div>
        """, unsafe_allow_html=True)
