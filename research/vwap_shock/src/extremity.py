"""Stage 2 extension (family G): extremity-threshold & retracement study.

Continuous-variable design. Builds a per-event impulse ledger at the top-10%
|z_mod1| threshold and records retracement dynamics anchored at the original
impulse extreme, VWAP-deviation signed values (both anchors), and
acceptance-strength variants (m-of-n, veto on/off), all measured causally.

Impulse (k=1): origin = C_{t-1}, extreme = C_t, direction d = sign(C_t-C_{t-1}),
magnitude M = |C_t - C_{t-1}| (points). Forward window W = 120 bars capped at
session end, starting at bar t+1. Retracement fraction is anchored at the
original impulse extreme: retr_frac_j = d*(C_t - adverse_price_j) / M, so a
value >= 1.0 means price has retraced the entire impulse (full failure).
"break extreme" = a forward bar trades beyond C_t in direction d by >= 1 tick.
"""
import os

import numpy as np
import pandas as pd

W = 120
TICK = 0.25
RETR_LEVELS = (0.10, 0.20, 0.30, 0.40, 0.50, 1.00)
ACC_RULES = {"m2of3": (2, 3), "m3of4": (3, 4), "m4of5": (4, 5)}
BAND_OUT = 2.0
BAND_IN = 1.0
TOP10_Q = 0.90
MIN_M_TICKS = 2.0  # retracement-fraction cells require impulse >= 2 ticks

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(REPO, "research", "vwap_shock", "outputs")


def _impulse_row(op, hi, lo, cl, i, d):
    n = len(cl)
    origin = cl[i - 1]
    extreme = cl[i]
    M = abs(extreme - origin)
    j0, j1 = i + 1, min(n, i + 1 + W)
    if j0 >= n or M <= 0:
        return None
    fav = hi[j0:j1] if d > 0 else lo[j0:j1]        # most favourable price
    adv = lo[j0:j1] if d > 0 else hi[j0:j1]        # most adverse price
    ext_beyond = d * (fav - extreme)               # >0 => new extreme
    retr = d * (extreme - adv)                      # >0 => pullback from extreme
    retr_frac = retr / M
    m = len(retr_frac)

    # break of original impulse extreme
    bidx = np.flatnonzero(ext_beyond >= TICK)
    t_break = int(bidx[0]) + 1 if len(bidx) else np.nan
    broke = np.isfinite(t_break)

    # running max retracement (anchored at extreme)
    run_retr = np.maximum.accumulate(retr_frac)
    max_retr = float(run_retr[-1])
    full_fail = max_retr >= 1.0

    row = {"M_ticks": M / TICK, "break_extreme": bool(broke),
           "t_break": t_break, "max_retr_frac": max_retr,
           "full_failure": bool(full_fail)}
    for R in RETR_LEVELS:
        hit = np.flatnonzero(retr_frac >= R)
        row[f"t_retr_{int(R*100)}"] = int(hit[0]) + 1 if len(hit) else np.nan
        row[f"reach_{int(R*100)}"] = bool(len(hit))

    # post-50% retracement dynamics: re-reference at the 50% level
    L50 = extreme - d * 0.5 * M
    h50 = np.flatnonzero(retr_frac >= 0.50)
    if len(h50):
        js = int(h50[0])
        fav_p = fav[js:]
        adv_p = adv[js:]
        row["post50_mfe_ticks"] = float(np.max(d * (fav_p - L50))) / TICK if len(fav_p) else np.nan
        row["post50_mae_ticks"] = float(np.max(d * (L50 - adv_p))) / TICK if len(adv_p) else np.nan
        bafter = np.flatnonzero(d * (fav[js:] - extreme) >= TICK)
        row["post50_break"] = bool(len(bafter))
        row["t_post50_break"] = int(bafter[0]) if len(bafter) else np.nan
    else:
        row["post50_mfe_ticks"] = row["post50_mae_ticks"] = np.nan
        row["post50_break"] = np.nan
        row["t_post50_break"] = np.nan

    # SYMMETRIC fractional first-passage from the impulse extreme:
    # does price reach extreme + f*M (further extension) before extreme - f*M
    # (retrace) ? Symmetric barriers in M units -> a fair directional test,
    # unlike break_extreme (1 tick) vs retrace (fraction of M).
    for f in (0.5, 1.0):
        up = d * f * M      # favourable extension target (signed handled below)
        ext = d * (fav - extreme)          # favourable progress
        ret = d * (extreme - adv)          # adverse progress
        te = np.flatnonzero(ext >= f * M)
        tr = np.flatnonzero(ret >= f * M)
        te = te[0] if len(te) else np.inf
        tr = tr[0] if len(tr) else np.inf
        if np.isinf(te) and np.isinf(tr):
            row[f"sym_race_{int(f*100)}"] = np.nan   # neither within window
        else:
            row[f"sym_race_{int(f*100)}"] = 1.0 if te < tr else (0.0 if tr < te else np.nan)

    # economic-size cross checks
    row["fret_30_ticks"] = (d * (cl[min(i + 30, n - 1)] - op[j0])) / TICK if j0 < n else np.nan
    return row


def _acceptance_strength(hi, lo, cl, vwap, sig, valid, i, d, n):
    """m-of-n beyond 2sigma with/without inner-band veto, measured on closes
    t+1..t+n; post-decision break of the impulse extreme within the remaining
    window (measured strictly AFTER the decision bar, so no overlap leakage)."""
    out = {}
    dev = d * (cl[i] - vwap[i]) / sig[i] if valid[i] else np.nan
    eligible = np.isfinite(dev) and dev >= BAND_OUT
    out["acc_eligible"] = bool(eligible)
    extreme = cl[i]
    for name, (m, nwin) in ACC_RULES.items():
        for veto in (True, False):
            key = f"{name}_veto{int(veto)}"
            if not eligible or i + nwin >= n:
                out[f"{key}_status"] = "NA"
                out[f"{key}_postbreak"] = np.nan
                continue
            beyond = reclaimed = 0
            for j in range(i + 1, i + 1 + nwin):
                if not valid[j]:
                    continue
                dv = d * (cl[j] - vwap[j])
                if dv >= BAND_OUT * sig[j]:
                    beyond += 1
                if dv < BAND_IN * sig[j]:
                    reclaimed += 1
            if veto and reclaimed:
                out[f"{key}_status"] = "REJECT"
            elif beyond >= m:
                out[f"{key}_status"] = "ACCEPT"
            else:
                out[f"{key}_status"] = "INDET"
            # post-decision break of the impulse extreme (bars after decision)
            db = i + nwin
            pb = np.nan
            if out[f"{key}_status"] in ("ACCEPT", "REJECT"):
                j0, j1 = db + 1, min(n, db + 1 + W)
                if j0 < n:
                    fav = hi[j0:j1] if d > 0 else lo[j0:j1]
                    pb = bool(np.any(d * (fav - extreme) >= TICK))
            out[f"{key}_postbreak"] = pb
    return out


def build_extremity_ledger(feat: pd.DataFrame, instrument: str) -> pd.DataFrame:
    z = feat["z_mod1"].abs()
    thr = z.dropna().quantile(TOP10_Q)
    ev_mask = (z >= thr) & feat["atr30"].notna()
    feat = feat.copy()
    feat["_ev"] = ev_mask.fillna(False)
    sess_dates = feat.loc[feat["_ev"], "session_date"].unique()
    rows = []
    for sd, sess in feat[feat["session_date"].isin(sess_dates)].groupby("session_date", sort=True):
        sess = sess.reset_index(drop=True)
        op, hi, lo, cl = (sess[c].to_numpy(float) for c in ("open", "high", "low", "close"))
        vw, sg = sess["vwap_g"].to_numpy(float), sess["sig_g"].to_numpy(float)
        vok = sess["vwap_g_valid"].to_numpy(bool)
        n = len(sess)
        idx = np.flatnonzero(sess["_ev"].to_numpy())
        for i in idx:
            if i < 1:
                continue
            d = 1 if sess["s1"].iloc[i] > 0 else -1
            imp = _impulse_row(op, hi, lo, cl, i, d)
            if imp is None:
                continue
            row = {"instrument": instrument, "session_date": sd,
                   "ts_event": sess["ts_event"].iloc[i], "et_minute": int(sess["et_minute"].iloc[i]),
                   "segment": sess["segment"].iloc[i], "direction": d,
                   "zmod1_abs": abs(sess["z_mod1"].iloc[i]),
                   "zatr1_abs": abs(sess["z_atr1"].iloc[i]),
                   "dev_g_signed": d * sess["dev_g"].iloc[i] if sess["vwap_g_valid"].iloc[i] else np.nan,
                   "vwap_g_valid": bool(sess["vwap_g_valid"].iloc[i]),
                   "dev_r_signed": d * sess["dev_r"].iloc[i] if sess["vwap_r_valid"].iloc[i] else np.nan,
                   "vwap_r_valid": bool(sess["vwap_r_valid"].iloc[i])}
            row.update(imp)
            row.update(_acceptance_strength(hi, lo, cl, vw, sg, vok, i, d, n))
            rows.append(row)
    df = pd.DataFrame(rows)
    df.attrs["z_thr_top10"] = float(thr)
    return df


def main(instrument):
    feat = pd.read_parquet(os.path.join(OUT, f"{instrument.lower()}_features_dev.parquet"))
    assert feat["session_date"].max() <= pd.Timestamp("2022-12-31"), "partition breach"
    led = build_extremity_ledger(feat, instrument)
    p = os.path.join(OUT, f"{instrument.lower()}_extremity_dev.parquet")
    led.to_parquet(p, index=False)
    print(f"{instrument}: {len(led)} impulses, top10 thr={led.attrs['z_thr_top10']:.3f}", flush=True)


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
