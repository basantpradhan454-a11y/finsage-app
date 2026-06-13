"""
FinsageAI — Community: Real Star Ratings + Real P&L Trade Sharing
No fake data. User-submitted only.
"""

import streamlit as st
import json
import os
from datetime import datetime
from config import LOGO_URL, APP_NAME

FEEDBACK_FILE = "/tmp/finsage_feedback_v2.json"


def _load():
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"ratings": [], "trades": []}


def _save(data):
    try:
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def _stars(rating: int, filled_color="#f0c040", empty_color="rgba(120,120,120,0.4)") -> str:
    """Render 5 stars — filled or empty."""
    out = ""
    for i in range(1, 6):
        if i <= rating:
            out += f'<span style="color:{filled_color};font-size:1.4rem;text-shadow:0 0 8px rgba(240,192,64,0.5);">★</span>'
        else:
            out += f'<span style="color:{empty_color};font-size:1.4rem;">☆</span>'
    return out


def render_feedback_dashboard():
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.95),rgba(0,15,30,0.9));
    border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:1.2rem 1.5rem;
    margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;border-radius:10px;
            box-shadow:0 0 15px rgba(0,212,255,0.3);">
            <div>
                <div style="font-size:1.1rem;font-weight:800;color:#00d4ff;
                font-family:Orbitron,monospace;">⭐ Community</div>
                <div style="color:#4a9eff;font-size:0.75rem;">
                Rate FinsageAI · Share real trades · Read community reviews
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    data = _load()
    tab_r, tab_t = st.tabs(["⭐ Ratings & Reviews", "📊 Trade Sharing"])

    # ════════════════════════════════════════════════════════════
    # TAB 1: RATINGS
    # ════════════════════════════════════════════════════════════
    with tab_r:
        ratings = data.get("ratings", [])

        # Summary bar
        if ratings:
            avg   = sum(r.get("rating", 0) for r in ratings) / len(ratings)
            total = len(ratings)
            dist  = {i: sum(1 for r in ratings if r.get("rating") == i) for i in range(1, 6)}

            sc1, sc2 = st.columns([1, 2])
            with sc1:
                st.markdown(f"""
                <div style="background:rgba(0,20,40,0.8);border:1px solid rgba(0,212,255,0.15);
                border-radius:12px;padding:1.2rem;text-align:center;">
                    <div style="font-size:3rem;font-weight:900;color:#f0c040;
                    text-shadow:0 0 20px rgba(240,192,64,0.5);line-height:1;">{avg:.1f}</div>
                    <div style="margin:0.4rem 0;">{_stars(round(avg))}</div>
                    <div style="color:#8b949e;font-size:0.78rem;">{total} reviews</div>
                </div>
                """, unsafe_allow_html=True)
            with sc2:
                for star in range(5, 0, -1):
                    count = dist.get(star, 0)
                    pct   = (count / total * 100) if total else 0
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.35rem;">
                        <span style="color:#f0c040;font-size:0.82rem;min-width:20px;">{star}★</span>
                        <div style="flex:1;background:rgba(255,255,255,0.05);border-radius:4px;height:9px;">
                            <div style="width:{pct:.0f}%;background:linear-gradient(90deg,#f0c040,#ff8c00);
                            height:9px;border-radius:4px;box-shadow:0 0 6px rgba(240,192,64,0.3);"></div>
                        </div>
                        <span style="color:#8b949e;font-size:0.75rem;min-width:18px;">{count}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:rgba(0,20,40,0.6);border:1px dashed rgba(0,212,255,0.2);
            border-radius:10px;padding:1.5rem;text-align:center;color:#8b949e;margin-bottom:1rem;">
                <div style="font-size:2.2rem;margin-bottom:0.5rem;">☆☆☆☆☆</div>
                <div>No reviews yet — be the first!</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### ✍️ Write a Review")

        with st.form("rating_form", clear_on_submit=True):
            name_in = st.text_input("Your Name (optional)", placeholder="Anonymous")

            # ── Interactive blank stars via select_slider ──────────────────
            st.markdown("**Your Rating — tap to select:**")
            star_val = st.select_slider(
                "Rating",
                options=[1, 2, 3, 4, 5],
                value=5,
                format_func=lambda x: "☆" * (5 - x) + "★" * x,
                label_visibility="collapsed"
            )
            labels = {1:"Poor 😞", 2:"Fair 😐", 3:"Good 🙂", 4:"Very Good 😊", 5:"Excellent 🤩"}
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.6rem;margin:0.3rem 0 0.6rem;">
                {_stars(star_val)}
                <span style="color:#f0c040;font-weight:700;font-size:0.9rem;">{labels[star_val]}</span>
            </div>
            """, unsafe_allow_html=True)

            comment = st.text_area(
                "Your Review",
                placeholder="Share your experience with FinsageAI — what analysis helped you?",
                max_chars=300, height=90
            )
            sub = st.form_submit_button("⭐ Submit Review", type="primary", use_container_width=True)

            if sub:
                if not comment.strip():
                    st.warning("Please write a short review.")
                else:
                    data["ratings"].append({
                        "user": name_in.strip() or "Anonymous",
                        "rating": star_val,
                        "comment": comment.strip(),
                        "time": datetime.now().strftime("%b %d, %Y"),
                    })
                    if _save(data):
                        st.success(f"Thank you for your {star_val}★ review! 🙏")
                        st.rerun()
                    else:
                        st.error("Could not save. Try again.")

        # Show reviews
        if ratings:
            st.markdown(f"### 💬 Reviews ({len(ratings)})")
            for rev in reversed(ratings[-50:]):
                r = rev.get("rating", 5)
                st.markdown(f"""
                <div style="background:rgba(0,15,30,0.8);border:1px solid rgba(0,212,255,0.1);
                border-radius:10px;padding:0.9rem 1.1rem;margin-bottom:0.6rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="display:flex;align-items:center;gap:0.5rem;">
                            <div style="width:32px;height:32px;background:linear-gradient(135deg,#0066cc,#6e40c9);
                            border-radius:50%;display:flex;align-items:center;justify-content:center;
                            color:white;font-weight:700;font-size:0.85rem;">
                                {rev.get("user","A")[0].upper()}
                            </div>
                            <div>
                                <div style="color:#e6edf3;font-weight:600;font-size:0.84rem;">{rev.get("user","Anonymous")}</div>
                                <div style="color:#8b949e;font-size:0.68rem;">{rev.get("time","")}</div>
                            </div>
                        </div>
                        <div>{_stars(r, filled_color="#f0c040")}</div>
                    </div>
                    <div style="color:#c9d1d9;font-size:0.82rem;margin-top:0.5rem;line-height:1.5;">
                        {rev.get("comment","")}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    # TAB 2: REAL TRADE SHARING
    # ════════════════════════════════════════════════════════════
    with tab_t:
        st.markdown("### 📊 Share Your Real Trade")
        st.markdown("""
        <div style="background:rgba(0,20,40,0.6);border:1px solid rgba(0,212,255,0.12);
        border-radius:8px;padding:0.7rem 1rem;margin-bottom:1rem;font-size:0.8rem;color:#8b949e;">
        Share your real trade results with the community. All data is self-reported.
        FinsageAI does not verify or endorse any trade results.
        </div>
        """, unsafe_allow_html=True)

        with st.form("trade_form", clear_on_submit=True):
            tc1, tc2 = st.columns(2)
            with tc1:
                t_name   = st.text_input("Your Name (optional)", placeholder="Trader name")
                t_ticker = st.text_input("Asset / Ticker", placeholder="e.g. AAPL, BTC, RELIANCE.NS")
                t_type   = st.selectbox("Trade Type", ["Long (Buy)", "Short (Sell)"])
                t_entry  = st.number_input("Entry Price (₹/$)", min_value=0.0, step=0.01, format="%.4f")
            with tc2:
                t_exit   = st.number_input("Exit Price (₹/$)", min_value=0.0, step=0.01, format="%.4f")
                t_qty    = st.number_input("Quantity / Lots", min_value=0.0, step=1.0)
                t_dur    = st.selectbox("Trade Duration", ["Intraday","Swing (2-7 days)","Positional (1+ month)","Long-term"])
                t_note   = st.text_input("Trade Notes (optional)", placeholder="Why did you enter/exit?")

            # Real-time P&L preview
            if t_entry > 0 and t_exit > 0 and t_qty > 0:
                if t_type.startswith("Long"):
                    pnl   = (t_exit - t_entry) * t_qty
                    pct   = (t_exit - t_entry) / t_entry * 100
                else:
                    pnl   = (t_entry - t_exit) * t_qty
                    pct   = (t_entry - t_exit) / t_entry * 100

                pnl_color = "#00ff88" if pnl >= 0 else "#ff4466"
                emoji     = "✅ PROFIT" if pnl >= 0 else "❌ LOSS"
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.4);border:1px solid {pnl_color}33;
                border-radius:8px;padding:0.7rem 1rem;margin:0.5rem 0;display:flex;gap:1.5rem;flex-wrap:wrap;">
                    <div><div style="color:#8b949e;font-size:0.7rem;">P&L</div>
                    <div style="color:{pnl_color};font-weight:900;font-size:1.2rem;">{emoji}</div></div>
                    <div><div style="color:#8b949e;font-size:0.7rem;">Amount</div>
                    <div style="color:{pnl_color};font-weight:700;">${pnl:+,.2f}</div></div>
                    <div><div style="color:#8b949e;font-size:0.7rem;">Return</div>
                    <div style="color:{pnl_color};font-weight:700;">{pct:+.2f}%</div></div>
                    <div><div style="color:#8b949e;font-size:0.7rem;">Trade</div>
                    <div style="color:#c9d1d9;font-size:0.85rem;">{t_type.split()[0]} {t_ticker.upper() if t_ticker else "—"}</div></div>
                </div>
                """, unsafe_allow_html=True)

            tsub = st.form_submit_button("📊 Share Trade", type="primary", use_container_width=True)

            if tsub:
                if not t_ticker.strip():
                    st.warning("Please enter the asset/ticker.")
                elif t_entry <= 0 or t_exit <= 0:
                    st.warning("Please enter valid entry and exit prices.")
                elif t_qty <= 0:
                    st.warning("Please enter quantity.")
                else:
                    if t_type.startswith("Long"):
                        pnl = (t_exit - t_entry) * t_qty
                        pct = (t_exit - t_entry) / t_entry * 100
                    else:
                        pnl = (t_entry - t_exit) * t_qty
                        pct = (t_entry - t_exit) / t_entry * 100

                    data["trades"].append({
                        "user":    t_name.strip() or "Anonymous",
                        "ticker":  t_ticker.strip().upper(),
                        "type":    t_type,
                        "entry":   t_entry,
                        "exit":    t_exit,
                        "qty":     t_qty,
                        "pnl":     round(pnl, 2),
                        "pct":     round(pct, 2),
                        "duration":t_dur,
                        "note":    t_note.strip(),
                        "time":    datetime.now().strftime("%b %d, %Y"),
                    })
                    _save(data)
                    result = "PROFIT ✅" if pnl >= 0 else "LOSS ❌"
                    st.success(f"Trade shared! {result} of ${pnl:+,.2f} ({pct:+.2f}%)")
                    st.rerun()

        # Community trade stats
        trades = data.get("trades", [])
        if trades:
            st.markdown("---")
            wins   = sum(1 for t in trades if t.get("pnl",0) >= 0)
            losses = len(trades) - wins
            wr     = wins / len(trades) * 100 if trades else 0
            total_pnl = sum(t.get("pnl",0) for t in trades)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📊 Total Trades", len(trades))
            m2.metric("✅ Wins", wins)
            m3.metric("❌ Losses", losses)
            m4.metric("🎯 Win Rate", f"{wr:.0f}%")

            st.markdown("---")
            st.markdown(f"### 📋 Community Trades ({len(trades)} shared)")
            for t in reversed(trades[-30:]):
                pnl   = t.get("pnl",0)
                pct   = t.get("pct",0)
                color = "#00ff88" if pnl >= 0 else "#ff4466"
                icon  = "✅" if pnl >= 0 else "❌"
                st.markdown(f"""
                <div style="background:rgba(0,15,30,0.8);border:1px solid rgba(0,212,255,0.1);
                border-left:3px solid {color};border-radius:10px;
                padding:0.75rem 1rem;margin-bottom:0.5rem;
                display:flex;align-items:center;flex-wrap:wrap;gap:1rem;">
                    <div>
                        <div style="color:#e6edf3;font-weight:700;font-size:0.88rem;">
                            {icon} {t.get("ticker","?")}
                            <span style="color:#8b949e;font-size:0.75rem;font-weight:400;margin-left:0.4rem;">
                            {t.get("type","").split("(")[0].strip()}
                            </span>
                        </div>
                        <div style="color:#8b949e;font-size:0.7rem;">{t.get("user","?")} · {t.get("time","")} · {t.get("duration","")}</div>
                    </div>
                    <div style="margin-left:auto;text-align:right;">
                        <div style="color:{color};font-weight:800;font-size:1rem;">{pct:+.2f}%</div>
                        <div style="color:{color};font-size:0.78rem;">${pnl:+,.2f}</div>
                    </div>
                    <div style="color:#8b949e;font-size:0.75rem;width:100%;">
                        Entry: ${t.get("entry",0):,.4f} → Exit: ${t.get("exit",0):,.4f} · Qty: {t.get("qty",0):.0f}
                        {f" · {t.get('note')}" if t.get("note") else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.6rem 1rem;margin-top:1rem;font-size:0.74rem;color:#8b949e;">
    ⚠️ <b style="color:#d29922;">Disclaimer:</b> All trades and reviews are self-reported by users.
    FinsageAI does not verify trade results. This is NOT financial advice.
    Past performance does not guarantee future results.
    </div>
    """, unsafe_allow_html=True)
