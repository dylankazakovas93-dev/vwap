"""Opening-displacement scale S(tau) — causal, per SPEC_DISCOVERY.md Sec. 2.

S(tau, s) = 1.4826 * median(|close(tau,s') - O(s')|) over the trailing 60
RTH sessions strictly before s, minimum 20 valid observations.
"""
import numpy as np
import pandas as pd

SCALE_TAU_MAX = 90    # SPEC_DISCOVERY Sec. 2: scale defined for tau in [0,90]
BAR_TAU_MAX = 450     # dense bar arrays cover the full RTH session (~390 min)
BASELINE_WINDOW = 60
BASELINE_MIN = 20


def build_opening_tables(df: pd.DataFrame, anchor_minute: int = 570):
    """df: base front-month bars for one instrument (has session_date,
    et_minute, open, high, low, close). Returns (O, S) both indexed by
    session_date, S columns = tau (0..SCALE_TAU_MAX), relative to
    `anchor_minute` (570 = 09:30 ET primary; 780 = 13:00 ET placebo)."""
    sub = df[(df["et_minute"] >= anchor_minute) & (df["et_minute"] <= anchor_minute + SCALE_TAU_MAX)]
    sub = sub[["session_date", "et_minute", "open", "close"]].copy()
    sub["tau"] = sub["et_minute"] - anchor_minute

    O = (sub.loc[sub["tau"] == 0, ["session_date", "open"]]
         .drop_duplicates("session_date").set_index("session_date")["open"])

    piv = sub.pivot_table(index="session_date", columns="tau", values="close")
    piv = piv.sort_index()
    O = O.reindex(piv.index)

    d = piv.sub(O, axis=0).abs()
    S = d.rolling(BASELINE_WINDOW, min_periods=BASELINE_MIN).median().shift(1) * 1.4826
    return O, S


def build_bar_frames(df: pd.DataFrame, tau_max: int = BAR_TAU_MAX, anchor_minute: int = 570):
    """Per-session OHLC arrays, DENSE on tau=0..tau_max (NaN where a minute
    is missing from the data), so array position == tau relative to
    `anchor_minute`. Keyed by session_date."""
    sub = df[(df["et_minute"] >= anchor_minute) & (df["et_minute"] <= anchor_minute + tau_max)].copy()
    sub["tau"] = sub["et_minute"] - anchor_minute
    n = tau_max + 1
    out = {}
    for sd, g in sub.groupby("session_date", sort=True):
        arrs = {k: np.full(n, np.nan) for k in ("open", "high", "low", "close")}
        ts = np.full(n, None, dtype=object)
        idx = g["tau"].to_numpy(int)
        for k in arrs:
            arrs[k][idx] = g[k].to_numpy(float)
        ts_vals = g["ts_event"].to_list()
        for pos, tv in zip(idx, ts_vals):
            ts[pos] = tv
        arrs["ts_event"] = ts
        out[sd] = arrs
    return out
