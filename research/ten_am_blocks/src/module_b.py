"""Module B: pre-10:00 rejection blocks -- interaction search, same-bar
morphology, post-interaction outcomes, barrier-first outcomes.
See SPEC_TEN_AM_BLOCKS.md sections 3-8.
"""
import numpy as np
import pandas as pd

HORIZONS = (1, 3, 5, 10, 15, 30, 60)
BARRIERS = (0.25, 0.50, 1.00)
POST10_START, POST10_END = 600, 659

ACTIVATION_WINDOWS = ("WITHIN_10AM_CANDLE", "WITHIN_5MIN", "WITHIN_10MIN", "WITHIN_15MIN", "WITHIN_30MIN", "WITHIN_60MIN")
_WINDOW_MINUTES = {"WITHIN_10AM_CANDLE": 1, "WITHIN_5MIN": 5, "WITHIN_10MIN": 10,
                    "WITHIN_15MIN": 15, "WITHIN_30MIN": 30, "WITHIN_60MIN": 60}


def _activation_flags(t_et: int) -> dict:
    elapsed = t_et - POST10_START + 1  # bar at 600 => elapsed=1 minute into window
    return {w: elapsed <= m for w, m in _WINDOW_MINUTES.items()}


def find_interaction(rec: dict, side: str):
    if not rec.get("post10_complete") or not rec[side]["valid"]:
        return None
    blk = rec[side]
    rth = rec["_rth"]
    et_to_idx = {int(e): i for i, e in enumerate(rth["et_minute"].to_numpy())}
    high = rth["high"].to_numpy()
    low = rth["low"].to_numpy()
    for et in range(POST10_START, POST10_END + 1):
        idx = et_to_idx[et]
        if low[idx] <= blk["high"] and high[idx] >= blk["low"]:
            return et
    return None


def compute_block_event(rec: dict, side: str) -> dict:
    if not rec[side]["valid"]:
        return None
    t_et = find_interaction(rec, side)
    if t_et is None:
        return None
    blk = rec[side]
    rth = rec["_rth"]
    et_to_idx = {int(e): i for i, e in enumerate(rth["et_minute"].to_numpy())}
    T = et_to_idx[t_et]
    high = rth["high"].to_numpy()
    low = rth["low"].to_numpy()
    close = rth["close"].to_numpy()
    open_ = rth["open"].to_numpy()
    range30 = rec["range_30"]
    med20 = rec["median_range_20"]

    close_t = close[T]
    if side == "upper":
        if close_t < blk["low"]:
            morph = "REVERSAL_PROXY"
        elif close_t > blk["high"]:
            morph = "BREAKTHROUGH_PROXY"
        else:
            morph = "INSIDE_UNRESOLVED"
    else:
        if close_t > blk["high"]:
            morph = "REVERSAL_PROXY"
        elif close_t < blk["low"]:
            morph = "BREAKTHROUGH_PROXY"
        else:
            morph = "INSIDE_UNRESOLVED"

    out = {
        "instrument": rec["instrument"], "session_date": rec["session_date"],
        "year": pd.Timestamp(rec["session_date"]).year,
        "side": side, "interaction_et": t_et, "block_low": blk["low"], "block_high": blk["high"],
        "block_width": blk["width"], "block_width_over_range30": blk["width_over_range30"],
        "freshness": blk["freshness"], "open_location": blk["open_location"],
        "momentum": blk["momentum"], "distance_o1000_to_block": blk["distance_o1000_to_block"],
        "range_30": range30, "median_range_20": med20,
        "pre10_stratum": rec["pre10_stratum"], "close_loc_stratum": rec["close_loc_stratum"],
        "dominance_stratum": rec["dominance_stratum"],
        "same_bar_morphology": morph,
        **{w: v for w, v in _activation_flags(t_et).items()},
    }

    retouch = None
    for H in range(1, max(HORIZONS) + 1):
        et = t_et + H
        if et not in et_to_idx:
            break
        idx = et_to_idx[et]
        if idx != T + H:
            break
        if low[idx] <= blk["high"] and high[idx] >= blk["low"] and retouch is None:
            retouch = et
    out["retouch_et"] = retouch
    out["retouched"] = retouch is not None

    for H in HORIZONS:
        window_ets = list(range(t_et + 1, t_et + H + 1))
        complete = all(e in et_to_idx and et_to_idx[e] == T + (e - t_et) for e in window_ets)
        out[f"horizon_{H}_complete"] = complete
        if not complete:
            for key in ("rev_exc", "brk_exc", "signed_close", "rev_exc_atr", "brk_exc_atr",
                        "signed_close_atr", "rev_exc_atr_med", "brk_exc_atr_med",
                        "signed_close_atr_med", "dominance"):
                out[f"{key}_h{H}"] = np.nan
            out[f"close_inside_zone_h{H}"] = np.nan
            continue
        idxs = [et_to_idx[e] for e in window_ets]
        w_high = high[idxs]
        w_low = low[idxs]
        close_th = close[et_to_idx[t_et + H]]
        inside = 0
        if side == "upper":
            rev = max(0.0, blk["low"] - float(w_low.min()))
            brk = max(0.0, float(w_high.max()) - blk["high"])
            if close_th < blk["low"]:
                signed = blk["low"] - close_th
            elif close_th > blk["high"]:
                signed = blk["high"] - close_th
            else:
                signed = 0.0
                inside = 1
        else:
            rev = max(0.0, float(w_high.max()) - blk["high"])
            brk = max(0.0, blk["low"] - float(w_low.min()))
            if close_th > blk["high"]:
                signed = close_th - blk["high"]
            elif close_th < blk["low"]:
                signed = close_th - blk["low"]
            else:
                signed = 0.0
                inside = 1
        out[f"rev_exc_h{H}"] = rev
        out[f"brk_exc_h{H}"] = brk
        out[f"signed_close_h{H}"] = signed
        out[f"close_inside_zone_h{H}"] = inside
        if range30 > 0:
            rev_a, brk_a = rev / range30, brk / range30
            out[f"rev_exc_atr_h{H}"] = rev_a
            out[f"brk_exc_atr_h{H}"] = brk_a
            out[f"signed_close_atr_h{H}"] = signed / range30
            denom = rev_a + brk_a
            out[f"dominance_h{H}"] = (rev_a - brk_a) / denom if denom > 0 else np.nan
        if pd.notna(med20) and med20 > 0:
            out[f"rev_exc_atr_med_h{H}"] = rev / med20
            out[f"brk_exc_atr_med_h{H}"] = brk / med20
            out[f"signed_close_atr_med_h{H}"] = signed / med20

    for b in BARRIERS:
        for H in HORIZONS:
            key = f"b{b}_h{H}"
            window_ets = list(range(t_et + 1, t_et + H + 1))
            complete = all(e in et_to_idx and et_to_idx[e] == T + (e - t_et) for e in window_ets)
            if not complete or range30 <= 0:
                out[f"{key}_outcome"] = "INVALID"
                continue
            if side == "upper":
                rev_barrier = blk["low"] - b * range30
                brk_barrier = blk["high"] + b * range30
            else:
                rev_barrier = blk["high"] + b * range30
                brk_barrier = blk["low"] - b * range30
            rev_first = brk_first = None
            for h in range(1, H + 1):
                et = t_et + h
                idx = et_to_idx[et]
                bar_hi, bar_lo = high[idx], low[idx]
                if side == "upper":
                    r_hit = bar_lo <= rev_barrier
                    b_hit = bar_hi >= brk_barrier
                else:
                    r_hit = bar_hi >= rev_barrier
                    b_hit = bar_lo <= brk_barrier
                if r_hit and rev_first is None:
                    rev_first = et
                if b_hit and brk_first is None:
                    brk_first = et
                if rev_first is not None and brk_first is not None:
                    break
            if rev_first is None and brk_first is None:
                outcome = "NEITHER"
            elif rev_first is not None and brk_first is None:
                outcome = "REVERSAL_FIRST"
            elif brk_first is not None and rev_first is None:
                outcome = "BREAKTHROUGH_FIRST"
            elif rev_first < brk_first:
                outcome = "REVERSAL_FIRST"
            elif brk_first < rev_first:
                outcome = "BREAKTHROUGH_FIRST"
            else:
                outcome = "SAME_BAR_TIE"
            out[f"{key}_outcome"] = outcome
    return out
