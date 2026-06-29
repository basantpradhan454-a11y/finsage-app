"""FinsageAI — Support & Resistance Engine"""
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from dataclasses import dataclass
from typing import List

@dataclass
class Level:
    price: float
    strength: int
    level_type: str
    label: str

class SupportResistanceEngine:
    def __init__(self, df: pd.DataFrame, sensitivity: int = 5, tolerance: float = 0.004):
        self.df          = df.copy()
        self.sensitivity = sensitivity
        self.tolerance   = tolerance
        self.curr_price  = float(df["Close"].iloc[-1])

    def _find_pivot_highs(self):
        highs = self.df["High"].values
        idx   = argrelextrema(highs, np.greater_equal, order=self.sensitivity)[0]
        return [float(highs[i]) for i in idx]

    def _find_pivot_lows(self):
        lows = self.df["Low"].values
        idx  = argrelextrema(lows, np.less_equal, order=self.sensitivity)[0]
        return [float(lows[i]) for i in idx]

    def _cluster(self, levels):
        if not levels: return []
        levels = sorted(levels)
        clusters, cluster = [], [levels[0]]
        for price in levels[1:]:
            if (price - cluster[-1]) / cluster[-1] <= self.tolerance:
                cluster.append(price)
            else:
                clusters.append({"price": round(float(np.mean(cluster)), 2), "strength": len(cluster)})
                cluster = [price]
        clusters.append({"price": round(float(np.mean(cluster)), 2), "strength": len(cluster)})
        return clusters

    def _count_touches(self, level, is_support):
        zone_hi = level * (1 + self.tolerance)
        zone_lo = level * (1 - self.tolerance)
        count = 0
        for _, row in self.df.iterrows():
            if is_support:
                if zone_lo <= row["Low"] <= zone_hi: count += 1
            else:
                if zone_lo <= row["High"] <= zone_hi: count += 1
        return count

    def get_levels(self, max_levels=5, price_range_pct=0.25):
        pivot_highs = self._find_pivot_highs()
        pivot_lows  = self._find_pivot_lows()
        resist_clusters  = self._cluster(pivot_highs)
        support_clusters = self._cluster(pivot_lows)
        price_min = self.curr_price * (1 - price_range_pct)
        price_max = self.curr_price * (1 + price_range_pct)
        resistance = sorted([c for c in resist_clusters if c["price"] > self.curr_price * 1.001 and c["price"] <= price_max], key=lambda x: x["price"])[:max_levels]
        support    = sorted([c for c in support_clusters if c["price"] < self.curr_price * 0.999 and c["price"] >= price_min], key=lambda x: x["price"], reverse=True)[:max_levels]
        for s in support:    s["touches"] = self._count_touches(s["price"], is_support=True)
        for r in resistance: r["touches"] = self._count_touches(r["price"], is_support=False)
        return {
            "current_price": self.curr_price,
            "support": support, "resistance": resistance,
            "nearest_support":    support[0]["price"]    if support    else None,
            "nearest_resistance": resistance[0]["price"] if resistance else None,
        }
