import math

import pandas as pd
import pytest

from grid_audit.events import reporting_spans, step_change, yoy_shift_runs


def test_reporting_spans() -> None:
    hourly = pd.DataFrame(
        {
            "ba": ["X", "X", "X", "G"],
            "utc": pd.to_datetime(
                ["2016-01-01 01:00", "2016-01-01 02:00", "2016-01-01 03:00", "2016-01-01 01:00"],
                utc=True,
            ),
            "demand": [float("nan"), 10.0, 20.0, float("nan")],
        }
    )
    spans = reporting_spans(hourly)
    assert spans.loc["X", "first_row"] == pd.Timestamp("2016-01-01 01:00", tz="UTC")
    assert spans.loc["X", "first_demand"] == pd.Timestamp("2016-01-01 02:00", tz="UTC")
    assert spans.loc["X", "mean_demand_mw"] == pytest.approx(15.0)
    assert pd.isna(spans.loc["G", "first_demand"])  # generation-only: no demand ever


def test_yoy_shift_runs() -> None:
    # One reading per month for 26 months: 100 for months 1-12, 50 for months 13-14, then 100.
    # Months 13-14 are x0.5 a year earlier (one run); months 25-26 are x2.0 of 13-14 (another).
    months = pd.date_range("2016-01-01", periods=26, freq="MS") + pd.Timedelta(days=14)
    demand = [100.0] * 12 + [50.0] * 2 + [100.0] * 12
    hourly = pd.DataFrame({"ba": "X", "utc": months.tz_localize("UTC"), "demand": demand})
    runs = yoy_shift_runs(hourly)
    assert [str(m) for m in runs["first_month"]] == ["2017-01", "2018-01"]
    assert list(runs["months"]) == [2, 2]
    assert list(runs["ratio"]) == pytest.approx([0.5, 2.0])
    assert list(runs["year_before_mw"]) == [100.0, 50.0]


def test_step_change_finds_the_break_and_the_forecast_ratio() -> None:
    # Daily readings: demand 100 for 30 days, then 60; forecast 110, then 66. The 7-day means on
    # either side of day 30 give 60/100 = 0.6 exactly; any other day mixes the two levels.
    days = pd.date_range("2016-01-01", periods=60, freq="D", tz="UTC")
    hourly = pd.DataFrame(
        {
            "ba": "X",
            "utc": days,
            "demand": [100.0] * 30 + [60.0] * 30,
            "forecast": [110.0] * 30 + [66.0] * 30,
        }
    )
    best = step_change(hourly, "X", days[25], search_days=10, window_days=7)
    assert best["day"] == days[30]
    assert best["demand_ratio"] == pytest.approx(0.6)
    assert best["forecast_ratio"] == pytest.approx(0.6)


def test_step_change_without_data() -> None:
    hourly = pd.DataFrame(
        {"ba": ["Y"], "utc": [pd.Timestamp("2016-01-01", tz="UTC")], "demand": [1.0]}
    ).assign(forecast=1.0)
    best = step_change(hourly, "X", pd.Timestamp("2016-01-01", tz="UTC"), 2, 1)
    assert pd.isna(best["day"]) and math.isnan(best["demand_ratio"])
