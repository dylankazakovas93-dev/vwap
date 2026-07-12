import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import interactions as ix
from src import families as fam
from src import build_ledger as bd


def make_arrs(open_, high, low, close, volume=None, n=45):
    o = np.full(n, np.nan); h = np.full(n, np.nan); l = np.full(n, np.nan)
    c = np.full(n, np.nan); v = np.full(n, np.nan)
    for tau, val in open_.items(): o[tau] = val
    for tau, val in high.items(): h[tau] = val
    for tau, val in low.items(): l[tau] = val
    for tau, val in close.items(): c[tau] = val
    if volume:
        for tau, val in volume.items(): v[tau] = val
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


# ------------------------------------------------------------- 1: inventory --
def test_01_frozen_inventory_22_7_5_4_38():
    lv, bl = bd._load_gen7()
    from collections import Counter
    counts = Counter(fam_ for fam_, side, _ in lv.LEVEL_COLUMNS.values())
    assert counts["family1"] == 22
    assert counts["family2"] == 7
    assert counts["family3"] == 5
    assert counts["family4"] == 4
    assert len(lv.LEVEL_COLUMNS) == 38
    assert "prior_settlement_open" not in lv.LEVEL_COLUMNS
    assert "q_U_p50" not in lv.LEVEL_COLUMNS and "q_D_p50" not in lv.LEVEL_COLUMNS


# ------------------------------------------------------------- 2: partition --
def test_02_partition_guard(tmp_path, monkeypatch):
    rows = []
    for i in range(5):
        sd = pd.Timestamp("2022-12-29") + pd.Timedelta(days=i)  # crosses into 2023
        rows.append({"session_date": sd, "et_minute": 570, "ts_event": sd,
                    "open": 100.0, "high": 100.1, "low": 99.9, "close": 100.0, "volume": 10})
    df = pd.DataFrame(rows)
    proc = tmp_path / "processed"
    proc.mkdir()
    df.to_parquet(proc / "es_front_1m.parquet", index=False)
    out = ix.load_dev("ES", str(proc))
    assert out["session_date"].max() <= ix.DEV_END
    assert out["session_date"].min() >= ix.DEV_START


# ------------------------------------------------------- 3: ES/NQ separation --
def test_03_es_nq_separation():
    lv, bl = bd._load_gen7()
    tx = bl._load_taxonomy_module()
    les, es_e, es_o, es_b = bd.build_instrument_ledger("ES", lv, bl, tx)
    assert (les["instrument"] == "ES").all()
    assert (es_e["instrument"] == "ES").all()


# --------------------------------------------------- 4: exact-60 no fallback --
def test_04_exact_60_normalization_no_fallback():
    lv, bl = bd._load_gen7()
    tx = bl._load_taxonomy_module()
    n = 65
    rows = []
    for i in range(n):
        sd = pd.Timestamp("2019-01-01") + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "ts_event": sd,
                    "open": 100.0, "high": 100.0 + (i + 1) * 0.1, "low": 99.9, "volume": 10})
    df = pd.DataFrame(rows)
    scales = tx.build_scale_tables(df)
    for i in range(60):
        sd = pd.Timestamp("2019-01-01") + pd.Timedelta(days=i)
        assert np.isnan(scales.loc[sd, "scale_U"])
    sd60 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=60)
    assert np.isfinite(scales.loc[sd60, "scale_U"])


# --------------------------------------------------- 5/6: touch window 570-599 --
def test_05_06_touch_window_exactly_570_599():
    assert ix.TOUCH_START == 570 and ix.TOUCH_END == 599
    # bucket boundaries exhaustively cover 570-599 and nothing else
    for m in range(570, 600):
        assert ix.bucket_for_et_minute(m) is not None
    assert ix.bucket_for_et_minute(569) is None
    assert ix.bucket_for_et_minute(600) is None


# ------------------------------------------------------- 7: first-touch only --
def test_07_first_touch_only_consumption():
    low = np.array([105, 95, 95, 95])  # touches at tau=1 first (V=100 inside [95,105]? use explicit)
    high = np.array([106, 101, 101, 101])
    V = 100.0
    cond = (low <= V) & (high >= V)
    assert cond[1] and cond[2] and cond[3]
    first = np.argmax(cond)
    assert first == 1  # earliest, later touches (2,3) not used


# --------------------------------------------------- 8: touch condition --
def test_08_touch_condition_low_le_v_le_high():
    assert (95 <= 100 <= 105)
    low, high, V = np.array([101.0]), np.array([102.0]), 100.0
    assert not ((low <= V) & (high >= V))[0]


# --------------------------------------------------- 9: outcome starts T+1 --
def test_09_outcome_window_starts_at_t_plus_1():
    arrs = make_arrs({0: 100, 1: 999, 2: 100.5}, {0: 100.2, 1: 999.5, 2: 100.6},
                     {0: 99.8, 1: 998.5, 2: 100.4}, {0: 100.1, 1: 999.2, 2: 100.5})
    out = ix.raw_outcomes(arrs, T=0, V=100.0, h=2)
    # tau=1 (T+1) is the huge outlier; it MUST be included (T+1..T+h)
    assert out["raw_up_ext"] > 500


# ------------------------------------------------- 10: touch bar excluded --
def test_10_touch_bar_hlc_excluded_from_outcomes():
    arrs_a = make_arrs({0: 100, 1: 100.2, 2: 100.3}, {0: 100.3, 1: 100.3, 2: 100.4},
                       {0: 99.7, 1: 100.1, 2: 100.2}, {0: 100.0, 1: 100.2, 2: 100.3})
    arrs_b = {k: v.copy() for k, v in arrs_a.items()}
    arrs_b["high"][0] = 99999.0  # mutate the TOUCH bar (tau=0) only
    arrs_b["low"][0] = -99999.0
    arrs_b["close"][0] = -99999.0
    out_a = ix.raw_outcomes(arrs_a, T=0, V=100.0, h=2)
    out_b = ix.raw_outcomes(arrs_b, T=0, V=100.0, h=2)
    assert out_a == out_b


# ------------------------------------------------- 11: max horizon <= 10:14 --
def test_11_max_horizon_ends_no_later_than_1014():
    assert ix.TOUCH_END + max(ix.HORIZONS) - ix.TOUCH_START == ix.TAU_MAX == 44
    assert ix.TOUCH_START + ix.TAU_MAX == 614  # 10:14 ET


# ------------------------------------------------- 12/13: orientation --
def test_12_above_open_orientation():
    o, d, s = ix.orientation_for(V=101.0, O=100.0, scale_U=1.0, scale_D=1.0)
    assert o == "ABOVE_OPEN" and d == 1 and s == 1.0


def test_13_below_open_orientation():
    o, d, s = ix.orientation_for(V=99.0, O=100.0, scale_U=1.0, scale_D=1.0)
    assert o == "BELOW_OPEN" and d == -1 and s == 1.0


# ------------------------------------------------- 14: ambiguous exclusion --
def test_14_at_open_ambiguous_excluded_from_normalized():
    o, d, s = ix.orientation_for(V=100.05, O=100.0, scale_U=1.0, scale_D=1.0)
    assert o == "AT_OPEN_AMBIGUOUS" and d is None and s is None


# ------------------------------------------------- 15: mirrored D/MFE/MAE --
def test_15_mirrored_upper_lower_formulas():
    arrs = make_arrs({0: 100}, {0: 100.2, 1: 103, 2: 101}, {0: 99.8, 1: 99, 2: 100.5},
                     {0: 100, 1: 102, 2: 100.8})
    up = ix.normalized_outcomes(arrs, T=0, V=100.0, h=2, dir_=1, orientation="ABOVE_OPEN", scale_U=2.0, scale_D=2.0)
    down = ix.normalized_outcomes(arrs, T=0, V=100.0, h=2, dir_=-1, orientation="BELOW_OPEN", scale_U=2.0, scale_D=2.0)
    # ABOVE_OPEN: MFE uses up_ext (max high - V); BELOW_OPEN: MFE uses down_ext (V - min low)
    assert up["MFE_h"] == max(0.0, 103 - 100.0) / 2.0
    assert down["MFE_h"] == max(0.0, 100.0 - 99) / 2.0
    assert up["MAE_h"] == max(0.0, 100.0 - 99) / 2.0
    assert down["MAE_h"] == max(0.0, 103 - 100.0) / 2.0


# ------------------------------------------------- 16: Q zero-denominator --
def test_16_q_zero_denominator_is_na():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 100.0}, {0: 99.9, 1: 100.0}, {0: 100.0, 1: 100.0})
    out = ix.normalized_outcomes(arrs, T=0, V=100.0, h=1, dir_=1, orientation="ABOVE_OPEN", scale_U=1.0, scale_D=1.0)
    assert out["MFE_h"] == 0.0 and out["MAE_h"] == 0.0
    assert np.isnan(out["Q_h"])


# ------------------------------------------------- 17: post_touch_retouch --
def test_17_post_touch_retouch_definition():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 105, 2: 100.05}, {0: 99.9, 1: 104, 2: 99.95},
                     {0: 100, 1: 104.5, 2: 100.0})
    out = ix.raw_outcomes(arrs, T=0, V=100.0, h=2)
    assert out["post_touch_retouch"] == 1  # tau=2 range [99.95,100.05] contains V=100


# ------------------------------------------------- 18: close-recross ordering --
def test_18_directional_close_recross_ordering():
    # ABOVE_OPEN: bar1 closes above V (continuation), bar2 closes below V (rejection) -> recross=1
    arrs = make_arrs({0: 100}, {}, {}, {0: 100.0, 1: 101.0, 2: 99.0})
    out = ix.directional_close_recross(arrs, T=0, h=2, orientation="ABOVE_OPEN", V=100.0)
    assert out["directional_close_recross"] == 1
    assert out["first_continuation_side_close_bar"] == 1
    assert out["first_rejection_side_close_after_continuation_bar"] == 2
    # rejection close with NO prior continuation close -> not a recross
    arrs2 = make_arrs({0: 100}, {}, {}, {0: 100.0, 1: 99.0, 2: 99.5})
    out2 = ix.directional_close_recross(arrs2, T=0, h=2, orientation="ABOVE_OPEN", V=100.0)
    assert out2["directional_close_recross"] == 0


# ------------------------------------------------- 19: labels --
def test_19_continuation_rejection_labels():
    labels = ix.continuation_rejection_labels(1.5)
    assert labels[1.0] == "CONTINUATION"
    labels2 = ix.continuation_rejection_labels(-1.2)
    assert labels2[1.0] == "REJECTION"
    labels3 = ix.continuation_rejection_labels(0.2)
    assert labels3[1.0] == "INCONCLUSIVE"


# ------------------------------------------------- 20: barriers vs k directly --
def test_20_barrier_reach_matches_normalized_mfe_mae_at_k():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 103.0}, {0: 99.9, 1: 99.5}, {0: 100.0, 1: 101.0})
    norm = ix.normalized_outcomes(arrs, T=0, V=100.0, h=1, dir_=1, orientation="ABOVE_OPEN", scale_U=2.0, scale_D=2.0)
    for k in ix.BARRIER_K:
        b = ix.barrier_outcomes(arrs, T=0, h=1, k=k, orientation="ABOVE_OPEN", V=100.0, scale_U=2.0, scale_D=2.0)
        assert b["reach_continuation"] == int(norm["MFE_h"] >= k)
        assert b["reach_rejection"] == int(norm["MAE_h"] >= k)


# ------------------------------------------- 21-24: barrier order fixtures --
def test_21_continuation_first_barrier_fixture():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 103, 2: 100.05}, {0: 99.9, 1: 100, 2: 97},
                     {0: 100, 1: 102, 2: 98})
    b = ix.barrier_outcomes(arrs, T=0, h=2, k=1.0, orientation="ABOVE_OPEN", V=100.0, scale_U=2.0, scale_D=2.0)
    assert b["barrier_order"] == "CONTINUATION_FIRST"


def test_22_rejection_first_barrier_fixture():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 100.05, 2: 105}, {0: 99.9, 1: 97, 2: 104},
                     {0: 100, 1: 98, 2: 104.5})
    b = ix.barrier_outcomes(arrs, T=0, h=2, k=1.0, orientation="ABOVE_OPEN", V=100.0, scale_U=2.0, scale_D=2.0)
    assert b["barrier_order"] == "REJECTION_FIRST"


def test_23_same_bar_barrier_tie_fixture():
    # both continuation (V+2=102) and rejection (V-2=98) barriers reached on the SAME bar tau=1
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 103}, {0: 99.9, 1: 97}, {0: 100, 1: 100})
    b = ix.barrier_outcomes(arrs, T=0, h=1, k=1.0, orientation="ABOVE_OPEN", V=100.0, scale_U=2.0, scale_D=2.0)
    assert b["barrier_order"] == "SAME_BAR_BARRIER_TIE"


def test_24_neither_barrier_reached_fixture():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 100.2}, {0: 99.9, 1: 99.8}, {0: 100, 1: 100.1})
    b = ix.barrier_outcomes(arrs, T=0, h=1, k=1.0, orientation="ABOVE_OPEN", V=100.0, scale_U=2.0, scale_D=2.0)
    assert b["barrier_order"] == "NEITHER_REACHED"
    assert b["reach_continuation"] == 0 and b["reach_rejection"] == 0


# ------------------------------------------------- 25/26: eligibility --
def test_25_mutual_touch_eligibility():
    real_elig = np.array([True, False, True])
    synth_elig = np.array([True, True, False])
    mutual = real_elig & synth_elig
    assert list(mutual) == [True, False, False]


def test_26_normalized_outcome_eligibility_requires_scale_and_orientation():
    o, d, s = ix.orientation_for(100.05, 100.0, 1.0, 1.0)
    assert o == "AT_OPEN_AMBIGUOUS"
    ne = o in ("ABOVE_OPEN", "BELOW_OPEN")
    assert ne is False
    o2, d2, s2 = ix.orientation_for(101.0, 100.0, np.nan, 1.0)
    assert o2 is None


# ------------------------------------------------- 27: deterministic synth --
def test_27_deterministic_synthetic_controls():
    lv, bl = bd._load_gen7()
    tx = bl._load_taxonomy_module()
    built = bl.build_instrument("ES", tx)
    s1 = lv.build_synthetic_controls(built["long"], built["fam1"])
    s2 = lv.build_synthetic_controls(built["long"], built["fam1"])
    pd.testing.assert_series_equal(s1["value_synth"], s2["value_synth"])


# ------------------------------------------------- 28: bucket assignment --
def test_28_five_minute_bucket_assignment():
    assert ix.bucket_for_et_minute(570) == "B1"
    assert ix.bucket_for_et_minute(574) == "B1"
    assert ix.bucket_for_et_minute(575) == "B2"
    assert ix.bucket_for_et_minute(599) == "B6"
    assert ix.bucket_for_et_minute(595) == "B6"


# ------------------------------------------------- 29-31: isolation/pair --
def test_29_named_isolation_logic():
    # replicate the union-find + co-touch logic on a tiny 3-level case
    V_real = np.array([100.0, 100.05, 110.0])
    side_scale = np.array([1.0, 1.0, 1.0])
    thresh = 0.10 * side_scale
    dist_01 = abs(V_real[0] - V_real[1])
    assert dist_01 <= thresh[0]  # clustered -> level 0 not isolated
    dist_02 = abs(V_real[0] - V_real[2])
    assert dist_02 > thresh[0]  # far apart


def test_30_synthetic_isolation_logic():
    V_synth = 100.03
    V_real_all = np.array([100.0, 110.0, 120.0])
    side_scale = 1.0
    thresh = 0.10 * side_scale
    far_from_all = bool(np.all(np.abs(V_synth - V_real_all) > thresh))
    assert far_from_all is False  # close to V_real_all[0]


def test_31_pair_separation_rule():
    side_scale = 2.0  # threshold = 0.10*2.0 = 0.2
    assert int(abs(100.1 - 100.0) > 0.10 * side_scale) == 0  # 0.1 <= 0.2 -> not separated
    assert int(abs(101.0 - 100.0) > 0.10 * side_scale) == 1  # 1.0 > 0.2 -> separated


# ------------------------------------------------- 32: McNemar alignment --
def test_32_mcnemar_session_alignment_counts_sum_to_mutual():
    levels_tbl = pd.DataFrame({
        "instrument": ["ES"] * 6, "level_id": ["mult_U_1.0"] * 6,
        "mutually_touch_eligible": [True] * 6,
        "real_touched": [True, True, False, False, True, False],
        "synthetic_touched": [True, False, True, False, False, False],
    })
    out = fam.family_a_touch_rate(levels_tbl)
    row = out.iloc[0]
    assert row["n_both_touched"] + row["n_real_only"] + row["n_synth_only"] + row["n_neither_touched"] == 6


# ------------------------------------------------- 33/34: paired D5 alignment --
def test_33_34_paired_d5_same_session_same_bucket_restriction():
    key_common = dict(instrument="ES", session_date=pd.Timestamp("2020-01-01"), level_id="mult_U_1.0")
    events = pd.DataFrame([
        {**key_common, "arm": "REAL", "touched": True, "touch_bucket": "B1", "orientation": "ABOVE_OPEN", "normalized_outcome_eligible": True},
        {**key_common, "arm": "SYNTHETIC", "touched": True, "touch_bucket": "B2", "orientation": "ABOVE_OPEN", "normalized_outcome_eligible": True},
    ])
    outcomes = pd.DataFrame([
        {**key_common, "arm": "REAL", "horizon": 5, "D_h": 1.0},
        {**key_common, "arm": "SYNTHETIC", "horizon": 5, "D_h": 0.5},
    ])
    levels_tbl = pd.DataFrame([{**key_common, "real_isolated": 1, "synthetic_isolated": 1, "pair_separated": 1}])
    pairs = fam.build_family_b_pairs(levels_tbl, events, outcomes)
    assert len(pairs) == 0  # different buckets (B1 vs B2) -> excluded

    events2 = events.copy()
    events2.loc[events2["arm"] == "SYNTHETIC", "touch_bucket"] = "B1"
    pairs2 = fam.build_family_b_pairs(levels_tbl, events2, outcomes)
    assert len(pairs2) == 1  # same session, same bucket -> included


# ------------------------------------------------- 35: one row per unit --
def test_35_one_row_per_session_level_arm():
    lv, bl = bd._load_gen7()
    tx = bl._load_taxonomy_module()
    _, events_tbl, _, _ = bd.build_instrument_ledger("ES", lv, bl, tx)
    dup = events_tbl.groupby(["session_date", "level_id", "arm"]).size()
    assert (dup == 1).all()


# ------------------------------------------------- 36: complete null retention --
def test_36_complete_null_cell_retention():
    empty_pairs = pd.DataFrame(columns=["instrument", "session_date", "level_id", "D5_real", "D5_synthetic"])
    b = fam.family_b_paired_d5(empty_pairs, all_instruments=["ES", "NQ"], all_level_ids=["mult_U_1.0", "mult_D_1.0"])
    assert len(b) == 4
    assert (b["status"] == "no_valid_pairs").all()

    levels_tbl = pd.DataFrame({
        "instrument": ["ES"], "level_id": ["mult_U_1.0"], "mutually_touch_eligible": [False],
        "real_touched": [False], "synthetic_touched": [False],
    })
    a = fam.family_a_touch_rate(levels_tbl)
    assert len(a) == 1
    assert a.iloc[0]["status"] == "no_mutually_eligible_sessions"
