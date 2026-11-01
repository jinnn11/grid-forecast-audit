"""Q5 step 2: fetch the approved operator files, one at a time.

Run: uv run python -m grid_audit.download_operators
Files already in data/raw/operators/ are skipped. A refused OASIS query (an error XML instead of
a CSV) is deleted, so it is never mistaken for data, and retried after a wait; anything else
stops the run.
"""

import time

from grid_audit.download import fetch_url
from grid_audit.operators import planned_files, read_oasis

PAUSE_SECONDS = {"caiso": 10.0, "spp": 1.5, "caiso_outlook": 1.5}  # OASIS: ~1 query per 5 s
OASIS_RETRY_WAITS = (60.0, 180.0)  # seconds before each retry of a refused OASIS query


def fetch_oasis(url: str, path) -> None:
    for wait in (*OASIS_RETRY_WAITS, None):
        fetch_url(url, path)
        try:
            read_oasis(path)
            return
        except ValueError as refused:
            path.unlink()
            if wait is None:
                raise
            print(f"refused ({refused}); retrying in {wait:.0f} s", flush=True)
            time.sleep(wait)


def main() -> None:
    files = planned_files()
    for number, (url, path) in enumerate(files, start=1):
        if path.exists():
            continue
        source = path.parent.name
        if source == "caiso":
            fetch_oasis(url, path)
        else:
            fetch_url(url, path)
        size = path.stat().st_size
        print(f"{number}/{len(files)} downloaded {path} ({size:,} bytes)", flush=True)
        time.sleep(PAUSE_SECONDS[source])
    print(f"all {len(files)} files cached")


if __name__ == "__main__":
    main()
