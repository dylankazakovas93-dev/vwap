"""Module A: 10:00 open mechanism -- continuation/reversal outcomes and
barrier-first outcomes. See SPEC_TEN_AM_BLOCKS.md section 2.
"""
import numpy as np
import pandas as pd

HORIZONS = (1, 3, 5, 10, 15, 30, 60)
BARRIERS = (0.25, 0.50, 1.00)


def compute_module_a(rec: dict) -> dict:
    if not rec.get("candle_available") or rec.get("candle_state") is None:
        return None
    state = rec["candle_state"]
    rth = rec["_rth"]
    et_to_idx = {int(e): i for i, e in enumerate(rth["et_minute"].to_numpy())}
    T_et = 600
    if T_et not in et_to_idx:
        return None
    T = et_to_idx[T_et]
    o1000 = rec["o_1000"]
    range30 = rec["range_30"]

    out = {
        "instrument": rec["instrument"], "session_date": rec["session_date"],
        "year": pd.Timestamp(rec["session_date"]).year,
        "candle_state": state, "o_1000": o1000, "range_30": range30,
        "median_range_20": rec["median_range_20"],
        "pre10_stratum": rec["pre10_stratum"], "close_loc_stratum": rec["close_loc_stratum"],
        "dominance_stratum": rec["dominance_stratum"],
    }
    if state == "NEUTRAL_1000":
        out["directional"] = False
        return out
    out["directional"] = True
    cont_up = state == "BULLISH_1000"  # continuation direction = above O_1000

    high = rth["high"].to_numpy()
    low = rth["low"].to_numpy()
    close = rth["close"].to_numpy()
    n = len(rth)

    retouch = None
    for H in range(1, max(HORIZONS) + 1):
        et = T_et + H
        if et not in et_to_idx:
            break
        idx = et_to_idx[et]
        if idx != T + H:
            break
        if low[idx] <= o1000 <= high[idx] and retouch is None:
            retouch = et
    out["retouch_et"] = retouch
    out["retouched"] = retouch is not None

    for H in HORIZONS:
        window_ets = list(range(T_et + 1, T_et + H + 1))
        complete = all(e in et_to_idx and et_to_idx[e] == T + (e - T_et) for e in window_ets)
        out[f"horizon_{H}_complete"] = complete
        if not complete:
            for key in ("signed_close", "cont_exc", "rev_exc", "signed_close_atr", "signed_close_atr_med",
                        "cont_exc_atr", "rev_exc_atr", "dominance"):
                out[f"{key}_h{H}"] = np.nan
            continue
        idxs = [et_to_idx[e] for e in window_ets]
        w_high = high[idxs]
        w_low = low[idxs]
        close_th = close[et_to_idx[T_et + H]]
        if cont_up:
            cont_exc = max(0.0, float(w_high.max()) - o1000)
            rev_exc = max(0.0, o1000 - float(w_low.min()))
            signed = close_th - o1000
        else:
            cont_exc = max(0.0, o1000 - float(w_low.min()))
            rev_exc = max(0.0, float(w_high.max()) - o1000)
            signed = o1000 - close_th
        out[f"signed_close_h{H}"] = signed
        out[f"cont_exc_h{H}"] = cont_exc
        out[f"rev_exc_h{H}"] = rev_exc
        if range30 > 0:
            out[f"signed_close_atr_h{H}"] = signed / range30
            out[f"cont_exc_atr_h{H}"] = cont_exc / range30
            out[f"rev_exc_atr_h{H}"] = rev_exc / range30
            denom = cont_exc / range30 + rev_exc / range30
            out[f"dominance_h{H}"] = (cont_exc / range30 - rev_exc / range30) / denom if denom > 0 else np.nan
        if pd.notna(rec["median_range_20"]) and rec["median_range_20"] > 0:
            out[f"signed_close_atr_med_h{H}"] = signed / rec["median_range_20"]

    for b in BARRIERS:
        for H in HORIZONS:
            key = f"b{b}_h{H}"
            window_ets = list(range(T_et + 1, T_et + H + 1))
            complete = all(e in et_to_idx and et_to_idx[e] == T + (e - T_et) for e in window_ets)
            if not complete or range30 <= 0:
                out[f"{key}_outcome"] = "INVALID"
                continue
            if cont_up:
                cont_barrier = o1000 + b * range30
                rev_barrier = o1000 - b * range30
            else:
                cont_barrier = o1000 - b * range30
                rev_barrier = o1000 + b * range30
            cont_first = rev_first = None
            for h in range(1, H + 1):
                et = T_et + h
                idx = et_to_idx[et]
                bar_hi, bar_lo = high[idx], low[idx]
                if cont_up:
                    c_hit = bar_hi >= cont_barrier
                    r_hit = bar_lo <= rev_barrier
                else:
                    c_hit = bar_lo <= cont_barrier
                    r_hit = bar_hi >= rev_barrier
                if c_hit and cont_first is None:
                    cont_first = et
                if r_hit and rev_first is None:
                    rev_first = et
                if cont_first is not None and rev_first is not None:
                    break
            if cont_first is None and rev_first is None:
                outcome = "NEITHER"
            elif cont_first is not None and rev_first is None:
                outcome = "CONTINUATION_FIRST"
            elif rev_first is not None and cont_first is None:
                outcome = "REVERSAL_FIRST"
            elif cont_first < rev_first:
                outcome = "CONTINUATION_FIRST"
            elif rev_first < cont_first:
                outcome = "REVERSAL_FIRST"
            else:
                outcome = "SAME_BAR_TIE"
            out[f"{key}_outcome"] = outcome
    return out
