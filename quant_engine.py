"""Quantitative Engine — Volatility, Beta, Trend Probability (LogReg)"""
import numpy as np, pandas as pd
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

def calculate_volatility(df, window=20):
    returns = df["Close"].pct_change().dropna()
    daily_vol = returns.std()
    annualized_vol = daily_vol * np.sqrt(252)
    recent_vol = returns.tail(window).std() * np.sqrt(252)
    return {"daily_volatility_pct": round(daily_vol*100,2),
            "annualized_volatility_pct": round(annualized_vol*100,2),
            "recent_20d_volatility_pct": round(recent_vol*100,2)}

def calculate_beta(stock_df, benchmark_df):
    stock_r = stock_df["Close"].pct_change().dropna()
    bench_r = benchmark_df["Close"].pct_change().dropna()
    merged  = pd.concat([stock_r, bench_r], axis=1, join="inner")
    merged.columns = ["stock","bench"]
    if len(merged) < 10: return None
    cov = merged["stock"].cov(merged["bench"]); var = merged["bench"].var()
    return round(cov/var, 2) if var else None

def build_features(df):
    data = df.copy()
    data["return_1d"]       = data["Close"].pct_change()
    data["momentum_5d"]     = data["Close"].pct_change(5)
    data["momentum_10d"]    = data["Close"].pct_change(10)
    data["volatility_10d"]  = data["return_1d"].rolling(10).std()
    data["volume_change"]   = data["Volume"].pct_change()
    data["future_return_5d"]= data["Close"].shift(-5)/data["Close"] - 1
    data["target"]          = (data["future_return_5d"] > 0).astype(int)
    return data.dropna()

def trend_probability(df):
    if not SKLEARN_OK: return {"ok":False,"error":"scikit-learn not available"}
    data = build_features(df)
    if len(data) < 60: return {"ok":False,"error":"Not enough data (need 60+ rows)"}
    feat = ["return_1d","momentum_5d","momentum_10d","volatility_10d","volume_change"]
    X = data[feat].values; y = data["target"].values
    X_train,y_train = X[:-1],y[:-1]; X_live = X[-1].reshape(1,-1)
    sc = StandardScaler(); X_tr = sc.fit_transform(X_train); X_lv = sc.transform(X_live)
    mdl = LogisticRegression(max_iter=500); mdl.fit(X_tr,y_train)
    prob_up = mdl.predict_proba(X_lv)[0][1]
    return {"ok":True,"prob_up_5d":round(prob_up*100,1),"prob_down_5d":round((1-prob_up)*100,1),
            "train_accuracy_pct":round(mdl.score(X_tr,y_train)*100,1),"rows_used":len(data)}

def run_quant_engine(df, benchmark_df=None):
    try:
        if df is None or df.empty or len(df)<30: return {"ok":False,"error":"Not enough data"}
        vol   = calculate_volatility(df)
        beta  = calculate_beta(df,benchmark_df) if benchmark_df is not None and not benchmark_df.empty else None
        trend = trend_probability(df)
        return {"ok":True,"volatility":vol,"beta":beta,"trend":trend}
    except Exception as e:
        return {"ok":False,"error":str(e)}
