"""Cached downloads (EIA-930 files, and the operator files the user approved on 2026-10-28):
each file is fetched at most once."""

import shutil
import subprocess
import urllib.request
from pathlib import Path

BASE_URL = "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/"
RAW_DIR = Path("data/raw")
USER_AGENT = "grid-forecast-audit/0.1"
HALVES = {1: "Jan_Jun", 2: "Jul_Dec"}


def balance_file_name(year: int, half: int) -> str:
    """Name of a six-month BALANCE file, e.g. (2026, 1) -> EIA930_BALANCE_2026_Jan_Jun.csv."""
    return f"EIA930_BALANCE_{year}_{HALVES[half]}.csv"


def balance_file_names(first: tuple[int, int], last: tuple[int, int]) -> list[str]:
    """BALANCE file names from `first` to `last` inclusive, each given as (year, half)."""
    (year, half), names = first, []
    while (year, half) <= last:
        names.append(balance_file_name(year, half))
        year, half = (year, 2) if half == 1 else (year + 1, 1)
    return names


def fetch(name: str, raw_dir: Path = RAW_DIR, base_url: str = BASE_URL) -> Path:
    """Return the cached path of `name`, downloading it only if it is not cached yet."""
    path = raw_dir / name
    if path.exists():
        return path
    raw_dir.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    request = urllib.request.Request(base_url + name, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as out:
        shutil.copyfileobj(response, out)
    partial.replace(path)
    return path


def fetch_url(url: str, path: Path) -> Path:
    """Return `path`, downloading `url` to it with curl only if it is not cached yet.

    curl checks certificates against the system's trust store. Python's bundled certificate
    file lacks some current roots (CAISO OASIS chains to Sectigo's 2021 root R46), and
    certificate checks stay on.
    """
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    command = ["curl", "--silent", "--show-error", "--fail", "--max-time", "120"]
    command += ["--user-agent", USER_AGENT, "--output", str(partial), url]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(path)
    return path
