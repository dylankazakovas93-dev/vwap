"""Arming, first-interaction classification, and breach/failure/control
terminal classes. See SPEC_SWEEP_FAILURE.md sections 4-10, 12.
"""
import numpy as np
import pandas as pd

from .data import TICK, tick_eq

LEVEL_TYPES = ("prev_rth_high", "prev_rth_low", "overnight_high", "overnight_low")
UPPER_TYPES = ("prev_rth_high", "overnight_high")
LOWER_TYPES = ("prev_rth_low", "overnight_low")


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


def _same_bar_morphology(side: str, close_b: float, level: float) -> str:
    if side == "upper":
        if close_b < level and not tick_eq(close_b, level):
            return "FAILURE_PROXY"
        if close_b > level and not tick_eq(close_b, level):
            return "OUTSIDE_CLOSE_PROXY"
        return "NEUTRAL"
    else:
        if close_b > level and not tick_eq(close_b, level):
            return "FAILURE_PROXY"
        if close_b < level and not tick_eq(close_b, level):
            return "OUTSIDE_CLOSE_PROXY"
        return "NEUTRAL"


def process_level_session(bars: pd.DataFrame, level: float, side: str, level_type: str,
                           instrument: str, session_date):
    """bars: this session's RTH 1-minute bars (390), sorted, reset_index."""
    n = len(bars)
    high = bars["high"].to_numpy()
    low = bars["low"].to_numpy()
    close = bars["close"].to_numpy()
    openp = bars["open"].to_numpy()
    volume = bars["volume"].to_numpy()
    atr = bars["atr20_event"].to_numpy()
    et_minute = bars["et_minute"].to_numpy()
    ts_event = bars["ts_event"].to_numpy()

    if side == "upper":
        cond_inside = high < level - 1e-9
    else:
        cond_inside = low > level + 1e-9

    armed = np.zeros(n, dtype=bool)
    for i in range(3, n):
        armed[i] = cond_inside[i - 3] and cond_inside[i - 2] and cond_inside[i - 1]

    episodes = []
    events = []
    prior_test_count = 0

    i = 0
    consumed_until = -1
    while i < n:
        if i <= consumed_until or not armed[i]:
            i += 1
            continue
        # find first interaction bar T >= i whose range reaches the level,
        # while the 3-bar arming condition continues to hold up to T
        T = None
        j = i
        while j < n:
            if side == "upper":
                reaches = high[j] >= level - 1e-9
            else:
                reaches = low[j] <= level + 1e-9
            if reaches:
                T = j
                break
            if not (cond_inside[j - 3] and cond_inside[j - 2] and cond_inside[j - 1]):
                break
            j += 1
        if T is None:
            episodes.append({"instrument": instrument, "session_date": session_date,
                              "level_type": level_type, "side": side, "start_idx": i,
                              "end_idx": n - 1, "interacted": False})
            break

        episodes.append({"instrument": instrument, "session_date": session_date,
                          "level_type": level_type, "side": side, "start_idx": i,
                          "end_idx": T, "interacted": True, "interaction_idx": T})

        is_touch = tick_eq(high[T] if side == "upper" else low[T], level)
        base = {
            "instrument": instrument, "session_date": session_date, "level_type": level_type,
            "side": side, "level": level, "atr20_event": atr[T],
            "prior_test_count_n": prior_test_count,
            "prior_test_category": (
                "FIRST_TEST" if prior_test_count == 0 else
                ("SECOND_TEST" if prior_test_count == 1 else "THIRD_PLUS_TEST")
            ),
        }

        if is_touch:
            base.update({
                "event_class": "TOUCH_WITHOUT_BREACH",
                "event_idx": T, "touch_time_stratum": _stratum(int(et_minute[T])),
                "touch_ts": ts_event[T], "touch_sub": (
                    "TOUCH_CLOSE_AT_LEVEL" if tick_eq(close[T], level) else "TOUCH_CLOSE_INSIDE"
                ),
            })
            events.append(base)
            prior_test_count += 1
            consumed_until = T
            i = T + 1
            continue

        # breach at B = T
        B = T
        breach_mag = (high[B] - level) if side == "upper" else (level - low[B])
        atr_b = atr[B]
        breach_mag_atr = breach_mag / atr_b if (atr_b is not None and not np.isnan(atr_b) and atr_b > 0) else np.nan
        if np.isnan(breach_mag_atr):
            band = None
        elif breach_mag_atr < 0.25:
            band = "0_TO_0.25_ATR"
        elif breach_mag_atr < 0.50:
            band = "0.25_TO_0.50_ATR"
        elif breach_mag_atr < 1.00:
            band = "0.50_TO_1.00_ATR"
        else:
            band = "ABOVE_1.00_ATR"

        def is_inside_close(idx):
            c = close[idx]
            if side == "upper":
                return c < level and not tick_eq(c, level)
            return c > level and not tick_eq(c, level)

        def is_outside_close(idx):
            c = close[idx]
            if side == "upper":
                return c > level and not tick_eq(c, level)
            return c < level and not tick_eq(c, level)

        base.update({
            "breach_idx": B, "breach_ts": ts_event[B],
            "breach_time_stratum": _stratum(int(et_minute[B])),
            "breach_magnitude": breach_mag, "breach_magnitude_atr": breach_mag_atr,
            "breach_magnitude_band": band,
            "same_bar_morphology": _same_bar_morphology(side, close[B], level),
            "candle_range": high[B] - low[B],
            "body_range_ratio": (abs(close[B] - openp[B]) / (high[B] - low[B])) if (high[B] - low[B]) > 0 else np.nan,
            "breach_side_wick": (high[B] - max(openp[B], close[B])) if side == "upper" else (min(openp[B], close[B]) - low[B]),
            "volume_b": volume[B],
            "close_distance_from_level": abs(close[B] - level),
        })
        if (high[B] - low[B]) > 0:
            base["breach_side_wick_ratio"] = base["breach_side_wick"] / (high[B] - low[B])
        else:
            base["breach_side_wick_ratio"] = np.nan

        classified = False
        end_of_session = False
        for k, delay_label in enumerate(("FAILED_BREACH_1MIN", "FAILED_BREACH_2MIN", "FAILED_BREACH_3MIN")):
            idx = B + k
            if idx >= n:
                end_of_session = True
                break
            if is_inside_close(idx):
                base.update({"event_class": delay_label, "event_idx": B, "confirmation_idx": idx})
                events.append(base)
                classified = True
                break
        if classified:
            prior_test_count += 1
            consumed_until = idx  # disarm as of the confirmation bar itself
            i = consumed_until + 1
            continue
        if end_of_session:
            base.update({"event_class": "INCOMPLETE_EPISODE", "event_idx": B})
            events.append(base)
            prior_test_count += 1
            break

        # none of B, B+1, B+2 closed inside; check successful-breach-control
        any_outside = any(is_outside_close(B + k) for k in range(3))
        if any_outside:
            base.update({"event_class": "SUCCESSFUL_BREACH_CONTROL", "event_idx": B,
                         "confirmation_idx": B + 2})
            events.append(base)
            prior_test_count += 1
            consumed_until = B + 2
            i = consumed_until + 1
            continue

        # neither inside nor outside close in B..B+2 (all tick-equal to level) ->
        # keep scanning for delayed failure within B+3..B+9, else NEITHER
        resolved = False
        for idx in range(B + 3, min(B + 10, n)):
            if is_inside_close(idx):
                base.update({"event_class": "DELAYED_FAILURE_CONTROL", "event_idx": B,
                             "confirmation_idx": idx})
                events.append(base)
                resolved = True
                consumed_until = idx
                break
        if not resolved:
            last_checked = min(B + 9, n - 1)
            base.update({"event_class": "NEITHER_RESOLVED_WITHIN_10MIN", "event_idx": B})
            events.append(base)
            consumed_until = last_checked
        prior_test_count += 1
        i = consumed_until + 1

    return episodes, events
