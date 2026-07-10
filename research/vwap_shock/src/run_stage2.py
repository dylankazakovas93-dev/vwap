"""Stage 2 runner: features + event ledgers on the DEVELOPMENT partition only.

Events are built once at the loosest registered threshold (|z_mod| >= 3);
the z >= 4 robustness set is a pure row-subset of the same ledger (identical
features/outcomes), so no separate pass is needed.

Usage: python -m src.run_stage2 [ES|NQ]
"""
import os
import sys

import pandas as pd

from .features import compute_features
from .events import build_event_ledger

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(REPO, "research", "vwap_shock", "outputs")

DEV_END = pd.Timestamp("2022-12-31")


def load_dev(instrument: str) -> pd.DataFrame:
    df = pd.read_parquet(os.path.join(PROC, f"{instrument.lower()}_front_1m.parquet"))
    df = df[df["session_date"] <= DEV_END].copy()
    assert df["session_date"].max() <= DEV_END, "partition breach"
    return df


def main(instrument: str):
    os.makedirs(OUT, exist_ok=True)
    feat_path = os.path.join(OUT, f"{instrument.lower()}_features_dev.parquet")
    if os.path.exists(feat_path):
        feat = pd.read_parquet(feat_path)
        print(f"{instrument}: loaded cached features ({len(feat)} bars)", flush=True)
    else:
        df = load_dev(instrument)
        print(f"{instrument}: {len(df)} dev bars, sessions "
              f"{df['session_date'].min().date()} -> {df['session_date'].max().date()}", flush=True)
        feat = compute_features(df)
        feat.to_parquet(feat_path, index=False)
        print("features done", flush=True)
    assert feat["session_date"].max() <= DEV_END, "partition breach"

    # candidate ledger (|z_mod|>=2 persistence rule, Decision #8)
    cand = feat[(feat["z_mod1"].abs() >= 2) | (feat["z_mod3"].abs() >= 2)]
    cand_cols = ["ts_event", "session_date", "et_minute", "symbol", "segment",
                 "macro_window", "z_mod1", "z_mod3", "z_atr1", "z_atr3",
                 "z_vol", "dev_g", "atr30", "close", "volume"]
    cand[cand_cols].to_parquet(os.path.join(OUT, f"{instrument.lower()}_candidates_dev.parquet"), index=False)
    per_sess = feat.groupby("session_date").agg(
        n_bars=("close", "size"),
        n_valid_z1=("z_mod1", lambda s: int(s.notna().sum())),
        n_ev_k1=("z_mod1", lambda s: int((s.abs() >= 3).sum())),
        n_ev_k3=("z_mod3", lambda s: int((s.abs() >= 3).sum())),
    )
    per_sess.to_csv(os.path.join(OUT, f"{instrument.lower()}_candidate_counts.csv"))

    for k in (1, 3):
        led = build_event_ledger(feat, k=k, z_thr=3.0, instrument=instrument)
        led.to_parquet(os.path.join(OUT, f"{instrument.lower()}_events_k{k}_dev.parquet"), index=False)
        print(f"k={k}: {len(led)} events "
              f"({(led[f'z_mod{k}'].abs() >= 4).sum()} at z>=4)", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
