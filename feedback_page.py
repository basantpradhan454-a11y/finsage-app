"""
FinSage — Feedback & Ratings Page
All users can submit feedback and view community ratings.
"""

import streamlit as st
import json
import os
import time
from datetime import datetime

FEEDBACK_FILE = "feedback_data.json"
SUPPORT_PHONE = "9692723774"


def _load_feedback() -> list:
    """Load feedback from JSON file (simple persistent storage)."""
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_feedback(data: list):
    """Save feedback list to JSON file."""
    try:
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        st.error(f"Could not save feedback: {e}")


def _star_html(rating: int, size: str = "1.1rem") -> str:
    """Return filled/empty star HTML for a rating."""
    stars = ""
    for i in range(1, 6):
        color = "#f0c040" if i <= rating else "#30363d"
        stars += f'<span style="color:{color};font-size:{size};">★</span>'
    return stars


def _avg_rating(feedbacks: list) -> float:
    if not feedbacks:
        return 0.0
    return round(sum(f["rating"] for f in feedbacks) / len(feedbacks), 1)


def _rating_distribution(feedbacks: list) -> dict:
    dist = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for f in feedbacks:
        dist[f["rating"]] = dist.get(f["rating"], 0) + 1
    return dist


def render_feedback_page(current_user=None):
    """Render the full feedback + ratings page."""

    feedbacks = _load_feedback()
    avg       = _avg_rating(feedbacks)
    dist      = _rating_distribution(feedbacks)
    total     = len(feedbacks)

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:1.5rem 0 0.5rem;">
        <div style="font-size:2.2rem;margin-bottom:0.3rem;">💬</div>
        <div style="background:linear-gradient(135deg,#58a6ff,#a78bfa);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.6rem;font-weight:800;letter-spacing:-0.5px;">
            Feedback & Ratings
        </div>
        <div style="color:#6e7681;font-size:0.88rem;margin-top:0.3rem;">
            Help us improve FinSage — your opinion matters!
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Overall rating summary ─────────────────────────────────────────────────
    col_avg, col_dist, col_support = st.columns([1, 2, 1])

    with col_avg:
        st.markdown(f"""
        <div style="background:rgba(240,192,64,0.07);border:1px solid rgba(240,192,64,0.2);
            border-radius:16px;padding:1.2rem;text-align:center;">
            <div style="font-size:3rem;font-weight:900;color:#f0c040;line-height:1;">
                {avg if total > 0 else "—"}
            </div>
            <div style="margin:0.4rem 0;">
                {_star_html(round(avg), "1.4rem") if total > 0 else '<span style="color:#30363d;font-size:1.4rem;">☆☆☆☆☆</span>'}
            </div>
            <div style="color:#8b949e;font-size:0.78rem;">
                {total} review{"s" if total != 1 else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_dist:
        st.markdown('<div style="padding:0.6rem 0;">', unsafe_allow_html=True)
        for star in [5, 4, 3, 2, 1]:
            count = dist.get(star, 0)
            pct   = int((count / total) * 100) if total > 0 else 0
            bar_color = {5:"#3fb950", 4:"#58a6ff", 3:"#f0c040", 2:"#d29922", 1:"#f85149"}[star]
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;">
                <span style="color:#f0c040;font-size:0.85rem;width:2.5rem;">{star} ★</span>
                <div style="flex:1;background:rgba(48,54,61,0.6);border-radius:6px;height:8px;overflow:hidden;">
                    <div style="width:{pct}%;background:{bar_color};height:100%;border-radius:6px;
                        transition:width 0.5s ease;"></div>
                </div>
                <span style="color:#6e7681;font-size:0.78rem;width:2rem;">{count}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_support:
        st.markdown(f"""
        <div style="background:rgba(63,185,80,0.07);border:1px solid rgba(63,185,80,0.2);
            border-radius:16px;padding:1.2rem;text-align:center;height:100%;">
            <div style="font-size:1.8rem;margin-bottom:0.4rem;">📞</div>
            <div style="color:#3fb950;font-weight:700;font-size:0.85rem;
                text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.3rem;">
                Customer Care
            </div>
            <div style="color:#e6edf3;font-size:1.15rem;font-weight:800;
                letter-spacing:1px;margin-bottom:0.3rem;">
                {SUPPORT_PHONE}
            </div>
            <div style="color:#6e7681;font-size:0.72rem;line-height:1.4;">
                Mon–Sat · 10 AM – 7 PM<br>
                We reply within 24 hours
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:rgba(48,54,61,0.5);'>", unsafe_allow_html=True)

    # ── Submit feedback form ───────────────────────────────────────────────────
    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#58a6ff,#a78bfa);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1rem;font-weight:700;margin-bottom:1rem;">
            ✍️ Share Your Feedback
        </div>
        """, unsafe_allow_html=True)

        # Autofill name if logged in
        default_name = ""
        if current_user:
            default_name = current_user.get("name", current_user.get("email", "")).split("@")[0].title()

        with st.form("feedback_form", clear_on_submit=True):
            name     = st.text_input("Your Name", value=default_name,
                                     placeholder="Enter your name (optional)")
            category = st.selectbox("Category",
                                    ["General App Feedback", "Chart & Analysis Quality",
                                     "AI Insights Accuracy", "User Interface / Design",
                                     "Feature Request", "Bug Report", "Other"])

            st.markdown("**Rate FinSage**")
            rating = st.radio("", [1, 2, 3, 4, 5],
                              format_func=lambda x: "★" * x + "☆" * (5 - x),
                              index=4, horizontal=True, key="fb_rating")

            message = st.text_area("Your Message",
                                   placeholder="Tell us what you love, what we can improve, or any bugs you found...",
                                   height=120)

            submitted = st.form_submit_button("📤 Submit Feedback",
                                              type="primary", use_container_width=True)

            if submitted:
                if not message.strip():
                    st.warning("Please write a message before submitting.")
                else:
                    new_entry = {
                        "id":        int(time.time() * 1000),
                        "name":      name.strip() if name.strip() else "Anonymous",
                        "category":  category,
                        "rating":    rating,
                        "message":   message.strip(),
                        "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                        "user_email": current_user.get("email","") if current_user else "",
                    }
                    all_feedback = _load_feedback()
                    all_feedback.insert(0, new_entry)   # newest first
                    _save_feedback(all_feedback)
                    st.success("✅ Thank you! Your feedback has been submitted.")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

    with right_col:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#58a6ff,#a78bfa);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1rem;font-weight:700;margin-bottom:1rem;">
            🌟 What Others Are Saying
        </div>
        """, unsafe_allow_html=True)

        if not feedbacks:
            st.markdown("""
            <div style="background:rgba(22,27,34,0.8);border:1px solid rgba(48,54,61,0.5);
                border-radius:12px;padding:2rem;text-align:center;color:#6e7681;">
                <div style="font-size:2rem;margin-bottom:0.5rem;">💭</div>
                No reviews yet — be the first to share your experience!
            </div>
            """, unsafe_allow_html=True)
        else:
            # Show latest 6 reviews
            for fb in feedbacks[:6]:
                r      = fb.get("rating", 5)
                clr    = {5:"#3fb950", 4:"#58a6ff", 3:"#f0c040", 2:"#d29922", 1:"#f85149"}.get(r, "#58a6ff")
                cat_bg = "rgba(88,166,255,0.08)"
                st.markdown(f"""
                <div style="background:rgba(22,27,34,0.85);border:1px solid rgba(48,54,61,0.5);
                    border-radius:12px;padding:0.9rem 1rem;margin-bottom:0.7rem;
                    border-left:3px solid {clr};">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;
                        margin-bottom:0.4rem;">
                        <div>
                            <span style="color:#e6edf3;font-weight:700;font-size:0.88rem;">
                                {fb.get("name","Anonymous")}
                            </span>
                            <span style="background:{cat_bg};color:#6e7681;font-size:0.65rem;
                                border-radius:4px;padding:0.05rem 0.35rem;margin-left:0.4rem;">
                                {fb.get("category","General")}
                            </span>
                        </div>
                        <span style="color:#6e7681;font-size:0.68rem;">
                            {fb.get("timestamp","")}
                        </span>
                    </div>
                    <div style="margin-bottom:0.3rem;">{_star_html(r, "0.95rem")}</div>
                    <div style="color:#c9d1d9;font-size:0.82rem;line-height:1.5;">
                        {fb.get("message","")}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if len(feedbacks) > 6:
                st.caption(f"Showing 6 of {len(feedbacks)} reviews")

    # ── All reviews section (expandable) ──────────────────────────────────────
    if len(feedbacks) > 6:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(f"📋 View All {len(feedbacks)} Reviews", expanded=False):
            # Filter by category
            all_cats   = ["All"] + sorted(set(f["category"] for f in feedbacks))
            filter_cat = st.selectbox("Filter by Category", all_cats, key="fb_filter")
            filtered   = feedbacks if filter_cat == "All" else [f for f in feedbacks if f["category"] == filter_cat]

            for fb in filtered:
                r   = fb.get("rating", 5)
                clr = {5:"#3fb950", 4:"#58a6ff", 3:"#f0c040", 2:"#d29922", 1:"#f85149"}.get(r, "#58a6ff")
                st.markdown(f"""
                <div style="background:rgba(22,27,34,0.85);border:1px solid rgba(48,54,61,0.4);
                    border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.6rem;
                    border-left:3px solid {clr};">
                    <div style="display:flex;justify-content:space-between;margin-bottom:0.3rem;">
                        <b style="color:#e6edf3;font-size:0.85rem;">{fb.get("name","Anonymous")}</b>
                        <span style="color:#6e7681;font-size:0.7rem;">{fb.get("timestamp","")}</span>
                    </div>
                    <div style="color:#6e7681;font-size:0.7rem;margin-bottom:0.25rem;">
                        {_star_html(r, "0.9rem")} &nbsp; {fb.get("category","")}
                    </div>
                    <div style="color:#c9d1d9;font-size:0.82rem;">{fb.get("message","")}</div>
                </div>
                """, unsafe_allow_html=True)

