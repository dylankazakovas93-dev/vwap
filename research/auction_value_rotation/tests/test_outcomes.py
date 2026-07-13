import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from research.auction_value_rotation.src import outcomes as out


def make_series(rows, start="2024-01-02 09:30"):
    ts = pd.date_range(start, periods=len(rows), freq="1min", tz="UTC")
    df = pd.DataFrame({
        "ts_event": ts, "low": [r[0] for r in rows], "high": [r[1] for r in rows],
        "close": [r[2] for r in rows],
    })
    return out.GlobalSeries(df), ts


def test_poc_first_beats_rediscovery():
    # anchor at idx0 (confirmation bar), level=100.0, poc=101.0, excursion_extreme=99.5 (long)
    rows = [(100.2, 100.3, 100.25)] + [(100.3, 100.4, 100.35)] * 3 + [(100.9, 101.1, 101.0)] + [(101.0, 101.2, 101.1)] * 15
    series, ts = make_series(rows)
    ev = [{"confirmation_ts": ts[0], "level": 100.0, "poc": 101.0, "side": "long", "excursion_extreme": 99.5}]
    result = out.add_primary_outcomes(ev, series)
    assert result[0]["outcome_h15"] == "POC_FIRST"


def test_rediscovery_first_beats_poc():
    rows = [(100.2, 100.3, 100.25)] + [(99.4, 99.6, 99.5)] + [(99.0, 99.2, 99.1)] * 16
    series, ts = make_series(rows)
    ev = [{"confirmation_ts": ts[0], "level": 100.0, "poc": 105.0, "side": "long", "excursion_extreme": 99.5}]
    result = out.add_primary_outcomes(ev, series)
    # bar1: close=99.5 < level(100.0) -> redis_hit; poc(105) never reached
    assert result[0]["outcome_h15"] == "REDISCOVERY_FIRST"


def test_same_bar_ambiguous():
    # single bar range covers both poc and triggers rediscovery close
    rows = [(100.2, 100.3, 100.25)] + [(99.0, 101.5, 99.5)] + [(99.0, 99.2, 99.1)] * 16
    series, ts = make_series(rows)
    ev = [{"confirmation_ts": ts[0], "level": 100.0, "poc": 101.0, "side": "long", "excursion_extreme": 99.5}]
    result = out.add_primary_outcomes(ev, series)
    assert result[0]["outcome_h15"] == "SAME_BAR_AMBIGUOUS"


def test_neither_when_flat():
    rows = [(100.2, 100.3, 100.25)] + [(100.2, 100.3, 100.25)] * 20
    series, ts = make_series(rows)
    ev = [{"confirmation_ts": ts[0], "level": 100.0, "poc": 105.0, "side": "long", "excursion_extreme": 99.0}]
    result = out.add_primary_outcomes(ev, series)
    assert result[0]["outcome_h15"] == "NEITHER"


def test_incomplete_horizon_near_series_end():
    rows = [(100.2, 100.3, 100.25)] * 5
    series, ts = make_series(rows)
    ev = [{"confirmation_ts": ts[0], "level": 100.0, "poc": 105.0, "side": "long", "excursion_extreme": 99.0}]
    result = out.add_primary_outcomes(ev, series)
    assert result[0]["outcome_h15"] == "INCOMPLETE_HORIZON"


def test_short_side_mirrors_long():
    # short: success = poc touched; failure = close back above level OR trade above excursion_extreme(high)
    rows = [(99.7, 99.8, 99.75)] + [(99.6, 99.7, 99.65)] * 3 + [(98.9, 99.1, 99.0)] + [(98.8, 99.0, 98.9)] * 15
    series, ts = make_series(rows)
    ev = [{"confirmation_ts": ts[0], "level": 100.0, "poc": 99.0, "side": "short", "excursion_extreme": 100.5}]
    result = out.add_primary_outcomes(ev, series)
    assert result[0]["outcome_h15"] == "POC_FIRST"


def test_no_lookahead_confirmation_bar_excluded():
    # confirmation bar itself touches poc, but outcome measurement starts at confirmation_idx+1
    rows = [(100.9, 101.1, 101.0)] + [(99.0, 99.2, 99.1)] * 16
    series, ts = make_series(rows)
    ev = [{"confirmation_ts": ts[0], "level": 100.0, "poc": 101.0, "side": "long", "excursion_extreme": 99.0}]
    result = out.add_primary_outcomes(ev, series)
    # bar0 (confirmation bar) is never scanned; from bar1 onward all bars are 99.x -> redis_hit immediately
    assert result[0]["outcome_h15"] == "REDISCOVERY_FIRST"


def test_opposite_edge_completion_only_for_poc_first():
    rows = [(100.2, 100.3, 100.25)] + [(100.9, 101.1, 101.0)] + [(101.0, 101.2, 101.1)] * 65
    series, ts = make_series(rows)
    ev = [{"confirmation_ts": ts[0], "level": 100.0, "poc": 101.0, "side": "long",
           "excursion_extreme": 99.5, "vah": 102.0, "val": 100.0}]
    resolved = out.add_primary_outcomes(ev, series)
    resolved = out.add_opposite_edge_completion(resolved, series)
    assert resolved[0]["outcome_h60"] == "POC_FIRST"
    assert resolved[0]["opposite_edge_completion"] in ("OPPOSITE_EDGE_FIRST", "ORIGIN_EDGE_FIRST", "NEITHER", "SAME_BAR_AMBIGUOUS", "INCOMPLETE_HORIZON")


def test_opposite_edge_completion_none_when_not_poc_first():
    rows = [(100.2, 100.3, 100.25)] + [(99.0, 99.2, 99.1)] * 65
    series, ts = make_series(rows)
    ev = [{"confirmation_ts": ts[0], "level": 100.0, "poc": 105.0, "side": "long",
           "excursion_extreme": 99.5, "vah": 106.0, "val": 100.0}]
    resolved = out.add_primary_outcomes(ev, series)
    resolved = out.add_opposite_edge_completion(resolved, series)
    assert resolved[0]["outcome_h60"] == "REDISCOVERY_FIRST"
    assert resolved[0]["opposite_edge_completion"] is None
