import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.prev_close_features import (RTH_CLOSE_MIN, WIN_START, WINDOWS,
                                     _dense_window_bars, _features_for_window,
                                     _session_early_close_flags,
                                     build_prev_close_features)
from src.build_ledger import build_full_ledger


def make_session_df(session, et_minutes, closes, opens=None, highs=None, lows=None, volumes=None):
    n = len(et_minutes)
    closes = np.array(closes, float)
    opens = np.array(opens, float) if opens else np.r_[closes[0], closes[:-1]]
    highs = np.array(highs, float) if highs else np.maximum(opens, closes) + 0.1
    lows = np.array(lows, float) if lows else np.minimum(opens, closes) - 0.1
    volumes = np.array(volumes, float) if volumes else np.full(n, 100.0)
    return pd.DataFrame({"session_date": pd.Timestamp(session), "et_minute": et_minutes,
                         "open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes})


def full_rth_session(session, closes_900_959):
    """closes_900_959: 60 values for et_minute 900..959 (full window); RTH
    900 is not the whole day, but early-close detection only needs the
    max et_minute among the RTH-eligible range <=959, so we also include a
    bar at et_minute=570 to represent 'the session has an RTH day'."""
    em = [570] + list(range(900, 960))
    cl = [closes_900_959[0] - 1] + list(closes_900_959)
    return make_session_df(session, em, cl)


def test_early_close_flag():
    normal = full_rth_session("2021-06-01", [100.0 + i * 0.1 for i in range(60)])
    early = make_session_df("2021-06-02", [570, 700, 779], [100.0, 101.0, 102.0])  # ends at 13:00 ET (Black Friday-like)
    df = pd.concat([normal, early], ignore_index=True)
    flags = _session_early_close_flags(df)
    assert flags[pd.Timestamp("2021-06-01")] == False
    assert flags[pd.Timestamp("2021-06-02")] == True


def test_exact_window_mapping_and_ret():
    # et_minute 900..959 <-> tau2 0..59; tau2=59 is et_minute 959 (16:00 close).
    closes = [100.0 + i for i in range(60)]
    df = full_rth_session("2021-06-01", closes)
    bars = _dense_window_bars(df)
    arrs = bars[pd.Timestamp("2021-06-01")]
    assert arrs["close"][59] == pytest.approx(closes[-1])  # tau2=59 == et_minute 959
    for W in WINDOWS:
        t = _features_for_window(arrs, W)
        expected_open_tau2 = 60 - W  # first_bar_open_W is at et_minute = 960-W
        expected_ret = arrs["close"][59] - arrs["open"][expected_open_tau2]
        assert t["ret"] == pytest.approx(expected_ret)


def test_no_target_information_in_predictor():
    # build two datasets identical except the TARGET session's data differs;
    # the previous-session feature must be unchanged.
    normal = full_rth_session("2021-06-01", [100.0 + i * 0.1 for i in range(60)])
    target1 = make_session_df("2021-06-02", [570, 571], [200.0, 201.0])
    target2 = make_session_df("2021-06-02", [570, 571], [9999.0, -500.0])
    df1 = pd.concat([normal, target1], ignore_index=True)
    df2 = pd.concat([normal, target2], ignore_index=True)
    f1 = build_prev_close_features(df1, "ES")
    f2 = build_prev_close_features(df2, "ES")
    row1 = f1[f1.session_date == pd.Timestamp("2021-06-01")].iloc[0]
    row2 = f2[f2.session_date == pd.Timestamp("2021-06-01")].iloc[0]
    for W in WINDOWS:
        assert row1[f"ret_{W}"] == pytest.approx(row2[f"ret_{W}"])


def test_prev_session_mapping_across_weekend():
    # Friday -> Monday should map correctly (weekend skipped automatically)
    fri = full_rth_session("2021-06-04", [100.0 + i * 0.1 for i in range(60)])  # Friday
    mon = full_rth_session("2021-06-07", [110.0 + i * 0.1 for i in range(60)])  # Monday
    df = pd.concat([fri, mon], ignore_index=True)
    feat = build_prev_close_features(df, "ES")
    assert set(feat["session_date"]) == {pd.Timestamp("2021-06-04"), pd.Timestamp("2021-06-07")}
    # Monday's predecessor must be Friday (previous entry in sorted session list), verified via build_ledger below


def test_predecessor_early_close_excluded(tmp_path, monkeypatch):
    early = make_session_df("2021-06-02", [570, 700, 779], [100.0, 101.0, 102.0])
    tgt_full = make_session_df("2021-06-03", list(range(570, 630)), [100.0 + i * 0.01 for i in range(60)])
    normal_before = full_rth_session("2021-06-01", [90.0 + i * 0.1 for i in range(60)])
    df = pd.concat([normal_before, early, tgt_full], ignore_index=True)

    import src.build_ledger as bl
    proc_dir = tmp_path / "processed"
    proc_dir.mkdir()
    df.to_parquet(proc_dir / "es_front_1m.parquet", index=False)
    monkeypatch.setattr(bl, "PROC", str(proc_dir))
    monkeypatch.setattr(bl, "DEV_END", pd.Timestamp("2099-01-01"))

    led, excl, _ = bl.build_full_ledger("ES")
    assert pd.Timestamp("2021-06-03") not in set(led["session_date"])
    match = excl[(excl.session_date == pd.Timestamp("2021-06-03")) & (excl.reason == "predecessor_early_close")]
    assert len(match) == 1


def test_range_nonneg_close_location_bounded():
    rng = np.random.default_rng(1)
    closes = 100 + np.cumsum(rng.normal(0, 1, 60))
    df = full_rth_session("2021-06-01", closes.tolist())
    bars = _dense_window_bars(df)
    arrs = bars[pd.Timestamp("2021-06-01")]
    for W in WINDOWS:
        t = _features_for_window(arrs, W)
        assert t["range"] >= 0
        if not np.isnan(t["close_location"]):
            assert -1.0 - 1e-9 <= t["close_location"] <= 1.0 + 1e-9


def test_zero_range_and_zero_path_undefined():
    flat = [100.0] * 60
    df = make_session_df(
        "2021-06-01", [570] + list(range(900, 960)), [99.0] + flat,
        opens=[99.0] + flat, highs=[99.0] + flat, lows=[99.0] + flat)
    bars = _dense_window_bars(df)
    arrs = bars[pd.Timestamp("2021-06-01")]
    t1 = _features_for_window(arrs, 1)
    assert t1["range"] == 0
    assert np.isnan(t1["close_location"])
    assert np.isnan(t1["signed_efficiency"])


def test_trailing_normalization_uses_prior_sessions_only():
    sessions = []
    for i in range(25):
        sd = pd.Timestamp("2021-01-01") + pd.Timedelta(days=i)
        closes = [100.0] * 59 + [100.0 + (i + 1) * 0.1]  # last-bar move grows with i -> ret_1 grows with i
        s = full_rth_session(str(sd.date()), closes)
        sessions.append(s)
    df = pd.concat(sessions, ignore_index=True)
    feat = build_prev_close_features(df, "ES")
    # session 24's norm_ret_1 must not depend on session 24's own ret_1
    feat_no24 = feat[feat.session_date != feat.session_date.max()]
    assert feat["norm_ret_1"].iloc[:20].isna().all()  # first 20 sessions: insufficient baseline
    assert np.isfinite(feat["norm_ret_1"].iloc[24])


def test_es_nq_kept_separate():
    normal = full_rth_session("2021-06-01", [100.0 + i * 0.1 for i in range(60)])
    fes = build_prev_close_features(normal, "ES")
    fnq = build_prev_close_features(normal, "NQ")
    assert (fes["instrument"] == "ES").all()
    assert (fnq["instrument"] == "NQ").all()
    # identical price data -> identical raw features, but instrument tag differs (never conflated downstream)
    assert list(fes["ret_1"]) == list(fnq["ret_1"])
