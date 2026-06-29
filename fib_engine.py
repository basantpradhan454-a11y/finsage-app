"""FinsageAI — Fibonacci Retracement Engine"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict
from scipy.signal import argrelextrema

@dataclass
class FibResult:
    swing_high: float; swing_low: float; trend: str; levels: Dict[str,float]; extensions: Dict[str,float]

class FibonacciEngine:
    RETRACEMENT_LEVELS = {"0.0":0.0,"0.236":0.236,"0.382":0.382,"0.5":0.5,"0.618":0.618,"0.786":0.786,"1.0":1.0}
    EXTENSION_LEVELS   = {"1.272":1.272,"1.414":1.414,"1.618":1.618,"2.0":2.0,"2.618":2.618}

    def __init__(self, df: pd.DataFrame, lookback: int = 60):
        self.df = df.tail(lookback).copy(); self.lookback = lookback

    def _detect_swing(self, order=5):
        highs = self.df["High"].values; lows = self.df["Low"].values
        peak_idx   = argrelextrema(highs, np.greater, order=order)[0]
        trough_idx = argrelextrema(lows,  np.less,    order=order)[0]
        swing_high = float(highs[peak_idx].max())  if len(peak_idx)   > 0 else float(highs.max())
        swing_low  = float(lows[trough_idx].min()) if len(trough_idx) > 0 else float(lows.min())
        last_peak_i   = peak_idx[-1]   if len(peak_idx)   > 0 else 0
        last_trough_i = trough_idx[-1] if len(trough_idx) > 0 else 0
        trend = "UP" if last_peak_i > last_trough_i else "DOWN"
        return swing_high, swing_low, trend

    def calculate(self) -> FibResult:
        swing_high, swing_low, trend = self._detect_swing()
        diff = swing_high - swing_low
        if trend == "UP":
            levels     = {k: round(swing_high - diff*v, 2) for k,v in self.RETRACEMENT_LEVELS.items()}
            extensions = {k: round(swing_high + diff*(v-1.0), 2) for k,v in self.EXTENSION_LEVELS.items()}
        else:
            levels     = {k: round(swing_low + diff*v, 2) for k,v in self.RETRACEMENT_LEVELS.items()}
            extensions = {k: round(swing_low - diff*(v-1.0), 2) for k,v in self.EXTENSION_LEVELS.items()}
        return FibResult(swing_high=round(swing_high,2), swing_low=round(swing_low,2), trend=trend, levels=levels, extensions=extensions)

    def get_nearest_levels(self, current_price, n=3):
        result = self.calculate(); all_levels = list(result.levels.items())
        above = sorted([(k,v) for k,v in all_levels if v > current_price], key=lambda x:x[1])[:n]
        below = sorted([(k,v) for k,v in all_levels if v < current_price], key=lambda x:x[1], reverse=True)[:n]
        return {"fib_result": result, "above_price": above, "below_price": below}
