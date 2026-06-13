"""
STOX AI — Community & Ratings
Real user ratings only — 5 blank stars, user fills them.
No fake trading proofs.
"""

import streamlit as st
import json
import os
from datetime import datetime

FEEDBACK_FILE = "/tmp/stox_feedback_real.json"
LOGO_URL = "https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"


def _load_feedback():
    """Load real user feedback only — no seeded fake data."""
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"ratings": []}


def _save_feedback(data):
    try:
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def _star_html(rating: int, max_stars: int = 5) -> str:
    """Render filled/unfilled stars."""
    stars = ""
    for i in range(1, max_stars + 1):
        if i <= rating:
            stars += '<span style="color:#f0c040;font-size:1.3rem;text-shadow:0 0 6px rgba(240,192,64,0.6);">★</span>'
        else:
            stars += '<span style="color:rgba(100,100,100,0.5);font-size:1.3rem;">☆</span>'
    return stars


def render_feedback_dashboard():
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.95),rgba(0,15,30,0.9));
    border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:1.2rem 1.5rem;
    margin-bottom:1.2rem;box-shadow:0 0 30px rgba(0,212,255,0.06);">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;width:44px;border-radius:10px;
            box-shadow:0 0 15px rgba(0,212,255,0.3);">
            <div>
                <div style="font-size:1.15rem;font-weight:800;color:#00d4ff;
                font-family:Orbitron,monospace;letter-spacing:0.05em;">
                ⭐ Community Ratings
                </div>
                <div style="color:#4a9eff;font-size:0.75rem;">
                Real user reviews — Rate STOX AI and share your experience
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    data = _load_feedback()
    ratings_list = data.get("ratings", [])

    # ── Average rating display ──────────────────────────────────────────────────
    if ratings_list:
        avg = sum(r.get("rating", 0) for r in ratings_list) / len(ratings_list)
        total = len(ratings_list)
        dist = {i: sum(1 for r in ratings_list if r.get("rating") == i) for i in range(1, 6)}

        col_avg, col_dist = st.columns([1, 2])
        with col_avg:
            st.markdown(f"""
            <div style="background:rgba(0,20,40,0.8);border:1px solid rgba(0,212,255,0.15);
            border-radius:12px;padding:1.2rem;text-align:center;
            box-shadow:0 0 20px rgba(0,212,255,0.05);">
                <div style="font-size:3rem;font-weight:900;color:#f0c040;
                text-shadow:0 0 20px rgba(240,192,64,0.5);line-height:1;">
                    {avg:.1f}
                </div>
                <div style="margin:0.4rem 0;">{_star_html(round(avg))}</div>
                <div style="color:#8b949e;font-size:0.78rem;">{total} review{"s" if total != 1 else ""}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_dist:
            st.markdown("<div style='margin-top:0.3rem;'>", unsafe_allow_html=True)
            for star in range(5, 0, -1):
                count = dist.get(star, 0)
                pct = (count / total * 100) if total else 0
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">
                    <span style="color:#f0c040;font-size:0.8rem;min-width:1.5rem;">{star}★</span>
                    <div style="flex:1;background:rgba(255,255,255,0.05);border-radius:4px;height:8px;">
                        <div style="width:{pct:.0f}%;background:linear-gradient(90deg,#f0c040,#ff8c00);
                        height:8px;border-radius:4px;transition:width 0.5s;
                        box-shadow:0 0 6px rgba(240,192,64,0.3);"></div>
                    </div>
                    <span style="color:#8b949e;font-size:0.75rem;min-width:1.5rem;">{count}</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:rgba(0,20,40,0.6);border:1px dashed rgba(0,212,255,0.2);
        border-radius:10px;padding:1.5rem;text-align:center;color:#8b949e;margin-bottom:1rem;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">⭐☆☆☆☆</div>
            <div>No reviews yet — be the first to rate STOX AI!</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Submit rating ───────────────────────────────────────────────────────────
    st.markdown("### ✍️ Rate STOX AI")
    st.markdown("""
    <div style="color:#8b949e;font-size:0.82rem;margin-bottom:0.8rem;">
    Share your honest experience. Select stars below and write a short review.
    </div>
    """, unsafe_allow_html=True)

    with st.form("rating_form", clear_on_submit=True):
        name_input = st.text_input("Your Name (optional)", placeholder="e.g. Rahul M.")

        # Interactive 5-star selector
        st.markdown("**Your Rating:**")
        star_rating = st.select_slider(
            "Stars",
            options=[1, 2, 3, 4, 5],
            value=5,
            format_func=lambda x: "★" * x + "☆" * (5 - x),
            label_visibility="collapsed"
        )

        # Visual star preview
        st.markdown(f"""
        <div style="font-size:2rem;margin:0.3rem 0;">
            {_star_html(star_rating)}
            <span style="color:#f0c040;font-size:0.9rem;margin-left:0.5rem;font-weight:700;">
            {["","Poor","Fair","Good","Very Good","Excellent"][star_rating]}
            </span>
        </div>
        """, unsafe_allow_html=True)

        comment = st.text_area(
            "Your Review",
            placeholder="Tell us about your experience with STOX AI — what did you like? What analysis was helpful?",
            max_chars=300,
            height=100
        )

        submitted = st.form_submit_button("⭐ Submit Review", type="primary", use_container_width=True)

        if submitted:
            if not comment.strip():
                st.warning("Please write a short review before submitting.")
            else:
                new_entry = {
                    "user": name_input.strip() or "Anonymous",
                    "rating": star_rating,
                    "comment": comment.strip(),
                    "time": datetime.now().strftime("%b %d, %Y %H:%M"),
                    "verified": False
                }
                data["ratings"].append(new_entry)
                if _save_feedback(data):
                    st.success(f"Thank you for your {star_rating}★ review! 🙏")
                    st.rerun()
                else:
                    st.error("Could not save review. Please try again.")

    st.markdown("---")

    # ── Display real reviews ────────────────────────────────────────────────────
    if ratings_list:
        st.markdown(f"### 💬 User Reviews ({len(ratings_list)})")
        for rev in reversed(ratings_list[-50:]):  # show latest 50
            rating = rev.get("rating", 5)
            st.markdown(f"""
            <div style="background:rgba(0,15,30,0.8);border:1px solid rgba(0,212,255,0.1);
            border-radius:10px;padding:0.9rem 1.1rem;margin-bottom:0.7rem;
            box-shadow:0 0 10px rgba(0,212,255,0.03);">
                <div style="display:flex;justify-content:space-between;align-items:center;
                margin-bottom:0.4rem;">
                    <div style="display:flex;align-items:center;gap:0.5rem;">
                        <div style="width:32px;height:32px;background:linear-gradient(135deg,#0066cc,#6e40c9);
                        border-radius:50%;display:flex;align-items:center;justify-content:center;
                        font-size:0.85rem;font-weight:700;color:white;">
                            {rev.get("user","A")[0].upper()}
                        </div>
                        <div>
                            <div style="color:#e6edf3;font-weight:600;font-size:0.85rem;">
                                {rev.get("user","Anonymous")}
                            </div>
                            <div style="color:#8b949e;font-size:0.7rem;">{rev.get("time","")}</div>
                        </div>
                    </div>
                    <div>{_star_html(rating)}</div>
                </div>
                <div style="color:#c9d1d9;font-size:0.82rem;line-height:1.5;">
                    {rev.get("comment","")}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.6rem 1rem;margin-top:1rem;font-size:0.75rem;color:#8b949e;">
    ⚠️ All reviews are submitted by real users. STOX AI does not endorse any investment decisions.
    Reviews are opinions, not financial advice.
    </div>
    """, unsafe_allow_html=True)
