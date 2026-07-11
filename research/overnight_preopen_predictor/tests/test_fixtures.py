import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.overnight_features import (PREOPEN_START, RTH_OPEN_MIN, WINDOWS,
                                    _dense_preopen_bars,
                                    _overnight_features_one_session,
                                    _session_early_close_flags,
                                    _window_feature, build_overnight_ledger)
from src.build_ledger import build_full_ledger


def make_bars(session, et_minutes, closes, opens=None, highs=None, lows=None, volumes=None):
    n = len(et_minutes)
    closes = np.array(closes, float)
    opens = np.array(opens, float) if opens else np.r_[closes[0], closes[:-1]]
    highs = np.array(highs, float) if highs else np.maximum(opens, closes) + 0.1
    lows = np.array(lows, float) if lows else np.minimum(opens, closes) - 0.1
    volumes = np.array(volumes, float) if volumes else np.full(n, 100.0)
    return pd.DataFrame({"session_date": pd.Timestamp(session), "et_minute": et_minutes,
                         "open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes,
                         "ts_event": pd.date_range("2000-01-01", periods=n, freq="min")})


def full_session(session, n_overnight=40, target_closes=None, full_primary_window=False):
    """overnight bars at et_minute 1080..1080+n_overnight-1 (well before
    midnight wrap, simplification for unit tests), then 09:30+ bars.
    full_primary_window=True adds the full 30-bar 09:30-09:59 atlas window
    so generation-3's atlas.py can validate the session as a target."""
    on_em = list(range(1080, 1080 + n_overnight))
    on_cl = [100.0 + i * 0.01 for i in range(n_overnight)]
    if full_primary_window:
        tgt_em = list(range(570, 600))
        tgt_cl = [on_cl[-1] + 0.5 + i * 0.01 for i in range(30)]
    else:
        tgt_em = [570, 571]
        tgt_cl = target_closes or [on_cl[-1] + 0.5, on_cl[-1] + 0.6]
    return make_bars(session, on_em + tgt_em, on_cl + tgt_cl)


def test_no_0930_or_later_information_in_overnight_features():
    s1 = full_session("2021-06-01", target_closes=[200.0, 201.0])
    s2 = full_session("2021-06-01", target_closes=[9999.0, -500.0])
    g1 = s1.sort_values("ts_event").reset_index(drop=True)
    g2 = s2.sort_values("ts_event").reset_index(drop=True)
    on1 = _overnight_features_one_session(g1)
    on2 = _overnight_features_one_session(g2)
    for k in ("overnight_return", "overnight_high", "overnight_low", "vwap_on"):
        assert on1[k] == pytest.approx(on2[k]) or (np.isnan(on1[k]) and np.isnan(on2[k]))


def test_preopen_window_uses_only_bars_before_0930():
    df = full_session("2021-06-01", n_overnight=5)  # small overnight, no preopen bars present
    bars = _dense_preopen_bars(df)
    arrs = bars.get(pd.Timestamp("2021-06-01"))
    assert arrs is None or np.all(np.isnan(arrs["close"]))  # no bars in [450,569) were provided


def test_exact_preopen_window_endpoint():
    n = 120
    closes = [100.0 + i * 0.1 for i in range(n)]
    em = list(range(PREOPEN_START, RTH_OPEN_MIN))
    df = make_bars("2021-06-01", em, closes)
    bars = _dense_preopen_bars(df)
    arrs = bars[pd.Timestamp("2021-06-01")]
    assert arrs["close"][119] == pytest.approx(closes[-1])  # tau3=119 == et_minute 569
    for W in WINDOWS:
        f = _window_feature(arrs, 120 - W, 120)
        expected_ret = arrs["close"][119] - arrs["open"][120 - W]
        assert f["ret"] == pytest.approx(expected_ret)


def test_dst_and_session_mapping_real_data():
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    path = os.path.join(repo, "data", "processed", "es_front_1m.parquet")
    if not os.path.exists(path):
        pytest.skip("base parquet not present in this environment")
    df = pd.read_parquet(path)
    df = df[df["session_date"] <= "2022-12-31"]
    led = build_overnight_ledger(df, "ES")
    # weekend mapping: Monday's overnight return must be defined and not
    # depend on a nonexistent Sunday RTH session
    mondays = led[pd.to_datetime(led["session_date"]).dt.dayofweek == 0]
    assert mondays["overnight_return"].notna().mean() > 0.9
    # DST transition dates (2021) must have valid rows
    for d in ("2021-03-15", "2021-11-08"):
        assert (led["session_date"] == pd.Timestamp(d)).any()


def test_one_row_per_instrument_session():
    df = pd.concat([full_session(f"2021-06-{d:02d}") for d in range(1, 6)], ignore_index=True)
    led = build_overnight_ledger(df, "ES")
    assert led["session_date"].is_unique


def test_zero_range_and_zero_path_undefined():
    flat = [100.0] * 40
    df = make_bars("2021-06-01", list(range(1080, 1120)) + [570, 571],
                   flat + [100.0, 100.0], opens=[100.0] * 42, highs=[100.0] * 42, lows=[100.0] * 42)
    g = df.sort_values("ts_event").reset_index(drop=True)
    on = _overnight_features_one_session(g)
    assert on["overnight_range"] == 0
    assert np.isnan(on["range_position_0929"])
    assert np.isnan(on["signed_path_efficiency_on"])


def test_vwap_causal_min_bars_and_no_lookahead():
    # 20 overnight bars (< VWAP_MIN_BARS=30) -> VWAP undefined
    df_small = full_session("2021-06-01", n_overnight=20)
    g = df_small.sort_values("ts_event").reset_index(drop=True)
    on_small = _overnight_features_one_session(g)
    assert np.isnan(on_small["vwap_on"])
    # 35 overnight bars -> VWAP defined, and unaffected by post-09:30 data
    df1 = full_session("2021-06-01", n_overnight=35, target_closes=[500.0, 501.0])
    df2 = full_session("2021-06-01", n_overnight=35, target_closes=[-999.0, 3.0])
    g1 = df1.sort_values("ts_event").reset_index(drop=True)
    g2 = df2.sort_values("ts_event").reset_index(drop=True)
    on1 = _overnight_features_one_session(g1)
    on2 = _overnight_features_one_session(g2)
    assert np.isfinite(on1["vwap_on"])
    assert on1["vwap_on"] == pytest.approx(on2["vwap_on"])


def test_target_matches_atlas_and_es_nq_separate(tmp_path, monkeypatch):
    df = pd.concat([full_session(f"2021-06-{d:02d}", full_primary_window=True) for d in range(1, 8)], ignore_index=True)
    import src.build_ledger as bl
    proc = tmp_path / "processed"
    proc.mkdir()
    for inst in ("es", "nq"):
        df.to_parquet(proc / f"{inst}_front_1m.parquet", index=False)
    monkeypatch.setattr(bl, "PROC", str(proc))
    monkeypatch.setattr(bl, "DEV_END", pd.Timestamp("2099-01-01"))
    led_es, _, _ = bl.build_full_ledger("ES")
    led_nq, _, _ = bl.build_full_ledger("NQ")
    assert (led_es["instrument"] == "ES").all()
    assert (led_nq["instrument"] == "NQ").all()
    assert "R_5" in led_es.columns and "Q_5" in led_es.columns


def test_trailing_normalization_causal_only():
    sessions = []
    for i in range(25):
        sd = f"2021-01-{i+1:02d}" if i < 20 else f"2021-02-{i-19:02d}"
        vol_mult = 1.0 + i * 0.1
        s = full_session(sd, n_overnight=35)
        s["volume"] = s["volume"] * (vol_mult if s["et_minute"].iloc[0] >= 1080 else 1.0)
        sessions.append(s)
    df = pd.concat(sessions, ignore_index=True)
    feat = build_overnight_ledger(df, "ES")
    assert feat["normalized_overnight_volume"].iloc[:20].isna().all()
    assert np.isfinite(feat["normalized_overnight_volume"].iloc[24])
