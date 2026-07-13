"""Matched stratified permutation test (reused pattern from the
sweep-and-failure generation). See SPEC_UNSUPPORTED_MOVE.md section 10.
"""
import numpy as np
import pandas as pd

N_PERMUTATIONS = 10000
SEED = 20260713


def stratified_permutation_test(df: pd.DataFrame, label_col: str, outcome_col: str,
                                 stratum_col: str, n_perms: int = N_PERMUTATIONS, seed: int = SEED):
    rng = np.random.default_rng(seed)
    is_closure = (df[outcome_col] == "RESIDUAL_CLOSURE_FIRST").to_numpy()
    labels = df[label_col].to_numpy()
    strata = df[stratum_col].to_numpy()

    def pooled_diff(lab):
        m_a = lab == "extreme"
        m_b = lab == "moderate"
        n_a, n_b = m_a.sum(), m_b.sum()
        if n_a == 0 or n_b == 0:
            return np.nan, n_a, n_b
        return is_closure[m_a].mean() - is_closure[m_b].mean(), n_a, n_b

    observed, n_extreme, n_moderate = pooled_diff(labels)

    unique_strata = np.unique(strata)
    strata_idx = {s: np.where(strata == s)[0] for s in unique_strata}

    perm_stats = np.empty(n_perms)
    for p in range(n_perms):
        perm_labels = labels.copy()
        for s, idx in strata_idx.items():
            perm_labels[idx] = rng.permutation(labels[idx])
        stat, _, _ = pooled_diff(perm_labels)
        perm_stats[p] = stat if not np.isnan(stat) else 0.0

    if np.isnan(observed):
        p_value = np.nan
    else:
        p_value = (np.sum(np.abs(perm_stats) >= abs(observed) - 1e-12) + 1) / (n_perms + 1)

    rate_extreme = is_closure[labels == "extreme"].mean() if n_extreme else np.nan
    rate_moderate = is_closure[labels == "moderate"].mean() if n_moderate else np.nan

    return {
        "observed_diff": observed, "p_value": p_value,
        "n_extreme": int(n_extreme), "n_moderate": int(n_moderate),
        "closure_rate_extreme": rate_extreme, "closure_rate_moderate": rate_moderate,
        "n_perms": n_perms, "seed": seed, "n_matched_strata": len(unique_strata),
    }
