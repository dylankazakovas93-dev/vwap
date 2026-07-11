"""Build the session-level atlas ledger for one instrument (dev partition)."""
import os

import pandas as pd

from .atlas import build_dense_bars, build_session_ledger

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(REPO, "research", "cash_open_atlas", "outputs")
DEV_END = pd.Timestamp("2022-12-31")


def load_dev(instrument: str) -> pd.DataFrame:
    df = pd.read_parquet(os.path.join(PROC, f"{instrument.lower()}_front_1m.parquet"))
    df = df[df["session_date"] <= DEV_END].copy()
    assert df["session_date"].max() <= DEV_END, "partition breach"
    return df


def main(instrument: str):
    os.makedirs(OUT, exist_ok=True)
    df = load_dev(instrument)
    bars = build_dense_bars(df, tau_max=59)
    led, missing = build_session_ledger(bars, instrument)
    led["data_partition"] = "development"
    led.to_parquet(os.path.join(OUT, f"{instrument.lower()}_atlas_ledger.parquet"), index=False)
    missing.to_csv(os.path.join(OUT, f"{instrument.lower()}_missing_sessions.csv"), index=False)
    n_total_sessions = df["session_date"].nunique()
    print(f"{instrument}: {n_total_sessions} total dev sessions; "
          f"{len(led)} primary-valid; {led['secondary_valid'].sum()} secondary-valid; "
          f"{len(missing)} missing-log rows", flush=True)


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
