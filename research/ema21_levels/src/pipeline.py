"""End-to-end pipeline: 1m parquet -> 5m bars -> EMA/ATR -> events -> outcomes
-> barriers -> summary cells -> primary BH -> year stability -> classification.

Usage: python -m src.pipeline   (run from research/ema21_levels/)
"""
import json
import os

import pandas as pd

from . import five_min_bars as fmb
from . import ema
from . import events as ev
from . import outcomes as oc
from . import summary as sm
from . import classification as cl

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "outputs")
REPORTS = os.path.join(HERE, "..", "reports")
TABLES = os.path.join(REPORTS, "tables")

INSTRUMENTS = ("ES", "NQ")
SESSION_DEFS = ("RTH_EMA", "FULL_SESSION_EMA")


def build_instrument(root: str):
    df1m = fmb.filter_development(fmb.load_1m(root))
    rth_bars, n_incomplete_rth = fmb.build_rth_5m(df1m)
    full_bars, n_incomplete_full = fmb.build_full_5m(df1m)

    rth_bars = ema.add_atr(ema.add_emas_and_levels(rth_bars))
    full_bars = ema.add_atr(ema.add_emas_and_levels(full_bars))

    audit = {
        "instrument": root,
        "n_1m_rows_dev": int(len(df1m)),
        "n_rth_5m_bars": int(len(rth_bars)),
        "n_rth_5m_incomplete_dropped": int(n_incomplete_rth),
        "n_full_5m_bars": int(len(full_bars)),
        "n_full_5m_incomplete_dropped": int(n_incomplete_full),
    }
    return {"RTH_EMA": rth_bars, "FULL_SESSION_EMA": full_bars}, audit


def run_all():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)

    all_events = []
    all_excursions = []
    all_barriers = []
    audits = []

    for root in INSTRUMENTS:
        bars_by_def, audit = build_instrument(root)
        audits.append(audit)
        for session_def, bars in bars_by_def.items():
            bars.to_parquet(os.path.join(OUT, f"{root.lower()}_5m_{session_def.lower()}.parquet"))
            for span in ema.SPANS:
                exc, touches = ev.detect(bars, span, root, session_def)
                if not exc.empty:
                    exc["stratum"] = sm._excursion_stratum(bars, exc)
                    all_excursions.append(exc)
                if touches.empty:
                    continue
                outc = oc.add_outcomes(bars, touches)
                barr = oc.add_barrier_outcomes(bars, outc)
                merged = outc.merge(
                    barr.drop(columns=["instrument", "ema_session_definition", "ema_span"]),
                    on="touch_idx",
                    how="left",
                )
                all_events.append(merged)

    events_full = pd.concat(all_events, ignore_index=True) if all_events else pd.DataFrame()
    excursions_full = pd.concat(all_excursions, ignore_index=True) if all_excursions else pd.DataFrame()

    events_full.drop(columns=["arming_bars"]).to_csv(
        os.path.join(OUT, "all_touch_events_with_outcomes.csv"), index=False
    )
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

    spec = cl.classify_specificity(classified)
    spec.to_csv(os.path.join(TABLES, "ema_specificity_table.csv"), index=False)

    tod = cells.loc[cells["horizon_bars"] == cl.PRIMARY_HORIZON]
    tod.to_csv(os.path.join(TABLES, "time_of_day_table.csv"), index=False)

    null_inv = classified.loc[classified["classification"] == "MIXED_OR_NULL"]
    null_inv.to_csv(os.path.join(TABLES, "null_inventory.csv"), index=False)
    underpowered_inv = classified.loc[classified["classification"] == "UNDERPOWERED"]
    underpowered_inv.to_csv(os.path.join(TABLES, "underpowered_inventory.csv"), index=False)

    return {
        "events_full": events_full,
        "excursions_full": excursions_full,
        "cells": cells,
        "primary_classified": classified,
        "specificity": spec,
        "year_stability": yr,
        "audits": audits,
    }


if __name__ == "__main__":
    result = run_all()
    print(json.dumps(result["audits"], indent=2, default=str))
    print("touch events:", len(result["events_full"]))
    print("armed excursions:", len(result["excursions_full"]))
    print(result["primary_classified"]["classification"].value_counts())
    print(result["specificity"]["specificity"].value_counts())
