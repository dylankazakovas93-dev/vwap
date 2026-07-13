from __future__ import annotations
import csv, io, re, zipfile
from collections import defaultdict
import numpy as np
import pandas as pd
import zstandard as zstd

ET = "America/New_York"
START = pd.Timestamp("2018-01-01", tz=ET)
END = pd.Timestamp("2022-12-31 23:59:59", tz=ET)
HORIZONS = (5, 10, 15, 30)
SEED = 20260713

def session_info(ts):
    m = ts.hour * 60 + ts.minute
    if m >= 1080 or m <= 179:
        return (ts.date() + pd.Timedelta(days=1) if m >= 1080 else ts.date(), "ASIA")
    if 180 <= m <= 509: return ts.date(), "LONDON"
    if 570 <= m <= 959: return ts.date(), "NEW_YORK"
    return None, None

def _read_dev_member(path):
    """Stream rows only through the development cutoff; do not parse validation rows."""
    cutoff=END.tz_convert("UTC")
    with zipfile.ZipFile(path) as zf:
        names=[n for n in zf.namelist() if n.endswith(".csv.zst")]
        if len(names)!=1: raise ValueError(f"expected one csv.zst: {path}")
        chunks=[]
        with zf.open(names[0]) as compressed, zstd.ZstdDecompressor().stream_reader(compressed) as rd:
            for chunk in pd.read_csv(rd, usecols=["ts_event","open","high","low","close","volume","symbol"], chunksize=100000):
                ts=pd.to_datetime(chunk.ts_event,utc=True)
                good=ts<=cutoff; chunks.append(chunk.loc[good].copy())
                if (~good).any(): break
    return pd.concat(chunks,ignore_index=True) if chunks else pd.DataFrame()

def load_archives(instrument, paths):
    frames=[]
    for path in paths:
        d=_read_dev_member(path)
        d=d[["ts_event","open","high","low","close","volume","symbol"]]
        d["ts_event"]=pd.to_datetime(d.ts_event, utc=True).dt.tz_convert(ET); frames.append(d)
    d=pd.concat(frames, ignore_index=True)
    d=d[d.symbol.astype(str).str.match(re.compile(rf"^{instrument}[HMUZ]\d$"))].drop_duplicates(["ts_event","symbol"])
    et=d.ts_event; minute=et.dt.hour*60+et.dt.minute
    d=d[(minute<1020)|(minute>=1080)].copy()
    info=d.ts_event.map(session_info); d["session_date"]=info.map(lambda x:x[0]); d["session"]=info.map(lambda x:x[1]); d=d[d.session.notna()]
    vol=d.groupby(["session_date","symbol"], sort=True).volume.sum(); leaders=vol.groupby(level=0).idxmax().to_dict(); dates=sorted(leaders)
    prior={dates[i]: leaders[dates[i-1]][1] for i in range(1,len(dates))}; d["front_symbol"]=d.session_date.map(prior); d=d[d.symbol==d.front_symbol].drop(columns="front_symbol")
    d=d[(d.ts_event>=START)&(d.ts_event<=END)].sort_values("ts_event").reset_index(drop=True)
    if d.ts_event.duplicated().any(): raise ValueError(f"duplicate front timestamps {instrument}")
    if len(d)==0 or d.ts_event.dt.year.max()>2022: raise ValueError("partition breach")
    d["instrument"]=instrument
    return d

def _pct(x, history): return float(np.mean(np.asarray(history[-60:]) <= x)) if len(history)>=60 else np.nan

def build_candidates(bars):
    rows=[]
    for (sd,sess), g in bars.groupby(["session_date","session"], sort=True):
        rec=list(g.sort_values("ts_event").itertuples(index=False))
        for i in range(2,len(rec)-2):
            a,b,c,d,e=rec[i-2:i+3]
            if c.ts_event.minute%3!=2: continue
            if any((rec[j].ts_event-rec[j-1].ts_event)!=pd.Timedelta(minutes=1) for j in range(i-1,i+3)): continue
            net=float(c.close-a.open)
            if net==0: continue
            path=abs(a.close-a.open)+abs(b.close-a.close)+abs(c.close-b.close); wh=max(a.high,b.high,c.high); wl=min(a.low,b.low,c.low); rng=wh-wl
            if path<=0 or rng<=0: continue
            s=1 if net>0 else -1; I=abs(net); diag_close=float(e.close)
            max_prog=max(0.0, s*(max(d.high,e.high)-c.close)); diag_rev=max(0.0, s*(c.close-min(d.low,e.low))) if s==1 else max(0.0, s*(c.close-max(d.high,e.high)))
            # The expression above is direction-coordinate equivalent: max opposite excursion.
            max_prog=max(0.0, (max(d.high,e.high)-c.close) if s==1 else (c.close-min(d.low,e.low)))
            diag_rev=max(0.0, (c.close-min(d.low,e.low)) if s==1 else (max(d.high,e.high)-c.close))
            rows.append({"instrument":bars.instrument.iloc[0],"session_date":sd,"session":sess,"impulse_start_ts":a.ts_event,"impulse_end_ts":c.ts_event,"diag_end_ts":e.ts_event,"clock_slot":c.ts_event.hour*60+c.ts_event.minute,"diag_clock_slot":e.ts_event.hour*60+e.ts_event.minute,"event_end_hour":e.ts_event.hour,"impulse_open":float(a.open),"impulse_close":float(c.close),"diagnostic_close":diag_close,"direction":s,"I":I,"net_move":net,"path_length":path,"impulse_range":rng,"volume_impulse":float(a.volume+b.volume+c.volume),"diagnostic_volume":float(d.volume+e.volume),"progress_ratio":s*(diag_close-c.close)/I,"max_progress_ratio":max_prog/I,"diagnostic_reversal_ratio":diag_rev/I})
    return pd.DataFrame(rows)

def causal_normalize(c):
    c=c.sort_values(["session_date","diag_end_ts"]).reset_index(drop=True).copy(); hi=defaultdict(lambda:{"I":[],"dv":[]}); rows=[]
    for r in c.itertuples(index=False):
        q=r._asdict(); k=(r.instrument,r.session,r.clock_slot); kd=(r.instrument,r.session,r.diag_clock_slot)
        q["impulse_prior_n"]=len(hi[k]["I"]); q["volume_prior_n"]=len(hi[kd]["dv"]); q["impulse_percentile"]=_pct(r.I,hi[k]["I"]); q["diagnostic_volume_percentile"]=_pct(r.diagnostic_volume,hi[kd]["dv"])
        hi[k]["I"].append(r.I); hi[kd]["dv"].append(r.diagnostic_volume); rows.append(q)
    return pd.DataFrame(rows)

def classify(r):
    price=(-.10<=r.progress_ratio<=.25 and r.max_progress_ratio<=.40 and r.diagnostic_reversal_ratio<=.25)
    if not np.isfinite(r.impulse_percentile) or r.impulse_percentile<.90 or not np.isfinite(r.diagnostic_volume_percentile): return "NOT_ELIGIBLE"
    if price and r.diagnostic_volume_percentile>=.80: return "HIGH_VOLUME_DECAY"
    if price and r.diagnostic_volume_percentile<=.50: return "LOW_VOLUME_DECAY_CONTROL"
    if r.diagnostic_volume_percentile>=.80 and r.progress_ratio>.25: return "HIGH_VOLUME_PROGRESS_CONTROL"
    return "OTHER"

def bands(c):
    c["impulse_band"]=pd.cut(c.impulse_percentile,[.90,.95,.99,np.inf],labels=["P90_TO_P95","P95_TO_P99","P99_PLUS"],right=False).astype(object).fillna("NA")
    c["progress_band"]=pd.cut(c.progress_ratio,[-.1000001,0,.10,.20,.2500001],labels=["P_NEG_10_TO_0","P_0_TO_10","P_10_TO_20","P_20_TO_25"],right=False).astype(object).fillna("NA")
    c["max_progress_band"]=pd.cut(c.max_progress_ratio,[-.000001,.10,.20,.30,.400001],labels=["MP_0_TO_10","MP_10_TO_20","MP_20_TO_30","MP_30_TO_40"],right=False).astype(object).fillna("NA")
    return c

def deduplicate(c):
    c=c.sort_values(["instrument","session_date","impulse_start_ts"]).copy(); kept=[]; lock=None; last=None
    for r in c.itertuples(index=False):
        if (r.instrument,r.session_date)!=last: lock=None; last=(r.instrument,r.session_date)
        ok=r.state in {"HIGH_VOLUME_DECAY","LOW_VOLUME_DECAY_CONTROL","HIGH_VOLUME_PROGRESS_CONTROL"} and (lock is None or r.impulse_start_ts>lock)
        kept.append(ok)
        if ok: lock=r.diag_end_ts+pd.Timedelta(minutes=30)
    c["dedup_kept"]=kept; return c[c.dedup_kept].copy()

def outcomes(events,bars):
    lookup={r.ts_event:r for r in bars.itertuples(index=False)}; rows=[]
    for r in events.itertuples(index=False):
        fut=[]; complete=True
        for h in range(1,31):
            x=lookup.get(r.diag_end_ts+pd.Timedelta(minutes=h))
            if x is None or x.session_date!=r.session_date or x.session!=r.session: complete=False; break
            fut.append(x)
        q=r._asdict();
        for H in HORIZONS:
            vals=fut[:H] if complete or len(fut)>=H else []
            if not vals: q[f"outcome_{H}"]="INCOMPLETE_HORIZON"; continue
            cb=r.diagnostic_close+r.direction*.5*r.I; rb=r.diagnostic_close-r.direction*.5*r.I; cf=rf=None
            for j,x in enumerate(vals,1):
                ch=x.high>=cb if r.direction==1 else x.low<=cb; rh=x.low<=rb if r.direction==1 else x.high>=rb
                if cf is None and ch: cf=j
                if rf is None and rh: rf=j
                if cf is not None and rf is not None: break
            if cf is None and rf is None: out="NEITHER_WITHIN_HORIZON"
            elif cf is not None and rf is not None and cf==rf: out="SAME_BAR_AMBIGUOUS"
            elif cf is not None and (rf is None or cf<rf): out="CONTINUATION_FIRST"
            else: out="REVERSAL_FIRST"
            q[f"outcome_{H}"]=out
        rows.append(q)
    return pd.DataFrame(rows)

def bh(p):
    p=np.asarray(p,float); q=np.full(len(p),np.nan); ok=np.isfinite(p)
    if not ok.any(): return q
    idx=np.flatnonzero(ok); order=idx[np.argsort(p[idx])]; adj=np.minimum.accumulate((p[order]*len(order)/np.arange(1,len(order)+1))[::-1])[::-1]; q[order]=np.minimum(adj,1); return q

def perm_pvalue(g, outcome_col="outcome_15", n=10000, seed=SEED):
    x=g[g.state.isin(["HIGH_VOLUME_DECAY","LOW_VOLUME_DECAY_CONTROL"]) & g[outcome_col].isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])].copy()
    if x.empty or not (x.state=="HIGH_VOLUME_DECAY").any() or not (x.state=="LOW_VOLUME_DECAY_CONTROL").any(): return np.nan
    y=(x[outcome_col]=="REVERSAL_FIRST").to_numpy(dtype=np.int8); lab=x.state.to_numpy(); strata=x.stratum.to_numpy(); obs=y[lab=="HIGH_VOLUME_DECAY"].mean()-y[lab=="LOW_VOLUME_DECAY_CONTROL"].mean(); rng=np.random.default_rng(seed); hit=0
    groups=[]
    for _,g in x.groupby("stratum",sort=True):
        yy=(g[outcome_col]=="REVERSAL_FIRST").to_numpy(dtype=np.int8); k=int((g.state=="HIGH_VOLUME_DECAY").sum()); groups.append((yy,k))
    ne=int((lab=="HIGH_VOLUME_DECAY").sum()); nl=len(lab)-ne
    for start in range(0,n,256):
        q=min(256,n-start); high=np.zeros(q,dtype=np.int64); low=np.zeros(q,dtype=np.int64)
        for yy,k in groups:
            if k==0 or k==len(yy): continue
            chosen=np.argpartition(rng.random((q,len(yy))),k-1,axis=1)[:,:k]; hw=yy[chosen].sum(axis=1); high+=hw; low+=yy.sum()-hw
        hit += int(np.sum(np.abs(high/ne-low/nl)>=abs(obs)-1e-15))
    return (hit+1)/(n+1)

def primary(events):
    x=events.copy(); x["stratum"]=x.apply(lambda r:f"{r.instrument}|{r.session}|{r.direction}|{r.diag_clock_slot}|{r.impulse_band}|{r.progress_band}|{r.max_progress_band}",axis=1); rows=[]
    for key,g in x.groupby(["instrument","session","direction"],sort=True):
        e=g[g.state=="HIGH_VOLUME_DECAY"]; q=g[g.state=="LOW_VOLUME_DECAY_CONTROL"]; re=e[e.outcome_15.isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])]; rq=q[q.outcome_15.isin(["REVERSAL_FIRST","CONTINUATION_FIRST"])]
        matched=sum(1 for _,s in g.groupby("stratum") if {"HIGH_VOLUME_DECAY","LOW_VOLUME_DECAY_CONTROL"}.issubset(set(s.state)))
        er=(re.outcome_15=="REVERSAL_FIRST").mean() if len(re) else np.nan; qr=(rq.outcome_15=="REVERSAL_FIRST").mean() if len(rq) else np.nan
        rows.append({"instrument":key[0],"session":key[1],"direction":key[2],"n_high_volume_decay":len(e),"n_low_volume_control":len(q),"resolved_high":len(re),"resolved_low":len(rq),"ambiguous_high":int((e.outcome_15=="SAME_BAR_AMBIGUOUS").sum()),"ambiguous_low":int((q.outcome_15=="SAME_BAR_AMBIGUOUS").sum()),"neither_high":int((e.outcome_15=="NEITHER_WITHIN_HORIZON").sum()),"neither_low":int((q.outcome_15=="NEITHER_WITHIN_HORIZON").sum()),"incomplete_high":int((e.outcome_15=="INCOMPLETE_HORIZON").sum()),"incomplete_low":int((q.outcome_15=="INCOMPLETE_HORIZON").sum()),"matched_strata":matched,"high_reversal_rate":er,"low_reversal_rate":qr,"difference":er-qr,"p_value":perm_pvalue(g)})
    out=pd.DataFrame(rows); out["q_value"]=bh(out.p_value); out["classification"]=np.where((out.n_low_volume_control<100)|(out.resolved_low<50),"UNDERPOWERED",np.where((out.difference>=.05)&(out.q_value<.05),"HIGH_VOLUME_REVERSAL_SUPPORTED",np.where((out.difference<=-.05)&(out.q_value<.05),"HIGH_VOLUME_REVERSAL_REJECTED","NULL_OR_MIXED"))); return out,x
