"""Matched stratified permutation test + Benjamini-Hochberg correction.
See SPEC_AUCTION_VALUE.md section 8. Seed and permutation count are
frozen constants reused from prior generations.
"""
import numpy as np

SEED = 20260713
N_PERMUTATIONS = 10000


def poc_first_rate(outcomes: list) -> float:
    """Rate of POC_FIRST among resolved, non-ambiguous outcomes
    (excludes SAME_BAR_AMBIGUOUS, NEITHER, INCOMPLETE_HORIZON)."""
    resolved = [o for o in outcomes if o in ("POC_FIRST", "REDISCOVERY_FIRST")]
    if len(resolved) == 0:
        return np.nan
    return sum(1 for o in resolved if o == "POC_FIRST") / len(resolved)


def stratified_permutation_test(treat_labels: np.ndarray, treat_strata: np.ndarray,
                                  control_labels: np.ndarray, control_strata: np.ndarray,
                                  n_permutations: int = N_PERMUTATIONS, seed: int = SEED) -> dict:
    """Two-sided matched stratified permutation test on the difference in
    POC_FIRST rate (treatment minus control), resolved/non-ambiguous
    outcomes only. Within each matched stratum, the treatment/control
    role labels are randomly reassigned among that stratum's pooled
    units, holding the stratum's treatment/control group sizes fixed
    (the standard matched-permutation null); the pooled (stratum-size
    weighted) rate difference is recomputed each draw. Vectorized across
    all `n_permutations` draws simultaneously, per stratum, so this stays
    tractable across a large grid of cells.

    `*_labels` are boolean-like arrays: True = POC_FIRST, False =
    REDISCOVERY_FIRST (ambiguous/neither/incomplete already excluded by
    the caller). `*_strata` are matched-stratum ids aligned to labels.
    """
    rng = np.random.default_rng(seed)
    treat_labels = np.asarray(treat_labels, dtype=bool)
    control_labels = np.asarray(control_labels, dtype=bool)
    treat_strata = np.asarray(treat_strata)
    control_strata = np.asarray(control_strata)

    common_strata = sorted(set(treat_strata.tolist()) & set(control_strata.tolist()))
    if len(common_strata) == 0:
        return {"n_treat": len(treat_labels), "n_control": len(control_labels),
                "observed_diff": np.nan, "p_value": np.nan, "n_strata": 0}

    num_t_obs, den_t_obs, num_c_obs, den_c_obs = 0, 0, 0, 0
    perm_num_t = np.zeros(n_permutations)
    perm_num_c = np.zeros(n_permutations)
    den_t, den_c = 0, 0

    for s in common_strata:
        tm = treat_strata == s
        cm = control_strata == s
        nt, nc = int(tm.sum()), int(cm.sum())
        if nt == 0 or nc == 0:
            continue
        labels_s = np.concatenate([treat_labels[tm], control_labels[cm]])
        n_s = nt + nc

        num_t_obs += treat_labels[tm].sum()
        num_c_obs += control_labels[cm].sum()
        den_t += nt
        den_c += nc

        rand = rng.random((n_permutations, n_s))
        order = np.argsort(rand, axis=1)
        top = order[:, :nt]
        selected = labels_s[top]  # (n_permutations, nt) -- permuted "treatment" role
        perm_num_t += selected.sum(axis=1)
        perm_num_c += labels_s.sum() - selected.sum(axis=1)

    if den_t == 0 or den_c == 0:
        return {"n_treat": len(treat_labels), "n_control": len(control_labels),
                "observed_diff": np.nan, "p_value": np.nan, "n_strata": 0}

    observed = (num_t_obs / den_t) - (num_c_obs / den_c)
    perm_diffs = (perm_num_t / den_t) - (perm_num_c / den_c)
    p_value = float((np.sum(np.abs(perm_diffs) >= abs(observed) - 1e-12) + 1) / (n_permutations + 1))

    return {
        "n_treat": int(len(treat_labels)), "n_control": int(len(control_labels)),
        "observed_diff": float(observed), "p_value": p_value, "n_strata": len(common_strata),
    }


def benjamini_hochberg(p_values: list) -> list:
    """Returns q-values (BH-adjusted) in the same order as input
    `p_values`. NaN p-values pass through as NaN q-values and do not
    participate in the correction (do not count toward m)."""
    p_arr = np.asarray(p_values, dtype=float)
    n = len(p_arr)
    q = np.full(n, np.nan)
    valid_idx = np.where(~np.isnan(p_arr))[0]
    m = len(valid_idx)
    if m == 0:
        return q.tolist()
    order = valid_idx[np.argsort(p_arr[valid_idx])]
    ranked_p = p_arr[order]
    ranks = np.arange(1, m + 1)
    raw_q = ranked_p * m / ranks
    # enforce monotonicity (BH step-up): cumulative minimum from the largest rank down
    adj_q = np.minimum.accumulate(raw_q[::-1])[::-1]
    adj_q = np.clip(adj_q, 0.0, 1.0)
    q[order] = adj_q
    return q.tolist()
