"""FinsageAI — Volume Profile Engine"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List

@dataclass
class VolumeProfileResult:
    poc: float; vah: float; val: float; vwap: float; profile: List[dict]; total_volume: float

class VolumeProfileEngine:
    def __init__(self, df: pd.DataFrame, bins: int = 40):
        self.df = df.copy(); self.bins = bins

    def calculate(self) -> VolumeProfileResult:
        price_min = float(self.df["Low"].min())
        price_max = float(self.df["High"].max())
        bin_edges  = np.linspace(price_min, price_max, self.bins + 1)
        bin_mids   = (bin_edges[:-1] + bin_edges[1:]) / 2
        vol_profile = np.zeros(self.bins)
        for _, row in self.df.iterrows():
            lo, hi, vol = row["Low"], row["High"], row["Volume"]
            if vol <= 0 or hi <= lo: continue
            candle_range = hi - lo
            for i in range(self.bins):
                overlap_lo = max(lo, bin_edges[i]); overlap_hi = min(hi, bin_edges[i+1])
                if overlap_hi > overlap_lo:
                    vol_profile[i] += vol * (overlap_hi - overlap_lo) / candle_range
        poc_idx = int(np.argmax(vol_profile)); poc = round(float(bin_mids[poc_idx]), 2)
        total_vol = float(vol_profile.sum()); target_vol = total_vol * 0.70
        sorted_idx = np.argsort(vol_profile)[::-1]; cum_vol = 0.0; va_prices = []
        for idx in sorted_idx:
            cum_vol += vol_profile[idx]; va_prices.append(float(bin_mids[idx]))
            if cum_vol >= target_vol: break
        vah = round(max(va_prices), 2) if va_prices else poc
        val = round(min(va_prices), 2) if va_prices else poc
        vwap = self._calculate_vwap()
        max_vol = float(vol_profile.max()) if vol_profile.max() > 0 else 1
        profile = [{"price": round(float(bin_mids[i]),2), "volume": round(float(vol_profile[i]),0),
                    "volume_pct": round(float(vol_profile[i])/max_vol*100,1),
                    "is_poc": bool(i==poc_idx), "in_value_area": bool(val <= bin_mids[i] <= vah)} for i in range(self.bins)]
        return VolumeProfileResult(poc=poc, vah=vah, val=val, vwap=round(vwap,2), profile=profile, total_volume=round(total_vol,0))

    def _calculate_vwap(self):
        df = self.df.copy(); df["typical"] = (df["High"]+df["Low"]+df["Close"])/3
        df["tpv"] = df["typical"]*df["Volume"]; total_vol = df["Volume"].sum()
        return float(df["Close"].iloc[-1]) if total_vol == 0 else float(df["tpv"].sum()/total_vol)
