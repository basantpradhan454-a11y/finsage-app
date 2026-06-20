"""
FinSage Marketplace — Ebook & Course Selling Platform
Features: Browse, Buy, Sell, Leaderboard, AI Ebook Builder
AI via Groq (GROW_API_KEY / GROQ_API_KEY from st.secrets)
"""
import streamlit as st
import os, json, time, secrets as _sec, re
from datetime import datetime
import requests

# ══════════════════════════════════════════════════════
# 0. GROQ API — reads from st.secrets correctly
# ══════════════════════════════════════════════════════
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

def _get_key(name):
    v = os.environ.get(name, "")
    if not v:
        try:
            v = st.secrets.get(name, "")
        except Exception:
            pass
    return v or ""

def _groq_key():
    return _get_key("GROW_API_KEY") or _get_key("GROQ_API_KEY")

def _call_groq(messages, max_tokens=1500, temperature=0.7):
    k = _groq_key()
    if not k:
        return "⚠️ API key not found. Please add GROW_API_KEY in Streamlit Secrets."
    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {k}",
                     "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages,
                  "temperature": temperature, "max_tokens": max_tokens},
            timeout=90,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ AI Error: {e}"

def _ai(prompt, system="", max_tokens=1500):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return _call_groq(msgs, max_tokens=max_tokens)

# ══════════════════════════════════════════════════════
# 1. DATA STORAGE (JSON, Firebase-compatible)
# ══════════════════════════════════════════════════════
MARKETPLACE_FILE = "marketplace_listings.json"
SELLER_FILE      = "seller_accounts.json"
PURCHASES_FILE   = "marketplace_purchases.json"
EBOOK_DRAFT_FILE = "ebook_drafts.json"

def _load(path):
    if os.path.exists(path):
        try:
            with open(path) as f: return json.load(f)
        except Exception: return {}
    return {}

def _save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

def load_listings():  return _load(MARKETPLACE_FILE)
def save_listings(d): _save(MARKETPLACE_FILE, d)
def load_sellers():   return _load(SELLER_FILE)
def save_sellers(d):  _save(SELLER_FILE, d)
def load_purchases(): return _load(PURCHASES_FILE)
def save_purchases(d): _save(PURCHASES_FILE, d)
def load_drafts():    return _load(EBOOK_DRAFT_FILE)
def save_drafts(d):   _save(EBOOK_DRAFT_FILE, d)

def get_seller(email):
    if not email: return None
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
    lid = _sec.token_hex(8)
    listings = load_listings()
    sellers  = load_sellers()
    listings[lid] = {**listing,
                     "id": lid,
                     "seller_email": seller_email.lower().strip(),
                     "created_at": datetime.now().isoformat(),
                     "sales_count": 0,
                     "active": True}
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
    pid = _sec.token_hex(6)
    purchases[pid] = {
        "id": pid,
        "buyer_email": buyer_email.lower().strip(),
        "listing_id": listing_id,
        "amount": amount,
        "purchased_at": datetime.now().isoformat(),
    }
    save_purchases(purchases)
    listings = load_listings()
    if listing_id in listings:
        listings[listing_id]["sales_count"] = (
            listings[listing_id].get("sales_count", 0) + 1)
        save_listings(listings)
    return pid

def get_buyer_purchases(buyer_email):
    purchases = load_purchases()
    listings  = load_listings()
    result = []
    for p in purchases.values():
        if p.get("buyer_email") == buyer_email.lower().strip():
            p2 = dict(p)
            p2["listing"] = listings.get(p.get("listing_id", ""), {})
            result.append(p2)
    return sorted(result, key=lambda x: x.get("purchased_at", ""), reverse=True)

def get_seller_sales(seller_email):
    purchases = load_purchases()
    listings  = load_listings()
    seller_lids = {v["id"] for v in get_seller_listings(seller_email)}
    result = []
    for p in purchases.values():
        if p.get("listing_id") in seller_lids:
            p2 = dict(p)
            p2["listing"] = listings.get(p.get("listing_id", ""), {})
            result.append(p2)
    return sorted(result, key=lambda x: x.get("purchased_at", ""), reverse=True)

def has_purchased(buyer_email, listing_id):
    if not buyer_email: return False
    purchases = load_purchases()
    for p in purchases.values():
        if (p.get("buyer_email") == buyer_email.lower().strip()
                and p.get("listing_id") == listing_id):
            return True
    return False

def get_leaderboard():
    """Return sorted list of sellers by total sales."""
    sellers   = load_sellers()
    listings  = load_listings()
    purchases = load_purchases()
    # count sales per seller
    counts = {}
    revenue = {}
    for p in purchases.values():
        lid = p.get("listing_id", "")
        if lid in listings:
            se = listings[lid].get("seller_email", "")
            counts[se]  = counts.get(se, 0) + 1
            revenue[se] = revenue.get(se, 0) + p.get("amount", 0)
    # build leaderboard
    board = []
    for email, seller in sellers.items():
        board.append({
            "email":   email,
            "name":    seller.get("name", ""),
            "bio":     seller.get("bio", ""),
            "sales":   counts.get(email, 0),
            "revenue": revenue.get(email, 0),
            "listings": sum(1 for l in listings.values()
                            if l.get("seller_email") == email
                            and l.get("active", True)),
        })
    return sorted(board, key=lambda x: x["sales"], reverse=True)

# ══════════════════════════════════════════════════════
# 2. LANGUAGE TRANSLATIONS
# ══════════════════════════════════════════════════════
_T = {
    "en": {
        "hero_title": "FinSage Marketplace",
        "hero_sub": "📖 Ebooks · 🎓 Courses · 🎬 Videos — By traders, for traders · 0% Commission",
        "browse": "🛍️ Browse",
        "my_library": "📚 My Library",
        "dashboard": "🏪 My Dashboard",
        "sell": "➕ Sell Content",
        "leaderboard": "🏆 Leaderboard",
        "build_ebook": "✍️ Build Ebook",
        "search_ph": "Search books, courses...",
        "all_types": "All Types",
        "all_prices": "All Prices",
        "free": "Free",
        "paid": "Paid",
        "listings_found": "listings found",
        "no_listings": "No listings yet — be the first to publish!",
        "get_free": "🆓 Get Free",
        "buy": "🛒 Buy",
        "view": "✅ View",
        "back": "← Back",
        "owned": "✅ Owned",
        "login_required": "Login to access content.",
        "confirm_purchase": "Confirm Purchase",
        "pay_via_upi": "Pay via UPI to seller:",
        "pay_note": "Pay seller directly, then confirm below.",
        "purchase_confirmed": "Purchase confirmed! Access granted.",
        "open_content": "📥 Open Content",
        "contact_seller": "Contact seller for access link.",
        "about_seller": "About the Seller",
        "ai_preview": "🤖 AI Preview",
        "gen_preview": "Generate AI Preview",
        "no_purchases": "No content yet. Browse marketplace and get books/courses.",
        "become_seller": "🏪 Become a Seller",
        "seller_exists": "You already have a seller account!",
        "go_dashboard": "Go to Seller Dashboard",
        "seller_how": "How selling works:",
        "seller_step1": "1. Create your seller account (2 minutes)",
        "seller_step2": "2. List your ebooks/courses — set your own price",
        "seller_step3": "3. Buyers pay you DIRECTLY via UPI — 0% commission",
        "seller_step4": "4. Track all sales and buyers in your dashboard",
        "seller_note": "Content delivery via Google Drive, Gumroad, Notion, etc.",
        "display_name": "Your Display Name",
        "bio": "Short Bio",
        "upi_id": "UPI ID (for payments)",
        "upi_note": "Buyers pay to this UPI. Make sure it is correct.",
        "create_account": "Create Seller Account",
        "name_upi_required": "Name and UPI ID are required.",
        "account_created": "Seller account created!",
        "no_seller": "You don't have a seller account yet.",
        "active_listings": "Active Listings",
        "total_sales": "Total Sales",
        "total_revenue": "Total Revenue",
        "unique_buyers": "Unique Buyers",
        "my_listings": "My Listings",
        "add_listing": "Add Listing",
        "sales_buyers": "Sales & Buyers",
        "settings": "Settings",
        "no_listings_yet": "No listings yet. Add your first!",
        "pause": "Pause",
        "activate": "Activate",
        "no_sales": "No sales yet. Share your listings!",
        "save_changes": "Save Changes",
        "profile_updated": "Profile updated!",
        "leaderboard_title": "🏆 Seller Leaderboard",
        "leaderboard_sub": "Top sellers ranked by total sales",
        "rank": "Rank",
        "seller": "Seller",
        "sales_count": "Sales",
        "revenue": "Revenue",
        "active_books": "Listings",
        "no_sellers": "No sellers yet. Be the first!",
        "build_title": "✍️ AI Ebook Builder",
        "build_sub": "Create a professional ebook step by step with AI",
        "your_drafts": "Your Drafts",
        "new_ebook": "New Ebook",
        "step1": "Step 1: Topic & Outline",
        "step2": "Step 2: Write Chapters",
        "step3": "Step 3: Preview & Publish",
        "ebook_topic": "Ebook Topic",
        "ebook_topic_ph": "e.g. Options Trading for Beginners",
        "target_audience": "Target Audience",
        "num_chapters": "Number of Chapters",
        "gen_outline": "Generate Outline with AI",
        "gen_chapter": "Generate Chapter with AI",
        "generating": "Generating...",
        "publish_listing": "Publish as Listing",
        "save_draft": "Save Draft",
        "draft_saved": "Draft saved!",
    },
    "hi": {
        "hero_title": "FinSage मार्केटप्लेस",
        "hero_sub": "📖 ईबुक · 🎓 कोर्स · 🎬 वीडियो — व्यापारियों द्वारा, व्यापारियों के लिए · 0% कमीशन",
        "browse": "🛍️ ब्राउज़ करें",
        "my_library": "📚 मेरी लाइब्रेरी",
        "dashboard": "🏪 मेरा डैशबोर्ड",
        "sell": "➕ सामग्री बेचें",
        "leaderboard": "🏆 लीडरबोर्ड",
        "build_ebook": "✍️ ईबुक बनाएं",
        "search_ph": "किताब, कोर्स खोजें...",
        "all_types": "सभी प्रकार",
        "all_prices": "सभी कीमत",
        "free": "मुफ्त",
        "paid": "पेड",
        "listings_found": "लिस्टिंग मिलीं",
        "no_listings": "अभी कोई लिस्टिंग नहीं — पहले प्रकाशित करें!",
        "get_free": "🆓 मुफ्त लें",
        "buy": "🛒 खरीदें",
        "view": "✅ देखें",
        "back": "← वापस",
        "owned": "✅ आपके पास है",
        "login_required": "सामग्री एक्सेस करने के लिए लॉगिन करें।",
        "confirm_purchase": "खरीद की पुष्टि करें",
        "pay_via_upi": "UPI से भुगतान करें:",
        "pay_note": "पहले भुगतान करें, फिर नीचे कन्फर्म करें।",
        "purchase_confirmed": "खरीद की पुष्टि! एक्सेस मिल गई।",
        "open_content": "📥 सामग्री खोलें",
        "contact_seller": "एक्सेस के लिए विक्रेता से संपर्क करें।",
        "about_seller": "विक्रेता के बारे में",
        "ai_preview": "🤖 AI प्रीव्यू",
        "gen_preview": "AI से प्रीव्यू बनाएं",
        "no_purchases": "अभी कोई सामग्री नहीं। मार्केटप्लेस से किताब/कोर्स लें।",
        "become_seller": "🏪 विक्रेता बनें",
        "seller_exists": "आपका विक्रेता खाता पहले से है!",
        "go_dashboard": "डैशबोर्ड पर जाएं",
        "seller_how": "बेचना कैसे काम करता है:",
        "seller_step1": "1. विक्रेता खाता बनाएं (2 मिनट)",
        "seller_step2": "2. ईबुक/कोर्स लिस्ट करें — अपनी कीमत तय करें",
        "seller_step3": "3. खरीदार सीधे UPI से भुगतान — 0% कमीशन",
        "seller_step4": "4. डैशबोर्ड में सभी बिक्री और खरीदार देखें",
        "seller_note": "सामग्री: Google Drive, Gumroad, Notion आदि से दें।",
        "display_name": "आपका नाम (खरीदारों को दिखेगा)",
        "bio": "संक्षिप्त परिचय",
        "upi_id": "UPI ID (भुगतान के लिए)",
        "upi_note": "खरीदार इस UPI पर भुगतान करेंगे।",
        "create_account": "विक्रेता खाता बनाएं",
        "name_upi_required": "नाम और UPI ID जरूरी है।",
        "account_created": "विक्रेता खाता बना लिया!",
        "no_seller": "आपका अभी कोई विक्रेता खाता नहीं है।",
        "active_listings": "सक्रिय लिस्टिंग",
        "total_sales": "कुल बिक्री",
        "total_revenue": "कुल कमाई",
        "unique_buyers": "अनूठे खरीदार",
        "my_listings": "मेरी लिस्टिंग",
        "add_listing": "लिस्टिंग जोड़ें",
        "sales_buyers": "बिक्री और खरीदार",
        "settings": "सेटिंग",
        "no_listings_yet": "अभी कोई लिस्टिंग नहीं। पहली जोड़ें!",
        "pause": "रोकें",
        "activate": "चालू करें",
        "no_sales": "अभी कोई बिक्री नहीं। अपनी लिस्टिंग शेयर करें!",
        "save_changes": "बदलाव सहेजें",
        "profile_updated": "प्रोफ़ाइल अपडेट हुई!",
        "leaderboard_title": "🏆 विक्रेता लीडरबोर्ड",
        "leaderboard_sub": "सर्वाधिक बिक्री वाले विक्रेता",
        "rank": "रैंक",
        "seller": "विक्रेता",
        "sales_count": "बिक्री",
        "revenue": "कमाई",
        "active_books": "लिस्टिंग",
        "no_sellers": "अभी कोई विक्रेता नहीं। पहले बनें!",
        "build_title": "✍️ AI ईबुक बिल्डर",
        "build_sub": "AI की मदद से चरण-दर-चरण प्रोफेशनल ईबुक बनाएं",
        "your_drafts": "आपके ड्राफ्ट",
        "new_ebook": "नई ईबुक",
        "step1": "चरण 1: विषय और आउटलाइन",
        "step2": "चरण 2: अध्याय लिखें",
        "step3": "चरण 3: प्रीव्यू और प्रकाशित करें",
        "ebook_topic": "ईबुक विषय",
        "ebook_topic_ph": "जैसे: शुरुआती लोगों के लिए ऑप्शंस ट्रेडिंग",
        "target_audience": "लक्षित पाठक",
        "num_chapters": "अध्यायों की संख्या",
        "gen_outline": "AI से आउटलाइन बनाएं",
        "gen_chapter": "AI से अध्याय लिखें",
        "generating": "बन रहा है...",
        "publish_listing": "लिस्टिंग के रूप में प्रकाशित करें",
        "save_draft": "ड्राफ्ट सहेजें",
        "draft_saved": "ड्राफ्ट सहेज लिया!",
    },
}

# Add fallback for other languages (use English)
for _lang in ["te","ta","bn","mr","pa","gu","es","fr"]:
    _T[_lang] = _T["en"]

def _t(key):
    """Get translated string for current user language."""
    lang = st.session_state.get("user_lang", "en")
    return _T.get(lang, _T["en"]).get(key, _T["en"].get(key, key))

# ══════════════════════════════════════════════════════
# 3. CSS
# ══════════════════════════════════════════════════════
MKT_CSS = """<style>
.mkt-hero{background:linear-gradient(135deg,#050d1f 0%,#0a1929 40%,#071a30 100%);
border:1px solid rgba(0,212,255,0.2);border-radius:18px;padding:28px 32px;
margin-bottom:20px;text-align:center;}
.mkt-hero h1{font-size:1.9rem;font-weight:900;color:#fff;margin:0;}
.mkt-hero h1 span{color:#00d4ff;}
.mkt-hero p{color:#7fa8c9;font-size:0.9rem;margin:6px 0 0;}
.mkt-card{background:linear-gradient(145deg,#071525,#0a1e35);
border:1px solid rgba(0,212,255,0.14);border-radius:14px;padding:16px;
margin-bottom:4px;transition:border-color .2s,transform .2s;}
.mkt-card:hover{border-color:rgba(0,212,255,0.4);transform:translateY(-2px);}
.mkt-card-type{display:inline-block;font-size:9px;font-weight:700;
text-transform:uppercase;letter-spacing:.6px;padding:3px 8px;
border-radius:20px;margin-bottom:8px;}
.type-ebook{background:rgba(0,212,255,.1);color:#00d4ff;border:1px solid rgba(0,212,255,.3);}
.type-course{background:rgba(123,47,247,.1);color:#a78bfa;border:1px solid rgba(123,47,247,.3);}
.type-video{background:rgba(255,68,102,.1);color:#ff7096;border:1px solid rgba(255,68,102,.3);}
.mkt-card-title{font-size:.95rem;font-weight:800;color:#e8f4fd;margin:4px 0;line-height:1.3;}
.mkt-card-seller{font-size:.72rem;color:#4a9eff;margin-bottom:6px;}
.mkt-card-desc{font-size:.78rem;color:#7fa8c9;line-height:1.4;margin-bottom:10px;
display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;}
.mkt-price-free{display:inline-block;background:rgba(0,255,136,.1);color:#00ff88;
border:1px solid rgba(0,255,136,.3);border-radius:20px;padding:3px 10px;
font-size:.82rem;font-weight:800;}
.mkt-price-paid{display:inline-block;background:rgba(255,170,0,.1);color:#ffaa00;
border:1px solid rgba(255,170,0,.3);border-radius:20px;padding:3px 10px;
font-size:.82rem;font-weight:800;}
.mkt-badge-owned{display:inline-block;background:rgba(0,212,255,.08);color:#00d4ff;
border:1px solid rgba(0,212,255,.25);border-radius:20px;padding:2px 8px;
font-size:.7rem;margin-left:5px;}
.mkt-section-title{font-size:1rem;font-weight:800;color:#e8f4fd;
margin:20px 0 12px;display:flex;align-items:center;gap:6px;}
.seller-stat{background:linear-gradient(135deg,#060f1e,#071525);
border:1px solid rgba(0,212,255,.15);border-radius:12px;padding:16px 18px;
text-align:center;margin-bottom:8px;}
.seller-stat-n{font-size:1.8rem;font-weight:900;color:#00d4ff;}
.seller-stat-l{font-size:.72rem;color:#7fa8c9;margin-top:2px;}
.info-box{background:linear-gradient(135deg,rgba(0,212,255,.03),rgba(74,158,255,.03));
border:1px solid rgba(0,212,255,.16);border-radius:12px;padding:14px 16px;
margin:10px 0;font-size:.8rem;color:#7fa8c9;line-height:1.8;}
.mkt-empty{text-align:center;padding:40px 20px;color:#4a5568;}
.mkt-empty-icon{font-size:2.5rem;margin-bottom:10px;}
.mkt-detail{background:linear-gradient(145deg,#060f1e,#071a30);
border:2px solid rgba(0,212,255,.18);border-radius:16px;padding:20px;margin-bottom:16px;}
.mkt-detail-title{font-size:1.4rem;font-weight:900;color:#fff;margin-bottom:4px;}
.lb-row{background:#071525;border:1px solid rgba(0,212,255,.1);border-radius:10px;
padding:12px 16px;margin:6px 0;display:flex;align-items:center;gap:12px;}
.lb-rank{font-size:1.3rem;font-weight:900;width:40px;text-align:center;}
.lb-name{font-size:.9rem;font-weight:700;color:#e8f4fd;}
.lb-sub{font-size:.72rem;color:#7fa8c9;}
.lb-stats{margin-left:auto;text-align:right;}
.lb-sales{font-size:.9rem;font-weight:800;color:#00ff88;}
.lb-rev{font-size:.72rem;color:#ffaa00;}
.ebook-step{background:#060f1e;border:1px solid rgba(0,212,255,.15);
border-radius:12px;padding:18px;margin:10px 0;}
.ebook-step-title{font-size:.85rem;font-weight:700;color:#00d4ff;
text-transform:uppercase;letter-spacing:.4px;margin-bottom:10px;}
.chapter-box{background:#071525;border:1px solid rgba(0,212,255,.12);
border-radius:10px;padding:14px;margin:8px 0;font-size:.82rem;color:#c9d8ea;
line-height:1.7;white-space:pre-wrap;}
</style>"""

# ══════════════════════════════════════════════════════
# 4. STATE
# ══════════════════════════════════════════════════════
def _init_state():
    for k, v in {
        "mkt_view": "browse",
        "mkt_sel_lid": "",
        "mkt_ai_lid": "",
        "mkt_ai_txt": "",
        "mkt_eb_draft_id": "",
        "mkt_eb_step": "topic",
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

def _email():
    u = st.session_state.get("user")
    return u.get("email", "").lower().strip() if u and isinstance(u, dict) else ""

def _uname():
    u = st.session_state.get("user")
    return u.get("name", "User") if u and isinstance(u, dict) else "User"

# ══════════════════════════════════════════════════════
# 5. BROWSE
# ══════════════════════════════════════════════════════
def _render_browse():
    email = _email()
    lang  = st.session_state.get("user_lang", "en")

    col_s, col_t, col_p = st.columns([3, 1.5, 1.5])
    with col_s:
        search = st.text_input("", placeholder=_t("search_ph"),
                               key="mkt_search", label_visibility="collapsed")
    with col_t:
        type_opts = [_t("all_types"), "Ebook", "Course", "Video"]
        ftype = st.selectbox("", type_opts, key="mkt_ftype",
                             label_visibility="collapsed")
    with col_p:
        price_opts = [_t("all_prices"), _t("free"), _t("paid")]
        fprice = st.selectbox("", price_opts, key="mkt_fprice",
                              label_visibility="collapsed")

    all_lst = get_active_listings()
    filtered = all_lst
    if search:
        s = search.lower()
        filtered = [l for l in filtered if
                    s in l.get("title", "").lower() or
                    s in l.get("description", "").lower() or
                    s in l.get("tags", "").lower()]
    if ftype not in (_t("all_types"), "All Types"):
        tmap = {"Ebook": "ebook", "Course": "course", "Video": "video"}
        filtered = [l for l in filtered if
                    l.get("content_type", "") == tmap.get(ftype, ftype.lower())]
    if fprice in (_t("free"), "Free"):
        filtered = [l for l in filtered if l.get("price", 0) == 0]
    elif fprice in (_t("paid"), "Paid"):
        filtered = [l for l in filtered if l.get("price", 0) > 0]

    st.markdown(f"**{len(filtered)}** {_t('listings_found')}")

    if not filtered:
        st.markdown(f"""<div class="mkt-empty">
        <div class="mkt-empty-icon">📭</div>
        <div>{_t('no_listings')}</div></div>""", unsafe_allow_html=True)
        return

    type_groups = [("📖 Ebooks", "ebook"), ("🎓 Courses", "course"), ("🎬 Videos", "video")]
    for type_lbl, type_key in type_groups:
        group = [l for l in filtered if l.get("content_type", "") == type_key]
        if not group: continue
        st.markdown(f'<div class="mkt-section-title">{type_lbl}</div>',
                    unsafe_allow_html=True)
        cols = st.columns(min(3, len(group)))
        for i, listing in enumerate(group):
            with cols[i % 3]:
                _render_card(listing, email)

def _render_card(listing, buyer_email):
    lid   = listing["id"]
    ctype = listing.get("content_type", "ebook")
    price = listing.get("price", 0)
    tc    = {"ebook": "type-ebook", "course": "type-course",
             "video": "type-video"}.get(ctype, "type-ebook")
    tl    = {"ebook": "📖 Ebook", "course": "🎓 Course",
             "video": "🎬 Video"}.get(ctype, "📖")
    price_html = (f'<span class="mkt-price-free">{_t("free").upper()}</span>'
                  if price == 0
                  else f'<span class="mkt-price-paid">₹{price:,.0f}</span>')
    purchased  = has_purchased(buyer_email, lid)
    badge      = f'<span class="mkt-badge-owned">{_t("owned")}</span>' if purchased else ""
    desc       = listing.get("description", "")[:110]

    st.markdown(f"""<div class="mkt-card">
    <span class="mkt-card-type {tc}">{tl}</span>
    <div class="mkt-card-title">{listing.get('title','')}</div>
    <div class="mkt-card-seller">by {listing.get('seller_name','')}</div>
    <div class="mkt-card-desc">{desc}</div>
    <div>{price_html}{badge}</div></div>""", unsafe_allow_html=True)

    if purchased:
        btn_lbl = _t("view")
    elif price == 0:
        btn_lbl = _t("get_free")
    else:
        btn_lbl = f"{_t('buy')} ₹{price:,.0f}"

    if st.button(btn_lbl, key=f"card_{lid}", use_container_width=True):
        st.session_state.mkt_sel_lid = lid
        st.session_state.mkt_view    = "detail"
        st.rerun()

# ══════════════════════════════════════════════════════
# 6. DETAIL
# ══════════════════════════════════════════════════════
def _render_detail():
    lid      = st.session_state.mkt_sel_lid
    email    = _email()
    listings = load_listings()
    listing  = listings.get(lid)

    if not listing:
        st.error("Listing not found.")
        if st.button(_t("back")):
            st.session_state.mkt_view = "browse"; st.rerun()
        return

    if st.button(_t("back"), key="det_back"):
        st.session_state.mkt_view = "browse"
        st.session_state.mkt_ai_lid = ""
        st.rerun()

    price     = listing.get("price", 0)
    purchased = has_purchased(email, lid)
    ctype     = listing.get("content_type", "ebook")
    tl        = {"ebook": "📖 Ebook", "course": "🎓 Course",
                 "video": "🎬 Video Series"}.get(ctype, "📖")

    st.markdown(f"""<div class="mkt-detail">
    <div style="font-size:9px;font-weight:700;color:#4a9eff;text-transform:uppercase;
    letter-spacing:.5px;margin-bottom:6px;">{tl}</div>
    <div class="mkt-detail-title">{listing.get('title','')}</div>
    <div style="font-size:.8rem;color:#4a9eff;margin-bottom:4px;">
    by {listing.get('seller_name','')} &nbsp;·&nbsp;
    🛒 {listing.get('sales_count',0)} sales &nbsp;·&nbsp;
    📅 {listing.get('created_at','')[:10]}</div></div>""",
    unsafe_allow_html=True)

    col_i, col_a = st.columns([2, 1])

    with col_i:
        st.markdown("**📝 Description**")
        st.markdown(listing.get("description", ""))
        if listing.get("tags"):
            tags_md = " ".join(f"`{t.strip()}`"
                               for t in listing.get("tags", "").split(","))
            st.markdown(f"**Tags:** {tags_md}")
        level_val = listing.get("level", "")
        if level_val:
            lc = {"Beginner": "#00ff88", "Intermediate": "#ffaa00",
                  "Advanced": "#ff4466"}.get(level_val, "#7fa8c9")
            st.markdown(f"**Level:** <span style='color:{lc};font-weight:700;'>"
                        f"{level_val}</span>", unsafe_allow_html=True)
        lang_val = listing.get("language", "")
        if lang_val:
            st.markdown(f"**Language:** {lang_val}")
        pages_val = listing.get("pages", "")
        if pages_val:
            st.markdown(f"**Pages/Lessons:** {pages_val}")

        st.write("")
        if st.button(_t("gen_preview"), key=f"aiprev_{lid}"):
            with st.spinner(_t("generating")):
                prompt = (f"Create a 150-word compelling preview for this trading content:\n"
                          f"Title: {listing.get('title','')}\nType: {tl}\n"
                          f"Author: {listing.get('seller_name','')}\n"
                          f"Description: {listing.get('description','')}\n"
                          f"Tags: {listing.get('tags','')}\nLevel: {level_val}\n\n"
                          f"Write: 1) What You Will Learn (3 bullets) "
                          f"2) Who Is This For (1 line) 3) Why Worth It (1 line)")
                reply = _ai(prompt, max_tokens=400)
                st.session_state.mkt_ai_lid = lid
                st.session_state.mkt_ai_txt = reply
                st.rerun()

        if (st.session_state.mkt_ai_lid == lid
                and st.session_state.mkt_ai_txt):
            st.markdown("""<div style="background:#060f1e;border:1px solid
            rgba(0,212,255,.15);border-radius:10px;padding:14px;margin-top:10px;">
            <div style="font-size:9px;color:#00d4ff;font-weight:700;
            text-transform:uppercase;margin-bottom:6px;">🤖 AI Preview</div>""",
            unsafe_allow_html=True)
            st.markdown(st.session_state.mkt_ai_txt)
            st.markdown("</div>", unsafe_allow_html=True)

    with col_a:
        st.markdown("""<div style="background:linear-gradient(145deg,#060f1e,#071a30);
        border:1px solid rgba(0,212,255,.2);border-radius:14px;padding:18px;">""",
        unsafe_allow_html=True)

        if price == 0:
            st.markdown(f'<div style="font-size:1.7rem;font-weight:900;'
                        f'color:#00ff88;">{_t("free").upper()}</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:1.7rem;font-weight:900;'
                        f'color:#ffaa00;">₹{price:,.0f}</div>',
                        unsafe_allow_html=True)
        st.write("")

        if not email:
            st.warning(_t("login_required"))
        elif purchased or price == 0:
            if purchased:
                st.success(_t("owned"))
            content_url = listing.get("content_url", "")
            if content_url:
                st.link_button(_t("open_content"), content_url,
                               use_container_width=True)
            else:
                st.info(_t("contact_seller"))
            if price == 0 and not purchased:
                record_purchase(email, lid, 0)
                st.rerun()
        else:
            upi = listing.get("seller_upi", "N/A")
            st.markdown(f'<div style="font-size:.76rem;color:#7fa8c9;margin-bottom:8px;">'
                        f'{_t("pay_via_upi")} <b style="color:#00d4ff;">{upi}</b></div>',
                        unsafe_allow_html=True)
            st.info(_t("pay_note"))
            if st.button(_t("confirm_purchase"), key=f"confirm_{lid}",
                         type="primary", use_container_width=True):
                record_purchase(email, lid, price)
                st.success(_t("purchase_confirmed"))
                time.sleep(1); st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")
        seller_bio = listing.get("seller_bio", "")[:80]
        st.markdown(f"""<div style="background:#060f1e;border:1px solid
        rgba(255,255,255,.06);border-radius:10px;padding:12px;
        font-size:.78rem;color:#7fa8c9;">
        <b style="color:#e8f4fd;">{_t('about_seller')}</b><br>
        {listing.get('seller_name','')}<br>
        <span style="font-size:.7rem;">{seller_bio}</span></div>""",
        unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# 7. MY LIBRARY
# ══════════════════════════════════════════════════════
def _render_my_library():
    email = _email()
    if not email:
        st.warning(_t("login_required"))
        return
    purchases = get_buyer_purchases(email)
    st.markdown(f'<div class="mkt-section-title">{_t("my_library")}</div>',
                unsafe_allow_html=True)
    if not purchases:
        st.markdown(f"""<div class="mkt-empty">
        <div class="mkt-empty-icon">📭</div>
        <div style="color:#7fa8c9;">{_t('no_purchases')}</div></div>""",
        unsafe_allow_html=True)
        return
    for p in purchases:
        l = p.get("listing", {})
        if not l: continue
        amt     = p.get("amount", 0)
        amt_txt = _t("free").upper() if amt == 0 else f"₹{amt:,.0f}"
        em      = {"ebook": "📖", "course": "🎓", "video": "🎬"}.get(
                   l.get("content_type", "ebook"), "📖")
        col_i, col_b = st.columns([4, 1])
        with col_i:
            st.markdown(f"""<div style="background:#071525;border:1px solid
            rgba(0,212,255,.1);border-radius:10px;padding:10px 14px;margin-bottom:8px;">
            <div style="font-weight:700;color:#e8f4fd;">{em} {l.get('title','')}</div>
            <div style="font-size:.72rem;color:#4a9eff;">by {l.get('seller_name','')}</div>
            <div style="font-size:.7rem;color:#556;margin-top:2px;">
            {p.get('purchased_at','')[:10]} · {amt_txt}</div></div>""",
            unsafe_allow_html=True)
        with col_b:
            cl = l.get("content_url", "")
            if cl:
                st.link_button("Open", cl, use_container_width=True)
            else:
                if st.button(_t("view"), key=f"libv_{p['id']}",
                             use_container_width=True):
                    st.session_state.mkt_sel_lid = l.get("id", "")
                    st.session_state.mkt_view    = "detail"
                    st.rerun()

# ══════════════════════════════════════════════════════
# 8. LEADERBOARD
# ══════════════════════════════════════════════════════
def _render_leaderboard():
    st.markdown(f'<div class="mkt-section-title">{_t("leaderboard_title")}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:.8rem;color:#7fa8c9;margin-bottom:16px;">'
                f'{_t("leaderboard_sub")}</div>', unsafe_allow_html=True)

    board = get_leaderboard()
    if not board:
        st.markdown(f"""<div class="mkt-empty">
        <div class="mkt-empty-icon">🏆</div>
        <div>{_t('no_sellers')}</div></div>""", unsafe_allow_html=True)
        return

    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(board):
        rank_icon = medals[i] if i < 3 else f"#{i+1}"
        rev_txt   = f"₹{row['revenue']:,.0f}" if row['revenue'] > 0 else "—"
        st.markdown(f"""<div class="lb-row">
        <div class="lb-rank">{rank_icon}</div>
        <div>
          <div class="lb-name">{row['name']}</div>
          <div class="lb-sub">{row['bio'][:50] if row['bio'] else ''}</div>
          <div style="font-size:.68rem;color:#556;margin-top:2px;">
          📚 {row['listings']} listings</div>
        </div>
        <div class="lb-stats">
          <div class="lb-sales">{row['sales']} {_t('sales_count').lower()}</div>
          <div class="lb-rev">{rev_txt}</div>
        </div></div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# 9. SELLER APPLY
# ══════════════════════════════════════════════════════
def _render_seller_apply():
    email = _email()
    if not email:
        st.warning(_t("login_required"))
        return
    st.markdown(f'<div class="mkt-section-title">{_t("become_seller")}</div>',
                unsafe_allow_html=True)
    if get_seller(email):
        st.success(_t("seller_exists"))
        if st.button(_t("go_dashboard"), type="primary"):
            st.session_state.mkt_view = "seller_dash"; st.rerun()
        return
    st.markdown(f"""<div class="info-box">
    <b style="color:#00d4ff;">{_t('seller_how')}</b><br>
    {_t('seller_step1')}<br>
    {_t('seller_step2')}<br>
    {_t('seller_step3')}<br>
    {_t('seller_step4')}<br>
    <br><b style="color:#ffaa00;">Note:</b> {_t('seller_note')}
    </div>""", unsafe_allow_html=True)

    with st.form("seller_apply_form"):
        s_name = st.text_input(_t("display_name"), value=_uname())
        s_bio  = st.text_area(_t("bio"), height=80)
        s_upi  = st.text_input(_t("upi_id"))
        st.markdown(f'<div style="font-size:.72rem;color:#556;">{_t("upi_note")}</div>',
                    unsafe_allow_html=True)
        if st.form_submit_button(_t("create_account"), type="primary",
                                 use_container_width=True):
            if not s_name or not s_upi:
                st.error(_t("name_upi_required"))
            else:
                register_seller(email, s_name, s_bio, s_upi)
                st.success(_t("account_created"))
                time.sleep(1)
                st.session_state.mkt_view = "seller_dash"; st.rerun()

# ══════════════════════════════════════════════════════
# 10. SELLER DASHBOARD
# ══════════════════════════════════════════════════════
def _render_seller_dashboard():
    email  = _email()
    seller = get_seller(email) if email else None
    if not seller:
        st.info(_t("no_seller"))
        if st.button(_t("become_seller"), type="primary"):
            st.session_state.mkt_view = "seller_apply"; st.rerun()
        return

    my_listings = get_seller_listings(email)
    my_sales    = get_seller_sales(email)
    total_rev   = sum(s.get("amount", 0) for s in my_sales)
    active_lst  = [l for l in my_listings if l.get("active", True)]

    st.markdown(f"### 🏪 {seller.get('name','')} — {_t('dashboard')}")

    c1, c2, c3, c4 = st.columns(4)
    for col, n, lbl in [
        (c1, len(active_lst),                                     _t("active_listings")),
        (c2, len(my_sales),                                       _t("total_sales")),
        (c3, f"₹{total_rev:,.0f}",                               _t("total_revenue")),
        (c4, len(set(s.get("buyer_email","") for s in my_sales)), _t("unique_buyers")),
    ]:
        with col:
            st.markdown(f"""<div class="seller-stat">
            <div class="seller-stat-n">{n}</div>
            <div class="seller-stat-l">{lbl}</div></div>""",
            unsafe_allow_html=True)

    st.write("")
    tab_lst, tab_add, tab_sales, tab_sets = st.tabs([
        _t("my_listings"), _t("add_listing"),
        _t("sales_buyers"), _t("settings"),
    ])

    with tab_lst:
        if not my_listings:
            st.markdown(f"""<div class="mkt-empty">
            <div class="mkt-empty-icon">📂</div>
            <div>{_t('no_listings_yet')}</div></div>""",
            unsafe_allow_html=True)
        else:
            for l in sorted(my_listings,
                             key=lambda x: x.get("created_at",""), reverse=True):
                ca, cb, cc = st.columns([3, 2, 1.5])
                active = l.get("active", True)
                with ca:
                    p    = l.get("price", 0)
                    ptxt = _t("free").upper() if p == 0 else f"₹{p:,.0f}"
                    sc   = "#00ff88" if active else "#ff4466"
                    st_lbl = _t("activate").replace("✓","") if active else _t("pause")
                    st.markdown(f"""<div style="padding:8px 0;">
                    <div style="font-weight:700;color:#e8f4fd;">{l.get('title','')}</div>
                    <div style="font-size:.72rem;color:#4a9eff;">
                    {l.get('content_type','').title()} · {ptxt}
                    · <span style="color:{sc};">{'Active' if active else 'Paused'}</span>
                    </div></div>""", unsafe_allow_html=True)
                with cb:
                    st.markdown(f"""<div style="padding:8px 0;font-size:.78rem;color:#7fa8c9;">
                    🛒 {l.get('sales_count',0)} sales
                    · {l.get('created_at','')[:10]}</div>""",
                    unsafe_allow_html=True)
                with cc:
                    if active:
                        if st.button(_t("pause"), key=f"pause_{l['id']}",
                                     use_container_width=True):
                            update_listing(l["id"], {"active": False}); st.rerun()
                    else:
                        if st.button(_t("activate"), key=f"act_{l['id']}",
                                     use_container_width=True):
                            update_listing(l["id"], {"active": True}); st.rerun()
                st.markdown(
                    "<hr style='border-color:rgba(255,255,255,.05);margin:4px 0;'>",
                    unsafe_allow_html=True)

    with tab_add:
        _render_add_listing_form(seller)

    with tab_sales:
        if not my_sales:
            st.markdown(f"""<div class="mkt-empty">
            <div class="mkt-empty-icon">💸</div>
            <div>{_t('no_sales')}</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"**{len(my_sales)} {_t('total_sales').lower()} · "
                        f"{_t('total_revenue')}: ₹{total_rev:,.0f}**")
            st.write("")
            from collections import defaultdict
            by_lid = defaultdict(list)
            for s in my_sales: by_lid[s.get("listing_id", "")].append(s)
            for lid2, sales in by_lid.items():
                l2  = sales[0].get("listing", {})
                rev = sum(s.get("amount", 0) for s in sales)
                with st.expander(
                    f"{l2.get('title','Listing')} — {len(sales)} "
                    f"{_t('unique_buyers').lower()} · ₹{rev:,.0f}"
                ):
                    st.markdown(f"""<table style="width:100%;border-collapse:collapse;">
                    <tr style="color:#4a9eff;font-size:.73rem;">
                    <th style="text-align:left;padding:5px;">Email</th>
                    <th style="text-align:left;padding:5px;">Date</th>
                    <th style="text-align:right;padding:5px;">Amount</th>
                    </tr>""", unsafe_allow_html=True)
                    for s in sorted(sales,
                                    key=lambda x: x.get("purchased_at",""),
                                    reverse=True):
                        amt = s.get("amount", 0)
                        atxt = _t("free").upper() if amt == 0 else f"₹{amt:,.0f}"
                        ac   = "#7fa8c9" if amt == 0 else "#00ff88"
                        st.markdown(
                            f"""<tr style="border-top:1px solid rgba(255,255,255,.05);">
                            <td style="padding:5px;font-size:.78rem;color:#c9d8ea;">
                            {s.get('buyer_email','')}</td>
                            <td style="padding:5px;font-size:.7rem;color:#556;">
                            {s.get('purchased_at','')[:10]}</td>
                            <td style="padding:5px;text-align:right;font-size:.78rem;
                            color:{ac};font-weight:700;">{atxt}</td>
                            </tr>""", unsafe_allow_html=True)
                    st.markdown("</table>", unsafe_allow_html=True)

    with tab_sets:
        with st.form("seller_settings_form"):
            sn = st.text_input("Display Name", value=seller.get("name",""))
            sb = st.text_area("Bio", value=seller.get("bio",""), height=80)
            su = st.text_input("UPI ID", value=seller.get("upi",""))
            if st.form_submit_button(_t("save_changes"), type="primary"):
                update_seller(email, {"name": sn, "bio": sb, "upi": su})
                st.success(_t("profile_updated"))
                time.sleep(0.5); st.rerun()

# ══════════════════════════════════════════════════════
# 11. ADD LISTING FORM
# ══════════════════════════════════════════════════════
def _render_add_listing_form(seller):
    se   = seller.get("email","")
    sn   = seller.get("name","")
    supi = seller.get("upi","")

    st.markdown("""<div class="info-box">
    <b>Tips:</b> Clear title · Describe WHO it's for & WHAT they learn ·
    Add Google Drive/Gumroad/Notion URL for delivery ·
    Free listings get more downloads</div>""", unsafe_allow_html=True)

    with st.form("add_listing_form", clear_on_submit=True):
        cl, cr = st.columns(2)
        with cl:
            title   = st.text_input("Title *",
                                    placeholder="e.g. Options Trading Masterclass")
            c_type  = st.selectbox(
                "Content Type *", ["ebook","course","video"],
                format_func=lambda x: {"ebook":"📖 Ebook","course":"🎓 Course",
                                        "video":"🎬 Video Series"}[x])
            price   = st.number_input("Price ₹ (0 = Free)",
                                      min_value=0, max_value=99999, value=0, step=50)
            level   = st.selectbox("Level",
                                   ["Beginner","Intermediate","Advanced","All Levels"])
        with cr:
            language    = st.text_input("Language", value="English/Hindi")
            pages       = st.text_input("Pages/Lessons",
                                        placeholder="e.g. 120 pages or 20 lessons")
            tags        = st.text_input("Tags (comma separated)",
                                        placeholder="options, swing, TA")
            content_url = st.text_input("Content URL",
                                        placeholder="Google Drive/Gumroad/Notion link")
        description = st.text_area("Description *", height=100,
                                   placeholder="What will buyers learn? Who is it for?")
        cover_emoji = st.text_input("Cover Emoji", value="📖")

        if st.form_submit_button(_t("publish_listing"), type="primary",
                                 use_container_width=True):
            if not title or not description:
                st.error("Title and description are required.")
            else:
                lid = add_listing(se, {
                    "title": title, "description": description,
                    "content_type": c_type, "price": price,
                    "level": level, "language": language,
                    "pages": pages, "tags": tags,
                    "content_url": content_url,
                    "cover_emoji": cover_emoji or "📖",
                    "seller_name": sn, "seller_upi": supi,
                    "seller_bio":  seller.get("bio",""),
                })
                st.success(f"Published! ID: {lid}")
                st.balloons()
                time.sleep(1.5); st.rerun()

# ══════════════════════════════════════════════════════
# 12. AI EBOOK BUILDER
# ══════════════════════════════════════════════════════
def _render_ebook_builder():
    email = _email()
    if not email:
        st.warning(_t("login_required"))
        return

    st.markdown(f'<div class="mkt-section-title">{_t("build_title")}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:.82rem;color:#7fa8c9;margin-bottom:16px;">'
                f'{_t("build_sub")}</div>', unsafe_allow_html=True)

    drafts = load_drafts()
    my_drafts = {k: v for k, v in drafts.items()
                 if v.get("author_email") == email}

    col_drafts, col_new = st.columns([3, 1])
    with col_new:
        if st.button(f"➕ {_t('new_ebook')}", type="primary",
                     use_container_width=True):
            draft_id = _sec.token_hex(6)
            drafts[draft_id] = {
                "id": draft_id, "author_email": email,
                "title": "", "topic": "", "audience": "",
                "num_chapters": 5, "language": "English",
                "outline": [], "chapters": {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            save_drafts(drafts)
            st.session_state.mkt_eb_draft_id = draft_id
            st.session_state.mkt_eb_step     = "topic"
            st.rerun()

    with col_drafts:
        if my_drafts:
            opts = {f"{v.get('title','Untitled')} ({k[:6]})": k
                    for k, v in my_drafts.items()}
            sel  = st.selectbox(f"📄 {_t('your_drafts')}",
                                list(opts.keys()),
                                label_visibility="collapsed")
            if st.button("Open Draft", use_container_width=True):
                st.session_state.mkt_eb_draft_id = opts[sel]
                st.session_state.mkt_eb_step     = "topic"
                st.rerun()

    draft_id = st.session_state.get("mkt_eb_draft_id","")
    if not draft_id or draft_id not in drafts:
        if not my_drafts:
            st.markdown("""<div class="mkt-empty"><div class="mkt-empty-icon">📝</div>
            <div style="color:#7fa8c9;">Click '+ New Ebook' to start building!</div>
            </div>""", unsafe_allow_html=True)
        return

    draft = drafts[draft_id]

    # ── Step navigation ───────────────────────────────
    steps = [_t("step1"), _t("step2"), _t("step3")]
    step_keys = ["topic", "chapters", "preview"]
    cur_step = st.session_state.get("mkt_eb_step","topic")
    cur_idx  = step_keys.index(cur_step) if cur_step in step_keys else 0

    nav_c = st.columns(3)
    for i, (slbl, skey) in enumerate(zip(steps, step_keys)):
        with nav_c[i]:
            active   = skey == cur_step
            bg       = "rgba(0,212,255,0.12)" if active else "rgba(255,255,255,0.03)"
            border   = "rgba(0,212,255,0.4)"  if active else "rgba(255,255,255,0.08)"
            color    = "#00d4ff" if active else "#7fa8c9"
            st.markdown(
                f"""<div style="background:{bg};border:1px solid {border};
                border-radius:10px;padding:10px 8px;text-align:center;
                font-size:.8rem;font-weight:700;color:{color};cursor:pointer;">
                {slbl}</div>""", unsafe_allow_html=True)
            if not active:
                if st.button("Go", key=f"eb_step_{skey}",
                             use_container_width=True,
                             help=slbl):
                    st.session_state.mkt_eb_step = skey; st.rerun()

    st.markdown("<hr style='border-color:rgba(0,212,255,0.1);margin:14px 0;'>",
                unsafe_allow_html=True)

    # ── STEP 1: Topic & Outline ─────────────────────
    if cur_step == "topic":
        st.markdown(f'<div class="ebook-step-title">{_t("step1")}</div>',
                    unsafe_allow_html=True)
        lang  = st.session_state.get("user_lang","en")

        with st.form("eb_topic_form"):
            e_title    = st.text_input(_t("ebook_topic"),
                                       value=draft.get("title",""),
                                       placeholder=_t("ebook_topic_ph"))
            e_audience = st.text_input(_t("target_audience"),
                                       value=draft.get("audience",""),
                                       placeholder="e.g. Beginners who want to trade options")
            e_lang     = st.text_input("Language", value=draft.get("language","English"))
            e_chapters = st.number_input(_t("num_chapters"),
                                         min_value=3, max_value=15,
                                         value=int(draft.get("num_chapters",5)))

            gen = st.form_submit_button(_t("gen_outline"), type="primary",
                                        use_container_width=True)
            if gen:
                if not e_title:
                    st.error("Topic is required.")
                else:
                    with st.spinner(_t("generating")):
                        sys_prompt = (f"You are an expert trading educator. "
                                      f"Respond in {e_lang}.")
                        prompt = (
                            f"Create a {e_chapters}-chapter ebook outline for:\n"
                            f"Title: {e_title}\nAudience: {e_audience}\n\n"
                            f"Format EXACTLY like this (one chapter per line):\n"
                            f"Chapter 1: [Title] | [One-sentence description]\n"
                            f"Chapter 2: ...\n"
                            f"Continue for all {e_chapters} chapters.\n"
                            f"Focus on Indian markets (NSE, BSE, Nifty, ₹).")
                        outline_raw = _ai(prompt, system=sys_prompt,
                                          max_tokens=800)

                        # Parse outline
                        outline = []
                        for line in outline_raw.splitlines():
                            m = re.match(r'Chapter\s+\d+:\s*(.+)', line,
                                         re.IGNORECASE)
                            if m:
                                parts = m.group(1).split("|", 1)
                                outline.append({
                                    "title": parts[0].strip(),
                                    "desc":  parts[1].strip() if len(parts)>1 else "",
                                })

                        if not outline:
                            # Fallback parse
                            for line in outline_raw.splitlines():
                                if line.strip():
                                    outline.append({"title": line.strip(), "desc": ""})

                        # Save to draft
                        drafts2 = load_drafts()
                        if draft_id in drafts2:
                            drafts2[draft_id].update({
                                "title": e_title,
                                "audience": e_audience,
                                "language": e_lang,
                                "num_chapters": e_chapters,
                                "outline": outline,
                                "updated_at": datetime.now().isoformat(),
                            })
                            save_drafts(drafts2)
                        st.success(f"Outline generated! {len(outline)} chapters ready.")
                        time.sleep(0.5); st.rerun()

        # Show current outline if exists
        outline = draft.get("outline", [])
        if outline:
            st.markdown("**📋 Current Outline:**")
            for i, ch in enumerate(outline):
                st.markdown(
                    f"**Chapter {i+1}: {ch.get('title','')}**  \n"
                    f"_{ch.get('desc','')}_")
            st.write("")
            if st.button(f"Next → {_t('step2')}", type="primary"):
                st.session_state.mkt_eb_step = "chapters"; st.rerun()

    # ── STEP 2: Write Chapters ──────────────────────
    elif cur_step == "chapters":
        outline = draft.get("outline", [])
        if not outline:
            st.warning(f"Generate an outline first in {_t('step1')}.")
            if st.button(f"← {_t('step1')}"):
                st.session_state.mkt_eb_step = "topic"; st.rerun()
            return

        st.markdown(f'<div class="ebook-step-title">{_t("step2")}</div>',
                    unsafe_allow_html=True)

        chapters = draft.get("chapters", {})
        e_lang   = draft.get("language", "English")
        e_title  = draft.get("title", "")
        audience = draft.get("audience","")

        for i, ch in enumerate(outline):
            ch_key   = str(i)
            ch_title = ch.get("title","")
            ch_desc  = ch.get("desc","")
            written  = ch_key in chapters and chapters[ch_key].get("content","")

            with st.expander(
                f"{'✅' if written else '📝'} Chapter {i+1}: {ch_title}",
                expanded=not written
            ):
                if written:
                    st.markdown(f'<div class="chapter-box">'
                                f'{chapters[ch_key]["content"]}</div>',
                                unsafe_allow_html=True)
                    if st.button(f"🔄 Regenerate Chapter {i+1}",
                                 key=f"regen_{i}"):
                        drafts2 = load_drafts()
                        if draft_id in drafts2:
                            drafts2[draft_id]["chapters"].pop(ch_key, None)
                            save_drafts(drafts2)
                        st.rerun()
                else:
                    # Custom notes
                    custom = st.text_area(
                        "Add specific points to include (optional):",
                        key=f"custom_{i}", height=60,
                        placeholder="e.g. Include Nifty 50 example, mention SEBI rules")
                    if st.button(f"✍️ {_t('gen_chapter')} {i+1}",
                                 key=f"gen_ch_{i}", type="primary"):
                        with st.spinner(f"Writing Chapter {i+1}..."):
                            sys_prompt = (f"You are an expert trading educator. "
                                          f"Write in {e_lang}. Use Indian market examples "
                                          f"(NSE, BSE, Nifty, ₹, Reliance, TCS, HDFC).")
                            prompt = (
                                f"Write a detailed, professional chapter for an ebook:\n"
                                f"Ebook: '{e_title}'\n"
                                f"Audience: {audience}\n"
                                f"Chapter {i+1}: {ch_title}\n"
                                f"Chapter overview: {ch_desc}\n"
                                f"{'Additional focus: ' + custom if custom else ''}\n\n"
                                f"Format:\n"
                                f"## Chapter {i+1}: {ch_title}\n\n"
                                f"### Introduction\n[2-3 paragraphs intro]\n\n"
                                f"### Core Concept\n[Explain the main idea with analogy]\n\n"
                                f"### Step-by-Step Guide\n[5-7 numbered steps]\n\n"
                                f"### Indian Market Example\n[Real ₹ example]\n\n"
                                f"### Key Takeaways\n[3-5 bullet points]\n\n"
                                f"### Common Mistakes to Avoid\n[3 mistakes]\n\n"
                                f"Write 600-900 words. Be practical and actionable.")
                            chapter_txt = _ai(prompt, system=sys_prompt,
                                              max_tokens=2000)
                            drafts2 = load_drafts()
                            if draft_id in drafts2:
                                if "chapters" not in drafts2[draft_id]:
                                    drafts2[draft_id]["chapters"] = {}
                                drafts2[draft_id]["chapters"][ch_key] = {
                                    "title":   ch_title,
                                    "content": chapter_txt,
                                }
                                drafts2[draft_id]["updated_at"] = (
                                    datetime.now().isoformat())
                                save_drafts(drafts2)
                            st.success(f"Chapter {i+1} written!")
                            time.sleep(0.3); st.rerun()

        # Progress bar
        written_count = sum(1 for i in range(len(outline))
                            if str(i) in chapters and chapters[str(i)].get("content",""))
        st.markdown(f"**Progress: {written_count}/{len(outline)} chapters written**")
        prog = written_count / len(outline) if outline else 0
        st.progress(prog)

        col_sv, col_nxt = st.columns(2)
        with col_sv:
            if st.button(f"💾 {_t('save_draft')}", use_container_width=True):
                st.success(_t("draft_saved"))
        with col_nxt:
            if written_count > 0:
                if st.button(f"Next → {_t('step3')}", type="primary",
                             use_container_width=True):
                    st.session_state.mkt_eb_step = "preview"; st.rerun()

    # ── STEP 3: Preview & Publish ───────────────────
    else:
        outline  = draft.get("outline",[])
        chapters = draft.get("chapters",{})
        e_title  = draft.get("title","Untitled Ebook")

        st.markdown(f'<div class="ebook-step-title">{_t("step3")}</div>',
                    unsafe_allow_html=True)
        st.markdown(f"## {e_title}")
        st.markdown(f"*by {_uname()} · {len(outline)} chapters*")
        st.markdown("---")

        for i, ch in enumerate(outline):
            ch_key = str(i)
            ch_txt = chapters.get(ch_key,{}).get("content","")
            if ch_txt:
                st.markdown(ch_txt)
                st.markdown("---")
            else:
                st.markdown(f"*Chapter {i+1}: {ch.get('title','')} — not written yet*")

        st.write("")
        seller = get_seller(email)
        if seller:
            st.markdown("### 🚀 Publish to Marketplace")
            with st.form("eb_publish_form"):
                pub_price = st.number_input("Price ₹ (0 = Free)",
                                            min_value=0, max_value=99999,
                                            value=0, step=50)
                pub_level = st.selectbox("Level",
                                         ["Beginner","Intermediate","Advanced"])
                pub_tags  = st.text_input("Tags",
                                          placeholder="options, swing, TA")
                pub_url   = st.text_input("Content URL (optional)",
                                          placeholder="Google Drive link to ebook PDF")

                # Build description from outline
                desc_lines = [f"Chapter {i+1}: {ch.get('title','')}"
                               for i, ch in enumerate(outline)]
                auto_desc  = (f"A comprehensive ebook on {e_title}. "
                               f"Covers: {', '.join(ch.get('title','') for ch in outline[:3])}...")

                if st.form_submit_button(_t("publish_listing"),
                                         type="primary", use_container_width=True):
                    lid = add_listing(email, {
                        "title": e_title,
                        "description": auto_desc,
                        "content_type": "ebook",
                        "price": pub_price,
                        "level": pub_level,
                        "language": draft.get("language","English"),
                        "pages": f"{len(outline)} chapters",
                        "tags": pub_tags,
                        "content_url": pub_url,
                        "cover_emoji": "📖",
                        "seller_name": seller.get("name",""),
                        "seller_upi":  seller.get("upi",""),
                        "seller_bio":  seller.get("bio",""),
                        "ebook_draft_id": draft_id,
                    })
                    st.success(f"Published to Marketplace! ID: {lid}")
                    st.balloons()
                    time.sleep(2)
                    st.session_state.mkt_view = "browse"; st.rerun()
        else:
            st.info(f"Create a seller account first to publish your ebook.")
            if st.button(_t("become_seller"), type="primary"):
                st.session_state.mkt_view = "seller_apply"; st.rerun()

# ══════════════════════════════════════════════════════
# 13. MAIN ENTRY
# ══════════════════════════════════════════════════════
def show_library_page():
    st.markdown(MKT_CSS, unsafe_allow_html=True)
    _init_state()

    email  = _email()
    seller = get_seller(email) if email else None

    hero_title = _t("hero_title")
    hero_sub   = _t("hero_sub")
    st.markdown(f"""<div class="mkt-hero">
    <h1>FinSage <span>Marketplace</span></h1>
    <p>{hero_sub}</p></div>""", unsafe_allow_html=True)

    nav_items = [
        (_t("browse"),      "browse"),
        (_t("my_library"),  "my_library"),
        (_t("leaderboard"), "leaderboard"),
        (_t("build_ebook"), "build_ebook"),
    ]
    if seller:
        nav_items.insert(2, (_t("dashboard"), "seller_dash"))
    nav_items.append((_t("sell"), "seller_apply"))

    view = st.session_state.mkt_view
    nav_cols = st.columns(len(nav_items))
    for i, (label, key) in enumerate(nav_items):
        with nav_cols[i]:
            btn_type = "primary" if view == key else "secondary"
            if st.button(label, key=f"mkt_nav_{key}",
                         use_container_width=True, type=btn_type):
                st.session_state.mkt_view = key; st.rerun()

    st.markdown(
        "<hr style='border-color:rgba(0,212,255,.1);margin:14px 0 18px;'>",
        unsafe_allow_html=True)

    v = st.session_state.mkt_view
    if   v == "browse":       _render_browse()
    elif v == "detail":       _render_detail()
    elif v == "my_library":   _render_my_library()
    elif v == "leaderboard":  _render_leaderboard()
    elif v == "build_ebook":  _render_ebook_builder()
    elif v == "seller_apply": _render_seller_apply()
    elif v == "seller_dash":  _render_seller_dashboard()
    else:                     _render_browse()
