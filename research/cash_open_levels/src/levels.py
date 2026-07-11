"""Cash-open level library engine — SPEC_LEVELS.md Revision 2.

Level construction only. No touch/reaction/return/outcome computation
anywhere in this module.
"""
import numpy as np
import pandas as pd

OPEN_MINUTE = 570   # 09:30 ET
RTH_END_MINUTE = 959  # 15:59 ET (last RTH minute before close, inclusive)
MIN_OVERNIGHT_BARS = 30

MULT_LADDER = (0.5, 1.0, 1.5, 2.0)
MAD_LADDER = (1.0, 1.5, 2.0)
VWAP_J = (-2, -1, 0, 1, 2)

DIST_BUCKETS = [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, np.inf)]
CLUSTER_THRESHOLD_FRAC = 0.1
SYNTHETIC_SEED = 20260711


def dist_bucket(nd: float):
    for lo, hi in DIST_BUCKETS:
        if lo <= nd < hi:
            return f"[{lo},{hi})"
    return None


# --------------------------------------------------------------- family 1 --
def build_family1(df: pd.DataFrame, scales: pd.DataFrame) -> pd.DataFrame:
    """scales: output of taxonomy.build_scale_tables(df) (generation 6,
    reused unmodified). Returns one row per session with the open and
    every family-1 level (multiplier + MAD), NaN where scale invalid."""
    opens = df[df["et_minute"] == OPEN_MINUTE][["session_date", "open"]].copy()
    opens = opens.drop_duplicates("session_date").set_index("session_date")
    idx = scales.index
    O = opens.reindex(idx)["open"]

    out = pd.DataFrame(index=idx)
    out["open"] = O
    out["scale_U"] = scales["scale_U"]
    out["scale_D"] = scales["scale_D"]
    out["scale_U_mad"] = scales["scale_U_mad"]
    out["scale_D_mad"] = scales["scale_D_mad"]

    for m in MULT_LADDER:
        out[f"mult_U_{m}"] = O + m * scales["scale_U"]
        out[f"mult_D_{m}"] = O - m * scales["scale_D"]
    for k in MAD_LADDER:
        out[f"mad_U_{k}"] = O + k * scales["scale_U_mad"]
        out[f"mad_D_{k}"] = O - k * scales["scale_D_mad"]
    return out


# ----------------------------------------------------------- overnight --
def _overnight_frame(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[df["et_minute"] < OPEN_MINUTE].sort_values("ts_event").copy()
    return sub


def build_family2(df: pd.DataFrame) -> pd.DataFrame:
    """Frozen overnight-VWAP deviation levels. Requires >=30 overnight bars
    for validity; sub-threshold sessions get NaN vwap/sigma/levels."""
    sub = _overnight_frame(df)
    sub["p"] = (sub["high"] + sub["low"] + sub["close"]) / 3.0
    g = sub.groupby("session_date", sort=True)
    n_bars = g.size()
    sum_v = g["volume"].sum()
    sum_vp = (sub["volume"] * sub["p"]).groupby(sub["session_date"]).sum()
    sum_vp2 = (sub["volume"] * sub["p"] ** 2).groupby(sub["session_date"]).sum()

    vwap = sum_vp / sum_v
    var = sum_vp2 / sum_v - vwap ** 2
    sigma = np.sqrt(var.clip(lower=0.0))

    valid = n_bars >= MIN_OVERNIGHT_BARS
    vwap = vwap.where(valid)
    sigma = sigma.where(valid)

    out = pd.DataFrame({"overnight_n_bars": n_bars, "vwap_on": vwap, "sigma_on": sigma})
    for j in VWAP_J:
        out[f"vwap_on_j{j:+d}"] = out["vwap_on"] + j * out["sigma_on"]
    return out


def build_family3(df: pd.DataFrame) -> pd.DataFrame:
    """Prior-session structural levels. A session's own RTH high/low/close
    plus an is_early_close flag; the PRIOR (chronologically immediately
    preceding) session's values are used for the current session's family-3
    levels, only if the prior session is not an early close."""
    rth = df[(df["et_minute"] >= OPEN_MINUTE) & (df["et_minute"] <= RTH_END_MINUTE)]
    g = rth.groupby("session_date", sort=True)
    rth_high = g["high"].max()
    rth_low = g["low"].min()
    max_minute = g["et_minute"].max()
    last_idx = rth.loc[rth.groupby("session_date")["et_minute"].idxmax()]
    rth_close = last_idx.set_index("session_date")["close"]

    sessions = pd.DataFrame({
        "rth_high": rth_high, "rth_low": rth_low, "rth_close": rth_close,
        "max_minute": max_minute,
    }).sort_index()
    sessions["is_early_close"] = sessions["max_minute"] < RTH_END_MINUTE

    prior_high = sessions["rth_high"].shift(1)
    prior_low = sessions["rth_low"].shift(1)
    prior_close = sessions["rth_close"].shift(1)
    prior_is_early = sessions["is_early_close"].shift(1).fillna(True).astype(bool)

    out = pd.DataFrame(index=sessions.index)
    out["prior_high"] = prior_high.where(~prior_is_early)
    out["prior_low"] = prior_low.where(~prior_is_early)
    out["prior_close"] = prior_close.where(~prior_is_early)
    out["prior_is_early_close"] = prior_is_early
    return out


def build_family4(df: pd.DataFrame, fam2: pd.DataFrame) -> pd.DataFrame:
    """Overnight structural levels, cross-referenced against family 2's
    VWAP_on. overnight_high/low only require >=1 overnight bar;
    VWAP-deviation fields require family 2 to be valid."""
    sub = _overnight_frame(df)
    g = sub.groupby("session_date", sort=True)
    overnight_high = g["high"].max()
    overnight_low = g["low"].min()

    out = pd.DataFrame({"overnight_high": overnight_high, "overnight_low": overnight_low})
    out = out.reindex(fam2.index.union(out.index)).sort_index()
    vwap_valid = fam2["vwap_on"].notna()
    out["overnight_high_dev_vwap"] = (out["overnight_high"] - fam2["vwap_on"]).where(vwap_valid)
    out["overnight_low_dev_vwap"] = (fam2["vwap_on"] - out["overnight_low"]).where(vwap_valid)
    return out


# -------------------------------------------------------- long-format --
LEVEL_COLUMNS = {
    # level_id -> (family, side, scale_col)
    **{f"mult_U_{m}": ("family1", "up", "scale_U") for m in MULT_LADDER},
    **{f"mult_D_{m}": ("family1", "down", "scale_D") for m in MULT_LADDER},
    **{f"mad_U_{k}": ("family1", "up", "scale_U") for k in MAD_LADDER},
    **{f"mad_D_{k}": ("family1", "down", "scale_D") for k in MAD_LADDER},
    **{f"vwap_on_j{j:+d}": ("family2", "up" if j > 0 else ("down" if j < 0 else "neutral"), None)
       for j in VWAP_J},
    "prior_high": ("family3", "up", None),
    "prior_low": ("family3", "down", None),
    "prior_close": ("family3", "neutral", None),
    "overnight_high": ("family4", "up", None),
    "overnight_low": ("family4", "down", None),
}

HORIZON_EXPOSURE = {"family1": "INTRADAY_ROLLING", "family2": "PRE_OPEN",
                    "family3": "PRIOR_SESSION", "family4": "PRE_OPEN"}


def build_long_levels(instrument: str, fam1: pd.DataFrame, fam2: pd.DataFrame,
                      fam3: pd.DataFrame, fam4: pd.DataFrame) -> pd.DataFrame:
    """One row per (session_date, level_id): value, family, side,
    normalized distance from open, distance bucket, horizon-exposure
    category. Missing (NaN value) rows are still emitted with value=NaN
    so missingness can be counted per level_id."""
    all_idx = fam1.index.union(fam2.index).union(fam3.index).union(fam4.index).sort_values()
    O = fam1["open"].reindex(all_idx)
    scale_U = fam1["scale_U"].reindex(all_idx)
    scale_D = fam1["scale_D"].reindex(all_idx)

    frames = {"family1": fam1, "family2": fam2, "family3": fam3, "family4": fam4}
    rows = []
    for level_id, (family, side, _scale_col) in LEVEL_COLUMNS.items():
        src = frames[family].reindex(all_idx)
        if level_id not in src.columns:
            continue
        value = src[level_id]
        scale_side = scale_U if side == "up" else (scale_D if side == "down" else (scale_U + scale_D) / 2.0)
        nd = (value - O).abs() / scale_side
        d = pd.DataFrame({
            "session_date": all_idx, "level_id": level_id, "family": family,
            "side": side, "value": value.to_numpy(),
            "normalized_distance": nd.to_numpy(),
        })
        d["horizon_exposure"] = HORIZON_EXPOSURE[family]
        d["distance_bucket"] = d["normalized_distance"].apply(
            lambda x: dist_bucket(x) if np.isfinite(x) else None)
        rows.append(d)
    long_df = pd.concat(rows, ignore_index=True)
    long_df.insert(0, "instrument", instrument)
    return long_df


# ------------------------------------------------------- synthetic control --
def build_synthetic_controls(long_df: pd.DataFrame, fam1: pd.DataFrame,
                             seed: int = SYNTHETIC_SEED) -> pd.DataFrame:
    """One synthetic control per real-level row, matched on instrument,
    side, horizon_exposure, distance_bucket; the synthetic normalized
    distance is drawn uniformly within the matched bucket's own interval
    (fixed seed, reproducible) and priced via that session's OWN open and
    scale (already causally known at 09:30) -- never via any other real
    level's value or any other session's price."""
    rng = np.random.default_rng(seed)
    bucket_bounds = {f"[{lo},{hi})": (lo, hi) for lo, hi in DIST_BUCKETS}

    out = long_df[["instrument", "session_date", "level_id", "family", "side",
                   "horizon_exposure", "distance_bucket"]].copy()
    nd_synth = np.full(len(out), np.nan)
    valid = out["distance_bucket"].notna()
    for bucket, (lo, hi) in bucket_bounds.items():
        mask = valid & (out["distance_bucket"] == bucket)
        n = int(mask.sum())
        if n == 0:
            continue
        hi_draw = hi if np.isfinite(hi) else lo + 1.0
        nd_synth[mask.to_numpy()] = rng.uniform(lo, hi_draw, size=n)
    out["normalized_distance_synth"] = nd_synth

    O = fam1["open"].reindex(long_df["session_date"]).to_numpy()
    scale_U = fam1["scale_U"].reindex(long_df["session_date"]).to_numpy()
    scale_D = fam1["scale_D"].reindex(long_df["session_date"]).to_numpy()
    side = out["side"].to_numpy()
    scale_side = np.where(side == "up", scale_U, np.where(side == "down", scale_D, (scale_U + scale_D) / 2.0))
    sign = np.where(side == "down", -1.0, 1.0)
    out["value_synth"] = O + sign * out["normalized_distance_synth"].to_numpy() * scale_side
    return out
