import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from research.auction_value_rotation.src import classification as cls


def test_compute_frozen_bands_terciles():
    rows = [{"va_width": v, "freshness_hours": v, "poc_distance_pct": v / 10, "confirmation_atr20": v} for v in range(1, 10)]
    bands = cls.compute_frozen_bands(rows)
    lo, hi = bands["va_width"]
    assert lo == pytest.approx(np.quantile(range(1, 10), 1 / 3))
    assert hi == pytest.approx(np.quantile(range(1, 10), 2 / 3))


def test_band_index_buckets_correctly():
    cutoffs = (2.0, 5.0)
    assert cls._band_index(1.0, cutoffs) == 0
    assert cls._band_index(2.0, cutoffs) == 0
    assert cls._band_index(3.0, cutoffs) == 1
    assert cls._band_index(5.0, cutoffs) == 1
    assert cls._band_index(6.0, cutoffs) == 2
    assert cls._band_index(np.nan, cutoffs) == -1


def test_clock_bucket_hour_extraction():
    assert cls.clock_bucket(9 * 60 + 45) == 9
    assert cls.clock_bucket(23 * 60 + 59) == 23
    assert cls.clock_bucket(0) == 0


def test_stratum_id_stable_and_distinguishes_bands():
    bands = {"va_width": (1.0, 2.0), "freshness": (1.0, 2.0), "poc_distance": (0.1, 0.2), "atr20": (1.0, 2.0)}
    row_a = {"confirmation_et_minute": 600, "va_width": 0.5, "freshness_hours": 0.5, "poc_distance_pct": 0.05, "confirmation_atr20": 0.5}
    row_b = {"confirmation_et_minute": 600, "va_width": 2.5, "freshness_hours": 0.5, "poc_distance_pct": 0.05, "confirmation_atr20": 0.5}
    assert cls.stratum_id(row_a, bands) != cls.stratum_id(row_b, bands)
    assert cls.stratum_id(row_a, bands) == cls.stratum_id(dict(row_a), bands)


def test_dev_year_of_uses_target_session_date():
    row = {"target_session_date": pd.Timestamp("2020-06-15"), "confirmation_ts": pd.Timestamp("2020-06-16")}
    assert cls.dev_year_of(row) == 2020


def test_evaluate_cell_basic_pooled_diff():
    bands = {"va_width": (np.nan, np.nan), "freshness": (np.nan, np.nan), "poc_distance": (np.nan, np.nan), "atr20": (np.nan, np.nan)}
    treat = [
        {"outcome_h60": "POC_FIRST", "outcome_h30": "POC_FIRST", "outcome_h120": "POC_FIRST", "stratum": "0",
         "target_session_date": pd.Timestamp(f"2018-01-0{i%5+1}")}
        for i in range(8)
    ] + [
        {"outcome_h60": "REDISCOVERY_FIRST", "outcome_h30": "REDISCOVERY_FIRST", "outcome_h120": "REDISCOVERY_FIRST", "stratum": "0",
         "target_session_date": pd.Timestamp(f"2018-01-0{i%5+1}")}
        for i in range(2)
    ]
    control = [
        {"outcome_h60": "POC_FIRST", "outcome_h30": "POC_FIRST", "outcome_h120": "POC_FIRST", "stratum": "0",
         "target_session_date": pd.Timestamp(f"2018-01-0{i%5+1}")}
        for i in range(3)
    ] + [
        {"outcome_h60": "REDISCOVERY_FIRST", "outcome_h30": "REDISCOVERY_FIRST", "outcome_h120": "REDISCOVERY_FIRST", "stratum": "0",
         "target_session_date": pd.Timestamp(f"2018-01-0{i%5+1}")}
        for i in range(7)
    ]
    result = cls.evaluate_cell(treat, control, dev_years=(2018,))
    assert result["n_treat_all"] == 10
    assert result["pooled_diff_h60"] == pytest.approx(0.8 - 0.3)


def test_evaluate_cell_no_common_strata_gives_nan_diff():
    treat = [{"outcome_h60": "POC_FIRST", "stratum": "0", "target_session_date": pd.Timestamp("2018-01-01")}]
    control = [{"outcome_h60": "POC_FIRST", "stratum": "1", "target_session_date": pd.Timestamp("2018-01-01")}]
    result = cls.evaluate_cell(treat, control, dev_years=(2018,))
    assert np.isnan(result["pooled_diff_h60"])


def test_check_poc_distance_matching_flags_artifact():
    treat_close = [{"poc_distance_pct": 0.01} for _ in range(5)]
    control_far = [{"poc_distance_pct": 0.5} for _ in range(5)]
    assert cls.check_poc_distance_matching(treat_close, control_far) is False
    assert cls.check_poc_distance_matching(control_far, treat_close) is True


def test_apply_bh_within_mapping_assigns_q_and_skips_none():
    cells = [
        {"permutation": {"p_value": 0.001}}, {"permutation": {"p_value": 0.04}},
        {"permutation": None}, {"permutation": {"p_value": 0.5}},
    ]
    out = cls.apply_bh_within_mapping(cells)
    assert np.isnan(out[2]["bh_q"])
    assert out[0]["bh_q"] <= out[1]["bh_q"] <= out[3]["bh_q"]


def test_gate_12_criteria_all_pass():
    cell = {
        "n_treat_all": 400, "n_control_matched": 200, "positive_years": 4,
        "pooled_diff_h60": 0.10, "worst_year_effect": -0.01, "bh_q": 0.05,
        "pooled_diff_h30": 0.08, "max_year_share": 0.3,
    }
    gate = cls.gate_12_criteria(cell, poc_distance_ok=True, bin_width_support=2, model_support=1, adjacent_sign_support=2)
    assert gate["ALL_PASS"] is True


def test_gate_12_criteria_fails_on_insufficient_n():
    cell = {
        "n_treat_all": 10, "n_control_matched": 200, "positive_years": 4,
        "pooled_diff_h60": 0.10, "worst_year_effect": -0.01, "bh_q": 0.05,
        "pooled_diff_h30": 0.08, "max_year_share": 0.3,
    }
    gate = cls.gate_12_criteria(cell, poc_distance_ok=True, bin_width_support=2, model_support=1, adjacent_sign_support=2)
    assert gate["ALL_PASS"] is False
    assert gate["c01_min_treat_300"] is False
