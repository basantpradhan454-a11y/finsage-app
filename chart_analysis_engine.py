"""
FinSage Chart Analysis Engine
FastAPI-style analysis logic running inside Streamlit
Pure pandas/numpy — no FastAPI server needed for Streamlit Cloud
"""
from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
import pandas as pd

# ── PATTERN LIBRARY (Educational White Paper) ────────────────────────────────
PATTERN_LIBRARY: Dict[str, Dict[str, str]] = {
    "doji": {
        "name": "Doji",
        "bias": "neutral",
        "definition": "Open aur Close price almost barabar — buyers aur sellers ka tug of war. Trend reversal ka signal ho sakta hai.",
    },
    "hammer": {
        "name": "Hammer",
        "bias": "bullish",
        "definition": "Chhoti body upar, lambi lower wick. Downtrend ke baad milne par bullish reversal signal. Sellers ne push kiya but buyers ne wapas upar kheencha.",
    },
    "inverted_hammer": {
        "name": "Inverted Hammer",
        "bias": "bullish",
        "definition": "Chhoti body neeche, lambi upper wick. Downtrend mein buyers ki entry dikhata hai — potential bullish reversal.",
    },
    "shooting_star": {
        "name": "Shooting Star",
        "bias": "bearish",
        "definition": "Chhoti body neeche, lambi upper wick. Uptrend ke baad bearish reversal warning — buyers ne upar le gaye but sellers ne wapas gira diya.",
    },
    "hanging_man": {
        "name": "Hanging Man",
        "bias": "bearish",
        "definition": "Hammer jaisi shape but uptrend ke baad — sellers enter ho rahe hain, possible bearish reversal.",
    },
    "bullish_engulfing": {
        "name": "Bullish Engulfing",
        "bias": "bullish",
        "definition": "Chhoti red candle ke baad badi green candle jo use poori tarah cover kar le. Buyers ne control le liya — strong bullish reversal signal.",
    },
    "bearish_engulfing": {
        "name": "Bearish Engulfing",
        "bias": "bearish",
        "definition": "Chhoti green candle ke baad badi red candle jo use poori tarah cover kar le. Sellers ne control le liya — strong bearish reversal signal.",
    },
    "morning_star": {
        "name": "Morning Star",
        "bias": "bullish",
        "definition": "3-candle: badi red → chhoti indecision → badi green. Downtrend se uptrend mein shift — classic bullish reversal.",
    },
    "evening_star": {
        "name": "Evening Star",
        "bias": "bearish",
        "definition": "3-candle: badi green → chhoti indecision → badi red. Uptrend khatam hone ka signal — classic bearish reversal.",
    },
    "three_white_soldiers": {
        "name": "Three White Soldiers",
        "bias": "bullish",
        "definition": "Lagatar 3 badi green candles, har ek pichli se upar close. Strong sustained buying — powerful bullish signal.",
    },
    "three_black_crows": {
        "name": "Three Black Crows",
        "bias": "bearish",
        "definition": "Lagatar 3 badi red candles, har ek neeche close. Strong sustained selling — powerful bearish signal.",
    },
    "piercing_line": {
        "name": "Piercing Line",
        "bias": "bullish",
        "definition": "Badi red candle ke baad green candle jo pichhli candle ki body ke aadhe se upar close ho. Bullish reversal pattern.",
    },
    "dark_cloud_cover": {
        "name": "Dark Cloud Cover",
        "bias": "bearish",
        "definition": "Badi green candle ke baad red candle jo pichhli candle ki body ke aadhe se neeche close ho. Bearish reversal signal.",
    },
}

CONCEPT_LIBRARY: Dict[str, str] = {
    "support": "Support woh price level hai jahan historically buying itni strong rahi ki price neeche nahi gayi. Ek floor ki tarah — price bounce karti hai.",
    "resistance": "Resistance ek price ceiling hai jahan selling itni strong rahi ki price nahi toot payi. Price yahan se wapas neeche aa jaati hai.",
    "volume": "Volume batata hai kitne shares trade hue. High volume ke saath move zyada valid hota hai — zyada traders us direction mein agree kar rahe hain.",
    "rsi": "RSI (0-100): 70+ overbought (pullback aa sakta hai), 30- oversold (bounce aa sakta hai). Momentum dikhata hai.",
    "macd": "MACD do moving averages ka difference. Signal line ke upar cross = bullish, neeche = bearish. Trend ka momentum dikhata hai.",
    "trend": "Trend price ki overall direction. Higher highs + higher lows = uptrend. Lower highs + lower lows = downtrend.",
    "moving_average": "MA ek period ke average price ki smooth line. Price MA ke upar = bullish bias, neeche = bearish bias.",
    "candlestick": "Ek candle ek time period ka Open, High, Low, Close dikhata hai. Body, upper wick, lower wick — sab milke market psychology batate hain.",
}


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sma20"] = df["close"].rolling(20, min_periods=1).mean()
    df["sma50"] = df["close"].rolling(50, min_periods=1).mean()
    df["ema9"]  = df["close"].ewm(span=9,  adjust=False).mean()
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14, min_periods=1).mean()
    avg_loss = loss.rolling(14, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi14"] = (100 - 100 / (1 + rs)).fillna(50)

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"]        = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]
    df["volume_ma20"] = df["volume"].rolling(20, min_periods=1).mean()

    # Bollinger Bands
    df["bb_mid"]   = df["close"].rolling(20, min_periods=1).mean()
    df["bb_std"]   = df["close"].rolling(20, min_periods=1).std().fillna(0)
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
    return df


def find_support_resistance(df: pd.DataFrame, left=3, right=3, cluster_pct=0.0075):
    highs, lows, n = df["high"].values, df["low"].values, len(df)
    pivot_highs, pivot_lows = [], []
    for i in range(left, n - right):
        if highs[i] == highs[i-left:i+right+1].max():
            pivot_highs.append((i, highs[i]))
        if lows[i] == lows[i-left:i+right+1].min():
            pivot_lows.append((i, lows[i]))

    def cluster(pivots, kind):
        if not pivots: return []
        ps = sorted(pivots, key=lambda x: x[1])
        clusters = [[ps[0]]]
        for p in ps[1:]:
            avg = np.mean([x[1] for x in clusters[-1]])
            if abs(p[1] - avg) / avg <= cluster_pct:
                clusters[-1].append(p)
            else:
                clusters.append([p])
        zones = []
        for c in clusters:
            price = float(np.mean([x[1] for x in c]))
            zones.append({"type": kind, "price": round(price, 2),
                          "strength": len(c),
                          "first_touch_index": min(x[0] for x in c),
                          "last_touch_index": max(x[0] for x in c)})
        zones = [z for z in zones if z["strength"] >= 2]
        zones.sort(key=lambda z: -z["strength"])
        return zones[:8]

    return cluster(pivot_lows, "support") + cluster(pivot_highs, "resistance")


def detect_patterns(df: pd.DataFrame):
    results = []
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    n = len(df)

    def body(o_, c_): return abs(c_ - o_)
    def rng(h_, l_): return max(h_ - l_, 1e-9)
    def bull(o_, c_): return c_ > o_

    def add(idx, key):
        info = PATTERN_LIBRARY[key]
        results.append({"index": idx, "pattern_key": key,
                         "name": info["name"], "bias": info["bias"],
                         "definition": info["definition"]})

    for i in range(n):
        bd = body(o[i], c[i]); rg = rng(h[i], l[i])
        uw = h[i] - max(o[i], c[i]); lw = min(o[i], c[i]) - l[i]
        bp = bd / rg

        if bp < 0.10:
            add(i, "doji")
        elif bp < 0.35 and lw > 2 * bd and uw < bd:
            prior_down = i >= 3 and c[i-3] > c[i-1]
            add(i, "hammer" if prior_down else "hanging_man")
        elif bp < 0.35 and uw > 2 * bd and lw < bd:
            prior_down = i >= 3 and c[i-3] > c[i-1]
            add(i, "inverted_hammer" if prior_down else "shooting_star")

        if i >= 1:
            po, pc = o[i-1], c[i-1]
            if not bull(po, pc) and bull(o[i], c[i]) and c[i] >= po and o[i] <= pc:
                add(i, "bullish_engulfing")
            if bull(po, pc) and not bull(o[i], c[i]) and o[i] >= pc and c[i] <= po:
                add(i, "bearish_engulfing")
            # Piercing / Dark Cloud
            if not bull(po, pc) and bull(o[i], c[i]):
                mid_prev = (po + pc) / 2
                if c[i] > mid_prev and o[i] < pc:
                    add(i, "piercing_line")
            if bull(po, pc) and not bull(o[i], c[i]):
                mid_prev = (po + pc) / 2
                if c[i] < mid_prev and o[i] > pc:
                    add(i, "dark_cloud_cover")

        if i >= 2:
            o1,c1 = o[i-2],c[i-2]; o2,c2 = o[i-1],c[i-1]; o3,c3 = o[i],c[i]
            b1=body(o1,c1); b2=body(o2,c2); b3=body(o3,c3)
            rg1=rng(h[i-2],l[i-2]); rg2=rng(h[i-1],l[i-1]); rg3=rng(h[i],l[i])
            if (not bull(o1,c1) and b1/rg1>0.5 and b2/rg2<0.4
                    and bull(o3,c3) and b3/rg3>0.5 and c3>(o1+c1)/2):
                add(i, "morning_star")
            if (bull(o1,c1) and b1/rg1>0.5 and b2/rg2<0.4
                    and not bull(o3,c3) and b3/rg3>0.5 and c3<(o1+c1)/2):
                add(i, "evening_star")
            if bull(o1,c1) and bull(o2,c2) and bull(o3,c3) and c1<c2<c3 and o1<o2<o3:
                add(i, "three_white_soldiers")
            if not bull(o1,c1) and not bull(o2,c2) and not bull(o3,c3) and c1>c2>c3 and o1>o2>o3:
                add(i, "three_black_crows")
    return results


def full_analysis(df: pd.DataFrame, symbol: str = "") -> Dict[str, Any]:
    df = df.reset_index(drop=True)
    df = compute_indicators(df)
    sr_zones = find_support_resistance(df)
    patterns = detect_patterns(df)
    last = df.iloc[-1]
    votes = sum([
        float(last["close"]) > float(last["sma20"]),
        float(last["sma20"]) > float(last["sma50"]),
        float(last["rsi14"]) > 50,
        float(last["macd"]) > float(last["macd_signal"]),
    ])
    bias = "bullish" if votes >= 3 else "bearish" if votes <= 1 else "neutral"
    return {
        "symbol": symbol.upper(),
        "candles": df[["time","open","high","low","close","volume"]].to_dict("records"),
        "indicators": df[["time","sma20","sma50","ema9","ema21","rsi14","macd","macd_signal","macd_hist","volume_ma20","bb_upper","bb_mid","bb_lower"]].to_dict("records"),
        "support_resistance": sr_zones,
        "patterns": patterns,
        "overall_bias": bias,
        "glossary": CONCEPT_LIBRARY,
    }
