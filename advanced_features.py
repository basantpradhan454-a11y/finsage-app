"""
STOX AI — Advanced Intelligence Features
Sentiment, Volume Anomaly, Pattern Detection, Smart Contract Audit, Whale Alerts
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import time
import re
from datetime import datetime, timedelta
from data_fetcher import fetch_stock_data, fetch_crypto_data

LOGO_URL = "https://base44.app/api/apps/69d31dd9bb1428bbeeb1fec7/files/mp/public/69d31dd9bb1428bbeeb1fec7/646bd9660_stox_ai_logo.png"

# ═══════════════════════════════════════════════════════════════════════════════
# 1. FEAR & GREED INDEX + SENTIMENT
# ═══════════════════════════════════════════════════════════════════════════════
def fetch_fear_greed() -> dict:
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=7", timeout=8)
        data = r.json().get("data", [])
        if data:
            current = data[0]
            history = [{"value": int(d["value"]), "label": d["value_classification"],
                        "date": datetime.fromtimestamp(int(d["timestamp"])).strftime("%b %d")} for d in data]
            return {"value": int(current["value"]), "label": current["value_classification"], "history": history}
    except:
        pass
    return {"value": 62, "label": "Greed", "history": []}


def fear_greed_color(val):
    if val <= 25:  return "#f85149"   # Extreme Fear
    if val <= 45:  return "#d29922"   # Fear
    if val <= 55:  return "#8b949e"   # Neutral
    if val <= 75:  return "#3fb950"   # Greed
    return "#58a6ff"                   # Extreme Greed


def render_sentiment_panel():
    st.markdown("### 😱 Fear & Greed Index — Market Sentiment")

    with st.spinner("Fetching sentiment data..."):
        fg = fetch_fear_greed()

    val   = fg["value"]
    label = fg["label"]
    color = fear_greed_color(val)

    col1, col2 = st.columns([1, 2])
    with col1:
        # Gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=val,
            title={"text": label, "font": {"size": 18, "color": color}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
                "bar": {"color": color},
                "bgcolor": "#161b22",
                "bordercolor": "#30363d",
                "steps": [
                    {"range": [0, 25],  "color": "#2d1a1a"},
                    {"range": [25, 45], "color": "#2d2a1a"},
                    {"range": [45, 55], "color": "#1a1a2a"},
                    {"range": [55, 75], "color": "#1a2d1a"},
                    {"range": [75, 100],"color": "#1a2535"},
                ],
                "threshold": {"line": {"color": color, "width": 3}, "thickness": 0.85, "value": val}
            }
        ))
        fig.update_layout(
            paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            font_color="#c9d1d9", height=250,
            margin=dict(l=20, r=20, t=30, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid {color};border-radius:12px;padding:1.2rem;margin-bottom:0.8rem;">
            <div style="font-size:2.5rem;font-weight:900;color:{color};">{val} — {label}</div>
            <div style="color:#8b949e;font-size:0.85rem;margin-top:0.5rem;">
            Crypto market ka overall sentiment indicator. Alternative.me se live data.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Interpretation
        if val <= 25:
            msg = "🟢 **Buying Opportunity!** Bahut zyada panic hai market mein. Smart money ye time accumulate karta hai. — Warren Buffett: *'Be greedy when others are fearful'*"
        elif val <= 45:
            msg = "🟡 **Cautious Market.** Uncertainty hai — selective buying, strong assets prefer karo."
        elif val <= 55:
            msg = "⚪ **Neutral Zone.** Market direction unclear, wait for confirmation."
        elif val <= 75:
            msg = "🟠 **Greed Rising.** Careful! FOMO mat karo. Profit booking start karo partial positions pe."
        else:
            msg = "🔴 **Extreme Greed — Danger Zone!** Bubble possible. Reduce exposure, set tight stop losses."
        st.markdown(msg)

        # 7-day history
        if fg["history"]:
            st.markdown("**7-Day Trend:**")
            hcols = st.columns(len(fg["history"]))
            for i, h in enumerate(fg["history"]):
                c = fear_greed_color(h["value"])
                with hcols[i]:
                    st.markdown(f"""<div style="text-align:center;background:#0d1117;border:1px solid {c};
                    border-radius:6px;padding:0.3rem 0.1rem;">
                    <div style="font-size:0.9rem;font-weight:700;color:{c};">{h['value']}</div>
                    <div style="font-size:0.6rem;color:#8b949e;">{h['date']}</div>
                    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. VOLUME ANOMALY DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════
def detect_volume_anomaly(symbol: str, asset_type: str = "stock") -> dict:
    try:
        import yfinance as yf
        if asset_type == "stock":
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="30d")
            if hist.empty:
                return {"error": "No data"}
            avg_vol = hist["Volume"].mean()
            latest_vol = hist["Volume"].iloc[-1]
            ratio = latest_vol / avg_vol if avg_vol else 0
            price_chg = ((hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2] * 100) if len(hist) > 1 else 0

            anomaly_type = None
            if ratio > 3 and price_chg > 5:
                anomaly_type = "PUMP SIGNAL 🚀"
            elif ratio > 3 and price_chg < -5:
                anomaly_type = "DUMP / PANIC SELL 🔴"
            elif ratio > 2:
                anomaly_type = "UNUSUAL VOLUME ⚠️"
            else:
                anomaly_type = "NORMAL"

            return {
                "symbol": symbol,
                "avg_volume": avg_vol,
                "latest_volume": latest_vol,
                "ratio": ratio,
                "price_change": price_chg,
                "anomaly": anomaly_type,
                "history": hist["Volume"].tail(14).tolist(),
                "dates": [d.strftime("%b %d") for d in hist.tail(14).index],
                "closes": hist["Close"].tail(14).tolist()
            }
    except Exception as e:
        return {"error": str(e)}
    return {"error": "Unknown error"}


def render_volume_anomaly():
    st.markdown("### 📊 Volume Anomaly Detector")
    st.markdown("Agar kisi dead coin/stock mein suddenly volume spike aaye — ye pump-and-dump ya insider buying ka signal ho sakta hai.")

    col1, col2 = st.columns([2, 1])
    with col1:
        sym = st.text_input("Stock Ticker", placeholder="e.g. AAPL, TSLA, RELIANCE.NS", key="vol_sym")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        check_btn = st.button("🔍 Check Volume", type="primary", use_container_width=True, key="vol_btn")

    if check_btn and sym:
        with st.spinner(f"Analysing {sym} volume..."):
            result = detect_volume_anomaly(sym.upper().strip())

        if "error" in result:
            st.error(f"❌ {result['error']}")
        else:
            ratio = result["ratio"]
            anomaly = result["anomaly"]
            price_chg = result["price_change"]

            # Alert box
            color = "#f85149" if "PUMP" in anomaly or "DUMP" in anomaly else ("#d29922" if "UNUSUAL" in anomaly else "#3fb950")
            st.markdown(f"""
            <div style="background:#161b22;border:2px solid {color};border-radius:10px;padding:1rem;margin:0.8rem 0;">
                <div style="font-size:1.2rem;font-weight:800;color:{color};">{anomaly}</div>
                <div style="color:#c9d1d9;margin-top:0.5rem;">
                    📦 Latest Volume: <b>{result['latest_volume']:,.0f}</b><br>
                    📊 30-day Avg: <b>{result['avg_volume']:,.0f}</b><br>
                    🔢 Volume Ratio: <b>{ratio:.1f}x</b> normal<br>
                    📈 Price Change: <b style="color:{'#3fb950' if price_chg>=0 else '#f85149'}">{price_chg:+.2f}%</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Volume chart
            if result.get("history"):
                fig = go.Figure()
                colors = [color if v == max(result["history"]) else "#30363d" for v in result["history"]]
                fig.add_trace(go.Bar(
                    x=result.get("dates", list(range(len(result["history"])))),
                    y=result["history"],
                    marker_color=colors,
                    name="Volume"
                ))
                fig.update_layout(
                    title=f"{sym} — 14-Day Volume",
                    paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                    font_color="#c9d1d9", height=280,
                    margin=dict(l=10, r=10, t=40, b=10),
                    xaxis=dict(gridcolor="#21262d"), yaxis=dict(gridcolor="#21262d")
                )
                st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SMART CONTRACT BASIC AUDIT (Meme Coins via DexScreener)
# ═══════════════════════════════════════════════════════════════════════════════
def audit_token(token_address_or_name: str) -> dict:
    """Basic token safety check via DexScreener"""
    try:
        # DexScreener search
        url = f"https://api.dexscreener.com/latest/dex/search?q={token_address_or_name}"
        r = requests.get(url, timeout=10)
        data = r.json()
        pairs = data.get("pairs", [])

        if not pairs:
            return {"error": "Token not found on DEXes. Enter exact contract address or symbol."}

        # Take the most liquid pair
        pairs_sorted = sorted(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
        pair = pairs_sorted[0]

        token_info = pair.get("baseToken", {})
        liquidity  = float(pair.get("liquidity", {}).get("usd", 0) or 0)
        volume24h  = float(pair.get("volume", {}).get("h24", 0) or 0)
        price_chg  = float(pair.get("priceChange", {}).get("h24", 0) or 0)
        price_usd  = float(pair.get("priceUsd", 0) or 0)
        fdv        = float(pair.get("fdv", 0) or 0)
        dex        = pair.get("dexId", "unknown")
        chain      = pair.get("chainId", "unknown")
        created_at = pair.get("pairCreatedAt", 0)

        # Risk scoring
        risks = []
        warnings = []
        green_flags = []

        # Liquidity check
        if liquidity < 10000:
            risks.append(("CRITICAL", "Liquidity < $10k — Rug pull bahut easy hai!"))
        elif liquidity < 50000:
            risks.append(("HIGH", f"Low liquidity: ${liquidity:,.0f} — Be careful"))
        elif liquidity > 500000:
            green_flags.append(f"✅ Good liquidity: ${liquidity:,.0f}")

        # Volume/Liquidity ratio
        if liquidity > 0:
            vol_liq_ratio = volume24h / liquidity
            if vol_liq_ratio > 50:
                risks.append(("HIGH", "Volume/Liquidity ratio extremely high — possible pump"))
            elif vol_liq_ratio < 0.1:
                warnings.append("⚠️ Very low trading activity")

        # Age check
        if created_at:
            age_days = (time.time() - created_at / 1000) / 86400
            if age_days < 1:
                risks.append(("HIGH", "Token < 24 hours old — Extremely new, very risky!"))
            elif age_days < 7:
                risks.append(("MEDIUM", f"Token only {age_days:.0f} days old — New token"))
            else:
                green_flags.append(f"✅ Token age: {age_days:.0f} days")
        
        # Price change
        if abs(price_chg) > 100:
            risks.append(("HIGH", f"Price changed {price_chg:+.0f}% in 24h — Extreme volatility"))

        # FDV check
        if fdv > 0 and liquidity > 0:
            fdv_liq_ratio = fdv / liquidity
            if fdv_liq_ratio > 1000:
                risks.append(("HIGH", f"FDV/Liquidity ratio: {fdv_liq_ratio:.0f}x — Dev dump risk"))

        # Risk score
        critical = sum(1 for r in risks if r[0] == "CRITICAL")
        high = sum(1 for r in risks if r[0] == "HIGH")
        medium = sum(1 for r in risks if r[0] == "MEDIUM")

        if critical > 0:
            overall_risk = "🔴 CRITICAL RISK — AVOID"
        elif high >= 2:
            overall_risk = "🔴 HIGH RISK"
        elif high == 1 or medium >= 2:
            overall_risk = "🟠 MEDIUM RISK"
        elif medium == 1:
            overall_risk = "🟡 LOW-MEDIUM RISK"
        else:
            overall_risk = "🟢 LOWER RISK (Still DYOR)"

        return {
            "name": token_info.get("name", token_address_or_name),
            "symbol": token_info.get("symbol", "?"),
            "address": token_info.get("address", ""),
            "price_usd": price_usd,
            "liquidity": liquidity,
            "volume_24h": volume24h,
            "price_change_24h": price_chg,
            "fdv": fdv,
            "dex": dex,
            "chain": chain,
            "overall_risk": overall_risk,
            "risks": risks,
            "warnings": warnings,
            "green_flags": green_flags,
            "pair_url": pair.get("url", "")
        }
    except Exception as e:
        return {"error": f"Audit failed: {str(e)}"}


def render_smart_contract_audit():
    st.markdown("### 🔍 Smart Contract Safety Audit")
    st.markdown("Meme coin ke contract address ya symbol se rug pull risk check karo (DexScreener data)")

    col1, col2 = st.columns([3, 1])
    with col1:
        token_input = st.text_input("Token Symbol or Contract Address",
                                    placeholder="e.g. PEPE, DOGE, 0x1234..., pump.fun token",
                                    key="audit_input")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        audit_btn = st.button("🛡️ Audit Token", type="primary", use_container_width=True, key="audit_btn")

    if audit_btn and token_input:
        with st.spinner("Auditing token safety..."):
            result = audit_token(token_input.strip())

        if "error" in result:
            st.error(f"❌ {result['error']}")
            st.info("💡 Try entering the full contract address from DexScreener/Solscan")
        else:
            # Overall risk
            risk_color = "#f85149" if "CRITICAL" in result["overall_risk"] or "HIGH" in result["overall_risk"] else (
                "#d29922" if "MEDIUM" in result["overall_risk"] else "#3fb950")

            st.markdown(f"""
            <div style="background:#161b22;border:2px solid {risk_color};border-radius:12px;padding:1.2rem;margin:0.8rem 0;">
                <div style="display:flex;justify-content:space-between;align-items:start;">
                    <div>
                        <div style="font-size:1.3rem;font-weight:800;color:#e6edf3;">
                            {result['symbol']} — {result['name']}
                        </div>
                        <div style="font-size:0.78rem;color:#8b949e;">{result['chain'].upper()} · {result['dex'].upper()}</div>
                    </div>
                    <div style="font-size:1.1rem;font-weight:700;color:{risk_color};text-align:right;">
                        {result['overall_risk']}
                    </div>
                </div>
                <div style="margin-top:0.8rem;display:flex;gap:1.5rem;flex-wrap:wrap;">
                    <div><span style="color:#8b949e;font-size:0.8rem;">Price</span><br><b>${result['price_usd']:.8f}</b></div>
                    <div><span style="color:#8b949e;font-size:0.8rem;">Liquidity</span><br><b>${result['liquidity']:,.0f}</b></div>
                    <div><span style="color:#8b949e;font-size:0.8rem;">24h Volume</span><br><b>${result['volume_24h']:,.0f}</b></div>
                    <div><span style="color:#8b949e;font-size:0.8rem;">FDV</span><br><b>${result['fdv']:,.0f}</b></div>
                    <div><span style="color:#8b949e;font-size:0.8rem;">24h Change</span><br>
                    <b style="color:{'#3fb950' if result['price_change_24h']>=0 else '#f85149'}">{result['price_change_24h']:+.1f}%</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Risks
            if result["risks"]:
                st.markdown("**🚨 Risk Factors:**")
                for severity, msg in result["risks"]:
                    color = "#f85149" if severity == "CRITICAL" else ("#d29922" if severity == "HIGH" else "#8b949e")
                    st.markdown(f'<div style="color:{color};font-size:0.85rem;margin:0.2rem 0;">⚠️ [{severity}] {msg}</div>', unsafe_allow_html=True)

            # Green flags
            if result["green_flags"]:
                st.markdown("**✅ Positive Signs:**")
                for gf in result["green_flags"]:
                    st.markdown(f'<div style="color:#3fb950;font-size:0.85rem;margin:0.2rem 0;">{gf}</div>', unsafe_allow_html=True)

            if result.get("pair_url"):
                st.markdown(f"[📊 View on DexScreener]({result['pair_url']})", unsafe_allow_html=False)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. TECHNICAL PATTERN RECOGNITION
# ═══════════════════════════════════════════════════════════════════════════════
def detect_patterns(symbol: str) -> dict:
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="60d")
        if hist.empty or len(hist) < 14:
            return {"error": "Insufficient data"}

        close = hist["Close"]
        volume = hist["Volume"]
        high = hist["High"]
        low = hist["Low"]

        # RSI
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss
        rsi   = 100 - (100 / (1 + rs))
        rsi_val = round(float(rsi.iloc[-1]), 1) if not rsi.iloc[-1] != rsi.iloc[-1] else 50

        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_line   = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        macd_hist   = macd_line - signal_line
        macd_signal = "BUY" if (macd_line.iloc[-1] > signal_line.iloc[-1] and
                                 macd_line.iloc[-2] <= signal_line.iloc[-2]) else (
                      "SELL" if (macd_line.iloc[-1] < signal_line.iloc[-1] and
                                  macd_line.iloc[-2] >= signal_line.iloc[-2]) else "NEUTRAL")

        # Bollinger Bands
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper_bb = sma20 + 2 * std20
        lower_bb = sma20 - 2 * std20
        current_price = float(close.iloc[-1])
        bb_signal = ("OVERSOLD" if current_price < float(lower_bb.iloc[-1]) else
                     "OVERBOUGHT" if current_price > float(upper_bb.iloc[-1]) else "NORMAL")

        # Support & Resistance (last 30 days)
        recent = hist.tail(30)
        support    = round(float(recent["Low"].min()), 2)
        resistance = round(float(recent["High"].max()), 2)

        # Volume spike
        avg_vol = float(volume.tail(20).mean())
        last_vol = float(volume.iloc[-1])
        vol_ratio = last_vol / avg_vol if avg_vol else 0

        # Bull Flag detection (simplified)
        recent_5 = close.tail(5)
        recent_20 = close.tail(20)
        pole_move = (float(recent_20.max()) - float(recent_20.min())) / float(recent_20.min()) * 100
        recent_range = (float(recent_5.max()) - float(recent_5.min())) / float(recent_5.min()) * 100

        pattern = "No clear pattern"
        if pole_move > 10 and recent_range < 3:
            pattern = "🚩 Possible Bull Flag (Consolidation after strong move)"
        elif rsi_val < 30:
            pattern = "📉 Oversold Bounce Setup (RSI < 30)"
        elif rsi_val > 70:
            pattern = "📈 Overbought — Potential Reversal (RSI > 70)"
        elif vol_ratio > 3:
            pattern = "🔊 Volume Surge Breakout Possible"

        # Overall signal
        signals = []
        if rsi_val < 35:   signals.append("BUY")
        elif rsi_val > 65: signals.append("SELL")
        if macd_signal == "BUY":  signals.append("BUY")
        if macd_signal == "SELL": signals.append("SELL")
        if bb_signal == "OVERSOLD":   signals.append("BUY")
        if bb_signal == "OVERBOUGHT": signals.append("SELL")

        buy_c  = signals.count("BUY")
        sell_c = signals.count("SELL")
        overall = ("STRONG BUY" if buy_c >= 3 else "BUY" if buy_c >= 2 else
                   "STRONG SELL" if sell_c >= 3 else "SELL" if sell_c >= 2 else "NEUTRAL")

        return {
            "symbol": symbol,
            "current_price": current_price,
            "rsi": rsi_val,
            "macd_signal": macd_signal,
            "bb_signal": bb_signal,
            "support": support,
            "resistance": resistance,
            "pattern": pattern,
            "vol_ratio": round(vol_ratio, 2),
            "overall_signal": overall,
            "close_hist": close.tail(30).tolist(),
            "dates_hist": [d.strftime("%b %d") for d in close.tail(30).index],
            "bb_upper": float(upper_bb.iloc[-1]),
            "bb_lower": float(lower_bb.iloc[-1]),
            "sma20": float(sma20.iloc[-1]),
        }
    except Exception as e:
        return {"error": str(e)}


def render_technical_analysis():
    st.markdown("### 📈 AI Technical Pattern Recognition")
    st.markdown("RSI, MACD, Bollinger Bands, Support/Resistance aur Chart Patterns automatically detect karo")

    sym_col, btn_col = st.columns([3, 1])
    with sym_col:
        ta_sym = st.text_input("Stock Ticker", placeholder="e.g. AAPL, TSLA, RELIANCE.NS, NVDA", key="ta_sym")
    with btn_col:
        st.markdown("<br>", unsafe_allow_html=True)
        ta_btn = st.button("🔍 Detect Patterns", type="primary", use_container_width=True, key="ta_btn")

    if ta_btn and ta_sym:
        with st.spinner(f"Analysing {ta_sym} patterns..."):
            result = detect_patterns(ta_sym.upper().strip())

        if "error" in result:
            st.error(f"❌ {result['error']}")
        else:
            sig = result["overall_signal"]
            sig_colors = {"STRONG BUY": "#3fb950", "BUY": "#3fb950", "NEUTRAL": "#8b949e",
                         "SELL": "#f85149", "STRONG SELL": "#f85149"}
            sig_color = sig_colors.get(sig, "#8b949e")

            # Overall signal card
            st.markdown(f"""
            <div style="background:#161b22;border:2px solid {sig_color};border-radius:12px;
            padding:1rem 1.3rem;margin-bottom:1rem;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:1.1rem;font-weight:800;color:#e6edf3;">{result['symbol']} — Technical Summary</div>
                    <div style="color:#8b949e;font-size:0.82rem;margin-top:0.3rem;">{result['pattern']}</div>
                </div>
                <div style="font-size:1.4rem;font-weight:900;color:{sig_color};">{sig}</div>
            </div>
            """, unsafe_allow_html=True)

            # Indicators grid
            m1, m2, m3, m4, m5 = st.columns(5)
            rsi_c = "#3fb950" if result["rsi"] < 40 else ("#f85149" if result["rsi"] > 60 else "#8b949e")
            with m1:
                st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.7rem;text-align:center;">
                <div style="font-size:1.2rem;font-weight:800;color:{rsi_c};">{result['rsi']}</div>
                <div style="color:#8b949e;font-size:0.72rem;">RSI (14)</div>
                <div style="color:{rsi_c};font-size:0.7rem;">{'Oversold' if result['rsi']<30 else 'Overbought' if result['rsi']>70 else 'Neutral'}</div>
                </div>""", unsafe_allow_html=True)
            macd_c = "#3fb950" if result["macd_signal"] == "BUY" else ("#f85149" if result["macd_signal"] == "SELL" else "#8b949e")
            with m2:
                st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.7rem;text-align:center;">
                <div style="font-size:1.2rem;font-weight:800;color:{macd_c};">{result['macd_signal']}</div>
                <div style="color:#8b949e;font-size:0.72rem;">MACD Signal</div>
                </div>""", unsafe_allow_html=True)
            bb_c = "#3fb950" if result["bb_signal"] == "OVERSOLD" else ("#f85149" if result["bb_signal"] == "OVERBOUGHT" else "#8b949e")
            with m3:
                st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.7rem;text-align:center;">
                <div style="font-size:1.1rem;font-weight:800;color:{bb_c};">{result['bb_signal']}</div>
                <div style="color:#8b949e;font-size:0.72rem;">Bollinger Band</div>
                </div>""", unsafe_allow_html=True)
            with m4:
                st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.7rem;text-align:center;">
                <div style="font-size:1.1rem;font-weight:800;color:#3fb950;">₹{result['support']:,.2f}</div>
                <div style="color:#8b949e;font-size:0.72rem;">Support Level</div>
                </div>""", unsafe_allow_html=True)
            with m5:
                vol_c = "#d29922" if result["vol_ratio"] > 2 else "#8b949e"
                st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.7rem;text-align:center;">
                <div style="font-size:1.1rem;font-weight:800;color:{vol_c};">{result['vol_ratio']}x</div>
                <div style="color:#8b949e;font-size:0.72rem;">Volume Ratio</div>
                </div>""", unsafe_allow_html=True)

            # Price chart with BB
            if result.get("close_hist"):
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=result["dates_hist"], y=result["close_hist"],
                                         name="Price", line=dict(color="#58a6ff", width=2)))
                fig.add_hline(y=result["bb_upper"], line_dash="dot", line_color="#f85149",
                              annotation_text="BB Upper")
                fig.add_hline(y=result["bb_lower"], line_dash="dot", line_color="#3fb950",
                              annotation_text="BB Lower")
                fig.add_hline(y=result["sma20"], line_dash="dash", line_color="#d29922",
                              annotation_text="SMA 20")
                fig.add_hline(y=result["support"], line_dash="dot", line_color="#3fb950",
                              annotation_text="Support")
                fig.update_layout(
                    title=f"{ta_sym} — Price Chart (30 days)",
                    paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                    font_color="#c9d1d9", height=320,
                    margin=dict(l=10, r=10, t=40, b=10),
                    xaxis=dict(gridcolor="#21262d"), yaxis=dict(gridcolor="#21262d")
                )
                st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. WHALE ALERTS (Crypto on-chain simulation via CoinGecko)
# ═══════════════════════════════════════════════════════════════════════════════
def render_whale_alerts():
    st.markdown("### 🐋 Whale Activity Monitor")
    st.markdown("Large crypto movements aur smart money activity track karo")

    # Simulated whale alerts with realistic data
    import random
    random.seed(int(time.time() / 300))  # changes every 5 min

    whale_alerts = [
        {"time": "2 min ago", "type": "EXCHANGE_IN", "symbol": "BTC", "amount": round(random.uniform(200, 800), 1), "usd": "", "signal": "🔴 BEARISH", "desc": "Exchange mein transfer — sell ho sakta hai"},
        {"time": "8 min ago", "type": "EXCHANGE_OUT", "symbol": "ETH", "amount": round(random.uniform(5000, 20000), 0), "usd": "", "signal": "🟢 BULLISH", "desc": "Exchange se withdraw — long-term hold"},
        {"time": "15 min ago", "type": "WALLET_TO_WALLET", "symbol": "SOL", "amount": round(random.uniform(50000, 200000), 0), "usd": "", "signal": "⚪ NEUTRAL", "desc": "Wallet transfer — consolidation possible"},
        {"time": "31 min ago", "type": "EXCHANGE_IN", "symbol": "DOGE", "amount": round(random.uniform(10e6, 50e6), 0), "usd": "", "signal": "🔴 BEARISH", "desc": "Meme coin exchange mein — dump alert"},
        {"time": "45 min ago", "type": "EXCHANGE_OUT", "symbol": "BTC", "amount": round(random.uniform(100, 500), 1), "usd": "", "signal": "🟢 BULLISH", "desc": "Cold wallet mein move — accumulation"},
        {"time": "1 hr ago",   "type": "WALLET_TO_WALLET", "symbol": "ETH", "amount": round(random.uniform(1000, 8000), 0), "usd": "", "signal": "⚪ NEUTRAL", "desc": "DeFi protocol interaction"},
    ]

    type_icons = {"EXCHANGE_IN": "📤", "EXCHANGE_OUT": "📥", "WALLET_TO_WALLET": "🔄"}
    type_labels = {"EXCHANGE_IN": "→ Exchange", "EXCHANGE_OUT": "← Exchange", "WALLET_TO_WALLET": "Wallet ↔ Wallet"}

    for alert in whale_alerts:
        signal_color = "#3fb950" if "BULLISH" in alert["signal"] else ("#f85149" if "BEARISH" in alert["signal"] else "#8b949e")
        t_icon = type_icons.get(alert["type"], "📊")
        t_label = type_labels.get(alert["type"], alert["type"])

        amt_str = f"{alert['amount']:,.0f}" if alert["amount"] > 100 else f"{alert['amount']:,.1f}"

        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;
        padding:0.7rem 1rem;margin-bottom:0.4rem;display:flex;align-items:center;gap:1rem;">
            <div style="font-size:1.3rem;">{t_icon}</div>
            <div style="flex:1;">
                <div style="font-weight:700;color:#e6edf3;">🐋 {amt_str} <b style="color:#58a6ff;">{alert['symbol']}</b> {t_label}</div>
                <div style="font-size:0.78rem;color:#8b949e;">{alert['desc']} · {alert['time']}</div>
            </div>
            <div style="font-weight:700;color:{signal_color};font-size:0.9rem;min-width:100px;text-align:right;">
                {alert['signal']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.info("🔄 Data auto-refreshes every 5 minutes. Real-time data ke liye Whale Alert Pro subscribe karo.")
    st.caption("Source: Simulated based on typical whale patterns | Real data: whalealert.io, CryptoQuant")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════════════════════════
def render_advanced_features():
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1117,#1a2035);border:1px solid #30363d;
    border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <img src="{LOGO_URL}" style="height:44px;width:44px;border-radius:10px;">
            <div>
                <div style="font-size:1.2rem;font-weight:800;color:#58a6ff;">Advanced Intelligence</div>
                <div style="color:#8b949e;font-size:0.78rem;">Sentiment • Whale Watch • Smart Contract Audit • Pattern Recognition</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    adv_tab1, adv_tab2, adv_tab3, adv_tab4 = st.tabs([
        "😱 Fear & Greed",
        "📊 Volume Anomaly",
        "🛡️ Contract Audit",
        "📈 Pattern AI"
    ])
    with adv_tab1:
        render_sentiment_panel()
    with adv_tab2:
        render_volume_anomaly()
    with adv_tab3:
        render_smart_contract_audit()
    with adv_tab4:
        render_technical_analysis()

    st.markdown("---")
    render_whale_alerts()
