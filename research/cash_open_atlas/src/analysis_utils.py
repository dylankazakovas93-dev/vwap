"""Self-contained statistical utilities for generation 3."""
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
GEN_DIR = os.path.join(REPO, "research", "cash_open_atlas")
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


def session_boot_ci(values, nboot=NBOOT, seed=SEED):
    """Day-block bootstrap over independent session observations (one value
    per session already, so a session-block resample is just an ordinary
    resample of rows here)."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if len(v) < 5:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(v, size=len(v), replace=True).mean() for _ in range(nboot)])
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def git_sha():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()


class Registry:
    def __init__(self):
        self.path = os.path.join(GEN_DIR, "RUN_REGISTRY.csv")
        self.sha = git_sha()
        self.n = 0

    def log(self, hyp, config, status="ok", metric="", notes=""):
        self.n += 1
        ch = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:12]
        row = pd.DataFrame([{
            "run_id": f"g3_{self.n:03d}", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": self.sha, "dataset_hash": "see DATA_CONTRACT.md", "stage": "atlas",
            "hypothesis_id": hyp, "config_hash": ch, "parent_run_id": "",
            "change_reason": "", "train_period": "2018-2022", "validation_period": "",
            "test_period": "", "seed": SEED, "command": json.dumps(config, default=str),
            "status": status, "primary_metric": metric, "selected": "", "notes": notes,
        }])
        row.to_csv(self.path, mode="a", header=False, index=False)
