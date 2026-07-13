"""ES-NQ confirmation: secondary diagnostic only.
See SPEC_SWEEP_FAILURE.md section 13.
"""
import numpy as np
import pandas as pd

BREACH_CLASSES = (
    "FAILED_BREACH_1MIN", "FAILED_BREACH_2MIN", "FAILED_BREACH_3MIN",
    "SUCCESSFUL_BREACH_CONTROL", "DELAYED_FAILURE_CONTROL",
    "NEITHER_RESOLVED_WITHIN_10MIN", "INCOMPLETE_EPISODE",
)

WINDOW = pd.Timedelta(minutes=1)


def _event_ts(ev: dict):
    if ev["event_class"] == "TOUCH_WITHOUT_BREACH":
        return ev["touch_ts"]
    return ev.get("breach_ts")


def add_confirmation(events_a: list, events_b: list) -> list:
    """events_a: events to annotate; events_b: paired instrument's events."""
    by_level_b = {}
    for ev in events_b:
        by_level_b.setdefault((ev["level_type"], ev["side"]), []).append(ev)
    for key, lst in by_level_b.items():
        lst.sort(key=lambda e: _event_ts(e))

    out = []
    for ev in events_a:
        row = dict(ev)
        ts = _event_ts(ev)
        candidates = by_level_b.get((ev["level_type"], ev["side"]), [])
        lo, hi = pd.Timestamp(ts) - WINDOW, pd.Timestamp(ts) + WINDOW
        breach_found, touch_found = False, False
        for cand in candidates:
            cts = pd.Timestamp(_event_ts(cand))
            if lo <= cts <= hi:
                if cand["event_class"] in BREACH_CLASSES:
                    breach_found = True
                    break
                if cand["event_class"] == "TOUCH_WITHOUT_BREACH":
                    touch_found = True
        if breach_found:
            row["confirmation"] = "CONFIRMED_BREACH"
        elif touch_found:
            row["confirmation"] = "PARTIAL_CONFIRMATION"
        else:
            row["confirmation"] = "UNCONFIRMED_BREACH"
        out.append(row)
    return out
