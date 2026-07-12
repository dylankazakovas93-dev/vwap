"""Three-bar arming, first-touch-only event detection, same-bar morphology.

See SPEC_EMA21_LEVELS.md sections 4 and 6, DECISIONS.md #5-#6.
"""
import numpy as np
import pandas as pd

HORIZONS = (1, 2, 3, 5, 10, 20)
MAX_HORIZON = max(HORIZONS)


def _stratum(et_minute: int) -> str:
    if 570 <= et_minute <= 629:
        return "OPEN"
    if 630 <= et_minute <= 719:
        return "MID_MORNING"
    if 720 <= et_minute <= 839:
        return "MIDDAY"
    if 840 <= et_minute <= 959:
        return "AFTERNOON"
    return "OUTSIDE_RTH"


def _morphology(side: str, close_t: float, level_t: float, open_t, high_t, low_t):
    if side == "FROM_ABOVE":
        if close_t > level_t:
            label = "SAME_BAR_REJECTION_PROXY"
        elif close_t < level_t:
            label = "SAME_BAR_BREAKTHROUGH_PROXY"
        else:
            label = "SAME_BAR_NEUTRAL"
    else:
        if close_t < level_t:
            label = "SAME_BAR_REJECTION_PROXY"
        elif close_t > level_t:
            label = "SAME_BAR_BREAKTHROUGH_PROXY"
        else:
            label = "SAME_BAR_NEUTRAL"
    rng = high_t - low_t
    body = abs(close_t - open_t)
    body_range_ratio = (body / rng) if rng > 0 else np.nan
    close_loc = ((close_t - low_t) / rng) if rng > 0 else np.nan
    upper_wick = (high_t - max(open_t, close_t))
    lower_wick = (min(open_t, close_t) - low_t)
    upper_wick_ratio = (upper_wick / rng) if rng > 0 else np.nan
    lower_wick_ratio = (lower_wick / rng) if rng > 0 else np.nan
    return label, close_t - level_t, close_loc, body_range_ratio, upper_wick_ratio, lower_wick_ratio


def detect(bars: pd.DataFrame, span: int, instrument: str, session_def: str):
    """Returns (armed_excursions_df, touch_events_df) for one span/instrument/session_def."""
    level = bars[f"level{span}"].to_numpy()
    low = bars["low"].to_numpy()
    high = bars["high"].to_numpy()
    close = bars["close"].to_numpy()
    openp = bars["open"].to_numpy()
    is_rth = bars["is_rth"].to_numpy()
    session_date = bars["session_date"].to_numpy()
    ts_event = bars["ts_event"].to_numpy()
    et_minute = (bars["bucket_start_min"]).to_numpy()
    n = len(bars)

    valid = ~np.isnan(level)
    cond_above = np.zeros(n, dtype=bool)
    cond_below = np.zeros(n, dtype=bool)
    cond_above[valid] = low[valid] > level[valid]
    cond_below[valid] = high[valid] < level[valid]

    armed_side = np.array([None] * n, dtype=object)
    for i in range(3, n):
        if valid[i - 3] and valid[i - 2] and valid[i - 1]:
            if cond_above[i - 3] and cond_above[i - 2] and cond_above[i - 1]:
                armed_side[i] = "FROM_ABOVE"
            elif cond_below[i - 3] and cond_below[i - 2] and cond_below[i - 1]:
                armed_side[i] = "FROM_BELOW"

    excursions = []
    events = []
    cur_side = None
    cur_start = None
    touched_in_excursion = False

    def close_excursion(end_idx):
        excursions.append(
            {
                "instrument": instrument,
                "ema_session_definition": session_def,
                "ema_span": span,
                "approach_side": cur_side,
                "start_idx": cur_start,
                "end_idx": end_idx,
                "start_session_date": session_date[cur_start],
                "end_session_date": session_date[end_idx],
                "touched": touched_in_excursion,
            }
        )

    for i in range(n):
        side = armed_side[i]
        if side != cur_side:
            if cur_side is not None:
                close_excursion(i - 1)
            if side is not None:
                cur_start = i
                touched_in_excursion = False
            cur_side = side
        if side is not None and valid[i] and is_rth[i] and not touched_in_excursion:
            if low[i] <= level[i] <= high[i]:
                touched_in_excursion = True
                lvl = level[i]
                label, close_minus_level, close_loc, body_ratio, up_wick, lo_wick = _morphology(
                    side, close[i], lvl, openp[i], high[i], low[i]
                )
                arming_bars = []
                for k in (i - 3, i - 2, i - 1):
                    arming_bars.append(
                        {
                            "idx": k,
                            "open": openp[k],
                            "high": high[k],
                            "low": low[k],
                            "close": close[k],
                            "level": level[k],
                        }
                    )
                events.append(
                    {
                        "instrument": instrument,
                        "ema_session_definition": session_def,
                        "ema_span": span,
                        "session_date": session_date[i],
                        "year": pd.Timestamp(session_date[i]).year,
                        "touch_idx": i,
                        "touch_ts": ts_event[i],
                        "touch_et_minute": int(et_minute[i]),
                        "time_stratum": _stratum(int(et_minute[i])),
                        "approach_side": side,
                        "level_t": lvl,
                        "prev_close": close[i - 1],
                        "distance_before_touch": abs(close[i - 1] - level[i - 1])
                        if valid[i - 1]
                        else np.nan,
                        "open_t": openp[i],
                        "high_t": high[i],
                        "low_t": low[i],
                        "close_t": close[i],
                        "volume_t": bars["volume"].to_numpy()[i],
                        "close_minus_level": close_minus_level,
                        "close_location": close_loc,
                        "body_range_ratio": body_ratio,
                        "upper_wick_ratio": up_wick,
                        "lower_wick_ratio": lo_wick,
                        "same_bar_morphology": label,
                        "arming_bars": arming_bars,
                    }
                )
    if cur_side is not None:
        close_excursion(n - 1)

    return pd.DataFrame(excursions), pd.DataFrame(events)
