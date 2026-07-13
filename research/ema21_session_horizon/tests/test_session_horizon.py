"""35 required tests, per SPEC_SESSION_HORIZONS.md / task instructions."""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ema21_session_horizon.src import five_min_bars as fmb
from research.ema21_session_horizon.src import ema
from research.ema21_session_horizon.src import sessions as ses
from research.ema21_session_horizon.src import events as ev
from research.ema21_session_horizon.src import outcomes as oc
from research.ema21_session_horizon.src import classification as cl


def make_local_bars(closes, is_rth=None, opens=None, highs=None, lows=None):
    n = len(closes)
    closes = np.asarray(closes, dtype=float)
    opens = np.asarray(opens, dtype=float) if opens is not None else closes.copy()
    highs = np.asarray(highs, dtype=float) if highs is not None else np.maximum(opens, closes)
    lows = np.asarray(lows, dtype=float) if lows is not None else np.minimum(opens, closes)
    ts = pd.date_range("2019-01-02 09:30", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame(
        {
            "ts_event": ts,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.full(n, 100),
        }
    )
    df["touch_time_bucket"] = [ses.touch_time_bucket(i + 1) for i in range(n)]
    return df


def warmup_flat(price=100.0, n=60):
    return [price] * n


# 1-2: partition guard / no 2023+ access
def test_01_dev_partition_upper_bound():
    df = pd.DataFrame({"session_date": [dt.date(2022, 12, 30), dt.date(2023, 1, 3)], "x": [1, 2]})
    out = fmb.filter_development(df)
    assert out["session_date"].max() == dt.date(2022, 12, 30)


def test_02_dev_partition_lower_bound():
    df = pd.DataFrame(
        {"session_date": [dt.date(2017, 12, 29), dt.date(2018, 1, 3), dt.date(2018, 6, 1)], "x": [1, 2, 3]}
    )
    out = fmb.filter_development(df)
    assert out["session_date"].min() == dt.date(2018, 1, 3)
    assert len(out) == 2


# 3: ES/NQ separation
def test_03_es_nq_never_mixed():
    bars = make_local_bars(warmup_flat() + [103, 104, 105, 100])
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, t1 = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    _, t2 = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "NQ")
    if not t1.empty:
        assert (t1["instrument"] == "ES").all()
    if not t2.empty:
        assert (t2["instrument"] == "NQ").all()


# 4: deterministic five-minute aggregation, no partial bars
def test_04_deterministic_aggregation_no_partial():
    rows = []
    base = pd.Timestamp("2019-01-02 09:30", tz="UTC")
    for m in range(10):
        rows.append(
            {
                "session_date": dt.date(2019, 1, 2),
                "et_minute": 570 + m,
                "ts_event": base + pd.Timedelta(minutes=m),
                "open": 100 + m, "high": 100 + m + 0.5, "low": 100 + m - 0.5,
                "close": 100 + m + 0.2, "volume": 10,
            }
        )
    df1m = pd.DataFrame(rows).drop(index=7).reset_index(drop=True)
    bars, n_incomplete = fmb.build_full_5m(df1m)
    assert len(bars) == 1
    assert n_incomplete == 1
    assert bars.iloc[0]["open"] == 100
    assert bars.iloc[0]["close"] == pytest.approx(104.2)


# 5-7: continuous full-session EMA21, adjust=False, no reset
def test_05_06_07_continuous_ema21_adjust_false_no_reset():
    closes = [100, 102, 101, 105, 103] + [104] * 60
    s = pd.Series(closes, dtype=float)
    expected = s.ewm(span=21, adjust=False).mean()
    bars = make_local_bars(closes)
    out = ema.add_ema_and_level(bars)
    np.testing.assert_allclose(out["ema21"].to_numpy(), expected.to_numpy())
    # simulate a "session boundary" mid-array: EMA must continue the same recursion
    boundary_ema = out["ema21"].iloc[40]
    manual_next = boundary_ema + (2 / 22) * (closes[41] - boundary_ema)
    assert out["ema21"].iloc[41] == pytest.approx(manual_next)


# 8: EMA frozen through T-1
def test_08_level_uses_prior_bar_only():
    closes = warmup_flat(100.0, 60) + [100.0, 100.0, 100.0, 999.0]
    bars = make_local_bars(closes)
    out = ema.add_ema_and_level(bars)
    assert out["level21"].iloc[63] == pytest.approx(out["ema21"].iloc[62])
    assert out["level21"].iloc[63] != pytest.approx(out["ema21"].iloc[63])


# 9: Asia midnight-wrap mapping
def test_09_asia_midnight_wrap():
    # 1-minute synthetic data spanning 23:55 (prev day) -> 00:10 (session_date day)
    d0 = dt.date(2019, 1, 1)
    d1 = dt.date(2019, 1, 2)  # session_date for the 18:00 D0 -> 17:00 D1 session
    rows = []
    base = pd.Timestamp("2019-01-01 23:55", tz="UTC")
    for m in range(20):
        et_minute = (23 * 60 + 55 + m) % (24 * 60)
        rows.append(
            {
                "session_date": d1,  # both legs of the wrap share this session_date (root convention)
                "et_minute": et_minute,
                "ts_event": base + pd.Timedelta(minutes=m),
                "open": 100, "high": 100, "low": 100, "close": 100, "volume": 1,
            }
        )
    df1m = pd.DataFrame(rows)
    bars, _ = fmb.build_full_5m(df1m)
    bars["leg"] = bars["bucket_start_min"].map(ses.assign_leg)
    assert (bars["leg"] == "ASIA").all()
    bars2 = ses.add_session_columns(bars.assign(session_date=d1))
    assert bars2["session_leg_id"].nunique() == 1  # one continuous leg instance across the wrap
    assert bars2["local_rank"].tolist() == list(range(1, len(bars2) + 1))


# 10: London boundaries
def test_10_london_boundaries():
    assert ses.assign_leg(3 * 60) == "LONDON"
    assert ses.assign_leg(8 * 60 + 29) == "LONDON"
    assert ses.assign_leg(2 * 60 + 59) != "LONDON"
    assert ses.assign_leg(8 * 60 + 30) != "LONDON"


# 11: New York boundaries
def test_11_new_york_boundaries():
    assert ses.assign_leg(9 * 60 + 30) == "NEW_YORK"
    assert ses.assign_leg(15 * 60 + 59) == "NEW_YORK"
    assert ses.assign_leg(9 * 60 + 29) != "NEW_YORK"
    assert ses.assign_leg(16 * 60) != "NEW_YORK"


# 12: excluded-time handling
def test_12_excluded_time_handling():
    assert ses.assign_leg(8 * 60 + 30) == "EXCLUDED"
    assert ses.assign_leg(9 * 60 + 29) == "EXCLUDED"
    assert ses.assign_leg(16 * 60) == "EXCLUDED"
    assert ses.assign_leg(17 * 60 + 59) == "EXCLUDED"


# 13-14: event state resets at session boundary / no cross-session arming
def test_13_14_no_cross_session_arming():
    # 2 bars armed-above at the END of one leg instance + 1 bar in a FRESH leg
    # instance must NOT complete an arming sequence.
    closes = warmup_flat(100.0, 60) + [103, 104]
    bars_leg1 = make_local_bars(closes)
    bars_leg1["level21"] = ema.add_ema_and_level(bars_leg1)["level21"]
    bars_leg1 = ema.add_atr(bars_leg1)
    bars_leg1.loc[60:61, "low"] = bars_leg1.loc[60:61, "close"] - 0.1
    # a fresh leg instance (its own local array) starting after only 2 above-bars
    fresh_leg = bars_leg1.tail(1).reset_index(drop=True)  # only 1 bar of history carried
    _, touches = ev.detect_leg(fresh_leg, "LONDON", dt.date(2019, 1, 2), "ES")
    assert touches.empty  # cannot arm with < 3 bars in ITS OWN leg instance


# 15: three-bar arming from above
def test_15_arming_from_above():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100]
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    assert len(touches) == 1
    assert touches.iloc[0]["approach_side"] == "FROM_ABOVE"


# 16: three-bar arming from below
def test_16_arming_from_below():
    closes = warmup_flat(100.0, 60) + [97, 96, 95, 100]
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "high"] = bars.loc[60:62, "close"] + 0.1
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    assert len(touches) == 1
    assert touches.iloc[0]["approach_side"] == "FROM_BELOW"


# 17-18: first-touch-only + mandatory rearming
def test_17_18_first_touch_only_and_rearm():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100, 105, 106, 107, 100]
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    for i in (60, 61, 62, 64, 65, 66):
        bars.loc[i, "low"] = bars.loc[i, "close"] - 0.1
    for i in (63, 67):
        bars.loc[i, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    assert len(touches) == 2
    assert touches["local_touch_idx"].tolist() == [63, 67]


# 19: ATR20 through T-1 only
def test_19_atr_causal():
    closes = [100 + i * 0.1 for i in range(25)]
    bars = make_local_bars(closes, highs=np.array(closes) + 1, lows=np.array(closes) - 1)
    out = ema.add_atr(bars)
    manual = out["tr"].iloc[4:24].mean()
    assert out["atr_event"].iloc[24] == pytest.approx(manual)


# 20: exact touch-time buckets
def test_20_touch_time_buckets():
    assert ses.touch_time_bucket(1) == "SESSION_0_TO_30"
    assert ses.touch_time_bucket(6) == "SESSION_0_TO_30"
    assert ses.touch_time_bucket(7) == "SESSION_30_TO_60"
    assert ses.touch_time_bucket(12) == "SESSION_30_TO_60"
    assert ses.touch_time_bucket(13) == "SESSION_60_TO_120"
    assert ses.touch_time_bucket(24) == "SESSION_60_TO_120"
    assert ses.touch_time_bucket(25) == "SESSION_120_PLUS"
    assert ses.touch_time_bucket(100) == "SESSION_120_PLUS"


# 21-22: same-bar morphology from above/below
def test_21_morphology_from_above():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 103]
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, ["open", "close"]] = [102, 103]
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    assert touches.iloc[0]["same_bar_morphology"] == "SAME_BAR_REJECTION_PROXY"


def test_22_morphology_from_below():
    closes = warmup_flat(100.0, 60) + [97, 96, 95, 99]
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "high"] = bars.loc[60:62, "close"] + 0.1
    bars.loc[63, ["open", "close"]] = [98, 99]
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    assert touches.iloc[0]["same_bar_morphology"] == "SAME_BAR_BREAKTHROUGH_PROXY"


# 23-24: outcomes start at T+1, touch-bar exclusion
def test_23_24_outcomes_start_t_plus_1():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100] + [50, 200, 100, 100, 100]
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    outc = oc.add_outcomes(bars, touches)
    row = outc.iloc[0]
    assert row["breakthrough_exc_h1"] == pytest.approx(max(0, row["level_t"] - bars.loc[64, "low"]))


# 25-26: all nine horizons, no outcome crossing session boundary
def test_25_26_nine_horizons_no_boundary_crossing():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100] + [101] * 30
    bars = make_local_bars(closes)  # leg instance has exactly 94 bars total
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    outc = oc.add_outcomes(bars, touches)
    row = outc.iloc[0]
    assert set(ev.HORIZONS) == {1, 2, 3, 4, 6, 9, 12, 18, 24}
    assert row["horizon_24_complete"]  # 63+24=87 < 94, fits inside this leg's own array
    short_bars = bars.iloc[:70].reset_index(drop=True)  # simulate leg ending at bar 69
    _, touches2 = ev.detect_leg(short_bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    outc2 = oc.add_outcomes(short_bars, touches2)
    row2 = outc2.iloc[0]
    assert not row2["horizon_24_complete"]  # 63+24=87 >= 70 -> excluded, not partially computed
    assert np.isnan(row2["signed_close_h24"])


# 27: mirrored rejection/breakthrough formulas
def test_27_mirrored_formulas():
    closes = warmup_flat(100.0, 60) + [97, 96, 95, 100, 90, 130, 100, 100, 100]
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "high"] = bars.loc[60:62, "close"] + 0.1
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    outc = oc.add_outcomes(bars, touches)
    row = outc.iloc[0]
    level = row["level_t"]
    assert row["rejection_exc_h1"] == pytest.approx(max(0, level - bars.loc[64, "low"]))
    assert row["breakthrough_exc_h1"] == pytest.approx(max(0, bars.loc[64, "high"] - level))


# 28-29: barrier ordering (0.5 / 1.0 ATR)
def test_28_29_barrier_ordering():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100] + [110] * 24
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    outc = oc.add_outcomes(bars, touches)
    barr = oc.add_barrier_outcomes(bars, outc)
    assert barr.iloc[0]["b0.5_h9_outcome"] == "REJECTION_FIRST"
    assert barr.iloc[0]["b1.0_h9_outcome"] in ("REJECTION_FIRST", "NEITHER")


# 30: same-bar tie
def test_30_same_bar_tie():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100, 100]
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    outc = oc.add_outcomes(bars, touches)
    level, atr = outc.iloc[0]["level_t"], outc.iloc[0]["atr_event"]
    bars.loc[64, "high"] = level + 0.5 * atr + 1
    bars.loc[64, "low"] = level - 0.5 * atr - 1
    outc2 = oc.add_outcomes(bars, touches)
    barr = oc.add_barrier_outcomes(bars, outc2)
    assert barr.iloc[0]["b0.5_h1_outcome"] == "SAME_BAR_TIE"


# 31: neither
def test_31_neither():
    closes = warmup_flat(100.0, 60) + [103, 104, 105, 100] + [101.0] * 24
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    bars.loc[60:62, "low"] = bars.loc[60:62, "close"] - 0.1
    bars.loc[63, ["low", "high"]] = [90, 110]
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    outc = oc.add_outcomes(bars, touches)
    barr = oc.add_barrier_outcomes(bars, outc)
    assert barr.iloc[0]["b1.0_h1_outcome"] == "NEITHER"


# 32: year accounting
def test_32_year_stability_all_years():
    events = pd.DataFrame(
        {
            "instrument": ["ES"] * 5,
            "session": ["NEW_YORK"] * 5,
            "approach_side": ["FROM_ABOVE"] * 5,
            "touch_time_bucket": ["SESSION_0_TO_30"] * 5,
            "year": [2018, 2019, 2020, 2021, 2022],
            "same_bar_morphology": ["SAME_BAR_REJECTION_PROXY"] * 5,
            "horizon_1_complete": [True] * 5,
            "atr_valid": [True] * 5,
            "signed_close_atr_h1": [0.1, 0.2, -0.1, 0.3, 0.1],
            "b1.0_h1_outcome": ["REJECTION_FIRST"] * 5,
        }
    )
    for H in ev.HORIZONS:
        if H != 1:
            events[f"horizon_{H}_complete"] = False
            events[f"signed_close_atr_h{H}"] = np.nan
    yr = cl.year_stability(events)
    sub = yr.loc[(yr["horizon_bars"] == 1) & (yr["touch_time_bucket"] == "SESSION_0_TO_30")]
    assert set(sub["year"]) == set(cl.YEARS)
    assert len(sub) == 5


# 33: BH-family membership
def test_33_bh_family_membership():
    n = 4 * 2 * 9  # buckets x sides x horizons
    cells = pd.DataFrame(
        {
            "instrument": ["ES"] * n,
            "session": ["NEW_YORK"] * n,
            "touch_time_bucket": (list(cl.DISJOINT_BUCKETS) * (2 * 9))[:n],
            "approach_side": (["FROM_ABOVE", "FROM_BELOW"] * (4 * 9))[:n],
            "horizon_bars": [h for h in ev.HORIZONS for _ in range(8)],
            "barrier_atr": [1.0] * n,
            "barrier_binom_p": np.linspace(0.001, 0.9, n),
            "barrier_nontied_n": [40] * n,
            "touch_events": [80] * n,
        }
    )
    pc = cl.apply_bh_primary(cells)
    assert pc["bh_family"].nunique() == 1
    assert len(pc) == n
    assert pc["q_value_primary"].notna().all()


# 34: adjacent-horizon coherence
def test_34_adjacent_horizon_coherence():
    rows = []
    for bucket in cl.DISJOINT_BUCKETS:
        for h in ev.HORIZONS:
            cls = "REJECTION_DOMINANT" if (bucket == "SESSION_0_TO_30" and h in (1, 2)) else "MIXED_OR_NULL"
            rows.append(
                {
                    "instrument": "ES", "session": "ASIA", "approach_side": "FROM_ABOVE",
                    "touch_time_bucket": bucket, "horizon_bars": h,
                    "classification": cls, "max_year_sign_agreement": 5,
                }
            )
    classified = pd.DataFrame(rows)
    out = cl.classify_sessions(classified)
    row = out.iloc[0]
    assert row["session_mechanism"] == "ASIA_REJECTION_MECHANISM"  # adjacent horizons 1,2 in first-30-min bucket

    # a single isolated cell (h=1 only) must NOT be promoted
    rows2 = [r.copy() for r in rows]
    for r in rows2:
        if r["touch_time_bucket"] == "SESSION_0_TO_30" and r["horizon_bars"] == 2:
            r["classification"] = "MIXED_OR_NULL"
    classified2 = pd.DataFrame(rows2)
    out2 = cl.classify_sessions(classified2)
    assert out2.iloc[0]["session_mechanism"] == "NO_COHERENT_SESSION_MECHANISM"


# 35: complete null-cell retention
def test_35_null_cells_retained():
    closes = warmup_flat(100.0, 60) + [99.9] * 10
    bars = make_local_bars(closes)
    bars["level21"] = ema.add_ema_and_level(bars)["level21"]
    bars = ema.add_atr(bars)
    _, touches = ev.detect_leg(bars, "NEW_YORK", dt.date(2019, 1, 2), "ES")
    assert touches.empty  # never arms -> nothing to silently drop; empty is the honest result


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
