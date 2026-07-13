"""Causal residual-path outcome classification (closure/expansion),
horizons 5/10/15/30 minutes. See SPEC_UNSUPPORTED_MOVE.md section 7.
"""
import numpy as np
import pandas as pd

HORIZONS = (5, 10, 15, 30)
PRIMARY_HORIZON = 15


def build_leg_bar_index(leg_bars: pd.DataFrame) -> dict:
    idx = {}
    for leg_id, g in leg_bars.groupby("session_leg_id", sort=False):
        idx[leg_id] = g.set_index("local_rank")[["close_es", "close_nq"]]
    return idx


def _residual_path(bars: pd.DataFrame, t: int, alpha: float, beta: float, h_max: int):
    base = t - 5
    if base not in bars.index:
        return None
    es0, nq0 = bars.loc[base, "close_es"], bars.loc[base, "close_nq"]
    path = {}
    for h in range(0, h_max + 1):
        idx = t + h
        if idx not in bars.index:
            return path, h - 1  # incomplete beyond this point
        es_cum = bars.loc[idx, "close_es"] / es0 - 1
        nq_cum = bars.loc[idx, "close_nq"] / nq0 - 1
        path[h] = nq_cum - alpha - beta * es_cum
    return path, h_max


def classify_outcome(events: pd.DataFrame, leg_bar_index: dict) -> pd.DataFrame:
    rows = []
    for ev in events.to_dict("records"):
        leg_id = ev["session_leg_id"]
        t = int(ev["local_rank"])
        alpha, beta = ev["alpha"], ev["beta"]
        bars = leg_bar_index.get(leg_id)
        row = dict(ev)
        if bars is None:
            rows.append(row)
            continue
        result = _residual_path(bars, t, alpha, beta, PRIMARY_HORIZON)
        if result is None:
            for H in HORIZONS:
                row[f"horizon_{H}_complete"] = False
                row[f"outcome_h{H}"] = "INCOMPLETE_HORIZON"
            rows.append(row)
            continue
        path, max_h_available = result
        if 0 not in path:
            for H in HORIZONS:
                row[f"horizon_{H}_complete"] = False
                row[f"outcome_h{H}"] = "INCOMPLETE_HORIZON"
            rows.append(row)
            continue
        r0 = path[0]
        row["r0"] = r0
        if r0 == 0 or pd.isna(r0):
            rows.append(row)
            continue
        closure_barrier = 0.50 * r0
        expansion_barrier = 1.50 * r0
        row["closure_barrier"] = closure_barrier
        row["expansion_barrier"] = expansion_barrier

        for H in HORIZONS:
            complete = max_h_available >= H
            row[f"horizon_{H}_complete"] = complete
            if not complete:
                row[f"outcome_h{H}"] = "INCOMPLETE_HORIZON"
                continue
            outcome = "NEITHER_WITHIN_HORIZON"
            first_h = None
            for h in range(1, H + 1):
                rp = path[h]
                if r0 > 0:
                    c_hit = rp <= closure_barrier
                    e_hit = rp >= expansion_barrier
                else:
                    c_hit = rp >= closure_barrier
                    e_hit = rp <= expansion_barrier
                if c_hit and e_hit:
                    outcome = "SAME_BAR_AMBIGUOUS"
                    first_h = h
                    break
                if c_hit:
                    outcome = "RESIDUAL_CLOSURE_FIRST"
                    first_h = h
                    break
                if e_hit:
                    outcome = "RESIDUAL_EXPANSION_FIRST"
                    first_h = h
                    break
            row[f"outcome_h{H}"] = outcome
            row[f"resolution_bar_h{H}"] = first_h
            if H == PRIMARY_HORIZON:
                row["residual_path"] = path
        rows.append(row)
    return pd.DataFrame(rows)
