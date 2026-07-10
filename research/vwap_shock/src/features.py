"""Causal feature engine (Stage 2). All features are as-of the close of bar t.

Windows never cross session boundaries (features are computed within
session groups; the front-month contract is constant within a session by
construction). Minute-of-day baselines use the trailing 60 sessions strictly
before the bar's session (min 20).
"""
import numpy as np
import pandas as pd

LOOKBACKS = (5, 15, 60)
ATR_N = 30
BASELINE_WINDOW = 60
BASELINE_MIN = 20

SEGMENTS = [
    (18 * 60, 24 * 60, "overnight"), (0, 3 * 60, "overnight"),
    (3 * 60, 8 * 60 + 30, "european"), (8 * 60 + 30, 9 * 60 + 30, "precash"),
    (9 * 60 + 30, 10 * 60, "cashopen"), (10 * 60, 11 * 60 + 30, "morning"),
    (11 * 60 + 30, 14 * 60, "midday"), (14 * 60, 15 * 60 + 30, "afternoon"),
    (15 * 60 + 30, 17 * 60, "close"),
]
MACRO_MINUTES = set()
for h, m in ((8, 30), (9, 45), (10, 0), (14, 0)):
    for off in range(3):
        MACRO_MINUTES.add(h * 60 + m + off)


def segment_of(et_minute: np.ndarray) -> np.ndarray:
    out = np.empty(len(et_minute), dtype=object)
    for lo, hi, name in SEGMENTS:
        mask = (et_minute >= lo) & (et_minute < hi)
        out[mask] = name
    return out


def _rolling_median_by_minute(df, col, out_col):
    """Trailing-60-prior-session median of `col` per et_minute, strictly
    excluding the current session. Also MAD when out_col ends with tuple."""
    return _rolling_robust_by_minute(df, col, out_col, want_mad=False)


def _rolling_robust_by_minute(df, col, med_col, mad_col=None, want_mad=True):
    med = np.full(len(df), np.nan)
    mad = np.full(len(df), np.nan) if want_mad else None
    # iterate minute-of-day groups; rows within a group are session-ordered
    sess_key = df["session_date"].to_numpy()
    for _, idx in df.groupby("et_minute", sort=False).indices.items():
        idx = idx[np.argsort(sess_key[idx], kind="stable")]
        vals = df[col].to_numpy()[idx]
        n = len(vals)
        if n < BASELINE_MIN + 1:
            continue
        sw = np.lib.stride_tricks.sliding_window_view  # noqa
        # expanding-then-rolling: for row j, window = vals[max(0, j-60):j]
        m = np.full(n, np.nan)
        md = np.full(n, np.nan) if want_mad else None
        # full 60-windows vectorized
        if n > BASELINE_WINDOW:
            w = sw(vals, BASELINE_WINDOW)  # rows 0..n-60 cover vals[j:j+60]
            wmed = np.nanmedian(w, axis=1)
            m[BASELINE_WINDOW:] = wmed[: n - BASELINE_WINDOW]
            if want_mad:
                md_full = np.nanmedian(np.abs(w - wmed[:, None]), axis=1)
                md[BASELINE_WINDOW:] = md_full[: n - BASELINE_WINDOW]
        # partial windows (>= BASELINE_MIN prior rows)
        hi = min(BASELINE_WINDOW, n)
        for j in range(BASELINE_MIN, hi):
            wv = vals[:j]
            mj = np.nanmedian(wv)
            m[j] = mj
            if want_mad:
                md[j] = np.nanmedian(np.abs(wv - mj))
        med[idx] = m
        if want_mad:
            mad[idx] = md
    df[med_col] = med
    if want_mad and mad_col:
        df[mad_col] = mad
    return df


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """df: front-month bars (one instrument), sorted by ts_event."""
    df = df.sort_values("ts_event").reset_index(drop=True).copy()
    g = df.groupby("session_date", sort=False)

    c, h, l, o, v = (df[x] for x in ("close", "high", "low", "open", "volume"))
    df["r"] = g["close"].diff()

    # shocks
    df["s1"] = df["r"]
    df["s3"] = c - g["close"].shift(3)
    df["abs_s1"] = df["s1"].abs()
    df["abs_s3"] = df["s3"].abs()

    # ATR30 as of t-1
    prev_c = g["close"].shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    tr[prev_c.isna()] = np.nan
    df["atr30"] = tr.groupby(df["session_date"], sort=False).rolling(ATR_N).mean().reset_index(level=0, drop=True).groupby(df["session_date"], sort=False).shift(1)

    # minute-of-day robust baselines (strictly prior sessions)
    df = _rolling_robust_by_minute(df, "abs_s1", "mod_s1_med", want_mad=False)
    df = _rolling_robust_by_minute(df, "abs_s3", "mod_s3_med", want_mad=False)
    df = _rolling_robust_by_minute(df, "volume", "mod_vol_med", "mod_vol_mad", want_mad=True)
    df["sigma_mod1"] = 1.4826 * df["mod_s1_med"]
    df["sigma_mod3"] = 1.4826 * df["mod_s3_med"]
    df["z_mod1"] = df["s1"] / df["sigma_mod1"]
    df["z_mod3"] = df["s3"] / df["sigma_mod3"]
    df["z_atr1"] = df["s1"] / df["atr30"]
    df["z_atr3"] = df["s3"] / df["atr30"]
    mad = df["mod_vol_mad"].where(df["mod_vol_mad"] > 0)
    df["z_vol"] = (v - df["mod_vol_med"]) / (1.4826 * mad)
    df["vol_ratio"] = v / df["mod_vol_med"].where(df["mod_vol_med"] > 0)

    # lookback families (windows end at t-1)
    absr = df["r"].abs()
    pos = (df["r"] > 0).astype(float)
    neg = (df["r"] < 0).astype(float)
    sd = df["session_date"]
    for L in LOOKBACKS:
        d = g["close"].shift(1) - g["close"].shift(1 + L)
        suma = absr.groupby(sd, sort=False).rolling(L).sum().reset_index(level=0, drop=True).groupby(sd, sort=False).shift(1)
        npos = pos.groupby(sd, sort=False).rolling(L).sum().reset_index(level=0, drop=True).groupby(sd, sort=False).shift(1)
        nneg = neg.groupby(sd, sort=False).rolling(L).sum().reset_index(level=0, drop=True).groupby(sd, sort=False).shift(1)
        df[f"D{L}"] = d
        df[f"D{L}_atr"] = d / df["atr30"]
        df[f"E{L}"] = (d.abs() / suma.where(suma > 0))
        df[f"P{L}"] = np.where(d > 0, npos / L, np.where(d < 0, nneg / L, np.nan))
        df[f"npos{L}"] = npos
        df[f"nneg{L}"] = nneg

    # terminal run length (of r, ending at t-1), signed by run direction
    s = np.sign(df["r"].fillna(0)).astype(int)
    new_run = (s != s.shift(1)) | (s == 0) | sd.ne(sd.shift(1))
    run_id = new_run.cumsum()
    runlen = df.groupby(run_id).cumcount() + 1
    runlen[s == 0] = 0
    df["runlen_prev"] = runlen.groupby(sd, sort=False).shift(1)
    df["runsign_prev"] = pd.Series(s, index=df.index).groupby(sd, sort=False).shift(1)

    # candle geometry k=1
    rng1 = (h - l).where((h - l) > 0)
    df["body_eff1"] = (c - o).abs() / rng1
    df["closeloc_up1"] = (c - l) / rng1  # fold by direction at event time
    # k=3 composite
    o3 = g["open"].shift(2)
    h3 = h.groupby(sd, sort=False).rolling(3).max().reset_index(level=0, drop=True)
    l3 = l.groupby(sd, sort=False).rolling(3).min().reset_index(level=0, drop=True)
    rng3 = (h3 - l3).where((h3 - l3) > 0)
    df["body_eff3"] = (c - o3).abs() / rng3
    df["closeloc_up3"] = (c - l3) / rng3

    # VWAP (Globex anchor = session start)
    pbar = (h + l + c) / 3.0
    pv = pbar * v
    pv2 = pbar * pbar * v
    cv = v.groupby(sd, sort=False).cumsum()
    df["vwap_g"] = pv.groupby(sd, sort=False).cumsum() / cv
    ex2 = pv2.groupby(sd, sort=False).cumsum() / cv
    var = (ex2 - df["vwap_g"] ** 2).clip(lower=0)
    df["sig_g"] = np.sqrt(var)
    df["nbar_g"] = g.cumcount()
    df["vwap_g_valid"] = (df["nbar_g"] >= 30) & (df["sig_g"] > 0)
    df["dev_g"] = (c - df["vwap_g"]) / df["sig_g"].where(df["vwap_g_valid"])
    df["vwap_g_slope10"] = (df["vwap_g"] - df["vwap_g"].groupby(sd, sort=False).shift(10)) / 10 / df["atr30"]

    # RTH VWAP (anchor 09:30 ET)
    rth = (df["et_minute"] >= 570) & (df["et_minute"] < 1020)
    pv_r = pv.where(rth, 0.0)
    pv2_r = pv2.where(rth, 0.0)
    v_r = v.where(rth, 0)
    cvr = v_r.groupby(sd, sort=False).cumsum().where(rth)
    df["vwap_r"] = pv_r.groupby(sd, sort=False).cumsum() / cvr
    ex2r = pv2_r.groupby(sd, sort=False).cumsum() / cvr
    df["sig_r"] = np.sqrt((ex2r - df["vwap_r"] ** 2).clip(lower=0))
    nbar_r = rth.groupby(sd, sort=False).cumsum().where(rth)
    df["vwap_r_valid"] = rth & (nbar_r >= 31) & (df["sig_r"] > 0)  # 30 completed bars + current
    df["dev_r"] = (c - df["vwap_r"]) / df["sig_r"].where(df["vwap_r_valid"])

    df["segment"] = segment_of(df["et_minute"].to_numpy())
    df["macro_window"] = df["et_minute"].isin(MACRO_MINUTES)
    return df
