"""Flatten the master excursion/acceptance ledger into one row per
(excursion, rule) and apply the 432-cell A x B x C x D x E grid as
boolean filters. See SPEC_AUCTION_VALUE.md section 4.
"""
import numpy as np

TICK = 0.25

A_BREACH_DEPTH = ("A_GE_1_TICK", "A_GE_5PCT_VA", "A_GE_10PCT_VA")
B_MAX_BARS_OUTSIDE = (1, 3, 5)
C_RULES = ("R1_ONE_CLOSE", "R2_TWO_CONSECUTIVE_CLOSES", "R3_TWO_OF_THREE_CLOSES", "R4_DEPTH_ACCEPTANCE")
D_POC_DISTANCE = (0.00, 0.10, 0.20)
E_FRESHNESS_HOURS = (2.0, 4.0, 6.0, None)  # None = no cap beyond mapping's own expiry_ts

GRID_SIZE = len(A_BREACH_DEPTH) * len(B_MAX_BARS_OUTSIDE) * len(C_RULES) * len(D_POC_DISTANCE) * len(E_FRESHNESS_HOURS)
assert GRID_SIZE == 432


def flatten_ledger(excursion_rows: list) -> list:
    """One row per (excursion, rule) where that rule produced a
    confirmation (i.e. a canonical failed-discovery + reacceptance
    candidate). Non-breach and unconfirmed rows contribute nothing."""
    out = []
    for ev in excursion_rows:
        if ev.get("interaction_kind") != "BREACH":
            continue
        rules = ev.get("rules") or {}
        for rule, r in rules.items():
            if r is None:
                continue
            row = {k: v for k, v in ev.items() if k != "rules"}
            row["rule"] = rule
            row.update(r)
            out.append(row)
    return out


def _passes_a(row, a):
    depth_ticks = row["breach_depth_ticks"]
    depth_pct_va = row["breach_depth_pct_va"]
    if a == "A_GE_1_TICK":
        return depth_ticks >= 1 - 1e-9
    if a == "A_GE_5PCT_VA":
        return depth_pct_va >= 0.05 - 1e-9
    if a == "A_GE_10PCT_VA":
        return depth_pct_va >= 0.10 - 1e-9
    raise ValueError(a)


def _passes_b(row, b):
    return row["bars_outside"] <= b


def _passes_d(row, d):
    return row["poc_distance_pct"] >= d - 1e-9


def _passes_e(row, e):
    if e is None:
        return True
    return row["freshness_hours"] <= e + 1e-9


def apply_cell(flat_rows: list, a, b, c, d, e) -> list:
    """Filter the flattened ledger down to exactly the events belonging
    to one of the 432 grid cells (single acceptance rule `c`)."""
    return [
        r for r in flat_rows
        if r["rule"] == c and _passes_a(r, a) and _passes_b(r, b) and _passes_d(r, d) and _passes_e(r, e)
    ]


def iter_grid_cells():
    for a in A_BREACH_DEPTH:
        for b in B_MAX_BARS_OUTSIDE:
            for c in C_RULES:
                for d in D_POC_DISTANCE:
                    for e in E_FRESHNESS_HOURS:
                        yield a, b, c, d, e
