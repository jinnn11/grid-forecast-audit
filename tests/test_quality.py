import pandas as pd
import pytest

from grid_audit.quality import (
    both_present,
    largest_bas,
    near_events,
    nonpositive,
    removed_by_ba,
    repeats_in_runs,
    rule_impact,
    run_length_sensitivity,
    short_history,
    usable_share,
)

NAN = float("nan")
F1, F2 = "EIA930_BALANCE_2015_Jul_Dec.csv", "EIA930_BALANCE_2016_Jan_Jun.csv"

# A: 10 consecutive hours h0-h9 from 2016-01-01 00:00 UTC; h0-h4 from F1, h5-h9 from F2.
#    demand   5 5 5 5 7 7 0 8 - 8   (h8 blank)
#    forecast 6 6 6 6 6 6 6 -1 6 6
# B: hours 00, 01, 03, 04 (02 absent), demand and forecast 9 throughout, all from F1.
A_DEMAND = [5, 5, 5, 5, 7, 7, 0, 8, NAN, 8]
A_FORECAST = [6, 6, 6, 6, 6, 6, 6, -1, 6, 6]


@pytest.fixture
def hourly() -> pd.DataFrame:
    start = pd.Timestamp("2016-01-01", tz="UTC")
    a = pd.DataFrame(
        {
            "ba": "A",
            "utc": [start + pd.Timedelta(hours=h) for h in range(10)],
            "demand": A_DEMAND,
            "forecast": A_FORECAST,
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
    return pd.concat([a, b], ignore_index=True)


def hours_of(flags: pd.Series, hourly: pd.DataFrame, ba: str) -> list[int]:
    """Hour numbers (hours after 2016-01-01 00:00) where `flags` is true for `ba`."""
    picked = hourly[flags & hourly["ba"].eq(ba)]
    start = pd.Timestamp("2016-01-01", tz="UTC")
    return [int((t - start) / pd.Timedelta(hours=1)) for t in picked["utc"]]


def test_both_present_and_nonpositive(hourly: pd.DataFrame) -> None:
    assert int(both_present(hourly).sum()) == 13  # A: all but h8; B: all 4
    assert hours_of(nonpositive(hourly), hourly, "A") == [6, 7]  # demand 0, forecast -1


def test_repeats_in_runs(hourly: pd.DataFrame) -> None:
    # N=4: only the run of four 5s counts; its first hour (h0) is kept.
    assert hours_of(repeats_in_runs(hourly, "demand", 4), hourly, "A") == [1, 2, 3]
    # N=2 also catches the pair of 7s.
    assert hours_of(repeats_in_runs(hourly, "demand", 2), hourly, "A") == [1, 2, 3, 5]
    assert hours_of(repeats_in_runs(hourly, "demand", 5), hourly, "A") == []
    # B's absent 02:00 splits four 9s into two runs of 2, so N=3 finds nothing.
    assert hours_of(repeats_in_runs(hourly, "demand", 3), hourly, "B") == []
    assert hours_of(repeats_in_runs(hourly, "demand", 2), hourly, "B") == [1, 4]
    # Forecast: seven 6s (h0-h6); -1 breaks the run, and h8-h9 is only two long.
    assert hours_of(repeats_in_runs(hourly, "forecast", 4), hourly, "A") == [1, 2, 3, 4, 5, 6]


def test_near_events(hourly: pd.DataFrame) -> None:
    events = pd.DataFrame(
        {
            "date": pd.to_datetime(["2016-01-01", "2016-01-01", "2016-01-01"], utc=True),
            "ba": ["A", "A", "C"],
            "event": ["footprint_change", "demand_level_shift", "stop"],
        }
    )
    # A quarter-day window: hours strictly within 6 h of midnight, so h0-h5. The
    # demand_level_shift event is not an R3a event, and C has no rows.
    flags = near_events(hourly, events, days=0.25)
    assert hours_of(flags, hourly, "A") == [0, 1, 2, 3, 4, 5]
    assert hours_of(flags, hourly, "B") == []


def test_short_history(hourly: pd.DataFrame) -> None:
    usable = pd.Series(False, index=hourly.index)
    usable[[0, 4, 9]] = True  # A: 3 usable hours
    usable[hourly["ba"] == "B"] = True  # B: 4 usable hours
    flags = short_history(hourly, usable, min_hours=4)
    assert list(hourly.loc[flags, "ba"].unique()) == ["A"]
    assert int(flags.sum()) == 10  # every row of A


def test_rule_impact(hourly: pd.DataFrame) -> None:
    rules = {
        "R1": nonpositive(hourly),
        "R2": repeats_in_runs(hourly, "demand", 4),
        "R2b": repeats_in_runs(hourly, "forecast", 4),
    }
    impact = rule_impact(hourly, rules).set_index("rule")
    # R1: A h6, h7. R2: A h1-h3. R2b alone: A h1-h6 (6); after R1 and R2 only h4, h5 remain.
    assert list(impact["alone"]) == [2, 3, 6]
    assert list(impact["after_earlier"]) == [2, 3, 2]
    assert list(impact["bas"]) == [1, 1, 1]


def test_removed_by_ba(hourly: pd.DataFrame) -> None:
    removed = removed_by_ba(hourly, nonpositive(hourly))
    assert list(removed.index) == ["A"]
    assert removed.loc["A", "hours"] == 2
    assert removed.loc["A", "pct"] == pytest.approx(100 * 2 / 9)


def test_largest_bas(hourly: pd.DataFrame) -> None:
    # Mean demand: A (5x4 + 7x2 + 0 + 8 + 8) / 9 = 5.6 MW; B 9 MW.
    assert largest_bas(hourly, 1) == ["B"]
    assert largest_bas(hourly, 5) == ["B", "A"]


def test_run_length_sensitivity(hourly: pd.DataFrame) -> None:
    table = run_length_sensitivity(
        hourly, [2, 4], nonpositive(hourly), top=["A", "B"], keep_pct=95.0
    ).set_index("n")
    # N=2: A loses h1, h2, h3, h5 (4 of 9); B loses h1, h4 (2 of 4). A keeps h0, h4, h9
    # (3 of 10 rows, 3 of 9 with both values); B keeps 2 of 4. Neither reaches 95%.
    assert table.loc[2].tolist() == [6, 2, 0, 0]
    # N=4: A loses h1-h3 and keeps h0, h4, h5, h9 (4 of 10 rows, 4 of 9); B keeps all 4.
    assert table.loc[4].tolist() == [3, 1, 1, 1]


def test_usable_share(hourly: pd.DataFrame) -> None:
    usable = both_present(hourly) & ~nonpositive(hourly) & ~repeats_in_runs(hourly, "demand", 4)
    share = usable_share(hourly, usable)
    # A keeps h0, h4 of its 5 F1 hours and h5, h9 of its 5 F2 hours; B keeps all 4 F1 hours.
    assert share.loc["A", "2015 H2"] == pytest.approx(40.0)
    assert share.loc["A", "2016 H1"] == pytest.approx(40.0)
    assert share.loc["B", "2015 H2"] == pytest.approx(100.0)
    assert pd.isna(share.loc["B", "2016 H1"])
