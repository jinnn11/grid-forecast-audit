import pandas as pd
from test_truth import COLUMNS, F1, F2, ROWS

from grid_audit.truth_check import pct_cell, render_truth_report


def test_pct_cell() -> None:
    assert [pct_cell(v) for v in (float("nan"), 0.0, 0.04, 0.05, 12.345)] == [
        "–",
        "0",
        "<0.1",
        "0.1",
        "12.3",
    ]


def test_render_truth_report() -> None:
    # The table from test_truth.py, with every forecast 50 MW and no events.
    start = pd.Timestamp("2016-01-01", tz="UTC")
    frames = []
    for ba, rows in ROWS.items():
        frame = pd.DataFrame(rows, columns=COLUMNS, dtype=float)
        frame.insert(0, "ba", ba)
        frame.insert(1, "utc", [start + pd.Timedelta(hours=h) for h in range(len(rows))])
        frame["forecast"] = 50.0
        frame["source_file"] = [F1 if h < 3 else F2 for h in range(len(rows))]
        frames.append(frame)
    hourly = pd.concat(frames, ignore_index=True)
    events = pd.DataFrame({"date": pd.Series(dtype="datetime64[ns, UTC]"), "ba": [], "event": []})
    page = render_truth_report(hourly, events)

    # (a): EIA replaced A1 and A4. A changed 1 of 2 raw hours in 2015 H2, 1 of 3 in 2016 H1.
    assert "| … raw reported, so EIA replaced it | 2 |" in page
    assert "| A | 50.0 | 33.3 |" in page
    assert "EIA changed no hour of these BAs (2): C, B." in page  # sorted by mean demand
    # Stretches: A1 is the only negative hour (replaced, imbalanced); B1 the only zero (balanced).
    assert "| Negative demand | 1 | 100.0 | 100.0 | 100.0 |" in page
    assert "| Zero demand | 1 | 0 | 100.0 | 0 |" in page
    assert "| CHPD level shift, 2015-12-18 to 2016-12-31 | 0 | – | – | – |" in page
    # (b): checkable A0, A1, A3, A4, B0, B1 (6 of 9 raw hours). Within 1 MW of NG - TI: A0,
    # A4, B0, B1 (4 of 6). Of NG + TI: B0 (5 vs 5.8) and B1 (0 vs 0), 2 of 6.
    assert "- 6 of 9 hours with raw demand (66.7%) also have net generation" in page
    assert "net generation minus interchange in 66.7% of hours, and of net generation plus" in page
    assert "interchange in 33.3%." in page
    assert "the plus sign fits better in 0 of 1 BAs." in page
    assert "| A | 4 | 50.0 | 0.0 | 50.0 |" in page
    assert "| B | 2 | 100.0 | -16.0 | 0 |" in page
    assert "| C | 0 | – | – | – |" in page
    # Impact. Base: A0, A1, A3, A4, A5, B0, B1, C0, C1 (9). R1: A1, B1. No run of 6, no events.
    # R4: A1, A4; A4 after R1. R5: A1, A3; A3 after R1. Left: A0, A5, B0, C0, C1, so every BA
    # is under 8,760 hours and R3b removes all 9 on its own and those 5 after the others.
    assert "| R1 | 2 | 2 | 2 |" in page
    assert "| R2 (N = 6) | 0 | 0 | 0 |" in page
    assert "| R4 (EIA changed) | 2 | 1 | 1 |" in page
    assert "| R5 (balance, 10%) | 2 | 1 | 1 |" in page
    assert "| R3b (after all the others) | 9 | 5 | 3 |" in page
    # Sensitivity, after R1-R4. 10%: removes A3 (1 of A's 5 hours with both values). Kept: A 2
    # of 6 rows (2 of 5 with both values), B 1 of 2 (1 of 2), C 2 of 3 (2 of 2), so only C keeps
    # 95% of its hours with both values. 50%: A3's 30% gap is kept, so nothing is removed.
    assert "| 10% (proposed) | 1 | 1 | 0 of 3 | 1 of 3 |" in page
    assert "| 50% | 0 | 0 | 0 of 3 | 1 of 3 |" in page
    assert "BAs with usable hours that it drops: A, B, C;" in page
