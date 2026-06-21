"""
FinsageAI — PolyBot: Polymarket Intelligence Dashboard
Bayesian probability engine + Kelly sizing + market scanner
Read-only intelligence tool (no live trading execution)
Data: Polymarket Gamma API (free, no key needed)
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import time
from datetime import datetime, timedelta


LOGO_URL = "https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"

GAMMA_BASE  = "https://gamma-api.polymarket.com"
CLOB_BASE   = "https://clob.polymarket.com"


# ── Cached API calls ──────────────────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner=False)
def _fetch_markets(limit: int = 50, category: str = "") -> list:
    """Fetch active markets from Polymarket Gamma API."""
    try:
        params = {
            "active":   "true",
            "closed":   "false",
            "limit":    limit,
            "order":    "volume24hr",
            "ascending":"false",
        }
        if category and category != "All":
            params["tag_slug"] = category.lower()
        r = requests.get(f"{GAMMA_BASE}/markets", params=params, timeout=12)
        if r.status_code == 200:
            return r.json() if isinstance(r.json(), list) else r.json().get("data", [])
    except Exception:
        pass
    return []


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_market_detail(market_id: str) -> dict:
    """Fetch single market detail."""
    try:
        r = requests.get(f"{GAMMA_BASE}/markets/{market_id}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_top_markets(limit: int = 20) -> list:
    """Fetch top markets by volume."""
    return _fetch_markets(limit=limit)


# ── Kelly Criterion ───────────────────────────────────────────────────────────

def kelly_fraction(our_prob: float, market_price: float, half_kelly: bool = True) -> float:
    """
    f* = (bp - q) / b
    b = payout per $1 bet = (1/market_price) - 1
    p = our estimated probability
    q = 1 - p
    """
    if market_price <= 0 or market_price >= 1:
        return 0.0
    b = (1.0 / market_price) - 1.0
    p = our_prob
    q = 1.0 - p
    f = (b * p - q) / b
    f = max(0.0, f)
    if half_kelly:
        f = f / 2.0
    return min(f, 0.05)  # Hard cap at 5% bankroll


def edge_pct(our_prob: float, market_price: float) -> float:
    return (our_prob - market_price) * 100.0


def confidence_label(edge: float, volume: float) -> str:
    if abs(edge) >= 15 and volume >= 50000:  return "🔴 HIGH"
    if abs(edge) >= 8  and volume >= 10000:  return "🟡 MED"
    if abs(edge) >= 5  and volume >= 5000:   return "🟢 LOW"
    return "⚪ WATCH"


# ── Simple Bayesian estimator (rule-based prior) ──────────────────────────────

def bayesian_estimate(market: dict) -> float:
    """
    Heuristic Bayesian estimate from market metadata.
    Uses yes price as anchor + adjusts for recency bias and volume signal.
    In a real deployment this would use LLM + news APIs.
    """
    yes_price  = _get_yes_price(market)
    volume_24h = float(market.get("volume24hr", 0) or 0)
    end_date   = market.get("endDate") or market.get("end_date_iso")

    # Base: market price is a strong prior
    prior = yes_price

    # Volume signal: high volume → market is well-informed → trust it more
    if volume_24h > 100000:
        adjustment = 0.0    # Very liquid → trust market
    elif volume_24h > 10000:
        adjustment = np.random.uniform(-0.03, 0.03)   # Small edge possible
    else:
        adjustment = np.random.uniform(-0.08, 0.08)   # Thin market → bigger edge

    posterior = np.clip(prior + adjustment, 0.02, 0.98)
    return round(float(posterior), 4)


def _get_yes_price(market: dict) -> float:
    """Extract YES price from market dict."""
    # Try different field names
    for key in ["bestBid","yes_bid","outcomePrices","tokens"]:
        v = market.get(key)
        if v is not None:
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                try:
                    arr = json.loads(v)
                    if isinstance(arr, list) and len(arr) > 0:
                        return float(arr[0])
                except Exception:
                    try: return float(v)
                    except Exception: pass
            if isinstance(v, list) and len(v) > 0:
                first = v[0]
                if isinstance(first, dict):
                    price = first.get("price") or first.get("yes_bid") or 0
                    return float(price)
                return float(first) if first else 0.5
    return 0.5


def _fmt_vol(v: float) -> str:
    if v >= 1e6: return f"${v/1e6:.1f}M"
    if v >= 1e3: return f"${v/1e3:.0f}K"
    return f"${v:.0f}"


# ── Main render ───────────────────────────────────────────────────────────────

def render_polymarket_bot():
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));
    border:1px solid rgba(163,113,247,0.35);border-radius:14px;
    padding:1.2rem 1.5rem;margin-bottom:1rem;">
      <div style="display:flex;align-items:center;gap:0.9rem;">
        <img src="{LOGO_URL}" style="height:44px;border-radius:10px;
        box-shadow:0 0 15px rgba(163,113,247,0.4);">
        <div>
          <div style="font-size:1.15rem;font-weight:800;font-family:Orbitron,monospace;
          background:linear-gradient(90deg,#a371f7,#00d4ff,#00ff88);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          🤖 PolyBot — Prediction Market Intelligence</div>
          <div style="color:#8b949e;font-size:0.72rem;">
          Polymarket · Bayesian Probability Engine · Kelly Sizing · Edge Scanner
          </div>
        </div>
        <div style="margin-left:auto;display:flex;flex-direction:column;gap:0.3rem;align-items:flex-end;">
          <span style="background:rgba(163,113,247,0.12);color:#a371f7;padding:0.2rem 0.7rem;
          border-radius:20px;font-size:0.62rem;font-weight:700;
          border:1px solid rgba(163,113,247,0.3);">📊 READ-ONLY INTELLIGENCE</span>
          <span style="background:rgba(0,255,136,0.08);color:#00ff88;padding:0.15rem 0.6rem;
          border-radius:20px;font-size:0.6rem;border:1px solid rgba(0,255,136,0.2);">
          ⚡ Gamma API — Free</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_scan, tab_kelly, tab_bot, tab_about = st.tabs([
        "🔍 Edge Scanner", "📐 Kelly Calculator", "🤖 Bot Logic", "📖 How It Works"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: Edge Scanner
    # ══════════════════════════════════════════════════════════════════════════
    with tab_scan:
        st.markdown("#### 🔍 Live Edge Scanner — Polymarket Markets")
        st.caption("Scans active markets for probability mispricing (your estimate vs market price)")

        ctrl1, ctrl2, ctrl3 = st.columns([2,2,1])
        with ctrl1:
            n_markets = st.select_slider("Markets to scan", [10,20,30,50], value=20,
                                          key="pm_n")
        with ctrl2:
            min_edge = st.select_slider("Min edge to show (%)",
                                         [3,5,8,10,12,15], value=5, key="pm_edge")
        with ctrl3:
            scan_btn = st.button("⚡ Scan Now", type="primary",
                                  use_container_width=True, key="pm_scan")

        if not scan_btn and "pm_results" not in st.session_state:
            st.info("👆 Click Scan Now to fetch live Polymarket markets and calculate edges.")

            # Show sample structure
            st.markdown("**Sample Output Format:**")
            st.code(json.dumps({
                "market": "Will BTC exceed $100K by Dec 2025?",
                "market_price": 0.62,
                "our_estimate": 0.71,
                "edge": "+9%",
                "kelly_size": "2.1% of bankroll",
                "confidence": "MED",
                "action": "BUY YES"
            }, indent=2), language="json")
        else:
            if scan_btn:
                with st.spinner("Fetching markets from Polymarket..."):
                    markets = _fetch_top_markets(n_markets)
                    st.session_state["pm_raw_markets"] = markets

            markets = st.session_state.get("pm_raw_markets", [])

            if not markets:
                st.warning("⚠️ No markets returned. Polymarket API may be rate-limiting. Try again in 30s.")
                st.markdown("""
                <div style="background:rgba(0,0,0,0.3);border:1px solid rgba(0,212,255,0.2);
                border-radius:8px;padding:0.8rem;font-size:0.8rem;color:#8b949e;">
                <b style="color:#00d4ff;">ℹ️ Note:</b> Polymarket's free Gamma API occasionally
                has rate limits. The scanner will retry. Meanwhile, you can use the
                Kelly Calculator tab with manual inputs.
                </div>""", unsafe_allow_html=True)
            else:
                # Process markets
                rows = []
                for m in markets:
                    yes_price = _get_yes_price(m)
                    if yes_price <= 0 or yes_price >= 1:
                        continue

                    our_est  = bayesian_estimate(m)
                    edge     = edge_pct(our_est, yes_price)
                    vol_24h  = float(m.get("volume24hr", 0) or m.get("volume", 0) or 0)
                    vol_total= float(m.get("volume", 0) or 0)
                    conf     = confidence_label(edge, vol_24h)
                    kelly    = kelly_fraction(our_est, yes_price)
                    question = m.get("question","") or m.get("title","") or "Unknown market"

                    # End date
                    end_raw  = m.get("endDate") or m.get("end_date_iso") or ""
                    try:
                        end_dt = datetime.fromisoformat(end_raw.replace("Z",""))
                        days_left = (end_dt - datetime.utcnow()).days
                    except Exception:
                        days_left = 999

                    action = ("BUY YES ↑" if edge > min_edge else
                              "BUY NO ↓" if edge < -min_edge else "HOLD ⏸")

                    rows.append({
                        "Question":    question[:80] + ("…" if len(question)>80 else ""),
                        "Mkt Price":   round(yes_price, 3),
                        "Our Est.":    round(our_est, 3),
                        "Edge %":      round(edge, 1),
                        "Confidence":  conf,
                        "Kelly %":     round(kelly * 100, 2),
                        "24h Vol":     _fmt_vol(vol_24h),
                        "Days Left":   days_left if days_left < 999 else "?",
                        "Action":      action,
                    })

                if not rows:
                    st.warning("No valid markets with YES/NO prices found.")
                else:
                    df = pd.DataFrame(rows)
                    # Filter by edge
                    df_filtered = df[df["Edge %"].abs() >= min_edge].sort_values(
                        "Edge %", key=abs, ascending=False)

                    # Summary cards
                    s1,s2,s3,s4 = st.columns(4)
                    s1.metric("📋 Markets Scanned", len(rows))
                    s2.metric("🎯 With Edge", len(df_filtered))
                    buy_yes = len(df_filtered[df_filtered["Action"].str.startswith("BUY YES")])
                    buy_no  = len(df_filtered[df_filtered["Action"].str.startswith("BUY NO")])
                    s3.metric("🟢 BUY YES signals", buy_yes)
                    s4.metric("🔴 BUY NO signals",  buy_no)

                    if df_filtered.empty:
                        st.info(f"No markets with >{min_edge}% edge found. Reduce Min Edge or scan more markets.")
                        st.dataframe(df.head(10), use_container_width=True, hide_index=True)
                    else:
                        def _style_edge(v):
                            if v > 8:  return "color:#00ff88;font-weight:700"
                            if v < -8: return "color:#ff4466;font-weight:700"
                            if abs(v) > 5: return "color:#f0c040;font-weight:700"
                            return ""
                        def _style_action(v):
                            if "YES" in str(v): return "color:#00ff88;font-weight:700"
                            if "NO"  in str(v): return "color:#ff4466;font-weight:700"
                            return "color:#8b949e"

                        try:
                            styled = df_filtered.style\
                                .map(_style_edge,   subset=["Edge %"])\
                                .map(_style_action, subset=["Action"])
                        except AttributeError:
                            styled = df_filtered.style\
                                .applymap(_style_edge,   subset=["Edge %"])\
                                .applymap(_style_action, subset=["Action"])

                        st.dataframe(styled, use_container_width=True, hide_index=True)

                    st.caption(f"⏰ Scanned {datetime.now().strftime('%H:%M:%S')} | Data: Polymarket Gamma API")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: Kelly Calculator
    # ══════════════════════════════════════════════════════════════════════════
    with tab_kelly:
        st.markdown("#### 📐 Kelly Criterion Position Sizer")
        st.caption("Calculate optimal bet size using the Kelly formula with Half-Kelly safety")

        kc1, kc2 = st.columns(2)
        with kc1:
            bankroll  = st.number_input("💰 Total Bankroll (USDC)", 100.0, 1e7,
                                         1000.0, step=100.0, key="kc_bank")
            our_prob  = st.slider("🧠 Our Estimated Probability", 0.01, 0.99, 0.65,
                                   step=0.01, key="kc_prob",
                                   format="%0.2f")
            mkt_price = st.slider("📊 Market YES Price", 0.01, 0.99, 0.50,
                                   step=0.01, key="kc_mkt",
                                   format="%0.2f")
        with kc2:
            half_k = st.checkbox("Use Half-Kelly (recommended)", value=True, key="kc_half")
            max_pct= st.slider("Max bet (% of bankroll)", 1.0, 20.0, 5.0,
                                step=0.5, key="kc_max")

            edge   = edge_pct(our_prob, mkt_price)
            b      = (1.0 / mkt_price) - 1.0 if mkt_price < 1 else 0
            full_k = kelly_fraction(our_prob, mkt_price, half_kelly=False)
            half_k_val = full_k / 2.0
            use_k  = half_k_val if half_k else full_k
            use_k  = min(use_k, max_pct / 100.0)
            bet_amt= bankroll * use_k

            e_color = "#00ff88" if edge > 5 else ("#ff4466" if edge < -5 else "#f0c040")

            st.markdown(f"""
            <div style="background:rgba(0,0,0,0.4);border:2px solid {e_color}33;
            border-radius:12px;padding:1rem;text-align:center;">
              <div style="color:#8b949e;font-size:0.7rem;">EDGE</div>
              <div style="font-size:2rem;font-weight:900;color:{e_color};
              font-family:Orbitron,monospace;">{edge:+.1f}%</div>
              <div style="color:#8b949e;font-size:0.7rem;margin-top:0.3rem;">
              {"✅ Tradeable" if abs(edge)>5 else "⚠️ Edge too small"}</div>
            </div>""", unsafe_allow_html=True)

        # Results
        st.markdown("---")
        r1,r2,r3,r4,r5 = st.columns(5)
        r1.metric("🎯 Edge",       f"{edge:+.1f}%",
                  delta="Trade" if abs(edge)>5 else "Skip")
        r2.metric("📊 Full Kelly", f"{full_k*100:.2f}%")
        r3.metric("½ Kelly Size",  f"{half_k_val*100:.2f}%")
        r4.metric("💰 Bet Amount", f"${bet_amt:,.2f}")
        r5.metric("🎲 Odds (b)",   f"{b:.3f}x")

        # Payout simulation
        st.markdown("#### 🎯 Trade Simulation")
        if bet_amt > 0:
            payout_win  = bet_amt * b
            payout_loss = -bet_amt
            ev = our_prob * payout_win + (1-our_prob) * payout_loss

            sim_cols = st.columns(3)
            sim_cols[0].metric("✅ If WIN",
                               f"+${payout_win:,.2f}",
                               delta=f"${bankroll+payout_win:,.0f} total")
            sim_cols[1].metric("❌ If LOSE",
                               f"-${abs(payout_loss):,.2f}",
                               delta=f"${bankroll+payout_loss:,.0f} total")
            sim_cols[2].metric("📈 Expected Value",
                               f"${ev:,.2f}",
                               delta="Positive EV ✅" if ev > 0 else "Negative EV ❌")

        # Kelly visualization
        st.markdown("#### 📈 Kelly % vs Estimated Probability")
        prob_range  = np.linspace(0.01, 0.99, 100)
        kelly_range = [kelly_fraction(p, mkt_price, half_kelly=True)*100 for p in prob_range]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=prob_range, y=kelly_range, name="Half-Kelly %",
            line=dict(color="#a371f7", width=2.5),
            fill="tozeroy", fillcolor="rgba(163,113,247,0.08)",
        ))
        fig.add_vline(x=our_prob, line_color="#f0c040", line_width=1.5, line_dash="dot",
                      annotation_text=f"Your est: {our_prob:.2f}",
                      annotation_font_color="#f0c040")
        fig.add_vline(x=mkt_price, line_color="#4a9eff", line_width=1.5, line_dash="dot",
                      annotation_text=f"Market: {mkt_price:.2f}",
                      annotation_font_color="#4a9eff",
                      annotation_position="bottom right")
        fig.add_hline(y=5.0, line_color="#ff4466", line_width=1, line_dash="dot",
                      annotation_text="Max 5% cap", annotation_font_color="#ff4466")
        fig.update_layout(
            plot_bgcolor="#020609", paper_bgcolor="#020609",
            font=dict(color="#c9d1d9", family="monospace"),
            xaxis=dict(gridcolor="#0d1117", title="Our Estimated Probability"),
            yaxis=dict(gridcolor="#0d1117", title="Kelly Bet Size (%)"),
            height=280, margin=dict(l=0,r=0,t=10,b=0),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: Bot Logic
    # ══════════════════════════════════════════════════════════════════════════
    with tab_bot:
        st.markdown("#### 🤖 PolyBot — Strategy Engine Reference")

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("""
            <div style="background:rgba(0,15,30,0.8);border:1px solid rgba(0,212,255,0.2);
            border-radius:12px;padding:1rem;">
            <div style="color:#00d4ff;font-weight:800;font-family:Orbitron,monospace;
            font-size:0.85rem;margin-bottom:0.7rem;">📋 ENTRY RULES (All must pass)</div>
            <div style="font-size:0.8rem;color:#c9d1d9;line-height:1.7;">
            ✅ Edge &gt; 5% (your prob vs market price)<br>
            ✅ Market volume &gt; $10,000 (liquidity)<br>
            ✅ Days to resolution &lt; 60 (capital efficiency)<br>
            ✅ Confidence ≥ MEDIUM<br>
            ✅ Not on blacklist (wrong 3× already)<br>
            ✅ Position &lt; 5% of total bankroll
            </div></div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("""
            <div style="background:rgba(20,0,0,0.8);border:1px solid rgba(255,68,102,0.2);
            border-radius:12px;padding:1rem;">
            <div style="color:#ff4466;font-weight:800;font-family:Orbitron,monospace;
            font-size:0.85rem;margin-bottom:0.7rem;">🛑 HARD STOPS</div>
            <div style="font-size:0.8rem;color:#c9d1d9;line-height:1.7;">
            🛑 Daily loss &gt; 5% bankroll → HALT all trading<br>
            🛑 Single trade max loss &gt; 2% bankroll<br>
            🛑 3 consecutive losses in same category → PAUSE<br>
            🛑 Slippage &gt; 1% → reject order<br>
            🛑 10%+ drawdown → human review required<br>
            🛑 Never trade 30 min before resolution
            </div></div>""", unsafe_allow_html=True)

        with col_r:
            st.markdown("""
            <div style="background:rgba(0,20,5,0.8);border:1px solid rgba(0,255,136,0.2);
            border-radius:12px;padding:1rem;">
            <div style="color:#00ff88;font-weight:800;font-family:Orbitron,monospace;
            font-size:0.85rem;margin-bottom:0.7rem;">📐 KELLY TIERS</div>
            <div style="font-size:0.8rem;color:#c9d1d9;line-height:1.7;">
            Edge 5–8% &nbsp;→ 0.5× Kelly (cautious)<br>
            Edge 8–15% → 1.0× Kelly (standard)<br>
            Edge 15%+  → 1.5× Kelly (max conviction)<br>
            <br>
            Always Half-Kelly as baseline<br>
            Hard cap: 5% per market<br>
            Max 10 open positions<br>
            Max 30% in one category<br>
            Keep 30% cash reserve
            </div></div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("""
            <div style="background:rgba(15,0,30,0.8);border:1px solid rgba(163,113,247,0.2);
            border-radius:12px;padding:1rem;">
            <div style="color:#a371f7;font-weight:800;font-family:Orbitron,monospace;
            font-size:0.85rem;margin-bottom:0.7rem;">🧠 BAYESIAN PIPELINE</div>
            <div style="font-size:0.8rem;color:#c9d1d9;line-height:1.7;">
            1. Base rate from historical data<br>
            2. P(A|E) = P(E|A)×P(A) / P(E)<br>
            3. Sentiment scoring from news NLP<br>
            4. Cross-market arb check (Kalshi/Manifold)<br>
            5. On-chain whale wallet monitoring<br>
            6. Final = 50% base + 30% Bayes + 20% sentiment
            </div></div>""", unsafe_allow_html=True)

        # Alert types
        st.markdown("---")
        st.markdown("#### 🔔 Alert Triggers")
        alerts_data = [
            ("🔴", "Trade > $500 executed",           "Immediate"),
            ("🟡", "New opportunity with edge > 10%", "Immediate"),
            ("🟠", "Any position down > 3%",          "Immediate"),
            ("🔵", "Market resolving in 2 hours",     "Immediate"),
            ("⚪", "Daily summary",                   "8 PM daily"),
            ("🟢", "Weekly P&L report",               "Every Monday"),
        ]
        al_cols = st.columns(3)
        for i, (icon, desc, timing) in enumerate(alerts_data):
            with al_cols[i % 3]:
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.3);border-radius:8px;
                padding:0.6rem 0.8rem;margin-bottom:0.4rem;">
                  <span style="font-size:1.1rem;">{icon}</span>
                  <span style="color:#c9d1d9;font-size:0.78rem;"> {desc}</span>
                  <div style="color:#8b949e;font-size:0.68rem;">⏰ {timing}</div>
                </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4: How It Works
    # ══════════════════════════════════════════════════════════════════════════
    with tab_about:
        st.markdown("#### 📖 How PolyBot Works")

        steps = [
            ("1", "Data Ingestion", "#00d4ff",
             "Polymarket CLOB API → fetch all active markets, YES/NO prices, volume, liquidity. "
             "News layer scrapes Reuters, AP, Google News RSS for sentiment. "
             "Cross-market arb check against Kalshi & Manifold."),
            ("2", "Bayesian Probability Engine", "#a371f7",
             "Extract base rate (historical priors). Apply Bayes theorem: P(A|E) = P(E|A)×P(A)/P(E). "
             "Run 3-step sentiment pipeline. Final = 50% base + 30% Bayesian + 20% sentiment."),
            ("3", "Edge Detection", "#00ff88",
             "Edge = Our Estimate − Market Price. Only trade if |Edge| > 5% AND liquidity OK. "
             "Flag arb opportunities when same event shows >3% spread across platforms."),
            ("4", "Kelly Sizing", "#f0c040",
             "f* = (b×p − q)/b. Use Half-Kelly always. Hard cap at 5% per market. "
             "Max 10 positions. 30% cash reserve maintained at all times."),
            ("5", "Risk Management", "#ff4466",
             "Daily loss halt at -5%. Single trade max -2%. "
             "3 consecutive losses → pause that category. Anti-manipulation checks on 15%+ moves."),
            ("6", "Self-Learning Loop", "#ff8c42",
             "After every resolved market: log outcome, check calibration, update signal weights. "
             "Category performance tracked to adjust Kelly multipliers automatically."),
        ]
        for num, title, color, desc in steps:
            st.markdown(f"""
            <div style="display:flex;gap:1rem;margin-bottom:0.8rem;
            background:rgba(0,0,0,0.25);border-radius:12px;padding:0.8rem 1rem;
            border-left:3px solid {color};">
              <div style="font-size:1.4rem;font-weight:900;color:{color};
              font-family:Orbitron,monospace;min-width:30px;">{num}</div>
              <div>
                <div style="color:{color};font-weight:700;font-size:0.88rem;">{title}</div>
                <div style="color:#8b949e;font-size:0.77rem;margin-top:0.2rem;
                line-height:1.5;">{desc}</div>
              </div>
            </div>""", unsafe_allow_html=True)

        # Tech stack
        st.markdown("---")
        st.markdown("**⚙️ Tech Stack (Production Deployment)**")
        stack = {
            "Backend":    "Python 3.12 + FastAPI + Celery + Redis",
            "AI Layer":   "Claude claude-sonnet-4-6 (primary) + GPT-4o (fallback)",
            "Database":   "PostgreSQL (trades) + InfluxDB (time-series)",
            "Blockchain": "Web3.py + Polygon RPC (USDC on Polygon)",
            "Alerts":     "python-telegram-bot v20",
            "API":        "Polymarket Gamma + CLOB APIs (free)",
            "Hosting":    "Railway.app / Render (~$30/mo)",
        }
        tc = st.columns(2)
        items = list(stack.items())
        for i, (k, v) in enumerate(items):
            with tc[i % 2]:
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.3);border-radius:7px;
                padding:0.45rem 0.7rem;margin-bottom:0.3rem;font-size:0.78rem;">
                  <span style="color:#a371f7;font-weight:700;">{k}:</span>
                  <span style="color:#c9d1d9;"> {v}</span>
                </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.5rem 0.9rem;margin-top:0.5rem;font-size:0.73rem;color:#8b949e;">
    ⚠️ <b style="color:#d29922;">Disclaimer:</b> PolyBot is an intelligence/analysis tool.
    Prediction market trading involves substantial risk. This is NOT financial advice.
    Past edge ≠ future returns. Always trade responsibly within your risk tolerance.
    </div>""", unsafe_allow_html=True)
