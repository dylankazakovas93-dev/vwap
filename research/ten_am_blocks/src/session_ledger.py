"""Per-session ledger: pre-10:00 window, RANGE_30, MEDIAN_RANGE_20, block
definitions, freshness, 10:00 open location, context variables and
strata. See SPEC_TEN_AM_BLOCKS.md sections 1, 3, 4, 9.
"""
import numpy as np
import pandas as pd

from .data import PRE10_START, PRE10_END, POST10_START, POST10_END, RTH_START, RTH_END

TICK = 0.25


def _wick_body_ratios(bar, wick_side):
    rng = bar["high"] - bar["low"]
    if rng <= 0:
        return np.nan, np.nan
    body = abs(bar["close"] - bar["open"])
    if wick_side == "upper":
        wick = bar["high"] - max(bar["open"], bar["close"])
    else:
        wick = min(bar["open"], bar["close"]) - bar["low"]
    return wick / rng, body / rng


def build_session_record(rth: pd.DataFrame, instrument: str, session_date) -> dict:
    """rth: this session's 1-minute bars, et_minute 570-959, sorted, reset_index."""
    et_to_idx = {int(e): i for i, e in enumerate(rth["et_minute"].to_numpy())}
    rec = {"instrument": instrument, "session_date": session_date, "valid": False, "_rth": rth}

    pre10_ets = list(range(PRE10_START, PRE10_END + 1))
    if not all(e in et_to_idx for e in pre10_ets):
        rec["reason"] = "PRE10_INCOMPLETE"
        return rec
    pre10 = rth.iloc[[et_to_idx[e] for e in pre10_ets]].reset_index(drop=True)

    open30 = float(pre10["open"].iloc[0])
    close30 = float(pre10["close"].iloc[29])
    high30 = float(pre10["high"].max())
    low30 = float(pre10["low"].min())
    range30 = high30 - low30
    if range30 <= 0:
        rec["reason"] = "RANGE30_NONPOSITIVE"
        return rec

    rec["valid"] = True
    rec["reason"] = "OK"
    rec["median_range_20"] = np.nan  # overwritten causally by build_ledger()
    rec["open_0930"] = open30
    rec["close_0959"] = close30
    rec["high_30"] = high30
    rec["low_30"] = low30
    rec["range_30"] = range30

    u30 = high30 - open30
    d30 = open30 - low30
    r30 = close30 - open30
    q30 = (u30 - d30) / range30
    close_loc = (close30 - low30) / range30
    rec["u_30"], rec["d_30"], rec["r_30"], rec["q_30"] = u30, d30, r30, q30
    rec["close_location_30"] = close_loc

    rec["pre10_stratum"] = "PRE10_UP" if r30 > 0 else ("PRE10_DOWN" if r30 < 0 else "PRE10_FLAT")
    if close_loc <= 0.25:
        rec["close_loc_stratum"] = "CLOSE_LOW"
    elif close_loc >= 0.75:
        rec["close_loc_stratum"] = "CLOSE_HIGH"
    else:
        rec["close_loc_stratum"] = "CLOSE_MIDDLE"
    if q30 >= 1 / 3:
        rec["dominance_stratum"] = "UP_DOMINANT"
    elif q30 <= -1 / 3:
        rec["dominance_stratum"] = "DOWN_DOMINANT"
    else:
        rec["dominance_stratum"] = "BALANCED"

    # H_BAR / L_BAR: last (most recent) bar matching the 30-minute extreme
    h_idx = int(np.max(np.where(np.isclose(pre10["high"].to_numpy(), high30))[0]))
    l_idx = int(np.max(np.where(np.isclose(pre10["low"].to_numpy(), low30))[0]))
    hbar, lbar = pre10.iloc[h_idx], pre10.iloc[l_idx]

    upper_low = max(hbar["open"], hbar["close"])
    upper_high = hbar["high"]
    lower_low = lbar["low"]
    lower_high = min(lbar["open"], lbar["close"])
    upper_width = upper_high - upper_low
    lower_width = lower_high - lower_low
    upper_valid = upper_width >= TICK
    lower_valid = lower_width >= TICK

    upper_wick_ratio, upper_body_ratio = _wick_body_ratios(hbar, "upper")
    lower_wick_ratio, lower_body_ratio = _wick_body_ratios(lbar, "lower")

    later_upper = pre10.iloc[h_idx + 1 :]
    upper_pretouched = bool(
        ((later_upper["low"] <= upper_high) & (later_upper["high"] >= upper_low)).any()
    ) if len(later_upper) else False
    later_lower = pre10.iloc[l_idx + 1 :]
    lower_pretouched = bool(
        ((later_lower["low"] <= lower_high) & (later_lower["high"] >= lower_low)).any()
    ) if len(later_lower) else False

    rec["upper"] = {
        "valid": bool(upper_valid), "low": float(upper_low), "high": float(upper_high),
        "width": float(upper_width), "width_over_range30": float(upper_width / range30),
        "forming_bar_et_minute": int(hbar["et_minute"]), "wick_ratio": upper_wick_ratio,
        "body_ratio": upper_body_ratio,
        "freshness": "PRETOUCHED" if upper_pretouched else "PRISTINE",
    }
    rec["lower"] = {
        "valid": bool(lower_valid), "low": float(lower_low), "high": float(lower_high),
        "width": float(lower_width), "width_over_range30": float(lower_width / range30),
        "forming_bar_et_minute": int(lbar["et_minute"]), "wick_ratio": lower_wick_ratio,
        "body_ratio": lower_body_ratio,
        "freshness": "PRETOUCHED" if lower_pretouched else "PRISTINE",
    }

    post10_ets = list(range(POST10_START, POST10_END + 1))
    rec["post10_complete"] = all(e in et_to_idx for e in post10_ets)
    rec["candle_available"] = POST10_START in et_to_idx
    if rec["candle_available"]:
        bar600 = rth.iloc[et_to_idx[POST10_START]]
        o1000 = float(bar600["open"])
        c1000 = float(bar600["close"])
        rec["o_1000"] = o1000
        rec["close_1000"] = c1000
        rec["bar600_idx"] = et_to_idx[POST10_START]
        rec["bar600_high"] = float(bar600["high"])
        rec["bar600_low"] = float(bar600["low"])
        if c1000 >= o1000 + TICK:
            rec["candle_state"] = "BULLISH_1000"
        elif c1000 <= o1000 - TICK:
            rec["candle_state"] = "BEARISH_1000"
        else:
            rec["candle_state"] = "NEUTRAL_1000"

        for side, blk in (("upper", rec["upper"]), ("lower", rec["lower"])):
            if not blk["valid"]:
                blk["open_location"] = None
                blk["distance_o1000_to_block"] = np.nan
                continue
            if side == "upper":
                if o1000 < blk["low"]:
                    loc = "APPROACH_SIDE"
                elif o1000 > blk["high"]:
                    loc = "ALREADY_BEYOND"
                else:
                    loc = "OPEN_INSIDE"
                dist = blk["low"] - o1000
            else:
                if o1000 > blk["high"]:
                    loc = "APPROACH_SIDE"
                elif o1000 < blk["low"]:
                    loc = "ALREADY_BEYOND"
                else:
                    loc = "OPEN_INSIDE"
                dist = o1000 - blk["high"]
            blk["open_location"] = loc
            blk["distance_o1000_to_block"] = float(dist)
    else:
        rec["candle_state"] = None

    for side, blk in (("upper", rec["upper"]), ("lower", rec["lower"])):
        if rec["candle_available"] and blk["valid"]:
            up = rec["pre10_stratum"] == "PRE10_UP"
            down = rec["pre10_stratum"] == "PRE10_DOWN"
            chigh = rec["close_loc_stratum"] == "CLOSE_HIGH"
            clow = rec["close_loc_stratum"] == "CLOSE_LOW"
            updom = rec["dominance_stratum"] == "UP_DOMINANT"
            downdom = rec["dominance_stratum"] == "DOWN_DOMINANT"
            if side == "upper":
                blk["momentum"] = "MOMENTUM_INTO_BLOCK" if (up and chigh and updom) else "NOT_MOMENTUM_INTO_BLOCK"
            else:
                blk["momentum"] = "MOMENTUM_INTO_BLOCK" if (down and clow and downdom) else "NOT_MOMENTUM_INTO_BLOCK"
        else:
            blk["momentum"] = None

    return rec


def build_ledger(df1m_dev: pd.DataFrame, instrument: str):
    records = []
    for session_date, g in df1m_dev.groupby("session_date", sort=True):
        g = g.sort_values("et_minute").reset_index(drop=True)
        rth_mask = (g["et_minute"] >= RTH_START) & (g["et_minute"] <= RTH_END)
        rth = g.loc[rth_mask].reset_index(drop=True)
        rec = build_session_record(rth, instrument, session_date)
        rec["_rth"] = rth
        records.append(rec)

    # causal MEDIAN_RANGE_20 over the chronologically prior 20 VALID sessions
    trailing = []
    for rec in records:
        if len(trailing) >= 20:
            rec["median_range_20"] = float(np.median(trailing[-20:]))
        else:
            rec["median_range_20"] = np.nan
        if rec["valid"]:
            trailing.append(rec["range_30"])
    return records
