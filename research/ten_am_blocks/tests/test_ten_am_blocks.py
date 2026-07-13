"""38 required tests, per SPEC_TEN_AM_BLOCKS.md / task instructions."""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ten_am_blocks.src import data as dta
from research.ten_am_blocks.src import session_ledger as sl
from research.ten_am_blocks.src import module_a as ma
from research.ten_am_blocks.src import module_b as mb
from research.ten_am_blocks.src import summary as sm
from research.ten_am_blocks.src import classification as cl


def bar(o, h, l, c):
    return {"open": o, "high": h, "low": l, "close": c, "volume": 1}


def make_rth(pre10, post10=None, extra=None):
    rows = [{"et_minute": 570 + i, **b} for i, b in enumerate(pre10)]
    if post10:
        rows += [{"et_minute": 600 + i, **b} for i, b in enumerate(post10)]
    if extra:
        rows += [{"et_minute": et, **b} for et, b in extra.items()]
    df = pd.DataFrame(rows)
    df = df.drop_duplicates("et_minute", keep="last")
    return df.sort_values("et_minute").reset_index(drop=True)


def flat_pre10(price=100.0, n=30):
    return [bar(price, price, price, price) for _ in range(n)]


def flat_post10(price=101.0, n=60):
    return [bar(price, price, price, price) for _ in range(n)]


# 1-2: partition guard / no 2023+ access
def test_01_02_dev_partition():
    df = pd.DataFrame(
        {"session_date": [dt.date(2017, 12, 29), dt.date(2018, 1, 3), dt.date(2022, 12, 30), dt.date(2023, 1, 3)]}
    )
    out = dta.filter_development(df)
    assert out["session_date"].min() == dt.date(2018, 1, 3)
    assert out["session_date"].max() == dt.date(2022, 12, 30)
    assert len(out) == 2


# 3: ES/NQ separation
def test_03_es_nq_separation():
    pre10 = flat_pre10()
    pre10[29] = bar(100, 103, 100, 102)
    rth = make_rth(pre10, flat_post10())
    rec_es = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    rec_nq = sl.build_session_record(rth, "NQ", dt.date(2019, 1, 2))
    assert rec_es["instrument"] == "ES"
    assert rec_nq["instrument"] == "NQ"


# 4: exact 09:30-09:59 construction window
def test_04_exact_pre10_window():
    pre10 = flat_pre10()[:-1]  # only 29 bars
    rth = make_rth(pre10, flat_post10())
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    assert rec["valid"] is False
    assert rec["reason"] == "PRE10_INCOMPLETE"

    pre10_full = flat_pre10()
    pre10_full[10] = bar(100, 105, 100, 101)  # nonzero RANGE_30
    rth_full = make_rth(pre10_full, flat_post10())
    rec_full = sl.build_session_record(rth_full, "ES", dt.date(2019, 1, 2))
    assert rec_full["valid"] is True


# 5: exact 10:00-10:59 interaction window
def test_05_exact_post10_window():
    pre10 = flat_pre10()
    pre10[29] = bar(100, 103, 100, 102)
    rth = make_rth(pre10, flat_post10(n=59))  # only 59 post-10 bars
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    assert rec["post10_complete"] is False
    assert mb.find_interaction(rec, "upper") is None  # incomplete window -> no search


# 6-8: final high-maker/low-maker bar selection, last-tied-extreme rule
def test_06_07_08_last_tied_extreme():
    pre10 = flat_pre10()
    pre10[5] = bar(100, 105, 99, 100)   # first bar tied at high=105
    pre10[20] = bar(100, 105, 100, 100)  # later bar also high=105 -> H_BAR must be idx 20
    pre10[10] = bar(100, 100, 95, 100)   # first tied low=95
    pre10[25] = bar(100, 100, 95, 100)   # later tied low=95 -> L_BAR must be idx 25
    rth = make_rth(pre10, flat_post10())
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    assert rec["upper"]["forming_bar_et_minute"] == 570 + 20
    assert rec["lower"]["forming_bar_et_minute"] == 570 + 25


# 9: upper-block formula
def test_09_upper_block_formula():
    pre10 = flat_pre10()
    pre10[15] = bar(101, 105, 100.5, 102.5)  # open=101,close=102.5 -> low=max(101,102.5)=102.5, high=105
    rth = make_rth(pre10, flat_post10())
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    assert rec["upper"]["low"] == pytest.approx(102.5)
    assert rec["upper"]["high"] == pytest.approx(105)


# 10: lower-block formula
def test_10_lower_block_formula():
    pre10 = flat_pre10()
    pre10[15] = bar(99, 100.5, 95, 97)  # open=99,close=97 -> high=min(99,97)=97, low=95
    rth = make_rth(pre10, flat_post10())
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    assert rec["lower"]["low"] == pytest.approx(95)
    assert rec["lower"]["high"] == pytest.approx(97)


# 11: one-tick minimum width
def test_11_one_tick_minimum_width():
    pre10 = flat_pre10()
    pre10[15] = bar(100, 100.1, 99.9, 100.05)  # tiny wick, open=close=high approx -> width < 0.25
    rth = make_rth(pre10, flat_post10())
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    assert rec["upper"]["width"] < 0.25
    assert rec["upper"]["valid"] is False


# 12-13: pristine / pretouched classification
def test_12_13_pristine_pretouched():
    pre10 = flat_pre10()
    pre10[10] = bar(100, 105, 100, 101)  # forms upper block [101,105]
    rth_pristine = make_rth(pre10, flat_post10())
    rec1 = sl.build_session_record(rth_pristine, "ES", dt.date(2019, 1, 2))
    assert rec1["upper"]["freshness"] == "PRISTINE"

    pre10b = list(pre10)
    pre10b[20] = bar(102, 103, 101.5, 102)  # later bar trades into [101,105]
    rth_touched = make_rth(pre10b, flat_post10())
    rec2 = sl.build_session_record(rth_touched, "ES", dt.date(2019, 1, 2))
    assert rec2["upper"]["freshness"] == "PRETOUCHED"


# 14: 10:00 open location states
def test_14_open_location_states():
    pre10 = flat_pre10()
    pre10[10] = bar(100, 105, 100, 101)  # upper block [101,105]
    post10_approach = flat_post10(price=100.5)  # open below block
    rth = make_rth(pre10, post10_approach)
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    assert rec["upper"]["open_location"] == "APPROACH_SIDE"

    post10_inside = flat_post10(price=103)
    rth2 = make_rth(pre10, post10_inside)
    rec2 = sl.build_session_record(rth2, "ES", dt.date(2019, 1, 2))
    assert rec2["upper"]["open_location"] == "OPEN_INSIDE"

    post10_beyond = flat_post10(price=110)
    rth3 = make_rth(pre10, post10_beyond)
    rec3 = sl.build_session_record(rth3, "ES", dt.date(2019, 1, 2))
    assert rec3["upper"]["open_location"] == "ALREADY_BEYOND"


# 15: first interaction only
def test_15_first_interaction_only():
    pre10 = flat_pre10()
    pre10[10] = bar(100, 105, 100, 101)  # upper block [101,105]
    post10 = flat_post10(price=100.0)
    post10[5] = bar(100, 101.5, 100, 101)   # first touch at et=605
    post10[10] = bar(100, 108, 100, 107)    # would also touch, must be ignored
    rth = make_rth(pre10, post10)
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    t = mb.find_interaction(rec, "upper")
    assert t == 605


# 16: nested activation windows derived from one timestamp
def test_16_nested_activation_windows():
    flags = mb._activation_flags(600)
    assert flags["WITHIN_10AM_CANDLE"] and flags["WITHIN_5MIN"] and flags["WITHIN_60MIN"]
    flags2 = mb._activation_flags(607)  # elapsed = 8 minutes
    assert not flags2["WITHIN_5MIN"] and flags2["WITHIN_10MIN"] and flags2["WITHIN_60MIN"]
    flags3 = mb._activation_flags(658)  # elapsed = 59 minutes
    assert not flags3["WITHIN_30MIN"] and flags3["WITHIN_60MIN"]


# 17-20: same-bar block morphology (upper/lower x reversal/breakthrough)
def _session_with_upper_block(interaction_bar, extra=None):
    pre10 = flat_pre10()
    pre10[10] = bar(100, 105, 100, 101)  # upper block [101,105]
    post10 = flat_post10(price=100.0)
    post10[5] = interaction_bar
    rth = make_rth(pre10, post10, extra=extra)
    return sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))


def test_17_upper_same_bar_reversal():
    rec = _session_with_upper_block(bar(102, 103, 100.5, 100.5))  # closes below 101
    ev = mb.compute_block_event(rec, "upper")
    assert ev["same_bar_morphology"] == "REVERSAL_PROXY"


def test_18_upper_same_bar_breakthrough():
    rec = _session_with_upper_block(bar(102, 106, 101.5, 106))  # closes above 105
    ev = mb.compute_block_event(rec, "upper")
    assert ev["same_bar_morphology"] == "BREAKTHROUGH_PROXY"


def _session_with_lower_block(interaction_bar, extra=None):
    pre10 = flat_pre10()
    pre10[10] = bar(99, 100, 95, 97)  # lower block [95,97]
    post10 = flat_post10(price=100.0)
    post10[5] = interaction_bar
    rth = make_rth(pre10, post10, extra=extra)
    return sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))


def test_19_lower_same_bar_reversal():
    rec = _session_with_lower_block(bar(96, 98, 95.5, 98))  # closes above 97
    ev = mb.compute_block_event(rec, "lower")
    assert ev["same_bar_morphology"] == "REVERSAL_PROXY"


def test_20_lower_same_bar_breakthrough():
    rec = _session_with_lower_block(bar(96, 96.5, 93, 93))  # closes below 95
    ev = mb.compute_block_event(rec, "lower")
    assert ev["same_bar_morphology"] == "BREAKTHROUGH_PROXY"


# 21-22: outcomes begin at T+1, interaction-bar exclusion
def test_21_22_outcomes_start_t_plus_1():
    rec = _session_with_upper_block(
        bar(102, 200, 0.1, 101.5), extra={606: bar(101.5, 101.5, 101.5, 101.5)}
    )
    ev = mb.compute_block_event(rec, "upper")
    # bar T's own high=200/low=0.1 must not enter the H=1 excursion
    assert ev["rev_exc_h1"] == pytest.approx(max(0, rec["upper"]["low"] - 101.5))
    assert ev["brk_exc_h1"] == pytest.approx(max(0, 101.5 - rec["upper"]["high"]))


# 23, 33: all complete horizons required, no partial fallback
def test_23_33_complete_horizons_no_partial():
    # interaction on the LAST post-10 bar (659); only one extra bar (660) provided
    # afterward -> horizon_1 can complete, horizon_3 cannot (no bars 661,662 exist)
    pre10 = flat_pre10()
    pre10[10] = bar(100, 105, 100, 101)  # upper block [101,105]
    post10 = flat_post10(price=100.0)
    post10[59] = bar(102, 103, 100.5, 100.5)  # interaction at et=659
    rth = make_rth(pre10, post10, extra={660: bar(100.5, 100.5, 100.5, 100.5)})
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    ev = mb.compute_block_event(rec, "upper")
    assert ev["horizon_1_complete"] is True
    assert ev["horizon_3_complete"] is False
    assert np.isnan(ev["signed_close_h3"])


# 24-25: mirrored reversal/breakthrough formulas (upper/lower)
def test_24_upper_mirrored_formulas():
    rec = _session_with_upper_block(
        bar(102, 103, 100.5, 100.5), extra={606: bar(95, 95, 95, 95), 607: bar(108, 108, 108, 108)}
    )
    ev = mb.compute_block_event(rec, "upper")
    assert ev["rev_exc_h3"] == pytest.approx(rec["upper"]["low"] - 95)
    assert ev["brk_exc_h3"] == pytest.approx(108 - rec["upper"]["high"])


def test_25_lower_mirrored_formulas():
    rec = _session_with_lower_block(
        bar(96, 98, 95.5, 98), extra={606: bar(105, 105, 105, 105), 607: bar(90, 90, 90, 90)}
    )
    ev = mb.compute_block_event(rec, "lower")
    assert ev["rev_exc_h3"] == pytest.approx(105 - rec["lower"]["high"])
    assert ev["brk_exc_h3"] == pytest.approx(rec["lower"]["low"] - 90)


# 26-27: barrier-first reversal / breakthrough
def test_26_27_barrier_first():
    pre10 = flat_pre10()
    pre10[10] = bar(100, 105, 100, 101)  # upper block [101,105], RANGE_30 computed from full pre10
    post10 = flat_post10(price=100.0)
    post10[5] = bar(102, 103, 100.5, 100.5)  # interaction at et=605
    tail = {606: bar(95, 95, 95, 95)}  # far below -> reversal barrier hit
    rth = make_rth(pre10, post10, extra=tail)
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    ev = mb.compute_block_event(rec, "upper")
    assert ev["b0.25_h1_outcome"] == "REVERSAL_FIRST"

    tail2 = {606: bar(120, 120, 120, 120)}  # far above -> breakthrough barrier hit
    rth2 = make_rth(pre10, post10, extra=tail2)
    rec2 = sl.build_session_record(rth2, "ES", dt.date(2019, 1, 2))
    ev2 = mb.compute_block_event(rec2, "upper")
    assert ev2["b0.25_h1_outcome"] == "BREAKTHROUGH_FIRST"


# 28: same-bar tie
def test_28_same_bar_tie():
    pre10 = flat_pre10()
    pre10[10] = bar(100, 105, 100, 101)
    post10 = flat_post10(price=100.0)
    post10[5] = bar(102, 103, 100.5, 100.5)
    rth = make_rth(pre10, post10)
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    range30 = rec["range_30"]
    b = 0.25
    rev_barrier = rec["upper"]["low"] - b * range30
    brk_barrier = rec["upper"]["high"] + b * range30
    tail = {606: bar(rev_barrier - 1, brk_barrier + 1, rev_barrier - 1, (rev_barrier + brk_barrier) / 2)}
    rth2 = make_rth(pre10, post10, extra=tail)
    rec2 = sl.build_session_record(rth2, "ES", dt.date(2019, 1, 2))
    ev = mb.compute_block_event(rec2, "upper")
    assert ev[f"b{b}_h1_outcome"] == "SAME_BAR_TIE"


# 29: neither
def test_29_neither():
    pre10 = flat_pre10()
    pre10[10] = bar(100, 105, 100, 101)
    post10 = flat_post10(price=100.0)
    post10[5] = bar(102, 103, 100.5, 100.5)
    tail = {606: bar(102.5, 102.5, 102.5, 102.5)}  # stays inside, no barrier reached
    rth = make_rth(pre10, post10, extra=tail)
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    ev = mb.compute_block_event(rec, "upper")
    assert ev["b1.0_h1_outcome"] == "NEITHER"


# 30: Module-A continuation/reversal formulas
def test_30_module_a_formulas():
    pre10 = flat_pre10()
    pre10[10] = bar(100, 102, 99, 100)  # nonzero RANGE_30
    post10 = flat_post10(price=100.0)
    post10[0] = bar(100, 100.5, 99.5, 100.5)  # bullish 10:00 candle, close>=open+0.25
    extra = {601: bar(100.5, 101, 99, 99.2), 602: bar(99.2, 99.2, 99.2, 99.2), 603: bar(99.2, 108, 99.2, 108)}
    rth = make_rth(pre10, post10, extra=extra)
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    assert rec["candle_state"] == "BULLISH_1000"
    ev = ma.compute_module_a(rec)
    o1000 = rec["o_1000"]
    assert ev["cont_exc_h3"] == pytest.approx(max(0, 108 - o1000))
    assert ev["rev_exc_h3"] == pytest.approx(max(0, o1000 - 99))


# 31: RANGE_30 normalization
def test_31_range30_normalization():
    pre10 = flat_pre10()
    pre10[10] = bar(100, 105, 100, 101)
    post10 = flat_post10(price=100.0)
    post10[5] = bar(102, 103, 100.5, 100.5)
    tail = {606: bar(95, 95, 95, 95)}
    rth = make_rth(pre10, post10, extra=tail)
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    ev = mb.compute_block_event(rec, "upper")
    assert ev["rev_exc_atr_h1"] == pytest.approx(ev["rev_exc_h1"] / rec["range_30"])


# 32: exact trailing-20 median scale
def test_32_median_range_20():
    df_rows = []
    for i in range(25):
        pre10 = flat_pre10(price=100.0)
        pre10[0] = bar(100, 100 + (i % 5) + 1, 100, 100)  # varying RANGE_30
        rth = make_rth(pre10, flat_post10())
        df_rows.append(rth.assign(session_date=dt.date(2019, 1, 1) + dt.timedelta(days=i)))
    df1m = pd.concat(df_rows, ignore_index=True)
    records = sl.build_ledger(df1m, "ES")
    assert all(np.isnan(r["median_range_20"]) for r in records[:20])
    assert not np.isnan(records[20]["median_range_20"])
    expected = np.median([r["range_30"] for r in records[0:20]])
    assert records[20]["median_range_20"] == pytest.approx(expected)


# 34: context-stratum boundaries
def test_34_context_stratum_boundaries():
    pre10 = flat_pre10()
    pre10[0] = bar(100, 100, 100, 100)
    pre10[5] = bar(100, 105, 95, 100)  # nonzero RANGE_30, but close_0959 will equal open_0930
    pre10[-1] = bar(100, 100, 100, 100)  # close_0959 == open_0930 == 100 -> R_30 == 0
    rth = make_rth(pre10, flat_post10())
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    assert rec["valid"] is True
    assert rec["pre10_stratum"] == "PRE10_FLAT"
    # construct close-location exactly at 0.25 boundary
    pre10b = flat_pre10()
    pre10b[0] = bar(100, 104, 100, 100)  # range 4, close set below via last bar
    pre10b[-1] = bar(100, 100, 100, 101)  # close_0959=101 -> loc=(101-100)/4=0.25
    rthb = make_rth(pre10b, flat_post10())
    recb = sl.build_session_record(rthb, "ES", dt.date(2019, 1, 2))
    assert recb["close_location_30"] == pytest.approx(0.25)
    assert recb["close_loc_stratum"] == "CLOSE_LOW"


# 35: aligned-momentum definition
def test_35_momentum_into_block():
    pre10 = flat_pre10()
    pre10[0] = bar(100, 100, 100, 100)
    pre10[15] = bar(100, 106, 100, 100)  # forms upper block (sets the 30-minute high)
    pre10[20] = bar(99, 99.5, 97, 99.3)  # forms a valid lower block (sets the 30-minute low)
    pre10[-1] = bar(105, 105.9, 104.8, 105.9)  # close high, up-dominant, but not a new extreme
    post10 = flat_post10(price=100.5)
    rth = make_rth(pre10, post10)
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    assert rec["pre10_stratum"] == "PRE10_UP"
    assert rec["close_loc_stratum"] == "CLOSE_HIGH"
    assert rec["dominance_stratum"] == "UP_DOMINANT"
    assert rec["upper"]["momentum"] == "MOMENTUM_INTO_BLOCK"
    assert rec["lower"]["momentum"] == "NOT_MOMENTUM_INTO_BLOCK"


# 36: year accounting
def test_36_year_accounting():
    events = pd.DataFrame(
        {
            "instrument": ["ES"] * 5, "candle_state": ["BULLISH_1000"] * 5,
            "directional": [True] * 5, "year": [2018, 2019, 2020, 2021, 2022],
            "horizon_15_complete": [True] * 5,
            "signed_close_atr_h15": [0.1, 0.1, -0.2, 0.1, 0.1],
            "b0.5_h15_outcome": ["CONTINUATION_FIRST"] * 5,
        }
    )
    for H in ma.HORIZONS:
        if H != 15:
            events[f"horizon_{H}_complete"] = False
            events[f"signed_close_atr_h{H}"] = np.nan
            events[f"b0.5_h{H}_outcome"] = "INVALID"
    yr = cl.module_a_year_stability(events)
    sub = yr.loc[yr["horizon_min"] == 15]
    assert set(sub["year"]) == set(cl.YEARS)
    assert len(sub) == 5


# 37: BH-family membership
def test_37_bh_family_membership():
    cells = pd.DataFrame(
        {
            "instrument": ["ES"] * 6, "candle_state": ["BULLISH_1000", "BEARISH_1000"] * 3,
            "horizon_min": [1, 1, 3, 3, 15, 15],
            "n_observations": [80] * 6, "n_nontied": [40] * 6,
            "cont_minus_rev_first_rate": [0.1] * 6,
            "median_signed_close_atr": [0.1] * 6,
            "binom_p": [0.001, 0.5, 0.2, 0.5, 0.03, 0.9],
            "is_primary": [False, False, False, False, True, True],
        }
    )
    out = cl.apply_bh_module_a(cells)
    assert out["q_value"].notna().all()
    # all 6 rows share the single instrument=ES family
    assert len(out.loc[out["instrument"] == "ES"]) == 6


# 38: complete null retention
def test_38_null_retention():
    pre10 = flat_pre10()
    pre10[0] = bar(100, 100.1, 99.9, 100)  # width < 0.25 -> block invalid, no events
    rth = make_rth(pre10, flat_post10())
    rec = sl.build_session_record(rth, "ES", dt.date(2019, 1, 2))
    ev = mb.compute_block_event(rec, "upper")
    assert ev is None  # invalid block -> no event, not a silently-dropped populated one


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
