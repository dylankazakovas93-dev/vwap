"""Post-event outcomes and barrier-first outcomes, anchored per event
class. See SPEC_SWEEP_FAILURE.md sections 14-16.
"""
import numpy as np
import pandas as pd

HORIZONS = (5, 10, 15, 30, 60)
BARRIERS = (0.25, 0.50, 1.00)

PRIMARY_CLASSES = ("FAILED_BREACH_1MIN", "FAILED_BREACH_2MIN", "FAILED_BREACH_3MIN")


def anchor_idx(ev: dict) -> int:
    cls = ev["event_class"]
    if cls in PRIMARY_CLASSES or cls == "DELAYED_FAILURE_CONTROL":
        return ev["confirmation_idx"]  # anchor = C; outcomes begin at C+1
    if cls == "SUCCESSFUL_BREACH_CONTROL":
        return ev["breach_idx"] + 2  # anchor = close of B+2; outcomes begin at B+3
    if cls == "TOUCH_WITHOUT_BREACH":
        return ev["event_idx"]  # anchor = T; outcomes begin at T+1
    return None  # INCOMPLETE_EPISODE / NEITHER_RESOLVED_WITHIN_10MIN: no legal outcome anchor


def add_outcomes(bars: pd.DataFrame, events: list) -> list:
    n = len(bars)
    high = bars["high"].to_numpy()
    low = bars["low"].to_numpy()
    close = bars["close"].to_numpy()
    atr_col = bars["atr20_event"].to_numpy()

    out = []
    for ev in events:
        A = anchor_idx(ev)
        row = dict(ev)
        if A is None:
            out.append(row)
            continue
        row["anchor_idx"] = A
        level = ev["level"]
        side = ev["side"]
        atr = atr_col[A]
        atr_valid = atr is not None and np.isfinite(atr) and atr > 0
        row["atr_valid"] = bool(atr_valid)
        row["atr_at_anchor"] = atr

        retouch = None
        max_bars_outside = 0
        cur_outside_run = 0
        for h in range(1, max(HORIZONS) + 1):
            idx = A + h
            if idx >= n:
                break
            if low[idx] <= level <= high[idx] and retouch is None:
                retouch = h
            if side == "upper":
                is_outside = close[idx] > level
            else:
                is_outside = close[idx] < level
            cur_outside_run = cur_outside_run + 1 if is_outside else 0
            max_bars_outside = max(max_bars_outside, cur_outside_run)
        row["retouch_h"] = retouch
        row["retouched"] = retouch is not None
        row["max_bars_outside"] = max_bars_outside

        for H in HORIZONS:
            complete = (A + H) < n
            row[f"horizon_{H}_complete"] = complete
            if not complete:
                for key in ("rotation_exc", "breakout_exc", "signed_close",
                            "rotation_exc_atr", "breakout_exc_atr", "signed_close_atr", "dominance"):
                    row[f"{key}_h{H}"] = np.nan
                row[f"close_through_again_h{H}"] = np.nan
                continue
            w_high = high[A + 1 : A + H + 1]
            w_low = low[A + 1 : A + H + 1]
            close_ah = close[A + H]
            if side == "upper":
                rot = max(0.0, level - float(w_low.min()))
                brk = max(0.0, float(w_high.max()) - level)
                signed = level - close_ah
                through_again = bool(close_ah > level)
            else:
                rot = max(0.0, float(w_high.max()) - level)
                brk = max(0.0, level - float(w_low.min()))
                signed = close_ah - level
                through_again = bool(close_ah < level)
            row[f"rotation_exc_h{H}"] = rot
            row[f"breakout_exc_h{H}"] = brk
            row[f"signed_close_h{H}"] = signed
            row[f"close_through_again_h{H}"] = through_again
            if atr_valid:
                rot_a, brk_a = rot / atr, brk / atr
                row[f"rotation_exc_atr_h{H}"] = rot_a
                row[f"breakout_exc_atr_h{H}"] = brk_a
                row[f"signed_close_atr_h{H}"] = signed / atr
                denom = rot_a + brk_a
                row[f"dominance_h{H}"] = (rot_a - brk_a) / denom if denom > 0 else np.nan
            else:
                row[f"rotation_exc_atr_h{H}"] = np.nan
                row[f"breakout_exc_atr_h{H}"] = np.nan
                row[f"signed_close_atr_h{H}"] = np.nan
                row[f"dominance_h{H}"] = np.nan
        out.append(row)
    return out


def add_barrier_outcomes(bars: pd.DataFrame, events_out: list) -> list:
    n = len(bars)
    high = bars["high"].to_numpy()
    low = bars["low"].to_numpy()

    out = []
    for ev in events_out:
        row = dict(ev)
        A = ev.get("anchor_idx")
        if A is None or not ev.get("atr_valid"):
            out.append(row)
            continue
        level = ev["level"]
        side = ev["side"]
        atr = ev["atr_at_anchor"]
        for b in BARRIERS:
            for H in HORIZONS:
                key = f"b{b}_h{H}"
                if (A + H) >= n:
                    row[f"{key}_outcome"] = "INVALID"
                    continue
                if side == "upper":
                    rot_barrier = level - b * atr
                    brk_barrier = level + b * atr
                else:
                    rot_barrier = level + b * atr
                    brk_barrier = level - b * atr
                rot_first = brk_first = None
                for h in range(1, H + 1):
                    idx = A + h
                    bar_hi, bar_lo = high[idx], low[idx]
                    if side == "upper":
                        r_hit = bar_lo <= rot_barrier
                        k_hit = bar_hi >= brk_barrier
                    else:
                        r_hit = bar_hi >= rot_barrier
                        k_hit = bar_lo <= brk_barrier
                    if r_hit and rot_first is None:
                        rot_first = h
                    if k_hit and brk_first is None:
                        brk_first = h
                    if rot_first is not None and brk_first is not None:
                        break
                if rot_first is None and brk_first is None:
                    outcome = "NEITHER"
                elif rot_first is not None and brk_first is None:
                    outcome = "ROTATION_FIRST"
                elif brk_first is not None and rot_first is None:
                    outcome = "BREAKOUT_FIRST"
                elif rot_first < brk_first:
                    outcome = "ROTATION_FIRST"
                elif brk_first < rot_first:
                    outcome = "BREAKOUT_FIRST"
                else:
                    outcome = "SAME_BAR_TIE"
                row[f"{key}_outcome"] = outcome
        out.append(row)
    return out
