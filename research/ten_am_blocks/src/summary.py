"""Required result surfaces for Module A and Module B.
See SPEC_TEN_AM_BLOCKS.md section 10.
"""
import numpy as np
import pandas as pd
from scipy import stats

from .module_a import HORIZONS as HORIZONS_A, BARRIERS as BARRIERS_A
from .module_b import HORIZONS as HORIZONS_B, BARRIERS as BARRIERS_B, ACTIVATION_WINDOWS

STRATA_DIMS = ("ALL", "pre10_stratum", "close_loc_stratum", "dominance_stratum")
STRATA_DIMS_B = STRATA_DIMS + ("freshness", "momentum")


def binom_p(k, n):
    if n == 0:
        return np.nan
    return float(stats.binomtest(k, n, 0.5, alternative="two-sided").pvalue)


def benjamini_hochberg(pvals, alpha=0.05):
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


def _strata_slices(df: pd.DataFrame, dim: str):
    if dim == "ALL":
        yield "ALL", df
        return
    for val in sorted(x for x in df[dim].dropna().unique()):
        yield val, df.loc[df[dim] == val]


def build_module_a_cells(events: pd.DataFrame) -> pd.DataFrame:
    cells = []
    if events.empty:
        return pd.DataFrame(cells)
    dir_events = events.loc[events["directional"]]
    for instrument, gi in dir_events.groupby("instrument"):
        for state, gs in gi.groupby("candle_state"):
            for dim in STRATA_DIMS:
                for val, gd in _strata_slices(gs, dim):
                    n_obs = len(gd)
                    for H in HORIZONS_A:
                        valid_h = gd.loc[gd[f"horizon_{H}_complete"]]
                        med_signed = float(valid_h[f"signed_close_atr_h{H}"].median()) if len(valid_h) else np.nan
                        med_cont = float(valid_h[f"cont_exc_atr_h{H}"].median()) if len(valid_h) else np.nan
                        med_rev = float(valid_h[f"rev_exc_atr_h{H}"].median()) if len(valid_h) else np.nan
                        med_dom = float(valid_h[f"dominance_h{H}"].median()) if valid_h[f"dominance_h{H}"].notna().any() else np.nan
                        p_cont_gt_rev = float((valid_h[f"cont_exc_atr_h{H}"] > valid_h[f"rev_exc_atr_h{H}"]).mean()) if len(valid_h) else np.nan
                        p_rev_gt_cont = float((valid_h[f"rev_exc_atr_h{H}"] > valid_h[f"cont_exc_atr_h{H}"]).mean()) if len(valid_h) else np.nan
                        retouch_rate = float(gd["retouched"].mean()) if n_obs else np.nan
                        for b in BARRIERS_A:
                            col = f"b{b}_h{H}_outcome"
                            vc = gd[col].value_counts()
                            n_cont = int(vc.get("CONTINUATION_FIRST", 0))
                            n_rev = int(vc.get("REVERSAL_FIRST", 0))
                            n_tie = int(vc.get("SAME_BAR_TIE", 0))
                            n_neither = int(vc.get("NEITHER", 0))
                            n_nontied = n_cont + n_rev
                            p_val = binom_p(n_cont, n_nontied) if n_nontied else np.nan
                            cells.append({
                                "instrument": instrument, "candle_state": state,
                                "context_dim": dim, "context_value": val, "horizon_min": H, "barrier": b,
                                "n_observations": n_obs,
                                "continuation_first_rate": n_cont / n_obs if n_obs else np.nan,
                                "reversal_first_rate": n_rev / n_obs if n_obs else np.nan,
                                "cont_minus_rev_first_rate": (n_cont - n_rev) / n_obs if n_obs else np.nan,
                                "tie_rate": n_tie / n_obs if n_obs else np.nan,
                                "neither_rate": n_neither / n_obs if n_obs else np.nan,
                                "median_signed_close_atr": med_signed,
                                "median_cont_exc_atr": med_cont, "median_rev_exc_atr": med_rev,
                                "median_dominance": med_dom,
                                "p_cont_exc_gt_rev_exc": p_cont_gt_rev, "p_rev_exc_gt_cont_exc": p_rev_gt_cont,
                                "retouch_rate": retouch_rate,
                                "n_nontied": n_nontied, "binom_p": p_val,
                                "sample_status": "OK" if (n_obs >= 50 and n_nontied >= 20) else "UNDERPOWERED",
                            })
    return pd.DataFrame(cells)


def build_module_b_cells(events: pd.DataFrame) -> pd.DataFrame:
    cells = []
    if events.empty:
        return pd.DataFrame(cells)
    for instrument, gi in events.groupby("instrument"):
        for side, gside in gi.groupby("side"):
            for window in ACTIVATION_WINDOWS:
                gw = gside.loc[gside[window]]
                for dim in STRATA_DIMS_B:
                    for val, gd in _strata_slices(gw, dim):
                        n_obs = len(gd)
                        n_rev_sb = int((gd["same_bar_morphology"] == "REVERSAL_PROXY").sum())
                        n_brk_sb = int((gd["same_bar_morphology"] == "BREAKTHROUGH_PROXY").sum())
                        n_unres_sb = int((gd["same_bar_morphology"] == "INSIDE_UNRESOLVED").sum())
                        retouch_rate = float(gd["retouched"].mean()) if n_obs else np.nan
                        for H in HORIZONS_B:
                            valid_h = gd.loc[gd[f"horizon_{H}_complete"]]
                            med_signed = float(valid_h[f"signed_close_atr_h{H}"].median()) if len(valid_h) else np.nan
                            med_rev = float(valid_h[f"rev_exc_atr_h{H}"].median()) if len(valid_h) else np.nan
                            med_brk = float(valid_h[f"brk_exc_atr_h{H}"].median()) if len(valid_h) else np.nan
                            med_dom = float(valid_h[f"dominance_h{H}"].median()) if valid_h[f"dominance_h{H}"].notna().any() else np.nan
                            p_rev_gt_brk = float((valid_h[f"rev_exc_atr_h{H}"] > valid_h[f"brk_exc_atr_h{H}"]).mean()) if len(valid_h) else np.nan
                            p_brk_gt_rev = float((valid_h[f"brk_exc_atr_h{H}"] > valid_h[f"rev_exc_atr_h{H}"]).mean()) if len(valid_h) else np.nan
                            for b in BARRIERS_B:
                                col = f"b{b}_h{H}_outcome"
                                vc = gd[col].value_counts()
                                n_rev = int(vc.get("REVERSAL_FIRST", 0))
                                n_brk = int(vc.get("BREAKTHROUGH_FIRST", 0))
                                n_tie = int(vc.get("SAME_BAR_TIE", 0))
                                n_neither = int(vc.get("NEITHER", 0))
                                n_nontied = n_rev + n_brk
                                p_val = binom_p(n_rev, n_nontied) if n_nontied else np.nan
                                cells.append({
                                    "instrument": instrument, "side": side, "activation_window": window,
                                    "context_dim": dim, "context_value": val, "horizon_min": H, "barrier": b,
                                    "valid_blocks": n_obs, "first_interactions": n_obs,
                                    "same_bar_reversal_rate": n_rev_sb / n_obs if n_obs else np.nan,
                                    "same_bar_breakthrough_rate": n_brk_sb / n_obs if n_obs else np.nan,
                                    "same_bar_unresolved_rate": n_unres_sb / n_obs if n_obs else np.nan,
                                    "median_signed_close_atr": med_signed,
                                    "median_rev_exc_atr": med_rev, "median_brk_exc_atr": med_brk,
                                    "median_dominance": med_dom,
                                    "p_rev_exc_gt_brk_exc": p_rev_gt_brk, "p_brk_exc_gt_rev_exc": p_brk_gt_rev,
                                    "retouch_rate": retouch_rate,
                                    "reversal_first_n": n_rev, "breakthrough_first_n": n_brk,
                                    "tie_n": n_tie, "neither_n": n_neither, "n_nontied": n_nontied,
                                    "reversal_first_rate": n_rev / n_obs if n_obs else np.nan,
                                    "breakthrough_first_rate": n_brk / n_obs if n_obs else np.nan,
                                    "rev_minus_brk_first_rate": (n_rev - n_brk) / n_obs if n_obs else np.nan,
                                    "tie_rate": n_tie / n_obs if n_obs else np.nan,
                                    "neither_rate": n_neither / n_obs if n_obs else np.nan,
                                    "binom_p": p_val,
                                    "sample_status": "OK" if (n_obs >= 50 and n_nontied >= 20) else "UNDERPOWERED",
                                })
    return pd.DataFrame(cells)
