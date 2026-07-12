"""Frozen validation-cell statistics -- SPEC_VALIDATION.md secs 5-11.
One-sided exact binomial (primary/supporting), Holm correction (the two
supporting candidates only), year-by-year reporting, same-bar
morphology, rolling-state replication. No multiplicity correction is
applied to the single primary test, per instruction.
"""
import numpy as np
import pandas as pd
from scipy import stats as sstats

VALIDATION_YEARS = (2023, 2024, 2025, 2026)  # 2026 partial, labelled explicitly

MIN_TOUCHES = 100
MIN_NONTIED = 50
MIN_DIFF_PP = 0.05
MIN_YEARS_SIGN = 3
MAX_YEAR_SHARE = 0.50


def cell_stats(levels_tbl, events_tbl, outcomes_tbl, barriers_tbl,
               instrument, level_id, A, H, b=1.0):
    lv = levels_tbl[(levels_tbl.instrument == instrument) & (levels_tbl.level_id == level_id)]
    n_eligible = int(lv["level_valid"].sum())

    ev = events_tbl[(events_tbl.instrument == instrument) & (events_tbl.level_id == level_id)
                    & (events_tbl.first_touch_elapsed_bar <= A)]
    n_touch = len(ev)

    b1 = barriers_tbl[(barriers_tbl.instrument == instrument) & (barriers_tbl.level_id == level_id)
                      & (barriers_tbl.b == b) & (barriers_tbl.horizon == H)
                      & (barriers_tbl.first_touch_elapsed_bar <= A)]
    n_cont = int((b1["barrier_first_outcome"] == "CONTINUATION_FIRST").sum())
    n_rev = int((b1["barrier_first_outcome"] == "REVERSAL_FIRST").sum())
    n_tie = int((b1["barrier_first_outcome"] == "SAME_BAR_TIE").sum())
    n_neither = int((b1["barrier_first_outcome"] == "NEITHER").sum())
    n_nontied = n_cont + n_rev
    n_barrier_total = len(b1)

    oc = outcomes_tbl[(outcomes_tbl.instrument == instrument) & (outcomes_tbl.level_id == level_id)
                      & (outcomes_tbl.horizon == H) & (outcomes_tbl.first_touch_elapsed_bar <= A)]
    median_signed_close_sd = oc["SIGNED_CLOSE_SD_H"].median() if len(oc) else np.nan

    cont_rate = n_cont / n_barrier_total if n_barrier_total else np.nan
    rev_rate = n_rev / n_barrier_total if n_barrier_total else np.nan
    diff = (n_cont - n_rev) / n_barrier_total if n_barrier_total else np.nan

    if n_nontied >= 1:
        p_raw = sstats.binomtest(n_cont, n_nontied, 0.5, alternative="greater").pvalue
    else:
        p_raw = np.nan

    # year breakdown
    year_rows = []
    for year in VALIDATION_YEARS:
        b1_y = b1[b1["calendar_year"] == year]
        n_cont_y = int((b1_y["barrier_first_outcome"] == "CONTINUATION_FIRST").sum())
        n_rev_y = int((b1_y["barrier_first_outcome"] == "REVERSAL_FIRST").sum())
        n_total_y = len(b1_y)
        ev_y = ev[ev["calendar_year"] == year]
        oc_y = oc[oc["calendar_year"] == year]
        year_rows.append({
            "year": year, "partial": year == 2026,
            "touches": len(ev_y), "n_nontied": n_cont_y + n_rev_y,
            "continuation_first_rate": n_cont_y / n_total_y if n_total_y else np.nan,
            "reversal_first_rate": n_rev_y / n_total_y if n_total_y else np.nan,
            "cont_minus_rev_diff": (n_cont_y - n_rev_y) / n_total_y if n_total_y else np.nan,
            "median_signed_close_sd": oc_y["SIGNED_CLOSE_SD_H"].median() if len(oc_y) else np.nan,
        })
    year_df = pd.DataFrame(year_rows)
    effects = year_df["cont_minus_rev_diff"].dropna()
    pooled_sign = np.sign(diff) if np.isfinite(diff) else 0
    n_years_same_sign = int((np.sign(effects) == pooled_sign).sum()) if len(effects) else 0
    total_touches = year_df["touches"].sum()
    max_year_share = (year_df["touches"].max() / total_touches) if total_touches else np.nan

    return {
        "instrument": instrument, "level_id": level_id, "activation_window": A, "horizon": H, "b": b,
        "n_eligible_sessions": n_eligible, "n_touch_in_A": n_touch,
        "n_continuation_first": n_cont, "n_reversal_first": n_rev,
        "n_same_bar_tie": n_tie, "n_neither": n_neither, "n_nontied": n_nontied,
        "continuation_first_rate": cont_rate, "reversal_first_rate": rev_rate,
        "cont_minus_rev_diff": diff, "p_raw_one_sided": p_raw,
        "median_signed_close_sd": median_signed_close_sd,
        "n_years_with_pooled_sign": n_years_same_sign, "n_years_reported": len(effects),
        "max_annual_effect": effects.max() if len(effects) else np.nan,
        "min_annual_effect": effects.min() if len(effects) else np.nan,
        "mean_annual_effect": effects.mean() if len(effects) else np.nan,
        "sd_annual_effect": effects.std(ddof=1) if len(effects) > 1 else np.nan,
        "max_year_touch_share": max_year_share,
        "year_table": year_df,
    }


def evaluate_success_criteria(stat: dict) -> dict:
    c1 = stat["n_touch_in_A"] >= MIN_TOUCHES
    c2 = stat["n_nontied"] >= MIN_NONTIED
    c3 = np.isfinite(stat["cont_minus_rev_diff"]) and stat["cont_minus_rev_diff"] >= MIN_DIFF_PP
    c4 = np.isfinite(stat.get("p_final", stat["p_raw_one_sided"])) and stat.get("p_final", stat["p_raw_one_sided"]) < 0.05
    c5 = np.isfinite(stat["median_signed_close_sd"]) and stat["median_signed_close_sd"] > 0
    c6 = stat["n_years_with_pooled_sign"] >= MIN_YEARS_SIGN
    c7 = np.isfinite(stat["max_year_touch_share"]) and stat["max_year_touch_share"] <= MAX_YEAR_SHARE
    criteria = {"c1_min_touches": c1, "c2_min_nontied": c2, "c3_min_diff": c3, "c4_p_significant": c4,
               "c5_median_signed_close_positive": c5, "c6_year_sign_stability": c6,
               "c7_no_year_dominance": c7}
    all_pass = all(criteria.values())
    underpowered = not (c1 and c2)
    if underpowered:
        cls = "UNDERPOWERED"
    elif all_pass:
        cls = "VALIDATED"
    elif c3 and c5 and not c4:
        cls = "DIRECTIONALLY_POSITIVE_BUT_INCONCLUSIVE"
    else:
        cls = "FAILED_VALIDATION"
    return {"criteria": criteria, "all_criteria_pass": all_pass, "classification": cls}


def holm_adjust(pvals):
    """Standard Holm step-down procedure."""
    pvals = np.asarray(pvals, dtype=float)
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    running_max = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * pvals[idx]
        running_max = max(running_max, val)
        adj[idx] = min(running_max, 1.0)
    return adj


def same_bar_stats(events_tbl, instrument, level_id, A):
    ev = events_tbl[(events_tbl.instrument == instrument) & (events_tbl.level_id == level_id)
                    & (events_tbl.first_touch_elapsed_bar <= A)]
    n_rev = int((ev["same_bar_morphology"] == "SAME_BAR_REVERSAL_PROXY").sum())
    n_blast = int((ev["same_bar_morphology"] == "SAME_BAR_BLAST_THROUGH_PROXY").sum())
    n_nonneutral = n_rev + n_blast
    diff = (n_blast - n_rev) / n_nonneutral if n_nonneutral else np.nan
    if n_nonneutral >= 1:
        k = min(n_rev, n_blast)
        p_raw = sstats.binomtest(k, n_nonneutral, 0.5, alternative="two-sided").pvalue
    else:
        p_raw = np.nan

    year_rows = []
    for year in VALIDATION_YEARS:
        ev_y = ev[ev["calendar_year"] == year]
        n_rev_y = int((ev_y["same_bar_morphology"] == "SAME_BAR_REVERSAL_PROXY").sum())
        n_blast_y = int((ev_y["same_bar_morphology"] == "SAME_BAR_BLAST_THROUGH_PROXY").sum())
        n_nn_y = n_rev_y + n_blast_y
        year_rows.append({"year": year, "partial": year == 2026,
                         "reversal_rate": n_rev_y / n_nn_y if n_nn_y else np.nan,
                         "blast_through_rate": n_blast_y / n_nn_y if n_nn_y else np.nan})
    return {"instrument": instrument, "level_id": level_id, "activation_window": A,
           "n_nonneutral": n_nonneutral, "n_reversal": n_rev, "n_blast_through": n_blast,
           "reversal_rate": n_rev / n_nonneutral if n_nonneutral else np.nan,
           "blast_through_rate": n_blast / n_nonneutral if n_nonneutral else np.nan,
           "blast_minus_reversal_diff": diff, "p_raw": p_raw, "year_table": pd.DataFrame(year_rows)}
