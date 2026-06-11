"""
STOX AI — AI Chat Assistant
Trader ke har sawaal ka jawab deta hai (rule-based + data-driven)
"""

import streamlit as st
import re
from datetime import datetime
from data_fetcher import fetch_stock_data, fetch_crypto_data
from analyzer import analyze_stock, analyze_crypto

LOGO_URL = "https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"

# ── Knowledge Base ──────────────────────────────────────────────────────────────
KNOWLEDGE_BASE = {
    # Trading basics
    r'\b(what is|kya hai|explain|samjhao)\b.*\b(rsi)\b': {
        "title": "RSI — Relative Strength Index",
        "answer": """📊 **RSI (Relative Strength Index)** ek momentum indicator hai jo 0-100 ke beech hota hai.

**Interpretation:**
• **RSI > 70** → Overbought 🔴 (Price bahut badh gayi, correction aa sakta hai)
• **RSI < 30** → Oversold 🟢 (Price bahut gir gayi, bounce ho sakta hai)
• **RSI 30-70** → Neutral zone

**Formula:** RSI = 100 - [100 / (1 + Average Gain/Average Loss)]

**Trading Rule:**
- RSI > 70 pe sell ya short karo
- RSI < 30 pe buy karo
- Divergence (price aur RSI opposite direction mein) strongest signal hai

**Example:** AAPL ka RSI 78 hai → Overbought signal → Entry mat lo abhi"""
    },
    r'\b(what is|kya hai|explain|samjhao)\b.*\b(macd)\b': {
        "title": "MACD — Moving Average Convergence Divergence",
        "answer": """📈 **MACD** trend-following momentum indicator hai.

**Components:**
• **MACD Line** = 12-day EMA - 26-day EMA
• **Signal Line** = 9-day EMA of MACD
• **Histogram** = MACD - Signal

**Signals:**
• MACD Signal Line cross karke **upar jaye** → BUY 🟢
• MACD Signal Line cross karke **neeche jaye** → SELL 🔴
• Histogram bar badhna → momentum strong ho raha hai

**Pro Tip:** MACD best hai trending markets mein, sideways market mein false signals deta hai"""
    },
    r'\b(what is|kya hai|explain|samjhao)\b.*\b(pe ratio|p\/e|price.?to.?earnings)\b': {
        "title": "P/E Ratio",
        "answer": """💰 **P/E Ratio (Price-to-Earnings)** = Stock Price / Earnings Per Share

**Interpretation:**
• **P/E < 15** → Undervalued ho sakta hai (Value buy opportunity)
• **P/E 15-25** → Fair value zone
• **P/E > 25** → Overvalued (Growth premium ya bubble)

**Sector Comparison:**
- Tech stocks: P/E 30-50 normal hai
- Banking: P/E 8-15 normal
- FMCG India: P/E 40-60 (premium brand)

**Warning:** High P/E always bad nahi, growth potential matter karta hai!"""
    },
    r'\b(what is|kya hai)\b.*\b(bull flag|bullish flag)\b': {
        "title": "Bull Flag Pattern",
        "answer": """🚩 **Bull Flag** ek continuation pattern hai.

**Structure:**
1. Strong upward move (flagpole) 📊
2. Slight downward consolidation (flag) 📉
3. Breakout upward (continuation) 🚀

**Entry Rule:** Flag ke upper trendline break pe buy karo
**Target:** Flagpole ki height jitna profit expect karo
**Stop Loss:** Flag ke lower trendline ke neeche

**Example:** Stock ₹100 se ₹150 gaya (flagpole = ₹50), phir ₹130-₹140 consolidate kiya, phir ₹140 break → Target ₹190"""
    },
    r'\b(rug pull|rugpull|rug)\b': {
        "title": "Rug Pull — Crypto Scam",
        "answer": """🚨 **Rug Pull** ek crypto scam hai jisme developers investors ka paisa lekar bhaag jaate hain.

**Types:**
1. **Hard Rug** — Liquidity overnight remove kar dete hain, coin ₹0 ho jaata hai
2. **Slow Rug** — Dev gradually sell karta hai, price slowly girti rehti hai
3. **Honeypot** — Buy kar sakte ho, sell nahi kar sakte (contract mein trap)

**Red Flags:**
• Anonymous team (no doxxed founders)
• Liquidity lock nahi hai
• Dev wallet mein 20%+ supply
• Contract mein mint function (unlimited tokens bana sakta hai)
• Social media overnight create hua

**Safe Checks:**
✅ Liquidity locked on Unicrypt/PinkSale
✅ Contract audited by CertiK/Hacken
✅ Team doxxed (verified identity)
✅ Honeypot check on honeypot.is"""
    },
    r'\b(whale|whales|whale watching)\b': {
        "title": "Whale Watching",
        "answer": """🐋 **Whales** = Bade investors jinke paas market move karne ki power hai

**Crypto Whales:**
• Bitcoin whale = 1000+ BTC holder
• Movement track karo: Whale Alert, CryptoQuant

**Whale Signals:**
• **Exchange mein BTC transfer** → Sell karne wala hai 🔴
• **Exchange se BTC withdraw** → Hold/Accumulate kar raha hai 🟢
• **Sudden large buy on DEX** → New meme coin pump signal

**Stock Market Smart Money:**
• Institutional filing (13F) track karo
• Options market ki unusual activity
• Dark pool prints (large off-exchange trades)

**Tools:** Whale Alert (crypto), SEC 13F filings (stocks), Nansen (on-chain)"""
    },
    r'\b(support|resistance|support.?resistance)\b': {
        "title": "Support & Resistance",
        "answer": """📉📈 **Support & Resistance** — Technical Analysis ka foundation

**Support:** Price jahan se bounce karta hai (buying pressure)
**Resistance:** Price jahan se reverse hota hai (selling pressure)

**Rules:**
• Support break ho jaye → Resistance ban jaata hai (flip)
• Jitni baar test ho, utna strong (3+ times = key level)
• Round numbers (₹1000, $100) psychological levels hote hain

**Entry Strategy:**
- Support pe buy, resistance pe sell
- Breakout pe momentum trade
- Fakeout se bachne ke liye candle close ka wait karo

**Volume Confirmation:** Breakout real hai tabhi maano jab high volume ke saath ho"""
    },
    r'\b(stop loss|stoploss|sl)\b': {
        "title": "Stop Loss — Risk Management",
        "answer": """🛡️ **Stop Loss** = Ek predetermined price jiske neeche aap apna trade close kar dete hain

**Why it's crucial:**
• Ek badi loss kaafi chhote wins ko wipe kar sakti hai
• Emotions ko remove karta hai trading se

**Stop Loss Types:**
1. **Fixed %** — Entry se 2-3% neeche (beginners ke liye best)
2. **ATR-based** — Volatility ke hisaab se dynamic SL
3. **Technical SL** — Support ke neeche place karo

**Golden Rule:**
💡 **Risk per trade = 1-2% of total capital**
- Capital ₹1,00,000 → Max risk per trade = ₹1,000-₹2,000

**Position Sizing:** Qty = Risk Amount / (Entry - Stop Loss)
Example: Risk ₹1000, Entry ₹500, SL ₹490 → Buy 100 shares"""
    },
    r'\b(dex|decentralized exchange|uniswap|pancakeswap|raydium)\b': {
        "title": "DEX — Decentralized Exchange",
        "answer": """🔄 **DEX (Decentralized Exchange)** — Bina central authority ke trading

**Popular DEXes:**
• **Ethereum:** Uniswap, Curve
• **BSC:** PancakeSwap
• **Solana:** Raydium, Jupiter
• **Base/Arbitrum:** Aerodrome, Camelot

**DEX vs CEX:**
| Feature | DEX | CEX (Binance) |
|---------|-----|----------------|
| KYC | No | Yes |
| Self-custody | Yes | No |
| Speed | Medium | Fast |
| Rug risk | High | Low |

**Meme Coin DEX Trading:**
- DexScreener pe liquidity check karo
- Slippage 5-15% set karo meme coins ke liye
- Gas fees check karo pehle"""
    },
    r'\b(fear.?greed|fear and greed)\b': {
        "title": "Fear & Greed Index",
        "answer": """😱😤 **Fear & Greed Index** — Market sentiment measure karta hai

**Scale:** 0 = Extreme Fear → 100 = Extreme Greed

**Zones:**
• **0-25: Extreme Fear** 😱 → Good buying opportunity
• **25-45: Fear** 😟 → Cautious buying
• **45-55: Neutral** 😐 → Wait and watch
• **55-75: Greed** 😏 → Be careful, reduce size
• **75-100: Extreme Greed** 🤑 → Sell signal, bubble possible

**Warren Buffett Rule:**
_"Be greedy when others are fearful, and fearful when others are greedy"_

**Crypto F&G:** alternative.me/crypto/fear-and-greed-index/
**Stock F&G:** CNN Fear & Greed Index"""
    },
    r'\b(pump.?dump|pump and dump)\b': {
        "title": "Pump & Dump Scheme",
        "answer": """🚨 **Pump & Dump** — Illegal market manipulation scheme

**How it works:**
1. Organizers secretly buy large amount of a cheap coin/stock
2. Social media, Telegram groups mein hype create karte hain
3. Retail investors FOMO mein buy karte hain → Price pumps
4. Organizers sell at peak → Price dumps 90%
5. Retail investors hold worthless bag 💼

**Warning Signs:**
• Sudden 200-500% price spike bina news ke
• Telegram groups mein "guaranteed profit" claims
• Anonymous project, no whitepaper
• Volume 10x+ overnight

**Protection:**
✅ Research before buying
✅ Never chase pumps already 50%+
✅ Set take profit at 2x-3x
✅ Never invest more than you can lose"""
    },
}

def get_ai_response(user_question: str, ticker: str = None) -> str:
    """Main AI response engine"""
    q_lower = user_question.lower()
    
    # 1. Check knowledge base
    for pattern, data in KNOWLEDGE_BASE.items():
        if re.search(pattern, q_lower):
            return f"**{data['title']}**\n\n{data['answer']}"
    
    # 2. Ticker-specific analysis
    ticker_match = re.findall(r'\b([A-Z]{2,6}(?:\.[A-Z]{1,3})?)\b', user_question.upper())
    crypto_hints = ['btc', 'eth', 'sol', 'bnb', 'doge', 'shib', 'pepe', 'xrp', 'ada', 'avax', 'bitcoin', 'ethereum']
    
    is_crypto = any(c in q_lower for c in crypto_hints)
    found_ticker = ticker or (ticker_match[0] if ticker_match else None)
    
    skip = {'BUY', 'SELL', 'THE', 'AND', 'FOR', 'GET', 'SET', 'AI', 'DO', 'RSI', 'MACD', 'PE', 'MY', 'ME', 'IS', 'IT', 'IN', 'ON', 'AT', 'OF'}
    if found_ticker and found_ticker in skip:
        found_ticker = None
    
    if found_ticker and any(kw in q_lower for kw in ['should i', 'buy', 'sell', 'analyse', 'analyze', 'check', 'dekho', 'kya lagta', 'good', 'kharidu', 'le lu']):
        try:
            if is_crypto or found_ticker in ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'SHIB', 'PEPE', 'XRP']:
                d = fetch_crypto_data(found_ticker)
                if 'error' not in d:
                    report = analyze_crypto(d)
                    return _format_asset_response(d, report, found_ticker, 'crypto')
            else:
                d = fetch_stock_data(found_ticker)
                if 'error' not in d:
                    report = analyze_stock(d)
                    return _format_asset_response(d, report, found_ticker, 'stock')
        except:
            pass
    
    # 3. Context-aware responses
    responses = {
        r'\b(hello|hi|hey|namaste|namaskar|hii)\b': "👋 Namaste! Main STOX AI Assistant hoon. Aap mujhse trading, stocks, crypto, aur market ke baare mein kuch bhi pooch sakte hain!\n\nKuch sawaal try karo:\n• `BTC buy karna chahiye?`\n• `RSI kya hota hai?`\n• `Stop loss kaise lagaate hain?`\n• `Whale watching kya hai?`",
        r'\b(thank|thanks|shukriya|dhanyawad|ty)\b': "😊 Khushi hui help karke! Koi aur sawaal ho toh zaroor poochho. Trading mein always research first! 📊",
        r'\b(best stock|konsa stock|which stock|konsa share)\b': "🤔 **Best stock** situation pe depend karta hai:\n\n**Conservative (Safe):**\n• RELIANCE.NS — India ka largest conglomerate\n• TCS.NS — IT sector leader\n• AAPL — World's most valuable company\n• MSFT — Cloud + AI play\n\n**Growth (Moderate risk):**\n• NVDA — AI chips monopoly\n• TSLA — EV + AI automation\n• INFY.NS — IT services\n\n**Note:** Ye suggestions hain, SEBI-registered advice nahi. Always do your own research! 📋",
        r'\b(best crypto|konsa crypto|which crypto)\b': "💎 **Market cap ke hisaab se safe cryptos:**\n\n**Blue Chip (Safest):**\n• BTC — Digital gold, most liquid\n• ETH — Smart contract platform\n• SOL — Fast, cheap transactions\n\n**Mid Cap (Moderate risk):**\n• BNB — Binance ecosystem\n• ADA — Academic approach\n• AVAX — DeFi platform\n\n**High Risk:**\n• Meme coins (DOGE, SHIB, PEPE) — Pure speculation\n\n⚠️ Crypto markets 24/7 operate karte hain, extremely volatile hain",
        r'\b(how to|kaise|kaise karu|sikho)\b.*\b(trading|trade)\b': "📚 **Trading Sikhne ka Roadmap:**\n\n**Step 1 — Basics (1-2 months)**\n• Candlestick patterns padhein\n• Support & Resistance samjhein\n• Risk management (1-2% rule)\n\n**Step 2 — Technical Analysis (2-3 months)**\n• RSI, MACD, Bollinger Bands\n• Volume analysis\n• Chart patterns (Bull flag, H&S)\n\n**Step 3 — Paper Trading (3-6 months)**\n• Bina real money ke practice karo\n• Strategy backtest karo\n\n**Step 4 — Live Trading**\n• Small size se shuru karo\n• Journal maintain karo\n\n**Resources:** Zerodha Varsity (FREE, Hindi available) 📖",
        r'\b(market|bazaar)\b.*\b(today|aaj|kal|tomorrow)\b': "📊 **Market Outlook** ek fixed answer nahi hota — ye depend karta hai:\n\n• Global cues (US Fed, Nasdaq)\n• India-specific (RBI policy, FII flows)\n• Sector rotation\n• Technical levels\n\n**Current Market Check karo:**\n- NSE: NIFTY 50 aur Bank NIFTY levels\n- Global: S&P 500, Nasdaq futures\n- Crypto: BTC dominance\n\nSpecific ticker check karne ke liye: `Check RELIANCE.NS` ya `Analyse BTC` type karo! 🎯",
        r'\b(sebi|sec|regulation|compliance)\b': "⚖️ **SEBI (Securities & Exchange Board of India)**\n\nSEBI Indian stock market ka regulator hai.\n\n**Key Rules for Traders:**\n• T+1 settlement (next day stocks milte hain)\n• Intraday margin 20% minimum\n• F&O ke liye 50L+ net worth required (SEBI rule)\n• Insider trading = criminal offence\n• P&L pe tax: Short term 15%, Long term 10% (above ₹1L)\n\n**SEBI complaint:** scores.sebi.gov.in\n\n⚠️ STOX AI SEBI-registered advisor nahi hai — ye educational tool hai",
    }
    
    for pattern, response in responses.items():
        if re.search(pattern, q_lower):
            return response
    
    # 4. Generic helpful fallback
    return (f"🤖 **'{user_question[:50]}...' ke baare mein:**\n\n"
            f"Ye specific topic meri knowledge base mein abhi nahi hai, lekin aap ye try kar sakte hain:\n\n"
            f"**Specific analysis ke liye:**\n"
            f"• Ticker ke naam ke saath poochho: `AAPL analysis` ya `BTC buy karna chahiye?`\n\n"
            f"**Topics jo main samjha sakta hoon:**\n"
            f"• RSI, MACD, Bollinger Bands\n"
            f"• Support/Resistance, Chart Patterns\n"
            f"• Whale watching, Rug pull\n"
            f"• Stop loss, Position sizing\n"
            f"• Fear & Greed Index\n"
            f"• DEX trading, On-chain analysis\n\n"
            f"_Type karo: `RSI kya hai` ya `Stop loss kaise lagaate hain`_")


def _format_asset_response(d: dict, report: dict, symbol: str, asset_type: str) -> str:
    price   = d.get('current_price', 0)
    name    = d.get('name', symbol)
    rec     = report.get('recommendation', 'HOLD')
    score   = report.get('score', 50)
    risk    = report.get('risk_level', 'Medium')
    summary = report.get('summary', '')

    icons = {"BUY": "🟢", "STRONG BUY": "💚", "SELL": "🔴", "STRONG SELL": "❤️", "HOLD": "🟡"}
    icon = icons.get(rec, "⚪")

    change_24h = d.get('change_24h', d.get('day_change_pct', 0)) or 0
    chg_icon = "▲" if change_24h >= 0 else "▼"
    chg_color_text = "UP" if change_24h >= 0 else "DOWN"

    lines = [
        f"**🔍 {name} ({symbol}) — Live Analysis**\n",
        f"💰 **Price:** ₹{price:,.4f}",
        f"📊 **24h Change:** {chg_icon} {abs(change_24h):.2f}% ({chg_color_text})",
        f"{icon} **AI Recommendation:** {rec}",
        f"📈 **Score:** {score}/100",
        f"⚠️ **Risk Level:** {risk}\n",
    ]
    
    if asset_type == 'stock':
        pe = d.get('pe_ratio', 0) or 0
        mktcap = d.get('market_cap', 0) or 0
        lines.append(f"📋 **P/E Ratio:** {pe:.1f}" if pe else "📋 **P/E Ratio:** N/A")
        lines.append(f"🏦 **Market Cap:** ₹{mktcap/1e9:.1f}B" if mktcap > 1e9 else "")
    else:
        vol = d.get('volume_24h', 0) or 0
        mktcap = d.get('market_cap', 0) or 0
        lines.append(f"📦 **24h Volume:** ${vol/1e6:.1f}M" if vol else "")
        lines.append(f"🏦 **Market Cap:** ${mktcap/1e9:.1f}B" if mktcap > 1e9 else "")
    
    lines.append(f"\n📝 **Summary:** {summary}" if summary else "")
    lines.append(f"\n_⚠️ Educational analysis only. Not SEBI-registered advice._")
    
    return "\n".join(l for l in lines if l)


# ── Render AI Assistant ─────────────────────────────────────────────────────────
def render_ai_assistant():
    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = []

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1117,#161b22);border:1px solid #30363d;
    border-radius:14px;padding:1.2rem 1.5rem 0.8rem;margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;width:44px;border-radius:10px;">
            <div>
                <div style="font-size:1.2rem;font-weight:800;color:#58a6ff;">STOX AI Assistant</div>
                <div style="color:#8b949e;font-size:0.78rem;">Trading ke har sawaal ka jawab • 24/7 Available</div>
            </div>
            <span style="margin-left:auto;background:#1a3a1a;color:#3fb950;padding:0.2rem 0.7rem;
            border-radius:20px;font-size:0.72rem;font-weight:600;">🟢 Online</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Suggested questions
    st.markdown("**💡 Popular Questions:**")
    sq = st.columns(4)
    suggestions = [
        ("📊 RSI kya hai?", "RSI kya hai?"),
        ("🐋 Whale Watch", "Whale watching kya hai?"),
        ("🛡️ Stop Loss", "Stop loss kaise lagaate hain?"),
        ("🚨 Rug Pull?", "Rug pull kya hota hai?"),
    ]
    for i, (label, q) in enumerate(suggestions):
        with sq[i]:
            if st.button(label, key=f"sq_ai_{i}", use_container_width=True):
                st.session_state.ai_chat_history.append({
                    "role": "user", "content": q,
                    "time": datetime.now().strftime("%H:%M")
                })
                resp = get_ai_response(q)
                st.session_state.ai_chat_history.append({
                    "role": "assistant", "content": resp,
                    "time": datetime.now().strftime("%H:%M")
                })
                st.rerun()

    st.markdown("---")

    # Chat display
    if not st.session_state.ai_chat_history:
        st.markdown("""
        <div style="text-align:center;padding:2.5rem;color:#8b949e;border:1px dashed #30363d;border-radius:10px;">
            <div style="font-size:2.5rem;">🤖</div>
            <p style="font-size:1rem;font-weight:600;color:#c9d1d9;">STOX AI Assistant ready hai!</p>
            <p style="font-size:0.85rem;">Trading, stocks, crypto, technical analysis — kuch bhi poochho</p>
            <p style="font-size:0.8rem;margin-top:0.5rem;">
            Examples: <code>BTC buy karna chahiye?</code> · <code>MACD samjhao</code> · <code>AAPL analysis karo</code>
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Show last 30 messages
    for msg in st.session_state.ai_chat_history[-30:]:
        if msg["role"] == "user":
            st.markdown(f"""
            <div style="display:flex;justify-content:flex-end;margin:0.5rem 0;">
                <div style="background:#1a3a2a;border:1px solid #238636;border-radius:14px 14px 2px 14px;
                padding:0.65rem 1rem;max-width:75%;font-size:0.88rem;color:#e6edf3;">
                    <span style="color:#8b949e;font-size:0.72rem;">You · {msg['time']}</span><br>
                    {msg['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            import re as _re
            html = _re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', msg['content'])
            html = html.replace('\n', '<br>').replace('`', '<code>').replace('`', '</code>')
            st.markdown(f"""
            <div style="display:flex;justify-content:flex-start;margin:0.5rem 0;">
                <div style="background:#161b22;border:1px solid #30363d;border-radius:14px 14px 14px 2px;
                padding:0.65rem 1rem;max-width:90%;font-size:0.83rem;color:#e6edf3;line-height:1.6;">
                    <span style="color:#58a6ff;font-weight:700;">🤖 STOX AI</span>
                    <span style="color:#8b949e;font-size:0.72rem;"> · {msg['time']}</span><br><br>
                    {html}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Input form
    with st.form("ai_chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_q = st.text_input(
                "Ask",
                placeholder="e.g. BTC buy karna chahiye? | RSI kya hai? | AAPL ka analysis karo",
                label_visibility="collapsed"
            )
        with col2:
            send = st.form_submit_button("Ask 🚀", type="primary", use_container_width=True)

        if send and user_q.strip():
            st.session_state.ai_chat_history.append({
                "role": "user", "content": user_q.strip(),
                "time": datetime.now().strftime("%H:%M")
            })
            with st.spinner("🤖 Thinking..."):
                response = get_ai_response(user_q.strip())
            st.session_state.ai_chat_history.append({
                "role": "assistant", "content": response,
                "time": datetime.now().strftime("%H:%M")
            })
            st.rerun()

    if st.button("🗑️ Clear Chat", key="clear_ai_chat"):
        st.session_state.ai_chat_history = []
        st.rerun()

    st.markdown("""
    <div style="background:#161b22;border-left:3px solid #388bfd;padding:0.6rem 0.9rem;
    border-radius:0 8px 8px 0;font-size:0.75rem;color:#8b949e;margin-top:0.8rem;">
    ℹ️ STOX AI educational purposes ke liye hai. SEBI-registered investment advisor nahi hai.
    Real investment decisions ke liye SEBI-registered advisor se consult karo.
    </div>
    """, unsafe_allow_html=True)
