"""Step 2: combine all BALANCE files. Run: uv run python -m grid_audit.build_history

Writes data/processed/balance.parquet and results/schema_check.md. Reads only cached files.
"""

import sys
from pathlib import Path

import pandas as pd

from grid_audit.balance import COLUMNS, read_balance
from grid_audit.data_check import sha256
from grid_audit.download import BASE_URL, RAW_DIR, balance_file_names
from grid_audit.download_history import FIRST, LAST
from grid_audit.history import RawFile, combine, render_schema_report

PARQUET_PATH = Path("data/processed/balance.parquet")
REPORT_PATH = Path("results/schema_check.md")


def raw_file(path: Path) -> RawFile:
    return RawFile(
        name=path.name,
        url=BASE_URL + path.name,
        size=path.stat().st_size,
        downloaded=pd.Timestamp(path.stat().st_mtime, unit="s", tz="UTC"),
        sha256=sha256(path),
        header=list(pd.read_csv(path, nrows=0).columns),
    )


def main() -> None:
    paths = [RAW_DIR / name for name in balance_file_names(FIRST, LAST)]
    absent = [p.name for p in paths if not p.exists()]
    if absent:
        sys.exit(f"not downloaded yet: {', '.join(absent)}")
    files = [raw_file(p) for p in paths]
    reference, required = files[-1], list(COLUMNS)
    combined = None
    if all(c in f.header for f in files for c in required):
        combined = combine({p.name: read_balance(p) for p in paths})
    REPORT_PATH.write_text(
        render_schema_report(files, reference, required, combined), encoding="utf-8"
    )
    print(f"wrote {REPORT_PATH}")
    if combined is None or not combined.conflicts.empty:
        sys.exit("files could not be combined; see the report")
    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.hourly.to_parquet(PARQUET_PATH, index=False)
    print(f"wrote {PARQUET_PATH} ({len(combined.hourly):,} rows)")


if __name__ == "__main__":
    main()
