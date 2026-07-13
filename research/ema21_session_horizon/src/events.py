"""Three-bar arming, first-touch-only event detection, same-bar morphology.

Scoped to one session-leg instance's own local bar array (DECISIONS.md
#4). See SPEC_SESSION_HORIZONS.md sections 3-5, 7.
"""
import numpy as np
import pandas as pd

HORIZONS = (1, 2, 3, 4, 6, 9, 12, 18, 24)
MAX_HORIZON = max(HORIZONS)


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
    upper_wick_ratio = ((high_t - max(open_t, close_t)) / rng) if rng > 0 else np.nan
    lower_wick_ratio = ((min(open_t, close_t) - low_t) / rng) if rng > 0 else np.nan
    return label, close_t - level_t, close_loc, body_range_ratio, upper_wick_ratio, lower_wick_ratio


def detect_leg(local_bars: pd.DataFrame, leg: str, session_date, instrument: str):
    """local_bars: bars for ONE (session_date, leg) instance, ts_event-sorted,
    with columns low/high/open/close/level21/atr_event/ts_event/local_rank/
    touch_time_bucket/volume. Returns (excursions_df, touches_df)."""
    level = local_bars["level21"].to_numpy()
    low = local_bars["low"].to_numpy()
    high = local_bars["high"].to_numpy()
    close = local_bars["close"].to_numpy()
    openp = local_bars["open"].to_numpy()
    ts_event = local_bars["ts_event"].to_numpy()
    touch_bucket = local_bars["touch_time_bucket"].to_numpy()
    n = len(local_bars)

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
                "session_date": session_date,
                "session": leg,
                "approach_side": cur_side,
                "start_local_idx": cur_start,
                "end_local_idx": end_idx,
                "touched": touched_in_excursion,
                "start_touch_time_bucket": touch_bucket[cur_start],
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
        if side is not None and valid[i] and not touched_in_excursion:
            if low[i] <= level[i] <= high[i]:
                touched_in_excursion = True
                lvl = level[i]
                label, close_minus_level, close_loc, body_ratio, up_wick, lo_wick = _morphology(
                    side, close[i], lvl, openp[i], high[i], low[i]
                )
                events.append(
                    {
                        "instrument": instrument,
                        "session_date": session_date,
                        "session": leg,
                        "year": pd.Timestamp(session_date).year,
                        "local_touch_idx": i,
                        "touch_ts": ts_event[i],
                        "touch_time_bucket": touch_bucket[i],
                        "approach_side": side,
                        "level_t": lvl,
                        "prev_close": close[i - 1],
                        "open_t": openp[i],
                        "high_t": high[i],
                        "low_t": low[i],
                        "close_t": close[i],
                        "volume_t": local_bars["volume"].to_numpy()[i],
                        "close_minus_level": close_minus_level,
                        "close_location": close_loc,
                        "body_range_ratio": body_ratio,
                        "upper_wick_ratio": up_wick,
                        "lower_wick_ratio": lo_wick,
                        "same_bar_morphology": label,
                    }
                )
    if cur_side is not None:
        close_excursion(n - 1)

    return pd.DataFrame(excursions), pd.DataFrame(events)
