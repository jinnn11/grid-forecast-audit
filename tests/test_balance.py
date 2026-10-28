import io
from pathlib import Path

import pandas as pd
import pytest

from grid_audit.balance import read_balance, to_mw

SAMPLE = Path(__file__).parent / "data" / "balance_sample.csv"


def test_read_balance_sample() -> None:
    hourly = read_balance(SAMPLE)
    assert list(hourly.columns) == [
        "ba",
        "utc",
        "local",
        "demand",
        "forecast",
        "demand_imputed",
        "demand_adjusted",
        "net_generation",
        "interchange",
    ]
    # 26 BIG + 4 SMALL + 2 GEN + 3 NEG rows, sorted by BA then time.
    assert len(hourly) == 35
    assert list(hourly["ba"].drop_duplicates()) == ["BIG", "GEN", "NEG", "SMALL"]

    big = hourly[hourly["ba"] == "BIG"].reset_index(drop=True)
    # Hour 1: UTC 01/01/2026 7:00:00 AM, demand written as "1,000".
    assert big.loc[0, "utc"] == pd.Timestamp("2026-01-01 07:00", tz="UTC")
    assert big.loc[0, "demand"] == 1000.0
    assert big.loc[0, "forecast"] == 1050.0
    # Hour 6 is "12:00:00 PM" (noon); hour 18 is "01/02/2026 12:00:00 AM" (midnight).
    assert big.loc[5, "utc"] == pd.Timestamp("2026-01-01 12:00", tz="UTC")
    assert big.loc[17, "utc"] == pd.Timestamp("2026-01-02 00:00", tz="UTC")
    # Local time has no zone: hour 1 is "01/01/2026 1:00:00 AM", hour 18 "6:00:00 PM" (UTC-6).
    assert big.loc[0, "local"] == pd.Timestamp("2026-01-01 01:00")
    assert big.loc[17, "local"] == pd.Timestamp("2026-01-01 18:00")
    # Hour 5 has a blank demand; hour 8 has a blank forecast.
    assert pd.isna(big.loc[4, "demand"]) and big.loc[4, "forecast"] == 1050.0
    assert big.loc[7, "demand"] == 1250.0 and pd.isna(big.loc[7, "forecast"])

    gen = hourly[hourly["ba"] == "GEN"]
    assert gen["demand"].isna().all() and gen["forecast"].isna().all()
    # The sample has the extra columns, but every value in them is blank.
    extra = ["demand_imputed", "demand_adjusted", "net_generation", "interchange"]
    assert hourly[extra].isna().all().all()


def test_read_balance_adjusted_column() -> None:
    csv = (
        "Balancing Authority,UTC Time at End of Hour,Demand Forecast (MW),Demand (MW),"
        "Demand (MW) (Adjusted)\n"
        'X,01/01/2026 1:00:00 AM,5,5,"1,234"\n'
        "X,01/01/2026 2:00:00 AM,5,5,\n"
    )
    hourly = read_balance(io.StringIO(csv))
    assert hourly.loc[0, "demand_adjusted"] == 1234.0
    assert pd.isna(hourly.loc[1, "demand_adjusted"])


def test_read_balance_imputed_generation_and_interchange() -> None:
    csv = (
        "Balancing Authority,UTC Time at End of Hour,Demand Forecast (MW),Demand (MW),"
        "Net Generation (MW),Total Interchange (MW),Demand (MW) (Imputed)\n"
        'X,01/01/2026 1:00:00 AM,5,,"1,200",-30,1230\n'
        "X,01/01/2026 2:00:00 AM,5,5,8,3,\n"
    )
    hourly = read_balance(io.StringIO(csv))
    assert pd.isna(hourly.loc[0, "demand"]) and hourly.loc[0, "demand_imputed"] == 1230.0
    assert hourly.loc[0, "net_generation"] == 1200.0 and hourly.loc[0, "interchange"] == -30.0
    assert hourly.loc[1, "net_generation"] == 8.0 and hourly.loc[1, "interchange"] == 3.0
    assert pd.isna(hourly.loc[1, "demand_imputed"])
    assert hourly["demand_adjusted"].isna().all()  # column absent from this file


def test_read_balance_without_adjusted_column() -> None:
    csv = (
        "Balancing Authority,UTC Time at End of Hour,Demand Forecast (MW),Demand (MW)\n"
        "X,01/01/2026 1:00:00 AM,5,5\n"
    )
    hourly = read_balance(io.StringIO(csv))
    assert pd.isna(hourly.loc[0, "demand_adjusted"])
    assert pd.isna(hourly.loc[0, "local"])  # no local-time column either


def test_to_mw() -> None:
    values = to_mw(pd.Series(["12,345", None, "0", "-5.5"], dtype=str))
    assert values.iloc[0] == 12345.0
    assert pd.isna(values.iloc[1])
    assert values.iloc[2] == 0.0
    assert values.iloc[3] == -5.5


def test_to_mw_rejects_text() -> None:
    with pytest.raises(ValueError):
        to_mw(pd.Series(["n/a"], dtype=str))


def test_read_balance_missing_column() -> None:
    csv = "Balancing Authority,UTC Time at End of Hour,Demand (MW)\nX,01/01/2026 1:00:00 AM,5\n"
    with pytest.raises(ValueError, match="Demand Forecast"):
        read_balance(io.StringIO(csv))


def test_read_balance_repeated_hour() -> None:
    csv = (
        "Balancing Authority,UTC Time at End of Hour,Demand Forecast (MW),Demand (MW)\n"
        "X,01/01/2026 1:00:00 AM,5,5\n"
        "X,01/01/2026 1:00:00 AM,6,6\n"
    )
    with pytest.raises(ValueError, match="repeated"):
        read_balance(io.StringIO(csv))
