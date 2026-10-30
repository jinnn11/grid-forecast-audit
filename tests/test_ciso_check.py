import io

import pandas as pd

from grid_audit.ciso_check import fetched_as, read_storage

HEADER = (
    '"Balancing Authority","UTC Time at End of Hour","Net Generation (MW) from Battery Storage",'
    '"Net Generation (MW) from Other Fuel Sources"'
)


def test_read_storage_keeps_one_ba() -> None:
    text = "\n".join(
        [
            HEADER,
            'CISO,01/01/2025 01:00:00 AM,,"-1,200"',
            "CISO,01/01/2025 02:00:00 AM,,350",
            "BANC,01/01/2025 01:00:00 AM,5,1",
        ]
    )
    table = read_storage(io.StringIO(text))
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


def test_fetched_as() -> None:
    assert fetched_as(pd.Period("2019-07", "M")) == "sample"
    assert fetched_as(pd.Period("2022-06", "M")) == "pin-down"
    assert fetched_as(pd.Period("2025-03", "M")) == "earlier check"
