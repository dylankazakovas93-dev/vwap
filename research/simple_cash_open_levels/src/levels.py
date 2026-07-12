"""Level construction -- SPEC_SIMPLE_LEVELS.md Families A and B. No
synthetic controls, no taxonomy conditioning, self-contained (does not
import generations 6-8, or generation 3's atlas.py directly).
"""
import os

import numpy as np
import pandas as pd

OPEN_MINUTE = 570          # 09:30 ET
RTH_END_MINUTE = 959         # 15:59 ET (last RTH minute, inclusive)
MIN_OVERNIGHT_BARS = 30

VWAP_J = (-3, -2, -1, 0, 1, 2, 3)
LOOKBACKS = (5, 10, 20)
CENTERS = ("mean", "median", "ema")
K_RUNGS = (0, 1, 2, 3)

DEV_START = pd.Timestamp("2018-01-01")
DEV_END = pd.Timestamp("2022-12-31")


def load_dev(instrument: str, proc_dir: str) -> pd.DataFrame:
    df = pd.read_parquet(os.path.join(proc_dir, f"{instrument.lower()}_front_1m.parquet"))
    df = df[(df["session_date"] >= DEV_START) & (df["session_date"] <= DEV_END)].copy()
    assert df["session_date"].min() >= DEV_START and df["session_date"].max() <= DEV_END, "partition breach"
    return df


# ---------------------------------------------------------- VWAP families --
def _vwap_sd(sub: pd.DataFrame, group_col: str = "session_date") -> pd.DataFrame:
    sub = sub.copy()
    sub["p"] = (sub["high"] + sub["low"] + sub["close"]) / 3.0
    g = sub.groupby(group_col, sort=True)
    n_bars = g.size()
    sum_v = g["volume"].sum()
    sum_vp = (sub["volume"] * sub["p"]).groupby(sub[group_col]).sum()
    sum_vp2 = (sub["volume"] * sub["p"] ** 2).groupby(sub[group_col]).sum()
    vwap = sum_vp / sum_v
    var = sum_vp2 / sum_v - vwap ** 2
    sd = np.sqrt(var.clip(lower=0.0))
    return pd.DataFrame({"n_bars": n_bars, "sum_vol": sum_v, "vwap": vwap, "sd": sd})


def build_family_a1_overnight(df: pd.DataFrame) -> pd.DataFrame:
    """A1: overnight-session VWAP. Window = bars with et_minute<570 for that
    session_date (Globex-overnight-leg convention, handles midnight wrap
    via session_date already resolved in generation 1's processed data).
    Valid only if >=30 bars and total volume > 0."""
    sub = df[df["et_minute"] < OPEN_MINUTE]
    stats = _vwap_sd(sub)
    valid = (stats["n_bars"] >= MIN_OVERNIGHT_BARS) & (stats["sum_vol"] > 0)
    vwap = stats["vwap"].where(valid)
    sd = stats["sd"].where(valid)
    out = pd.DataFrame({"VWAP_ON": vwap, "SD_ON": sd, "n_overnight_bars": stats["n_bars"]})
    for j in VWAP_J:
        out[f"ON_VWAP_{_jname(j)}"] = vwap + j * sd
    return out


def build_family_a2_prior_rth(df: pd.DataFrame) -> pd.DataFrame:
    """A2: prior-RTH VWAP. Uses the immediately preceding session's full
    RTH window (570-959) ONLY if that session is not an early close (no
    substitution to a more distant predecessor)."""
    rth = df[(df["et_minute"] >= OPEN_MINUTE) & (df["et_minute"] <= RTH_END_MINUTE)]
    stats = _vwap_sd(rth)
    max_minute = rth.groupby("session_date")["et_minute"].max()
    sessions = stats.copy()
    sessions["max_minute"] = max_minute
    sessions = sessions.sort_index()
    sessions["is_early_close"] = sessions["max_minute"] < RTH_END_MINUTE

    prior_vwap = sessions["vwap"].shift(1)
    prior_sd = sessions["sd"].shift(1)
    prior_is_early = sessions["is_early_close"].shift(1).fillna(True).astype(bool)

    vwap = prior_vwap.where(~prior_is_early)
    sd = prior_sd.where(~prior_is_early)
    out = pd.DataFrame(index=sessions.index)
    out["VWAP_PR"] = vwap
    out["SD_PR"] = sd
    out["prior_is_early_close"] = prior_is_early
    for j in VWAP_J:
        out[f"PR_VWAP_{_jname(j)}"] = vwap + j * sd
    return out


def _jname(j: int) -> str:
    if j == 0:
        return "0"
    return f"m{abs(j)}" if j < 0 else f"p{j}"


# ------------------------------------------------------- excursion family --
def _ewm_last(x: np.ndarray, span: int) -> float:
    """Final value of ewm(span=span, adjust=False).mean() over x (oldest
    to newest), computed fresh over exactly this window -- not a
    continuously-updated EMA across the whole history."""
    alpha = 2.0 / (span + 1.0)
    y = x[0]
    for v in x[1:]:
        y = alpha * v + (1 - alpha) * y
    return y


def build_family_b_excursions(df: pd.DataFrame) -> pd.DataFrame:
    """B: historical 09:30-candle excursion levels. U_i/D_i use ONLY the
    single 09:30 bar of prior session i. Exact-N causal lookback (5/10/20),
    no expanding/partial-window fallback; one shared raw sample SD per
    side/lookback reused across mean/median/EMA centers."""
    sub = df[df["et_minute"] == OPEN_MINUTE][["session_date", "open", "high", "low"]].copy()
    sub = sub.drop_duplicates("session_date").sort_values("session_date").reset_index(drop=True)
    sub["U"] = sub["high"] - sub["open"]
    sub["D"] = sub["open"] - sub["low"]
    sub = sub.set_index("session_date")

    out = pd.DataFrame(index=sub.index)
    out["O_0930"] = sub["open"]
    out["U_0930"] = sub["U"]
    out["D_0930"] = sub["D"]

    for side, raw in (("U", sub["U"]), ("D", sub["D"])):
        for N in LOOKBACKS:
            roll = raw.rolling(N, min_periods=N)
            out[f"CENTER_{side}_mean_N{N}"] = roll.mean().shift(1)
            out[f"CENTER_{side}_median_N{N}"] = roll.median().shift(1)
            out[f"CENTER_{side}_ema_N{N}"] = raw.rolling(N, min_periods=N).apply(
                lambda a, span=N: _ewm_last(a, span), raw=True).shift(1)
            out[f"SD_{side}_N{N}"] = roll.std(ddof=1).shift(1)

    O = out["O_0930"]
    for N in LOOKBACKS:
        for center in CENTERS:
            cu = out[f"CENTER_U_{center}_N{N}"]
            cd = out[f"CENTER_D_{center}_N{N}"]
            su = out[f"SD_U_N{N}"]
            sd = out[f"SD_D_N{N}"]
            for k in K_RUNGS:
                out[f"upper_N{N}_{center}_k{k}"] = O + cu + k * su
                out[f"lower_N{N}_{center}_k{k}"] = O - cd - k * sd
    return out


# -------------------------------------------------------- level inventory --
def family_a_level_ids():
    return [f"ON_VWAP_{_jname(j)}" for j in VWAP_J] + [f"PR_VWAP_{_jname(j)}" for j in VWAP_J]


def family_b_level_ids():
    ids = []
    for N in LOOKBACKS:
        for center in CENTERS:
            for k in K_RUNGS:
                ids.append(f"upper_N{N}_{center}_k{k}")
    for N in LOOKBACKS:
        for center in CENTERS:
            for k in K_RUNGS:
                ids.append(f"lower_N{N}_{center}_k{k}")
    return ids


def all_level_ids():
    return family_a_level_ids() + family_b_level_ids()


LEVEL_META = {}
for j in VWAP_J:
    LEVEL_META[f"ON_VWAP_{_jname(j)}"] = ("family_a1_overnight_vwap", "overnight_vwap", None, None, j)
    LEVEL_META[f"PR_VWAP_{_jname(j)}"] = ("family_a2_prior_rth_vwap", "prior_rth_vwap", None, None, j)
for N in LOOKBACKS:
    for center in CENTERS:
        for k in K_RUNGS:
            LEVEL_META[f"upper_N{N}_{center}_k{k}"] = ("family_b_excursion", "upper_09_30_excursion", N, center, k)
            LEVEL_META[f"lower_N{N}_{center}_k{k}"] = ("family_b_excursion", "lower_09_30_excursion", N, center, k)

assert len(family_a_level_ids()) == 14
assert len(family_b_level_ids()) == 72
assert len(all_level_ids()) == 86
