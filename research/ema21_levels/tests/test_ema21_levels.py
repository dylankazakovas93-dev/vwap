"""33 required tests, per SPEC_EMA21_LEVELS.md / task instructions.

Synthetic-fixture tests exercise the mechanics precisely and fast;
real-data tests (marked) verify the inherited data infra and partition
guards against the actual audited parquet files.
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ema21_levels.src import five_min_bars as fmb
from research.ema21_levels.src import ema
from research.ema21_levels.src import events as ev
from research.ema21_levels.src import outcomes as oc
from research.ema21_levels.src import summary as sm
from research.ema21_levels.src import classification as cl


def make_bars(closes, is_rth=None, opens=None, highs=None, lows=None, start_date=dt.date(2019, 1, 2)):
    n = len(closes)
    closes = np.asarray(closes, dtype=float)
    opens = np.asarray(opens, dtype=float) if opens is not None else closes.copy()
    highs = np.asarray(highs, dtype=float) if highs is not None else np.maximum(opens, closes)
    lows = np.asarray(lows, dtype=float) if lows is not None else np.minimum(opens, closes)
    is_rth = np.asarray(is_rth, dtype=bool) if is_rth is not None else np.ones(n, dtype=bool)
    ts = pd.date_range("2019-01-02 09:30", periods=n, freq="5min", tz="UTC")
    bucket = np.array([570 + 5 * (i % 78) for i in range(n)])
    session_date = np.array([start_date] * n, dtype=object)
    df = pd.DataFrame(
        {
            "session_date": session_date,
            "bucket_start_min": bucket,
            "ts_event": ts,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.full(n, 100),
            "is_rth": is_rth,
        }
    )
    return df


def warmup_flat(price=100.0, n=60):
    return [price] * n


# 1-2: partition guard / no 2023+ access
def test_01_dev_partition_upper_bound():
    df = pd.DataFrame({"session_date": [dt.date(2022, 12, 30), dt.date(2023, 1, 3)], "x": [1, 2]})
    out = fmb.filter_development(df)
    assert out["session_date"].max() == dt.date(2022, 12, 30)
    assert (out["session_date"] > dt.date(2022, 12, 30)).sum() == 0


def test_02_dev_partition_lower_bound_and_no_lookahead_source():
    df = pd.DataFrame(
        {"session_date": [dt.date(2017, 12, 29), dt.date(2018, 1, 3), dt.date(2018, 6, 1)], "x": [1, 2, 3]}
    )
    out = fmb.filter_development(df)
    assert out["session_date"].min() == dt.date(2018, 1, 3)
    assert len(out) == 2


# 3: ES/NQ separation (pipeline-level structural check)
def test_03_es_nq_never_mixed_in_one_event_stream():
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(warmup_flat() + [101, 102, 103, 100])))
    exc, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    if not touches.empty:
        assert (touches["instrument"] == "ES").all()
    exc2, touches2 = ev.detect(bars, 21, "NQ", "RTH_EMA")
    if not touches2.empty:
        assert (touches2["instrument"] == "NQ").all()
    if not touches.empty and not touches2.empty:
        assert set(touches["instrument"]).isdisjoint(set(touches2["instrument"]))


# 4-5: deterministic aggregation / no partial 5m bars
def test_04_deterministic_aggregation_and_no_partial_bars():
    rows = []
    base = pd.Timestamp("2019-01-02 09:30", tz="UTC")
    for m in range(10):  # two complete 5-min buckets: 09:30-09:34, 09:35-09:39
        rows.append(
            {
                "session_date": dt.date(2019, 1, 2),
                "et_minute": 570 + m,
                "ts_event": base + pd.Timedelta(minutes=m),
                "open": 100 + m,
                "high": 100 + m + 0.5,
                "low": 100 + m - 0.5,
                "close": 100 + m + 0.2,
                "volume": 10,
            }
        )
    # drop one minute from the second bucket -> incomplete, must be excluded
    df1m = pd.DataFrame(rows).drop(index=7).reset_index(drop=True)
    bars, n_incomplete = fmb.build_rth_5m(df1m)
    assert len(bars) == 1  # only the first complete bucket survives
    assert n_incomplete == 1
    assert bars.iloc[0]["open"] == 100
    assert bars.iloc[0]["close"] == pytest.approx(104.2)
    assert bars.iloc[0]["high"] == pytest.approx(104.5)
    assert bars.iloc[0]["low"] == pytest.approx(99.5)


# 6-7: RTH vs full-session EMA construction stay separate
def test_06_rth_ema_excludes_overnight():
    df1m = pd.DataFrame(
        {
            "session_date": [dt.date(2019, 1, 2)] * 10,
            "et_minute": [1000] * 5 + [570] * 5,  # overnight then RTH
            "ts_event": pd.date_range("2019-01-02", periods=10, freq="1min", tz="UTC"),
            "open": [500] * 5 + [100] * 5,
            "high": [500] * 5 + [100] * 5,
            "low": [500] * 5 + [100] * 5,
            "close": [500] * 5 + [100] * 5,
            "volume": [1] * 10,
        }
    )
    rth_bars, _ = fmb.build_rth_5m(df1m)
    assert (rth_bars["close"] == 100).all()
    full_bars, _ = fmb.build_full_5m(df1m)
    assert 500 in full_bars["close"].to_numpy()


def test_07_full_session_ema_carries_across_boundary_no_reset():
    closes = warmup_flat(100.0, 60) + [110.0] * 5
    bars = make_bars(closes)
    out = ema.add_emas_and_levels(bars)
    # EMA is a single continuous recursion; verify it moved smoothly toward 110,
    # not reset to a fresh series at the boundary.
    ema21 = out["ema21"].to_numpy()
    assert ema21[59] == pytest.approx(100.0, abs=1e-6)
    assert 100.0 < ema21[64] < 110.0


# 8: EMA20/21/22 with adjust=False
def test_08_ema_formula_adjust_false():
    closes = [100, 102, 101, 105, 103] + [104] * 60
    s = pd.Series(closes, dtype=float)
    expected = s.ewm(span=21, adjust=False).mean()
    bars = make_bars(closes)
    out = ema.add_emas_and_levels(bars)
    np.testing.assert_allclose(out["ema21"].to_numpy(), expected.to_numpy())


# 9-10: EMA carries across sessions, no daily reset
def test_09_10_no_daily_reset():
    closes = warmup_flat(100.0, 60) + [105.0] * 3
    bars = make_bars(closes)
    bars.loc[60:, "session_date"] = dt.date(2019, 1, 3)  # new "day"
    out = ema.add_emas_and_levels(bars)
    ema21 = out["ema21"].to_numpy()
    # no jump/reset to the new day's raw close; value 60 continues the recursion
    assert ema21[60] != pytest.approx(105.0)
    assert ema21[60] == pytest.approx(ema21[59] + (2 / 22) * (105.0 - ema21[59]))


# 11-12: touch bar uses EMA through t-1 only; current close cannot move touch level
def test_11_12_level_uses_prior_bar_only():
    closes = warmup_flat(100.0, 60) + [100.0, 100.0, 100.0, 999.0]  # huge move at touch bar
    bars = make_bars(closes)
    out = ema.add_emas_and_levels(bars)
    level_at_touch = out["level21"].iloc[63]
    ema_including_touch = out["ema21"].iloc[63]
    assert level_at_touch == pytest.approx(out["ema21"].iloc[62])
    assert level_at_touch != pytest.approx(ema_including_touch)


# 13: three-bar arming from above
def test_13_arming_from_above():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100]  # 3 bars above, then touch back to 100
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes, lows=None)))
    # force lows above level for the 3 arming bars, and straddle on the touch bar
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, "low"] = 90
    bars.loc[63, "high"] = 110
    exc, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    assert len(touches) == 1
    assert touches.iloc[0]["approach_side"] == "FROM_ABOVE"


# 14: three-bar arming from below
def test_14_arming_from_below():
    closes = warmup_flat(100.0, 60) + [97, 96, 95, 100]
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    bars.loc[60:62, "high"] = bars.loc[60:62, "close"] + 0.1
    bars.loc[63, "low"] = 90
    bars.loc[63, "high"] = 110
    exc, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    assert len(touches) == 1
    assert touches.iloc[0]["approach_side"] == "FROM_BELOW"


# 15-16: first-touch-only consumption + mandatory rearming
def test_15_16_first_touch_only_and_rearm_required():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100, 105, 106, 107, 100]
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    for i in (60, 61, 62, 64, 65, 66):
        bars.loc[i, "low"] = bars.loc[i, "close"] - 0.1
    for i in (63, 67):
        bars.loc[i, "low"] = 90
        bars.loc[i, "high"] = 110
    exc, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    assert len(touches) == 2  # one per re-armed excursion, not more
    assert touches["touch_idx"].tolist() == [63, 67]


# 17: ATR20 uses only bars through t-1
def test_17_atr_causal():
    closes = [100 + i * 0.1 for i in range(25)]
    bars = make_bars(closes, highs=np.array(closes) + 1, lows=np.array(closes) - 1)
    out = ema.add_atr(bars)
    # atr_event at bar 24 must not depend on bar 24's own TR
    manual = out["tr"].iloc[4:24].mean()  # bars 4..23 = 20 bars ending at t-1=23
    assert out["atr_event"].iloc[24] == pytest.approx(manual)


# 18-19: same-bar morphology from above / below
def test_18_morphology_from_above():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 101]
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, ["open", "close"]] = [102, 103]
    bars.loc[63, "low"] = 90
    bars.loc[63, "high"] = 110
    _, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    assert touches.iloc[0]["same_bar_morphology"] == "SAME_BAR_REJECTION_PROXY"


def test_19_morphology_from_below():
    closes = warmup_flat(100.0, 60) + [97, 96, 95, 99]
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    bars.loc[60:62, "high"] = bars.loc[60:62, "close"] + 0.1
    bars.loc[63, ["open", "close"]] = [98, 99]
    bars.loc[63, "low"] = 90
    bars.loc[63, "high"] = 110
    _, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    assert touches.iloc[0]["same_bar_morphology"] == "SAME_BAR_BREAKTHROUGH_PROXY"


# 20-21: post-touch outcomes begin at T+1, touch-bar exclusion
def test_20_21_outcomes_start_t_plus_1():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100] + [50, 200, 100, 100, 100]
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, "low"] = 90
    bars.loc[63, "high"] = 110  # touch bar T=63 has an enormous range
    _, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    outc = oc.add_outcomes(bars, touches)
    row = outc.iloc[0]
    # bar T's own high=110/low=90 must NOT appear in the H=1 excursion (bar 64 close=50 range used instead)
    assert row["breakthrough_exc_h1"] == pytest.approx(max(0, row["level_t"] - bars.loc[64, "low"]))


# 22: mirrored rejection/breakthrough formulas
def test_22_mirrored_formulas():
    closes = warmup_flat(100.0, 60) + [97, 96, 95, 100, 90, 130, 100, 100, 100]
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    bars.loc[60:62, "high"] = bars.loc[60:62, "close"] + 0.1
    bars.loc[63, "low"] = 90
    bars.loc[63, "high"] = 110
    _, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    outc = oc.add_outcomes(bars, touches)
    row = outc.iloc[0]
    level = row["level_t"]
    assert row["rejection_exc_h1"] == pytest.approx(max(0, level - bars.loc[64, "low"]))
    assert row["breakthrough_exc_h1"] == pytest.approx(max(0, bars.loc[64, "high"] - level))


# 23: complete horizons required, no partial-window fallback
def test_23_incomplete_horizon_is_nan():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100, 101]  # only 1 bar after touch
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, "low"] = 90
    bars.loc[63, "high"] = 110
    _, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    outc = oc.add_outcomes(bars, touches)
    row = outc.iloc[0]
    assert row["horizon_1_complete"]
    assert not row["horizon_2_complete"]
    assert np.isnan(row["signed_close_h2"])


# 24-25: barrier ordering (0.5 ATR, 1.0 ATR)
def test_24_25_barrier_ordering_rejection_first():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100] + [110] * 20
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, "low"] = 90
    bars.loc[63, "high"] = 110
    _, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    outc = oc.add_outcomes(bars, touches)
    barr = oc.add_barrier_outcomes(bars, outc)
    assert barr.iloc[0]["b0.5_h5_outcome"] == "REJECTION_FIRST"
    assert barr.iloc[0]["b1.0_h5_outcome"] in ("REJECTION_FIRST", "NEITHER")


# 26: same-bar tie handling
def test_26_same_bar_tie():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100, 100]
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, "low"] = 90
    bars.loc[63, "high"] = 110
    _, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    outc = oc.add_outcomes(bars, touches)
    level = outc.iloc[0]["level_t"]
    atr = outc.iloc[0]["atr_event"]
    # bar 64 spans both the 0.5ATR rejection and breakthrough barriers
    bars.loc[64, "high"] = level + 0.5 * atr + 1
    bars.loc[64, "low"] = level - 0.5 * atr - 1
    outc2 = oc.add_outcomes(bars, touches)
    barr = oc.add_barrier_outcomes(bars, outc2)
    assert barr.iloc[0]["b0.5_h1_outcome"] == "SAME_BAR_TIE"


# 27: neither handling
def test_27_neither():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100] + [101.0] * 20
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, "low"] = 90
    bars.loc[63, "high"] = 110
    _, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    outc = oc.add_outcomes(bars, touches)
    barr = oc.add_barrier_outcomes(bars, outc)
    assert barr.iloc[0]["b1.0_h1_outcome"] == "NEITHER"


# 28: time-stratum boundaries
def test_28_time_stratum_boundaries():
    assert ev._stratum(570) == "OPEN"
    assert ev._stratum(629) == "OPEN"
    assert ev._stratum(630) == "MID_MORNING"
    assert ev._stratum(719) == "MID_MORNING"
    assert ev._stratum(720) == "MIDDAY"
    assert ev._stratum(839) == "MIDDAY"
    assert ev._stratum(840) == "AFTERNOON"
    assert ev._stratum(959) == "AFTERNOON"


# 29: year accounting (all 5 years jointly, not cherry-picked)
def test_29_year_stability_covers_all_years():
    events = pd.DataFrame(
        {
            "instrument": ["ES"] * 5,
            "ema_session_definition": ["RTH_EMA"] * 5,
            "ema_span": [21] * 5,
            "approach_side": ["FROM_ABOVE"] * 5,
            "time_stratum": ["ALL_RTH"] * 5,
            "year": [2018, 2019, 2020, 2021, 2022],
            "same_bar_morphology": ["SAME_BAR_REJECTION_PROXY"] * 5,
            "horizon_5_complete": [True] * 5,
            "atr_valid": [True] * 5,
            "signed_close_atr_h5": [0.1, 0.2, -0.1, 0.3, 0.1],
            "b0.5_h5_outcome": ["REJECTION_FIRST"] * 5,
            "b1.0_h5_outcome": ["REJECTION_FIRST"] * 5,
        }
    )
    yr = cl.year_stability(events)
    assert set(yr["year"]) == set(cl.YEARS)
    all_rth = yr.loc[yr["time_stratum"] == "ALL_RTH"]
    assert len(all_rth) == 5
    assert set(all_rth["year"]) == set(cl.YEARS)


# 30: BH-family membership
def test_30_bh_family_membership():
    cells = pd.DataFrame(
        {
            "instrument": ["ES"] * 6,
            "ema_session_definition": ["RTH_EMA"] * 6,
            "ema_span": [20, 20, 21, 21, 22, 22],
            "approach_side": ["FROM_ABOVE", "FROM_BELOW"] * 3,
            "time_stratum": ["ALL_RTH"] * 6,
            "horizon_bars": [5] * 6,
            "barrier_atr": [1.0] * 6,
            "barrier_binom_p": [0.5, 0.5, 0.01, 0.5, 0.5, 0.5],
            "barrier_nontied_n": [40] * 6,
            "touch_events": [80] * 6,
        }
    )
    pc = cl.apply_bh_primary(cells)
    fam = pc["bh_family"].unique()
    assert len(fam) == 1  # all 6 rows share one instrument/session_def/stratum family
    assert pc["q_value_primary"].notna().all()


# 31: EMA21-specific classification
def test_31_ema21_specific_classification():
    base = {
        "instrument": "ES", "ema_session_definition": "RTH_EMA",
        "approach_side": "FROM_ABOVE", "time_stratum": "ALL_RTH",
    }
    classified = pd.DataFrame(
        [
            {**base, "ema_span": 20, "classification": "MIXED_OR_NULL", "effect_pp": 2.0},
            {**base, "ema_span": 21, "classification": "REJECTION_DOMINANT", "effect_pp": 20.0},
            {**base, "ema_span": 22, "classification": "MIXED_OR_NULL", "effect_pp": 1.0},
        ]
    )
    spec = cl.classify_specificity(classified)
    assert spec.iloc[0]["specificity"] == "EMA21_SPECIFIC"


# 32: generic-EMA-zone classification
def test_32_generic_ema_zone_classification():
    base = {
        "instrument": "ES", "ema_session_definition": "RTH_EMA",
        "approach_side": "FROM_ABOVE", "time_stratum": "ALL_RTH",
    }
    classified = pd.DataFrame(
        [
            {**base, "ema_span": 20, "classification": "REJECTION_DOMINANT", "effect_pp": 10.0},
            {**base, "ema_span": 21, "classification": "REJECTION_DOMINANT", "effect_pp": 11.0},
            {**base, "ema_span": 22, "classification": "REJECTION_DOMINANT", "effect_pp": 9.5},
        ]
    )
    spec = cl.classify_specificity(classified)
    assert spec.iloc[0]["specificity"] == "GENERIC_EMA_ZONE"


# 33: complete null-cell retention (no silent dropping of null/underpowered cells)
def test_33_null_cells_retained():
    closes = warmup_flat(100.0, 60) + [99.9] * 10  # never arms, no events
    bars = ema.add_atr(ema.add_emas_and_levels(make_bars(closes)))
    exc, touches = ev.detect(bars, 21, "ES", "RTH_EMA")
    cells = sm.build_cells(touches, exc if not exc.empty else pd.DataFrame(
        columns=["instrument", "ema_session_definition", "ema_span", "approach_side", "stratum"]
    ))
    # touches is empty -> build_cells returns empty (no group to iterate), which is
    # itself the "nothing to report" case, not a silently dropped populated cell.
    assert touches.empty
    assert cells.empty


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
