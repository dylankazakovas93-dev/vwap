"""EMA20/21/22 computation and causal level freezing.

LEVEL_t = EMA computed through the close of bar t-1 (never bar t's own
close). Warm-up: a bar is eligible only once at least WARMUP completed
bars precede it (see DECISIONS.md #4).
"""
import numpy as np
import pandas as pd

SPANS = (20, 21, 22)
WARMUP = 60


def add_emas_and_levels(bars: pd.DataFrame) -> pd.DataFrame:
    """bars must be sorted chronologically, one row per completed 5m bar."""
    out = bars.copy()
    for span in SPANS:
        ema = out["close"].ewm(span=span, adjust=False).mean()
        level = ema.shift(1)
        # warm-up: LEVEL_t valid only if bar t-1 index >= WARMUP-1 (i.e. t >= WARMUP)
        valid = np.arange(len(out)) >= WARMUP
        level = level.where(valid, np.nan)
        out[f"ema{span}"] = ema
        out[f"level{span}"] = level
    return out


def add_atr(bars: pd.DataFrame) -> pd.DataFrame:
    out = bars.copy()
    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - prev_close).abs(),
            (out["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    tr = tr.where(prev_close.notna(), np.nan)
    atr20_asof = tr.rolling(20).mean()
    atr_event = atr20_asof.shift(1)
    out["tr"] = tr
    out["atr20_asof"] = atr20_asof
    out["atr_event"] = atr_event
    return out
