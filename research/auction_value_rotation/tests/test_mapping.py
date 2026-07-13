import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from research.auction_value_rotation.src import data as dat
from research.auction_value_rotation.src import mapping as mp
from research.auction_value_rotation.src import profiles as prof


def make_leg_df(session_dates):
    """Builds a minimal synthetic leg_df spanning ASIA/LONDON/NEW_YORK_RTH
    for each session_date, with complete leg bar counts and simple prices."""
    rows = []
    specs = [("ASIA", dat.LEG_EXPECTED_BARS["ASIA"], 18 * 60), ("LONDON", dat.LEG_EXPECTED_BARS["LONDON"], 3 * 60),
             ("NEW_YORK_RTH", dat.LEG_EXPECTED_BARS["NEW_YORK_RTH"], 9 * 60 + 30)]
    for d in session_dates:
        base_ts = pd.Timestamp(d) - pd.Timedelta(hours=6)  # session_date = date(ET+6h) convention (approx for synth)
        for leg_name, n, start_min in specs:
            for i in range(n):
                rows.append({
                    "session_date": pd.Timestamp(d), "leg": leg_name,
                    "session_leg_id": f"{d}|{leg_name}", "local_rank": i + 1,
                    "leg_bar_count": n, "leg_complete": True,
                    "ts_event": base_ts + pd.Timedelta(minutes=i),
                    "et_minute": start_min + i,
                    "low": 100.0, "high": 100.5, "close": 100.25, "volume": 10.0,
                    "atr20_event": 1.0,
                })
    df = pd.DataFrame(rows)
    return df.sort_values("ts_event").reset_index(drop=True)


def test_mapping_1_asia_to_london_same_session_date():
    leg_df = make_leg_df(["2024-01-02", "2024-01-03"])
    profiles = mp.build_all_profiles(leg_df, prof.PRIMARY)
    mappings = mp.build_mappings(leg_df, profiles)
    m1 = mappings["M1_ASIA_TO_LONDON"]
    assert len(m1) == 2
    for _, row in m1.iterrows():
        asia_id = f"{row['target_session_date'].date()}|ASIA"
        assert row["source_session_leg_id"] == asia_id


def test_mapping_3_rth_to_overnight_uses_prior_rth():
    leg_df = make_leg_df(["2024-01-02", "2024-01-03", "2024-01-04"])
    profiles = mp.build_all_profiles(leg_df, prof.PRIMARY)
    mappings = mp.build_mappings(leg_df, profiles)
    m3 = mappings["M3_RTH_TO_OVERNIGHT"]
    # Asia leg of 2024-01-03 should map to NY RTH profile of the nearest PRIOR ny date, i.e. 2024-01-02
    row = m3.loc[m3["target_session_date"] == pd.Timestamp("2024-01-03")].iloc[0]
    assert row["source_session_leg_id"] == "2024-01-02|NEW_YORK_RTH"
    # first date has no prior RTH -> excluded
    assert (m3["target_session_date"] == pd.Timestamp("2024-01-02")).sum() == 0


def test_mapping_4_rth_to_next_rth_uses_prior_rth():
    leg_df = make_leg_df(["2024-01-02", "2024-01-03", "2024-01-04"])
    profiles = mp.build_all_profiles(leg_df, prof.PRIMARY)
    mappings = mp.build_mappings(leg_df, profiles)
    m4 = mappings["M4_RTH_TO_NEXT_RTH"]
    row = m4.loc[m4["target_session_date"] == pd.Timestamp("2024-01-04")].iloc[0]
    assert row["source_session_leg_id"] == "2024-01-03|NEW_YORK_RTH"


def test_mapping_expiry_ts_is_targets_own_completion():
    leg_df = make_leg_df(["2024-01-02", "2024-01-03"])
    profiles = mp.build_all_profiles(leg_df, prof.PRIMARY)
    mappings = mp.build_mappings(leg_df, profiles)
    m2 = mappings["M2_LONDON_TO_NY"]
    row = m2.iloc[0]
    ny_bars = leg_df.loc[leg_df["session_leg_id"] == row["target_session_leg_id"]]
    assert row["expiry_ts"] == ny_bars["ts_event"].max() + pd.Timedelta(minutes=1)


def test_incomplete_leg_excluded_from_profiles():
    leg_df = make_leg_df(["2024-01-02"])
    leg_df.loc[leg_df["leg"] == "ASIA", "leg_complete"] = False
    profiles = mp.build_all_profiles(leg_df, prof.PRIMARY)
    assert "2024-01-02|ASIA" not in profiles
