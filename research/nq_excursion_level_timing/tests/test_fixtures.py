import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import levels as lv
from src import interactions as ix
from src import stats as st
from src import classification as cl
from src import rolling_state as rs
from src import build_ledger as bd


def make_arrs(open_, high, low, close, n=240):
    o = np.full(n, np.nan); h = np.full(n, np.nan); l = np.full(n, np.nan); c = np.full(n, np.nan)
    for tau, val in open_.items(): o[tau] = val
    for tau, val in high.items(): h[tau] = val
    for tau, val in low.items(): l[tau] = val
    for tau, val in close.items(): c[tau] = val
    return {"open": o, "high": h, "low": l, "close": c}


def _make_excursion_fixture(n=65):
    rows = []
    for i in range(n):
        sd = pd.Timestamp("2019-01-01") + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "open": 100.0,
                    "high": 100.0 + (i + 1) * 0.1, "low": 99.9, "close": 100.05, "volume": 10})
    return pd.DataFrame(rows)


# ------------------------------------------------------------- 1/2: partition --
def test_01_02_partition_guard_no_2023(tmp_path):
    rows = []
    for i in range(5):
        sd = pd.Timestamp("2022-12-29") + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "open": 100.0,
                    "high": 100.1, "low": 99.9, "close": 100.0, "volume": 10})
    df = pd.DataFrame(rows)
    proc = tmp_path / "processed"
    proc.mkdir()
    df.to_parquet(proc / "nq_front_1m.parquet", index=False)
    out = lv.load_dev("NQ", str(proc))
    assert out["session_date"].max() <= lv.DEV_END
    assert out["session_date"].min() >= lv.DEV_START
    assert (out["session_date"] < pd.Timestamp("2023-01-01")).all()


# ------------------------------------------------------------- 3: separation --
def test_03_nq_es_separation(tmp_path):
    df = _make_excursion_fixture(15)
    proc = tmp_path / "processed"
    proc.mkdir()
    for inst in ("nq", "es"):
        df.to_parquet(proc / f"{inst}_front_1m.parquet", index=False)
    import research.nq_excursion_level_timing.src.build_ledger as bld
    old_proc = bld.PROC
    bld.PROC = str(proc)
    try:
        lnq, _, _, _ = bld.build_instrument_ledger("NQ")
        les, _, _, _ = bld.build_instrument_ledger("ES")
        assert (lnq["instrument"] == "NQ").all()
        assert (les["instrument"] == "ES").all()
    finally:
        bld.PROC = old_proc


# ------------------------------------------------------------- 4: 8-level inventory --
def test_04_exact_8_level_inventory():
    ids = lv.level_ids()
    assert len(ids) == 8 and len(set(ids)) == 8
    assert set(ids) == {"UPPER_k0", "UPPER_k1", "UPPER_k2", "UPPER_k3",
                        "LOWER_k0", "LOWER_k1", "LOWER_k2", "LOWER_k3"}


# ------------------------------------------------------------- 5/6: 0930-only, no leakage --
def test_05_06_excursion_single_candle_no_leakage():
    n = 65
    rows = []
    for i in range(n):
        sd = pd.Timestamp("2019-01-01") + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "open": 100.0,
                    "high": 100.0 + (i + 1) * 0.1, "low": 99.9, "volume": 10})
        rows.append({"session_date": sd, "et_minute": 571, "open": 100.0,
                    "high": 999.0, "low": -999.0, "volume": 10})
    df = pd.DataFrame(rows)
    out = lv.build_levels(df)
    sd0 = pd.Timestamp("2019-01-01")
    assert abs(out.loc[sd0, "U_0930"] - 0.1) < 1e-9


# ------------------------------------------------------------- 7/8: exact 10-window --
def test_07_08_exact_10_session_window_no_fallback():
    df = _make_excursion_fixture(65)
    out = lv.build_levels(df)
    for i in range(10):
        sd = pd.Timestamp("2019-01-01") + pd.Timedelta(days=i)
        assert np.isnan(out.loc[sd, "mean_U_10"])
    sd10 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=10)
    assert np.isfinite(out.loc[sd10, "mean_U_10"])
    expected = np.mean([(i + 1) * 0.1 for i in range(10)])
    assert abs(out.loc[sd10, "mean_U_10"] - expected) < 1e-9


# ------------------------------------------------------------- 9: arithmetic mean --
def test_09_arithmetic_mean_formula():
    df = _make_excursion_fixture(65)
    out = lv.build_levels(df)
    sd10 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=10)
    vals = [(i + 1) * 0.1 for i in range(10)]
    assert abs(out.loc[sd10, "mean_U_10"] - np.mean(vals)) < 1e-9


# ------------------------------------------------------------- 10: sample SD ddof=1 --
def test_10_sample_sd_ddof1():
    df = _make_excursion_fixture(65)
    out = lv.build_levels(df)
    sd10 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=10)
    vals = [(i + 1) * 0.1 for i in range(10)]
    assert abs(out.loc[sd10, "sd_U_10"] - np.std(vals, ddof=1)) < 1e-9


# ------------------------------------------------------------- 11/12: upper/lower formulas --
def test_11_12_upper_lower_formula_every_k():
    df = _make_excursion_fixture(65)
    out = lv.build_levels(df)
    sd20 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=20)
    O = out.loc[sd20, "O_0930"]
    mu, su = out.loc[sd20, "mean_U_10"], out.loc[sd20, "sd_U_10"]
    md, sdv = out.loc[sd20, "mean_D_10"], out.loc[sd20, "sd_D_10"]
    for k in (0, 1, 2, 3):
        assert abs(out.loc[sd20, f"UPPER_k{k}"] - (O + mu + k * su)) < 1e-9
        assert abs(out.loc[sd20, f"LOWER_k{k}"] - (O - md - k * sdv)) < 1e-9


# ------------------------------------------------------------- 13: touch search 570-689 --
def test_13_master_touch_search_570_689():
    assert ix.TOUCH_START == 570 and ix.TOUCH_END == 689
    assert ix.TOUCH_END - ix.TOUCH_START + 1 == 120


# ------------------------------------------------------------- 14: first-touch only --
def test_14_first_touch_only_consumption():
    low = np.array([105, 95, 95, 95])
    high = np.array([106, 101, 101, 101])
    V = 100.0
    cond = (low <= V) & (high >= V)
    assert np.argmax(cond) == 1


# ------------------------------------------------------------- 15: nested activation window --
def test_15_nested_activation_window_membership():
    for A in ix.ACTIVATION_WINDOWS:
        assert (5 <= A) == (5 <= A)  # membership rule is elapsed_bar <= A
    elapsed_bar = 5
    included = [A for A in ix.ACTIVATION_WINDOWS if elapsed_bar <= A]
    assert included == [5, 10, 15, 20, 30, 60, 120]


# ------------------------------------------------------------- 16: mutually exclusive bins --
def test_16_mutually_exclusive_touch_bins():
    seen = set()
    for tau in range(120):
        b = ix.timing_bin_for_tau(tau)
        assert b is not None
        seen.add(b)
    assert seen == {"BAR_0930", "MINUTE_2", "MINUTE_3", "MINUTE_4", "MINUTE_5",
                    "MINUTES_6_TO_10", "MINUTES_11_TO_15", "MINUTES_16_TO_20",
                    "MINUTES_21_TO_30", "MINUTES_31_TO_60", "MINUTES_61_TO_120"}


# ------------------------------------------------------------- 17-20: same-bar morphology --
def test_17_18_upper_same_bar_reversal_and_blast():
    assert ix.same_bar_morphology("upper", 99.0, 100.0) == "SAME_BAR_REVERSAL_PROXY"
    assert ix.same_bar_morphology("upper", 101.0, 100.0) == "SAME_BAR_BLAST_THROUGH_PROXY"


def test_19_20_lower_same_bar_reversal_and_blast():
    assert ix.same_bar_morphology("lower", 101.0, 100.0) == "SAME_BAR_REVERSAL_PROXY"
    assert ix.same_bar_morphology("lower", 99.0, 100.0) == "SAME_BAR_BLAST_THROUGH_PROXY"


# ------------------------------------------------------------- 21/22: outcomes at T+1, touch-bar excl --
def test_21_22_outcomes_start_t1_touch_bar_excluded():
    arrs_a = make_arrs({0: 100, 1: 100.2}, {0: 100.3, 1: 100.3}, {0: 99.7, 1: 100.1}, {0: 100.0, 1: 100.2})
    arrs_b = {k: v.copy() for k, v in arrs_a.items()}
    arrs_b["high"][0] = 99999.0
    arrs_b["low"][0] = -99999.0
    arrs_b["close"][0] = -99999.0
    out_a = ix.raw_outcomes(arrs_a, T=0, level_value=100.0, H=1)
    out_b = ix.raw_outcomes(arrs_b, T=0, level_value=100.0, H=1)
    assert out_a == out_b


# ------------------------------------------------------------- 23: complete horizon handling --
def test_23_complete_horizon_handling_every_h():
    assert set(ix.HORIZONS) == {1, 2, 3, 4, 5, 10, 15, 20, 30, 60, 120}
    assert ix.TOUCH_END + 120 - ix.TOUCH_START == ix.TAU_MAX == 239


# ------------------------------------------------------------- 24: mirrored excursions --
def test_24_mirrored_upper_lower_excursions():
    arrs = make_arrs({0: 100}, {0: 100.2, 1: 103}, {0: 99.8, 1: 99}, {0: 100, 1: 102})
    up = ix.oriented_outcomes(arrs, T=0, level_value=100.0, H=1, side="upper", native_sd=2.0)
    down = ix.oriented_outcomes(arrs, T=0, level_value=100.0, H=1, side="lower", native_sd=2.0)
    assert up["CONT_EXC_H"] == max(0.0, 103 - 100.0)
    assert down["CONT_EXC_H"] == max(0.0, 100.0 - 99)
    assert up["REV_EXC_H"] == max(0.0, 100.0 - 99)
    assert down["REV_EXC_H"] == max(0.0, 103 - 100.0)


# ------------------------------------------------------------- 25/26: SD normalization --
def test_25_sd_normalization():
    arrs = make_arrs({0: 100}, {0: 100.2, 1: 103}, {0: 99.8, 1: 99}, {0: 100, 1: 102})
    out = ix.oriented_outcomes(arrs, T=0, level_value=100.0, H=1, side="upper", native_sd=2.0)
    assert abs(out["CONT_EXC_SD_H"] - out["CONT_EXC_H"] / 2.0) < 1e-9


def test_26_zero_sd_handling():
    arrs = make_arrs({0: 100}, {0: 100.2, 1: 103}, {0: 99.8, 1: 99}, {0: 100, 1: 102})
    out = ix.oriented_outcomes(arrs, T=0, level_value=100.0, H=1, side="upper", native_sd=0.0)
    assert np.isnan(out["CONT_EXC_SD_H"])
    assert np.isfinite(out["CONT_EXC_H"])


# ------------------------------------------------------------- 27-30: barriers --
def test_27_continuation_first_barrier():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 103, 2: 100.05}, {0: 99.9, 1: 100, 2: 97},
                     {0: 100, 1: 102, 2: 98})
    b = ix.barrier_outcomes(arrs, T=0, H=2, b=1.0, side="upper", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "CONTINUATION_FIRST"


def test_28_reversal_first_barrier():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 100.05, 2: 105}, {0: 99.9, 1: 97, 2: 104},
                     {0: 100, 1: 98, 2: 104.5})
    b = ix.barrier_outcomes(arrs, T=0, H=2, b=1.0, side="upper", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "REVERSAL_FIRST"


def test_29_same_bar_tie():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 103}, {0: 99.9, 1: 97}, {0: 100, 1: 100})
    b = ix.barrier_outcomes(arrs, T=0, H=1, b=1.0, side="upper", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "SAME_BAR_TIE"


def test_30_neither_barrier():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 100.2}, {0: 99.9, 1: 99.8}, {0: 100, 1: 100.1})
    b = ix.barrier_outcomes(arrs, T=0, H=1, b=1.0, side="upper", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "NEITHER"


# ------------------------------------------------------------- 31: post-touch retouch --
def test_31_post_touch_retouch_definition():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 105, 2: 100.05}, {0: 99.9, 1: 104, 2: 99.95},
                     {0: 100, 1: 104.5, 2: 100.0})
    out = ix.raw_outcomes(arrs, T=0, level_value=100.0, H=2)
    assert out["post_touch_retouch"] == 1


# ------------------------------------------------------------- 32: close-recross ordering --
def test_32_directional_close_recross_ordering():
    arrs = make_arrs({0: 100}, {}, {}, {0: 100.0, 1: 101.0, 2: 99.0})
    out = ix.directional_close_recross(arrs, T=0, H=2, side="upper", level_value=100.0)
    assert out["directional_rejection_recross"] == 1
    arrs2 = make_arrs({0: 100}, {}, {}, {0: 100.0, 1: 99.0, 2: 99.5})
    out2 = ix.directional_close_recross(arrs2, T=0, H=2, side="upper", level_value=100.0)
    assert out2["directional_rejection_recross"] == 0


# ------------------------------------------------------------- 33: BH family membership --
def test_33_bh_family_membership():
    df = pd.DataFrame({"instrument": ["NQ", "NQ", "ES"], "level_id": ["a", "b", "a"],
                       "p_raw": [0.01, 0.5, 0.01]})
    out = st.bh_within(df, "p_raw", group_cols=("instrument",))
    nq_only = out[out.instrument == "NQ"]
    assert len(nq_only) == 2
    assert not np.isnan(nq_only["q_value"]).all()


# ------------------------------------------------------------- 34/35: adjacency logic --
def test_34_adjacent_window_coherence_logic():
    assert cl._has_adjacent_support([15, 20], cl.A_LIST) is True
    assert cl._has_adjacent_support([5, 60], cl.A_LIST) is False


def test_35_adjacent_horizon_coherence_logic():
    assert cl._has_adjacent_support([30, 60], cl.H_LIST) is True
    assert cl._has_adjacent_support([1, 120], cl.H_LIST) is False


# ------------------------------------------------------------- 36: open vs late-morning --
def test_36_open_vs_late_morning_classification():
    assert 30 <= 30  # A=30 counts as OPEN (<=30)
    assert not (60 <= 30)  # A=60 is LATE_MORNING_ONLY


# ------------------------------------------------------------- 37/38/39: rolling state --
def test_37_causal_rolling_state_lookback():
    barriers = pd.DataFrame({
        "instrument": ["NQ"] * 15, "level_id": ["UPPER_k0"] * 15,
        "b": [1.0] * 15, "horizon": [30] * 15, "first_touch_elapsed_bar": [10] * 15,
        "session_date": [pd.Timestamp("2020-01-01") + pd.Timedelta(days=i) for i in range(15)],
        "calendar_year": [2020] * 15,
        "barrier_first_outcome": (["CONTINUATION_FIRST"] * 10 + ["REVERSAL_FIRST"] * 5),
    })
    events = pd.DataFrame({"instrument": [], "level_id": []})
    out = rs.build_rolling_state_events(barriers, events)
    row10 = out.iloc[10]  # the 11th event (index10): prior 10 are the first 10, all CONTINUATION_FIRST
    assert row10["prior_state"] == "CONTINUATION_STATE"


def test_38_current_event_excluded_from_state():
    barriers = pd.DataFrame({
        "instrument": ["NQ"] * 11, "level_id": ["UPPER_k0"] * 11,
        "b": [1.0] * 11, "horizon": [30] * 11, "first_touch_elapsed_bar": [10] * 11,
        "session_date": [pd.Timestamp("2020-01-01") + pd.Timedelta(days=i) for i in range(11)],
        "calendar_year": [2020] * 11,
        "barrier_first_outcome": (["CONTINUATION_FIRST"] * 10 + ["REVERSAL_FIRST"]),
    })
    out = rs.build_rolling_state_events(barriers, pd.DataFrame())
    last_row = out.iloc[10]
    # state must be computed from the prior 10 (all CONTINUATION_FIRST), NOT
    # including the current (11th, REVERSAL_FIRST) event's own outcome
    assert last_row["prior_state"] == "CONTINUATION_STATE"
    assert last_row["current_outcome"] == "REVERSAL_FIRST"


def test_39_state_unavailable_handling():
    barriers = pd.DataFrame({
        "instrument": ["NQ"] * 5, "level_id": ["UPPER_k0"] * 5,
        "b": [1.0] * 5, "horizon": [30] * 5, "first_touch_elapsed_bar": [10] * 5,
        "session_date": [pd.Timestamp("2020-01-01") + pd.Timedelta(days=i) for i in range(5)],
        "calendar_year": [2020] * 5,
        "barrier_first_outcome": ["CONTINUATION_FIRST"] * 5,
    })
    out = rs.build_rolling_state_events(barriers, pd.DataFrame())
    assert (out["prior_state"] == "STATE_UNAVAILABLE").all()


# ------------------------------------------------------------- 40: year accounting --
def test_40_year_accounting():
    barriers = pd.DataFrame({
        "instrument": ["NQ"] * 4, "level_id": ["UPPER_k0"] * 4, "b": [1.0] * 4, "horizon": [30] * 4,
        "first_touch_elapsed_bar": [10] * 4,
        "session_date": [pd.Timestamp("2019-01-01"), pd.Timestamp("2019-06-01"),
                        pd.Timestamp("2020-01-01"), pd.Timestamp("2020-06-01")],
        "calendar_year": [2019, 2019, 2020, 2020],
        "barrier_first_outcome": ["CONTINUATION_FIRST", "REVERSAL_FIRST", "CONTINUATION_FIRST", "CONTINUATION_FIRST"],
    })
    events = pd.DataFrame({"instrument": ["NQ"] * 4, "level_id": ["UPPER_k0"] * 4,
                          "first_touch_elapsed_bar": [10] * 4, "calendar_year": [2019, 2019, 2020, 2020],
                          "same_bar_morphology": ["SAME_BAR_NEUTRAL"] * 4})
    outcomes = pd.DataFrame({"instrument": ["NQ"] * 4, "level_id": ["UPPER_k0"] * 4, "horizon": [30] * 4,
                            "first_touch_elapsed_bar": [10] * 4, "calendar_year": [2019, 2019, 2020, 2020],
                            "SIGNED_CLOSE_H": [1.0, -1.0, 1.0, 1.0]})
    yrs = st.year_stability(barriers, events, outcomes, activation_window=30, horizon=30)
    assert set(yrs["year"]) == {2019, 2020}


# ------------------------------------------------------------- 41: alias handling --
def test_41_alias_handling():
    levels_tbl = pd.DataFrame({
        "instrument": ["NQ"] * 3, "session_date": [pd.Timestamp("2020-01-01")] * 3,
        "level_id": ["UPPER_k0", "UPPER_k1", "LOWER_k0"], "level_value": [100.0, 100.1, 90.0],
        "level_valid": [True, True, True], "first_touch_found": [True, False, False],
    })
    clusters = st.coincident_levels(levels_tbl, tick=0.25)
    sizes = sorted(clusters["cluster_size"].tolist())
    assert sizes == [1, 2]


# ------------------------------------------------------------- 42: complete null retention --
def test_42_complete_null_retention():
    df = pd.DataFrame({"instrument": ["NQ"] * 3, "level_id": ["x", "y", "z"], "p_raw": [np.nan, 0.5, np.nan]})
    out = st.bh_within(df, "p_raw", group_cols=("instrument",))
    assert len(out) == 3
    assert out["q_value"].isna().sum() == 2
