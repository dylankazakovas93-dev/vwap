"""Read-only audit of Part 2B-1 Family A results: for every (instrument,
level_id), compares the real and synthetic arms' normalized distance from
the 09:30 open (using already-frozen O_0930/scale_U/scale_D/V_real/
V_synth from the committed ledgers) and classifies the control-match
quality. Does NOT redesign the study, generate new controls, recompute
Family A's touch-rate statistics, or run any post-touch hypothesis.
Reads existing committed outputs only; writes a new audit table/report.
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

from . import interactions as ix

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(REPO, "research", "cash_open_level_interactions", "outputs")
TABLES = os.path.join(REPO, "research", "cash_open_level_interactions", "reports", "tables")

BUCKETS = [
    ("0_0p5", 0.0, 0.5), ("0p5_1", 0.5, 1.0), ("1_1p5", 1.0, 1.5), ("1p5_2", 1.5, 2.0),
    ("2_3", 2.0, 3.0), ("3_5", 3.0, 5.0), ("5_10", 5.0, 10.0), ("10_20", 10.0, 20.0),
    ("20_plus", 20.0, np.inf),
]

VALID_MEDIAN_DIFF = 0.25
VALID_P90_DIFF = 0.50
VALID_SMD = 0.20
VALID_OPEN_BUCKET_PP = 5.0
VALID_SAME_ORIENT = 0.95

INVALID_MEDIAN_DIFF = 0.50
INVALID_SMD = 0.50
INVALID_OPEN_BUCKET_PP = 10.0
INVALID_SAME_ORIENT = 0.90
INVALID_SYNTH_CAP = 3.0
INVALID_REAL_EXTENT = 5.0


def _pctl(a, q):
    return float(np.percentile(a, q)) if len(a) else np.nan


def _bucket_pct(a, lo, hi):
    if len(a) == 0:
        return np.nan
    return float(np.mean((a >= lo) & (a < hi)) * 100.0)


def compute_row(instrument, level_id, level_family, g, fa_row):
    n_mutual = len(g)
    O = g["O_0930"].to_numpy()
    su = g["scale_U"].to_numpy()
    sd = g["scale_D"].to_numpy()
    Vr = g["V_real"].to_numpy()
    Vs = g["V_synth"].to_numpy()

    scale_ok = np.isfinite(su) & np.isfinite(sd) & (su > 0) & (sd > 0) & np.isfinite(O)
    n_distance_comparable = int(scale_ok.sum())

    def orient_dist(V):
        orient = np.full(len(V), None, dtype=object)
        dist = np.full(len(V), np.nan)
        for i in range(len(V)):
            if not scale_ok[i]:
                continue
            o, d, s = ix.orientation_for(V[i], O[i], su[i], sd[i])
            orient[i] = o
            if o in ("ABOVE_OPEN", "BELOW_OPEN"):
                dist[i] = abs(V[i] - O[i]) / s
        return orient, dist

    orient_r, dist_r = orient_dist(Vr)
    orient_s, dist_s = orient_dist(Vs)

    n_amb_r = int(np.sum(orient_r == "AT_OPEN_AMBIGUOUS"))
    n_amb_s = int(np.sum(orient_s == "AT_OPEN_AMBIGUOUS"))
    n_above_r = int(np.sum(orient_r == "ABOVE_OPEN"))
    n_below_r = int(np.sum(orient_r == "BELOW_OPEN"))
    n_above_s = int(np.sum(orient_s == "ABOVE_OPEN"))
    n_below_s = int(np.sum(orient_s == "BELOW_OPEN"))

    real_d = dist_r[np.isfinite(dist_r)]
    synth_d = dist_s[np.isfinite(dist_s)]

    row = {
        "instrument": instrument, "level_id": level_id, "level_family": level_family,
        "n_mutually_touch_eligible": n_mutual, "n_distance_comparable": n_distance_comparable,
        "n_at_open_ambiguous_real": n_amb_r, "n_at_open_ambiguous_synth": n_amb_s,
        "pct_above_open_real": 100 * n_above_r / n_distance_comparable if n_distance_comparable else np.nan,
        "pct_below_open_real": 100 * n_below_r / n_distance_comparable if n_distance_comparable else np.nan,
        "pct_above_open_synth": 100 * n_above_s / n_distance_comparable if n_distance_comparable else np.nan,
        "pct_below_open_synth": 100 * n_below_s / n_distance_comparable if n_distance_comparable else np.nan,
    }

    for prefix, arr in (("real", real_d), ("synth", synth_d)):
        row[f"{prefix}_distance_mean"] = float(np.mean(arr)) if len(arr) else np.nan
        row[f"{prefix}_distance_sd"] = float(np.std(arr, ddof=1)) if len(arr) > 1 else np.nan
        row[f"{prefix}_distance_min"] = float(np.min(arr)) if len(arr) else np.nan
        row[f"{prefix}_distance_p10"] = _pctl(arr, 10)
        row[f"{prefix}_distance_p25"] = _pctl(arr, 25)
        row[f"{prefix}_distance_median"] = _pctl(arr, 50)
        row[f"{prefix}_distance_p75"] = _pctl(arr, 75)
        row[f"{prefix}_distance_p90"] = _pctl(arr, 90)
        row[f"{prefix}_distance_p95"] = _pctl(arr, 95)
        row[f"{prefix}_distance_max"] = float(np.max(arr)) if len(arr) else np.nan
        for name, lo, hi in BUCKETS:
            row[f"{prefix}_bucket_{name}_pct"] = _bucket_pct(arr, lo, hi)
        row[f"{prefix}_pct_above_3_units"] = float(np.mean(arr > 3.0) * 100) if len(arr) else np.nan
        row[f"{prefix}_pct_above_5_units"] = float(np.mean(arr > 5.0) * 100) if len(arr) else np.nan
        row[f"{prefix}_pct_above_10_units"] = float(np.mean(arr > 10.0) * 100) if len(arr) else np.nan

    if len(real_d) and len(synth_d):
        row["mean_distance_difference"] = row["real_distance_mean"] - row["synth_distance_mean"]
        row["median_distance_difference"] = row["real_distance_median"] - row["synth_distance_median"]
        row["p90_distance_difference"] = row["real_distance_p90"] - row["synth_distance_p90"]
        row["p95_distance_difference"] = row["real_distance_p95"] - row["synth_distance_p95"]
        pooled_sd = np.sqrt(((row["real_distance_sd"] or 0) ** 2 + (row["synth_distance_sd"] or 0) ** 2) / 2.0)
        row["standardized_mean_difference"] = (row["mean_distance_difference"] / pooled_sd) if pooled_sd > 0 else np.nan
        row["kolmogorov_smirnov_statistic"] = float(stats.ks_2samp(real_d, synth_d).statistic)
        row["wasserstein_distance"] = float(stats.wasserstein_distance(real_d, synth_d))
        row["real_p95_within_synth_support"] = bool(row["real_distance_p95"] <= row["synth_distance_max"])
        row["synth_p95_within_real_support"] = bool(row["synth_distance_p95"] <= row["real_distance_max"])
        row["open_ended_bucket_share_difference_pp"] = row["real_bucket_20_plus_pct"] - row["synth_bucket_20_plus_pct"]
    else:
        for k in ("mean_distance_difference", "median_distance_difference", "p90_distance_difference",
                  "p95_distance_difference", "standardized_mean_difference", "kolmogorov_smirnov_statistic",
                  "wasserstein_distance", "open_ended_bucket_share_difference_pp"):
            row[k] = np.nan
        row["real_p95_within_synth_support"] = False
        row["synth_p95_within_real_support"] = False

    same_orient = (orient_r == orient_s) & scale_ok
    row["same_orientation_rate"] = float(np.mean(same_orient[scale_ok])) if n_distance_comparable else np.nan

    # ------------------------------------------- existing Family A columns --
    row["real_touch_count"] = int(fa_row["n_real_touched"]) if fa_row is not None else np.nan
    row["real_touch_rate"] = fa_row["real_touch_rate"] if fa_row is not None else np.nan
    row["synthetic_touch_count"] = int(fa_row["n_synth_touched"]) if fa_row is not None else np.nan
    row["synthetic_touch_rate"] = fa_row["synth_touch_rate"] if fa_row is not None else np.nan
    row["touch_rate_difference"] = fa_row["paired_touch_rate_diff"] if fa_row is not None else np.nan
    row["n_real_only"] = int(fa_row["n_real_only"]) if fa_row is not None else np.nan
    row["n_synthetic_only"] = int(fa_row["n_synth_only"]) if fa_row is not None else np.nan
    row["n_both_touched"] = int(fa_row["n_both_touched"]) if fa_row is not None else np.nan
    row["n_neither_touched"] = int(fa_row["n_neither_touched"]) if fa_row is not None else np.nan
    row["mcnemar_raw_p"] = fa_row["p_raw"] if fa_row is not None else np.nan
    row["mcnemar_bonferroni_p"] = fa_row["p_bonferroni"] if fa_row is not None else np.nan
    row["bonferroni_survivor"] = bool(fa_row["bonferroni_survivor"]) if fa_row is not None else False
    row["family_a_original_status"] = fa_row["status"] if fa_row is not None else "not_found_in_committed_table"

    # audit mismatch check: recompute n_mutually_eligible from the ledger,
    # compare to the committed Family A table's own count (no recompute of
    # the McNemar statistic itself, only a cross-check of the input count)
    if fa_row is not None and int(fa_row["n_mutually_eligible"]) != n_mutual:
        row["audit_mismatch"] = (f"committed_n_mutually_eligible={int(fa_row['n_mutually_eligible'])} "
                                 f"!= ledger_recount={n_mutual}")
    else:
        row["audit_mismatch"] = ""

    return row


def classify(row):
    reasons = []
    if row["n_distance_comparable"] == 0 or not np.isfinite(row.get("median_distance_difference", np.nan)):
        return "INVALID_DISTANCE_MATCH", "no_distance_comparable_observations"

    med_diff = abs(row["median_distance_difference"])
    p90_diff = abs(row["p90_distance_difference"])
    smd = abs(row["standardized_mean_difference"]) if np.isfinite(row["standardized_mean_difference"]) else np.inf
    open_pp = abs(row["open_ended_bucket_share_difference_pp"]) if np.isfinite(row["open_ended_bucket_share_difference_pp"]) else np.inf
    same_orient = row["same_orientation_rate"] if np.isfinite(row["same_orientation_rate"]) else 0.0
    real_p95_ok = row["real_p95_within_synth_support"]
    synth_capped = row["synth_distance_p95"] <= INVALID_SYNTH_CAP if np.isfinite(row["synth_distance_p95"]) else False
    real_extends = row["real_distance_p95"] > INVALID_REAL_EXTENT if np.isfinite(row["real_distance_p95"]) else False

    invalid = False
    if med_diff > INVALID_MEDIAN_DIFF:
        reasons.append(f"median_diff {med_diff:.2f} > {INVALID_MEDIAN_DIFF}"); invalid = True
    if smd > INVALID_SMD:
        reasons.append(f"|SMD| {smd:.2f} > {INVALID_SMD}"); invalid = True
    if open_pp > INVALID_OPEN_BUCKET_PP:
        reasons.append(f"open_bucket_pp_diff {open_pp:.1f} > {INVALID_OPEN_BUCKET_PP}"); invalid = True
    if not real_p95_ok:
        reasons.append("real_p95 exceeds synthetic max"); invalid = True
    if synth_capped and real_extends:
        reasons.append(f"synthetic capped (p95<={INVALID_SYNTH_CAP}) while real p95>{INVALID_REAL_EXTENT}"); invalid = True
    if same_orient < INVALID_SAME_ORIENT:
        reasons.append(f"same_orientation_rate {same_orient:.2f} < {INVALID_SAME_ORIENT}"); invalid = True

    if invalid:
        return "INVALID_DISTANCE_MATCH", "; ".join(reasons)

    valid = (med_diff <= VALID_MEDIAN_DIFF and p90_diff <= VALID_P90_DIFF and smd <= VALID_SMD
             and open_pp <= VALID_OPEN_BUCKET_PP and real_p95_ok and same_orient >= VALID_SAME_ORIENT)
    if valid:
        return "VALID_DISTANCE_MATCH", ""

    fail_reasons = []
    if med_diff > VALID_MEDIAN_DIFF: fail_reasons.append(f"median_diff {med_diff:.2f} > {VALID_MEDIAN_DIFF}")
    if p90_diff > VALID_P90_DIFF: fail_reasons.append(f"p90_diff {p90_diff:.2f} > {VALID_P90_DIFF}")
    if smd > VALID_SMD: fail_reasons.append(f"|SMD| {smd:.2f} > {VALID_SMD}")
    if open_pp > VALID_OPEN_BUCKET_PP: fail_reasons.append(f"open_bucket_pp_diff {open_pp:.1f} > {VALID_OPEN_BUCKET_PP}")
    if not real_p95_ok: fail_reasons.append("real_p95 not within synth support")
    if same_orient < VALID_SAME_ORIENT: fail_reasons.append(f"same_orientation_rate {same_orient:.2f} < {VALID_SAME_ORIENT}")
    return "QUESTIONABLE_DISTANCE_MATCH", "; ".join(fail_reasons)


def interpretation(row):
    if row["family_a_original_status"] != "tested":
        return "UNDERPOWERED"
    cls = row["control_match_classification"]
    if cls == "INVALID_DISTANCE_MATCH":
        return "INVALID_CONTROL_ARTIFACT"
    if cls == "QUESTIONABLE_DISTANCE_MATCH":
        return "QUESTIONABLE_RESULT_REQUIRES_BETTER_MATCHING"
    # cls == VALID_DISTANCE_MATCH
    return "VALID_SUPPORTED_TOUCH_RATE_DIFFERENCE" if row["bonferroni_survivor"] else "VALID_NULL_TOUCH_RATE_DIFFERENCE"


def main():
    es_levels = pd.read_parquet(os.path.join(OUT, "es_levels.parquet"))
    nq_levels = pd.read_parquet(os.path.join(OUT, "nq_levels.parquet"))
    levels_tbl = pd.concat([es_levels, nq_levels], ignore_index=True)
    levels_tbl = levels_tbl[levels_tbl["mutually_touch_eligible"]]

    family_a = pd.read_csv(os.path.join(TABLES, "primary_family_a_results.csv"))

    rows = []
    for (instrument, level_id), g in levels_tbl.groupby(["instrument", "level_id"]):
        level_family = g["level_family"].iloc[0]
        fa_match = family_a[(family_a["instrument"] == instrument) & (family_a["level_id"] == level_id)]
        fa_row = fa_match.iloc[0] if len(fa_match) else None
        row = compute_row(instrument, level_id, level_family, g, fa_row)
        cls, reasons = classify(row)
        row["control_match_classification"] = cls
        row["control_match_failure_reasons"] = reasons
        row["family_a_interpretation"] = interpretation(row)
        rows.append(row)

    audit = pd.DataFrame(rows).sort_values(["instrument", "level_id"]).reset_index(drop=True)
    assert len(audit) == 76, f"expected 76 rows, got {len(audit)}"
    audit.to_csv(os.path.join(TABLES, "family_a_distance_match_audit.csv"), index=False)
    print(f"wrote {len(audit)} rows to family_a_distance_match_audit.csv", flush=True)
    print(audit["control_match_classification"].value_counts(), flush=True)
    print(audit["family_a_interpretation"].value_counts(), flush=True)
    mismatches = audit[audit["audit_mismatch"] != ""]
    if len(mismatches):
        print("AUDIT MISMATCHES FOUND:", flush=True)
        print(mismatches[["instrument", "level_id", "audit_mismatch"]], flush=True)
    return audit


if __name__ == "__main__":
    main()
