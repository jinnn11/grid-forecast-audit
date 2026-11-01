"""Net generation from storage in the cached EIA-930 BALANCE files, which the combined history
does not keep. Parsing only; used by the CISO check, the battery check and the audit's charging
variants.
"""

from pathlib import Path
from typing import IO

import pandas as pd

from grid_audit.balance import UTC_FORMAT, to_mw
from grid_audit.download import RAW_DIR, balance_file_names

STORAGE_COLUMNS = {
    "Net Generation (MW) from Battery Storage": "battery",
    "Net Generation (MW) from Other Fuel Sources": "other",
}
STORAGE_FILES = balance_file_names((2018, 2), (2026, 1))  # fuel types start in July 2018


def read_storage_columns(source: str | Path | IO[str]) -> pd.DataFrame:
    """Every BA's net generation from battery storage and from other fuel sources (MW): columns
    ba, utc (hour end), battery and other; NaN where blank, or where the file lacks the column."""
    wanted = {"Balancing Authority", "UTC Time at End of Hour", *STORAGE_COLUMNS}
    raw = pd.read_csv(source, usecols=lambda column: column in wanted, dtype=str)
    table = pd.DataFrame(
        {
            "ba": raw["Balancing Authority"],
            "utc": pd.to_datetime(raw["UTC Time at End of Hour"], format=UTC_FORMAT, utc=True),
        }
    )
    for column, name in STORAGE_COLUMNS.items():
        table[name] = to_mw(raw[column]) if column in raw.columns else float("nan")
    return table


def read_storage(source: str | Path | IO[str], ba: str = "CISO") -> pd.DataFrame:
    """The BA's battery and other-fuel net generation (MW) by UTC hour end, from one file."""
    table = read_storage_columns(source)
    return table[table["ba"].eq(ba)].drop(columns="ba").set_index("utc")


def all_storage(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """read_storage_columns over every file with fuel types, an hour reported twice kept once."""
    tables = [read_storage_columns(raw_dir / name) for name in STORAGE_FILES]
    return pd.concat(tables, ignore_index=True).drop_duplicates(["ba", "utc"])


def charging(storage: pd.Series) -> pd.Series:
    """Charging (MW, at least 0) from net generation from storage, which is below 0 while
    charging."""
    return (-storage).clip(lower=0) + 0.0  # + 0.0 turns -0.0 into 0.0
