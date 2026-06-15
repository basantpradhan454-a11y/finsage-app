"""
FinsageAI — Options Greeks Calculator
Black-Scholes model: Delta, Gamma, Theta, Vega, Rho + IV Rank
Pure Python/NumPy — no external options library needed
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import norm
from datetime import date, datetime, timedelta
import yfinance as yf


# ── Black-Scholes Greeks ──────────────────────────────────────────────────────

def _d1(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0: return 0.0
    return (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))

def _d2(S, K, T, r, sigma):
    return _d1(S, K, T, r, sigma) - sigma*np.sqrt(T)

def bs_price(S, K, T, r, sigma, option_type="call"):
    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(S, K, T, r, sigma)
    if option_type.lower() == "call":
        return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
    else:
        return K*np.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)

def greeks(S, K, T, r, sigma, option_type="call"):
    if T <= 0: return {"delta":0,"gamma":0,"theta":0,"vega":0,"rho":0,"price":0}
    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(S, K, T, r, sigma)
    nd1 = norm.pdf(d1)
    price = bs_price(S, K, T, r, sigma, option_type)

    gamma = nd1 / (S * sigma * np.sqrt(T))
    vega  = S * nd1 * np.sqrt(T) / 100          # per 1% vol move
    theta_daily = -(S*nd1*sigma/(2*np.sqrt(T)))  # time decay per day

    if option_type.lower() == "call":
        delta = norm.cdf(d1)
        theta = (theta_daily - r*K*np.exp(-r*T)*norm.cdf(d2)) / 365
        rho   = K*T*np.exp(-r*T)*norm.cdf(d2) / 100
    else:
        delta = norm.cdf(d1) - 1
        theta = (theta_daily + r*K*np.exp(-r*T)*norm.cdf(-d2)) / 365
        rho   = -K*T*np.exp(-r*T)*norm.cdf(-d2) / 100

    return {
        "price": round(price, 4),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega":  round(vega,  4),
        "rho":   round(rho,   4),
    }


def implied_vol(market_price, S, K, T, r, option_type="call", tol=1e-5, max_iter=200):
    """Newton-Raphson IV solver."""
    if T <= 0 or market_price <= 0: return 0.0
    sigma = 0.3  # initial guess
    for _ in range(max_iter):
        price  = bs_price(S, K, T, r, sigma, option_type)
        d1     = _d1(S, K, T, r, sigma)
        vega_v = S * norm.pdf(d1) * np.sqrt(T)
        if vega_v < 1e-10: break
        diff = price - market_price
        if abs(diff) < tol: break
        sigma -= diff / vega_v
        if sigma <= 0: sigma = 1e-5
    return round(sigma, 6)


@st.cache_data(ttl=300, show_spinner=False)
def _get_spot_and_iv(sym: str):
    try:
        t    = yf.Ticker(sym)
        hist = t.history(period="1y", interval="1d")
        if hist.empty: return None, None, None
        spot = float(hist["Close"].iloc[-1])

        # Historical volatility (30-day annualized)
        ret  = hist["Close"].pct_change().dropna()
        hv30 = float(ret.tail(30).std() * np.sqrt(252))

        # IV Rank — compare current HV to 52-week range
        hv_series = ret.rolling(30).std() * np.sqrt(252)
        hv_min = float(hv_series.min())
        hv_max = float(hv_series.max())
        iv_rank = ((hv30 - hv_min) / (hv_max - hv_min) * 100) if hv_max != hv_min else 50

        return spot, round(hv30, 4), round(iv_rank, 1)
    except Exception:
        return None, None, None


def render_options_calc():
    from config import LOGO_URL

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.97),rgba(0,5,20,0.95));
    border:1px solid rgba(0,255,136,0.25);border-radius:14px;
    padding:1.2rem 1.5rem;margin-bottom:1rem;">
      <div style="display:flex;align-items:center;gap:0.9rem;">
        <img src="{LOGO_URL}" style="height:44px;border-radius:10px;">
        <div>
          <div style="font-size:1.1rem;font-weight:800;font-family:Orbitron,monospace;
          background:linear-gradient(90deg,#00ff88,#4a9eff);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          ⚙️ Options Greeks Calculator</div>
          <div style="color:#8b949e;font-size:0.73rem;">
          Black-Scholes · Delta · Gamma · Theta · Vega · IV Rank · P&L Simulator
          </div>
        </div>
        <span style="margin-left:auto;background:rgba(0,255,136,0.08);color:#00ff88;
        padding:0.2rem 0.7rem;border-radius:20px;font-size:0.65rem;font-weight:700;
        border:1px solid rgba(0,255,136,0.2);">🧮 Black-Scholes Model</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Symbol Auto-fill ───────────────────────────────────────────────────────
    c1, c2 = st.columns([2,1])
    with c1:
        sym = st.text_input("Stock Symbol (optional — auto-fills spot price)",
                            placeholder="AAPL, RELIANCE.NS, TSLA...", key="oc_sym")
    with c2:
        if st.button("🔍 Fetch Live Price", key="oc_fetch"):
            with st.spinner("Fetching..."):
                spot_live, hv30, iv_rank_live = _get_spot_and_iv(sym)
            if spot_live:
                st.session_state["oc_spot"]    = spot_live
                st.session_state["oc_sigma"]   = round(hv30 * 100, 1)
                st.session_state["oc_iv_rank"] = iv_rank_live
                st.success(f"✅ {sym}: Spot=${spot_live:.2f} | HV30={hv30*100:.1f}% | IV Rank={iv_rank_live:.1f}")
            else:
                st.error("Could not fetch data for this symbol.")

    if "oc_iv_rank" in st.session_state:
        ivr = st.session_state["oc_iv_rank"]
        ivr_color = "#00ff88" if ivr > 50 else ("#ff8c42" if ivr > 30 else "#4a9eff")
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.3);border:1px solid {ivr_color}33;
        border-radius:8px;padding:0.5rem 1rem;margin-bottom:0.5rem;font-size:0.82rem;">
        📊 <b>IV Rank: <span style="color:{ivr_color};">{ivr:.1f}</span></b>
        &nbsp;|&nbsp;
        {"🔴 High IV — good for SELLING options (Straddle, Iron Condor)" if ivr > 50 else
         "🟡 Medium IV — directional spreads work well" if ivr > 30 else
         "🟢 Low IV — good for BUYING options (Debit spreads, Long calls/puts)"}
        </div>""", unsafe_allow_html=True)

    # ── Input Grid ────────────────────────────────────────────────────────────
    st.markdown("#### 🔢 Option Parameters")
    p1, p2, p3 = st.columns(3)
    with p1:
        S      = st.number_input("📈 Spot Price (S)", 0.01, 1e7,
                                  st.session_state.get("oc_spot", 100.0),
                                  step=1.0, key="oc_s")
        K      = st.number_input("🎯 Strike Price (K)", 0.01, 1e7, S * 1.0,
                                  step=1.0, key="oc_k")
    with p2:
        exp_date = st.date_input("📅 Expiry Date", date.today() + timedelta(days=30), key="oc_exp")
        T = max((exp_date - date.today()).days / 365, 1/365)
        st.caption(f"Days to expiry: **{(exp_date - date.today()).days}** | T = {T:.4f} years")
    with p3:
        sigma  = st.number_input("📊 Implied Volatility %", 1.0, 500.0,
                                  st.session_state.get("oc_sigma", 30.0),
                                  step=0.5, key="oc_sigma2") / 100
        r      = st.number_input("💰 Risk-Free Rate %", 0.0, 30.0, 6.5,
                                  step=0.1, key="oc_r") / 100

    opt_type = st.radio("Option Type", ["call", "put"],
                         horizontal=True, key="oc_type")

    # ── Calculate Greeks ──────────────────────────────────────────────────────
    g = greeks(S, K, T, r, sigma, opt_type)

    # ── Greeks Display ────────────────────────────────────────────────────────
    st.markdown("#### 📊 Option Greeks")
    g1,g2,g3,g4,g5,g6 = st.columns(6)

    g1.metric("💵 Option Price", f"${g['price']:.4f}")
    g2.metric("🎯 Delta",        f"{g['delta']:.4f}",
              help="Price change per $1 move in underlying")
    g3.metric("⚡ Gamma",        f"{g['gamma']:.6f}",
              help="Delta change per $1 move in underlying")
    g4.metric("⏰ Theta",        f"{g['theta']:.4f}/day",
              help="Value lost per day (time decay)")
    g5.metric("🌊 Vega",         f"{g['vega']:.4f}",
              help="Value change per 1% IV change")
    g6.metric("📈 Rho",          f"{g['rho']:.4f}",
              help="Value change per 1% rate change")

    # Greeks explanation cards
    greeks_info = [
        ("Delta", g['delta'], "#4a9eff",
         f"{'Call' if opt_type=='call' else 'Put'} has {abs(g['delta'])*100:.1f}% chance of expiring ITM",
         "For every $1 up in stock, option {'gains' if opt_type=='call' else 'loses'} ${abs(g['delta']):.2f}"),
        ("Theta", g['theta'], "#ff8c42",
         f"Loses ${abs(g['theta']):.4f} per day",
         f"In 7 days: ${abs(g['theta'])*7:.3f} decay | In 30 days: ${abs(g['theta'])*30:.3f}"),
        ("Vega", g['vega'], "#a371f7",
         f"${g['vega']:.4f} gain per 1% IV increase",
         f"If IV goes from {sigma*100:.1f}% → {sigma*100+5:.1f}%: ${g['vega']*5:.3f} gain"),
        ("Gamma", g['gamma'], "#00ff88",
         f"Delta changes by {g['gamma']:.6f} per $1 move",
         "High gamma near expiry = risky but high reward"),
    ]

    gc = st.columns(4)
    for i, (name, val, color, line1, line2) in enumerate(greeks_info):
        with gc[i]:
            st.markdown(f"""
            <div style="background:rgba(0,0,0,0.3);border:1px solid {color}33;
            border-radius:10px;padding:0.7rem;text-align:center;">
              <div style="color:{color};font-weight:800;font-family:Orbitron,monospace;
              font-size:0.85rem;">{name}: {val}</div>
              <div style="color:#c9d1d9;font-size:0.72rem;margin-top:0.3rem;">{line1}</div>
              <div style="color:#8b949e;font-size:0.68rem;margin-top:0.2rem;">{line2}</div>
            </div>""", unsafe_allow_html=True)

    # ── P&L Simulator ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🎯 P&L Simulator — What if price moves to...?")

    spot_range = np.linspace(S * 0.7, S * 1.3, 100)
    pl_now     = [bs_price(sp, K, T,     r, sigma, opt_type) - g["price"] for sp in spot_range]
    pl_7d      = [bs_price(sp, K, max(T-7/365,0.001), r, sigma, opt_type) - g["price"] for sp in spot_range]
    pl_30d     = [bs_price(sp, K, max(T-30/365,0.001),r, sigma, opt_type) - g["price"] for sp in spot_range]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=spot_range, y=pl_now,  name="At Expiry",
                             line=dict(color="#00ff88", width=2.5)))
    if T > 7/365:
        fig.add_trace(go.Scatter(x=spot_range, y=pl_7d,  name="-7 Days",
                                 line=dict(color="#4a9eff", width=1.8, dash="dash")))
    if T > 30/365:
        fig.add_trace(go.Scatter(x=spot_range, y=pl_30d, name="-30 Days",
                                 line=dict(color="#a371f7", width=1.5, dash="dot")))
    fig.add_hline(y=0, line_color="#8b949e", line_width=1)
    fig.add_vline(x=S, line_color="#f0c040", line_width=1.5, line_dash="dot",
                  annotation_text=f"Current ${S:.2f}", annotation_font_color="#f0c040")
    fig.add_vline(x=K, line_color="#ff8c42", line_width=1.5, line_dash="dot",
                  annotation_text=f"Strike ${K:.2f}", annotation_font_color="#ff8c42",
                  annotation_position="bottom")
    fig.update_layout(
        plot_bgcolor="#020609", paper_bgcolor="#020609",
        font=dict(color="#c9d1d9", family="monospace"),
        xaxis=dict(gridcolor="#0d1117", title="Underlying Price"),
        yaxis=dict(gridcolor="#0d1117", title="P&L ($)"),
        height=320, margin=dict(l=0,r=0,t=10,b=0),
        hovermode="x unified", legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Quick Scenarios ────────────────────────────────────────────────────────
    st.markdown("#### 📋 Scenario Analysis")
    scenarios = [
        ("Stock up 5%",   S*1.05), ("Stock up 10%",  S*1.10),
        ("Stock up 20%",  S*1.20), ("No change",     S),
        ("Stock down 5%", S*0.95), ("Stock down 10%",S*0.90),
    ]
    sc_data = []
    for label, sp in scenarios:
        new_price = bs_price(sp, K, T, r, sigma, opt_type)
        pnl       = new_price - g["price"]
        pnl_pct   = pnl / g["price"] * 100 if g["price"] > 0 else 0
        sc_data.append({
            "Scenario":      label,
            "Spot":          f"${sp:.2f}",
            "Option Price":  f"${new_price:.4f}",
            "P&L ($)":       round(pnl, 4),
            "P&L %":         round(pnl_pct, 1),
        })
    sc_df = pd.DataFrame(sc_data)

    def _col_pnl(val):
        return "color:#00ff88;font-weight:700" if val > 0 else "color:#ff4466;font-weight:700"

    st.dataframe(sc_df.style.applymap(_col_pnl, subset=["P&L ($)","P&L %"]),
                 use_container_width=True, hide_index=True)

    # ── IV Rank meter ─────────────────────────────────────────────────────────
    st.markdown("---")
    itm = "In-the-Money (ITM)" if (opt_type=="call" and S>K) or (opt_type=="put" and S<K) else \
          "At-the-Money (ATM)" if abs(S-K)/K < 0.01 else "Out-of-the-Money (OTM)"
    be  = (K + g["price"]) if opt_type=="call" else (K - g["price"])
    intrinsic = max(S-K,0) if opt_type=="call" else max(K-S,0)
    time_val  = g["price"] - intrinsic

    info_cols = st.columns(4)
    info_cols[0].metric("📍 Moneyness",    itm)
    info_cols[1].metric("💲 Break-Even",   f"${be:.2f}")
    info_cols[2].metric("📊 Intrinsic Val",f"${intrinsic:.4f}")
    info_cols[3].metric("⏱️ Time Value",   f"${time_val:.4f}")

    st.caption("Model: Black-Scholes | For educational use only | Not financial advice")
    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.5rem 0.9rem;margin-top:0.5rem;font-size:0.73rem;color:#8b949e;">
    ⚠️ <b style="color:#d29922;">Disclaimer:</b> Options trading involves substantial risk.
    This calculator is for educational purposes only. Always consult a SEBI-registered advisor.
    </div>""", unsafe_allow_html=True)
