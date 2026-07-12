"""Post-touch excursion outcomes and barrier-first outcomes.

See SPEC_EMA21_LEVELS.md sections 5, 7, 8. Measurement starts strictly at
T+1; bar T's own H/L/C never enter these computations.
"""
import numpy as np
import pandas as pd

from .events import HORIZONS, MAX_HORIZON

BARRIERS = (0.5, 1.0)


def add_outcomes(bars: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events
    low = bars["low"].to_numpy()
    high = bars["high"].to_numpy()
    close = bars["close"].to_numpy()
    atr_event_col = bars["atr_event"].to_numpy()
    n = len(bars)

    rows = []
    for ev in events.itertuples():
        T = ev.touch_idx
        side = ev.approach_side
        level_t = ev.level_t
        atr = atr_event_col[T]
        row = dict(ev._asdict())
        row.pop("Index", None)
        row["atr_event"] = atr
        atr_valid = np.isfinite(atr) and atr > 0
        row["atr_valid"] = bool(atr_valid)

        retouch_bar = None
        for H in range(1, MAX_HORIZON + 1):
            idx = T + H
            if idx >= n:
                break
            if low[idx] <= level_t <= high[idx] and retouch_bar is None:
                retouch_bar = idx

        for H in HORIZONS:
            complete = (T + H) < n
            row[f"horizon_{H}_complete"] = complete
            if not complete:
                for key in (
                    "rejection_exc",
                    "breakthrough_exc",
                    "signed_close",
                    "rejection_exc_atr",
                    "breakthrough_exc_atr",
                    "signed_close_atr",
                    "dominance",
                ):
                    row[f"{key}_h{H}"] = np.nan
                continue
            window_high = high[T + 1 : T + H + 1]
            window_low = low[T + 1 : T + H + 1]
            close_th = close[T + H]
            if side == "FROM_ABOVE":
                rej = max(0.0, float(window_high.max()) - level_t)
                brk = max(0.0, level_t - float(window_low.min()))
                signed = close_th - level_t
            else:
                rej = max(0.0, level_t - float(window_low.min()))
                brk = max(0.0, float(window_high.max()) - level_t)
                signed = level_t - close_th
            row[f"rejection_exc_h{H}"] = rej
            row[f"breakthrough_exc_h{H}"] = brk
            row[f"signed_close_h{H}"] = signed
            if atr_valid:
                rej_a = rej / atr
                brk_a = brk / atr
                row[f"rejection_exc_atr_h{H}"] = rej_a
                row[f"breakthrough_exc_atr_h{H}"] = brk_a
                row[f"signed_close_atr_h{H}"] = signed / atr
                denom = rej_a + brk_a
                row[f"dominance_h{H}"] = (rej_a - brk_a) / denom if denom > 0 else np.nan
            else:
                row[f"rejection_exc_atr_h{H}"] = np.nan
                row[f"breakthrough_exc_atr_h{H}"] = np.nan
                row[f"signed_close_atr_h{H}"] = np.nan
                row[f"dominance_h{H}"] = np.nan

        row["retouch_bar_idx"] = retouch_bar
        row["retouched"] = retouch_bar is not None
        rows.append(row)
    return pd.DataFrame(rows)


def add_barrier_outcomes(bars: pd.DataFrame, events_out: pd.DataFrame) -> pd.DataFrame:
    if events_out.empty:
        return events_out
    low = bars["low"].to_numpy()
    high = bars["high"].to_numpy()
    n = len(bars)
    rows = []
    for ev in events_out.itertuples():
        T = ev.touch_idx
        side = ev.approach_side
        level_t = ev.level_t
        atr = ev.atr_event
        row = {"touch_idx": T, "instrument": ev.instrument,
               "ema_session_definition": ev.ema_session_definition,
               "ema_span": ev.ema_span}
        atr_valid = np.isfinite(atr) and atr > 0
        for b in BARRIERS:
            for H in HORIZONS:
                key = f"b{b}_h{H}"
                if not atr_valid or (T + H) >= n:
                    row[f"{key}_outcome"] = "INVALID"
                    row[f"{key}_reject_reached"] = None
                    row[f"{key}_break_reached"] = None
                    continue
                if side == "FROM_ABOVE":
                    rej_barrier = level_t + b * atr
                    brk_barrier = level_t - b * atr
                else:
                    rej_barrier = level_t - b * atr
                    brk_barrier = level_t + b * atr
                rej_first_bar = None
                brk_first_bar = None
                for h in range(1, H + 1):
                    idx = T + h
                    bar_hi = high[idx]
                    bar_lo = low[idx]
                    if side == "FROM_ABOVE":
                        rej_hit = bar_hi >= rej_barrier
                        brk_hit = bar_lo <= brk_barrier
                    else:
                        rej_hit = bar_lo <= rej_barrier
                        brk_hit = bar_hi >= brk_barrier
                    if rej_hit and rej_first_bar is None:
                        rej_first_bar = idx
                    if brk_hit and brk_first_bar is None:
                        brk_first_bar = idx
                    if rej_first_bar is not None and brk_first_bar is not None:
                        break
                if rej_first_bar is None and brk_first_bar is None:
                    outcome = "NEITHER"
                elif rej_first_bar is not None and brk_first_bar is None:
                    outcome = "REJECTION_FIRST"
                elif brk_first_bar is not None and rej_first_bar is None:
                    outcome = "BREAKTHROUGH_FIRST"
                elif rej_first_bar < brk_first_bar:
                    outcome = "REJECTION_FIRST"
                elif brk_first_bar < rej_first_bar:
                    outcome = "BREAKTHROUGH_FIRST"
                else:
                    outcome = "SAME_BAR_TIE"
                row[f"{key}_outcome"] = outcome
                row[f"{key}_reject_reached"] = rej_first_bar
                row[f"{key}_break_reached"] = brk_first_bar
        rows.append(row)
    return pd.DataFrame(rows)
