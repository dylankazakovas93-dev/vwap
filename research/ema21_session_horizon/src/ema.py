"""EMA21 (only) computation, causal level freezing, causal ATR20.

LEVEL_t = EMA computed through the close of bar t-1. Warm-up: 60
completed bars minimum, evaluated on the full continuous sequence (never
reset per session leg -- see DECISIONS.md #5).
"""
import numpy as np
import pandas as pd

SPAN = 21
WARMUP = 60


def add_ema_and_level(bars: pd.DataFrame) -> pd.DataFrame:
    out = bars.copy()
    ema = out["close"].ewm(span=SPAN, adjust=False).mean()
    level = ema.shift(1)
    valid = np.arange(len(out)) >= WARMUP
    level = level.where(valid, np.nan)
    out["ema21"] = ema
    out["level21"] = level
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
