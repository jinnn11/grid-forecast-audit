import io

import pandas as pd

from grid_audit.storage import charging, read_storage, read_storage_columns

HEADER = (
    '"Balancing Authority","UTC Time at End of Hour","Net Generation (MW) from Battery Storage",'
    '"Net Generation (MW) from Other Fuel Sources"'
)
ROWS = [
    HEADER,
    'CISO,01/01/2025 01:00:00 AM,,"-1,200"',
    "CISO,01/01/2025 02:00:00 AM,,350",
    "BANC,01/01/2025 01:00:00 AM,5,1",
]


def test_read_storage_keeps_one_ba() -> None:
    table = read_storage(io.StringIO("\n".join(ROWS)))
    assert table.index.tolist() == list(
        pd.to_datetime(["2025-01-01 01:00", "2025-01-01 02:00"], utc=True)
    )
    # Blank battery values stay NaN; "-1,200" is -1200 MW.
    assert table["battery"].isna().all()
    assert table["other"].tolist() == [-1200.0, 350.0]


def test_read_storage_without_the_battery_column() -> None:
    text = '"Balancing Authority","UTC Time at End of Hour",'
    text += '"Net Generation (MW) from Other Fuel Sources"\nCISO,07/01/2018 08:00:00 AM,12'
    table = read_storage(io.StringIO(text))
    assert table["battery"].isna().all() and table["other"].tolist() == [12.0]


def test_read_storage_columns_keeps_every_ba() -> None:
    table = read_storage_columns(io.StringIO("\n".join(ROWS)))
    assert table["ba"].tolist() == ["CISO", "CISO", "BANC"]
    assert table.loc[2, "battery"] == 5.0 and table.loc[2, "other"] == 1.0


def test_charging() -> None:
    # Net generation below 0 is charging; discharging and blanks give 0 and NaN.
    assert charging(pd.Series([-300.0, 0.0, 250.0])).tolist() == [300.0, 0.0, 0.0]
    assert pd.isna(charging(pd.Series([float("nan")]))[0])
