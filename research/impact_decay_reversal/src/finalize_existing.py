from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.engine import primary
ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/"research/impact_decay_reversal/outputs"

def main():
    events={i:pd.read_csv(OUT/f"{i.lower()}_event_ledger.csv",parse_dates=["impulse_start_ts","impulse_end_ts","diag_end_ts"]) for i in ["ES","NQ"]}
    all_events=pd.concat(events.values(),ignore_index=True); prim,x=primary(all_events); prim.to_csv(OUT/"primary_matched_comparison.csv",index=False)
    adj=[]
    for h in [5,10,30]:
        for key,g in x.groupby(["instrument","session","direction"],sort=True):
            e=g[g.state=="HIGH_VOLUME_DECAY"]; q=g[g.state=="LOW_VOLUME_DECAY_CONTROL"]; er=e[e[f"outcome_{h}"].isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])]; qr=q[q[f"outcome_{h}"].isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])]
            a=(er[f"outcome_{h}"]=="REVERSAL_FIRST").mean() if len(er) else np.nan; b=(qr[f"outcome_{h}"]=="REVERSAL_FIRST").mean() if len(qr) else np.nan; adj.append({"instrument":key[0],"session":key[1],"direction":key[2],"horizon":h,"resolved_high":len(er),"resolved_low":len(qr),"high_reversal_rate":a,"low_reversal_rate":b,"difference":a-b})
    pd.DataFrame(adj).to_csv(OUT/"adjacent_horizon_table.csv",index=False)
    sup=[]
    for key,g in x.groupby(["instrument","session","direction"],sort=True):
        for state in ["HIGH_VOLUME_DECAY","HIGH_VOLUME_PROGRESS_CONTROL"]:
            z=g[g.state==state]; r=z[z.outcome_15.isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])]
            sup.append({"instrument":key[0],"session":key[1],"direction":key[2],"state":state,"n":len(z),"resolved":len(r),"reversal_rate":(r.outcome_15=="REVERSAL_FIRST").mean() if len(r) else np.nan})
    pd.DataFrame(sup).to_csv(OUT/"high_volume_progress_control.csv",index=False)
    y=x[x.state.isin(["HIGH_VOLUME_DECAY","LOW_VOLUME_DECAY_CONTROL"])].copy(); y["year"]=pd.to_datetime(y.session_date).dt.year; rows=[]
    for key,g in y.groupby(["instrument","session","direction","year","state"],sort=True):
        r=g[g.outcome_15.isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])]
        rows.append({"instrument":key[0],"session":key[1],"direction":key[2],"year":key[3],"state":key[4],"n":len(g),"resolved":len(r),"reversal_rate":(r.outcome_15=="REVERSAL_FIRST").mean() if len(r) else np.nan,"median_progress_ratio":g.progress_ratio.median()})
    pd.DataFrame(rows).to_csv(OUT/"year_stability_table.csv",index=False)
    es=events["ES"].set_index("diag_end_ts"); nq=events["NQ"].set_index("diag_end_ts"); rows=[]
    for inst,ev in events.items():
        pair=nq if inst=="ES" else es
        for r in ev.itertuples(index=False):
            p=pair.loc[r.diag_end_ts] if r.diag_end_ts in pair.index else None
            if p is None: conf="NO_MATCH"
            elif p.direction==r.direction and p.impulse_percentile>=.70: conf="CONFIRMED"
            elif p.direction!=r.direction or (np.isfinite(p.impulse_percentile) and p.impulse_percentile<.50): conf="UNCONFIRMED"
            else: conf="PARTIAL_CONFIRMATION"
            rows.append({"event_id":r.event_id,"instrument":inst,"state":r.state,"confirmation":conf,"outcome_15":r.outcome_15})
    conf=pd.DataFrame(rows)
    conf.groupby(["instrument","confirmation","state","outcome_15"],dropna=False).size().reset_index(name="n").to_csv(OUT/"cross_market_confirmation_table.csv",index=False)
    counts=all_events.groupby(["instrument","session","direction","state"],dropna=False).size().reset_index(name="n"); counts.to_csv(OUT/"sample_accounting.csv",index=False)
    (OUT/"IMPACT_DECAY_REVERSAL_REPORT.md").write_text("\n".join(["# Impact-decay reversal — frozen 2018–2022 development study","","No validation or trading simulation was run.","","## Sample accounting","",counts.to_string(index=False),"","## Primary comparison","",prim.to_string(index=False),"","Adjacent horizons: `adjacent_horizon_table.csv`. Supporting control: `high_volume_progress_control.csv`. Year stability: `year_stability_table.csv`. Cross-market diagnostics: `cross_market_confirmation_table.csv`. "]))
    print(prim.to_string(index=False))
if __name__=="__main__": main()
