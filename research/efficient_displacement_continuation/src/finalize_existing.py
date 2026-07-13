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
    y = eligible[eligible.barrier_multiple == .5].merge(events[["event_id", "signed_close_15"]], on="event_id", how="left")
    y["year"] = pd.to_datetime(y.session_date).dt.year; y["cont"] = (y.outcome == "CONTINUATION_FIRST").astype(int)
    ys = y.groupby(["instrument", "session", "direction", "year", "state"], as_index=False).agg(n=("event_id", "size"), continuation_rate=("cont", "mean"), median_signed_close=("signed_close_15", "median"))
    piv = ys.pivot_table(index=["instrument", "session", "direction", "year"], columns="state", values=["n", "continuation_rate", "median_signed_close"])
    yr = piv.reset_index()
    for metric in ("n", "continuation_rate", "median_signed_close"):
        e = (metric, "EFFICIENT_DISPLACEMENT"); i = (metric, "INEFFICIENT_DISPLACEMENT_CONTROL")
        if e in yr.columns and i in yr.columns: yr[f"efficient_minus_inefficient_{metric}"] = yr[e] - yr[i]
    yr.to_csv(OUT / "year_stability_table.csv", index=False)
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
