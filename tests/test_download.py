from pathlib import Path

from grid_audit.download import balance_file_name, fetch


def test_balance_file_name() -> None:
    assert balance_file_name(2026, 1) == "EIA930_BALANCE_2026_Jan_Jun.csv"
    assert balance_file_name(2025, 2) == "EIA930_BALANCE_2025_Jul_Dec.csv"


def test_fetch_returns_cached_file_without_downloading(tmp_path: Path) -> None:
    cached = tmp_path / "EIA930_BALANCE_2026_Jan_Jun.csv"
    cached.write_text("cached")
    # conftest blocks sockets, so any download attempt would raise.
    path = fetch(cached.name, raw_dir=tmp_path, base_url="https://example.invalid/")
    assert path == cached
    assert path.read_text() == "cached"
