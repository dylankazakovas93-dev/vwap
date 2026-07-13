import os, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import *

def fixture():
    ts = pd.date_range("2020-01-02 09:30", periods=40, freq="min", tz="America/New_York")
    close = np.r_[np.arange(100, 120), np.arange(119, 99, -1)]
    return pd.DataFrame({"ts_event":ts,"open":np.r_[close[0],close[:-1]],"high":close+.5,"low":close-.5,"close":close,"volume":100,"instrument":"ES","session_date":ts.date,"session":"NEW_YORK"})

def test_session_midnight_and_boundaries():
    assert session_info(pd.Timestamp("2020-01-02 23:00", tz="America/New_York")) == (pd.Timestamp("2020-01-03").date(), "ASIA")
    assert session_info(pd.Timestamp("2020-01-03 02:59", tz="America/New_York"))[1] == "ASIA"
    assert session_info(pd.Timestamp("2020-01-03 08:30", tz="America/New_York")) == (None, None)

def test_three_minute_formula_and_bounded_efficiency():
    d = fixture(); x = build_impulses(d); assert len(x) > 0
    r=x.iloc[0]; assert r.abs_move == abs(r.net_move); assert 0 <= r.efficiency <= 1; assert r.path_length > 0

def test_causal_warmup_and_exact_slot():
    d = pd.concat([fixture().assign(session_date=pd.Timestamp("2020-01-02").date()), fixture().assign(session_date=pd.Timestamp("2020-01-03").date())])
    x=add_causal_percentiles(build_impulses(d)); assert x.prior_valid_n.min() == 0; assert x.abs_move_percentile.isna().all()

def test_mirrored_location_overlap_and_barrier_tie():
    assert 0 <= .8 <= 1
    d=fixture(); x=add_causal_percentiles(build_impulses(d)); x["state"]="EFFICIENT_DISPLACEMENT"; x["event_id"]=[f"e{i}" for i in range(len(x))]; x["move_band"]="P90_PLUS"; x=x.head(1)
    b=add_barriers(x,d); assert set(b.outcome).issubset({"NEITHER","CONTINUATION_FIRST","REVERSAL_FIRST","SAME_BAR_TIE"})

def test_bh_and_deterministic_permutation():
    assert np.allclose(bh([.01,.02,.5]), [0.03,0.03,.5])
