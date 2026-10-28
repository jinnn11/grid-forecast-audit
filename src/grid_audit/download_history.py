"""Step 2: fetch every BALANCE file, one at a time.

Run: uv run python -m grid_audit.download_history
Files already in data/raw/ are skipped. Stops at the first error.
"""

import time

from grid_audit.download import RAW_DIR, balance_file_names, fetch

FIRST, LAST = (2015, 2), (2026, 1)  # EIA-930 starts in July 2015
PAUSE_SECONDS = 2


def main() -> None:
    names = balance_file_names(FIRST, LAST)
    for number, name in enumerate(names, start=1):
        cached = (RAW_DIR / name).exists()
        path = fetch(name)
        status = "cached" if cached else "downloaded"
        print(f"{number}/{len(names)} {status} {path} ({path.stat().st_size:,} bytes)", flush=True)
        if not cached:
            time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main()
