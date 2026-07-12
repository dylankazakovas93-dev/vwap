"""Primary confirmatory Family A (McNemar touch rate) and Family B
(paired D_5, Wilcoxon signed-rank), plus secondary/exploratory grid with
Benjamini-Hochberg correction. No profitability, no TP/SL, no entries.
"""
import itertools

import numpy as np
import pandas as pd
from scipy import stats

N_TESTS = 76  # 2 instruments x 38 level_ids, each primary family independently

FAMILY_A_MIN_MUTUAL = 100
FAMILY_A_MIN_DISCORDANT = 20
FAMILY_B_MIN_PAIRS = 50
FAMILY_B_MIN_NONZERO = 20

HL_BOOTSTRAP_SEED = 20260712
HL_BOOTSTRAP_N = 2000


def _wald_ci_diff(n01, n10, N, z=1.96):
    d = (n01 - n10) / N
    var = (n01 + n10 - (n01 - n10) ** 2 / N) / (N ** 2)
    se = np.sqrt(max(var, 0.0))
    return d - z * se, d + z * se


def _mcnemar_or_ci(n01, n10, z=1.96):
    a, b = n01, n10
    if a == 0 or b == 0:
        a, b = a + 0.5, b + 0.5
    log_or = np.log(a / b)
    se = np.sqrt(1 / a + 1 / b)
    return np.exp(log_or - z * se), np.exp(log_or + z * se)


def family_a_touch_rate(levels_tbl: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (instrument, level_id), g in levels_tbl.groupby(["instrument", "level_id"]):
        mutual = g[g["mutually_touch_eligible"]]
        n_mutual = len(mutual)
        row = {"instrument": instrument, "level_id": level_id, "n_mutually_eligible": n_mutual}
        if n_mutual == 0:
            row.update({"status": "no_mutually_eligible_sessions"})
            rows.append(row)
            continue
        # touched flags come from the events table via a separate merge upstream;
        # here levels_tbl carries real/synthetic touch through the events table join
        real_t = mutual["real_touched"].to_numpy()
        synth_t = mutual["synthetic_touched"].to_numpy()
        n_both = int(np.sum(real_t & synth_t))
        n_real_only = int(np.sum(real_t & ~synth_t))
        n_synth_only = int(np.sum(~real_t & synth_t))
        n_neither = int(np.sum(~real_t & ~synth_t))
        n_discordant = n_real_only + n_synth_only

        real_rate = (n_both + n_real_only) / n_mutual
        synth_rate = (n_both + n_synth_only) / n_mutual
        diff = real_rate - synth_rate
        ci_lo, ci_hi = _wald_ci_diff(n_real_only, n_synth_only, n_mutual)
        or_val = (n_real_only / n_synth_only) if n_synth_only > 0 else np.inf if n_real_only > 0 else np.nan
        or_ci_lo, or_ci_hi = _mcnemar_or_ci(n_real_only, n_synth_only)

        if n_discordant > 0:
            k = min(n_real_only, n_synth_only)
            p_raw = stats.binomtest(k, n_discordant, 0.5, alternative="two-sided").pvalue
        else:
            p_raw = 1.0

        confirmatory = n_mutual >= FAMILY_A_MIN_MUTUAL and n_discordant >= FAMILY_A_MIN_DISCORDANT
        row.update({
            "n_real_touched": int(np.sum(real_t)), "n_synth_touched": int(np.sum(synth_t)),
            "real_touch_rate": real_rate, "synth_touch_rate": synth_rate,
            "n_real_only": n_real_only, "n_synth_only": n_synth_only,
            "n_both_touched": n_both, "n_neither_touched": n_neither,
            "n_discordant": n_discordant,
            "paired_touch_rate_diff": diff, "diff_ci_lo": ci_lo, "diff_ci_hi": ci_hi,
            "discordant_odds_ratio": or_val, "or_ci_lo": or_ci_lo, "or_ci_hi": or_ci_hi,
            "p_raw": p_raw, "confirmatory_eligible": confirmatory,
            "status": "tested" if confirmatory else "underpowered_descriptive",
        })
        rows.append(row)

    out = pd.DataFrame(rows)
    if "confirmatory_eligible" not in out.columns:
        out["confirmatory_eligible"] = False
    if "p_raw" not in out.columns:
        out["p_raw"] = np.nan
    out["confirmatory_eligible"] = out["confirmatory_eligible"].fillna(False).astype(bool)
    out["p_bonferroni"] = np.minimum(1.0, out["p_raw"].fillna(1.0) * N_TESTS)
    out["bonferroni_alpha"] = 0.05 / N_TESTS
    out["bonferroni_survivor"] = out["confirmatory_eligible"] & (out["p_bonferroni"] < 0.05)
    return out


def _hodges_lehmann(diffs: np.ndarray) -> float:
    n = len(diffs)
    walsh = []
    for i in range(n):
        for j in range(i, n):
            walsh.append((diffs[i] + diffs[j]) / 2.0)
    return float(np.median(walsh))


def _hl_bootstrap_ci(diffs: np.ndarray, seed=HL_BOOTSTRAP_SEED, n_boot=HL_BOOTSTRAP_N):
    rng = np.random.default_rng(seed)
    n = len(diffs)
    estimates = np.empty(n_boot)
    for b in range(n_boot):
        sample = diffs[rng.integers(0, n, size=n)]
        estimates[b] = _hodges_lehmann(sample)
    return float(np.percentile(estimates, 2.5)), float(np.percentile(estimates, 97.5))


def build_family_b_pairs(levels_tbl: pd.DataFrame, events_tbl: pd.DataFrame, outcomes_tbl: pd.DataFrame) -> pd.DataFrame:
    """One row per (instrument, session_date, level_id) satisfying every
    Family B inclusion criterion (SPEC_LEVEL_INTERACTIONS.md sec 16)."""
    key = ["instrument", "session_date", "level_id"]
    ev = events_tbl.set_index(key + ["arm"])
    real_ev = ev.xs("REAL", level="arm")[["touched", "touch_bucket", "orientation", "normalized_outcome_eligible"]]
    synth_ev = ev.xs("SYNTHETIC", level="arm")[["touched", "touch_bucket", "orientation", "normalized_outcome_eligible"]]
    merged = real_ev.join(synth_ev, lsuffix="_real", rsuffix="_synth", how="inner").reset_index()

    d5 = outcomes_tbl[outcomes_tbl["horizon"] == 5].set_index(key + ["arm"])["D_h"]
    d5_real = d5.xs("REAL", level="arm").rename("D5_real")
    d5_synth = d5.xs("SYNTHETIC", level="arm").rename("D5_synthetic")

    merged = merged.merge(d5_real.reset_index(), on=key, how="left")
    merged = merged.merge(d5_synth.reset_index(), on=key, how="left")
    merged = merged.merge(
        levels_tbl[key + ["real_isolated", "synthetic_isolated", "pair_separated"]], on=key, how="left")

    cond = (
        merged["touched_real"] & merged["touched_synth"]
        & (merged["touch_bucket_real"] == merged["touch_bucket_synth"])
        & merged["normalized_outcome_eligible_real"] & merged["normalized_outcome_eligible_synth"]
        & (merged["orientation_real"] == merged["orientation_synth"])
        & merged["orientation_real"].isin(["ABOVE_OPEN", "BELOW_OPEN"])
        & (merged["real_isolated"] == 1)
        & (merged["synthetic_isolated"] == 1)
        & (merged["pair_separated"] == 1)
        & merged["D5_real"].notna() & merged["D5_synthetic"].notna()
    )
    return merged[cond].copy()


def family_b_paired_d5(pairs_tbl: pd.DataFrame, all_instruments=None, all_level_ids=None) -> pd.DataFrame:
    """pairs_tbl: one row per (instrument, session_date, level_id) satisfying
    all Family B inclusion criteria, with columns D5_real, D5_synthetic.
    all_instruments/all_level_ids: full grid to guarantee every
    (instrument, level_id) cell is reported even with zero valid pairs
    (complete null-cell retention, no silent omission)."""
    rows = []
    groups = dict(iter(pairs_tbl.groupby(["instrument", "level_id"]))) if len(pairs_tbl) else {}
    keys = list(groups.keys())
    if all_instruments is not None and all_level_ids is not None:
        keys = list(itertools.product(all_instruments, all_level_ids))
    for instrument, level_id in keys:
        g = groups.get((instrument, level_id), pairs_tbl.iloc[0:0])
        n_pairs = len(g)
        row = {"instrument": instrument, "level_id": level_id, "n_valid_pairs": n_pairs}
        if n_pairs == 0:
            row["status"] = "no_valid_pairs"
            rows.append(row)
            continue
        diffs = (g["D5_real"] - g["D5_synthetic"]).to_numpy()
        n_nonzero = int(np.sum(diffs != 0))
        confirmatory = n_pairs >= FAMILY_B_MIN_PAIRS and n_nonzero >= FAMILY_B_MIN_NONZERO

        median_real = float(g["D5_real"].median())
        median_synth = float(g["D5_synthetic"].median())
        median_diff = float(np.median(diffs))
        mean_diff = float(np.mean(diffs))

        if n_nonzero > 0:
            try:
                stat, p_raw = stats.wilcoxon(diffs, zero_method="wilcox", alternative="two-sided",
                                             mode="auto")
            except ValueError:
                p_raw = 1.0
            hl = _hodges_lehmann(diffs)
            hl_ci_lo, hl_ci_hi = _hl_bootstrap_ci(diffs)
        else:
            p_raw = 1.0
            hl = 0.0
            hl_ci_lo, hl_ci_hi = 0.0, 0.0

        row.update({
            "n_nonzero_diff": n_nonzero, "median_D5_real": median_real,
            "median_D5_synthetic": median_synth, "median_paired_diff": median_diff,
            "mean_paired_diff_descriptive": mean_diff,
            "hodges_lehmann_estimate": hl, "hl_ci_lo": hl_ci_lo, "hl_ci_hi": hl_ci_hi,
            "p_raw": p_raw, "confirmatory_eligible": confirmatory,
            "status": "tested" if confirmatory else "underpowered_descriptive",
        })
        rows.append(row)

    out = pd.DataFrame(rows)
    if "confirmatory_eligible" not in out.columns:
        out["confirmatory_eligible"] = False
    if "p_raw" not in out.columns:
        out["p_raw"] = np.nan
    out["confirmatory_eligible"] = out["confirmatory_eligible"].fillna(False).astype(bool)
    out["p_bonferroni"] = np.minimum(1.0, out["p_raw"].fillna(1.0) * N_TESTS)
    out["bonferroni_alpha"] = 0.05 / N_TESTS
    out["bonferroni_survivor"] = out["confirmatory_eligible"] & (out["p_bonferroni"] < 0.05)
    return out


def _bh_adjust(pvals: np.ndarray) -> np.ndarray:
    """Standard Benjamini-Hochberg step-up adjustment (NaN-preserving)."""
    out = np.full(len(pvals), np.nan)
    valid_mask = ~np.isnan(pvals)
    p = pvals[valid_mask]
    m = len(p)
    if m == 0:
        return out
    order = np.argsort(p)
    ranked = p[order]
    ranks = np.arange(1, m + 1)
    adj_sorted = np.minimum.accumulate((ranked * m / ranks)[::-1])[::-1]
    adj_sorted = np.clip(adj_sorted, 0, 1)
    adj = np.empty(m)
    adj[order] = adj_sorted
    out[valid_mask] = adj
    return out


def secondary_bh(df: pd.DataFrame, pval_col: str, group_cols=("instrument", "outcome_name", "horizon")) -> pd.DataFrame:
    """Benjamini-Hochberg within each (instrument, outcome_name, horizon)
    family across the 38 level_ids. Adds p_bh column."""
    df = df.copy()
    df["p_bh"] = np.nan
    for _, g in df.groupby(list(group_cols)):
        df.loc[g.index, "p_bh"] = _bh_adjust(g[pval_col].to_numpy())
    return df
