import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from research.auction_value_rotation.src import permutation as perm


def test_poc_first_rate_excludes_ambiguous_neither_incomplete():
    outcomes = ["POC_FIRST", "POC_FIRST", "REDISCOVERY_FIRST", "SAME_BAR_AMBIGUOUS", "NEITHER", "INCOMPLETE_HORIZON"]
    rate = perm.poc_first_rate(outcomes)
    assert rate == pytest.approx(2 / 3)


def test_permutation_null_when_no_true_difference():
    rng = np.random.default_rng(1)
    n = 400
    strata = rng.integers(0, 5, size=n)
    labels = rng.random(n) < 0.5  # same generating rate for both "groups"
    treat_mask = rng.random(n) < 0.5
    result = perm.stratified_permutation_test(
        labels[treat_mask], strata[treat_mask], labels[~treat_mask], strata[~treat_mask],
        n_permutations=2000, seed=perm.SEED,
    )
    assert result["p_value"] > 0.01  # should not spuriously reject at typical thresholds


def test_permutation_detects_strong_true_difference():
    rng = np.random.default_rng(2)
    n_per_stratum = 100
    strata = np.repeat(np.arange(5), n_per_stratum)
    treat_labels = rng.random(len(strata)) < 0.80  # strong POC_FIRST rate
    control_labels = rng.random(len(strata)) < 0.20  # weak POC_FIRST rate
    result = perm.stratified_permutation_test(treat_labels, strata, control_labels, strata,
                                                n_permutations=2000, seed=perm.SEED)
    assert result["p_value"] < 0.01
    assert result["observed_diff"] > 0.4


def test_permutation_deterministic_with_fixed_seed():
    rng = np.random.default_rng(3)
    n = 200
    strata = rng.integers(0, 4, size=n)
    labels = rng.random(n) < 0.5
    treat_mask = rng.random(n) < 0.5
    r1 = perm.stratified_permutation_test(labels[treat_mask], strata[treat_mask], labels[~treat_mask], strata[~treat_mask],
                                           n_permutations=500, seed=42)
    r2 = perm.stratified_permutation_test(labels[treat_mask], strata[treat_mask], labels[~treat_mask], strata[~treat_mask],
                                           n_permutations=500, seed=42)
    assert r1["p_value"] == r2["p_value"]
    assert r1["observed_diff"] == r2["observed_diff"]


def test_permutation_no_common_strata_returns_nan():
    result = perm.stratified_permutation_test(
        np.array([True, False]), np.array([1, 1]), np.array([True, False]), np.array([2, 2]),
    )
    assert np.isnan(result["p_value"])
    assert result["n_strata"] == 0


def test_benjamini_hochberg_monotonic_and_bounded():
    p = [0.001, 0.02, 0.03, 0.5, 0.9, np.nan]
    q = perm.benjamini_hochberg(p)
    valid = [x for x in q if not np.isnan(x)]
    assert all(0.0 <= x <= 1.0 for x in valid)
    # sorted by p, q must be monotonic non-decreasing in the same order
    order = np.argsort([x if not np.isnan(x) else np.inf for x in p])
    ordered_q = [q[i] for i in order if not np.isnan(q[i])]
    assert ordered_q == sorted(ordered_q)
    assert np.isnan(q[-1])  # NaN input -> NaN output, excluded from correction


def test_benjamini_hochberg_all_nan():
    q = perm.benjamini_hochberg([np.nan, np.nan])
    assert all(np.isnan(x) for x in q)


def test_benjamini_hochberg_single_pvalue_equals_itself():
    q = perm.benjamini_hochberg([0.03])
    assert q[0] == pytest.approx(0.03)
