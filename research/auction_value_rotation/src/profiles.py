"""Deterministic volume-profile construction (3 models x bin width x VA%).
See SPEC_AUCTION_VALUE.md section 1.
"""
import numpy as np
import pandas as pd

MODELS = ("UNIFORM_RANGE", "TYPICAL_PRICE_ROW", "CLOSE_PRICE_ROW")
BIN_WIDTHS = (0.25, 0.50, 1.00)
VA_PCTS = (0.68, 0.70, 0.72)
PRIMARY = {"model": "UNIFORM_RANGE", "bin_width": 0.25, "va_pct": 0.70}


def build_profile(bars: pd.DataFrame, model: str = "UNIFORM_RANGE",
                   bin_width: float = 0.25, va_pct: float = 0.70) -> dict:
    lows = bars["low"].to_numpy(dtype=float)
    highs = bars["high"].to_numpy(dtype=float)
    closes = bars["close"].to_numpy(dtype=float)
    vols = bars["volume"].to_numpy(dtype=float)
    session_low, session_high = lows.min(), highs.max()

    origin = np.floor(session_low / bin_width) * bin_width
    n_bins = int(round((session_high - origin) / bin_width)) + 1
    bin_edges = origin + np.arange(n_bins + 1) * bin_width
    vol_per_bin = np.zeros(n_bins)

    lo_bin = np.clip(np.floor((lows - origin) / bin_width).astype(int), 0, n_bins - 1)
    hi_bin = np.clip(np.floor((highs - origin) / bin_width).astype(int), 0, n_bins - 1)

    if model == "UNIFORM_RANGE":
        for i in range(len(bars)):
            a, b = lo_bin[i], hi_bin[i]
            k = b - a + 1
            vol_per_bin[a : b + 1] += vols[i] / k
    elif model == "TYPICAL_PRICE_ROW":
        tp = (highs + lows + closes) / 3.0
        idx = np.clip(np.floor((tp - origin) / bin_width).astype(int), 0, n_bins - 1)
        np.add.at(vol_per_bin, idx, vols)
    elif model == "CLOSE_PRICE_ROW":
        idx = np.clip(np.floor((closes - origin) / bin_width).astype(int), 0, n_bins - 1)
        np.add.at(vol_per_bin, idx, vols)
    else:
        raise ValueError(f"unknown profile model {model}")

    total = float(vol_per_bin.sum())
    max_vol = vol_per_bin.max()
    poc_candidates = np.where(np.isclose(vol_per_bin, max_vol))[0]
    poc_idx = int(poc_candidates.min())  # tie-break: lowest-priced bin

    lo, hi = poc_idx, poc_idx
    included = vol_per_bin[poc_idx]
    target = va_pct * total
    while included < target and (lo > 0 or hi < n_bins - 1):
        vol_below = vol_per_bin[lo - 1] if lo > 0 else -1.0
        vol_above = vol_per_bin[hi + 1] if hi < n_bins - 1 else -1.0
        if vol_above >= vol_below:  # tie-break: prefer upper bin
            hi += 1
            included += vol_per_bin[hi]
        else:
            lo -= 1
            included += vol_per_bin[lo]

    val = float(bin_edges[lo])
    vah = float(bin_edges[hi + 1])
    poc = float((bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2.0)

    return {
        "poc": poc, "vah": vah, "val": val, "va_width": vah - val,
        "total_volume": total, "n_bins": n_bins, "bin_width": bin_width,
        "model": model, "va_pct": va_pct,
        "session_low": float(session_low), "session_high": float(session_high),
    }
