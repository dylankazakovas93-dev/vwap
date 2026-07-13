"""Four profile mappings, kept separate. See SPEC_AUCTION_VALUE.md section 2.
"""
import bisect

import pandas as pd

from . import profiles as prof


def build_all_profiles(leg_df: pd.DataFrame, config: dict) -> dict:
    """Returns {session_leg_id: profile_dict} for every complete leg instance."""
    out = {}
    complete = leg_df.loc[leg_df["leg_complete"]]
    for leg_id, g in complete.groupby("session_leg_id", sort=False):
        g = g.sort_values("local_rank")
        p = prof.build_profile(g, **config)
        p["session_leg_id"] = leg_id
        p["session_date"] = g["session_date"].iloc[0]
        p["leg"] = g["leg"].iloc[0]
        p["completion_ts"] = g["ts_event"].max() + pd.Timedelta(minutes=1)
        out[leg_id] = p
    return out


def _leg_instances_by_type(leg_df: pd.DataFrame, leg_name: str):
    ids = leg_df.loc[(leg_df["leg"] == leg_name) & leg_df["leg_complete"], "session_leg_id"].unique()
    sub = leg_df.loc[leg_df["session_leg_id"].isin(ids)]
    dates = sub.groupby("session_leg_id")["session_date"].first().sort_values()
    return list(zip(dates.index.tolist(), dates.tolist()))  # [(session_leg_id, session_date), ...] sorted


def build_mappings(leg_df: pd.DataFrame, profiles: dict) -> dict:
    """Returns {mapping_id: DataFrame[target_session_leg_id, source_session_leg_id,
    poc, vah, val, va_width, completion_ts, expiry_ts]}."""
    asia = _leg_instances_by_type(leg_df, "ASIA")
    london = _leg_instances_by_type(leg_df, "LONDON")
    ny = _leg_instances_by_type(leg_df, "NEW_YORK_RTH")

    ny_by_date = {d: lid for lid, d in ny}
    ny_dates_sorted = sorted(ny_by_date.keys())

    target_expiry = {}
    for lid, g in leg_df.groupby("session_leg_id", sort=False):
        if g["leg_complete"].iloc[0]:
            target_expiry[lid] = g["ts_event"].max() + pd.Timedelta(minutes=1)

    def make_rows(mapping_id, target_list, source_lookup_fn):
        rows = []
        for target_lid, target_date in target_list:
            source_lid = source_lookup_fn(target_date)
            if source_lid is None or source_lid not in profiles or target_lid not in target_expiry:
                continue
            p = profiles[source_lid]
            rows.append({
                "mapping_id": mapping_id, "target_session_leg_id": target_lid,
                "target_session_date": target_date, "source_session_leg_id": source_lid,
                "poc": p["poc"], "vah": p["vah"], "val": p["val"], "va_width": p["va_width"],
                "completion_ts": p["completion_ts"], "expiry_ts": target_expiry[target_lid],
            })
        return pd.DataFrame(rows)

    # mapping 1: ASIA -> LONDON, same session_date
    asia_by_date = {d: lid for lid, d in asia}
    m1 = make_rows("M1_ASIA_TO_LONDON", london, lambda d: asia_by_date.get(d))

    # mapping 2: LONDON -> NEW_YORK_RTH, same session_date
    london_by_date = {d: lid for lid, d in london}
    m2 = make_rows("M2_LONDON_TO_NY", ny, lambda d: london_by_date.get(d))

    # mapping 3: NEW_YORK_RTH -> next ASIA (nearest prior RTH session_date)
    def prior_ny(target_date):
        i = bisect.bisect_left(ny_dates_sorted, target_date)
        if i == 0:
            return None
        return ny_by_date[ny_dates_sorted[i - 1]]

    m3 = make_rows("M3_RTH_TO_OVERNIGHT", asia, prior_ny)

    # mapping 4: NEW_YORK_RTH -> next NEW_YORK_RTH (nearest prior RTH session_date)
    m4 = make_rows("M4_RTH_TO_NEXT_RTH", ny, prior_ny)

    return {"M1_ASIA_TO_LONDON": m1, "M2_LONDON_TO_NY": m2, "M3_RTH_TO_OVERNIGHT": m3, "M4_RTH_TO_NEXT_RTH": m4}
