"""Evidence from the data for BA starts, stops and footprint changes (for data/ba_events.csv)."""

import numpy as np
import pandas as pd


def reporting_spans(hourly: pd.DataFrame) -> pd.DataFrame:
    """Per BA: first and last hour with a row, first and last hour with demand, mean demand."""
    groups = hourly.groupby("ba")
    with_demand = hourly[hourly["demand"].notna()].groupby("ba")["utc"]
    return pd.DataFrame(
        {
            "first_row": groups["utc"].min(),
            "last_row": groups["utc"].max(),
            "first_demand": with_demand.min(),
            "last_demand": with_demand.max(),
            "mean_demand_mw": groups["demand"].mean(),
        }
    )


def yoy_shift_runs(
    hourly: pd.DataFrame, low: float = 0.75, high: float = 1.33, min_months: int = 2
) -> pd.DataFrame:
    """Runs of at least `min_months` consecutive months whose median positive demand is below
    `low` or above `high` times the same month a year earlier.

    Columns: ba, first_month, months, ratio (in the first month), median_mw, year_before_mw.
    """
    positive = hourly[hourly["demand"] > 0]
    month = positive["utc"].dt.tz_convert(None).dt.to_period("M").rename("month")
    medians = positive.groupby([positive["ba"], month])["demand"].median().unstack("ba")
    medians = medians.reindex(pd.period_range(medians.index.min(), medians.index.max(), freq="M"))
    year_before = medians.shift(12)
    ratio = medians / year_before
    outside = (ratio < low) | (ratio > high)
    rows = []
    for ba in medians.columns:
        run_id = (outside[ba] != outside[ba].shift()).cumsum()
        for _, run in outside[ba][outside[ba]].groupby(run_id[outside[ba]]):
            if len(run) >= min_months:
                first = run.index[0]
                rows.append(
                    {
                        "ba": ba,
                        "first_month": first,
                        "months": len(run),
                        "ratio": ratio.loc[first, ba],
                        "median_mw": medians.loc[first, ba],
                        "year_before_mw": year_before.loc[first, ba],
                    }
                )
    columns = ["ba", "first_month", "months", "ratio", "median_mw", "year_before_mw"]
    return pd.DataFrame(rows, columns=columns)


def step_change(
    hourly: pd.DataFrame,
    ba: str,
    around: pd.Timestamp,
    search_days: int = 45,
    window_days: int = 14,
) -> dict[str, object]:
    """The day within `search_days` of `around` where mean positive demand in the next
    `window_days` differs most (by log ratio) from the `window_days` before it.

    Returns the day, that demand ratio, and the forecast's ratio for the same windows, which shows
    whether the forecast moved too (as it would for a footprint change).
    """
    rows = hourly[hourly["ba"] == ba]
    window = pd.Timedelta(days=window_days)
    best: dict[str, object] = {"ba": ba, "day": pd.NaT, "demand_ratio": np.nan}
    for day in pd.date_range(around - pd.Timedelta(days=search_days), periods=2 * search_days + 1):
        before = rows[(rows["utc"] >= day - window) & (rows["utc"] < day)]
        after = rows[(rows["utc"] >= day) & (rows["utc"] < day + window)]
        ratios = {
            column: after[column].where(after[column] > 0).mean()
            / before[column].where(before[column] > 0).mean()
            for column in ("demand", "forecast")
        }
        current = best["demand_ratio"]
        if not np.isnan(ratios["demand"]) and (
            np.isnan(current) or abs(np.log(ratios["demand"])) > abs(np.log(current))
        ):
            best = {
                "ba": ba,
                "day": day,
                "demand_ratio": ratios["demand"],
                "forecast_ratio": ratios["forecast"],
            }
    return best
