"""Technical & Pattern Engine — RSI, MACD, BB, S/R, Patterns (pure pandas/numpy)"""
import pandas as pd, numpy as np

def fetch_price_history(ticker, period="6mo", interval="1d"):
    import yfinance as yf
    df = yf.Ticker(ticker).history(period=period, interval=interval).dropna()
    return df

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0,np.nan)
    return (100 - (100/(1+rs))).fillna(50)

def macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast,adjust=False).mean()
    ema_slow = series.ewm(span=slow,adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal,adjust=False).mean()
    return macd_line, signal_line, macd_line-signal_line

def bollinger_bands(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    return sma+std_dev*std, sma, sma-std_dev*std

def moving_averages(df):
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["EMA20"] = df["Close"].ewm(span=20,adjust=False).mean()
    return df

def detect_support_resistance(df, window=10):
    highs = df["High"].rolling(window,center=True).max()
    lows  = df["Low"].rolling(window,center=True).min()
    resistance = df["High"][df["High"]==highs].dropna().tail(3).tolist()
    support    = df["Low"][df["Low"]==lows].dropna().tail(3).tolist()
    return support, resistance

def detect_candlestick_patterns(df):
    patterns = []
    if len(df)<3: return patterns
    last = df.iloc[-1]; prev = df.iloc[-2]
    body = abs(last["Close"]-last["Open"]); r = last["High"]-last["Low"]+1e-9
    upper_wick = last["High"]-max(last["Close"],last["Open"])
    lower_wick = min(last["Close"],last["Open"])-last["Low"]
    if prev["Close"]<prev["Open"] and last["Close"]>last["Open"] and last["Close"]>prev["Open"] and last["Open"]<prev["Close"]:
        patterns.append(("Bullish Engulfing","Bullish"))
    if prev["Close"]>prev["Open"] and last["Close"]<last["Open"] and last["Open"]>prev["Close"] and last["Close"]<prev["Open"]:
        patterns.append(("Bearish Engulfing","Bearish"))
    if lower_wick>body*2 and upper_wick<body*0.5 and body>0: patterns.append(("Hammer","Bullish"))
    if upper_wick>body*2 and lower_wick<body*0.5 and body>0: patterns.append(("Shooting Star","Bearish"))
    if body/r<0.1: patterns.append(("Doji","Neutral"))
    return patterns

def detect_head_and_shoulders(df, lookback=40):
    recent = df.tail(lookback).reset_index(); highs = recent["High"]
    peak_idxs = [i for i in range(2,len(highs)-2) if highs[i]==highs[i-2:i+3].max()]
    if len(peak_idxs)<3: return None
    p1,p2,p3 = peak_idxs[-3],peak_idxs[-2],peak_idxs[-1]
    h1,h2,h3 = highs[p1],highs[p2],highs[p3]
    if h2>h1 and h2>h3 and abs(h1-h3)/h2<0.05: return "Head & Shoulders (Bearish Reversal)"
    return None

def run_technical_engine(ticker, period="6mo"):
    try:
        df = fetch_price_history(ticker, period=period)
        if df.empty or len(df)<20: return {"ok":False,"error":"Not enough data"}
        df["RSI"] = rsi(df["Close"])
        ml,sl,hl = macd(df["Close"]); df["MACD"]=ml; df["MACD_signal"]=sl; df["MACD_hist"]=hl
        u,m,l = bollinger_bands(df["Close"]); df["BB_upper"]=u; df["BB_mid"]=m; df["BB_lower"]=l
        df = moving_averages(df)
        support,resistance = detect_support_resistance(df)
        candle_pats = detect_candlestick_patterns(df)
        hns = detect_head_and_shoulders(df)
        last_rsi = round(df["RSI"].iloc[-1],2)
        last_macd = round(df["MACD_hist"].iloc[-1],3)
        rsi_sig = "Overbought (possible pullback)" if last_rsi>70 else "Oversold (possible bounce)" if last_rsi<30 else "Neutral zone"
        macd_sig = "Bullish momentum" if last_macd>0 else "Bearish momentum"
        return {"ok":True,"df":df,"rsi":last_rsi,"rsi_signal":rsi_sig,"macd_hist":last_macd,
                "macd_signal":macd_sig,"support":support,"resistance":resistance,
                "candlestick_patterns":candle_pats,"chart_pattern":hns}
    except Exception as e:
        return {"ok":False,"error":str(e)}
