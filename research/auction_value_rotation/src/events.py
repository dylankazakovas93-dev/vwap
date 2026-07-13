"""VAH/VAL event state machine: first interaction (touch or breach) per
profile/side, and the master per-excursion, per-acceptance-rule ledger.
See SPEC_AUCTION_VALUE.md sections 3-4.
"""
import numpy as np
import pandas as pd

TICK = 0.25
EPS = 1e-9
ACCEPTANCE_RULES = ("R1_ONE_CLOSE", "R2_TWO_CONSECUTIVE_CLOSES", "R3_TWO_OF_THREE_CLOSES", "R4_DEPTH_ACCEPTANCE")


def _inside_strict(close, level, side):
    return (close > level + EPS) if side == "long" else (close < level - EPS)


def _tick_eq(a, b):
    return abs(a - b) < TICK / 2 - EPS


def first_interaction(lows, highs, level, side):
    """Returns (idx, kind) for the first bar whose range reaches `level`,
    kind in {'TOUCH','BREACH'}; None if no interaction."""
    if side == "long":
        reaches = lows <= level + EPS
    else:
        reaches = highs >= level - EPS
    idxs = np.where(reaches)[0]
    if len(idxs) == 0:
        return None
    i = int(idxs[0])
    if side == "long":
        kind = "TOUCH" if _tick_eq(lows[i], level) else "BREACH"
    else:
        kind = "TOUCH" if _tick_eq(highs[i], level) else "BREACH"
    return i, kind


def _find_confirmation(closes, breach_idx, level, va_width, side, rule):
    n = len(closes)
    if rule == "R1_ONE_CLOSE":
        for i in range(breach_idx, n):
            c = closes[i]
            inside = (c >= level + TICK - EPS) if side == "long" else (c <= level - TICK + EPS)
            if inside:
                return i
        return None
    if rule == "R2_TWO_CONSECUTIVE_CLOSES":
        run = 0
        for i in range(breach_idx, n):
            if _inside_strict(closes[i], level, side):
                run += 1
                if run >= 2:
                    return i
            else:
                run = 0
        return None
    if rule == "R3_TWO_OF_THREE_CLOSES":
        for start in range(breach_idx + 1, n - 1):
            window = closes[start : start + 3]
            if len(window) < 3:
                break
            count = sum(_inside_strict(c, level, side) for c in window)
            if count >= 2:
                return start + 2
        return None
    if rule == "R4_DEPTH_ACCEPTANCE":
        depth = 0.10 * va_width
        for i in range(breach_idx, n):
            c = closes[i]
            inside = (c >= level + depth - EPS) if side == "long" else (c <= level - depth + EPS)
            if inside:
                return i
        return None
    raise ValueError(rule)


def scan_profile_side(target_bars: pd.DataFrame, profile_row: pd.Series, side: str) -> dict:
    """Returns a dict describing the first interaction (touch or breach)
    for this (mapping row, side); if breach, includes per-rule confirmation
    results. Bars must be sorted by local_rank, restricted to this leg
    instance, and restricted to ts_event in [completion_ts, expiry_ts)."""
    level = profile_row["val"] if side == "long" else profile_row["vah"]
    poc, va_width = profile_row["poc"], profile_row["va_width"]
    lows = target_bars["low"].to_numpy()
    highs = target_bars["high"].to_numpy()
    closes = target_bars["close"].to_numpy()
    ts = target_bars["ts_event"].to_numpy()
    et_minute = target_bars["et_minute"].to_numpy()
    atr20 = target_bars["atr20_event"].to_numpy()
    n = len(target_bars)

    fi = first_interaction(lows, highs, level, side)
    base = {
        "mapping_id": profile_row["mapping_id"], "target_session_leg_id": profile_row["target_session_leg_id"],
        "source_session_leg_id": profile_row["source_session_leg_id"], "side": side,
        "level": level, "poc": poc, "va_width": va_width,
        "vah": profile_row["vah"], "val": profile_row["val"],
        "completion_ts": profile_row["completion_ts"], "expiry_ts": profile_row["expiry_ts"],
    }
    if fi is None:
        base["interaction_kind"] = None
        return base
    idx, kind = fi
    base["interaction_idx"] = idx
    base["interaction_ts"] = ts[idx]
    base["interaction_kind"] = kind
    base["interaction_et_minute"] = int(et_minute[idx])
    if kind == "TOUCH":
        base["touch_close"] = closes[idx]
        base["touch_poc_distance_pct"] = abs(poc - closes[idx]) / va_width if va_width > 0 else np.nan
        return base

    # BREACH: evaluate all four acceptance rules independently
    rules_out = {}
    for rule in ACCEPTANCE_RULES:
        conf_idx = _find_confirmation(closes, idx, level, va_width, side, rule)
        if conf_idx is None or ts[conf_idx] >= base["expiry_ts"]:
            rules_out[rule] = None
            continue
        conf_close = closes[conf_idx]
        inside_ok = (level < conf_close < profile_row["vah"]) if side == "long" else (profile_row["val"] < conf_close < level)
        side_ok = (conf_close < poc) if side == "long" else (conf_close > poc)
        if not inside_ok or not side_ok:
            rules_out[rule] = None
            continue
        window = slice(idx, conf_idx + 1)
        depth = (level - lows[window].min()) if side == "long" else (highs[window].max() - level)
        excursion_extreme = float(lows[window].min()) if side == "long" else float(highs[window].max())
        rules_out[rule] = {
            "confirmation_idx": int(conf_idx), "confirmation_ts": ts[conf_idx], "confirmation_close": float(conf_close),
            "bars_outside": int(conf_idx - idx), "breach_depth": float(depth),
            "breach_depth_ticks": float(depth / TICK), "breach_depth_pct_va": float(depth / va_width) if va_width > 0 else np.nan,
            "poc_distance_pct": float(abs(poc - conf_close) / va_width) if va_width > 0 else np.nan,
            "freshness_hours": float((pd.Timestamp(ts[conf_idx]) - pd.Timestamp(base["completion_ts"])).total_seconds() / 3600),
            "excursion_extreme": excursion_extreme,
            "confirmation_et_minute": int(et_minute[conf_idx]),
            "confirmation_atr20": float(atr20[conf_idx]) if not np.isnan(atr20[conf_idx]) else np.nan,
        }
    base["rules"] = rules_out
    base["successful_discovery"] = all(v is None for v in rules_out.values())
    return base


def build_excursion_ledger(mapping_df: pd.DataFrame, target_bars_by_leg: dict) -> list:
    """One row per (mapping row, side); breach rows carry a nested `rules` dict."""
    out = []
    for _, prow in mapping_df.iterrows():
        bars = target_bars_by_leg.get(prow["target_session_leg_id"])
        if bars is None or len(bars) == 0:
            continue
        bars = bars.loc[(bars["ts_event"] >= prow["completion_ts"]) & (bars["ts_event"] < prow["expiry_ts"])]
        bars = bars.sort_values("local_rank").reset_index(drop=True)
        if len(bars) == 0:
            continue
        for side in ("long", "short"):
            out.append(scan_profile_side(bars, prow, side))
    return out
