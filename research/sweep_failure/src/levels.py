"""Causal level ledger: previous-RTH and overnight high/low.
See DATA_CONTRACT.md "Causal level ledger", SPEC_SWEEP_FAILURE.md sec 1.
"""
import numpy as np
import pandas as pd

from .data import RTH_START, RTH_END, is_overnight_minute

RTH_BAR_COUNT = RTH_END - RTH_START + 1  # 390
OVN_BAR_COUNT = 930


def build_level_ledger(df1m: pd.DataFrame, instrument: str):
    """Returns list of dicts, one per session_date, chronological order."""
    records = []
    last_valid_rth_high = None
    last_valid_rth_low = None

    for session_date, g in df1m.groupby("session_date", sort=True):
        g = g.sort_values("et_minute").reset_index(drop=True)
        et = g["et_minute"].to_numpy()

        rth_mask = (et >= RTH_START) & (et <= RTH_END)
        rth = g.loc[rth_mask]
        rth_valid = len(rth) == RTH_BAR_COUNT

        ovn_mask = np.array([is_overnight_minute(int(m)) for m in et])
        ovn = g.loc[ovn_mask]
        ovn_valid = len(ovn) == OVN_BAR_COUNT

        rec = {
            "instrument": instrument,
            "session_date": session_date,
            "rth_valid": rth_valid,
            "prev_rth_high": last_valid_rth_high,
            "prev_rth_low": last_valid_rth_low,
            "prev_rth_level_valid": last_valid_rth_high is not None,
            "overnight_valid": ovn_valid,
            "overnight_high": float(ovn["high"].max()) if ovn_valid else np.nan,
            "overnight_low": float(ovn["low"].min()) if ovn_valid else np.nan,
        }
        rec["_rth_bars"] = rth.reset_index(drop=True)
        records.append(rec)

        if rth_valid:
            last_valid_rth_high = float(rth["high"].max())
            last_valid_rth_low = float(rth["low"].min())

    return records
