"""Self-contained statistical utilities for generation 4."""
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
GEN_DIR = os.path.join(REPO, "research", "previous_close_predictor")
TAB = os.path.join(GEN_DIR, "reports", "tables")
OUT = os.path.join(GEN_DIR, "outputs")


def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 10 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 10 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    xr = pd.Series(x).rank().to_numpy()
    yr = pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(xr, yr)[0, 1])


def n_valid_pairs(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return int((np.isfinite(x) & np.isfinite(y)).sum())


def boot_ci_corr(x, y, method="spearman", nboot=NBOOT, seed=SEED):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    n = len(x)
    if n < 20:
        return np.nan, np.nan
    fn = spearman if method == "spearman" else pearson
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(nboot):
        idx = rng.integers(0, n, n)
        stats.append(fn(x[idx], y[idx]))
    stats = np.asarray(stats, float)
    return float(np.nanpercentile(stats, 2.5)), float(np.nanpercentile(stats, 97.5))


def z_from_spearman(rho, n):
    """Approx two-sided p-value for Spearman rho via Fisher z (n-3)."""
    if not np.isfinite(rho) or n < 4 or abs(rho) >= 1:
        return np.nan
    z = np.arctanh(rho) * np.sqrt((n - 3) / 1.06)
    from math import erf
    p = 2 * (1 - 0.5 * (1 + erf(abs(z) / np.sqrt(2))))
    return p


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
            "run_id": f"g4_{self.n:04d}", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": self.sha, "dataset_hash": "see DATA_CONTRACT.md", "stage": "predictor_screen",
            "hypothesis_id": hyp, "config_hash": ch, "parent_run_id": "",
            "change_reason": "", "train_period": "2018-2022", "validation_period": "",
            "test_period": "", "seed": SEED, "command": json.dumps(config, default=str),
            "status": status, "primary_metric": metric, "selected": "", "notes": notes,
        }])
        row.to_csv(self.path, mode="a", header=False, index=False)
