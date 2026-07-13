"""Causal per-clock-slot return normalization and frozen-orientation OLS
regression (NQ = alpha + beta*ES + residual), trailing 60 valid prior
occurrences, current excluded, no shorter-history fallback.
See SPEC_UNSUPPORTED_MOVE.md sections 3-4.
"""
import numpy as np
import pandas as pd

REQUIRED_PRIOR = 60


def _causal_stats_for_group(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("session_date").reset_index(drop=True)
    es = g["es_ret"].to_numpy()
    nq = g["nq_ret"].to_numpy()
    n = len(es)

    es_mean = np.full(n, np.nan)
    es_std = np.full(n, np.nan)
    nq_mean = np.full(n, np.nan)
    nq_std = np.full(n, np.nan)
    beta = np.full(n, np.nan)
    alpha = np.full(n, np.nan)
    resid = np.full(n, np.nan)
    es_z = np.full(n, np.nan)
    nq_z = np.full(n, np.nan)

    for i in range(REQUIRED_PRIOR, n):
        we = es[i - REQUIRED_PRIOR : i]
        wn = nq[i - REQUIRED_PRIOR : i]
        em, nm = we.mean(), wn.mean()
        es_mean[i], nq_mean[i] = em, nm
        es_std[i] = we.std(ddof=1)
        nq_std[i] = wn.std(ddof=1)
        var_es = ((we - em) ** 2).sum() / (REQUIRED_PRIOR - 1)
        cov_esnq = ((we - em) * (wn - nm)).sum() / (REQUIRED_PRIOR - 1)
        if var_es > 0:
            b = cov_esnq / var_es
            a = nm - b * em
            beta[i], alpha[i] = b, a
            resid[i] = nq[i] - (a + b * es[i])
        if es_std[i] > 0:
            es_z[i] = (es[i] - em) / es_std[i]
        if nq_std[i] > 0:
            nq_z[i] = (nq[i] - nm) / nq_std[i]

    resid_std = np.full(n, np.nan)
    resid_z = np.full(n, np.nan)
    es_lead_frac = np.full(n, np.nan)
    for i in range(2 * REQUIRED_PRIOR, n):
        hist_resid = resid[i - REQUIRED_PRIOR : i]
        if not np.any(np.isnan(hist_resid)):
            s = hist_resid.std(ddof=1)
            resid_std[i] = s
            if s > 0 and not np.isnan(resid[i]):
                resid_z[i] = resid[i] / s
        hist_es_z = es_z[i - REQUIRED_PRIOR : i]
        hist_nq_z = nq_z[i - REQUIRED_PRIOR : i]
        valid_mask = ~np.isnan(hist_es_z) & ~np.isnan(hist_nq_z)
        n_valid = valid_mask.sum()
        if n_valid > 0:
            tie_mask = np.abs(hist_es_z[valid_mask]) == np.abs(hist_nq_z[valid_mask])
            n_nontied = n_valid - tie_mask.sum()
            if n_nontied > 0:
                es_lead = (np.abs(hist_es_z[valid_mask]) > np.abs(hist_nq_z[valid_mask])).sum()
                es_lead_frac[i] = es_lead / n_nontied

    g["es_ret_mean"], g["es_ret_std"], g["es_ret_z"] = es_mean, es_std, es_z
    g["nq_ret_mean"], g["nq_ret_std"], g["nq_ret_z"] = nq_mean, nq_std, nq_z
    g["alpha"], g["beta"], g["residual"] = alpha, beta, resid
    g["residual_std"], g["residual_z"] = resid_std, resid_z
    g["historical_es_lead_fraction"] = es_lead_frac
    return g


def add_causal_normalization_and_regression(endpoints: pd.DataFrame) -> pd.DataFrame:
    groups = []
    for _, g in endpoints.groupby(["leg", "et_minute"], sort=False):
        groups.append(_causal_stats_for_group(g))
    return pd.concat(groups, ignore_index=True)
