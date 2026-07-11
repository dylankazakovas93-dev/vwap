"""Build the generation-5 session-level ledger: overnight/pre-open
features joined to next-session atlas targets (reused unmodified from
generation 3 via file-path import). Development partition only.
"""
import importlib.util
import os

import pandas as pd

from .overnight_features import build_overnight_ledger

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(REPO, "research", "overnight_preopen_predictor", "outputs")
ATLAS_PATH = os.path.join(REPO, "research", "cash_open_atlas", "src", "atlas.py")
DEV_END = pd.Timestamp("2022-12-31")
TARGET_HORIZONS = (5, 10, 15, 30)


def _load_atlas_module():
    spec = importlib.util.spec_from_file_location("gen3_atlas_g5", ATLAS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_dev(instrument: str) -> pd.DataFrame:
    df = pd.read_parquet(os.path.join(PROC, f"{instrument.lower()}_front_1m.parquet"))
    df = df[df["session_date"] <= DEV_END].copy()
    assert df["session_date"].max() <= DEV_END, "partition breach"
    return df


def build_full_ledger(instrument: str):
    df = load_dev(instrument)
    atlas = _load_atlas_module()

    bar_frames = atlas.build_dense_bars(df, tau_max=59)
    target_led, target_missing = atlas.build_session_ledger(bar_frames, instrument)
    target_cols = ["session_date"] + [f"{m}_{h}" for h in TARGET_HORIZONS for m in ("R", "Q")]
    target_led = target_led[target_cols].copy()

    feat = build_overnight_ledger(df, instrument)
    led = target_led.merge(feat, on="session_date", how="inner")
    led["data_partition"] = "development"
    n_no_feat = len(target_led) - len(led)
    return led, n_no_feat, target_missing


def main(instrument: str):
    os.makedirs(OUT, exist_ok=True)
    led, n_no_feat, target_missing = build_full_ledger(instrument)
    led.to_parquet(os.path.join(OUT, f"{instrument.lower()}_overnight_ledger.parquet"), index=False)
    target_missing.to_csv(os.path.join(OUT, f"{instrument.lower()}_target_missing.csv"), index=False)
    n_sec6 = int(led["prior_rth_close"].notna().sum()) if "prior_rth_close" in led.columns else 0
    print(f"{instrument}: {len(led)} primary rows ({n_no_feat} target sessions lacked overnight "
          f"features); {n_sec6} rows have a valid Sec.6 predecessor "
          f"({len(led) - n_sec6} lack one)", flush=True)


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
