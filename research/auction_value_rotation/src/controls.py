"""Four matched controls. See SPEC_AUCTION_VALUE.md section 7.

Control 2 (MATCHED_INSIDE_STATE) implementation note (DECISIONS.md): for
each (profile, side) one candidate bar is sampled -- the last bar in the
active window that is inside the correct value-area half with no edge
breach (either side) in the trailing 6 hours -- giving a control
population of comparable scale to the treatment event population per
profile/side, matched via the same stratified-permutation bands as the
primary comparison rather than exact 1:1 pairing.
"""
import numpy as np
import pandas as pd

EPS = 1e-9
LOOKBACK_HOURS = 6.0


def build_touch_controls(excursion_rows: list) -> list:
    return [r for r in excursion_rows if r.get("interaction_kind") == "TOUCH"]


def build_successful_discovery_controls(excursion_rows: list) -> list:
    return [r for r in excursion_rows if r.get("interaction_kind") == "BREACH" and r.get("successful_discovery")]


def build_matched_inside_state_controls(mapping_df: pd.DataFrame, target_bars_by_leg: dict,
                                         breach_ts_by_profile_side: dict) -> list:
    out = []
    for _, prow in mapping_df.iterrows():
        bars = target_bars_by_leg.get(prow["target_session_leg_id"])
        if bars is None or len(bars) == 0:
            continue
        bars = bars.loc[(bars["ts_event"] >= prow["completion_ts"]) & (bars["ts_event"] < prow["expiry_ts"])]
        bars = bars.sort_values("local_rank").reset_index(drop=True)
        if len(bars) == 0:
            continue
        closes = bars["close"].to_numpy()
        ts = bars["ts_event"].to_numpy()
        et_minute = bars["et_minute"].to_numpy()
        atr20 = bars["atr20_event"].to_numpy()
        poc, val, vah = prow["poc"], prow["val"], prow["vah"]
        va_width = prow["va_width"]
        for side in ("long", "short"):
            breach_ts_list = sorted(
                breach_ts_by_profile_side.get((prow["target_session_leg_id"], "long"), [])
                + breach_ts_by_profile_side.get((prow["target_session_leg_id"], "short"), [])
            )
            candidate_idx = None
            for i in range(len(bars) - 1, -1, -1):
                c = closes[i]
                if side == "long":
                    in_half = val + EPS < c < poc - EPS
                else:
                    in_half = poc + EPS < c < vah - EPS
                if not in_half:
                    continue
                cur_ts = pd.Timestamp(ts[i])
                recent_breach = any(
                    0 <= (cur_ts - pd.Timestamp(bts)).total_seconds() / 3600 < LOOKBACK_HOURS
                    for bts in breach_ts_list
                )
                if not recent_breach:
                    candidate_idx = i
                    break
            if candidate_idx is None:
                continue
            c = closes[candidate_idx]
            out.append({
                "mapping_id": prow["mapping_id"], "target_session_leg_id": prow["target_session_leg_id"],
                "side": side, "level": val if side == "long" else vah, "poc": poc, "va_width": va_width,
                "vah": vah, "val": val, "completion_ts": prow["completion_ts"], "expiry_ts": prow["expiry_ts"],
                "confirmation_ts": ts[candidate_idx], "confirmation_close": float(c),
                "poc_distance_pct": float(abs(poc - c) / va_width) if va_width > 0 else np.nan,
                "freshness_hours": float((pd.Timestamp(ts[candidate_idx]) - pd.Timestamp(prow["completion_ts"])).total_seconds() / 3600),
                "excursion_extreme": float(c),  # matched-inside-state control has no excursion; symmetric fallback
                "control_type": "MATCHED_INSIDE_STATE",
                "confirmation_et_minute": int(et_minute[candidate_idx]),
                "confirmation_atr20": float(atr20[candidate_idx]) if not np.isnan(atr20[candidate_idx]) else np.nan,
            })
    return out
