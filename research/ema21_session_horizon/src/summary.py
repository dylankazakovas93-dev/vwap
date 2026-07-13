"""Required summary cells: instrument x session x touch_time_bucket x
approach_side x horizon. See SPEC_SESSION_HORIZONS.md section 11.
"""
import numpy as np
import pandas as pd
from scipy import stats

from .events import HORIZONS
from .outcomes import BARRIERS

TOUCH_BUCKETS = ("SESSION_0_TO_30", "SESSION_30_TO_60", "SESSION_60_TO_120", "SESSION_120_PLUS", "ALL_SESSION")
SESSIONS = ("ASIA", "LONDON", "NEW_YORK")
MIN_SAMPLE_UNDERPOWERED = 20


def binom_p(k, n):
    if n == 0:
        return np.nan
    return float(stats.binomtest(k, n, 0.5, alternative="two-sided").pvalue)


def build_cells(events_full: pd.DataFrame, excursions_full: pd.DataFrame) -> pd.DataFrame:
    cells = []
    if events_full.empty:
        return pd.DataFrame(cells)

    group_keys = ["instrument", "session", "approach_side"]
    for gvals, g in events_full.groupby(group_keys):
        instrument, session, side = gvals
        exmask = (
            (excursions_full["instrument"] == instrument)
            & (excursions_full["session"] == session)
            & (excursions_full["approach_side"] == side)
        )
        ex_g = excursions_full.loc[exmask]

        for bucket in TOUCH_BUCKETS:
            if bucket == "ALL_SESSION":
                gs = g
                ex_s = ex_g
            else:
                gs = g.loc[g["touch_time_bucket"] == bucket]
                ex_s = ex_g.loc[ex_g["start_touch_time_bucket"] == bucket]

            n_touch = len(gs)
            n_armed = len(ex_s)
            touch_rate = (n_touch / n_armed) if n_armed > 0 else np.nan

            n_rej_sb = int((gs["same_bar_morphology"] == "SAME_BAR_REJECTION_PROXY").sum())
            n_brk_sb = int((gs["same_bar_morphology"] == "SAME_BAR_BREAKTHROUGH_PROXY").sum())
            n_neutral_sb = int((gs["same_bar_morphology"] == "SAME_BAR_NEUTRAL").sum())
            sb_p = binom_p(n_rej_sb, n_rej_sb + n_brk_sb) if (n_rej_sb + n_brk_sb) > 0 else np.nan
            retouch_rate = float(gs["retouched"].mean()) if n_touch > 0 else np.nan

            for H in HORIZONS:
                signed_col = f"signed_close_atr_h{H}"
                rej_col = f"rejection_exc_atr_h{H}"
                brk_col = f"breakthrough_exc_atr_h{H}"
                dom_col = f"dominance_h{H}"
                valid_h = gs.loc[gs[f"horizon_{H}_complete"] & gs["atr_valid"]]

                med_signed = float(valid_h[signed_col].median()) if len(valid_h) else np.nan
                med_rej = float(valid_h[rej_col].median()) if len(valid_h) else np.nan
                med_brk = float(valid_h[brk_col].median()) if len(valid_h) else np.nan
                med_dom = float(valid_h[dom_col].median()) if valid_h[dom_col].notna().any() else np.nan
                p_rej_gt_brk = float((valid_h[rej_col] > valid_h[brk_col]).mean()) if len(valid_h) else np.nan
                p_brk_gt_rej = float((valid_h[brk_col] > valid_h[rej_col]).mean()) if len(valid_h) else np.nan

                for b in BARRIERS:
                    col = f"b{b}_h{H}_outcome"
                    if col not in gs.columns:
                        continue
                    vc = gs[col].value_counts()
                    n_rej_first = int(vc.get("REJECTION_FIRST", 0))
                    n_brk_first = int(vc.get("BREAKTHROUGH_FIRST", 0))
                    n_tie = int(vc.get("SAME_BAR_TIE", 0))
                    n_neither = int(vc.get("NEITHER", 0))
                    n_nontied = n_rej_first + n_brk_first
                    p_barrier = binom_p(n_rej_first, n_nontied) if n_nontied > 0 else np.nan
                    rej_rate = n_rej_first / n_touch if n_touch else np.nan
                    brk_rate = n_brk_first / n_touch if n_touch else np.nan
                    tie_rate = n_tie / n_touch if n_touch else np.nan
                    neither_rate = n_neither / n_touch if n_touch else np.nan

                    cells.append(
                        {
                            "instrument": instrument,
                            "session": session,
                            "touch_time_bucket": bucket,
                            "approach_side": side,
                            "horizon_bars": H,
                            "barrier_atr": b,
                            "eligible_armed_excursions": n_armed,
                            "touch_events": n_touch,
                            "touch_rate": touch_rate,
                            "same_bar_rejection_count": n_rej_sb,
                            "same_bar_breakthrough_count": n_brk_sb,
                            "same_bar_neutral_count": n_neutral_sb,
                            "same_bar_rejection_rate": (n_rej_sb / n_touch) if n_touch else np.nan,
                            "same_bar_breakthrough_rate": (n_brk_sb / n_touch) if n_touch else np.nan,
                            "same_bar_rej_minus_brk": ((n_rej_sb - n_brk_sb) / n_touch) if n_touch else np.nan,
                            "same_bar_binom_p": sb_p,
                            "median_signed_close_atr": med_signed,
                            "median_rejection_exc_atr": med_rej,
                            "median_breakthrough_exc_atr": med_brk,
                            "median_dominance": med_dom,
                            "p_rejection_exc_gt_breakthrough_exc": p_rej_gt_brk,
                            "p_breakthrough_exc_gt_rejection_exc": p_brk_gt_rej,
                            "post_touch_retouch_rate": retouch_rate,
                            "barrier_rejection_first_n": n_rej_first,
                            "barrier_breakthrough_first_n": n_brk_first,
                            "barrier_tie_n": n_tie,
                            "barrier_neither_n": n_neither,
                            "barrier_rejection_first_rate": rej_rate,
                            "barrier_breakthrough_first_rate": brk_rate,
                            "barrier_tie_rate": tie_rate,
                            "barrier_neither_rate": neither_rate,
                            "barrier_rej_minus_brk_first_rate": (rej_rate - brk_rate) if n_touch else np.nan,
                            "barrier_nontied_n": n_nontied,
                            "barrier_binom_p": p_barrier,
                            "sample_status": "OK" if (n_touch >= 50 and n_nontied >= 20) else "UNDERPOWERED",
                        }
                    )
    return pd.DataFrame(cells)


def benjamini_hochberg(pvals: np.ndarray, alpha: float = 0.05):
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    out_adj = np.full(n, np.nan)
    out_rej = np.zeros(n, dtype=bool)
    idx = np.where(np.isfinite(p))[0]
    if len(idx) == 0:
        return out_adj, out_rej
    order = idx[np.argsort(p[idx])]
    m = len(order)
    prev = 1.0
    adj_sorted = np.empty(m)
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        val = min(p[i] * m / rank, prev)
        prev = val
        adj_sorted[rank - 1] = val
    for j, i in enumerate(order):
        out_adj[i] = adj_sorted[j]
    out_rej[idx] = out_adj[idx] < alpha
    return out_adj, out_rej
