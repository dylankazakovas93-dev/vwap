"""Matching-strata construction, per-cell development statistics, and the
12-criteria candidate-family gate. See SPEC_AUCTION_VALUE.md sections 7-9
and DECISIONS.md #5, #6, #11.
"""
import numpy as np
import pandas as pd

from . import permutation as perm

MIN_TREAT_FOR_PERMUTATION = 300
MIN_CONTROL_FOR_PERMUTATION = 150

CANDIDATE_MIN_TREAT = 300
CANDIDATE_MIN_CONTROL = 150
CANDIDATE_MIN_POOLED_EFFECT = 0.05
CANDIDATE_MAX_WORST_YEAR_EFFECT = -0.03
CANDIDATE_BH_Q = 0.10
CANDIDATE_MAX_YEAR_SHARE = 0.50


def compute_frozen_bands(dev_rows: list) -> dict:
    """Tercile cut points for va_width, freshness_hours, poc_distance_pct,
    confirmation_atr20, computed once on pooled development-year rows
    (treatment + control together) and frozen (DECISIONS.md #5)."""
    def cuts(vals):
        vals = np.asarray([v for v in vals if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
        if len(vals) < 3:
            return (np.nan, np.nan)
        return (float(np.quantile(vals, 1 / 3)), float(np.quantile(vals, 2 / 3)))

    return {
        "va_width": cuts([r.get("va_width") for r in dev_rows]),
        "freshness": cuts([r.get("freshness_hours") for r in dev_rows]),
        "poc_distance": cuts([r.get("poc_distance_pct") for r in dev_rows]),
        "atr20": cuts([r.get("confirmation_atr20") for r in dev_rows]),
    }


def _band_index(value, cutoffs):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return -1
    lo, hi = cutoffs
    if np.isnan(lo):
        return -1
    if value <= lo:
        return 0
    if value <= hi:
        return 1
    return 2


def clock_bucket(et_minute) -> int:
    return int(et_minute) // 60


def stratum_id(row: dict, bands: dict) -> str:
    # A plain string key, not a tuple: numpy's elementwise `==` against a
    # tuple-valued object array silently mis-broadcasts (compares each
    # tuple element positionally instead of the whole tuple), which would
    # corrupt every stratum-mask comparison downstream. Strings compare
    # correctly under numpy `==`.
    parts = (
        clock_bucket(row["confirmation_et_minute"]),
        _band_index(row.get("va_width"), bands["va_width"]),
        _band_index(row.get("freshness_hours"), bands["freshness"]),
        _band_index(row.get("poc_distance_pct"), bands["poc_distance"]),
        _band_index(row.get("confirmation_atr20"), bands["atr20"]),
    )
    return "-".join(str(p) for p in parts)


def add_strata(rows: list, bands: dict) -> list:
    out = []
    for r in rows:
        r = dict(r)
        r["stratum"] = stratum_id(r, bands)
        out.append(r)
    return out


def dev_year_of(row: dict) -> int:
    ts = row.get("target_session_date", row.get("confirmation_ts"))
    return int(pd.Timestamp(ts).year)


def _resolved_labels(rows: list, horizon: int):
    """Returns (labels[bool: True=POC_FIRST], strata) for rows resolved
    (non-ambiguous, non-incomplete) at the given horizon. `strata` is an
    object array of stratum-id tuples -- built via explicit assignment,
    not `np.array(list_of_tuples, dtype=object)`, because numpy silently
    collapses a list of equal-length tuples into a 2D array instead of a
    1D array of tuple objects, which would make each "stratum" unhashable."""
    labels, strata = [], []
    for r in rows:
        o = r.get(f"outcome_h{horizon}")
        if o not in ("POC_FIRST", "REDISCOVERY_FIRST"):
            continue
        labels.append(o == "POC_FIRST")
        strata.append(r["stratum"])
    strata_arr = np.empty(len(strata), dtype=object)
    strata_arr[:] = strata
    return np.array(labels, dtype=bool), strata_arr


def _simple_pooled_diff(treat_rows, control_rows, horizon):
    t_lab, t_str = _resolved_labels(treat_rows, horizon)
    c_lab, c_str = _resolved_labels(control_rows, horizon)
    common = sorted(set(t_str.tolist()) & set(c_str.tolist()), key=lambda x: str(x))
    if not common:
        return np.nan, 0, 0
    num_t, den_t, num_c, den_c = 0, 0, 0, 0
    for s in common:
        tm, cm = t_str == s, c_str == s
        if tm.sum() == 0 or cm.sum() == 0:
            continue
        num_t += t_lab[tm].sum(); den_t += tm.sum()
        num_c += c_lab[cm].sum(); den_c += cm.sum()
    if den_t == 0 or den_c == 0:
        return np.nan, den_t, den_c
    return (num_t / den_t) - (num_c / den_c), int(den_t), int(den_c)


def evaluate_cell(treat_rows: list, control_rows: list, dev_years=(2018, 2020, 2022, 2024),
                   primary_horizon: int = 60) -> dict:
    """Full development-statistics record for one grid cell (already
    filtered to one profile_mapping x side x A x B x C x D x E
    combination), against its MATCHED_INSIDE_STATE control population."""
    n_treat_all = len(treat_rows)
    n_control_all = len(control_rows)

    pooled_diff, n_treat_matched, n_control_matched = _simple_pooled_diff(treat_rows, control_rows, primary_horizon)

    year_effects = {}
    for y in dev_years:
        ty = [r for r in treat_rows if dev_year_of(r) == y]
        cy = [r for r in control_rows if dev_year_of(r) == y]
        d, nt, nc = _simple_pooled_diff(ty, cy, primary_horizon)
        year_effects[y] = {"diff": d, "n_treat": nt, "n_control": nc}

    diff_30, _, _ = _simple_pooled_diff(treat_rows, control_rows, 30)
    diff_120, _, _ = _simple_pooled_diff(treat_rows, control_rows, 120)

    permutation_result = None
    if n_treat_all >= MIN_TREAT_FOR_PERMUTATION and n_control_matched >= MIN_CONTROL_FOR_PERMUTATION:
        t_lab, t_str = _resolved_labels(treat_rows, primary_horizon)
        c_lab, c_str = _resolved_labels(control_rows, primary_horizon)
        permutation_result = perm.stratified_permutation_test(t_lab, t_str, c_lab, c_str)

    positive_years = sum(1 for y in dev_years if not np.isnan(year_effects[y]["diff"]) and year_effects[y]["diff"] > 0)
    worst_year_effect = min(
        (year_effects[y]["diff"] for y in dev_years if not np.isnan(year_effects[y]["diff"])), default=np.nan
    )

    mass = {y: (year_effects[y]["n_treat"] * abs(year_effects[y]["diff"])
                if not np.isnan(year_effects[y]["diff"]) else 0.0) for y in dev_years}
    total_mass = sum(mass.values())
    max_year_share = (max(mass.values()) / total_mass) if total_mass > 0 else np.nan

    return {
        "n_treat_all": n_treat_all, "n_control_all": n_control_all,
        "n_treat_matched": n_treat_matched, "n_control_matched": n_control_matched,
        "pooled_diff_h60": pooled_diff, "pooled_diff_h30": diff_30, "pooled_diff_h120": diff_120,
        "year_effects": year_effects, "positive_years": positive_years,
        "worst_year_effect": worst_year_effect, "max_year_share": max_year_share,
        "permutation": permutation_result,
    }


def check_poc_distance_matching(treat_rows: list, control_rows: list) -> bool:
    """Candidate criterion 11 positive-control check: treatment group must
    not start materially closer to POC than its matched control (would
    indicate the tercile-band matching itself failed)."""
    t_vals = [r["poc_distance_pct"] for r in treat_rows if r.get("poc_distance_pct") is not None and not np.isnan(r["poc_distance_pct"])]
    c_vals = [r["poc_distance_pct"] for r in control_rows if r.get("poc_distance_pct") is not None and not np.isnan(r["poc_distance_pct"])]
    if not t_vals or not c_vals:
        return False
    return bool(np.median(t_vals) >= np.median(c_vals) - 0.01)


def apply_bh_within_mapping(cell_results: list) -> list:
    """`cell_results` is a flat list of dicts, one per (side x acceptance
    family) cell for ONE profile_mapping, each with a `permutation`
    sub-dict (or None if not computed). BH is applied across all cells
    in this list that have a computed p-value; cells without a computed
    permutation get q=NaN and are excluded from correction, per
    DECISIONS.md #11."""
    p_values = [c["permutation"]["p_value"] if c.get("permutation") else np.nan for c in cell_results]
    q_values = perm.benjamini_hochberg(p_values)
    out = []
    for c, q in zip(cell_results, q_values):
        c = dict(c)
        c["bh_q"] = q
        out.append(c)
    return out


def gate_12_criteria(cell: dict, poc_distance_ok: bool, bin_width_support: int,
                      model_support: int, adjacent_sign_support: int) -> dict:
    """Returns {criterion_name: bool} for all 12 candidate-family
    criteria (SPEC_AUCTION_VALUE.md section 9). `bin_width_support`,
    `model_support`, `adjacent_sign_support` are pre-computed counts from
    the second-pass sensitivity check (DECISIONS.md #11)."""
    perm_r = cell.get("permutation")
    q = cell.get("bh_q")
    c = {
        "c01_min_treat_300": cell["n_treat_all"] >= CANDIDATE_MIN_TREAT,
        "c02_min_control_150": cell["n_control_matched"] >= CANDIDATE_MIN_CONTROL,
        "c03_positive_ge3_of_4_years": cell["positive_years"] >= 3,
        "c04_pooled_effect_ge_5pp": (not np.isnan(cell["pooled_diff_h60"])) and cell["pooled_diff_h60"] >= CANDIDATE_MIN_POOLED_EFFECT,
        "c05_worst_year_no_worse_than_neg3pp": (not np.isnan(cell["worst_year_effect"])) and cell["worst_year_effect"] >= CANDIDATE_MAX_WORST_YEAR_EFFECT,
        "c06_bh_q_le_0_10": (q is not None) and (not np.isnan(q)) and q <= CANDIDATE_BH_Q,
        "c07_same_sign_30_60": (not np.isnan(cell["pooled_diff_h30"])) and (not np.isnan(cell["pooled_diff_h60"]))
                                 and np.sign(cell["pooled_diff_h30"]) == np.sign(cell["pooled_diff_h60"]) and cell["pooled_diff_h60"] > 0,
        "c08_support_2_bin_widths": bin_width_support >= 2,
        "c09_support_uniform_and_1_sensitivity": model_support >= 1,
        "c10_adjacent_params_same_sign": adjacent_sign_support >= 2,
        "c11_not_poc_distance_artifact": poc_distance_ok,
        "c12_no_year_over_50pct_effect_mass": (not np.isnan(cell["max_year_share"])) and cell["max_year_share"] <= CANDIDATE_MAX_YEAR_SHARE,
    }
    c["ALL_PASS"] = all(c.values())
    return c
