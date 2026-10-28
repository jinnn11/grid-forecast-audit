import pandas as pd

from grid_audit.calendar import (
    HOLIDAYS,
    baseline_days,
    comparison_days,
    extreme_days,
    holiday_days,
    local_hours,
    window_days,
)

# The holiday table of docs/step3_audit_plan.md, 2016-2025: the actual date, then the observed
# weekday in brackets when the holiday falls on a weekend.
PLAN_TABLE = {
    "New Year's Day": "01-01|01-01 (01-02)|01-01|01-01|01-01|01-01|01-01 (2021-12-31)"
    "|01-01 (01-02)|01-01|01-01",
    "Memorial Day": "05-30|05-29|05-28|05-27|05-25|05-31|05-30|05-29|05-27|05-26",
    "Independence Day": "07-04|07-04|07-04|07-04|07-04 (07-03)|07-04 (07-05)|07-04|07-04|07-04"
    "|07-04",
    "Labor Day": "09-05|09-04|09-03|09-02|09-07|09-06|09-05|09-04|09-02|09-01",
    "Thanksgiving Day": "11-24|11-23|11-22|11-28|11-26|11-25|11-24|11-23|11-28|11-27",
    "Day after Thanksgiving": "11-25|11-24|11-23|11-29|11-27|11-26|11-25|11-24|11-29|11-28",
    "Christmas Eve": "|".join(["12-24"] * 10),
    "Christmas Day": "12-25 (12-26)|12-25|12-25|12-25|12-25|12-25 (12-24)|12-25 (12-26)|12-25"
    "|12-25|12-25",
    "New Year's Eve": "|".join(["12-31"] * 10),
}


def plan_rows() -> set[tuple[str, int, str, bool]]:
    rows = set()
    for holiday, cells in PLAN_TABLE.items():
        for year, cell in zip(range(2016, 2026), cells.split("|"), strict=True):
            actual, _, observed = cell.partition(" (")
            rows.add((holiday, year, f"{year}-{actual}", False))
            if observed:
                observed = observed.rstrip(")")  # "MM-DD", or "YYYY-MM-DD" in another year
                day = observed if len(observed) > 5 else f"{year}-{observed}"
                rows.add((holiday, year, day, True))
    return rows


def test_holiday_days_match_the_plan_table() -> None:
    days = holiday_days(range(2016, 2026))
    got = {
        (str(r.holiday), r.year, f"{r.day:%Y-%m-%d}", bool(r.observed)) for r in days.itertuples()
    }
    assert got == plan_rows()
    # 9 holidays x 10 years, plus 7 observed days: New Year's 2017, 2022, 2023; Independence Day
    # 2020, 2021; Christmas 2016, 2021, 2022 -> 8. 90 + 8 = 98.
    assert len(days) == 98
    assert list(days["holiday"].cat.categories) == HOLIDAYS


def test_local_hours() -> None:
    local_end = pd.Series(
        pd.to_datetime(["2025-01-01 00:00", "2025-03-01 01:00", "2025-07-04 13:00"])
    )
    fields = local_hours(local_end)
    # Midnight ends the last hour of Dec 31 (hour ending 24), which counts with the next winter.
    assert fields.loc[0, "day"] == pd.Timestamp("2024-12-31")
    assert fields.loc[0, ["year", "month", "hour_ending"]].tolist() == [2024, 12, 24]
    assert fields.loc[0, "season"] == "DJF" and fields.loc[0, "season_year"] == 2025
    # 01:00 ends hour ending 1 of Mar 1, the first spring hour.
    assert fields.loc[1, "day"] == pd.Timestamp("2025-03-01")
    assert fields.loc[1, "hour_ending"] == 1 and fields.loc[1, "season"] == "MAM"
    # 13:00 ends hour ending 13 (12:00-13:00) of Jul 4.
    assert fields.loc[2, "hour_ending"] == 13 and fields.loc[2, "season"] == "JJA"
    assert fields.loc[2, "season_year"] == 2025


def test_comparison_days() -> None:
    # Thanksgiving 2025 is Thursday Nov 27: Thursdays Nov 13, Nov 20, Dec 4 and Dec 11; Dec 4 is
    # excluded (say, an event day).
    days = comparison_days(
        pd.DatetimeIndex(["2025-11-27"]), pd.DatetimeIndex(["2025-12-04", "2025-11-27"])
    )
    assert list(days.strftime("%m-%d")) == ["11-13", "11-20", "12-11"]
    # New Year's Day 2025 (Wed): Dec 18, Dec 25 (a holiday, excluded), Jan 8, Jan 15.
    days = comparison_days(pd.DatetimeIndex(["2025-01-01"]), pd.DatetimeIndex(["2024-12-25"]))
    assert list(days.strftime("%Y-%m-%d")) == ["2024-12-18", "2025-01-08", "2025-01-15"]


def test_event_window_and_baseline() -> None:
    first, last = pd.Timestamp("2022-12-21"), pd.Timestamp("2022-12-26")
    assert len(window_days(first, last)) == 6
    # 14 days before (Dec 7-20) and 14 after (Dec 27 - Jan 9) = 28, less New Year's Eve, New
    # Year's Day and its observed Monday Jan 2 = 25.
    excluded = pd.DatetimeIndex(["2022-12-31", "2023-01-01", "2023-01-02", "2022-12-25"])
    days = baseline_days(first, last, excluded)
    assert len(days) == 25
    assert days[0] == pd.Timestamp("2022-12-07") and days[-1] == pd.Timestamp("2023-01-09")
    assert pd.Timestamp("2022-12-20") in days and pd.Timestamp("2022-12-27") in days


def test_extreme_days() -> None:
    peaks = pd.DataFrame(
        {
            "ba": ["A"] * 10 + ["B"] * 3,
            "season": ["JJA"] * 13,
            "season_year": [2025] * 13,
            "peak": [float(p) for p in [*range(1, 11), 5, 5, 5]],
        }
    )
    flags = extreme_days(peaks)
    # A: 99th percentile of 1..10 = 9 + 0.91 x (10 - 9) = 9.91 (position 0.99 x 9 = 8.91), so
    # only the day with peak 10 is above it.
    assert flags[:10].tolist() == [False] * 9 + [True]
    # B: three equal peaks; the percentile is 5 and no day is above it.
    assert not flags[10:].any()
