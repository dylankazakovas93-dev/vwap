"""Stage 2 preregistered analysis: quantile response maps, monotonicity,
nested increments, acceptance, matched placebo. Development partition only.

All CIs: session-block bootstrap, 500 resamples, seed 20260710.
Continuation label: first-passage CONT = 1; REV and AMBIG = 0 (conservative);
NONE/INVALID excluded from the rate denominator (reported separately).
"""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd

SEED = 20260710
NBOOT = 500
TICK = 0.25  # points per tick, ES and NQ
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(REPO, "research", "vwap_shock", "outputs")
TAB = os.path.join(REPO, "research", "vwap_shock", "reports", "tables")

FEATURES = [
    "D5_atr_d", "D15_atr_d", "D60_atr_d",
    "P5_d", "P15_d", "P60_d",
    "E5_d", "E15_d", "E60_d",
    "run_d", "z_vol", "vol_ratio", "body_eff", "closeloc_dir",
    "dev_g_d", "dev_r_d", "slope_d",
]
INCREMENT_MAP = {  # nested comparison name -> feature added to displacement
    "persistence": "P15_d", "path_efficiency": "E15_d",
    "candle_efficiency": "body_eff", "volume": "z_vol",
    "vwap_distance": "dev_g_d",
}


def decided(df):
    return df[df["fp_outcome"].isin(["CONT", "REV", "AMBIG"])].copy()


def cont_y(df):
    return (df["fp_outcome"] == "CONT").astype(float)


def spearman(x, y):
    xr = pd.Series(x).rank().to_numpy()
    yr = pd.Series(y).rank().to_numpy()
    if len(xr) < 10 or np.std(xr) == 0 or np.std(yr) == 0:
        return np.nan
    return float(np.corrcoef(xr, yr)[0, 1])


def session_boot_ci(df, stat_fn, nboot=NBOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    sess = df["session_date"].to_numpy()
    uniq = np.unique(sess)
    groups = {s: np.flatnonzero(sess == s) for s in uniq}
    stats = []
    for _ in range(nboot):
        draw = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([groups[s] for s in draw])
        stats.append(stat_fn(df.iloc[idx]))
    stats = np.asarray(stats, float)
    return float(np.nanpercentile(stats, 2.5)), float(np.nanpercentile(stats, 97.5))


def response_map(df, feature, k):
    d = decided(df).dropna(subset=[feature])
    if len(d) < 100:
        return []
    d["y"] = cont_y(d)
    try:
        d["q"] = pd.qcut(d[feature], 5, labels=False, duplicates="drop")
    except ValueError:
        return []
    rows = []
    for q, grp in d.groupby("q"):
        rows.append({
            "feature": feature, "quintile": int(q), "n": len(grp),
            "feat_lo": float(grp[feature].min()), "feat_hi": float(grp[feature].max()),
            "cont_rate": float(grp["y"].mean()),
            "fret_15_ticks": float(grp["fret_15"].mean() / TICK),
            "fret_30_ticks": float(grp["fret_30"].mean() / TICK),
            "fret_60_ticks": float(grp["fret_60"].mean() / TICK),
        })
    return rows


def monotonicity(df, feature, with_ci):
    d = decided(df).dropna(subset=[feature])
    if len(d) < 100:
        return None
    d["y"] = cont_y(d)
    rec = {"feature": feature, "n": len(d),
           "spearman_cont": spearman(d[feature], d["y"]),
           "spearman_fret30": spearman(d[feature], d["fret_30"].fillna(0))}
    if with_ci:
        lo, hi = session_boot_ci(d, lambda b: spearman(b[feature], b["y"]))
        rec["ci_lo"], rec["ci_hi"] = lo, hi
    return rec


def increment_stat(d, feature):
    """Displacement-controlled top-vs-bottom quintile continuation diff."""
    diffs, ws = [], []
    d = d.dropna(subset=[feature, "zabs"])
    if len(d) < 250:
        return np.nan
    try:
        d = d.assign(zq=pd.qcut(d["zabs"], 5, labels=False, duplicates="drop"))
    except ValueError:
        return np.nan
    for _, s in d.groupby("zq"):
        if len(s) < 50:
            continue
        try:
            fq = pd.qcut(s[feature], 5, labels=False, duplicates="drop")
        except ValueError:
            continue
        top = s.loc[fq == fq.max(), "y"]
        bot = s.loc[fq == fq.min(), "y"]
        if len(top) >= 10 and len(bot) >= 10:
            diffs.append(top.mean() - bot.mean())
            ws.append(len(s))
    if not diffs:
        return np.nan
    return float(np.average(diffs, weights=ws))


def acceptance_table(df, instrument, k, z):
    rows = []
    for anchor in ("g", "r"):
        for rule in ("A1", "A2"):
            col = f"{anchor}_{rule}_status"
            if col not in df.columns:
                continue
            sub = df[df[col].isin(["ACCEPT", "REJECT"])]
            for st, grp in sub.groupby(col):
                rec = {"instrument": instrument, "k": k, "z_thr": z,
                       "anchor": anchor, "rule": rule, "status": st, "n": len(grp)}
                if anchor == "g":
                    fp = grp[f"{rule}_post_fp"].dropna()
                    dec = fp[fp.isin(["CONT", "REV", "AMBIG"])]
                    rec["post_cont_rate"] = float((dec == "CONT").mean()) if len(dec) else np.nan
                    rec["post_n_decided"] = int(len(dec))
                    for h in (15, 30, 60):
                        c = f"{rule}_post_fret_{h}"
                        rec[f"post_fret_{h}_ticks"] = float(grp[c].mean() / TICK) if c in grp else np.nan
                d2 = decided(grp)
                rec["evt_cont_rate"] = float(cont_y(d2).mean()) if len(d2) else np.nan
                rows.append(rec)
    return rows


def match_placebo(feat, events, rng):
    """Match each event to a non-event bar: same segment, ATR decile
    (dev-sample deciles, Decision #10), ET minute bucket (15-min)."""
    pool = feat[(feat["z_mod1"].abs() < 1.5) & feat["z_mod1"].notna()
                & feat["atr30"].notna()].copy()
    pool["atr_dec"] = pd.qcut(pool["atr30"], 10, labels=False, duplicates="drop")
    dec_edges = pool["atr30"].quantile(np.linspace(0, 1, 11)).to_numpy()
    ev_dec = np.clip(np.searchsorted(dec_edges[1:-1], events["atr30"].to_numpy()), 0, 9)
    pool["bucket"] = pool["et_minute"] // 15
    groups = {kk: v.sample(frac=1, random_state=SEED).index.to_list()
              for kk, v in pool.groupby(["segment", "atr_dec", "bucket"])}
    fallback = {kk: v.sample(frac=1, random_state=SEED).index.to_list()
                for kk, v in pool.groupby(["segment", "atr_dec"])}
    used = set()
    chosen = []
    for (seg, mb), dec in zip(zip(events["segment"], events["et_minute"] // 15), ev_dec):
        for key, table in (((seg, dec, mb), groups), ((seg, dec), fallback)):
            lst = table.get(key, [])
            while lst:
                cand = lst.pop()
                if cand not in used:
                    used.add(cand)
                    chosen.append(cand)
                    break
            else:
                continue
            break
    return feat.loc[sorted(chosen)]


def git_sha():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()


class Registry:
    def __init__(self):
        self.path = os.path.join(REPO, "RUN_REGISTRY.csv")
        self.sha = git_sha()
        self.n = 0

    def log(self, stage, hyp, config, status, metric, notes=""):
        self.n += 1
        ch = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:12]
        row = pd.DataFrame([{
            "run_id": f"s2_{self.n:03d}", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": self.sha, "dataset_hash": "see DATA_CONTRACT.md", "stage": stage,
            "hypothesis_id": hyp, "config_hash": ch, "parent_run_id": "",
            "change_reason": "", "train_period": "2018-2022", "validation_period": "",
            "test_period": "", "seed": SEED, "command": json.dumps(config, default=str),
            "status": status, "primary_metric": metric, "selected": "", "notes": notes,
        }])
        row.to_csv(self.path, mode="a", header=False, index=False)
