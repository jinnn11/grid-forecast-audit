"""Step 3 calendar: local days and hours, seasons, holidays, event windows and extreme-demand days.

Each hour belongs to the local day and hour in which it starts (local hour end minus one hour), so
hour ending 24 is the last hour of its day. Pure functions.
"""

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

HOUR = pd.Timedelta(hours=1)
DAY = pd.Timedelta(days=1)
SEASON_ORDER = ["DJF", "MAM", "JJA", "SON"]
SEASONS = {month: SEASON_ORDER[month % 12 // 3] for month in range(1, 13)}
# The plan's holidays, in its table's order. Six follow pandas' federal calendar; it lacks the
# other three.
FEDERAL = [
    "New Year's Day",
    "Memorial Day",
    "Independence Day",
    "Labor Day",
    "Thanksgiving Day",
    "Christmas Day",
]
HOLIDAYS = [
    "New Year's Day",
    "Memorial Day",
    "Independence Day",
    "Labor Day",
    "Thanksgiving Day",
    "Day after Thanksgiving",
    "Christmas Eve",
    "Christmas Day",
    "New Year's Eve",
]
COMPARISON_WEEKS = (-2, -1, 1, 2)  # same weekday, one and two weeks before and after
BASELINE_DAYS = 14  # event baseline: this many days before and after the window
EXTREME_PERCENTILE = 99
MIN_DAY_HOURS = 20  # a day needs this many usable hours for its peak to count


def local_hours(local_end: pd.Series) -> pd.DataFrame:
    """Per hour, from its local end time: the local day it starts in (midnight), its year and
    month, hour ending (1-24), season, and season year (December counts with the next year's
    January and February)."""
    start = local_end - HOUR
    month = start.dt.month
    return pd.DataFrame(
        {
            "day": start.dt.normalize(),
            "year": start.dt.year,
            "month": month,
            "hour_ending": start.dt.hour + 1,
            "season": pd.Categorical(month.map(SEASONS), categories=SEASON_ORDER),
            "season_year": start.dt.year + month.eq(12),
        },
        index=local_end.index,
    )


def holiday_days(years: range) -> pd.DataFrame:
    """The plan's holidays in `years`: columns holiday, year, day and observed (True for the
    weekday on which a weekend holiday is observed). Federal dates follow the rules of pandas'
    USFederalHolidayCalendar; the observed day can fall in the previous year."""
    rules = {rule.name: rule for rule in USFederalHolidayCalendar.rules}
    rows = []
    for year in years:
        dates: dict[str, pd.Timestamp] = {}
        for name in FEDERAL:
            rule = rules[name]
            if rule.observance is None:
                actual = rule.dates(f"{year}-01-01", f"{year}-12-31")[0]
            else:
                actual = pd.Timestamp(year, rule.month, rule.day)
                observed = rule.observance(actual)
                if observed != actual:
                    rows.append((name, year, observed, True))
            dates[name] = actual
        dates["Day after Thanksgiving"] = dates["Thanksgiving Day"] + DAY
        dates["Christmas Eve"] = pd.Timestamp(year, 12, 24)
        dates["New Year's Eve"] = pd.Timestamp(year, 12, 31)
        rows += [(name, year, day, False) for name, day in dates.items()]
    days = pd.DataFrame(rows, columns=["holiday", "year", "day", "observed"])
    days["holiday"] = pd.Categorical(days["holiday"], categories=HOLIDAYS)
    return days.sort_values(["holiday", "year", "day"], ignore_index=True)


def comparison_days(days: pd.DatetimeIndex, excluded: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """The same weekday one and two weeks before and after each of `days`, without `excluded`
    days (other holidays and events)."""
    shifted = [days + pd.Timedelta(weeks=weeks) for weeks in COMPARISON_WEEKS]
    candidates = pd.DatetimeIndex(sorted({day for group in shifted for day in group}))
    return candidates[~candidates.isin(excluded)]


def window_days(first: pd.Timestamp, last: pd.Timestamp) -> pd.DatetimeIndex:
    """Every day from `first` to `last`, inclusive."""
    return pd.date_range(first, last, freq="D")


def baseline_days(
    first: pd.Timestamp, last: pd.Timestamp, excluded: pd.DatetimeIndex
) -> pd.DatetimeIndex:
    """The BASELINE_DAYS days before `first` and after `last`, without `excluded` days."""
    before = pd.date_range(first - BASELINE_DAYS * DAY, first - DAY, freq="D")
    after = pd.date_range(last + DAY, last + BASELINE_DAYS * DAY, freq="D")
    days = before.append(after)
    return days[~days.isin(excluded)]


def extreme_days(peaks: pd.DataFrame, percentile: float = EXTREME_PERCENTILE) -> pd.Series:
    """For one row per BA and day (columns ba, season, season_year, peak): True for days whose
    peak is above the BA's `percentile` percentile (linear interpolation) of daily peaks within
    the same season and season year."""
    groups = peaks.groupby(["ba", "season", "season_year"], observed=True)["peak"]
    return peaks["peak"].gt(groups.transform("quantile", percentile / 100))
