import pandas as pd

from grid_audit.quality_rules import render_proposal

NAN = float("nan")
F1, F2 = "EIA930_BALANCE_2015_Jul_Dec.csv", "EIA930_BALANCE_2016_Jan_Jun.csv"


def test_render_proposal() -> None:
    # Same table as test_quality.py. A: 10 hours, demand 5 5 5 5 7 7 0 8 - 8, forecast
    # 6 6 6 6 6 6 6 -1 6 6. B: 4 hours (02:00 absent), demand and forecast 9.
    start = pd.Timestamp("2016-01-01", tz="UTC")
    a = pd.DataFrame(
        {
            "ba": "A",
            "utc": [start + pd.Timedelta(hours=h) for h in range(10)],
            "demand": [5, 5, 5, 5, 7, 7, 0, 8, NAN, 8],
            "forecast": [6, 6, 6, 6, 6, 6, 6, -1, 6, 6],
            "source_file": [F1] * 5 + [F2] * 5,
        }
    )
    b = pd.DataFrame(
        {
            "ba": "B",
            "utc": [start + pd.Timedelta(hours=h) for h in (0, 1, 3, 4)],
            "demand": 9.0,
            "forecast": 9.0,
            "source_file": F1,
        }
    )
    hourly = pd.concat([a, b], ignore_index=True)
    events = pd.DataFrame(
        {
            "date": pd.to_datetime(["2016-01-01", "2016-01-01"], utc=True),
            "ba": ["A", "B"],
            "event": ["footprint_change", "demand_level_shift"],
            "basis": ["data only", "data only"],
            "evidence": ["A moved", "B's demand jumped"],
        }
    )
    page = render_proposal(hourly, events, run_hours=4)
    # R1: A h6, h7. R2: A h1-h3. R3a: all 9 of A's hours with both values are within 7 days of
    # its event; 4 are left after R1 and R2. R3b: A has 0 and B 4 usable hours (< 8,760), so
    # it removes all 13 on its own and B's 4 after the others.
    assert "| R1 | 2 | 2 | 1 |" in page
    assert "| R2 (N = 4) | 3 | 3 | 1 |" in page
    assert "| R3a | 9 | 4 | 1 |" in page
    assert "| R3b | 13 | 4 | 2 |" in page
    assert "Usable after all four rules: 0 hours (0.0% of all BA-hours)." in page
    # N=4 after R1 and R3a removes nothing; B keeps all its hours, A none.
    assert "| 4 (proposed) | 0 | 0 | 1 of 2 | 1 of 2 |" in page
    assert "| 2016-01-01 | A | footprint_change | data only | 9 |" in page
    assert "| B | 4 |" in page
    assert "BAs with no usable hours at all (1): A." in page
    assert "| 2016-01-01 | B | demand_level_shift | data only | B's demand jumped |" in page
    # R2b on the forecast: A h1-h6 repeat inside a run of seven 6s, 6 of A's 9 hours.
    assert "| A | 66.67 |" in page
