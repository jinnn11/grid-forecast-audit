"""Step 1 go/no-go data check. Run: uv run python -m grid_audit.data_check"""

import hashlib
from pathlib import Path

from grid_audit.balance import read_balance
from grid_audit.check import Source, ba_stats, render_report
from grid_audit.download import BASE_URL, balance_file_name, fetch

YEAR, HALF = 2026, 1  # most recent complete six-month file as of 2026-10-26
REPORT_PATH = Path("results/data_check.md")


def sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main() -> None:
    name = balance_file_name(YEAR, HALF)
    path = fetch(name)
    hourly = read_balance(path)
    source = Source(name, BASE_URL + name, sha256(path), hourly["utc"].min(), hourly["utc"].max())
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(render_report(ba_stats(hourly), source), encoding="utf-8")
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
