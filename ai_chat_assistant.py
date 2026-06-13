"""
FinsageAI — AI Trading Assistant (Chat Interface)
Full conversational guide for traders — answers any trading question.
Uses Gemini API if available, falls back to rule-based smart engine.
"""

import streamlit as st
import os
import re
import time
from datetime import datetime
from config import LOGO_URL, APP_NAME
from data_fetcher import fetch_stock_data, fetch_crypto_data
from analyzer import format_number

# ─── Gemini integration (optional) ────────────────────────────────────────────
def _gemini_response(prompt: str) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        system = (
            f"You are the FinsageAI Trading Assistant — an expert financial advisor and trading guide. "
            f"You help traders understand stocks, crypto, meme coins, technical analysis, fundamental analysis, "
            f"risk management, and market concepts. Always be educational, clear, and professional. "
            f"Never give specific buy/sell recommendations as SEBI-registered advice. "
            f"Always add: 'For educational purposes only. Not SEBI investment advice.' "
            f"Respond concisely in 150-300 words unless a detailed explanation is needed. "
            f"Use emojis sparingly for clarity. Today is {datetime.now().strftime('%B %d, %Y')}."
        )
        response = model.generate_content(f"{system}\n\nUser: {prompt}")
        return response.text
    except Exception as e:
        return None


# ─── Smart rule-based engine ───────────────────────────────────────────────────
KNOWLEDGE_BASE = {
    # Technical Analysis
    "rsi": """**📊 RSI (Relative Strength Index)**

RSI is a momentum oscillator that measures speed and change of price movements.

**Scale:** 0–100
- **Below 30** → Oversold 🟢 (potential buy signal)
- **Above 70** → Overbought 🔴 (potential sell signal)
- **30–70** → Neutral zone

**How to use:**
- RSI divergence: price makes new high but RSI doesn't → bearish signal
- RSI > 70 in uptrend = strong momentum, not always reversal
- Best used with other indicators (MACD, Volume)

**Example:** If AAPL RSI hits 28, it's oversold — watch for reversal candle before entering.

> ⚖️ Educational only. Not investment advice.""",

    "macd": """**📈 MACD (Moving Average Convergence Divergence)**

MACD shows relationship between two moving averages.

**Components:**
- **MACD Line:** 12-day EMA − 26-day EMA
- **Signal Line:** 9-day EMA of MACD
- **Histogram:** MACD − Signal

**Signals:**
- 🟢 MACD crosses above Signal → Bullish
- 🔴 MACD crosses below Signal → Bearish
- Histogram growing → momentum increasing
- Divergence with price → potential reversal

**Best for:** Trend-following in 1H, 4H, Daily charts.

> ⚖️ Educational only. Not investment advice.""",

    "candlestick": """**🕯️ Candlestick Patterns Guide**

**Bullish Reversals:**
- 🟢 **Hammer** — Long lower shadow, small body → buyers rejected lower prices
- 🟢 **Morning Star** — 3 candles: red → doji → large green
- 🟢 **Bullish Engulfing** — Green candle fully covers previous red

**Bearish Reversals:**
- 🔴 **Shooting Star** — Long upper shadow after uptrend
- 🔴 **Evening Star** — 3 candles: green → doji → large red
- 🔴 **Bearish Engulfing** — Red candle covers previous green

**Neutral:**
- ⚪ **Doji** — Open ≈ Close → market indecision

**Pro Tip:** Confirm patterns with volume. High volume = stronger signal.

> ⚖️ Educational only. Not investment advice.""",

    "support resistance": """**📐 Support & Resistance Levels**

**Support** = Price floor where buyers historically step in.
**Resistance** = Price ceiling where sellers dominate.

**How to identify:**
1. Look for price bouncing 2+ times from same level
2. Previous highs become support after breakout
3. Round numbers (₹1000, $100) act as psychological levels
4. Volume spike at level confirms strength

**Trading strategies:**
- Buy near support with stop below it
- Sell/short near resistance with stop above it
- Breakout: price closes above resistance with volume → new support

**Key rule:** The more times price tests a level, the stronger it is (until it breaks).

> ⚖️ Educational only. Not investment advice.""",

    "moving average": """**📉 Moving Averages (MA)**

**Types:**
- **SMA (Simple MA):** Equal weight to all periods
- **EMA (Exponential MA):** More weight to recent prices — faster signals

**Key levels:**
- **20 MA** → Short-term trend
- **50 MA** → Medium-term trend
- **200 MA** → Long-term trend (golden standard)

**Golden Cross** 🟢 → 50 MA crosses above 200 MA → Strong bullish signal
**Death Cross** 🔴 → 50 MA crosses below 200 MA → Strong bearish signal

**Price vs MA:**
- Price above 200 MA = bullish territory
- Price below 200 MA = bearish territory

> ⚖️ Educational only. Not investment advice.""",

    "risk management": """**🛡️ Risk Management — The Most Important Skill**

**The 1% Rule:** Never risk more than 1-2% of total capital on a single trade.

**Position Sizing Formula:**
`Position Size = (Account × Risk%) / (Entry - Stop Loss)`

**Stop Loss placement:**
- Below support for longs
- Above resistance for shorts
- ATR-based: Entry ± 1.5× ATR

**Risk:Reward Ratio:**
- Minimum 1:2 (risk ₹1 to make ₹2)
- Ideal: 1:3 or better

**Portfolio rules:**
- Max 5-10 positions simultaneously
- Diversify across sectors/assets
- Never go all-in on one trade
- Keep 20-30% cash for opportunities

**Biggest mistake:** Letting small losses become big losses by not using stop losses.

> ⚖️ Educational only. Not investment advice.""",

    "fundamental analysis": """**📋 Fundamental Analysis — Evaluating a Company**

**Key metrics to check:**

| Metric | What It Means | Good Range |
|--------|---------------|------------|
| P/E Ratio | Price per ₹1 earnings | 10-25x typical |
| EPS Growth | Earnings growth YoY | >15% strong |
| Debt/Equity | Leverage level | <1.5x healthy |
| ROE | Return on equity | >15% strong |
| Gross Margin | Pricing power | >40% excellent |
| Revenue Growth | Top-line expansion | >10% good |

**Steps to analyze:**
1. Read last 4 quarters earnings reports
2. Compare P/E with sector average
3. Check debt trend (rising debt = warning)
4. Verify management guidance accuracy
5. Look at insider buying/selling

> ⚖️ Educational only. Not investment advice.""",

    "crypto": """**₿ Cryptocurrency Trading Guide**

**Key concepts:**
- **Market Cap** = Price × Circulating Supply (more reliable than price)
- **Dominance** = BTC % of total crypto market cap
- **DeFi** = Decentralized Finance (no banks)
- **Altcoins** = All crypto except Bitcoin
- **Meme Coins** = Highly speculative, community-driven

**Crypto-specific risks:**
- 🔴 24/7 market = no closing bell
- 🔴 Extreme volatility (50%+ swings common)
- 🔴 Smart contract bugs / hacks
- 🔴 Regulatory risk
- 🔴 Rug pulls in meme coins

**Indicators that work well for crypto:**
- RSI on daily charts
- Volume analysis
- Bitcoin dominance as macro signal
- Fear & Greed Index (alternative.me)

**Rule:** Only invest what you can afford to lose completely in crypto.

> ⚖️ Educational only. Not investment advice.""",

    "ipo": """**🏦 IPO (Initial Public Offering) Guide**

An IPO is when a private company sells shares to the public for the first time.

**How to evaluate an IPO:**

✅ **Green flags:**
- Strong revenue growth (>20% YoY)
- Clear path to profitability
- Dominant market position
- Quality lead underwriters
- Reasonable valuation vs peers

🔴 **Red flags:**
- Negative revenue growth
- Extreme valuation (P/S >20x for non-tech)
- Heavy insider selling at IPO
- No clear moat
- History of governance issues

**India IPO process:**
- Apply through UPI/ASBA via bank/broker
- Allotment is lottery-based if oversubscribed
- Listing day: usually ±20% from issue price

**Key rule:** Most IPO "pops" are priced in. Wait 3-6 months for price discovery.

> ⚖️ Educational only. Not investment advice.""",

    "portfolio": """**📁 Portfolio Building Guide**

**Asset Allocation by Risk Profile:**

| Profile | Stocks | Crypto | Bonds/FD | Cash |
|---------|--------|--------|----------|------|
| Conservative | 40% | 5% | 45% | 10% |
| Moderate | 60% | 10% | 25% | 5% |
| Aggressive | 70% | 20% | 5% | 5% |

**Stock portfolio diversification:**
- Large-cap (Nifty 50): 50% (stability)
- Mid-cap: 30% (growth)
- Small-cap: 10% (high risk/reward)
- International: 10% (hedge INR)

**Rebalancing:**
- Review quarterly
- Rebalance when any asset deviates 5%+ from target
- Don't over-trade — "time in market > timing the market"

**SIP Strategy:**
- Invest fixed amount monthly regardless of market
- Averages out cost over time (rupee cost averaging)

> ⚖️ Educational only. Not investment advice.""",

    "options": """**⚙️ Options Trading Basics**

**Call Option** = Right to BUY at strike price
**Put Option** = Right to SELL at strike price

**Key terms:**
- **Strike Price:** Agreed buy/sell price
- **Premium:** Cost of the option
- **Expiry:** Date option expires
- **ITM/OTM/ATM:** In/Out/At the money

**Basic strategies:**
- 🟢 **Buy Call** → Bullish view, limited loss (premium only)
- 🔴 **Buy Put** → Bearish view, limited loss (premium only)
- ⚙️ **Covered Call** → Own stock + sell call = income strategy
- ⚙️ **Iron Condor** → Profit in low-volatility range

**Greeks:**
- **Delta** → Price sensitivity (0 to 1)
- **Theta** → Time decay (options lose value daily)
- **Vega** → Volatility sensitivity
- **Gamma** → Rate of delta change

**Warning:** Options are leveraged instruments. 80%+ of retail options traders lose money.

> ⚖️ Educational only. Not investment advice.""",
}


def _smart_response(query: str) -> str:
    """Smart rule-based response system."""
    q = query.lower()

    # Check knowledge base
    for key, answer in KNOWLEDGE_BASE.items():
        if key in q:
            return answer

    # Price check
    m = re.search(r'\b([A-Z]{1,10}(?:\.NS|\.BO)?)\b', query.upper())
    if m and any(word in q for word in ["price","chart","trading","analysis","stock","crypto","coin"]):
        sym = m.group(1)
        if len(sym) >= 2:
            return f"🔍 Let me analyze **{sym}** for you...\n\n*(Use the Pro Analyser module for a full deep-dive analysis on {sym} with real-time data, DCF, Red Flags, and more!)*\n\n> ⚖️ For educational purposes only."

    # Greetings
    if any(g in q for g in ["hello","hi","hey","namaste","hola","start"]):
        return f"""👋 **Welcome to FinsageAI Trading Assistant!**

I'm your personal AI trading guide. Ask me anything about:

📊 **Technical Analysis** — RSI, MACD, Moving Averages, Candlesticks
📋 **Fundamental Analysis** — P/E, EPS, Margins, Valuations
₿ **Crypto** — Bitcoin, DeFi, Altcoins, Meme Coins
🛡️ **Risk Management** — Position sizing, Stop losses
📁 **Portfolio Building** — Diversification, Asset allocation
⚙️ **Options & Derivatives** — Basics, Greeks, Strategies
📈 **IPO Analysis** — How to evaluate new listings

**Try asking:**
- "Explain RSI"
- "How to manage risk?"
- "What is MACD?"
- "How to build a portfolio?"

> ⚖️ Educational guide only. Not SEBI investment advice."""

    # Catch-all
    common = {
        "buy": "**When to Buy?**\n\nLook for:\n- 🟢 Strong fundamental story (rising revenue, profitable)\n- 🟢 Technical breakout with volume\n- 🟢 RSI not overbought (<65)\n- 🟢 Near support level\n- 🟢 Positive sector momentum\n\n**Never buy:**\n- Just because price is falling (catching falling knife)\n- On tips without doing research\n- Using borrowed money (leverage)\n\n> ⚖️ Educational only. Not investment advice.",
        "sell": "**When to Sell?**\n\n- 🔴 Stop loss hit (non-negotiable)\n- 🔴 Fundamental story has changed\n- 🔴 RSI > 80 in overbought zone\n- 🔴 Price hits your target (take profits)\n- 🔴 Better opportunity elsewhere\n\n**Avoid:**\n- Panic selling on temporary dips\n- Selling winners too early, holding losers too long\n\n> ⚖️ Educational only. Not investment advice.",
        "chart": "**Reading Charts**\n\nStart with:\n1. **Trend direction** — Higher highs = uptrend\n2. **Key levels** — Support and resistance\n3. **Volume** — Confirms price moves\n4. **Candlestick patterns** — Entry/exit signals\n5. **Indicators** — RSI, MACD for confirmation\n\n📈 Use TradingView (in the menu) for live interactive charts!\n\n> ⚖️ Educational only.",
        "beginner": "**Getting Started as a Trader**\n\n1. 📚 **Learn first** — Paper trade before real money\n2. 💰 **Start small** — Only invest what you can afford to lose\n3. 🛡️ **Risk management** — 1-2% max risk per trade\n4. 📊 **Pick 2-3 indicators** — Don't overcomplicate\n5. 📝 **Keep a journal** — Track every trade\n6. 😌 **Control emotions** — FOMO is your enemy\n\n**Tools to learn:** FinsageAI Pro Analyser, TradingView Charts\n\n> ⚖️ Educational only. Not investment advice.",
    }

    for keyword, resp in common.items():
        if keyword in q:
            return resp

    return f"""🤔 **I can help you with:**

- 📊 **Technical Analysis** — Type "explain RSI", "what is MACD", "candlestick patterns"
- 📋 **Fundamentals** — Type "fundamental analysis", "how to read P/E ratio"
- 🛡️ **Risk Management** — Type "risk management", "position sizing"
- 📁 **Portfolio** — Type "how to build portfolio", "asset allocation"
- ₿ **Crypto Guide** — Type "crypto trading", "meme coins"
- ⚙️ **Options** — Type "options trading basics"
- 📈 **IPO** — Type "IPO analysis"

*For real-time price analysis, use the **Pro Analyser** module from the main menu!*

> ⚖️ FinsageAI is educational only. Not SEBI investment advice."""


# ─── Main render function ──────────────────────────────────────────────────────
def render_ai_chat_assistant():
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(2,6,9,0.95),rgba(0,15,30,0.9));
    border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:1.2rem 1.5rem;
    margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;border-radius:10px;
            box-shadow:0 0 15px rgba(0,212,255,0.3);">
            <div>
                <div style="font-size:1.1rem;font-weight:800;color:#00d4ff;
                font-family:Orbitron,monospace;">🤖 AI Trading Assistant</div>
                <div style="color:#4a9eff;font-size:0.75rem;">
                Your personal guide to stocks, crypto & trading — Ask anything
                </div>
            </div>
            <span style="margin-left:auto;background:rgba(0,212,255,0.1);color:#00d4ff;
            padding:0.2rem 0.7rem;border-radius:20px;font-size:0.68rem;font-weight:700;
            border:1px solid rgba(0,212,255,0.3);">🧠 AI GUIDE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Init chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": f"👋 **Welcome to FinsageAI AI Assistant!**\n\nI'm your personal trading guide. Ask me anything about stocks, crypto, technical analysis, risk management, or market concepts.\n\n**Quick topics:**\n- Explain RSI / MACD / Candlestick patterns\n- How to manage risk in trading?\n- What is fundamental analysis?\n- How to build a portfolio?\n- Guide me on crypto trading\n\n> ⚖️ For educational purposes only. Not SEBI investment advice.",
                "time": datetime.now().strftime("%H:%M")
            }
        ]

    # Quick question chips
    st.markdown("**⚡ Quick Questions:**")
    chips = ["Explain RSI","MACD basics","Risk management","Build portfolio","Crypto guide","Candlestick patterns","Options basics","IPO analysis"]
    chip_cols = st.columns(4)
    for i, chip in enumerate(chips):
        with chip_cols[i % 4]:
            if st.button(chip, key=f"chip_{i}", use_container_width=True):
                st.session_state.pending_question = chip

    st.markdown("<br>", unsafe_allow_html=True)

    # Chat display
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_messages[-20:]:  # show last 20
            role = msg["role"]
            content = msg["content"]
            time_str = msg.get("time","")

            if role == "user":
                st.markdown(f"""
                <div style="display:flex;justify-content:flex-end;margin-bottom:0.8rem;">
                    <div style="max-width:80%;background:linear-gradient(135deg,#0066cc,#004499);
                    border-radius:14px 14px 4px 14px;padding:0.7rem 1rem;
                    box-shadow:0 2px 10px rgba(0,102,204,0.2);">
                        <div style="color:#e6edf3;font-size:0.85rem;">{content}</div>
                        <div style="color:rgba(255,255,255,0.4);font-size:0.65rem;
                        text-align:right;margin-top:0.3rem;">{time_str} ✓</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display:flex;gap:0.6rem;margin-bottom:0.8rem;">
                    <div style="width:32px;height:32px;min-width:32px;background:linear-gradient(135deg,#00d4ff,#0066cc);
                    border-radius:50%;display:flex;align-items:center;justify-content:center;
                    font-size:1rem;margin-top:2px;">🤖</div>
                    <div style="max-width:85%;background:rgba(0,20,40,0.8);
                    border:1px solid rgba(0,212,255,0.15);border-radius:4px 14px 14px 14px;
                    padding:0.8rem 1rem;box-shadow:0 2px 10px rgba(0,212,255,0.05);">
                        <div style="color:#c9d1d9;font-size:0.84rem;line-height:1.6;">{content}</div>
                        <div style="color:#4a9eff;font-size:0.65rem;margin-top:0.3rem;">{time_str}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # Handle pending question from chips
    if "pending_question" in st.session_state:
        q = st.session_state.pop("pending_question")
        st.session_state.chat_messages.append({"role": "user", "content": q, "time": datetime.now().strftime("%H:%M")})
        with st.spinner("🤖 Thinking..."):
            answer = _gemini_response(q) or _smart_response(q)
        st.session_state.chat_messages.append({"role": "assistant", "content": answer, "time": datetime.now().strftime("%H:%M")})
        st.rerun()

    # Input
    st.markdown("<br>", unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        ic1, ic2 = st.columns([6, 1])
        with ic1:
            user_input = st.text_input(
                "Ask anything...",
                placeholder="e.g. How do I use RSI? What is a stop loss? Explain candlestick patterns...",
                label_visibility="collapsed",
                key="chat_input_box"
            )
        with ic2:
            send = st.form_submit_button("Send ➤", type="primary", use_container_width=True)

        if send and user_input.strip():
            q = user_input.strip()
            st.session_state.chat_messages.append({"role": "user", "content": q, "time": datetime.now().strftime("%H:%M")})
            with st.spinner("🤖 Thinking..."):
                answer = _gemini_response(q) or _smart_response(q)
            st.session_state.chat_messages.append({"role": "assistant", "content": answer, "time": datetime.now().strftime("%H:%M")})
            st.rerun()

    # Clear chat
    col_c, _ = st.columns([1, 4])
    with col_c:
        if st.button("🗑️ Clear Chat", key="clear_chat"):
            st.session_state.chat_messages = []
            st.rerun()

    st.markdown("""
    <div style="background:rgba(10,8,0,0.8);border:1px solid rgba(210,153,34,0.3);
    border-radius:8px;padding:0.6rem 1rem;margin-top:0.8rem;font-size:0.74rem;color:#8b949e;">
    ⚖️ <b style="color:#d29922;">Disclaimer:</b> FinsageAI Assistant provides educational information only.
    Not SEBI-registered investment advice. Always consult a qualified financial advisor before investing.
    </div>
    """, unsafe_allow_html=True)
