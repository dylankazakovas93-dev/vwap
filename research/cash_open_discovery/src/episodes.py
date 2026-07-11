"""Episode/reclaim state machine — SPEC_DISCOVERY.md Sec. 4-6.

One primary episode per (instrument, session, A). Outer excursion detected
via bar H/L (touch); reclaim detected via bar CLOSE, starting strictly after
the outer bar. Checkpoint statuses at H in {5,10,15} minutes past the outer
bar support the matched held/reclaimed comparison (Sec. 6).
"""
import numpy as np
import pandas as pd

OUTER_WINDOW = 60      # tau_outer in [0, 60]
RECLAIM_WINDOW = 60    # bars after outer bar
CHECKPOINTS = (5, 10, 15)
A_DOMAIN = (0.5, 1.0, 1.5, 2.0)


def _find_outer(bars, S_row, A):
    hi, lo = bars["high"], bars["low"]
    for tau in range(0, OUTER_WINDOW + 1):
        s = S_row[tau] if tau < len(S_row) else np.nan
        if not np.isfinite(s) or s <= 0:
            continue
        O = bars["open"][0]
        up_thr = O + A * s
        dn_thr = O - A * s
        up_hit = np.isfinite(hi[tau]) and hi[tau] >= up_thr
        dn_hit = np.isfinite(lo[tau]) and lo[tau] <= dn_thr
        if up_hit and dn_hit:
            return {"tau": tau, "direction": "AMBIGUOUS_DIRECTION", "S": s,
                    "O": O, "outer_price": np.nan, "threshold": np.nan}
        if up_hit:
            return {"tau": tau, "direction": "upper", "S": s, "O": O,
                    "outer_price": hi[tau], "threshold": up_thr}
        if dn_hit:
            return {"tau": tau, "direction": "lower", "S": s, "O": O,
                    "outer_price": lo[tau], "threshold": dn_thr}
    return None


def _find_reclaim(bars, tau_outer, direction, O, S, B):
    cl = bars["close"]
    lvl = (O - B * S) if direction == "lower" else (O + B * S)
    j_end = min(len(cl) - 1, tau_outer + RECLAIM_WINDOW)
    for tau in range(tau_outer + 1, j_end + 1):
        c = cl[tau]
        if not np.isfinite(c):
            continue
        if direction == "lower" and c >= lvl:
            return tau
        if direction == "upper" and c <= lvl:
            return tau
    return None


def build_episode_ledger(bar_frames: dict, S: pd.DataFrame, instrument: str,
                         A_list=A_DOMAIN) -> pd.DataFrame:
    rows = []
    for sd, bars in bar_frames.items():
        if sd not in S.index:
            continue
        S_row = S.loc[sd].to_numpy()
        if np.isnan(bars["open"][0]):
            continue
        for A in A_list:
            outer = _find_outer(bars, S_row, A)
            if outer is None:
                continue
            row = {"instrument": instrument, "session_date": sd, "A": A,
                   "O": outer["O"], "outer_direction": outer["direction"],
                   "outer_threshold_price": outer["threshold"],
                   "outer_price": outer["outer_price"],
                   "minutes_to_outer": outer["tau"], "S_tau_outer": outer["S"]}
            if outer["direction"] == "AMBIGUOUS_DIRECTION":
                rows.append(row)
                continue
            direction = outer["direction"]
            tau_outer = outer["tau"]
            t50 = _find_reclaim(bars, tau_outer, direction, outer["O"], outer["S"], 0.5 * A)
            tfull = _find_reclaim(bars, tau_outer, direction, outer["O"], outer["S"], 0.0)
            row["reclaim_50_tau"] = t50
            row["reclaim_full_tau"] = tfull
            row["minutes_to_reclaim_50"] = (t50 - tau_outer) if t50 is not None else np.nan
            row["minutes_to_reclaim_full"] = (tfull - tau_outer) if tfull is not None else np.nan
            row["reclaim_type"] = "FULL" if tfull is not None else ("HALF" if t50 is not None else "NONE")
            # max excursion before first reclaim (or within window if none)
            end = (t50 if t50 is not None else min(len(bars["close"]) - 1, tau_outer + RECLAIM_WINDOW))
            seg_hi = bars["high"][tau_outer:end + 1]
            seg_lo = bars["low"][tau_outer:end + 1]
            row["max_excursion_before_reclaim"] = (
                float(np.nanmax(seg_hi) - outer["O"]) if direction == "upper"
                else float(outer["O"] - np.nanmin(seg_lo)))
            for reclaim_name, t in (("reclaim_50", t50), ("reclaim_full", tfull)):
                if t is not None:
                    row[f"{reclaim_name}_ts"] = bars["ts_event"][t]
                    # decision = reclaim bar close = next bar open (contiguous)
                    dec_tau = t + 1
                    row[f"{reclaim_name}_decision_tau"] = dec_tau
                    row[f"{reclaim_name}_legal_outcome_start_tau"] = dec_tau
                else:
                    row[f"{reclaim_name}_ts"] = pd.NaT
                    row[f"{reclaim_name}_decision_tau"] = np.nan
                    row[f"{reclaim_name}_legal_outcome_start_tau"] = np.nan
            # checkpoint statuses (Sec. 6)
            for H in CHECKPOINTS:
                cp_tau = tau_outer + H
                if t50 is not None and t50 <= cp_tau:
                    status = "RECLAIMED_FULL" if (tfull is not None and tfull <= cp_tau) else "RECLAIMED_50"
                    origin_tau = (tfull if status == "RECLAIMED_FULL" else t50) + 1
                else:
                    status = "HELD"
                    origin_tau = min(cp_tau, len(bars["close"]) - 1) + 1
                row[f"cp{H}_status"] = status
                row[f"cp{H}_origin_tau"] = origin_tau
            rows.append(row)
    return pd.DataFrame(rows)
