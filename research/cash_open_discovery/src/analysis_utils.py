"""Shared statistical utilities (self-contained in this generation)."""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd

SEED = 20260711
NBOOT = 500

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GEN_DIR = os.path.join(REPO, "research", "cash_open_discovery")
TAB = os.path.join(GEN_DIR, "reports", "tables")
OUT = os.path.join(GEN_DIR, "outputs")


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 10 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    xr = pd.Series(x).rank().to_numpy()
    yr = pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(xr, yr)[0, 1])


def session_boot_ci(df, stat_fn, session_col="session_date", nboot=NBOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    sess = df[session_col].to_numpy()
    uniq = np.unique(sess)
    if len(uniq) < 5:
        return np.nan, np.nan
    groups = {s: np.flatnonzero(sess == s) for s in uniq}
    stats = []
    for _ in range(nboot):
        draw = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([groups[s] for s in draw])
        stats.append(stat_fn(df.iloc[idx]))
    stats = np.asarray(stats, float)
    return float(np.nanpercentile(stats, 2.5)), float(np.nanpercentile(stats, 97.5))


def git_sha():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()


class Registry:
    def __init__(self, path=None):
        self.path = path or os.path.join(GEN_DIR, "RUN_REGISTRY.csv")
        self.sha = git_sha()
        self.n = 0

    def log(self, hyp, config, status="ok", metric="", notes=""):
        self.n += 1
        ch = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:12]
        row = pd.DataFrame([{
            "run_id": f"g2_{self.n:03d}", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": self.sha, "dataset_hash": "see DATA_CONTRACT.md", "stage": "discovery",
            "hypothesis_id": hyp, "config_hash": ch, "parent_run_id": "",
            "change_reason": "", "train_period": "2018-2022", "validation_period": "",
            "test_period": "", "seed": SEED, "command": json.dumps(config, default=str),
            "status": status, "primary_metric": metric, "selected": "", "notes": notes,
        }])
        row.to_csv(self.path, mode="a", header=False, index=False)
