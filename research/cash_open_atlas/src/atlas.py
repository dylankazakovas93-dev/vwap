"""Cash-open target atlas engine — SPEC_ATLAS.md.

Builds one row per (instrument, session_date) with R/U/D/Q/E at horizons
h in {1,3,5,10,15,30} (primary) and h=60 (secondary), using tau = h-1
(SPEC_ATLAS.md Sec. 2). Self-contained: no imports from other generations.
"""
import numpy as np
import pandas as pd

PRIMARY_HORIZONS = (1, 3, 5, 10, 15, 30)
SECONDARY_HORIZON = 60
ANCHOR_MINUTE = 570  # 09:30 ET


def build_dense_bars(df: pd.DataFrame, tau_max: int = 59):
    """df: one instrument's base bars. Returns dict session_date -> dict of
    dense open/high/low/close arrays indexed by tau=0..tau_max (NaN where a
    minute is missing)."""
    sub = df[(df["et_minute"] >= ANCHOR_MINUTE) & (df["et_minute"] <= ANCHOR_MINUTE + tau_max)].copy()
    sub["tau"] = sub["et_minute"] - ANCHOR_MINUTE
    n = tau_max + 1
    out = {}
    for sd, g in sub.groupby("session_date", sort=True):
        arrs = {k: np.full(n, np.nan) for k in ("open", "high", "low", "close")}
        idx = g["tau"].to_numpy(int)
        for k in arrs:
            arrs[k][idx] = g[k].to_numpy(float)
        out[sd] = arrs
    return out


def _targets_for_window(arrs, O, n_bars):
    """R/U/D/Q/E dict for the window tau=0..n_bars-1 (the first n_bars bars),
    Close = close(tau=n_bars-1). Returns None if any bar in the window is
    missing (NaN) -- i.e. window is not fully complete."""
    hi = arrs["high"][:n_bars]
    lo = arrs["low"][:n_bars]
    cl = arrs["close"][:n_bars]
    if np.any(np.isnan(hi)) or np.any(np.isnan(lo)) or np.any(np.isnan(cl)):
        return None
    close_h = cl[n_bars - 1]
    U = float(np.max(hi) - O)
    D = float(O - np.min(lo))
    R = float(close_h - O)
    denom = U + D
    Q = float((U - D) / denom) if denom > 0 else np.nan
    E = float(R / denom) if denom > 0 else np.nan
    return {"R": R, "U": U, "D": D, "Q": Q, "E": E}


def build_session_ledger(bar_frames: dict, instrument: str) -> pd.DataFrame:
    rows = []
    missing_log = []
    for sd, arrs in bar_frames.items():
        O = arrs["open"][0]
        if not np.isfinite(O):
            missing_log.append({"instrument": instrument, "session_date": sd,
                                "reason": "no_0930_bar"})
            continue
        primary_ok = not (np.any(np.isnan(arrs["high"][:30])) or
                          np.any(np.isnan(arrs["low"][:30])) or
                          np.any(np.isnan(arrs["close"][:30])))
        if not primary_ok:
            missing_log.append({"instrument": instrument, "session_date": sd,
                                "reason": "incomplete_0930_0959_window"})
            continue
        row = {"instrument": instrument, "session_date": sd, "O": float(O),
              "year": pd.Timestamp(sd).year, "primary_valid": True}
        for h in PRIMARY_HORIZONS:
            t = _targets_for_window(arrs, O, n_bars=h)
            for k, v in t.items():
                row[f"{k}_{h}"] = v
        secondary_ok = len(arrs["high"]) >= SECONDARY_HORIZON and not (
            np.any(np.isnan(arrs["high"][:60])) or np.any(np.isnan(arrs["low"][:60])) or
            np.any(np.isnan(arrs["close"][:60])))
        row["secondary_valid"] = bool(secondary_ok)
        if secondary_ok:
            t60 = _targets_for_window(arrs, O, n_bars=SECONDARY_HORIZON)
            for k, v in t60.items():
                row[f"{k}_60"] = v
        else:
            for k in ("R", "U", "D", "Q", "E"):
                row[f"{k}_60"] = np.nan
            missing_log.append({"instrument": instrument, "session_date": sd,
                                "reason": "incomplete_0930_1029_window_secondary_only"})
        rows.append(row)

    led = pd.DataFrame(rows)
    for h in list(PRIMARY_HORIZONS) + [SECONDARY_HORIZON]:
        r = led[f"R_{h}"]
        led[f"closing_direction_{h}"] = np.select(
            [r.isna(), r > 0, r < 0], ["NA", "UP", "DOWN"], default="NEUTRAL")
        q = led[f"Q_{h}"]
        led[f"dominant_side_{h}"] = np.select(
            [q.isna() & r.notna(), q > 0, q < 0], ["NEUTRAL", "UPPER", "LOWER"], default="NEUTRAL")
        led.loc[led[f"R_{h}"].isna(), f"dominant_side_{h}"] = "NA"
    r1 = led["R_1"]
    for h in PRIMARY_HORIZONS[1:] + (SECONDARY_HORIZON,):
        rh = led[f"R_{h}"]
        agree = np.select(
            [rh.isna(), (r1 == 0) | (rh == 0), np.sign(r1) == np.sign(rh)],
            ["NA", "NEUTRAL", "AGREE"], default="DISAGREE")
        led[f"initial_final_agree_{h}"] = agree
    return led, pd.DataFrame(missing_log)
