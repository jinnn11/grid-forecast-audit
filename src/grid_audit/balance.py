"""Read EIA-930 six-month BALANCE files into a tidy DataFrame."""

from pathlib import Path
from typing import IO

import pandas as pd

# Source column -> our name. Demand is the raw reported series, not EIA's imputed or adjusted one.
COLUMNS = {
    "Balancing Authority": "ba",
    "UTC Time at End of Hour": "utc",
    "Demand (MW)": "demand",
    "Demand Forecast (MW)": "forecast",
}
UTC_FORMAT = "%m/%d/%Y %I:%M:%S %p"


def to_mw(values: pd.Series) -> pd.Series:
    """Parse MW strings such as '12,345' to floats; blanks become NaN, anything else raises."""
    return pd.to_numeric(values.str.replace(",", "", regex=False), errors="raise").astype(float)


def read_balance(source: str | Path | IO[str]) -> pd.DataFrame:
    """One row per BA and hour: ba, utc (end of hour), demand and forecast in MW (NaN if blank).

    Rows are sorted by BA, then time. Raises ValueError on a missing column or a repeated hour.
    """
    raw = pd.read_csv(source, usecols=list(COLUMNS), dtype=str)
    hourly = pd.DataFrame(
        {
            "ba": raw["Balancing Authority"],
            "utc": pd.to_datetime(raw["UTC Time at End of Hour"], format=UTC_FORMAT, utc=True),
            "demand": to_mw(raw["Demand (MW)"]),
            "forecast": to_mw(raw["Demand Forecast (MW)"]),
        }
    )
    repeated = hourly.duplicated(["ba", "utc"])
    if repeated.any():
        raise ValueError(f"{int(repeated.sum())} repeated BA/hour rows")
    return hourly.sort_values(["ba", "utc"], ignore_index=True)
