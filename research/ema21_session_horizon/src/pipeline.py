"""End-to-end pipeline: 1m parquet -> continuous 5m bars -> EMA21/ATR20
-> session legs -> per-leg events -> outcomes -> barriers -> summary
cells -> primary BH -> year stability -> classification.

Usage: python -m src.pipeline   (run from research/ema21_session_horizon/)
"""
import json
import os

import pandas as pd

from . import five_min_bars as fmb
from . import ema
from . import sessions as ses
from . import events as ev
from . import outcomes as oc
from . import summary as sm
from . import classification as cl

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "outputs")
REPORTS = os.path.join(HERE, "..", "reports")
TABLES = os.path.join(REPORTS, "tables")

INSTRUMENTS = ("ES", "NQ")


def build_instrument(root: str):
    df1m = fmb.filter_development(fmb.load_1m(root))
    bars, n_incomplete = fmb.build_full_5m(df1m)
    bars = ema.add_atr(ema.add_ema_and_level(bars))
    bars = ses.add_session_columns(bars)

    audit = {
        "instrument": root,
        "n_1m_rows_dev": int(len(df1m)),
        "n_full_5m_bars": int(len(bars)),
        "n_full_5m_incomplete_dropped": int(n_incomplete),
        "n_bars_by_leg": bars["leg"].value_counts().to_dict(),
        "n_session_leg_instances": int(bars.loc[bars["leg"] != "EXCLUDED", "session_leg_id"].nunique()),
    }
    return bars, audit


def run_instrument(root: str, bars: pd.DataFrame):
    all_events = []
    all_excursions = []
    for leg_id, g in bars.loc[bars["leg"] != "EXCLUDED"].groupby("session_leg_id", sort=False):
        g = g.sort_values("ts_event").reset_index(drop=True)
        leg = g["leg"].iloc[0]
        session_date = g["session_date"].iloc[0]
        exc, touches = ev.detect_leg(g, leg, session_date, root)
        if not exc.empty:
            all_excursions.append(exc)
        if touches.empty:
            continue
        outc = oc.add_outcomes(g, touches)
        barr = oc.add_barrier_outcomes(g, outc)
        merged = outc.merge(
            barr.drop(columns=["instrument", "session_date", "session"]),
            on="local_touch_idx", how="left",
        )
        all_events.append(merged)

    events_full = pd.concat(all_events, ignore_index=True) if all_events else pd.DataFrame()
    excursions_full = pd.concat(all_excursions, ignore_index=True) if all_excursions else pd.DataFrame()
    return events_full, excursions_full


def run_all():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)

    all_events = []
    all_excursions = []
    audits = []

    for root in INSTRUMENTS:
        bars, audit = build_instrument(root)
        audits.append(audit)
        bars.to_parquet(os.path.join(OUT, f"{root.lower()}_5m_full.parquet"))
        events_full, excursions_full = run_instrument(root, bars)
        if not events_full.empty:
            all_events.append(events_full)
        if not excursions_full.empty:
            all_excursions.append(excursions_full)

    events_full = pd.concat(all_events, ignore_index=True) if all_events else pd.DataFrame()
    excursions_full = pd.concat(all_excursions, ignore_index=True) if all_excursions else pd.DataFrame()

    events_full.to_csv(os.path.join(OUT, "all_touch_events_with_outcomes.csv"), index=False)
    excursions_full.to_csv(os.path.join(OUT, "all_armed_excursions.csv"), index=False)

    with open(os.path.join(OUT, "bar_audit.json"), "w") as fh:
        json.dump(audits, fh, indent=2, default=str)

    cells = sm.build_cells(events_full, excursions_full)
    cells.to_csv(os.path.join(TABLES, "full_exploratory_results.csv"), index=False)

    pc = cl.apply_bh_primary(cells)
    yr = cl.year_stability(events_full)
    yr.to_csv(os.path.join(TABLES, "year_stability.csv"), index=False)

    classified = cl.classify_primary(pc, yr)
    classified.to_csv(os.path.join(TABLES, "primary_result_table.csv"), index=False)

    session_mech = cl.classify_sessions(classified)
    session_mech.to_csv(os.path.join(TABLES, "session_mechanism_table.csv"), index=False)

    same_bar = cells.loc[(cells["horizon_bars"] == cl.HORIZONS[0]) & (cells["barrier_atr"] == 1.0)]
    same_bar.to_csv(os.path.join(TABLES, "same_bar_table.csv"), index=False)

    null_inv = classified.loc[classified["classification"] == "MIXED_OR_NULL"]
    null_inv.to_csv(os.path.join(TABLES, "null_inventory.csv"), index=False)
    underpowered_inv = classified.loc[classified["classification"] == "UNDERPOWERED"]
    underpowered_inv.to_csv(os.path.join(TABLES, "underpowered_inventory.csv"), index=False)

    return {
        "events_full": events_full,
        "excursions_full": excursions_full,
        "cells": cells,
        "primary_classified": classified,
        "session_mechanism": session_mech,
        "year_stability": yr,
        "audits": audits,
    }


if __name__ == "__main__":
    result = run_all()
    print(json.dumps(result["audits"], indent=2, default=str))
    print("touch events:", len(result["events_full"]))
    print("armed excursions:", len(result["excursions_full"]))
    print(result["primary_classified"]["classification"].value_counts())
    print(result["session_mechanism"]["session_mechanism"].value_counts())
