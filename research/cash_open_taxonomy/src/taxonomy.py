"""Cash-open path taxonomy engine — SPEC_TAXONOMY.md Revision 3.

Self-contained (only reuses generation 3's `build_dense_bars` for bar
arrays, via file-path import in build_ledger.py). All path variables,
same-bar proxy logic, ordinary taxonomy, and the excursion ladder are
defined independently here.
"""
import numpy as np
import pandas as pd

TAU_MAX = 59            # 09:30-10:29 ET, matches atlas secondary ceiling
BASELINE_WINDOW = 60    # exactly the previous 60 valid sessions; no expanding-window fallback
TAU_C = 1.0              # primary commitment threshold
TAU_D = 0.0               # dominance threshold
TAU_B = 0.15              # primary ambiguity band
TAU_C_GRID = (0.75, 1.0, 1.5)
TAU_B_GRID = (0.10, 0.15, 0.25)
LADDER = (0.5, 1.0, 1.5, 2.0)
N_INITIAL_BALANCE = 15   # minutes, class 6 cutoff
HORIZONS_PRIMARY = (1, 3, 5, 10, 15, 30)
HORIZON_SECONDARY = 60
CAVEAT = ("One-minute OHLCV does not establish the true intrabar order. "
         "Same-bar bullish and bearish reversal labels are morphology-based "
         "proxies determined by dual-sided excursion and closing side.")

TIMING_BINS = [(2, 3, "minutes_2_3"), (4, 5, "minutes_4_5"),
              (6, 10, "minutes_6_10"), (11, 15, "minutes_11_15"),
              (16, np.inf, "later_than_15")]


def timing_bin(h):
    for lo, hi, lab in TIMING_BINS:
        if lo <= h <= hi:
            return lab
    return None


# ---------------------------------------------------------------- scales --
def build_scale_tables(df: pd.DataFrame):
    """df: base bars for one instrument. Returns per-session scale_U,
    scale_D (causal, EXACTLY the previous 60 valid sessions -- no
    expanding-window / partial-window fallback; a session with fewer than
    60 valid predecessors has an undefined scale), plus the raw
    U_0930/D_0930 series."""
    sub = df[df["et_minute"] == 570][["session_date", "open", "high", "low"]].copy()
    sub = sub.drop_duplicates("session_date").sort_values("session_date").reset_index(drop=True)
    sub["U_0930"] = sub["high"] - sub["open"]
    sub["D_0930"] = sub["open"] - sub["low"]
    sub["scale_U"] = sub["U_0930"].rolling(BASELINE_WINDOW, min_periods=BASELINE_WINDOW).median().shift(1)
    sub["scale_D"] = sub["D_0930"].rolling(BASELINE_WINDOW, min_periods=BASELINE_WINDOW).median().shift(1)
    sub["scale_U_mad"] = sub["U_0930"].rolling(BASELINE_WINDOW, min_periods=BASELINE_WINDOW).apply(
        lambda x: 1.4826 * np.median(np.abs(x - np.median(x))), raw=True).shift(1)
    sub["scale_D_mad"] = sub["D_0930"].rolling(BASELINE_WINDOW, min_periods=BASELINE_WINDOW).apply(
        lambda x: 1.4826 * np.median(np.abs(x - np.median(x))), raw=True).shift(1)
    return sub.set_index("session_date")[["scale_U", "scale_D", "scale_U_mad", "scale_D_mad", "U_0930", "D_0930"]]


# ------------------------------------------------------------ primitives --
def path_arrays(arrs, O, scale_U, scale_D):
    """u(t), d(t), Q(t), close_disp(t) for t=0..len-1. A bar's value is
    undefined (NaN) once any bar 0..t is missing (matches the project's
    "incomplete window -> undefined, never imputed" convention) or the
    scale is invalid."""
    n = len(arrs["close"])
    hi, lo, cl = arrs["high"], arrs["low"], arrs["close"]
    any_missing = np.isnan(hi) | np.isnan(lo)
    complete_so_far = ~np.maximum.accumulate(any_missing.astype(int)).astype(bool)
    running_high = np.fmax.accumulate(np.where(np.isnan(hi), -np.inf, hi))
    running_low = np.fmin.accumulate(np.where(np.isnan(lo), np.inf, lo))
    if scale_U and scale_U > 0:
        u = np.where(complete_so_far, (running_high - O) / scale_U, np.nan)
    else:
        u = np.full(n, np.nan)
    if scale_D and scale_D > 0:
        d = np.where(complete_so_far, (O - running_low) / scale_D, np.nan)
    else:
        d = np.full(n, np.nan)
    denom = u + d
    with np.errstate(invalid="ignore", divide="ignore"):
        Q = np.where(denom > 0, (u - d) / denom, np.nan)
    close_disp = np.where(np.isnan(cl), np.nan, cl - O)
    return u, d, Q, close_disp


def bar0_morphology(arrs, O, scale_U, scale_D):
    O0, H0, L0, C0 = arrs["open"][0], arrs["high"][0], arrs["low"][0], arrs["close"][0]
    rng = H0 - L0
    row = {"close_disp_0": C0 - O0}
    if rng > 0:
        row["close_location_0"] = 2 * (C0 - L0) / rng - 1
        row["body_ratio_0"] = abs(C0 - O0) / rng
        row["upper_wick_ratio_0"] = (H0 - max(O0, C0)) / rng
        row["lower_wick_ratio_0"] = (min(O0, C0) - L0) / rng
    else:
        row["close_location_0"] = row["body_ratio_0"] = np.nan
        row["upper_wick_ratio_0"] = row["lower_wick_ratio_0"] = np.nan
    cd = row["close_disp_0"]
    if cd > 0 and scale_U and scale_U > 0:
        row["norm_close_disp_0"] = cd / scale_U
    elif cd < 0 and scale_D and scale_D > 0:
        row["norm_close_disp_0"] = cd / scale_D
    else:
        row["norm_close_disp_0"] = 0.0
    return row


# ---------------------------------------------------------- same-bar family
def classify_samebar_h1(u0, d0, norm_close_disp_0, tau_c=TAU_C, tau_b=TAU_B):
    if not (np.isfinite(u0) and np.isfinite(d0)):
        return None
    dual = (u0 >= tau_c) and (d0 >= tau_c)
    if not dual:
        return None
    if norm_close_disp_0 > tau_b:
        return "SAME_BAR_BULLISH_REVERSAL_PROXY"
    if norm_close_disp_0 < -tau_b:
        return "SAME_BAR_BEARISH_REVERSAL_PROXY"
    return "SAME_BAR_DUAL_SIDED_AMBIGUOUS"


def classify_samebar_subsequent(Q, u, d, proxy_sign, t_h, tau_d=TAU_D):
    """Q,u,d: arrays indexed by tau (0..N-1). proxy_sign: +1 bullish, -1
    bearish. t_h: last bar index of the horizon (inclusive)."""
    t_takeover = None
    for t in range(1, t_h + 1):
        if t >= len(Q) or not np.isfinite(Q[t]):
            continue
        if np.sign(Q[t]) == -proxy_sign and abs(Q[t]) > tau_d:
            t_takeover = t
            break
    if t_takeover is None:
        if proxy_sign > 0:
            expanded = np.isfinite(u[t_h]) and np.isfinite(u[0]) and u[t_h] > u[0]
        else:
            expanded = np.isfinite(d[t_h]) and np.isfinite(d[0]) and d[t_h] > d[0]
        return ("CONTINUATION_EXPANSION_PROXY_DIRECTION" if expanded
               else "BALANCE_FAILURE_TO_EXPAND"), None
    hold_bars = range(1, t_takeover)
    clean_hold = len(list(hold_bars)) > 0 and all(
        np.isfinite(Q[t]) and np.sign(Q[t]) == proxy_sign for t in hold_bars)
    if clean_hold:
        return "LATER_ORDERED_REVERSAL_AFTER_PROXY", t_takeover
    return "LATER_OPPOSITE_SIDE_TAKEOVER", None


# ------------------------------------------------------------ ordinary 6 --
def classify_ordinary(u, d, Q, close_disp, t_h, tau_c=TAU_C, tau_d=TAU_D, n_balance=N_INITIAL_BALANCE):
    """u,d,Q,close_disp: arrays 0..N-1 (bar 0 already confirmed NOT
    dual-sided by the caller). Returns (class_label, extra_dict)."""
    t_init, init_dir = None, None
    ambiguous_bars = []
    for t in range(0, t_h + 1):
        if t >= len(u) or not (np.isfinite(u[t]) and np.isfinite(d[t])):
            continue
        up_c = u[t] >= tau_c
        dn_c = d[t] >= tau_c
        if up_c and dn_c:
            ambiguous_bars.append(t)
            continue
        if up_c:
            t_init, init_dir = t, 1
            break
        if dn_c:
            t_init, init_dir = t, -1
            break

    if t_init is None:
        # possible class 6: quiet through n_balance, then breakout
        if t_h + 1 > n_balance:
            post = None
            for t in range(n_balance, t_h + 1):
                if t >= len(u) or not (np.isfinite(u[t]) and np.isfinite(d[t])):
                    continue
                if u[t] >= tau_c and d[t] >= tau_c:
                    continue
                if u[t] >= tau_c:
                    post = (t, 1); break
                if d[t] >= tau_c:
                    post = (t, -1); break
            if post is not None:
                _, pdir = post
                if np.isfinite(Q[t_h]) and np.sign(Q[t_h]) == pdir and abs(Q[t_h]) > tau_d:
                    return "DELAYED_EXPANSION_AFTER_INITIAL_BALANCE", {"ambiguous_bars": ambiguous_bars}
        return "TWO_SIDED_BALANCED", {"ambiguous_bars": ambiguous_bars}

    # open recross + reversal confirmation
    t_conf = None
    recrossed = False
    for t in range(t_init + 1, t_h + 1):
        if t >= len(close_disp) or not np.isfinite(close_disp[t]):
            continue
        if not recrossed and np.sign(close_disp[t]) == -init_dir:
            recrossed = True
        if recrossed:
            if init_dir > 0 and np.isfinite(d[t]) and d[t] >= tau_c:
                t_conf = t; break
            if init_dir < 0 and np.isfinite(u[t]) and u[t] >= tau_c:
                t_conf = t; break

    qh = Q[t_h] if t_h < len(Q) else np.nan
    if t_conf is not None:
        dominance_flipped = np.isfinite(qh) and np.sign(qh) == -init_dir and abs(qh) > tau_d
        if dominance_flipped:
            label = "INITIAL_DOWNSIDE_BULLISH_REVERSAL" if init_dir < 0 else "INITIAL_UPSIDE_BEARISH_REVERSAL"
            h_conf = t_conf + 1
            return label, {"t_init": t_init, "t_conf": t_conf, "timing_bin": timing_bin(h_conf),
                          "ambiguous_bars": ambiguous_bars}
    # no confirmed, dominance-flipped reversal -> direct or balanced
    if np.isfinite(qh) and np.sign(qh) == init_dir and abs(qh) > tau_d and np.isfinite(close_disp[t_h]) and \
       np.sign(close_disp[t_h]) == init_dir:
        label = "DIRECT_BULLISH_EXPANSION" if init_dir > 0 else "DIRECT_BEARISH_EXPANSION"
        return label, {"t_init": t_init, "ambiguous_bars": ambiguous_bars}
    return "TWO_SIDED_BALANCED", {"t_init": t_init, "ambiguous_bars": ambiguous_bars}


# --------------------------------------------------------------- ladder --
def excursion_ladder(u, d):
    events = []
    result = {}
    for side, arr in (("UP", u), ("DOWN", d)):
        for th in LADDER:
            idx = np.flatnonzero(np.isfinite(arr) & (arr >= th))
            first = int(idx[0]) if len(idx) else None
            result[f"reached_{side}_{th}"] = first is not None
            result[f"first_bar_{side}_{th}"] = first
            if first is not None:
                events.append((first, side, th))
    events.sort(key=lambda e: e[0])
    order = [(s, t) for _, s, t in events]
    result["crossing_order"] = order
    ties = {}
    for tau, grp in _groupby_first(events):
        grp = list(grp)
        if len(grp) > 1:
            ties[tau] = [(s, t) for _, s, t in grp]
    result["same_bar_ties"] = ties
    return result


def _groupby_first(events):
    from itertools import groupby
    return groupby(events, key=lambda e: e[0])
