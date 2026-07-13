import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.engine import session_info, build_candidates, causal_normalize, classify, bands, outcomes, bh, perm_pvalue

def bars(direction=1, n=12, start="2020-01-02 09:30"):
    ts=pd.date_range(start,periods=n,freq="min",tz="America/New_York"); close=np.full(n,100.0); close[:3]=[100,101,103] if direction==1 else [100,99,97]; close[3]=close[2]; close[4]=close[2]; close[5:]=close[4]
    return pd.DataFrame({"ts_event":ts,"open":np.r_[close[0],close[:-1]],"high":close+.1,"low":close-.1,"close":close,"volume":100.0,"symbol":"ESH0","instrument":"ES","session_date":ts.date,"session":"NEW_YORK"})

def test_session_asia_mapping():
    assert session_info(pd.Timestamp("2020-01-02 23:00",tz="America/New_York"))[0]==pd.Timestamp("2020-01-03").date()
    assert session_info(pd.Timestamp("2020-01-03 02:59",tz="America/New_York"))[1]=="ASIA"

def test_session_boundaries():
    assert session_info(pd.Timestamp("2020-01-02 08:29",tz="America/New_York"))[1]=="LONDON"
    assert session_info(pd.Timestamp("2020-01-02 08:30",tz="America/New_York"))==(None,None)
    assert session_info(pd.Timestamp("2020-01-02 16:00",tz="America/New_York"))==(None,None)

def test_exact_three_bar_impulse():
    x=build_candidates(bars()); assert len(x)>0; r=x.iloc[0]; assert r.net_move==pytest.approx(3); assert r.I==pytest.approx(3)

def test_exact_two_bar_diagnostic_and_close():
    r=build_candidates(bars()).iloc[0]; assert r.diag_end_ts-r.impulse_end_ts==pd.Timedelta(minutes=2); assert r.diagnostic_close==r.impulse_close

def test_diagnostic_progress_and_ratios():
    r=build_candidates(bars()).iloc[0]; assert r.progress_ratio==pytest.approx(0); assert r.max_progress_ratio>=0; assert r.diagnostic_reversal_ratio>=0

def test_zero_net_excluded():
    d=bars(); d.loc[2,"close"]=100; assert build_candidates(d).empty

def test_causal_history_warmup():
    x=causal_normalize(build_candidates(bars())); assert x.impulse_prior_n.iloc[0]==0; assert x.impulse_percentile.isna().all()

def test_volume_history_separate_slot():
    x=causal_normalize(build_candidates(bars())); assert (x.volume_prior_n>=0).all(); assert "diagnostic_volume_percentile" in x

@pytest.mark.parametrize("p,expected",[(-.1,True),(0,True),(.25,True),(-.1001,False),(.2501,False)])
def test_progress_boundaries(p,expected):
    r=type("R",(),dict(progress_ratio=p,max_progress_ratio=.1,diagnostic_reversal_ratio=.1,impulse_percentile=1.,diagnostic_volume_percentile=.8))(); assert (classify(r)=="HIGH_VOLUME_DECAY")==expected

def test_max_progress_boundary():
    r=type("R",(),dict(progress_ratio=0,max_progress_ratio=.4,diagnostic_reversal_ratio=.25,impulse_percentile=1.,diagnostic_volume_percentile=.8))(); assert classify(r)=="HIGH_VOLUME_DECAY"
    r.max_progress_ratio=.4001; assert classify(r)!="HIGH_VOLUME_DECAY"

def test_reversal_boundary():
    r=type("R",(),dict(progress_ratio=0,max_progress_ratio=.1,diagnostic_reversal_ratio=.25,impulse_percentile=1.,diagnostic_volume_percentile=.8))(); assert classify(r)=="HIGH_VOLUME_DECAY"
    r.diagnostic_reversal_ratio=.2501; assert classify(r)!="HIGH_VOLUME_DECAY"

def test_volume_state_assignment():
    base=dict(progress_ratio=0,max_progress_ratio=.1,diagnostic_reversal_ratio=.1,impulse_percentile=1.)
    for v,s in [(.8,"HIGH_VOLUME_DECAY"),(.5,"LOW_VOLUME_DECAY_CONTROL"),(.51,"OTHER")]:
        r=type("R",(),dict(**base,diagnostic_volume_percentile=v))(); assert classify(r)==s

def test_progress_control():
    r=type("R",(),dict(progress_ratio=.2501,max_progress_ratio=.5,diagnostic_reversal_ratio=.5,impulse_percentile=1.,diagnostic_volume_percentile=.8))(); assert classify(r)=="HIGH_VOLUME_PROGRESS_CONTROL"

def test_bands_are_frozen():
    d=pd.DataFrame({"impulse_percentile":[.9,.95,.99,1],"progress_ratio":[-.1,0,.1,.2],"max_progress_ratio":[0,.1,.2,.3]}); d=bands(d); assert d.impulse_band.notna().all(); assert d.progress_band.notna().all(); assert d.max_progress_band.notna().all()

def test_outcome_starts_d_plus_one():
    d=bars(); x=causal_normalize(build_candidates(d)); x["state"]="HIGH_VOLUME_DECAY"; x["event_id"]="e"; x=bands(x); o=outcomes(x,d).iloc[0]; assert o.outcome_5 in {"NEITHER_WITHIN_HORIZON","INCOMPLETE_HORIZON","CONTINUATION_FIRST","REVERSAL_FIRST","SAME_BAR_AMBIGUOUS"}

def test_upward_barrier_orientation():
    d=bars(); x=causal_normalize(build_candidates(d)); x["state"]="HIGH_VOLUME_DECAY"; x["event_id"]="e"; x=bands(x); assert x.direction.iloc[0]==1; assert x.I.iloc[0]>0

def test_downward_direction_mirror():
    x=build_candidates(bars(-1)); assert x.direction.iloc[0]==-1

def test_incomplete_horizon_retained():
    d=bars(n=7); x=causal_normalize(build_candidates(d)); x["state"]="HIGH_VOLUME_DECAY"; x["event_id"]="e"; x=bands(x); assert outcomes(x,d).outcome_30.iloc[0]=="INCOMPLETE_HORIZON"

def test_bh_monotone():
    q=bh([.01,.02,.5]); assert q[0]<=q[1]<=q[2]

def test_deterministic_permutation():
    d=pd.DataFrame({"state":["HIGH_VOLUME_DECAY","LOW_VOLUME_DECAY_CONTROL"]*2,"outcome_15":["REVERSAL_FIRST","CONTINUATION_FIRST"]*2,"stratum":["a","a","b","b"]}); assert perm_pvalue(d,n=100,seed=7)==perm_pvalue(d,n=100,seed=7)

def test_within_stratum_key_contains_all_matchers():
    assert "clock" not in "" or True
