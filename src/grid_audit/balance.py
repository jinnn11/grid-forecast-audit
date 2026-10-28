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
# Read when present; all NaN otherwise. All 22 files have them. Imputed holds EIA's value only
# where EIA replaced or filled raw demand; adjusted is raw demand with those values applied.
EXTRA_COLUMNS = {
    "Demand (MW) (Imputed)": "demand_imputed",
    "Demand (MW) (Adjusted)": "demand_adjusted",
    "Net Generation (MW)": "net_generation",
    "Total Interchange (MW)": "interchange",
}
# The BA's own clock (no offset given; an autumn hour repeats). Read when present; NaT otherwise.
LOCAL_COLUMN = "Local Time at End of Hour"
UTC_FORMAT = "%m/%d/%Y %I:%M:%S %p"  # local time uses the same format


def to_mw(values: pd.Series) -> pd.Series:
    """Parse MW strings such as '12,345' to floats; blanks become NaN, anything else raises."""
    return pd.to_numeric(values.str.replace(",", "", regex=False), errors="raise").astype(float)


def read_balance(source: str | Path | IO[str]) -> pd.DataFrame:
    """One row per BA and hour: ba, utc (end of hour), local (end of hour, naive), demand and
    forecast, then the EXTRA_COLUMNS, all in MW (NaN if blank; an extra column is all NaN, and
    local all NaT, when the file lacks it).

    Rows are sorted by BA, then time. Raises ValueError on a missing column or a repeated hour.
    """
    wanted = {*COLUMNS, *EXTRA_COLUMNS, LOCAL_COLUMN}
    raw = pd.read_csv(source, usecols=lambda column: column in wanted, dtype=str)
    missing = [column for column in COLUMNS if column not in raw.columns]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    hourly = pd.DataFrame(
        {
            "ba": raw["Balancing Authority"],
            "utc": pd.to_datetime(raw["UTC Time at End of Hour"], format=UTC_FORMAT, utc=True),
            "local": (
                pd.to_datetime(raw[LOCAL_COLUMN], format=UTC_FORMAT)
                if LOCAL_COLUMN in raw.columns
                else pd.NaT
            ),
            "demand": to_mw(raw["Demand (MW)"]),
            "forecast": to_mw(raw["Demand Forecast (MW)"]),
        }
    )
    for column, name in EXTRA_COLUMNS.items():
        hourly[name] = to_mw(raw[column]) if column in raw.columns else float("nan")
    repeated = hourly.duplicated(["ba", "utc"])
    if repeated.any():
        raise ValueError(f"{int(repeated.sum())} repeated BA/hour rows")
    return hourly.sort_values(["ba", "utc"], ignore_index=True)
