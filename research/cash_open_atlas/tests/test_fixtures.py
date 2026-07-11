import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.atlas import (ANCHOR_MINUTE, PRIMARY_HORIZONS, SECONDARY_HORIZON,
                       _targets_for_window, build_dense_bars, build_session_ledger)


def make_df(session, closes, opens=None, highs=None, lows=None, start_min=ANCHOR_MINUTE):
    n = len(closes)
    closes = np.array(closes, float)
    opens = np.array(opens, float) if opens else np.r_[closes[0], closes[:-1]]
    highs = np.array(highs, float) if highs else np.maximum(opens, closes) + 0.1
    lows = np.array(lows, float) if lows else np.minimum(opens, closes) - 0.1
    return pd.DataFrame({
        "session_date": pd.Timestamp(session), "et_minute": [start_min + i for i in range(n)],
        "open": opens, "high": highs, "low": lows, "close": closes,
    })


def test_horizon_bar_mapping_exact():
    # 61 bars (tau 0..60 not needed, only 0..59); place a distinctive value
    # at each tau so we can prove Close_h == close(tau=h-1).
    closes = [100.0 + i for i in range(60)]
    df = make_df("2021-03-15", closes)
    bars = build_dense_bars(df, tau_max=59)
    arrs = bars[pd.Timestamp("2021-03-15")]
    O = arrs["open"][0]
    for h, expected_tau in [(1, 0), (3, 2), (5, 4), (10, 9), (15, 14), (30, 29), (60, 59)]:
        t = _targets_for_window(arrs, O, n_bars=h)
        assert t["R"] == pytest.approx(closes[expected_tau] - O)


def test_no_lookahead_beyond_horizon():
    closes = [100.0] * 60
    df = make_df("2021-03-15", closes)
    bars1 = build_dense_bars(df, tau_max=59)
    arrs1 = bars1[pd.Timestamp("2021-03-15")]
    O = arrs1["open"][0]
    t5_before = _targets_for_window(arrs1, O, n_bars=5)

    closes2 = list(closes)
    closes2[10] = 999.0  # change a bar strictly AFTER h=5's window (tau=10 > 4)
    df2 = make_df("2021-03-15", closes2)
    bars2 = build_dense_bars(df2, tau_max=59)
    arrs2 = bars2[pd.Timestamp("2021-03-15")]
    t5_after = _targets_for_window(arrs2, O, n_bars=5)
    assert t5_before == t5_after  # h=5 target must be unaffected by tau=10


def test_one_row_per_instrument_session_and_primary_exclusion():
    sessions = []
    for i in range(3):
        sd = f"2021-03-{15+i}"
        closes = [100.0 + i] * 60
        sessions.append(make_df(sd, closes))
    # third session missing a bar inside the primary window (tau=20)
    df3 = sessions[2].copy()
    df3 = df3[df3["et_minute"] != ANCHOR_MINUTE + 20]
    df = pd.concat([sessions[0], sessions[1], df3], ignore_index=True)
    bars = build_dense_bars(df, tau_max=59)
    led, missing = build_session_ledger(bars, "ES")
    assert len(led) == led["session_date"].nunique() == 2  # one row per session; incomplete one excluded
    assert (missing["reason"] == "incomplete_0930_0959_window").any()


def test_secondary_missing_does_not_remove_primary_session():
    sd = "2021-03-15"
    closes = [100.0] * 60
    df = make_df(sd, closes)
    df = df[df["et_minute"] != ANCHOR_MINUTE + 45]  # drop a bar only in the secondary (60-bar) window... wait 45<60
    bars = build_dense_bars(df, tau_max=59)
    led, missing = build_session_ledger(bars, "ES")
    assert len(led) == 1
    assert bool(led["primary_valid"].iloc[0]) is True
    assert bool(led["secondary_valid"].iloc[0]) is False
    assert np.isnan(led["R_60"].iloc[0])
    assert np.isfinite(led["R_30"].iloc[0])  # primary horizon unaffected


def test_U_D_nonnegative_and_Q_bounded():
    rng = np.random.default_rng(0)
    for trial in range(20):
        closes = 100 + np.cumsum(rng.normal(0, 1, 60))
        df = make_df(f"2021-03-{15+trial%10}", closes.tolist())
        # unique session dates required; reuse with offset day won't collide within loop scope
        df["session_date"] = pd.Timestamp("2021-01-01") + pd.Timedelta(days=trial)
        bars = build_dense_bars(df, tau_max=59)
        arrs = list(bars.values())[0]
        O = arrs["open"][0]
        for h in list(PRIMARY_HORIZONS) + [SECONDARY_HORIZON]:
            t = _targets_for_window(arrs, O, n_bars=h)
            assert t["U"] >= 0
            assert t["D"] >= 0
            if not np.isnan(t["Q"]):
                assert -1.0 - 1e-9 <= t["Q"] <= 1.0 + 1e-9


def test_undefined_when_flat():
    closes = [100.0] * 10
    df = make_df("2021-03-15", closes, opens=closes, highs=closes, lows=closes)
    bars = build_dense_bars(df, tau_max=59)
    arrs = bars[pd.Timestamp("2021-03-15")]
    t = _targets_for_window(arrs, arrs["open"][0], n_bars=1)
    assert t["U"] == 0 and t["D"] == 0
    assert np.isnan(t["Q"]) and np.isnan(t["E"])


def test_timestamp_dst_correctness_synthetic():
    # et_minute==570 must map to a single well-defined 09:30 ET bar
    # regardless of calendar date; DST resolution itself is verified below
    # against the real base parquet (generation 1's tz-aware construction).
    df = make_df("2021-03-15", [100.0] * 5)
    bars = build_dense_bars(df, tau_max=59)
    assert pd.Timestamp("2021-03-15") in bars
    arrs = bars[pd.Timestamp("2021-03-15")]
    assert np.isfinite(arrs["open"][0])


def test_timestamp_dst_correctness_real_data():
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    path = os.path.join(repo, "data", "processed", "es_front_1m.parquet")
    if not os.path.exists(path):
        pytest.skip("base parquet not present in this environment")
    df = pd.read_parquet(path, columns=["ts_event", "session_date", "et_minute"])
    # 2021: spring-forward 2021-03-14, fall-back 2021-11-07. The 09:30 ET
    # bar must exist on the surrounding sessions with a UTC offset that
    # actually shifts by an hour across the transition (proving DST, not a
    # fixed offset, was applied).
    for d in ("2021-03-12", "2021-03-15", "2021-11-05", "2021-11-08"):
        sd = pd.Timestamp(d)
        row = df[(df["session_date"] == sd) & (df["et_minute"] == 570)]
        assert len(row) == 1, f"missing/duplicate 09:30 bar on {d}"
    before = df[(df["session_date"] == pd.Timestamp("2021-03-12")) & (df["et_minute"] == 570)]["ts_event"].iloc[0]
    after = df[(df["session_date"] == pd.Timestamp("2021-03-15")) & (df["et_minute"] == 570)]["ts_event"].iloc[0]
    # pre-DST 09:30 ET = 14:30 UTC; post-DST 09:30 ET = 13:30 UTC
    assert before.hour == 14 and after.hour == 13
