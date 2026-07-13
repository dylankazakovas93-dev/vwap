from pathlib import Path
import argparse, hashlib, sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.engine import load_archives, build_candidates, causal_normalize, classify, bands, deduplicate, outcomes, primary

ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/"research/impact_decay_reversal/outputs"

def main(data_root):
    OUT.mkdir(parents=True,exist_ok=True)
    files={"ES":[data_root/"ES/es2018.zip",data_root/"ES/es2023.zip"],"NQ":[data_root/"NQ/nq2018.zip",data_root/"NQ/nq2020.zip",data_root/"NQ/nq2021.zip"]}
    all_events={}; all_bars={}
    for inst,paths in files.items():
        bars=load_archives(inst,[str(x) for x in paths]); all_bars[inst]=bars
        c=causal_normalize(build_candidates(bars)); c["state"]=c.apply(classify,axis=1); c=bands(c); c["event_id"]=[f"{inst}_{i:08d}" for i in range(len(c))]
        c=deduplicate(c); ev=outcomes(c,bars); all_events[inst]=ev
        ev.to_csv(OUT/f"{inst.lower()}_event_ledger.csv",index=False)
        ev[["event_id","instrument","session_date","session","clock_slot","diag_clock_slot","impulse_prior_n","volume_prior_n","I","impulse_percentile","diagnostic_volume","diagnostic_volume_percentile","state"]].to_csv(OUT/f"{inst.lower()}_normalization_ledger.csv",index=False)
    events=pd.concat(all_events.values(),ignore_index=True)
    prim,x=primary(events); prim.to_csv(OUT/"primary_matched_comparison.csv",index=False)
    # Adjacent horizons use the same complete-event and barrier logic.
    adj=[]
    for h in [5,10,30]:
        for key,g in x.groupby(["instrument","session","direction"],sort=True):
            e=g[g.state=="HIGH_VOLUME_DECAY"]; q=g[g.state=="LOW_VOLUME_DECAY_CONTROL"]; er=e[e[f"outcome_{h}"].isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])]; qr=q[q[f"outcome_{h}"].isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])]
            a=(er[f"outcome_{h}"]=="REVERSAL_FIRST").mean() if len(er) else np.nan; b=(qr[f"outcome_{h}"]=="REVERSAL_FIRST").mean() if len(qr) else np.nan
            adj.append({"instrument":key[0],"session":key[1],"direction":key[2],"horizon":h,"resolved_high":len(er),"resolved_low":len(qr),"high_reversal_rate":a,"low_reversal_rate":b,"difference":a-b})
    pd.DataFrame(adj).to_csv(OUT/"adjacent_horizon_table.csv",index=False)
    # Supporting high-volume progress control.
    sup=[]
    for key,g in x.groupby(["instrument","session","direction"],sort=True):
        for state in ["HIGH_VOLUME_DECAY","HIGH_VOLUME_PROGRESS_CONTROL"]:
            z=g[g.state==state]; r=z[z.outcome_15.isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])]
            sup.append({"instrument":key[0],"session":key[1],"direction":key[2],"state":state,"n":len(z),"resolved":len(r),"reversal_rate":(r.outcome_15=="REVERSAL_FIRST").mean() if len(r) else np.nan})
    pd.DataFrame(sup).to_csv(OUT/"high_volume_progress_control.csv",index=False)
    # Year stability for primary states.
    y=x[x.state.isin(["HIGH_VOLUME_DECAY","LOW_VOLUME_DECAY_CONTROL"])].copy(); y["year"]=pd.to_datetime(y.session_date).dt.year; rows=[]
    for key,g in y.groupby(["instrument","session","direction","year","state"],sort=True):
        r=g[g.outcome_15.isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])]
        rows.append({"instrument":key[0],"session":key[1],"direction":key[2],"year":key[3],"state":key[4],"n":len(g),"resolved":len(r),"reversal_rate":(r.outcome_15=="REVERSAL_FIRST").mean() if len(r) else np.nan,"median_progress_ratio":g.progress_ratio.median()})
    pd.DataFrame(rows).to_csv(OUT/"year_stability_table.csv",index=False)
    # Exact diagnostic-time ES/NQ confirmation, descriptive only.
    es=all_events["ES"].set_index("diag_end_ts"); nq=all_events["NQ"].set_index("diag_end_ts"); rows=[]
    for inst,ev in all_events.items():
        pair=nq if inst=="ES" else es
        for r in ev.itertuples(index=False):
            p=pair.loc[r.diag_end_ts] if r.diag_end_ts in pair.index else None
            if p is None: state="NO_MATCH"
            elif p.direction==r.direction and p.impulse_percentile>=.70: state="CONFIRMED"
            elif p.direction!=r.direction or (np.isfinite(p.impulse_percentile) and p.impulse_percentile<.50): state="UNCONFIRMED"
            else: state="PARTIAL_CONFIRMATION"
            rows.append({"event_id":r.event_id,"instrument":inst,"state":r.state,"confirmation":state,"outcome_15":r.outcome_15})
    conf=pd.DataFrame(rows); conf.groupby(["instrument","confirmation","state","outcome_15"],dropna=False).size().reset_index(name="n").to_csv(OUT/"cross_market_confirmation_table.csv",index=False)
    counts=events.groupby(["instrument","session","direction","state"],dropna=False).size().reset_index(name="n"); counts.to_csv(OUT/"sample_accounting.csv",index=False)
    lines=["# Impact-decay reversal — frozen 2018–2022 development study","","## Verdict","", "The primary classification is determined by the matched high-volume-decay minus low-volume-decay reversal-rate difference, with 10,000 within-stratum permutations and BH correction. No profitability or validation analysis was performed.","","## Sample accounting","",counts.to_string(index=False),"","## Primary comparison","",prim.to_string(index=False),"","Adjacent horizons: `adjacent_horizon_table.csv`. Supporting control: `high_volume_progress_control.csv`. Year stability: `year_stability_table.csv`. Cross-market diagnostics: `cross_market_confirmation_table.csv`."]
    (OUT/"IMPACT_DECAY_REVERSAL_REPORT.md").write_text("\n".join(lines)); print(prim.to_string(index=False))

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--data-root",type=Path,required=True); main(ap.parse_args().data_root)
