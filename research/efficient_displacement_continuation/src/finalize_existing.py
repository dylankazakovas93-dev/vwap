from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import primary_table

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research/efficient_displacement_continuation/outputs"

def main():
    events = pd.concat([pd.read_csv(OUT / f"{i.lower()}_three_minute_impulse_ledger.csv") for i in ("ES", "NQ")], ignore_index=True)
    barriers = pd.concat([pd.read_csv(OUT / f"{i.lower()}_barrier_first_ledger.csv") for i in ("ES", "NQ")], ignore_index=True)
    conf = pd.read_csv(OUT / "es_nq_confirmation_ledger.csv")
    barriers = barriers.merge(conf[["event_id", "confirmation"]], on="event_id", how="left")
    primary, eligible = primary_table(events, barriers)
    primary.to_csv(OUT / "primary_matched_comparison.csv", index=False)
    barriers.to_csv(OUT / "full_exploratory_table.csv", index=False)
    y = eligible[eligible.barrier_multiple == .5].merge(events[["event_id", "signed_close_5", "signed_close_10", "signed_close_15", "signed_close_30"]], on="event_id", how="left")
    y["year"] = pd.to_datetime(y.session_date).dt.year; y["cont"] = (y.outcome == "CONTINUATION_FIRST").astype(int)
    ys = y.groupby(["instrument", "session", "direction", "year", "state"], as_index=False).agg(n=("event_id", "size"), continuation_rate=("cont", "mean"), median_signed_close=("signed_close_15", "median"))
    piv = ys.pivot_table(index=["instrument", "session", "direction", "year"], columns="state", values=["n", "continuation_rate", "median_signed_close"])
    yr = piv.reset_index()
    for metric in ("n", "continuation_rate", "median_signed_close"):
        e = (metric, "EFFICIENT_DISPLACEMENT"); i = (metric, "INEFFICIENT_DISPLACEMENT_CONTROL")
        if e in yr.columns and i in yr.columns: yr[f"efficient_minus_inefficient_{metric}"] = yr[e] - yr[i]
    yr.columns = [a if not b or str(b) == "nan" else f"{a}_{b}" for a, b in yr.columns]
    yr.to_csv(OUT / "year_stability_table.csv", index=False)
    adjacent = []
    for h in (5, 10, 15, 30):
        x = y[y[f"signed_close_{h}"].notna()].copy()
        def horizon_outcome(r):
            c, rev = r.continuation_first_bar, r.reversal_first_bar
            if pd.notna(c) and c <= h and (pd.isna(rev) or c < rev): return "CONTINUATION_FIRST"
            if pd.notna(rev) and rev <= h and (pd.isna(c) or rev < c): return "REVERSAL_FIRST"
            if pd.notna(c) and pd.notna(rev) and c == rev and c <= h: return "SAME_BAR_TIE"
            return "NEITHER"
        x["outcome_h"] = x.apply(horizon_outcome, axis=1)
        for key, g in x.groupby(["instrument", "session", "direction"], sort=True):
            e = g[g.state == "EFFICIENT_DISPLACEMENT"]; q = g[g.state == "INEFFICIENT_DISPLACEMENT_CONTROL"]
            en = e[e.outcome_h.isin(["CONTINUATION_FIRST", "REVERSAL_FIRST"])]
            qn = q[q.outcome_h.isin(["CONTINUATION_FIRST", "REVERSAL_FIRST"])]
            er = (en.outcome_h == "CONTINUATION_FIRST").mean() if len(en) else float("nan")
            qr = (qn.outcome_h == "CONTINUATION_FIRST").mean() if len(qn) else float("nan")
            adjacent.append({"instrument": key[0], "session": key[1], "direction": key[2], "horizon": h,
                             "n_efficient": len(e), "n_inefficient": len(q), "non_tied_efficient": len(en),
                             "non_tied_inefficient": len(qn), "efficient_continuation_rate": er,
                             "inefficient_continuation_rate": qr, "difference": er - qr})
    pd.DataFrame(adjacent).to_csv(OUT / "adjacent_horizon_table.csv", index=False)
    barriers[barriers.barrier_multiple == .5].groupby(["instrument","confirmation","state","outcome"], dropna=False).size().reset_index(name="n").to_csv(OUT / "cross_market_confirmation_table.csv", index=False)
    primary[primary.classification == "MIXED_OR_NULL"].to_csv(OUT / "null_inventory.csv", index=False)
    primary[primary.classification == "UNDERPOWERED"].to_csv(OUT / "underpowered_inventory.csv", index=False)
    counts = events.groupby(["instrument","session","state"], dropna=False).size().reset_index(name="n")
    (OUT / "EFFICIENT_DISPLACEMENT_REPORT.md").write_text("\n".join([
        "# Efficient displacement continuation — frozen 2018–2022 development study", "",
        "This report is descriptive and contains no trading simulation.", "",
        "## Answers", "",
        "1. The answer is determined by the sign, size, and corrected significance of the size-matched efficient-minus-inefficient continuation difference in the primary table.",
        "2. Upward and downward impulses are reported separately.",
        "3. Asia, London, and New York are reported separately.",
        "4. ES/NQ agreement is reported in the cross-market confirmation table.",
        "5. Confirmation is secondary and is not promoted unless the frozen strengthening criteria are met.", "",
        "## Sample accounting", "", "```", counts.to_string(index=False), "```", "", "## Primary results", "", "```", primary.to_string(index=False), "```"
    ]))
    print(primary.to_string(index=False))
if __name__ == "__main__": main()
