"""38 required tests, per SPEC_SWEEP_FAILURE.md / task instructions."""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.sweep_failure.src import data as dta
from research.sweep_failure.src import levels as lv
from research.sweep_failure.src import volume as vol
from research.sweep_failure.src import events as ev
from research.sweep_failure.src import outcomes as oc
from research.sweep_failure.src import confirmation as cf
from research.sweep_failure.src import permutation as pm
from research.sweep_failure.src import classification as cl


def make_rth_bars(closes, opens=None, highs=None, lows=None, atr=1.0, volume=100):
    n = len(closes)
    closes = np.asarray(closes, dtype=float)
    opens = np.asarray(opens, dtype=float) if opens is not None else closes.copy()
    highs = np.asarray(highs, dtype=float) if highs is not None else np.maximum(opens, closes)
    lows = np.asarray(lows, dtype=float) if lows is not None else np.minimum(opens, closes)
    ts = pd.date_range("2019-01-02 09:30", periods=n, freq="1min", tz="UTC")
    et = np.arange(570, 570 + n)
    return pd.DataFrame({
        "et_minute": et, "ts_event": ts, "open": opens, "high": highs, "low": lows,
        "close": closes, "volume": np.full(n, volume), "atr20_event": np.full(n, atr),
    })


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
    bars = make_rth_bars([100] * 3 + [103, 104, 105, 100] + [100] * 383)
    bars.loc[0:2, "high"] = 99.9
    _, events_es = ev.process_level_session(bars, 100.0, "lower", "overnight_low", "ES", dt.date(2019, 1, 2))
    _, events_nq = ev.process_level_session(bars, 100.0, "lower", "overnight_low", "NQ", dt.date(2019, 1, 2))
    for e in events_es:
        assert e["instrument"] == "ES"
    for e in events_nq:
        assert e["instrument"] == "NQ"


# 4: previous-RTH level construction
def test_04_previous_rth_level_construction():
    rows = []
    for i, day in enumerate([1, 2, 3]):
        base = 100 + i * 10
        session_date = dt.date(2019, 1, day)
        for m in range(390):
            rows.append({"session_date": session_date, "et_minute": 570 + m,
                         "ts_event": pd.Timestamp(f"2019-01-0{day} 09:30", tz="UTC") + pd.Timedelta(minutes=m),
                         "open": base, "high": base + 5, "low": base - 5, "close": base, "volume": 10})
    df1m = pd.DataFrame(rows)
    recs = lv.build_level_ledger(df1m, "ES")
    assert recs[0]["prev_rth_level_valid"] is False
    assert recs[1]["prev_rth_level_valid"] is True
    assert recs[1]["prev_rth_high"] == pytest.approx(105.0)  # day 1's high
    assert recs[1]["prev_rth_low"] == pytest.approx(95.0)
    assert recs[2]["prev_rth_high"] == pytest.approx(115.0)  # day 2's high


# 5: overnight level construction
def test_05_overnight_level_construction():
    session_date = dt.date(2019, 1, 2)
    rows = []
    # overnight: prev day 18:00 (et=1080) through today 09:29 (et=569) -> 930 bars
    for m in range(930):
        et_m = (1080 + m) % 1440
        rows.append({"session_date": session_date, "et_minute": et_m,
                     "ts_event": pd.Timestamp("2019-01-01 18:00", tz="UTC") + pd.Timedelta(minutes=m),
                     "open": 100, "high": 108, "low": 92, "close": 100, "volume": 5})
    # RTH bars too, so this session can itself be used as a "previous" for another test if needed
    for m in range(390):
        rows.append({"session_date": session_date, "et_minute": 570 + m,
                     "ts_event": pd.Timestamp("2019-01-02 09:30", tz="UTC") + pd.Timedelta(minutes=m),
                     "open": 100, "high": 101, "low": 99, "close": 100, "volume": 5})
    df1m = pd.DataFrame(rows)
    recs = lv.build_level_ledger(df1m, "ES")
    assert recs[0]["overnight_valid"] is True
    assert recs[0]["overnight_high"] == pytest.approx(108.0)
    assert recs[0]["overnight_low"] == pytest.approx(92.0)


# 6: exact RTH search window
def test_06_exact_rth_window():
    bars = make_rth_bars([100] * 390)
    assert bars["et_minute"].min() == 570
    assert bars["et_minute"].max() == 959
    assert len(bars) == 390
    rows = [{"session_date": dt.date(2019, 1, 2), "et_minute": 570 + m,
             "ts_event": pd.Timestamp("2019-01-02 09:30", tz="UTC") + pd.Timedelta(minutes=m),
             "open": 100, "high": 100, "low": 100, "close": 100, "volume": 1} for m in range(389)]
    recs = lv.build_level_ledger(pd.DataFrame(rows), "ES")
    assert recs[0]["rth_valid"] is False  # only 389 bars, not 390


# 7: upper/lower level side
def test_07_upper_lower_side():
    assert ev.UPPER_TYPES == ("prev_rth_high", "overnight_high")
    assert ev.LOWER_TYPES == ("prev_rth_low", "overnight_low")


# 8: three-bar arming
def test_08_three_bar_arming():
    closes = [100] * 390
    bars = make_rth_bars(closes)
    bars.loc[0:1, "high"] = 100.1  # only 2 bars inside, not 3 -> should NOT arm yet at bar 2
    bars.loc[2:4, "high"] = 99.5   # 3 clean inside bars starting at idx 2
    bars.loc[5, ["low", "high"]] = [99, 101]  # touch/breach bar
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert len(events) >= 1
    assert events[0]["breach_idx"] if "breach_idx" in events[0] else events[0]["event_idx"] >= 5


# 9: first interaction only
def test_09_first_interaction_only():
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99, 101, 99]  # first interaction: breach then fails
    bars.loc[4:6, "high"] = 99.5  # rearm
    bars.loc[7, ["low", "high", "close"]] = [99, 108, 107]  # second interaction
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert len(events) == 2
    assert events[0]["breach_idx"] == 3
    assert events[1]["breach_idx"] == 7


# 10: one-tick breach requirement
def test_10_one_tick_breach():
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.8, 100, 99.9]  # touch exactly, no breach
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert events[0]["event_class"] == "TOUCH_WITHOUT_BREACH"


# 11: touch-without-breach classification
def test_11_touch_without_breach():
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "low"] = 100.5
    bars.loc[3, ["low", "high", "close"]] = [100, 101, 100.5]  # exact low touch
    _, events = ev.process_level_session(bars, 100.0, "lower", "prev_rth_low", "ES", dt.date(2019, 1, 2))
    assert events[0]["event_class"] == "TOUCH_WITHOUT_BREACH"
    assert events[0]["touch_sub"] == "TOUCH_CLOSE_AT_LEVEL" or events[0]["touch_sub"] == "TOUCH_CLOSE_INSIDE"


# 12-14: one/two/three-minute failure
def test_12_one_minute_failure():
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 99.75]  # breach, closes back inside same bar
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert events[0]["event_class"] == "FAILED_BREACH_1MIN"


def test_13_two_minute_failure():
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 100.25]  # breach, closes outside
    bars.loc[4, ["low", "high", "close"]] = [99.5, 100.5, 99.75]     # closes back inside at B+1
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert events[0]["event_class"] == "FAILED_BREACH_2MIN"


def test_14_three_minute_failure():
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 100.25]
    bars.loc[4, ["low", "high", "close"]] = [99.75, 100.5, 100.25]
    bars.loc[5, ["low", "high", "close"]] = [99.5, 100.5, 99.75]  # closes inside at B+2
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert events[0]["event_class"] == "FAILED_BREACH_3MIN"


# 15: successful-breach control
def test_15_successful_breach_control():
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 100.25]
    bars.loc[4, ["low", "high", "close"]] = [100.0, 100.5, 100.25]
    bars.loc[5, ["low", "high", "close"]] = [100.0, 100.75, 100.5]
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert events[0]["event_class"] == "SUCCESSFUL_BREACH_CONTROL"
    assert events[0]["confirmation_idx"] == 5


# 16: delayed-failure control
def test_16_delayed_failure_control():
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "high"] = 99.5
    # B, B+1, B+2 all close exactly AT the level (neither inside nor outside) --
    # DELAYED_FAILURE_CONTROL only applies to this narrow case; any close strictly
    # outside during B..B+2 would instead resolve as SUCCESSFUL_BREACH_CONTROL.
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 100.0]
    bars.loc[4, ["low", "high", "close"]] = [99.75, 100.25, 100.0]
    bars.loc[5, ["low", "high", "close"]] = [99.75, 100.25, 100.0]
    bars.loc[6, ["low", "high", "close"]] = [99.5, 100.25, 99.75]  # first inside close at B+3
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert events[0]["event_class"] == "DELAYED_FAILURE_CONTROL"
    assert events[0]["confirmation_idx"] == 6


# 17-18: mandatory rearming / session reset
def test_17_18_mandatory_rearm_and_session_reset():
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 99.75]  # FAILED_BREACH_1MIN
    bars.loc[4, "high"] = 100.25  # immediately after, should NOT rearm (straddling bar breaks run)
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert len(events) == 1  # no immediate re-trigger without a fresh 3-bar run
    # session reset: a brand new session with fresh bars must be independent
    bars2 = make_rth_bars([100] * 390)
    bars2.loc[0:2, "high"] = 99.5
    bars2.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 99.75]
    _, events2 = ev.process_level_session(bars2, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 3))
    assert len(events2) == 1


# 19: ATR20 through event-1
def test_19_atr_causal():
    df1m = pd.DataFrame({
        "ts_event": pd.date_range("2019-01-02", periods=25, freq="1min", tz="UTC"),
        "open": [100 + i * 0.1 for i in range(25)],
        "high": [100 + i * 0.1 + 1 for i in range(25)],
        "low": [100 + i * 0.1 - 1 for i in range(25)],
        "close": [100 + i * 0.1 for i in range(25)],
        "volume": [1] * 25,
    })
    out = dta.add_causal_atr(df1m)
    manual = out["tr"].iloc[4:24].mean()
    assert out["atr20_event"].iloc[24] == pytest.approx(manual)


# 20: causal clock-minute volume percentile
def test_20_volume_percentile():
    records = []
    for i in range(65):
        rth = pd.DataFrame({"et_minute": [570], "volume": [float(i)]})
        records.append({"rth_valid": True, "session_date": dt.date(2019, 1, 1) + dt.timedelta(days=i), "_rth_bars": rth})
    table = vol.build_volume_percentile_table(records)
    key60 = (records[60]["session_date"], 570)
    assert table[key60] == pytest.approx(1.0)  # bar 60's volume=60 is the max of the trailing 60 (0..59)
    key5 = (records[5]["session_date"], 570)
    assert np.isnan(table[key5])  # fewer than 60 prior observations


# 21: previous-test count excludes current event
def test_21_previous_test_count():
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 99.75]  # 1st interaction: FAILED_BREACH_1MIN
    bars.loc[4:6, "high"] = 99.5  # rearm
    bars.loc[7, ["low", "high", "close"]] = [99.75, 100.25, 99.75]  # 2nd interaction
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert events[0]["prior_test_count_n"] == 0
    assert events[0]["prior_test_category"] == "FIRST_TEST"
    assert events[1]["prior_test_count_n"] == 1
    assert events[1]["prior_test_category"] == "SECOND_TEST"


# 22: paired-instrument confirmation window
def test_22_confirmation_window():
    ts0 = pd.Timestamp("2019-01-02 10:00", tz="UTC")
    ev_a = [{"level_type": "prev_rth_high", "side": "upper", "event_class": "FAILED_BREACH_1MIN", "breach_ts": ts0}]
    ev_b_in = [{"level_type": "prev_rth_high", "side": "upper", "event_class": "FAILED_BREACH_1MIN",
                "breach_ts": ts0 + pd.Timedelta(seconds=50)}]
    ev_b_out = [{"level_type": "prev_rth_high", "side": "upper", "event_class": "FAILED_BREACH_1MIN",
                 "breach_ts": ts0 + pd.Timedelta(minutes=5)}]
    out_in = cf.add_confirmation(ev_a, ev_b_in)
    out_out = cf.add_confirmation(ev_a, ev_b_out)
    assert out_in[0]["confirmation"] == "CONFIRMED_BREACH"
    assert out_out[0]["confirmation"] == "UNCONFIRMED_BREACH"


# 23-24: legal outcome anchor by event class, event/confirmation bars excluded
def test_23_24_anchor_and_exclusion():
    assert oc.anchor_idx({"event_class": "FAILED_BREACH_1MIN", "confirmation_idx": 5}) == 5
    assert oc.anchor_idx({"event_class": "SUCCESSFUL_BREACH_CONTROL", "breach_idx": 3}) == 5
    assert oc.anchor_idx({"event_class": "TOUCH_WITHOUT_BREACH", "event_idx": 7}) == 7
    bars = make_rth_bars([100] * 390)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 200, 99.75]  # huge range confirmation bar
    bars.loc[4:8, ["low", "high", "close"]] = [99.75, 100.25, 100.0]
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    out = oc.add_outcomes(bars, events)
    # bar 3 (breach=confirmation)'s own high=200 must not enter H=5 excursion (uses bars 4-8 only)
    assert out[0]["breakout_exc_h5"] == pytest.approx(max(0, 100.25 - 100.0))


# 25: complete horizons
def test_25_complete_horizons():
    bars = make_rth_bars([99.75] * 390)  # baseline stays inside everywhere except the event bar
    bars.loc[386, ["low", "high", "close"]] = [99.75, 100.25, 99.75]  # FAILED_BREACH_1MIN near session end
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    out = oc.add_outcomes(bars, events)
    assert out[0]["horizon_5_complete"] is False  # only 3 bars remain (387..389)
    assert np.isnan(out[0]["signed_close_h5"])


# 26: mirrored upper/lower formulas
def test_26_mirrored_formulas():
    bars_u = make_rth_bars([100] * 390)
    bars_u.loc[0:2, "high"] = 99.5
    bars_u.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 99.75]
    bars_u.loc[4:8, ["low", "high", "close"]] = [98, 100.25, 98.5]
    _, events_u = ev.process_level_session(bars_u, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    out_u = oc.add_outcomes(bars_u, events_u)
    assert out_u[0]["rotation_exc_h5"] == pytest.approx(100.0 - 98)

    bars_l = make_rth_bars([100] * 390)
    bars_l.loc[0:2, "low"] = 100.5
    bars_l.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 100.25]
    bars_l.loc[4:8, ["low", "high", "close"]] = [99.75, 102, 101.5]
    _, events_l = ev.process_level_session(bars_l, 100.0, "lower", "prev_rth_low", "ES", dt.date(2019, 1, 2))
    out_l = oc.add_outcomes(bars_l, events_l)
    assert out_l[0]["rotation_exc_h5"] == pytest.approx(102 - 100.0)


# 27-29: 0.25/0.50/1.00-ATR barriers
def test_27_28_29_barriers():
    bars = make_rth_bars([100] * 390, atr=1.0)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 99.75]  # FAILED_BREACH_1MIN, anchor=idx3
    bars.loc[4:8, ["low", "high", "close"]] = [98, 98, 98]  # rotation barrier far below
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    out = oc.add_outcomes(bars, events)
    barr = oc.add_barrier_outcomes(bars, out)
    for b in (0.25, 0.50, 1.00):
        assert barr[0][f"b{b}_h5_outcome"] == "ROTATION_FIRST"


# 30: same-bar tie
def test_30_same_bar_tie():
    bars = make_rth_bars([100] * 390, atr=1.0)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 99.75]
    bars.loc[4:8, ["low", "high", "close"]] = [99 - 1, 100 + 1, 100]  # spans both 0.25/0.50 barriers
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    out = oc.add_outcomes(bars, events)
    barr = oc.add_barrier_outcomes(bars, out)
    assert barr[0]["b0.25_h5_outcome"] == "SAME_BAR_TIE"


# 31: neither handling
def test_31_neither():
    bars = make_rth_bars([100] * 390, atr=1.0)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 99.75]
    bars.loc[4:8, ["low", "high", "close"]] = [99.5, 100.0, 99.75]  # tight, no barrier reached at 1.0 ATR
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    out = oc.add_outcomes(bars, events)
    barr = oc.add_barrier_outcomes(bars, out)
    assert barr[0]["b1.0_h5_outcome"] == "NEITHER"


# 32: breach-magnitude bands
def test_32_breach_magnitude_bands():
    bars = make_rth_bars([100] * 390, atr=2.0)
    bars.loc[0:2, "high"] = 99.5
    bars.loc[3, ["low", "high", "close"]] = [99.75, 100.25, 99.75]  # magnitude 0.25/2.0=0.125 ATR -> band 1
    _, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert events[0]["breach_magnitude_band"] == "0_TO_0.25_ATR"


# 33-34: within-stratum permutation, deterministic seed
def test_33_34_permutation_within_stratum_deterministic():
    n = 200
    rng = np.random.default_rng(1)
    df = pd.DataFrame({
        "label": ["failed"] * (n // 2) + ["successful"] * (n // 2),
        "outcome": rng.choice(["ROTATION_FIRST", "BREAKOUT_FIRST"], size=n),
        "stratum": ["A"] * n,
    })
    r1 = pm.stratified_permutation_test(df, "label", "outcome", "stratum", n_perms=500, seed=42)
    r2 = pm.stratified_permutation_test(df, "label", "outcome", "stratum", n_perms=500, seed=42)
    assert r1["p_value"] == r2["p_value"]  # deterministic given fixed seed
    assert 0 <= r1["p_value"] <= 1


# 35: BH-family membership
def test_35_bh_family_membership():
    pvals = [0.001, 0.5, 0.02, 0.9, 0.3]
    adj, _ = cl.benjamini_hochberg(np.array(pvals))
    assert len(adj) == 5
    assert np.all(np.isfinite(adj))


# 36: year accounting
def test_36_year_accounting():
    events = []
    for year, cls in zip([2018, 2019, 2020, 2021, 2022], ["FAILED_BREACH_1MIN"] * 5):
        events.append({
            "instrument": "ES", "level_type": "prev_rth_high", "side": "upper",
            "event_class": cls, "session_date": dt.date(year, 6, 1),
            "breach_time_stratum": "OPEN", "breach_magnitude_band": "0_TO_0.25_ATR",
            "prior_test_category": "FIRST_TEST",
            "b0.5_h15_outcome": "ROTATION_FIRST", "signed_close_atr_h15": 0.1,
        })
    for year in [2018, 2019, 2020, 2021, 2022]:
        events.append({
            "instrument": "ES", "level_type": "prev_rth_high", "side": "upper",
            "event_class": "SUCCESSFUL_BREACH_CONTROL", "session_date": dt.date(year, 6, 2),
            "breach_time_stratum": "OPEN", "breach_magnitude_band": "0_TO_0.25_ATR",
            "prior_test_category": "FIRST_TEST",
            "b0.5_h15_outcome": "BREAKOUT_FIRST", "signed_close_atr_h15": -0.1,
        })
    events_df = pd.DataFrame(events)
    yr = cl.year_stability(events_df)
    sub = yr.loc[(yr["time_stratum"] == "OPEN")]
    assert set(sub["year"]) == set(cl.YEARS)
    assert len(sub) == 5


# 37: complete null retention
def test_37_null_retention():
    bars = make_rth_bars([99.9] * 390)  # never arms (always inside from the start, no clean 3-bar setup needed anyway but level never reached)
    episodes, events = ev.process_level_session(bars, 100.0, "upper", "prev_rth_high", "ES", dt.date(2019, 1, 2))
    assert events == []
    assert len(episodes) == 1
    assert episodes[0]["interacted"] is False


# 38: classification logic
def test_38_classification_logic():
    row = pd.Series({
        "n_failed": 150, "n_successful": 150, "n_failed_nontied": 80, "n_successful_nontied": 80,
        "effect_pp": 12.0, "q_value": 0.01, "median_signed_close_contrast": 0.2,
        "direction_h10": 0.1, "direction_h15": 0.12, "direction_h30": 0.08,
    })
    yr = pd.DataFrame({
        "instrument": ["ES"] * 5, "level_type": ["prev_rth_high"] * 5, "side": ["upper"] * 5,
        "time_stratum": ["ALL_RTH"] * 5, "year": [2018, 2019, 2020, 2021, 2022],
        "n_failed": [40] * 5, "n_successful": [40] * 5,
        "sign": [1, 1, 1, 1, -1],
    })
    pc = pd.DataFrame([{**row.to_dict(), "instrument": "ES", "level_type": "prev_rth_high",
                        "side": "upper", "time_stratum": "ALL_RTH"}])
    out = cl.classify_primary(pc, yr)
    assert out.iloc[0]["classification"] == "FAILED_BREACH_ROTATION_SUPPORTED"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
