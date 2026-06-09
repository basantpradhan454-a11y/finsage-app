"""
FinSage — TradingView Connect & Step-by-Step Market Guide
"""
import streamlit as st
import requests
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY","")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"


def _call_groq_guide(prompt: str) -> str:
    if not GROQ_API_KEY:
        return "⚠️ AI not configured."
    try:
        resp = requests.post(GROQ_URL, headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }, json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role":"system","content":"You are a professional trading coach. Give step-by-step practical trading guidance. Use numbered steps, be very specific with prices/levels, explain WHY each step matters. Language: English only."},
                {"role":"user","content": prompt}
            ],
            "max_tokens": 1200,
            "temperature": 0.6
        }, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"⚠️ Error {resp.status_code}"
    except Exception as e:
        return f"⚠️ {str(e)[:80]}"


def render_tradingview_guide(data: dict = None, report: str = ""):
    """Render TradingView connect section + step-by-step guide."""

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(72,187,120,0.1),rgba(99,179,237,0.1));
        border:1px solid rgba(72,187,120,0.2);border-radius:18px;padding:1.2rem 1.5rem;
        margin-bottom:1.2rem;display:flex;align-items:center;gap:1rem;">
        <div style="font-size:2rem;">📺</div>
        <div>
            <div style="font-size:1.05rem;font-weight:800;
                background:linear-gradient(90deg,#48bb78,#63b3ed);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                TradingView Connect
            </div>
            <div style="color:#8b949e;font-size:0.8rem;">
                Open live chart on TradingView + get step-by-step trading guide
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not data or not data.get("ticker"):
        st.markdown("""
        <div style="background:rgba(22,27,34,0.8);border:1px solid rgba(48,54,61,0.4);
            border-radius:14px;padding:2rem;text-align:center;color:#6e7681;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">📊</div>
            <div style="font-size:0.9rem;">Analyze any stock or crypto first — then get your step-by-step TradingView guide here.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    ticker   = data.get("ticker","")
    name     = data.get("name", ticker)
    price    = float(data.get("current_price") or 0)
    change   = float(data.get("change_pct") or 0)
    atype    = data.get("asset_type","stock")

    # Build TradingView URL
    # Convert .NS tickers for TradingView (NSE prefix)
    tv_symbol = ticker.replace(".NS","").replace(".BO","")
    if ".NS" in ticker or ".BO" in ticker:
        tv_symbol = f"NSE:{tv_symbol}"
    elif atype in ["crypto","meme"]:
        tv_symbol = f"BINANCE:{tv_symbol}USDT"
    else:
        tv_symbol = f"NASDAQ:{tv_symbol}"

    tv_url = f"https://www.tradingview.com/chart/?symbol={tv_symbol}"

    chg_color = "#48bb78" if change >= 0 else "#fc8181"
    chg_icon  = "▲" if change >= 0 else "▼"

    # ── Asset info + TradingView button ───────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.9);border:1px solid rgba(48,54,61,0.5);
            border-radius:14px;padding:1rem 1.2rem;">
            <div style="color:#e6edf3;font-size:1rem;font-weight:800;">{name}</div>
            <div style="color:#6e7681;font-size:0.78rem;margin-bottom:0.5rem;">{ticker} · {atype.upper()}</div>
            <div style="font-size:1.4rem;font-weight:900;color:#e6edf3;">
                {'₹' if '.NS' in ticker or '.BO' in ticker else '$'}{price:,.2f}
            </div>
            <div style="color:{chg_color};font-size:0.85rem;font-weight:700;">
                {chg_icon} {abs(change):.2f}% today
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.9);border:1px solid rgba(72,187,120,0.3);
            border-radius:14px;padding:1rem;text-align:center;height:100%;">
            <div style="font-size:1.4rem;margin-bottom:0.3rem;">📺</div>
            <div style="color:#48bb78;font-size:0.78rem;font-weight:700;">TradingView Chart</div>
            <a href="{tv_url}" target="_blank" style="text-decoration:none;">
                <div style="background:linear-gradient(135deg,#48bb78,#38a169);color:#fff;
                    border-radius:8px;padding:0.4rem 0.8rem;font-size:0.78rem;font-weight:700;
                    margin-top:0.5rem;display:inline-block;">Open Live Chart →</div>
            </a>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.9);border:1px solid rgba(99,179,237,0.3);
            border-radius:14px;padding:1rem;text-align:center;height:100%;">
            <div style="font-size:1.4rem;margin-bottom:0.3rem;">📱</div>
            <div style="color:#63b3ed;font-size:0.78rem;font-weight:700;">TradingView App</div>
            <a href="https://www.tradingview.com/gopro/" target="_blank" style="text-decoration:none;">
                <div style="background:linear-gradient(135deg,#63b3ed,#4299e1);color:#fff;
                    border-radius:8px;padding:0.4rem 0.8rem;font-size:0.78rem;font-weight:700;
                    margin-top:0.5rem;display:inline-block;">Get Free Account →</div>
            </a>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Step-by-step guide ────────────────────────────────────────────────────
    st.markdown("""
    <div style="color:#e6edf3;font-size:0.95rem;font-weight:700;margin-bottom:0.8rem;">
        🎯 Step-by-Step Trading Guide
    </div>
    """, unsafe_allow_html=True)

    guide_key = f"tv_guide_{ticker}"
    if guide_key not in st.session_state:
        st.session_state[guide_key] = None

    if st.button("🚀 Generate My Trading Guide", key="gen_tv_guide", type="primary", use_container_width=True):
        with st.spinner(f"Building your step-by-step guide for {name}..."):
            prompt = f"""
Asset: {name} ({ticker})
Current Price: {price}
24h Change: {change}%
Asset Type: {atype}
Analysis Report: {report[:1500] if report else 'Not available'}

Create a detailed step-by-step trading guide for this asset. Include:
1. Market Overview — what is happening right now
2. How to set up the chart on TradingView (what indicators to add: RSI, MACD, Bollinger Bands)
3. What to look for — key price levels, support, resistance
4. Entry Strategy — exact price zone to enter the trade
5. Stop Loss — exact level with reasoning
6. Target 1, Target 2, Target 3 — with % gain for each
7. Timeline — how long to hold (intraday / swing / position)
8. Risk Management — how much of portfolio to use, risk/reward ratio
9. What will signal you are WRONG (exit immediately if...)
10. Demo trade setup on TradingView — what chart to open, what to draw

Be very specific with price levels. Keep it practical and actionable.
"""
            guide = _call_groq_guide(prompt)
            st.session_state[guide_key] = guide

    if st.session_state.get(guide_key):
        guide_text = st.session_state[guide_key]
        # Render each numbered step as a card
        lines = guide_text.split("\n")
        current_step = ""
        current_content = []
        steps_html = ""
        step_colors = ["#63b3ed","#9a75ea","#48bb78","#f6ad55","#fc8181","#68d391","#76e4f7","#b794f4","#fbb6ce","#90cdf4"]

        step_num = 0
        buffer = []
        for line in lines:
            import re
            m = re.match(r'^(\d+)\.\s+(.+)', line.strip())
            if m:
                if buffer and current_step:
                    color = step_colors[(step_num-1) % len(step_colors)]
                    content_html = "<br>".join(b for b in buffer if b.strip())
                    steps_html += f"""
                    <div style="background:rgba(22,27,34,0.85);border:1px solid rgba(48,54,61,0.5);
                        border-left:3px solid {color};border-radius:12px;padding:0.9rem 1.1rem;
                        margin-bottom:0.7rem;">
                        <div style="color:{color};font-size:0.72rem;font-weight:700;text-transform:uppercase;
                            letter-spacing:0.5px;margin-bottom:0.3rem;">Step {step_num}</div>
                        <div style="color:#e6edf3;font-size:0.88rem;font-weight:700;margin-bottom:0.4rem;">{current_step}</div>
                        <div style="color:#c9d1d9;font-size:0.82rem;line-height:1.6;">{content_html}</div>
                    </div>"""
                step_num += 1
                current_step = m.group(2)
                buffer = []
            else:
                if line.strip():
                    buffer.append(line.strip())

        # Last step
        if buffer and current_step:
            color = step_colors[(step_num-1) % len(step_colors)]
            content_html = "<br>".join(b for b in buffer if b.strip())
            steps_html += f"""
            <div style="background:rgba(22,27,34,0.85);border:1px solid rgba(48,54,61,0.5);
                border-left:3px solid {color};border-radius:12px;padding:0.9rem 1.1rem;
                margin-bottom:0.7rem;">
                <div style="color:{color};font-size:0.72rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.5px;margin-bottom:0.3rem;">Step {step_num}</div>
                <div style="color:#e6edf3;font-size:0.88rem;font-weight:700;margin-bottom:0.4rem;">{current_step}</div>
                <div style="color:#c9d1d9;font-size:0.82rem;line-height:1.6;">{content_html}</div>
            </div>"""

        if steps_html:
            st.markdown(steps_html, unsafe_allow_html=True)
        else:
            # Fallback plain text
            st.markdown(f"""
            <div style="background:rgba(22,27,34,0.85);border:1px solid rgba(48,54,61,0.5);
                border-radius:12px;padding:1rem;color:#c9d1d9;font-size:0.85rem;line-height:1.7;
                white-space:pre-wrap;">{guide_text}</div>
            """, unsafe_allow_html=True)

        # TradingView demo setup card
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(72,187,120,0.08),rgba(99,179,237,0.08));
            border:1px solid rgba(72,187,120,0.25);border-radius:14px;padding:1rem 1.2rem;
            margin-top:1rem;">
            <div style="color:#48bb78;font-weight:700;font-size:0.88rem;margin-bottom:0.6rem;">
                📺 Open This Chart on TradingView Right Now
            </div>
            <div style="color:#c9d1d9;font-size:0.82rem;line-height:1.8;">
                1. Click <b style="color:#63b3ed;">Open Live Chart →</b> above<br>
                2. Search <b style="color:#f6ad55;">{tv_symbol}</b> in TradingView<br>
                3. Add indicators: <b>RSI (14)</b> + <b>MACD (12,26,9)</b> + <b>Bollinger Bands (20)</b><br>
                4. Switch to <b>1D</b> or <b>4H</b> timeframe for swing trade view<br>
                5. Draw horizontal lines at your Entry, Stop Loss, and Target levels<br>
                6. Set a <b>Price Alert</b> at your entry zone so TradingView notifies you
            </div>
            <a href="{tv_url}" target="_blank" style="text-decoration:none;">
                <div style="background:linear-gradient(135deg,#48bb78,#38a169);color:#fff;
                    border-radius:10px;padding:0.5rem 1.2rem;font-size:0.85rem;font-weight:700;
                    margin-top:0.8rem;display:inline-block;box-shadow:0 4px 15px rgba(72,187,120,0.3);">
                    🚀 Open {name} on TradingView
                </div>
            </a>
        </div>
        """, unsafe_allow_html=True)

