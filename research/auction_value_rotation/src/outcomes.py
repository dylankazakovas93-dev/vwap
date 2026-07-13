"""POC_REACHED_BEFORE_REDISCOVERY across horizons, secondary path stats,
and the conditional POC_TO_OPPOSITE_EDGE_COMPLETION outcome.
See SPEC_AUCTION_VALUE.md section 6.
"""
import numpy as np
import pandas as pd

HORIZONS = (15, 30, 60, 120)


class GlobalSeries:
    """Continuous 1-minute bar series for one instrument/partition, with
    O(log n) timestamp -> position lookup for outcome measurement."""

    def __init__(self, df1m: pd.DataFrame):
        df = df1m.sort_values("ts_event").reset_index(drop=True)
        ts = df["ts_event"]
        # normalize to tz-naive UTC datetime64[ns] so np.datetime64 comparisons
        # in `pos()` are well-defined regardless of the caller's tz-awareness
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_convert("UTC").dt.tz_localize(None)
        self.ts = ts.to_numpy(dtype="datetime64[ns]")
        self.high = df["high"].to_numpy()
        self.low = df["low"].to_numpy()
        self.close = df["close"].to_numpy()
        self.n = len(df)

    def pos(self, ts) -> int:
        t = pd.Timestamp(ts)
        if t.tzinfo is not None:
            t = t.tz_convert("UTC").tz_localize(None)
        t64 = np.datetime64(t)
        i = np.searchsorted(self.ts, t64)
        if i < self.n and self.ts[i] == t64:
            return int(i)
        return -1


def _resolve(series: GlobalSeries, anchor_pos: int, level: float, poc: float, side: str,
             excursion_extreme: float, H: int):
    end = anchor_pos + H
    if end >= series.n:
        return "INCOMPLETE_HORIZON", None
    first_poc = None
    first_redis = None
    for h in range(1, H + 1):
        idx = anchor_pos + h
        hi, lo = series.high[idx], series.low[idx]
        if side == "long":
            poc_hit = lo <= poc <= hi
            redis_hit = (series.close[idx] < level) or (lo < excursion_extreme)
        else:
            poc_hit = lo <= poc <= hi
            redis_hit = (series.close[idx] > level) or (hi > excursion_extreme)
        if poc_hit and redis_hit:
            return "SAME_BAR_AMBIGUOUS", h
        if poc_hit:
            return "POC_FIRST", h
        if redis_hit:
            return "REDISCOVERY_FIRST", h
    return "NEITHER", None


def add_primary_outcomes(events: list, series: GlobalSeries) -> list:
    out = []
    for ev in events:
        pos = series.pos(ev["confirmation_ts"])
        row = dict(ev)
        if pos < 0:
            for H in HORIZONS:
                row[f"outcome_h{H}"] = "INCOMPLETE_HORIZON"
            out.append(row)
            continue
        row["anchor_pos"] = pos
        for H in HORIZONS:
            outcome, first_h = _resolve(series, pos, ev["level"], ev["poc"], ev["side"], ev["excursion_extreme"], H)
            row[f"outcome_h{H}"] = outcome
            row[f"resolution_bar_h{H}"] = first_h
        # secondary path stats at the primary reporting horizon (60)
        H = 60
        end = pos + H
        if end < series.n:
            window_hi = series.high[pos + 1 : end + 1]
            window_lo = series.low[pos + 1 : end + 1]
            if ev["side"] == "long":
                mfe = max(0.0, ev["poc"] - window_lo.min())
                mae = max(0.0, ev["level"] - window_lo.min())
                exc_beyond_edge = max(0.0, ev["level"] - window_lo.min())
            else:
                mfe = max(0.0, window_hi.max() - ev["poc"])
                mae = max(0.0, window_hi.max() - ev["level"])
                exc_beyond_edge = max(0.0, window_hi.max() - ev["level"])
            row["mfe_toward_poc"] = mfe
            row["mae"] = mae
            row["excursion_beyond_edge"] = exc_beyond_edge
        out.append(row)
    return out


OPPOSITE_EDGE_HORIZON = 60  # measured from the POC-touch bar, same primary horizon as stage 1


def add_opposite_edge_completion(events_out: list, series: GlobalSeries) -> list:
    """For POC_FIRST (horizon 60) events only: does price reach the
    opposite value-area edge before returning to the originating edge,
    within OPPOSITE_EDGE_HORIZON minutes of the POC-touch bar? Reported
    as its own separate outcome, per SPEC_AUCTION_VALUE.md sec 6."""
    out = []
    H = OPPOSITE_EDGE_HORIZON
    for ev in events_out:
        row = dict(ev)
        if ev.get("outcome_h60") != "POC_FIRST" or ev.get("resolution_bar_h60") is None:
            row["opposite_edge_completion"] = None
            out.append(row)
            continue
        poc_pos = ev["anchor_pos"] + ev["resolution_bar_h60"]
        level = ev["level"]
        opposite_edge = ev["vah"] if ev["side"] == "long" else ev["val"]
        end = poc_pos + H
        if end >= series.n:
            row["opposite_edge_completion"] = "INCOMPLETE_HORIZON"
            out.append(row)
            continue
        result = "NEITHER"
        for h in range(1, H + 1):
            idx = poc_pos + h
            hi, lo = series.high[idx], series.low[idx]
            opp_hit = (hi >= opposite_edge) if ev["side"] == "long" else (lo <= opposite_edge)
            orig_hit = (lo <= level) if ev["side"] == "long" else (hi >= level)
            if opp_hit and orig_hit:
                result = "SAME_BAR_AMBIGUOUS"
                break
            if opp_hit:
                result = "OPPOSITE_EDGE_FIRST"
                break
            if orig_hit:
                result = "ORIGIN_EDGE_FIRST"
                break
        row["opposite_edge_completion"] = result
        out.append(row)
    return out
