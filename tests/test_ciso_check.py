import pandas as pd
import pytest

from grid_audit.ciso_check import battery_months, fetched_as, other_timing


def test_fetched_as() -> None:
    assert fetched_as(pd.Period("2019-07", "M")) == "sample"
    assert fetched_as(pd.Period("2022-06", "M")) == "pin-down"
    assert fetched_as(pd.Period("2025-03", "M")) == "earlier check"
    assert fetched_as(pd.Period("2021-05", "M")) == "spell check"


def daily_wave(index: pd.DatetimeIndex) -> pd.Series:
    """A net storage pattern: -100 to -500 MW charging from 10:00 to 14:00 UTC, 300 MW from
    20:00 to 22:00, 0 otherwise, the charging deeper on even days so days differ."""
    values = []
    for t in index:
        depth = 1 + (t.day % 2)
        if 10 <= t.hour <= 14:
            values.append(-100.0 * depth * (t.hour - 9))
        elif 20 <= t.hour <= 22:
            values.append(300.0)
        else:
            values.append(0.0)
    return pd.Series(values, index=index)


def test_other_timing_reads_late_and_on_time() -> None:
    # March 2025: EIA's value for t is CAISO's battery output for t - 1 (an hour late).
    march = pd.date_range("2025-03-01 09:00", "2025-03-31 06:00", freq="h", tz="UTC")
    batteries = daily_wave(march)
    other = pd.Series(batteries.shift(1).to_numpy(), index=march)
    # July 2023: no battery data; CAISO's gap is exactly the charging of EIA's same hour.
    july = pd.date_range("2023-07-01 08:00", "2023-07-31 06:00", freq="h", tz="UTC")
    other_july = daily_wave(july)
    caiso = pd.DataFrame({"actual": 1000 + (-other_july).clip(lower=0), "forecast": 1000.0})
    table = other_timing(pd.concat([other, other_july]).sort_index(), batteries, caiso)
    # March: moved +1 h the two are identical (correlation 1), so the column is late.
    assert table.loc["2025-03", "source"] == "batteries"
    assert table.loc["2025-03", "late"] == pytest.approx(1.0)
    assert table.loc["2025-03", "verdict"] == "late"
    # July 2023: the same hour's charging fits the gap exactly (R² 1), so it is on time.
    assert table.loc["2023-07", "source"] == "forecast gap"
    assert table.loc["2023-07", "on_time"] == pytest.approx(1.0)
    assert table.loc["2023-07", "verdict"] == "on time"


def test_battery_months() -> None:
    index = pd.to_datetime(["2025-01-10 20:00", "2025-01-10 21:00", "2025-02-10 20:00"], utc=True)
    other = pd.Series([-100.0, 300.0, -50.0], index=index)
    batteries = pd.Series([-120.0, 280.0, float("nan")], index=index)
    table = battery_months(other, batteries)
    # February has no CAISO value, so only January is left: charging means (100 + 0) / 2 and
    # (120 + 0) / 2, discharging (0 + 300) / 2 and (0 + 280) / 2.
    assert table.index.tolist() == [1]
    row = table.loc[1]
    assert (row.eia_charging, row.caiso_charging) == (50.0, 60.0)
    assert (row.eia_discharging, row.caiso_discharging) == (150.0, 140.0)
