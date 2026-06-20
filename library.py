"""
FinSage Marketplace — Ebook & Course Selling Platform
Sellers list books/courses (free or paid), buyers browse & access.
All data in JSON files (Firebase-compatible). AI via Groq.
"""
import streamlit as st
import os, json, time, secrets
from datetime import datetime
import requests

# ══════════════════════════════════════════
# 0. API
# ══════════════════════════════════════════
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

def _get_key(name):
    v = os.environ.get(name, "")
    if not v:
        try: v = st.secrets.get(name, "")
        except Exception: pass
    return v or ""

def _groq_key():
    return _get_key("GROQ_API_KEY") or _get_key("GROW_API_KEY")

def _call_groq(messages, max_tokens=1200):
    k = _groq_key()
    if not k:
        return "Set GROQ_API_KEY in Streamlit Secrets to enable AI features."
    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages,
                  "temperature": 0.65, "max_tokens": max_tokens},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI Error: {e}"

# ══════════════════════════════════════════
# 1. DATA STORAGE
# ══════════════════════════════════════════
MARKETPLACE_FILE  = "marketplace_listings.json"
SELLER_FILE       = "seller_accounts.json"
PURCHASES_FILE    = "marketplace_purchases.json"

def _load(path):
    if os.path.exists(path):
        try:
            with open(path) as f: return json.load(f)
        except Exception: return {}
    return {}

def _save(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=2, default=str)

def load_listings():  return _load(MARKETPLACE_FILE)
def save_listings(d): _save(MARKETPLACE_FILE, d)
def load_sellers():   return _load(SELLER_FILE)
def save_sellers(d):  _save(SELLER_FILE, d)
def load_purchases(): return _load(PURCHASES_FILE)
def save_purchases(d): _save(PURCHASES_FILE, d)

def get_seller(email):
    return load_sellers().get(email.lower().strip())

def register_seller(email, name, bio, upi):
    sellers = load_sellers()
    key = email.lower().strip()
    if key not in sellers:
        sellers[key] = {
            "email": key, "name": name, "bio": bio, "upi": upi,
            "created_at": datetime.now().isoformat(), "listing_ids": [],
        }
        save_sellers(sellers)
    return sellers[key]

def update_seller(email, fields):
    sellers = load_sellers()
    key = email.lower().strip()
    if key in sellers:
        sellers[key].update(fields)
        save_sellers(sellers)

def add_listing(seller_email, listing):
    lid = secrets.token_hex(8)
    listings = load_listings()
    sellers  = load_sellers()
    se = load_sellers().get(seller_email.lower().strip(), {})
    listings[lid] = {**listing, "id": lid,
                     "seller_email": seller_email.lower().strip(),
                     "created_at": datetime.now().isoformat(),
                     "sales_count": 0, "active": True}
    save_listings(listings)
    key = seller_email.lower().strip()
    if key in sellers:
        sellers[key].setdefault("listing_ids", []).append(lid)
        save_sellers(sellers)
    return lid

def update_listing(lid, fields):
    listings = load_listings()
    if lid in listings:
        listings[lid].update(fields)
        save_listings(listings)

def get_seller_listings(email):
    listings = load_listings()
    return [v for v in listings.values()
            if v.get("seller_email") == email.lower().strip()]

def get_active_listings():
    listings = load_listings()
    return [v for v in listings.values() if v.get("active", True)]

def record_purchase(buyer_email, listing_id, amount):
    purchases = load_purchases()
    pid = secrets.token_hex(6)
    purchases[pid] = {
        "id": pid, "buyer_email": buyer_email.lower().strip(),
        "listing_id": listing_id, "amount": amount,
        "purchased_at": datetime.now().isoformat(),
    }
    save_purchases(purchases)
    listings = load_listings()
    if listing_id in listings:
        listings[listing_id]["sales_count"] = listings[listing_id].get("sales_count",0) + 1
        save_listings(listings)
    return pid

def get_buyer_purchases(buyer_email):
    purchases = load_purchases()
    listings  = load_listings()
    result = []
    for p in purchases.values():
        if p.get("buyer_email") == buyer_email.lower().strip():
            lid = p.get("listing_id","")
            p2 = dict(p)
            p2["listing"] = listings.get(lid, {})
            result.append(p2)
    return sorted(result, key=lambda x: x.get("purchased_at",""), reverse=True)

def get_seller_sales(seller_email):
    purchases = load_purchases()
    listings  = load_listings()
    seller_lids = {v["id"] for v in get_seller_listings(seller_email)}
    result = []
    for p in purchases.values():
        if p.get("listing_id") in seller_lids:
            p2 = dict(p)
            p2["listing"] = listings.get(p.get("listing_id",""), {})
            result.append(p2)
    return sorted(result, key=lambda x: x.get("purchased_at",""), reverse=True)

def has_purchased(buyer_email, listing_id):
    purchases = load_purchases()
    for p in purchases.values():
        if (p.get("buyer_email") == buyer_email.lower().strip()
                and p.get("listing_id") == listing_id):
            return True
    return False

# ══════════════════════════════════════════
# 2. CSS
# ══════════════════════════════════════════
MKT_CSS = """<style>
.mkt-hero {
    background: linear-gradient(135deg,#050d1f 0%,#0a1929 40%,#071a30 100%);
    border:1px solid rgba(0,212,255,0.2);border-radius:18px;
    padding:32px 36px;margin-bottom:24px;text-align:center;
}
.mkt-hero h1 {font-size:2rem;font-weight:900;color:#fff;margin:0;}
.mkt-hero h1 span {color:#00d4ff;}
.mkt-hero p  {color:#7fa8c9;font-size:0.95rem;margin:8px 0 0;}
.mkt-card {
    background:linear-gradient(145deg,#071525,#0a1e35);
    border:1px solid rgba(0,212,255,0.14);border-radius:14px;
    padding:18px;margin-bottom:4px;
    transition:border-color 0.2s,transform 0.2s;
}
.mkt-card:hover {border-color:rgba(0,212,255,0.4);transform:translateY(-2px);}
.mkt-card-type {
    display:inline-block;font-size:10px;font-weight:700;
    text-transform:uppercase;letter-spacing:0.6px;
    padding:3px 9px;border-radius:20px;margin-bottom:10px;
}
.type-ebook  {background:rgba(0,212,255,0.1);color:#00d4ff;border:1px solid rgba(0,212,255,0.3);}
.type-course {background:rgba(123,47,247,0.1);color:#a78bfa;border:1px solid rgba(123,47,247,0.3);}
.type-video  {background:rgba(255,68,102,0.1);color:#ff7096;border:1px solid rgba(255,68,102,0.3);}
.mkt-card-title {font-size:1rem;font-weight:800;color:#e8f4fd;margin:6px 0 4px;line-height:1.3;}
.mkt-card-seller {font-size:0.75rem;color:#4a9eff;margin-bottom:8px;}
.mkt-card-desc {
    font-size:0.8rem;color:#7fa8c9;line-height:1.5;margin-bottom:12px;
    display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;
}
.mkt-price-free {
    display:inline-block;background:rgba(0,255,136,0.1);color:#00ff88;
    border:1px solid rgba(0,255,136,0.3);border-radius:20px;
    padding:4px 12px;font-size:0.85rem;font-weight:800;
}
.mkt-price-paid {
    display:inline-block;background:rgba(255,170,0,0.1);color:#ffaa00;
    border:1px solid rgba(255,170,0,0.3);border-radius:20px;
    padding:4px 12px;font-size:0.85rem;font-weight:800;
}
.mkt-badge-purchased {
    display:inline-block;background:rgba(0,212,255,0.08);color:#00d4ff;
    border:1px solid rgba(0,212,255,0.25);border-radius:20px;
    padding:3px 10px;font-size:0.72rem;margin-left:6px;
}
.mkt-section-title {
    font-size:1.1rem;font-weight:800;color:#e8f4fd;
    margin:24px 0 14px;display:flex;align-items:center;gap:8px;
}
.seller-stat {
    background:linear-gradient(135deg,#060f1e,#071525);
    border:1px solid rgba(0,212,255,0.15);border-radius:12px;
    padding:18px 20px;text-align:center;margin-bottom:8px;
}
.seller-stat-n {font-size:2rem;font-weight:900;color:#00d4ff;}
.seller-stat-l {font-size:0.75rem;color:#7fa8c9;margin-top:2px;}
.seller-info-box {
    background:linear-gradient(135deg,rgba(0,212,255,0.04),rgba(74,158,255,0.04));
    border:1px solid rgba(0,212,255,0.18);border-radius:12px;
    padding:16px 18px;margin:12px 0;font-size:0.82rem;color:#7fa8c9;line-height:1.8;
}
.mkt-empty {text-align:center;padding:48px 24px;color:#4a5568;}
.mkt-empty-icon {font-size:3rem;margin-bottom:12px;}
.mkt-detail {
    background:linear-gradient(145deg,#060f1e,#071a30);
    border:2px solid rgba(0,212,255,0.18);border-radius:16px;padding:24px;margin-bottom:20px;
}
.mkt-detail-title {font-size:1.5rem;font-weight:900;color:#fff;margin-bottom:6px;}
</style>"""

# ══════════════════════════════════════════
# 3. STATE
# ══════════════════════════════════════════
def _init_state():
    for k, v in {
        "mkt_view": "browse",
        "mkt_selected_lid": "",
        "mkt_ai_prev_lid": "",
        "mkt_ai_prev_txt": "",
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

def _curr_email():
    u = st.session_state.get("user")
    return u.get("email","").lower().strip() if u and isinstance(u, dict) else ""

def _curr_name():
    u = st.session_state.get("user")
    return u.get("name","User") if u and isinstance(u, dict) else "User"

# ══════════════════════════════════════════
# 4. BROWSE
# ══════════════════════════════════════════
def _render_browse():
    email = _curr_email()
    col_s, col_t, col_p = st.columns([3,1.5,1.5])
    with col_s:
        search = st.text_input("", placeholder="Search books, courses...",
                               key="mkt_search", label_visibility="collapsed")
    with col_t:
        ftype = st.selectbox("", ["All Types","Ebook","Course","Video"],
                             key="mkt_ftype", label_visibility="collapsed")
    with col_p:
        fprice = st.selectbox("", ["All Prices","Free","Paid"],
                              key="mkt_fprice", label_visibility="collapsed")

    all_lst = get_active_listings()
    filtered = all_lst
    if search:
        s = search.lower()
        filtered = [l for l in filtered if
                    s in l.get("title","").lower() or
                    s in l.get("description","").lower() or
                    s in l.get("tags","").lower()]
    if ftype != "All Types":
        tmap = {"Ebook":"ebook","Course":"course","Video":"video"}
        filtered = [l for l in filtered if l.get("content_type","") == tmap.get(ftype,"")]
    if fprice == "Free":
        filtered = [l for l in filtered if l.get("price",0) == 0]
    elif fprice == "Paid":
        filtered = [l for l in filtered if l.get("price",0) > 0]

    st.markdown(f"**{len(filtered)}** listings found")

    if not filtered:
        st.markdown("""<div class="mkt-empty"><div class="mkt-empty-icon">📭</div>
        <div>No listings yet — be the first to publish!</div></div>""",
        unsafe_allow_html=True)
        return

    for type_lbl, type_key in [("📖 Ebooks","ebook"),("🎓 Courses","course"),("🎬 Video Series","video")]:
        group = [l for l in filtered if l.get("content_type","") == type_key]
        if not group: continue
        st.markdown(f"""<div class="mkt-section-title">{type_lbl}</div>""",
                    unsafe_allow_html=True)
        cols = st.columns(min(3, len(group)))
        for i, listing in enumerate(group):
            with cols[i % 3]:
                _render_card(listing, email)

def _render_card(listing, buyer_email):
    lid   = listing["id"]
    ctype = listing.get("content_type","ebook")
    price = listing.get("price",0)
    tc    = {"ebook":"type-ebook","course":"type-course","video":"type-video"}.get(ctype,"type-ebook")
    tl    = {"ebook":"📖 Ebook","course":"🎓 Course","video":"🎬 Video"}.get(ctype,"📖")
    price_html = (f'<span class="mkt-price-free">FREE</span>' if price==0
                  else f'<span class="mkt-price-paid">₹{price:,.0f}</span>')
    purchased = has_purchased(buyer_email, lid) if buyer_email else False
    pb    = '<span class="mkt-badge-purchased">✅ Owned</span>' if purchased else ""

    st.markdown(f"""<div class="mkt-card">
    <span class="mkt-card-type {tc}">{tl}</span>
    <div class="mkt-card-title">{listing.get("title","Untitled")}</div>
    <div class="mkt-card-seller">by {listing.get("seller_name","Seller")}</div>
    <div class="mkt-card-desc">{listing.get("description","")[:120]}</div>
    <div>{price_html}{pb}</div>
    </div>""", unsafe_allow_html=True)

    btn_lbl = ("✅ View" if purchased
               else ("🆓 Get Free" if price==0 else f"🛒 Buy ₹{price:,.0f}"))
    if st.button(btn_lbl, key=f"card_{lid}", use_container_width=True):
        st.session_state.mkt_selected_lid = lid
        st.session_state.mkt_view = "detail"
        st.rerun()

# ══════════════════════════════════════════
# 5. DETAIL
# ══════════════════════════════════════════
def _render_detail():
    lid      = st.session_state.mkt_selected_lid
    email    = _curr_email()
    listings = load_listings()
    listing  = listings.get(lid)

    if not listing:
        st.error("Listing not found.")
        if st.button("Back"):
            st.session_state.mkt_view = "browse"; st.rerun()
        return

    if st.button("Back to Marketplace", key="det_back"):
        st.session_state.mkt_view = "browse"; st.rerun()

    price     = listing.get("price",0)
    purchased = has_purchased(email, lid) if email else False
    ctype     = listing.get("content_type","ebook")
    tl        = {"ebook":"📖 Ebook","course":"🎓 Course","video":"🎬 Video Series"}.get(ctype,"📖")

    st.markdown(f"""<div class="mkt-detail">
    <div style="font-size:10px;font-weight:700;color:#4a9eff;text-transform:uppercase;
    letter-spacing:0.5px;margin-bottom:8px;">{tl}</div>
    <div class="mkt-detail-title">{listing.get("title","")}</div>
    <div style="font-size:0.82rem;color:#4a9eff;margin-bottom:4px;">
    by {listing.get("seller_name","")} &nbsp;·&nbsp;
    🛒 {listing.get("sales_count",0)} sales &nbsp;·&nbsp;
    📅 {listing.get("created_at","")[:10]}</div>
    </div>""", unsafe_allow_html=True)

    col_info, col_action = st.columns([2,1])

    with col_info:
        st.markdown("**📝 Description**")
        st.markdown(listing.get("description",""))
        if listing.get("tags"):
            tags_html = " ".join(f"`{t.strip()}`" for t in listing.get("tags","").split(","))
            st.markdown(f"**Tags:** {tags_html}")
        if listing.get("level"):
            lc = {"Beginner":"#00ff88","Intermediate":"#ffaa00","Advanced":"#ff4466"}.get(listing.get("level",""),"#7fa8c9")
            lv = listing.get("level","")
            st.markdown(f"**Level:** <span style='color:{lc};font-weight:700;'>{lv}</span>",
                        unsafe_allow_html=True)
        if listing.get("language"):
            lang_val = listing.get("language","")
            st.markdown(f"**Language:** {lang_val}")
        if listing.get("pages"):
            pages_val = listing.get("pages","")
            st.markdown(f"**Pages/Lessons:** {pages_val}")

        st.write("")
        if st.button("🤖 AI Preview/Summary", key=f"aiprev_{lid}"):
            with st.spinner("AI reading listing..."):
                prompt = f"""Create a 150-word compelling preview for this trading content listing:
Title: {listing.get("title","")}
Type: {tl} | Author: {listing.get("seller_name","")}
Description: {listing.get("description","")}
Tags: {listing.get("tags","")} | Level: {listing.get("level","")}

Write:
1. What You Will Learn (3 bullets)
2. Who Is This For (1 sentence)
3. Why Worth It (1 sentence)
Keep it honest and engaging."""
                reply = _call_groq([{"role":"user","content":prompt}], max_tokens=400)
                st.session_state.mkt_ai_prev_lid = lid
                st.session_state.mkt_ai_prev_txt = reply
                st.rerun()

        if st.session_state.mkt_ai_prev_lid == lid and st.session_state.mkt_ai_prev_txt:
            st.markdown("""<div style="background:#060f1e;border:1px solid rgba(0,212,255,0.15);
            border-radius:10px;padding:14px;margin-top:10px;">
            <div style="font-size:10px;color:#00d4ff;font-weight:700;
            text-transform:uppercase;margin-bottom:8px;">AI Preview</div>""",
            unsafe_allow_html=True)
            st.markdown(st.session_state.mkt_ai_prev_txt)
            st.markdown("</div>", unsafe_allow_html=True)

    with col_action:
        st.markdown("""<div style="background:linear-gradient(145deg,#060f1e,#071a30);
        border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:20px;">""",
        unsafe_allow_html=True)

        if price == 0:
            st.markdown('<div style="font-size:1.8rem;font-weight:900;color:#00ff88;">FREE</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:1.8rem;font-weight:900;color:#ffaa00;">₹{price:,.0f}</div>',
                        unsafe_allow_html=True)
        st.write("")

        if not email:
            st.warning("Login to access content.")
        elif purchased or price == 0:
            if purchased:
                st.success("✅ You own this")
            content_url = listing.get("content_url","")
            if content_url:
                st.link_button("📥 Open Content", content_url, use_container_width=True)
            else:
                st.info("Contact seller for access.")
            if price == 0 and not purchased:
                record_purchase(email, lid, 0)
                st.rerun()
        else:
            st.markdown(f"""<div style="font-size:0.78rem;color:#7fa8c9;margin-bottom:10px;">
            Pay via UPI: <b style="color:#00d4ff;">{listing.get("seller_upi","N/A")}</b></div>""",
            unsafe_allow_html=True)
            st.info("Pay seller directly, then confirm below.")
            if st.button("Confirm Purchase", key=f"confirm_{lid}",
                         type="primary", use_container_width=True):
                record_purchase(email, lid, price)
                st.success("Purchase confirmed! Access granted.")
                time.sleep(1); st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")
        st.markdown(f"""<div style="background:#060f1e;border:1px solid rgba(255,255,255,0.06);
        border-radius:10px;padding:14px;font-size:0.8rem;color:#7fa8c9;">
        <b style="color:#e8f4fd;">About the Seller</b><br>
        {listing.get("seller_name","")}<br>
        <span style="font-size:0.72rem;">{listing.get("seller_bio","")[:80]}</span>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════
# 6. MY LIBRARY
# ══════════════════════════════════════════
def _render_my_library():
    email = _curr_email()
    if not email:
        st.warning("Please login to view your library.")
        return

    purchases = get_buyer_purchases(email)
    st.markdown('<div class="mkt-section-title">📚 My Library</div>', unsafe_allow_html=True)

    if not purchases:
        st.markdown("""<div class="mkt-empty"><div class="mkt-empty-icon">📭</div>
        <div style="color:#7fa8c9;">No content yet. Browse marketplace and get books/courses.</div>
        </div>""", unsafe_allow_html=True)
        return

    for p in purchases:
        l = p.get("listing",{})
        if not l: continue
        amt  = p.get("amount",0)
        amt_txt = "FREE" if amt==0 else f"₹{amt:,.0f}"
        em   = {"ebook":"📖","course":"🎓","video":"🎬"}.get(l.get("content_type","ebook"),"📖")
        col_i, col_b = st.columns([4,1])
        with col_i:
            st.markdown(f"""<div style="background:#071525;border:1px solid rgba(0,212,255,0.1);
            border-radius:10px;padding:12px 16px;margin-bottom:8px;">
            <div style="font-weight:700;color:#e8f4fd;">{em} {l.get("title","")}</div>
            <div style="font-size:0.75rem;color:#4a9eff;">by {l.get("seller_name","")}</div>
            <div style="font-size:0.72rem;color:#556;margin-top:3px;">
            {p.get("purchased_at","")[:10]} · {amt_txt}</div>
            </div>""", unsafe_allow_html=True)
        with col_b:
            cl = l.get("content_url","")
            if cl:
                st.link_button("Open", cl, use_container_width=True)
            else:
                if st.button("View", key=f"libv_{p['id']}", use_container_width=True):
                    st.session_state.mkt_selected_lid = l.get("id","")
                    st.session_state.mkt_view = "detail"; st.rerun()

# ══════════════════════════════════════════
# 7. SELLER APPLY
# ══════════════════════════════════════════
def _render_seller_apply():
    email = _curr_email()
    name  = _curr_name()

    st.markdown('<div class="mkt-section-title">🏪 Become a Seller</div>', unsafe_allow_html=True)

    if not email:
        st.warning("Please login first to create a seller account.")
        return

    if get_seller(email):
        st.success("You already have a seller account!")
        if st.button("Go to Seller Dashboard", type="primary"):
            st.session_state.mkt_view = "seller_dash"; st.rerun()
        return

    st.markdown("""<div class="seller-info-box">
    <b style="color:#00d4ff;">How selling works:</b><br>
    1. Create your seller account (2 minutes)<br>
    2. List your ebooks/courses — set your own price (free or paid)<br>
    3. Buyers pay you DIRECTLY via UPI — FinSage takes 0% commission<br>
    4. Track all sales and buyers in your dashboard<br>
    <br>
    <b style="color:#ffaa00;">Note:</b> Deliver content via Google Drive, Gumroad, Notion, or any URL.
    </div>""", unsafe_allow_html=True)

    with st.form("seller_apply_form"):
        s_name = st.text_input("Your Display Name", value=name,
                               placeholder="Name buyers will see")
        s_bio  = st.text_area("Short Bio", height=80,
                              placeholder="e.g. Trader with 5+ years. Teaches options & technical analysis.")
        s_upi  = st.text_input("UPI ID (for receiving payments)",
                               placeholder="name@upi or phone@paytm")
        st.markdown('<div style="font-size:0.75rem;color:#556;">Buyers pay to this UPI. Make sure it is correct.</div>',
                    unsafe_allow_html=True)
        if st.form_submit_button("Create Seller Account", type="primary", use_container_width=True):
            if not s_name or not s_upi:
                st.error("Name and UPI ID are required.")
            else:
                register_seller(email, s_name, s_bio, s_upi)
                st.success("Seller account created! You can now list content.")
                time.sleep(1)
                st.session_state.mkt_view = "seller_dash"; st.rerun()

# ══════════════════════════════════════════
# 8. SELLER DASHBOARD
# ══════════════════════════════════════════
def _render_seller_dashboard():
    email  = _curr_email()
    seller = get_seller(email) if email else None

    if not seller:
        st.info("You don't have a seller account yet.")
        if st.button("Become a Seller", type="primary"):
            st.session_state.mkt_view = "seller_apply"; st.rerun()
        return

    my_listings = get_seller_listings(email)
    my_sales    = get_seller_sales(email)
    total_rev   = sum(s.get("amount",0) for s in my_sales)
    active_lst  = [l for l in my_listings if l.get("active",True)]

    st.markdown(f"### 🏪 {seller.get('name','')} — Seller Dashboard")

    c1,c2,c3,c4 = st.columns(4)
    for col, n, lbl in [
        (c1, len(active_lst), "Active Listings"),
        (c2, len(my_sales),   "Total Sales"),
        (c3, f"₹{total_rev:,.0f}", "Total Revenue"),
        (c4, len(set(s.get("buyer_email","") for s in my_sales)), "Unique Buyers"),
    ]:
        with col:
            st.markdown(f"""<div class="seller-stat">
            <div class="seller-stat-n">{n}</div>
            <div class="seller-stat-l">{lbl}</div></div>""", unsafe_allow_html=True)

    st.write("")
    tab_lst, tab_add, tab_sales, tab_settings = st.tabs(
        ["My Listings","Add Listing","Sales & Buyers","Settings"])

    # ── My Listings ──────────────────────
    with tab_lst:
        if not my_listings:
            st.markdown("""<div class="mkt-empty"><div class="mkt-empty-icon">📂</div>
            <div>No listings yet. Add your first!</div></div>""", unsafe_allow_html=True)
        else:
            for l in sorted(my_listings, key=lambda x: x.get("created_at",""), reverse=True):
                c_lbl, c_st, c_act = st.columns([3,2,1.5])
                active = l.get("active",True)
                with c_lbl:
                    price = l.get("price",0)
                    p_txt = "FREE" if price==0 else f"₹{price:,.0f}"
                    status_color = "#00ff88" if active else "#ff4466"
                    status_txt   = "Active" if active else "Paused"
                    st.markdown(f"""<div style="padding:8px 0;">
                    <div style="font-weight:700;color:#e8f4fd;">{l.get("title","")}</div>
                    <div style="font-size:0.75rem;color:#4a9eff;">{l.get("content_type","").title()} · {p_txt}
                    · <span style="color:{status_color};">{status_txt}</span></div>
                    </div>""", unsafe_allow_html=True)
                with c_st:
                    st.markdown(f"""<div style="padding:8px 0;font-size:0.8rem;color:#7fa8c9;">
                    🛒 {l.get("sales_count",0)} sales · {l.get("created_at","")[:10]}</div>""",
                    unsafe_allow_html=True)
                with c_act:
                    if active:
                        if st.button("Pause", key=f"pause_{l['id']}", use_container_width=True):
                            update_listing(l["id"],{"active":False}); st.rerun()
                    else:
                        if st.button("Activate", key=f"act_{l['id']}", use_container_width=True):
                            update_listing(l["id"],{"active":True}); st.rerun()
                st.markdown("<hr style='border-color:rgba(255,255,255,0.05);margin:4px 0;'>",
                            unsafe_allow_html=True)

    # ── Add Listing ──────────────────────
    with tab_add:
        _render_add_listing_form(seller)

    # ── Sales & Buyers ───────────────────
    with tab_sales:
        if not my_sales:
            st.markdown("""<div class="mkt-empty"><div class="mkt-empty-icon">💸</div>
            <div>No sales yet. Share your listings!</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"**{len(my_sales)} total sales · Revenue: ₹{total_rev:,.0f}**")
            st.write("")
            from collections import defaultdict
            by_lid = defaultdict(list)
            for s in my_sales: by_lid[s.get("listing_id","")].append(s)

            for lid2, sales in by_lid.items():
                l2  = sales[0].get("listing",{})
                rev = sum(s.get("amount",0) for s in sales)
                with st.expander(f"{l2.get('title','Listing')} — {len(sales)} buyers · ₹{rev:,.0f}"):
                    st.markdown("""<table style="width:100%;border-collapse:collapse;">
                    <tr style="color:#4a9eff;font-size:0.75rem;">
                    <th style="text-align:left;padding:6px;">Buyer Email</th>
                    <th style="text-align:left;padding:6px;">Date</th>
                    <th style="text-align:right;padding:6px;">Amount</th>
                    </tr>""", unsafe_allow_html=True)
                    for s in sorted(sales, key=lambda x: x.get("purchased_at",""), reverse=True):
                        amt = s.get("amount",0)
                        amt_txt = "FREE" if amt==0 else f"₹{amt:,.0f}"
                        st.markdown(f"""<tr style="border-top:1px solid rgba(255,255,255,0.05);">
                        <td style="padding:6px;font-size:0.8rem;color:#c9d8ea;">{s.get("buyer_email","")}</td>
                        <td style="padding:6px;font-size:0.75rem;color:#556;">{s.get("purchased_at","")[:10]}</td>
                        <td style="padding:6px;text-align:right;font-size:0.8rem;
                        color:{"#7fa8c9" if amt==0 else "#00ff88"};font-weight:700;">{amt_txt}</td>
                        </tr>""", unsafe_allow_html=True)
                    st.markdown("</table>", unsafe_allow_html=True)

    # ── Settings ─────────────────────────
    with tab_settings:
        with st.form("seller_settings_form"):
            s_n = st.text_input("Display Name", value=seller.get("name",""))
            s_b = st.text_area("Bio", value=seller.get("bio",""), height=80)
            s_u = st.text_input("UPI ID", value=seller.get("upi",""))
            if st.form_submit_button("Save Changes", type="primary"):
                update_seller(email, {"name":s_n,"bio":s_b,"upi":s_u})
                st.success("Profile updated!"); time.sleep(0.5); st.rerun()

# ══════════════════════════════════════════
# 9. ADD LISTING FORM
# ══════════════════════════════════════════
def _render_add_listing_form(seller):
    seller_email = seller.get("email","")
    seller_name  = seller.get("name","")
    seller_upi   = seller.get("upi","")

    st.markdown("""<div class="seller-info-box">
    <b>Tips for a great listing:</b><br>
    • Write a clear, benefit-focused title<br>
    • Description: say WHO it's for and WHAT they'll learn<br>
    • Add a Google Drive / Gumroad / Notion URL for content delivery<br>
    • Free listings get more downloads — consider pricing strategically
    </div>""", unsafe_allow_html=True)

    with st.form("add_listing_form", clear_on_submit=True):
        c_l, c_r = st.columns(2)
        with c_l:
            title   = st.text_input("Title *", placeholder="e.g. Options Trading Masterclass")
            c_type  = st.selectbox("Content Type *",["ebook","course","video"],
                                   format_func=lambda x: {"ebook":"📖 Ebook","course":"🎓 Course","video":"🎬 Video Series"}[x])
            price   = st.number_input("Price (₹) — 0 for Free", min_value=0, max_value=99999, value=0, step=50)
            level   = st.selectbox("Level",["Beginner","Intermediate","Advanced","All Levels"])
        with c_r:
            language    = st.text_input("Language", value="English/Hindi")
            pages       = st.text_input("Pages / Lessons", placeholder="e.g. 180 pages or 24 lessons")
            tags        = st.text_input("Tags (comma-separated)", placeholder="options, swing, technical analysis")
            content_url = st.text_input("Content URL", placeholder="Google Drive / Gumroad / Notion link")

        description = st.text_area("Description *", height=120,
                                   placeholder="What will buyers learn? Who is it for? What's included?")
        cover_emoji = st.text_input("Cover Emoji (optional)", value="📖", placeholder="Single emoji")

        if st.form_submit_button("Publish Listing", type="primary", use_container_width=True):
            if not title or not description:
                st.error("Title and description are required.")
            else:
                lid = add_listing(seller_email, {
                    "title": title, "description": description,
                    "content_type": c_type, "price": price,
                    "level": level, "language": language, "pages": pages,
                    "tags": tags, "content_url": content_url,
                    "cover_emoji": cover_emoji or "📖",
                    "seller_name": seller_name, "seller_upi": seller_upi,
                    "seller_bio": seller.get("bio",""),
                })
                st.success(f"Listing published! ID: {lid}")
                st.balloons()
                time.sleep(1.5); st.rerun()

# ══════════════════════════════════════════
# 10. MAIN ENTRY
# ══════════════════════════════════════════
def show_library_page():
    st.markdown(MKT_CSS, unsafe_allow_html=True)
    _init_state()

    email  = _curr_email()
    seller = get_seller(email) if email else None

    st.markdown("""<div class="mkt-hero">
    <h1>FinSage <span>Marketplace</span></h1>
    <p>📖 Ebooks · 🎓 Courses · 🎬 Video Series — By traders, for traders · 0% Commission</p>
    </div>""", unsafe_allow_html=True)

    # Nav bar
    nav_items = [("🛍️ Browse","browse"),("📚 My Library","my_library")]
    if seller:
        nav_items.append(("🏪 Dashboard","seller_dash"))
    nav_items.append(("➕ Sell Your Content","seller_apply"))

    view = st.session_state.mkt_view
    nav_cols = st.columns(len(nav_items))
    for i,(label,key) in enumerate(nav_items):
        with nav_cols[i]:
            btn_type = "primary" if view == key else "secondary"
            if st.button(label, key=f"mkt_nav_{key}", use_container_width=True, type=btn_type):
                st.session_state.mkt_view = key; st.rerun()

    st.markdown("<hr style='border-color:rgba(0,212,255,0.1);margin:16px 0 20px;'>",
                unsafe_allow_html=True)

    v = st.session_state.mkt_view
    if v == "browse":          _render_browse()
    elif v == "detail":        _render_detail()
    elif v == "my_library":    _render_my_library()
    elif v == "seller_apply":  _render_seller_apply()
    elif v == "seller_dash":   _render_seller_dashboard()
    else:                      _render_browse()
