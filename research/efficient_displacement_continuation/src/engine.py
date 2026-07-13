from __future__ import annotations

import io
import json
import os
import re
import zipfile
from collections import defaultdict

import numpy as np
import pandas as pd
import zstandard as zstd

DEV_START = pd.Timestamp("2018-01-01", tz="America/New_York")
DEV_END = pd.Timestamp("2022-12-31 23:59:59", tz="America/New_York")
SESSIONS = ("ASIA", "LONDON", "NEW_YORK")
HORIZONS = (5, 10, 15, 30)
BARRIERS = (0.25, 0.50, 1.00)
SEED = 20260713


def session_info(ts_et: pd.Timestamp):
    m = ts_et.hour * 60 + ts_et.minute
    if m >= 18 * 60 or m <= 2 * 60 + 59:
        return (ts_et.normalize() + (pd.Timedelta(days=1) if m >= 18 * 60 else pd.Timedelta(0))).date(), "ASIA"
    if 3 * 60 <= m <= 8 * 60 + 29:
        return ts_et.date(), "LONDON"
    if 9 * 60 + 30 <= m <= 15 * 60 + 59:
        return ts_et.date(), "NEW_YORK"
    return None, None


def _zip_csv_member(path):
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.endswith(".csv.zst")]
        if len(names) != 1:
            raise ValueError(f"expected one csv.zst in {path}, got {names}")
        return zf.read(names[0])


def load_archives(instrument: str, paths: list[str]) -> pd.DataFrame:
    frames = []
    for path in paths:
        raw = _zip_csv_member(path)
        with zstd.ZstdDecompressor().stream_reader(io.BytesIO(raw)) as reader:
            data = reader.read()
        df = pd.read_csv(io.BytesIO(data), usecols=["ts_event", "open", "high", "low", "close", "volume", "symbol"])
        ts = pd.to_datetime(df.pop("ts_event"), utc=True).dt.tz_convert("America/New_York")
        df.insert(0, "ts_event", ts)
        df["instrument"] = instrument
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    root_re = re.compile(rf"^{instrument}[HMUZ]\d$")
    out = out[out.symbol.astype(str).str.match(root_re)].copy()
    out = out.drop_duplicates(["ts_event", "symbol"], keep="first")
    et = out.ts_event.dt.tz_convert("America/New_York")
    et_min = et.dt.hour * 60 + et.dt.minute
    out = out[(et_min < 17 * 60) | (et_min >= 18 * 60)].copy()
    # Causal continuous front month: the prior session's volume leader.
    info = et.map(session_info)
    out["session_date"] = info.map(lambda x: x[0])
    out["session"] = info.map(lambda x: x[1])
    out = out[out.session.notna()]
    sess_vol = out.groupby(["session_date", "symbol"], sort=True).volume.sum()
    leaders = sess_vol.groupby(level=0).idxmax().to_dict()
    session_dates = sorted(leaders)
    prior_front = {session_dates[i]: leaders[session_dates[i - 1]][1] for i in range(1, len(session_dates))}
    out["front_symbol"] = out.session_date.map(prior_front)
    out = out[out.symbol == out.front_symbol].drop(columns="front_symbol")
    out = out[(out.ts_event >= DEV_START) & (out.ts_event <= DEV_END)].copy()
    if len(out) == 0:
        raise ValueError(f"no development rows for {instrument}")
    if out.ts_event.duplicated().any():
        raise ValueError(f"duplicate timestamps for {instrument}")
    if not np.isfinite(out[["open", "high", "low", "close", "volume"]].to_numpy()).all():
        raise ValueError(f"non-finite OHLCV for {instrument}")
    if (out.high < out.low).any() or (out.volume < 0).any():
        raise ValueError(f"invalid OHLCV for {instrument}")
    out = out.sort_values("ts_event").reset_index(drop=True)
    assert out.ts_event.max() <= DEV_END and out.ts_event.dt.year.max() <= 2022
    return out


def _empirical_rank(x, hist):
    return float(np.mean(np.asarray(hist, dtype=float) <= x))


def build_impulses(bars: pd.DataFrame):
    rows = []
    grouped = bars.groupby(["session_date", "session"], sort=True)
    for (sd, sess), g in grouped:
        g = g.sort_values("ts_event").reset_index(drop=True)
        records = list(g.itertuples(index=False))
        for i in range(2, len(records)):
            c = records[i]
            if c.ts_event.minute % 3 != 2:
                continue
            a, b = records[i - 2], records[i - 1]
            if (b.ts_event - a.ts_event) != pd.Timedelta(minutes=1) or (c.ts_event - b.ts_event) != pd.Timedelta(minutes=1):
                continue
            # Exact non-overlapping three-minute clock slots: t is the third bar.
            net = float(c.close - a.open)
            if net == 0:
                continue
            path = abs(float(a.close - a.open)) + abs(float(b.close - a.close)) + abs(float(c.close - b.close))
            wh, wl = float(max(a.high, b.high, c.high)), float(min(a.low, b.low, c.low))
            wr = wh - wl
            if path <= 0 or wr <= 0:
                continue
            direction = 1 if net > 0 else -1
            loc = (c.close - wl) / wr if direction == 1 else (wh - c.close) / wr
            def overlap(x, y):
                inter = max(0.0, min(x.high, y.high) - max(x.low, y.low))
                union = max(x.high, y.high) - min(x.low, y.low)
                return inter / union if union > 0 else np.nan
            ov1, ov2 = overlap(a, b), overlap(b, c)
            if not np.isfinite(ov1) or not np.isfinite(ov2):
                continue
            rows.append({"instrument": bars.instrument.iloc[0], "session_date": sd, "session": sess,
                         "start_ts": a.ts_event, "end_ts": c.ts_event, "clock_slot": c.ts_event.hour * 60 + c.ts_event.minute,
                         "event_end_hour": c.ts_event.hour, "impulse_open": float(a.open), "impulse_close": float(c.close),
                         "net_move": net, "direction": direction, "abs_move": abs(net), "path_length": path,
                         "efficiency": abs(net) / path, "window_high": wh, "window_low": wl, "window_range": wr,
                         "directional_close_location": loc, "overlap_1": ov1, "overlap_2": ov2,
                         "mean_overlap": (ov1 + ov2) / 2, "volume_3m": float(a.volume + b.volume + c.volume)})
    return pd.DataFrame(rows)


def add_causal_percentiles(impulses: pd.DataFrame):
    impulses = impulses.sort_values(["session_date", "end_ts"]).reset_index(drop=True).copy()
    histories = defaultdict(lambda: {"abs_move": [], "window_range": [], "volume_3m": []})
    out = []
    for r in impulses.itertuples(index=False):
        key = (r.instrument, r.session, r.clock_slot)
        h = histories[key]
        row = r._asdict()
        row["prior_valid_n"] = len(h["abs_move"])
        if len(h["abs_move"]) >= 60:
            row["abs_move_percentile"] = _empirical_rank(r.abs_move, h["abs_move"][-60:])
            row["range_percentile"] = _empirical_rank(r.window_range, h["window_range"][-60:])
            row["volume_percentile"] = _empirical_rank(r.volume_3m, h["volume_3m"][-60:])
        else:
            row["abs_move_percentile"] = np.nan; row["range_percentile"] = np.nan; row["volume_percentile"] = np.nan
        h["abs_move"].append(r.abs_move); h["window_range"].append(r.window_range); h["volume_3m"].append(r.volume_3m)
        out.append(row)
    return pd.DataFrame(out)


def classify(imp):
    if not np.isfinite(imp.abs_move_percentile) or imp.abs_move_percentile < .90:
        return "NOT_ELIGIBLE"
    if imp.efficiency >= .80 and imp.directional_close_location >= .80 and imp.mean_overlap <= .35:
        return "EFFICIENT_DISPLACEMENT"
    if imp.efficiency <= .50 and imp.mean_overlap >= .50:
        return "INEFFICIENT_DISPLACEMENT_CONTROL"
    return "INTERMEDIATE"


def add_outcomes(impulses: pd.DataFrame, bars: pd.DataFrame):
    lookup = {r.ts_event: r for r in bars.itertuples(index=False)}
    rows = []
    for r in impulses.itertuples(index=False):
        if r.state == "NOT_ELIGIBLE":
            continue
        future = []
        for h in range(1, 31):
            x = lookup.get(r.end_ts + pd.Timedelta(minutes=h))
            if x is None or x.session_date != r.session_date or x.session != r.session:
                future = []; break
            future.append(x)
        row = r._asdict()
        for h in HORIZONS:
            vals = future[:h] if len(future) >= h else []
            if not vals:
                row.update({f"continuation_exc_{h}": np.nan, f"reversal_exc_{h}": np.nan, f"signed_close_{h}": np.nan,
                            f"continuation_exc_r_{h}": np.nan, f"reversal_exc_r_{h}": np.nan, f"signed_close_r_{h}": np.nan,
                            f"dominance_{h}": np.nan})
                continue
            if r.direction == 1:
                ce = max(0.0, max(x.high for x in vals) - r.impulse_close); re = max(0.0, r.impulse_close - min(x.low for x in vals)); sc = vals[-1].close - r.impulse_close
            else:
                ce = max(0.0, r.impulse_close - min(x.low for x in vals)); re = max(0.0, max(x.high for x in vals) - r.impulse_close); sc = r.impulse_close - vals[-1].close
            den = ce + re
            row.update({f"continuation_exc_{h}": ce, f"reversal_exc_{h}": re, f"signed_close_{h}": sc,
                        f"continuation_exc_r_{h}": ce / r.abs_move, f"reversal_exc_r_{h}": re / r.abs_move,
                        f"signed_close_r_{h}": sc / r.abs_move, f"dominance_{h}": (ce - re) / den if den else np.nan})
        rows.append(row)
    return pd.DataFrame(rows)


def add_barriers(events: pd.DataFrame, bars: pd.DataFrame):
    lookup = {r.ts_event: r for r in bars.itertuples(index=False)}
    rows = []
    for r in events.itertuples(index=False):
        for mult in BARRIERS:
            vals = []
            for h in range(1, 31):
                x = lookup.get(r.end_ts + pd.Timedelta(minutes=h))
                if x is None or x.session_date != r.session_date or x.session != r.session:
                    vals = []; break
                vals.append(x)
            cbar = r.impulse_close + r.direction * mult * r.abs_move
            rbar = r.impulse_close - r.direction * mult * r.abs_move
            cf = rf = None
            for i, x in enumerate(vals, 1):
                c_hit = x.high >= cbar if r.direction == 1 else x.low <= cbar
                r_hit = x.low <= rbar if r.direction == 1 else x.high >= rbar
                if cf is None and c_hit: cf = i
                if rf is None and r_hit: rf = i
                if cf is not None and rf is not None: break
            if cf is None and rf is None: outcome = "NEITHER"
            elif cf is not None and rf is not None and cf == rf: outcome = "SAME_BAR_TIE"
            elif cf is not None and (rf is None or cf < rf): outcome = "CONTINUATION_FIRST"
            else: outcome = "REVERSAL_FIRST"
            rows.append({"event_id": r.event_id, "instrument": r.instrument, "session_date": r.session_date, "session": r.session,
                         "direction": r.direction, "state": r.state, "abs_move_percentile": r.abs_move_percentile,
                         "move_band": r.move_band, "end_hour": r.event_end_hour, "barrier_multiple": mult,
                         "continuation_first_bar": cf, "reversal_first_bar": rf, "outcome": outcome})
    return pd.DataFrame(rows)


def add_confirmation(events_by_inst):
    es = events_by_inst.get("ES", pd.DataFrame()).set_index("end_ts") if "ES" in events_by_inst else pd.DataFrame()
    nq = events_by_inst.get("NQ", pd.DataFrame()).set_index("end_ts") if "NQ" in events_by_inst else pd.DataFrame()
    rows = []
    for inst, ev in events_by_inst.items():
        pair = nq if inst == "ES" else es
        for r in ev.itertuples(index=False):
            p = pair.loc[r.end_ts] if not pair.empty and r.end_ts in pair.index else None
            if p is None: conf = "NO_MATCH"
            elif p.direction == r.direction and p.abs_move_percentile >= .70: conf = "CONFIRMED"
            elif p.direction != r.direction or (np.isfinite(p.abs_move_percentile) and p.abs_move_percentile < .50): conf = "UNCONFIRMED"
            else: conf = "PARTIAL_CONFIRMATION"
            rows.append({"event_id": r.event_id, "instrument": inst, "end_ts": r.end_ts, "paired_direction": getattr(p, "direction", np.nan),
                         "paired_abs_move_percentile": getattr(p, "abs_move_percentile", np.nan), "confirmation": conf})
    return pd.DataFrame(rows)


def bh(p):
    p = np.asarray(p, float); q = np.full(len(p), np.nan); ok = np.isfinite(p)
    if not ok.any(): return q
    order = np.argsort(p[ok]); vals = p[ok][order]; adj = np.minimum.accumulate((vals * len(vals) / np.arange(1, len(vals)+1))[::-1])[::-1]
    tmp = np.empty(len(vals)); tmp[order] = np.minimum(adj, 1.0); q[ok] = tmp; return q


def permutation_pvalue(df, n=10000, seed=SEED):
    x = df[df.state.isin(["EFFICIENT_DISPLACEMENT", "INEFFICIENT_DISPLACEMENT_CONTROL"])].copy()
    x = x[x.outcome.isin(["CONTINUATION_FIRST", "REVERSAL_FIRST"])]
    if x.empty: return np.nan
    observed = (x[x.state == "EFFICIENT_DISPLACEMENT"].outcome == "CONTINUATION_FIRST").mean() - (x[x.state == "INEFFICIENT_DISPLACEMENT_CONTROL"].outcome == "CONTINUATION_FIRST").mean()
    rng = np.random.default_rng(seed); hits = 0
    # Vectorize permutations in chunks while preserving efficient/control counts
    # independently inside every fixed matching stratum.
    stratum_data = []
    for _, g in x.groupby("stratum", sort=True):
        y = (g.outcome == "CONTINUATION_FIRST").to_numpy(dtype=np.int8)
        k = int((g.state == "EFFICIENT_DISPLACEMENT").sum())
        stratum_data.append((y, k, len(y)))
    ne = int((x.state == "EFFICIENT_DISPLACEMENT").sum()); ni = len(x) - ne
    for start in range(0, n, 256):
        q = min(256, n - start); win_e = np.zeros(q, dtype=np.int64); win_i = np.zeros(q, dtype=np.int64)
        for y, k, m in stratum_data:
            if k == 0 or k == m: continue
            chosen = np.argpartition(rng.random((q, m)), k - 1, axis=1)[:, :k]
            e_wins = y[chosen].sum(axis=1)
            win_e += e_wins; win_i += y.sum() - e_wins
        ds = win_e / ne - win_i / ni
        hits += int(np.sum(np.abs(ds) >= abs(observed) - 1e-15))
    return (hits + 1) / (n + 1)


def primary_table(events, barriers):
    b = barriers[(barriers.barrier_multiple == .5) & (barriers.state.isin(["EFFICIENT_DISPLACEMENT", "INEFFICIENT_DISPLACEMENT_CONTROL"]))]
    b = b[b.outcome.isin(["CONTINUATION_FIRST", "REVERSAL_FIRST"])].copy()
    b["stratum"] = b.apply(lambda r: f"{r.instrument}|{r.session}|{r.direction}|{r.end_hour}|{r.move_band}", axis=1)
    b["cont"] = (b.outcome == "CONTINUATION_FIRST").astype(int)
    rows = []
    for key, g in b.groupby(["instrument", "session", "direction"], sort=True):
        st = g.groupby(["instrument", "session", "direction", "end_hour", "move_band", "state"], as_index=False).agg(n=("cont", "size"), continuation_rate=("cont", "mean"))
        piv = st.pivot_table(index=["instrument", "session", "direction", "end_hour", "move_band"], columns="state", values=["n", "continuation_rate"])
        diffs = []
        for _, row in piv.iterrows():
            if ("continuation_rate", "EFFICIENT_DISPLACEMENT") in row.index and ("continuation_rate", "INEFFICIENT_DISPLACEMENT_CONTROL") in row.index:
                diffs.append(row[("continuation_rate", "EFFICIENT_DISPLACEMENT")] - row[("continuation_rate", "INEFFICIENT_DISPLACEMENT_CONTROL")])
        obs = g.groupby("state").cont.mean(); diff = obs.get("EFFICIENT_DISPLACEMENT", np.nan) - obs.get("INEFFICIENT_DISPLACEMENT_CONTROL", np.nan)
        p = permutation_pvalue(g, n=10000)
        rows.append({"instrument": key[0], "session": key[1], "direction": key[2], "n_efficient": int((g.state == "EFFICIENT_DISPLACEMENT").sum()), "n_inefficient": int((g.state == "INEFFICIENT_DISPLACEMENT_CONTROL").sum()), "non_tied": len(g), "efficient_continuation_rate": obs.get("EFFICIENT_DISPLACEMENT", np.nan), "inefficient_continuation_rate": obs.get("INEFFICIENT_DISPLACEMENT_CONTROL", np.nan), "difference": diff, "p_value": p, "matched_strata": len(diffs), "classification": "UNDERPOWERED"})
    out = pd.DataFrame(rows)
    if len(out):
        out["q_value"] = bh(out.p_value)
        for i, r in out.iterrows():
            enough = r.n_efficient >= 100 and r.n_inefficient >= 100 and r.non_tied >= 100
            out.loc[i, "classification"] = "EFFICIENT_CONTINUATION_SUPPORTED" if enough and r.difference >= .05 and r.q_value < .05 else ("EFFICIENT_REVERSAL_SUPPORTED" if enough and r.difference <= -.05 and r.q_value < .05 else ("MIXED_OR_NULL" if enough else "UNDERPOWERED"))
    return out, b
