"""Outcome measures from a legal outcome-start position — SPEC_DISCOVERY.md
Sec. 7. All operate on dense per-session bar arrays (position == tau).
"""
import numpy as np

FIXED_HORIZONS = (1, 3, 5, 10, 15, 30, 60)
SYM_BARRIER_FRACS_M = (0.25, 0.50)  # of initial excursion magnitude M
FP_WINDOW = 120


def fixed_horizon_returns(bars, origin_tau, direction, anchor_minute=570):
    """direction: +1 (long / lower-excursion convention) or -1 (short)."""
    n = len(bars["close"])
    out = {}
    if origin_tau >= n or not np.isfinite(bars["open"][origin_tau]):
        return {f"fret_{h}": np.nan for h in FIXED_HORIZONS} | {"origin_open": np.nan}
    entry = bars["open"][origin_tau]
    out["origin_open"] = entry
    rth_close_tau = 960 - anchor_minute  # 16:00 ET in tau units
    for h in FIXED_HORIZONS:
        j = origin_tau + h
        if h == 60 and j > rth_close_tau:
            # 60-min window would run past 16:00 ET RTH close; skip (non-saturating rule)
            out[f"fret_{h}"] = np.nan
            continue
        out[f"fret_{h}"] = (bars["close"][j] - entry) * direction if j < n and np.isfinite(bars["close"][j]) else np.nan
    return out


def symmetric_first_passage(bars, origin_tau, direction, M, S):
    """Barriers at +-f*M (f in SYM_BARRIER_FRACS_M) and +-1.0*S (scale-based).
    Positive barrier = reclaim direction. Returns dict of {label: (outcome, bars_to_outcome)}."""
    n = len(bars["close"])
    res = {}
    if origin_tau + 1 >= n or not np.isfinite(bars["open"][origin_tau]):
        for label in list(SYM_BARRIER_FRACS_M) + ["S"]:
            res[f"fp_{label}"] = ("INVALID", np.nan)
        return res
    entry = bars["open"][origin_tau]
    hi, lo = bars["high"], bars["low"]
    barriers = [(f, f * M) for f in SYM_BARRIER_FRACS_M] + [("S", 1.0 * S)]
    for label, x in barriers:
        if not np.isfinite(x) or x <= 0:
            res[f"fp_{label}"] = ("INVALID", np.nan)
            continue
        up = entry + direction * x   # favourable barrier (reclaim direction)
        dn = entry - direction * x   # adverse barrier
        outcome, tb = "NONE", np.nan
        j_end = min(n - 1, origin_tau + FP_WINDOW)
        for j in range(origin_tau + 1, j_end + 1):
            if not np.isfinite(hi[j]):
                continue
            hit_fav = (hi[j] >= up) if direction > 0 else (lo[j] <= up)
            hit_adv = (lo[j] <= dn) if direction > 0 else (hi[j] >= dn)
            if hit_fav and hit_adv:
                outcome, tb = "AMBIG", j - origin_tau
                break
            if hit_fav:
                outcome, tb = "CONT", j - origin_tau
                break
            if hit_adv:
                outcome, tb = "REV", j - origin_tau
                break
        res[f"fp_{label}"] = (outcome, tb)
    return res


def structural_outcomes(bars, origin_tau, direction, O, A, S, outer_price,
                        overnight_hi, overnight_lo):
    n = len(bars["close"])
    out = {}
    j_end = min(n - 1, origin_tau + FP_WINDOW)
    cl, hi, lo = bars["close"], bars["high"], bars["low"]

    opp_thr = (O - A * S) if direction > 0 else (O + A * S)
    t = np.nan
    for j in range(origin_tau, j_end + 1):
        if direction > 0 and np.isfinite(lo[j]) and lo[j] <= opp_thr:
            t = j - origin_tau; break
        if direction < 0 and np.isfinite(hi[j]) and hi[j] >= opp_thr:
            t = j - origin_tau; break
    out["t_opposite_threshold"] = t

    t = np.nan
    for j in range(origin_tau, j_end + 1):
        if direction > 0 and np.isfinite(lo[j]) and lo[j] <= outer_price:
            t = j - origin_tau; break
        if direction < 0 and np.isfinite(hi[j]) and hi[j] >= outer_price:
            t = j - origin_tau; break
    out["t_rebreak_original_extreme"] = t

    if np.isfinite(overnight_hi) and np.isfinite(overnight_lo):
        t = np.nan
        for j in range(origin_tau, j_end + 1):
            if np.isfinite(cl[j]) and overnight_lo <= cl[j] <= overnight_hi:
                t = j - origin_tau; break
        out["t_return_inside_overnight_range"] = t
    else:
        out["t_return_inside_overnight_range"] = np.nan
    return out
