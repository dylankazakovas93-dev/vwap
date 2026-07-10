"""Event grid, forward outcomes, first passage, VWAP acceptance (Stage 2).

Events are identified at the close of bar t only. Forward outcomes are
measured from the open of bar t+1 (and from the open of the acceptance
decision bar + 1 where applicable), always within the same session.
"""
import numpy as np
import pandas as pd

HORIZONS = (1, 5, 15, 30, 60)
MAEMFE_WIN = 60
FP_WIN = 120
FP_X_ATR = 1.0
ACCEPT = {"A1": (2, 3), "A2": (3, 5)}
BAND_OUT = 2.0
BAND_IN = 1.0


def _forward_block(op, hi, lo, cl, i, d):
    """Forward outcomes from open of bar i+1, direction d. Arrays are one
    session. Returns dict."""
    n = len(cl)
    out = {}
    if i + 1 >= n:
        return None
    entry = op[i + 1]
    out["entry_price"] = entry
    for h in HORIZONS:
        j = i + h
        out[f"fret_{h}"] = (cl[j] - entry) * d if j < n else np.nan
    # MAE/MFE over bars i+1 .. i+MAEMFE_WIN
    j2 = min(n, i + 1 + MAEMFE_WIN)
    hs = hi[i + 1:j2]
    ls = lo[i + 1:j2]
    if len(hs):
        # signed favourable/adverse excursions
        if d > 0:
            fav = hs - entry
            adv = entry - ls
        else:
            fav = entry - ls
            adv = hs - entry
        out["mfe"] = float(np.max(fav))
        out["mae"] = float(np.max(adv))
        out["t_mfe"] = int(np.argmax(fav)) + 1
        out["t_mae"] = int(np.argmax(adv)) + 1
    else:
        out["mfe"] = out["mae"] = out["t_mfe"] = out["t_mae"] = np.nan
    return out


def _first_passage(op, hi, lo, i, d, x):
    """Symmetric first passage +-x from open of i+1. Conservative: both
    barriers touched in one bar => AMBIG (counted against continuation
    downstream). Returns (outcome, bars_to_outcome)."""
    n = len(hi)
    if i + 1 >= n or not np.isfinite(x) or x <= 0:
        return "INVALID", np.nan
    entry = op[i + 1]
    up, dn = entry + x, entry - x
    j2 = min(n, i + 1 + FP_WIN)
    for j in range(i + 1, j2):
        hit_up = hi[j] >= up
        hit_dn = lo[j] <= dn
        if hit_up and hit_dn:
            return "AMBIG", j - i
        if hit_up:
            return ("CONT" if d > 0 else "REV"), j - i
        if hit_dn:
            return ("CONT" if d < 0 else "REV"), j - i
    return "NONE", np.nan


def _acceptance(cl, vwap, sig, valid, i, d, n_sess):
    """A1/A2 acceptance + rejection + reclaim timing after event bar i."""
    res = {}
    dev_evt = d * (cl[i] - vwap[i]) / sig[i] if valid[i] else np.nan
    res["dev_evt_signed"] = dev_evt
    eligible = np.isfinite(dev_evt) and dev_evt >= BAND_OUT
    res["accept_eligible"] = bool(eligible)
    # reclaim: first bar j>i with close inside the inner band (side-d metric)
    reclaim_t = np.nan
    j2 = min(n_sess, i + 1 + FP_WIN)
    for j in range(i + 1, j2):
        if not valid[j]:
            continue
        if d * (cl[j] - vwap[j]) < BAND_IN * sig[j]:
            reclaim_t = j - i
            break
    res["reclaim_t"] = reclaim_t
    for name, (m, nwin) in ACCEPT.items():
        if not eligible or i + nwin >= n_sess:
            res[f"{name}_status"] = "NA"
            continue
        beyond = 0
        reclaimed = False
        for j in range(i + 1, i + 1 + nwin):
            if not valid[j]:
                continue
            dv = d * (cl[j] - vwap[j])
            if dv >= BAND_OUT * sig[j]:
                beyond += 1
            if dv < BAND_IN * sig[j]:
                reclaimed = True
        if reclaimed:
            res[f"{name}_status"] = "REJECT"
        elif beyond >= m:
            res[f"{name}_status"] = "ACCEPT"
        else:
            res[f"{name}_status"] = "INDET"
        res[f"{name}_decision_bar"] = nwin
    return res


def build_event_ledger(feat: pd.DataFrame, k: int, z_thr: float,
                       instrument: str, mask: pd.Series = None) -> pd.DataFrame:
    """One row per event bar (|z_mod{k}| >= z_thr, valid features).

    If `mask` is given (boolean, aligned with feat), it replaces the
    z-threshold trigger (used for matched placebo bars); direction is then
    the sign of the bar's own s_k."""
    zc = f"z_mod{k}"
    if mask is None:
        ev_mask = feat[zc].abs() >= z_thr
    else:
        sc = f"s{k}"
        ev_mask = mask & (feat[sc] != 0) & feat[sc].notna()
    ev_mask &= feat["atr30"].notna()
    feat = feat.copy()
    feat["_evmask"] = ev_mask.fillna(False)
    rows = []
    cols_np = ["open", "high", "low", "close", "vwap_g", "sig_g"]
    for sd, sess in feat[feat["session_date"].isin(
            feat.loc[feat["_evmask"], "session_date"].unique())].groupby("session_date", sort=True):
        sess = sess.reset_index(drop=True)
        op, hi, lo, cl, vw, sg = (sess[c].to_numpy(float) for c in cols_np)
        vgood = sess["vwap_g_valid"].to_numpy(bool)
        vw_r, sg_r = sess["vwap_r"].to_numpy(float), sess["sig_r"].to_numpy(float)
        vgood_r = sess["vwap_r_valid"].to_numpy(bool)
        n = len(sess)
        emask = sess["_evmask"]
        for i in np.flatnonzero(emask.to_numpy()):
            d = 1 if sess[f"s{k}"].iloc[i] > 0 else -1
            fb = _forward_block(op, hi, lo, cl, i, d)
            if fb is None:
                continue
            x = FP_X_ATR * sess["atr30"].iloc[i]
            fp, fp_t = _first_passage(op, hi, lo, i, d, x)
            acc_g = _acceptance(cl, vw, sg, vgood, i, d, n)
            acc_r = _acceptance(cl, vw_r, sg_r, vgood_r, i, d, n)
            row = {
                "instrument": instrument, "session_date": sd,
                "ts_event": sess["ts_event"].iloc[i], "bar_idx": i,
                "symbol": sess["symbol"].iloc[i], "k": k, "z_thr": z_thr,
                "direction": d, "segment": sess["segment"].iloc[i],
                "macro_window": bool(sess["macro_window"].iloc[i]),
                "roll_session": bool(sess["roll"].iloc[i]),
                "fp_outcome": fp, "fp_bars": fp_t, "atr30": sess["atr30"].iloc[i],
            }
            row.update(fb)
            for cname in ("z_mod1", "z_mod3", "z_atr1", "z_atr3", "z_vol",
                          "vol_ratio", "runlen_prev", "runsign_prev",
                          "vwap_g_slope10", "dev_g", "dev_r"):
                row[cname] = sess[cname].iloc[i]
            row["body_eff"] = sess[f"body_eff{k}"].iloc[i]
            clu = sess[f"closeloc_up{k}"].iloc[i]
            row["closeloc_dir"] = clu if d > 0 else (1 - clu if np.isfinite(clu) else np.nan)
            for L in (5, 15, 60):
                DL = sess[f"D{L}"].iloc[i]
                agree = bool(np.sign(DL) == d) if np.isfinite(DL) and DL != 0 else None
                row[f"D{L}_atr"] = sess[f"D{L}_atr"].iloc[i]
                row[f"D{L}_atr_d"] = sess[f"D{L}_atr"].iloc[i] * d
                PL, EL = sess[f"P{L}"].iloc[i], sess[f"E{L}"].iloc[i]
                if agree is None:
                    row[f"P{L}_d"] = np.nan
                    row[f"E{L}_d"] = np.nan
                else:
                    row[f"P{L}_d"] = PL if agree else (1 - PL)
                    row[f"E{L}_d"] = EL if agree else -EL
            rs = row["runsign_prev"]
            row["run_d"] = row["runlen_prev"] * d * (rs if np.isfinite(rs) else 0) if np.isfinite(row["runlen_prev"]) else np.nan
            row["dev_g_d"] = row["dev_g"] * d if np.isfinite(row["dev_g"]) else np.nan
            row["dev_r_d"] = row["dev_r"] * d if np.isfinite(row["dev_r"]) else np.nan
            row["slope_d"] = row["vwap_g_slope10"] * d if np.isfinite(row["vwap_g_slope10"]) else np.nan
            for pfx, acc in (("g", acc_g), ("r", acc_r)):
                for kk, vv in acc.items():
                    row[f"{pfx}_{kk}"] = vv
            # forward outcomes from acceptance decision bar (Globex, A1/A2)
            for name, (m, nwin) in ACCEPT.items():
                st = acc_g.get(f"{name}_status")
                if st in ("ACCEPT", "REJECT"):
                    di = i + nwin  # decision bar index
                    fb2 = _forward_block(op, hi, lo, cl, di, d)
                    fp2, fp2_t = _first_passage(op, hi, lo, di, d, x)
                    if fb2 is not None:
                        row[f"{name}_post_fret_15"] = fb2.get("fret_15")
                        row[f"{name}_post_fret_30"] = fb2.get("fret_30")
                        row[f"{name}_post_fret_60"] = fb2.get("fret_60")
                        row[f"{name}_post_fp"] = fp2
            rows.append(row)
    return pd.DataFrame(rows)
