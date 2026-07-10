"""Stage 0: build causal front-month continuous 1-minute series for ES and NQ.

Reads raw Databento GLBX.MDP3 ohlcv-1m csv.zst files (parent symbology),
filters to outright quarterly contracts, constructs session dates in
America/New_York, selects the front month causally (prior session's volume
leader), and writes one parquet per root to data/processed/.

Raw data are never modified. All exclusions are logged to the audit report.

Usage: python -m src.data_build  (run from research/vwap_shock/)
"""
import io
import json
import os
import re
import sys

import numpy as np
import pandas as pd
import zstandard

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RAW = os.path.join(REPO, "data", "raw")
PROC = os.path.join(REPO, "data", "processed")
REPORTS = os.path.join(REPO, "research", "vwap_shock", "reports")

OUTRIGHT_RE = re.compile(r"^(ES|NQ)[HMUZ]\d$")
ET = "America/New_York"

FILES = {
    "ES": ["es2018.ohlcv-1m.csv.zst", "es2023.ohlcv-1m.csv.zst", "es2026.ohlcv-1m.csv.zst"],
    "NQ": [
        "nq2018.ohlcv-1m.csv.zst", "nq2020.ohlcv-1m.csv.zst", "nq2021.ohlcv-1m.csv.zst",
        "nq2023.ohlcv-1m.csv.zst", "nq2025.ohlcv-1m.csv.zst",
    ],
}


def read_zst_csv(path: str) -> pd.DataFrame:
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    df = pd.read_csv(
        io.BytesIO(data),
        usecols=["ts_event", "open", "high", "low", "close", "volume", "symbol"],
        dtype={"open": "float64", "high": "float64", "low": "float64",
               "close": "float64", "volume": "int64", "symbol": "str"},
    )
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    return df


def build_root(root: str, audit: dict) -> pd.DataFrame:
    frames = [read_zst_csv(os.path.join(RAW, f)) for f in FILES[root]]
    df = pd.concat(frames, ignore_index=True)
    audit[f"{root}_raw_rows"] = int(len(df))

    # outrights only (drop calendar spreads etc.)
    m = df["symbol"].str.match(OUTRIGHT_RE)
    audit[f"{root}_spread_rows_dropped"] = int((~m).sum())
    df = df[m].copy()

    # overlap between adjacent archive date ranges -> exact duplicates possible
    before = len(df)
    df = df.drop_duplicates(subset=["ts_event", "symbol"], keep="first")
    audit[f"{root}_duplicate_rows_dropped"] = int(before - len(df))

    # ET session construction: session_date = date(ET + 6h); maintenance
    # halt bars 17:00-17:59 ET excluded.
    et = df["ts_event"].dt.tz_convert(ET)
    df["et_minute"] = et.dt.hour * 60 + et.dt.minute
    halt = (df["et_minute"] >= 17 * 60) & (df["et_minute"] < 18 * 60)
    audit[f"{root}_maintenance_halt_rows_dropped"] = int(halt.sum())
    df = df[~halt].copy()
    et = df["ts_event"].dt.tz_convert(ET)
    df["session_date"] = (et + pd.Timedelta(hours=6)).dt.date

    # causal front-month: volume leader of the PRIOR session
    sess_vol = df.groupby(["session_date", "symbol"], sort=True)["volume"].sum()
    leader = sess_vol.groupby(level=0).idxmax().map(lambda x: x[1])
    sessions = leader.index.to_list()
    front = {}
    for i, s in enumerate(sessions):
        if i == 0:
            continue  # no prior session -> dropped (logged)
        front[s] = leader.iloc[i - 1]
    audit[f"{root}_first_session_dropped"] = str(sessions[0])
    fm = pd.Series(front, name="front_symbol")
    df = df.merge(fm.rename_axis("session_date").reset_index(), on="session_date", how="inner")
    df = df[df["symbol"] == df["front_symbol"]].drop(columns=["front_symbol"])
    audit[f"{root}_front_month_rows"] = int(len(df))

    df = df.sort_values("ts_event").reset_index(drop=True)

    # OHLC sanity
    bad = (
        (df["high"] < df["low"])
        | (df["open"] > df["high"]) | (df["open"] < df["low"])
        | (df["close"] > df["high"]) | (df["close"] < df["low"])
        | (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    )
    audit[f"{root}_impossible_ohlc_rows"] = int(bad.sum())
    if bad.any():
        df = df[~bad].copy()

    audit[f"{root}_zero_volume_rows"] = int((df["volume"] == 0).sum())

    # roll flags: first session on a new contract
    sd = df.drop_duplicates("session_date")[["session_date", "symbol"]].sort_values("session_date")
    sd["roll"] = sd["symbol"] != sd["symbol"].shift(1)
    df = df.merge(sd[["session_date", "roll"]], on="session_date", how="left")
    audit[f"{root}_n_rolls"] = int(sd["roll"].sum()) - 1

    # coverage / gap stats
    per_sess = df.groupby("session_date").size()
    audit[f"{root}_n_sessions"] = int(len(per_sess))
    audit[f"{root}_first_session"] = str(per_sess.index[0])
    audit[f"{root}_last_session"] = str(per_sess.index[-1])
    audit[f"{root}_median_bars_per_session"] = float(per_sess.median())
    audit[f"{root}_sessions_lt_800_bars"] = int((per_sess < 800).sum())
    audit[f"{root}_bars_total"] = int(len(df))

    # intra-session duplicate timestamps must be zero now
    dup_ts = df.duplicated(subset=["ts_event"]).sum()
    audit[f"{root}_residual_duplicate_ts"] = int(dup_ts)

    df["session_date"] = pd.to_datetime(df["session_date"])
    out = df[["ts_event", "session_date", "et_minute", "symbol", "roll",
              "open", "high", "low", "close", "volume"]]
    out.to_parquet(os.path.join(PROC, f"{root.lower()}_front_1m.parquet"), index=False)
    return out


def main():
    os.makedirs(PROC, exist_ok=True)
    audit = {}
    for root in ("ES", "NQ"):
        build_root(root, audit)
    with open(os.path.join(REPORTS, "stage0_audit.json"), "w") as fh:
        json.dump(audit, fh, indent=2)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
