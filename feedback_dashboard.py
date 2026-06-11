"""
STOX AI — Feedback & Community Dashboard
Rating, trade proof share, leaderboard
"""

import streamlit as st
import json
import os
import time
from datetime import datetime, timedelta
import random

FEEDBACK_FILE = "/tmp/stox_feedback.json"
LOGO_URL = "https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"

# ── Data helpers ────────────────────────────────────────────────────────────────
def _load_feedback():
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE) as f:
                return json.load(f)
        except:
            pass
    # Seed with demo data
    return {
        "ratings": [
            {"user": "Rahul M.", "rating": 5, "comment": "NVDA call 40% profit mila!", "time": "2 days ago", "verified": True},
            {"user": "Priya K.", "rating": 5, "comment": "BTC ka analysis bilkul sahi nikla", "time": "3 days ago", "verified": True},
            {"user": "Arjun S.", "rating": 4, "comment": "RSI signal ne TSLA pe achha entry diya", "time": "5 days ago", "verified": True},
            {"user": "Neha T.", "rating": 5, "comment": "Meme coin rug pull alert ne ₹30k bachaye!", "time": "1 week ago", "verified": True},
            {"user": "Vikram R.", "rating": 4, "comment": "Technical analysis features bahut useful", "time": "1 week ago", "verified": False},
        ],
        "trade_proofs": [
            {"user": "Rahul M.", "symbol": "NVDA", "entry": 850, "exit": 1190, "pct": 40.0, "type": "stock", "time": "2 days ago", "likes": 24},
            {"user": "Crypto_Degen", "symbol": "SOL", "entry": 95, "exit": 185, "pct": 94.7, "type": "crypto", "time": "3 days ago", "likes": 41},
            {"user": "Priya K.", "symbol": "RELIANCE.NS", "entry": 2850, "exit": 3120, "pct": 9.5, "type": "stock", "time": "5 days ago", "likes": 18},
            {"user": "MoonBoi99", "symbol": "PEPE", "entry": 0.0000085, "exit": 0.0000215, "pct": 152.9, "type": "meme", "time": "1 week ago", "likes": 89},
            {"user": "TechTrader", "symbol": "AAPL", "entry": 175, "exit": 198, "pct": 13.1, "type": "stock", "time": "2 weeks ago", "likes": 15},
        ]
    }

def _save_feedback(data):
    try:
        with open(FEEDBACK_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

def _avg_rating(ratings):
    if not ratings:
        return 0
    return sum(r["rating"] for r in ratings) / len(ratings)

def _star_html(rating, size=18):
    stars = ""
    for i in range(1, 6):
        color = "#d29922" if i <= rating else "#30363d"
        stars += f'<span style="color:{color};font-size:{size}px;">★</span>'
    return stars


# ── Main Render ─────────────────────────────────────────────────────────────────
def render_feedback_dashboard():
    data = _load_feedback()
    ratings = data.get("ratings", [])
    trade_proofs = data.get("trade_proofs", [])

    avg = _avg_rating(ratings)
    total = len(ratings)

    # ── Header ──
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1117,#1a2035);border:1px solid #30363d;
    border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;width:44px;border-radius:10px;">
            <div>
                <div style="font-size:1.2rem;font-weight:800;color:#58a6ff;">Community Dashboard</div>
                <div style="color:#8b949e;font-size:0.78rem;">Traders ki real success stories aur ratings</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Stats Row ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:0.9rem;text-align:center;">
            <div style="font-size:1.8rem;font-weight:800;color:#d29922;">{avg:.1f}</div>
            <div>{_star_html(round(avg))}</div>
            <div style="color:#8b949e;font-size:0.75rem;margin-top:0.3rem;">Average Rating</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:0.9rem;text-align:center;">
            <div style="font-size:1.8rem;font-weight:800;color:#58a6ff;">{total}</div>
            <div style="color:#8b949e;font-size:0.75rem;margin-top:0.5rem;">Total Reviews</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:0.9rem;text-align:center;">
            <div style="font-size:1.8rem;font-weight:800;color:#3fb950;">{len(trade_proofs)}</div>
            <div style="color:#8b949e;font-size:0.75rem;margin-top:0.5rem;">Trade Proofs Shared</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        five_star = sum(1 for r in ratings if r["rating"] == 5)
        pct = int((five_star / total * 100)) if total else 0
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:0.9rem;text-align:center;">
            <div style="font-size:1.8rem;font-weight:800;color:#3fb950;">{pct}%</div>
            <div style="color:#8b949e;font-size:0.75rem;margin-top:0.5rem;">5-Star Reviews</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Two columns: Submit + Trade Proof ──
    left, right = st.columns([1, 1])

    with left:
        st.markdown("#### ⭐ Rate STOX AI")
        with st.form("rating_form"):
            user_name = st.text_input("Your Name / Username", placeholder="e.g. Rahul M. or CryptoTrader99")
            rating_val = st.select_slider("Rating", options=[1, 2, 3, 4, 5], value=5,
                                          format_func=lambda x: "⭐" * x)
            comment = st.text_area("Your Experience", placeholder="e.g. BTC call 30% profit mila! STOX AI ka analysis bahut accurate hai...")
            submit_rating = st.form_submit_button("Submit Rating ⭐", type="primary", use_container_width=True)

            if submit_rating:
                if not user_name or not comment:
                    st.warning("⚠️ Name aur comment dono fill karo!")
                else:
                    data["ratings"].insert(0, {
                        "user": user_name,
                        "rating": rating_val,
                        "comment": comment,
                        "time": "Just now",
                        "verified": False
                    })
                    _save_feedback(data)
                    st.success(f"✅ Thanks {user_name}! Rating submit ho gayi!")
                    st.rerun()

    with right:
        st.markdown("#### 📸 Share Trade Proof")
        with st.form("trade_proof_form"):
            tp_name = st.text_input("Your Name / Username", placeholder="e.g. MoonBoi99", key="tp_name")
            tp_sym = st.text_input("Asset Symbol", placeholder="e.g. BTC, AAPL, NVDA, PEPE")
            tp_col1, tp_col2 = st.columns(2)
            with tp_col1:
                tp_entry = st.number_input("Entry Price (₹/$)", min_value=0.0, value=0.0, format="%.6f")
            with tp_col2:
                tp_exit = st.number_input("Exit Price (₹/$)", min_value=0.0, value=0.0, format="%.6f")
            tp_type = st.selectbox("Asset Type", ["stock", "crypto", "meme"])
            submit_proof = st.form_submit_button("Share Trade 🚀", type="primary", use_container_width=True)

            if submit_proof:
                if not tp_name or not tp_sym or tp_entry <= 0 or tp_exit <= 0:
                    st.warning("⚠️ Sab fields fill karo!")
                else:
                    pct = ((tp_exit - tp_entry) / tp_entry * 100) if tp_entry else 0
                    icon = "🟢" if pct >= 0 else "🔴"
                    data["trade_proofs"].insert(0, {
                        "user": tp_name,
                        "symbol": tp_sym.upper(),
                        "entry": tp_entry,
                        "exit": tp_exit,
                        "pct": pct,
                        "type": tp_type,
                        "time": "Just now",
                        "likes": 0
                    })
                    _save_feedback(data)
                    st.success(f"{icon} Trade shared! {tp_sym.upper()} {pct:+.1f}% return!")
                    st.rerun()

    st.markdown("---")

    # ── Trade Leaderboard ──
    st.markdown("#### 🏆 Top Traders — Trade Proof Hall of Fame")

    sorted_proofs = sorted(trade_proofs, key=lambda x: x.get("pct", 0), reverse=True)
    for i, proof in enumerate(sorted_proofs[:8]):
        pct   = proof.get("pct", 0)
        icon  = "🟢" if pct >= 0 else "🔴"
        medal = ["🥇", "🥈", "🥉"] [i] if i < 3 else f"#{i+1}"
        type_icon = {"stock": "📊", "crypto": "₿", "meme": "🎭"}.get(proof["type"], "📈")
        entry_fmt = f"₹{proof['entry']:,.6f}".rstrip('0').rstrip('.')
        exit_fmt  = f"₹{proof['exit']:,.6f}".rstrip('0').rstrip('.')

        st.markdown(f"""
        <div style="background:#161b22;border:1px solid {'#238636' if pct>=0 else '#da3633'};
        border-radius:10px;padding:0.8rem 1.1rem;margin-bottom:0.5rem;
        display:flex;align-items:center;gap:1rem;">
            <div style="font-size:1.4rem;min-width:2rem;text-align:center;">{medal}</div>
            <div style="flex:1;">
                <div style="font-weight:700;color:#e6edf3;">{type_icon} {proof['symbol']}
                    <span style="color:#8b949e;font-size:0.78rem;font-weight:400;"> by {proof['user']}</span>
                </div>
                <div style="font-size:0.8rem;color:#8b949e;">
                    Entry: {entry_fmt} → Exit: {exit_fmt} · {proof['time']}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.3rem;font-weight:800;color:{'#3fb950' if pct>=0 else '#f85149'};">
                    {icon} {pct:+.1f}%
                </div>
                <div style="font-size:0.75rem;color:#8b949e;">❤️ {proof.get('likes', 0)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Reviews ──
    st.markdown("#### 💬 User Reviews")
    for review in ratings[:6]:
        verified_badge = ' <span style="background:#1a3a1a;color:#3fb950;padding:0.1rem 0.4rem;border-radius:10px;font-size:0.7rem;">✅ Verified</span>' if review.get("verified") else ""
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
        padding:0.8rem 1rem;margin-bottom:0.5rem;">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div>
                    <span style="font-weight:700;color:#e6edf3;">👤 {review['user']}</span>
                    {verified_badge}
                    <span style="color:#8b949e;font-size:0.75rem;margin-left:0.5rem;">{review['time']}</span>
                </div>
                <div>{_star_html(review['rating'], 14)}</div>
            </div>
            <div style="color:#c9d1d9;font-size:0.85rem;margin-top:0.4rem;">"{review['comment']}"</div>
        </div>
        """, unsafe_allow_html=True)
