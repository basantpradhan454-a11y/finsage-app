"""FinsageAI — Candlestick Pattern Detector — 20+ patterns"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Pattern:
    name: str; signal: str; strength: str; index: int; timestamp: object

class CandlePatternDetector:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy(); self._precompute()

    def _precompute(self):
        df = self.df
        df["body"]        = abs(df["Close"] - df["Open"])
        df["body_pct"]    = df["body"] / (df["High"] - df["Low"]).replace(0, np.nan)
        df["upper_wick"]  = df["High"] - df[["Open","Close"]].max(axis=1)
        df["lower_wick"]  = df[["Open","Close"]].min(axis=1) - df["Low"]
        df["candle_range"]= df["High"] - df["Low"]
        df["bull"]        = df["Close"] >= df["Open"]
        df["avg_body"]    = df["body"].rolling(14).mean()

    def detect_all(self, lookback=5) -> List[Pattern]:
        patterns = []; df = self.df; n = len(df)
        for i in range(max(2, n-lookback), n):
            row = df.iloc[i]; prev = df.iloc[i-1]; prev2 = df.iloc[i-2] if i>=2 else prev; ts = df.index[i]
            if row["body"] <= row["candle_range"]*0.05:
                if row["upper_wick"] >= row["candle_range"]*0.6 and row["lower_wick"] <= row["candle_range"]*0.05:
                    patterns.append(Pattern("Gravestone Doji","BEARISH","STRONG",i,ts))
                elif row["lower_wick"] >= row["candle_range"]*0.6 and row["upper_wick"] <= row["candle_range"]*0.05:
                    patterns.append(Pattern("Dragonfly Doji","BULLISH","STRONG",i,ts))
                else:
                    patterns.append(Pattern("Doji","NEUTRAL","MODERATE",i,ts))
            elif row["lower_wick"]>=row["body"]*2 and row["upper_wick"]<=row["body"]*0.3 and not row["bull"]:
                patterns.append(Pattern("Hammer","BULLISH","STRONG",i,ts))
            elif row["upper_wick"]>=row["body"]*2 and row["lower_wick"]<=row["body"]*0.3 and not prev["bull"]:
                patterns.append(Pattern("Inverted Hammer","BULLISH","MODERATE",i,ts))
            elif row["upper_wick"]>=row["body"]*2 and row["lower_wick"]<=row["body"]*0.3 and row["bull"]:
                patterns.append(Pattern("Shooting Star","BEARISH","STRONG",i,ts))
            elif row["lower_wick"]>=row["body"]*2 and row["upper_wick"]<=row["body"]*0.3 and row["bull"]:
                patterns.append(Pattern("Hanging Man","BEARISH","MODERATE",i,ts))
            elif row["bull"] and row["upper_wick"]<=row["body"]*0.05 and row["lower_wick"]<=row["body"]*0.05 and row["body"]>=row.get("avg_body",row["body"])*1.5:
                patterns.append(Pattern("Bullish Marubozu","BULLISH","STRONG",i,ts))
            elif not row["bull"] and row["upper_wick"]<=row["body"]*0.05 and row["lower_wick"]<=row["body"]*0.05 and row["body"]>=row.get("avg_body",row["body"])*1.5:
                patterns.append(Pattern("Bearish Marubozu","BEARISH","STRONG",i,ts))
            elif row["body_pct"]<0.3 and row["upper_wick"]>row["body"] and row["lower_wick"]>row["body"]:
                patterns.append(Pattern("Spinning Top","NEUTRAL","WEAK",i,ts))
            if row["bull"] and not prev["bull"] and row["Open"]<=prev["Close"] and row["Close"]>=prev["Open"] and row["body"]>prev["body"]:
                patterns.append(Pattern("Bullish Engulfing","BULLISH","STRONG",i,ts))
            elif not row["bull"] and prev["bull"] and row["Open"]>=prev["Close"] and row["Close"]<=prev["Open"] and row["body"]>prev["body"]:
                patterns.append(Pattern("Bearish Engulfing","BEARISH","STRONG",i,ts))
            elif not prev["bull"] and row["bull"] and row["Open"]>prev["Close"] and row["Close"]<prev["Open"] and row["body"]<prev["body"]*0.6:
                patterns.append(Pattern("Bullish Harami","BULLISH","MODERATE",i,ts))
            elif prev["bull"] and not row["bull"] and row["Open"]<prev["Close"] and row["Close"]>prev["Open"] and row["body"]<prev["body"]*0.6:
                patterns.append(Pattern("Bearish Harami","BEARISH","MODERATE",i,ts))
            elif not prev["bull"] and row["bull"] and abs(row["Low"]-prev["Low"])/max(prev["Low"],0.0001)<0.002:
                patterns.append(Pattern("Tweezer Bottom","BULLISH","MODERATE",i,ts))
            elif prev["bull"] and not row["bull"] and abs(row["High"]-prev["High"])/max(prev["High"],0.0001)<0.002:
                patterns.append(Pattern("Tweezer Top","BEARISH","MODERATE",i,ts))
            if i>=2:
                if not prev2["bull"] and prev2["body"]>prev2.get("avg_body",prev2["body"])*0.8 and prev["body"]<prev2["body"]*0.3 and row["bull"] and row["Close"]>(prev2["Open"]+prev2["Close"])/2:
                    patterns.append(Pattern("Morning Star","BULLISH","STRONG",i,ts))
                elif prev2["bull"] and prev2["body"]>prev2.get("avg_body",prev2["body"])*0.8 and prev["body"]<prev2["body"]*0.3 and not row["bull"] and row["Close"]<(prev2["Open"]+prev2["Close"])/2:
                    patterns.append(Pattern("Evening Star","BEARISH","STRONG",i,ts))
                elif row["bull"] and prev["bull"] and prev2["bull"] and row["Close"]>prev["Close"]>prev2["Close"] and row["body"]>row.get("avg_body",row["body"])*0.7 and prev["body"]>prev.get("avg_body",prev["body"])*0.7:
                    patterns.append(Pattern("Three White Soldiers","BULLISH","STRONG",i,ts))
                elif not row["bull"] and not prev["bull"] and not prev2["bull"] and row["Close"]<prev["Close"]<prev2["Close"] and row["body"]>row.get("avg_body",row["body"])*0.7:
                    patterns.append(Pattern("Three Black Crows","BEARISH","STRONG",i,ts))
        return patterns

    def latest_pattern(self) -> Optional[Pattern]:
        patterns = self.detect_all(lookback=3)
        return patterns[-1] if patterns else None
