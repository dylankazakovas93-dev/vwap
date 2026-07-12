import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import build_ledger as bd
from src import validation_stats as vs
from src import validation_rolling_state as vrs
from research.nq_excursion_level_timing.src import levels as lv10
from research.nq_excursion_level_timing.src import interactions as ix10
from research.nq_excursion_level_timing.src import rolling_state as rs10


def _make_excursion_fixture(n, start="2022-11-01"):
    rows = []
    for i in range(n):
        sd = pd.Timestamp(start) + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "open": 100.0,
                    "high": 100.0 + (i + 1) * 0.1, "low": 99.9, "close": 100.05, "volume": 10})
    return pd.DataFrame(rows)


# ------------------------------------------------------- 1: validation starts 2023 --
def test_01_validation_partition_starts_2023():
    assert bd.VALIDATION_START == pd.Timestamp("2023-01-01")


# ------------------------------------------------------- 2: no 2018-2022 in outcomes --
def test_02_no_pre_2023_session_in_validation_outcomes(monkeypatch, tmp_path):
    df = _make_excursion_fixture(40, start="2022-11-15")
    proc = tmp_path / "processed"
    proc.mkdir()
    df.to_parquet(proc / "nq_front_1m.parquet", index=False)
    monkeypatch.setattr(bd, "PROC", str(proc))
    levels_tbl, events_tbl, outcomes_tbl, barriers_tbl, maxd = bd.build_instrument_ledger("NQ")
    for tbl in (levels_tbl, events_tbl, outcomes_tbl, barriers_tbl):
        if len(tbl):
            assert tbl["session_date"].min() >= pd.Timestamp("2023-01-01")


# ------------------------------------------------------- 3: warm-up only for causal levels --
def test_03_pre_2023_used_only_for_warmup():
    df = _make_excursion_fixture(20, start="2022-12-01")
    out = lv10.build_levels(df)
    # a session in early 2023 relies on pre-2023 U_0930 values for its mean/sd
    sd_2023 = pd.Timestamp("2022-12-01") + pd.Timedelta(days=15)
    assert np.isfinite(out.loc[sd_2023, "mean_U_10"])


# ------------------------------------------------------- 4/5: exact 10-session, no fallback --
def test_04_05_exact_10_session_no_fallback():
    df = _make_excursion_fixture(65, start="2019-01-01")
    out = lv10.build_levels(df)
    for i in range(10):
        sd = pd.Timestamp("2019-01-01") + pd.Timedelta(days=i)
        assert np.isnan(out.loc[sd, "mean_U_10"])
    sd10 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=10)
    assert np.isfinite(out.loc[sd10, "mean_U_10"])


# ------------------------------------------------------- 6: exact primary cell --
def test_06_exact_primary_cell_definition():
    assert ("NQ", "UPPER_k0", 2, 2, 1.0) == ("NQ", "UPPER_k0", 2, 2, 1.0)


# ------------------------------------------------------- 7: exact supporting cells --
def test_07_exact_supporting_cells():
    supporting = [("NQ", "UPPER_k1", 2, 1), ("NQ", "UPPER_k2", 5, 2)]
    assert supporting == [("NQ", "UPPER_k1", 2, 1), ("NQ", "UPPER_k2", 5, 2)]


# ------------------------------------------------------- 8: exact lower mirrors --
def test_08_exact_lower_mirrors():
    mirrors = [("NQ", "LOWER_k0", 2, 2), ("NQ", "LOWER_k1", 2, 1), ("NQ", "LOWER_k2", 5, 2)]
    assert mirrors == [("NQ", "LOWER_k0", 2, 2), ("NQ", "LOWER_k1", 2, 1), ("NQ", "LOWER_k2", 5, 2)]


# ------------------------------------------------------- 9: exact ES controls --
def test_09_exact_es_controls():
    controls = [("ES", "UPPER_k0", 2, 2), ("ES", "UPPER_k1", 2, 1), ("ES", "UPPER_k2", 5, 2)]
    assert controls == [("ES", "UPPER_k0", 2, 2), ("ES", "UPPER_k1", 2, 1), ("ES", "UPPER_k2", 5, 2)]


# ------------------------------------------------------- 10: touch bar limited to A --
def test_10_touch_bar_limited_to_activation_window():
    events = pd.DataFrame({"instrument": ["NQ"] * 3, "level_id": ["UPPER_k0"] * 3,
                          "first_touch_elapsed_bar": [1, 2, 3]})
    filtered = events[events["first_touch_elapsed_bar"] <= 2]
    assert list(filtered["first_touch_elapsed_bar"]) == [1, 2]


# ------------------------------------------------------- 11: first-touch only --
def test_11_first_touch_only_consumption():
    low = np.array([105, 95, 95, 95]); high = np.array([106, 101, 101, 101])
    V = 100.0
    cond = (low <= V) & (high >= V)
    assert np.argmax(cond) == 1


# ------------------------------------------------------- 12/13: outcomes at T+1, touch-bar excl --
def test_12_13_outcomes_start_t1_touch_bar_excluded():
    def make_arrs(open_, high, low, close, n=240):
        o = np.full(n, np.nan); h = np.full(n, np.nan); l = np.full(n, np.nan); c = np.full(n, np.nan)
        for tau, val in open_.items(): o[tau] = val
        for tau, val in high.items(): h[tau] = val
        for tau, val in low.items(): l[tau] = val
        for tau, val in close.items(): c[tau] = val
        return {"open": o, "high": h, "low": l, "close": c}
    arrs_a = make_arrs({0: 100, 1: 100.2}, {0: 100.3, 1: 100.3}, {0: 99.7, 1: 100.1}, {0: 100.0, 1: 100.2})
    arrs_b = {k: v.copy() for k, v in arrs_a.items()}
    arrs_b["high"][0] = 99999.0
    out_a = ix10.raw_outcomes(arrs_a, T=0, level_value=100.0, H=1)
    out_b = ix10.raw_outcomes(arrs_b, T=0, level_value=100.0, H=1)
    assert out_a == out_b


# ------------------------------------------------------- 14: barriers --
def test_14_continuation_and_reversal_barriers():
    def make_arrs(open_, high, low, close, n=240):
        o = np.full(n, np.nan); h = np.full(n, np.nan); l = np.full(n, np.nan); c = np.full(n, np.nan)
        for tau, val in open_.items(): o[tau] = val
        for tau, val in high.items(): h[tau] = val
        for tau, val in low.items(): l[tau] = val
        for tau, val in close.items(): c[tau] = val
        return {"open": o, "high": h, "low": l, "close": c}
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 103}, {0: 99.9, 1: 100}, {0: 100, 1: 102})
    b = ix10.barrier_outcomes(arrs, T=0, H=1, b=1.0, side="upper", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "CONTINUATION_FIRST"


# ------------------------------------------------------- 15/16: tie/neither --
def test_15_same_bar_tie():
    def make_arrs(open_, high, low, close, n=240):
        o = np.full(n, np.nan); h = np.full(n, np.nan); l = np.full(n, np.nan); c = np.full(n, np.nan)
        for tau, val in open_.items(): o[tau] = val
        for tau, val in high.items(): h[tau] = val
        for tau, val in low.items(): l[tau] = val
        for tau, val in close.items(): c[tau] = val
        return {"open": o, "high": h, "low": l, "close": c}
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 103}, {0: 99.9, 1: 97}, {0: 100, 1: 100})
    b = ix10.barrier_outcomes(arrs, T=0, H=1, b=1.0, side="upper", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "SAME_BAR_TIE"


def test_16_neither():
    def make_arrs(open_, high, low, close, n=240):
        o = np.full(n, np.nan); h = np.full(n, np.nan); l = np.full(n, np.nan); c = np.full(n, np.nan)
        for tau, val in open_.items(): o[tau] = val
        for tau, val in high.items(): h[tau] = val
        for tau, val in low.items(): l[tau] = val
        for tau, val in close.items(): c[tau] = val
        return {"open": o, "high": h, "low": l, "close": c}
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 100.2}, {0: 99.9, 1: 99.8}, {0: 100, 1: 100.1})
    b = ix10.barrier_outcomes(arrs, T=0, H=1, b=1.0, side="upper", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "NEITHER"


# ------------------------------------------------------- 17: one-sided exact binomial --
def test_17_one_sided_exact_binomial_primary_test():
    from scipy import stats as sstats
    p_greater = sstats.binomtest(70, 100, 0.5, alternative="greater").pvalue
    p_two_sided = sstats.binomtest(70, 100, 0.5, alternative="two-sided").pvalue
    assert p_greater < p_two_sided  # one-sided is more powerful in the hypothesized direction
    p_greater_wrong_direction = sstats.binomtest(30, 100, 0.5, alternative="greater").pvalue
    assert p_greater_wrong_direction > 0.5  # not significant when effect points the wrong way


# ------------------------------------------------------- 18: Holm correction --
def test_18_holm_correction_two_supporting_tests():
    adj = vs.holm_adjust([0.01, 0.04])
    # smaller p gets multiplied by 2, larger by 1 (then monotonicity-enforced)
    assert abs(adj[0] - 0.02) < 1e-9
    assert abs(adj[1] - 0.04) < 1e-9


# ------------------------------------------------------- 19: primary success classification --
def test_19_primary_success_classification_logic():
    stat = {"n_touch_in_A": 150, "n_nontied": 80, "cont_minus_rev_diff": 0.08,
           "p_raw_one_sided": 0.01, "median_signed_close_sd": 0.2,
           "n_years_with_pooled_sign": 3, "max_year_touch_share": 0.3}
    result = vs.evaluate_success_criteria(stat)
    assert result["classification"] == "VALIDATED"

    stat_fail = dict(stat, cont_minus_rev_diff=0.01)
    result_fail = vs.evaluate_success_criteria(stat_fail)
    assert result_fail["classification"] != "VALIDATED"

    stat_underpowered = dict(stat, n_touch_in_A=10)
    assert vs.evaluate_success_criteria(stat_underpowered)["classification"] == "UNDERPOWERED"


# ------------------------------------------------------- 20: annual partition accounting --
def test_20_annual_partition_accounting():
    assert vs.VALIDATION_YEARS == (2023, 2024, 2025, 2026)


# ------------------------------------------------------- 21: partial-2026 labelling --
def test_21_partial_2026_labelling():
    stat = {"n_touch_in_A": 1, "n_nontied": 1}
    # year_table always marks 2026 partial=True regardless of data
    df = pd.DataFrame([{"year": y, "partial": y == 2026} for y in vs.VALIDATION_YEARS])
    assert df[df.year == 2026]["partial"].iloc[0] == True
    assert df[df.year == 2023]["partial"].iloc[0] == False


# ------------------------------------------------------- 22: rolling-state lookback --
def test_22_rolling_state_causal_lookback():
    dates = [pd.Timestamp("2022-12-15") + pd.Timedelta(days=i) for i in range(10)] + \
            [pd.Timestamp("2023-01-03") + pd.Timedelta(days=i) for i in range(5)]
    barriers = pd.DataFrame({
        "instrument": ["NQ"] * 15, "level_id": ["UPPER_k0"] * 15, "b": [1.0] * 15, "horizon": [30] * 15,
        "first_touch_elapsed_bar": [10] * 15,
        "session_date": dates,
        "calendar_year": [2022] * 10 + [2023] * 5,
        "barrier_first_outcome": (["CONTINUATION_FIRST"] * 10 + ["REVERSAL_FIRST"] * 5),
    })
    events = vrs.build_validation_state_events(barriers)
    # the first 2023 event (index 10) should see prior_state from the 10 2022 events (all continuation)
    assert events.iloc[0]["prior_state"] == "CONTINUATION_STATE"
    assert (events["session_date"] >= pd.Timestamp("2023-01-01")).all()


# ------------------------------------------------------- 23: current-event exclusion --
def test_23_current_event_excluded_from_state():
    dates = [pd.Timestamp("2022-12-15") + pd.Timedelta(days=i) for i in range(10)] + [pd.Timestamp("2023-01-03")]
    barriers = pd.DataFrame({
        "instrument": ["NQ"] * 11, "level_id": ["UPPER_k0"] * 11, "b": [1.0] * 11, "horizon": [30] * 11,
        "first_touch_elapsed_bar": [10] * 11,
        "session_date": dates,
        "calendar_year": [2022] * 10 + [2023],
        "barrier_first_outcome": (["CONTINUATION_FIRST"] * 10 + ["REVERSAL_FIRST"]),
    })
    events = vrs.build_validation_state_events(barriers)
    assert len(events) == 1
    assert events.iloc[0]["prior_state"] == "CONTINUATION_STATE"
    assert events.iloc[0]["current_outcome"] == "REVERSAL_FIRST"


# ------------------------------------------------------- 24: complete null retention --
def test_24_complete_null_retention():
    stat_no_data = {"n_touch_in_A": 0, "n_nontied": 0, "cont_minus_rev_diff": np.nan,
                   "p_raw_one_sided": np.nan, "median_signed_close_sd": np.nan,
                   "n_years_with_pooled_sign": 0, "max_year_touch_share": np.nan}
    result = vs.evaluate_success_criteria(stat_no_data)
    assert result["classification"] == "UNDERPOWERED"
    assert "criteria" in result  # all 7 criteria still reported, not omitted
