"""Matched stratified permutation test.
See SPEC_SWEEP_FAILURE.md section 17.
"""
import numpy as np
import pandas as pd

N_PERMUTATIONS = 10000
SEED = 20260713


def stratified_permutation_test(df: pd.DataFrame, label_col: str, outcome_col: str,
                                 stratum_col: str, n_perms: int = N_PERMUTATIONS, seed: int = SEED):
    """df rows restricted to non-tied outcomes (ROTATION_FIRST/BREAKOUT_FIRST) only.
    Returns dict with observed stat, p-value, and per-label rotation rates."""
    rng = np.random.default_rng(seed)
    is_rot = (df[outcome_col] == "ROTATION_FIRST").to_numpy()
    labels = df[label_col].to_numpy()
    strata = df[stratum_col].to_numpy()

    def pooled_diff(lab):
        m_a = lab == "failed"
        m_b = lab == "successful"
        n_a, n_b = m_a.sum(), m_b.sum()
        if n_a == 0 or n_b == 0:
            return np.nan, n_a, n_b
        rate_a = is_rot[m_a].mean()
        rate_b = is_rot[m_b].mean()
        return rate_a - rate_b, n_a, n_b

    observed, n_failed, n_success = pooled_diff(labels)

    unique_strata = np.unique(strata)
    strata_idx = {s: np.where(strata == s)[0] for s in unique_strata}

    perm_stats = np.empty(n_perms)
    for p in range(n_perms):
        perm_labels = labels.copy()
        for s, idx in strata_idx.items():
            shuffled = rng.permutation(labels[idx])
            perm_labels[idx] = shuffled
        stat, _, _ = pooled_diff(perm_labels)
        perm_stats[p] = stat if not np.isnan(stat) else 0.0

    if np.isnan(observed):
        p_value = np.nan
    else:
        p_value = (np.sum(np.abs(perm_stats) >= abs(observed) - 1e-12) + 1) / (n_perms + 1)

    rate_failed = is_rot[labels == "failed"].mean() if n_failed else np.nan
    rate_success = is_rot[labels == "successful"].mean() if n_success else np.nan

    return {
        "observed_diff": observed, "p_value": p_value,
        "n_failed_nontied": int(n_failed), "n_successful_nontied": int(n_success),
        "rotation_rate_failed": rate_failed, "rotation_rate_successful": rate_success,
        "n_perms": n_perms, "seed": seed,
    }
