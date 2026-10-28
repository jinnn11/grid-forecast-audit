import pandas as pd
import pytest

from grid_audit.history import (
    RawFile,
    combine,
    file_summary,
    half_year,
    header_differences,
    header_section,
    level_shifts,
)

NAN = float("nan")
F1, F2, F3 = (
    "EIA930_BALANCE_2015_Jul_Dec.csv",
    "EIA930_BALANCE_2016_Jan_Jun.csv",
    "EIA930_BALANCE_2016_Jul_Dec.csv",
)


def hours(rows: list[tuple[str, str, float, float, float]]) -> pd.DataFrame:
    """Per-file table from (ba, UTC time, demand, forecast, demand_adjusted) tuples."""
    frame = pd.DataFrame(rows, columns=["ba", "utc", "demand", "forecast", "demand_adjusted"])
    frame["utc"] = pd.to_datetime(frame["utc"], utc=True)
    return frame


def test_half_year() -> None:
    assert half_year(F1) == "2015 H2"
    assert half_year(F2) == "2016 H1"
    with pytest.raises(ValueError):
        half_year("EIA930_INTERCHANGE_2016_Jan_Jun.csv")


def test_header_differences() -> None:
    assert header_differences(["a", "b", "x"], ["a", "b", "c"]) == (["c"], ["x"])
    assert header_differences(["a"], ["a"]) == ([], [])


def test_combine_drops_identical_rows_and_keeps_first_file() -> None:
    first = hours([("X", "2016-01-01 05:00", 10, 11, NAN), ("X", "2016-01-01 06:00", 12, 13, NAN)])
    # 06:00 repeats identically in the second file; 07:00 is new.
    second = hours([("X", "2016-01-01 06:00", 12, 13, NAN), ("X", "2016-01-01 07:00", 14, 15, 14)])
    combined = combine({F1: first, F2: second})
    assert combined.exact_duplicates == 1
    assert combined.conflicts.empty
    assert list(combined.hourly["demand"]) == [10, 12, 14]
    assert list(combined.hourly["source_file"].astype(str)) == [F1, F1, F2]
    assert list(combined.hourly["source_file"].cat.categories) == [F1, F2]


def test_combine_reports_conflicting_rows() -> None:
    first = hours([("X", "2016-01-01 05:00", 10, 11, NAN), ("X", "2016-01-01 06:00", 12, 13, NAN)])
    second = hours([("X", "2016-01-01 06:00", 99, 13, NAN)])
    combined = combine({F1: first, F2: second})
    # Both versions of 06:00 are reported and neither is kept.
    assert len(combined.conflicts) == 2
    assert sorted(combined.conflicts["demand"]) == [12, 99]
    assert list(combined.hourly["demand"]) == [10]


def test_file_summary() -> None:
    first = hours(
        [
            ("X", "2015-07-01 06:00", 10, 11, NAN),
            ("X", "2015-07-01 07:00", NAN, 11, NAN),
            ("G", "2015-07-01 06:00", NAN, NAN, NAN),
        ]
    )
    second = hours([("X", "2016-01-01 07:00", 14, 15, 14)])
    summary = file_summary(combine({F1: first, F2: second}).hourly)
    assert list(summary["rows"]) == [3, 1]
    assert list(summary["bas"]) == [2, 1]
    assert list(summary["bas_with_demand"]) == [1, 1]  # G never reports demand
    assert summary.loc[F1, "demand_pct"] == pytest.approx(100 / 3)  # 1 of 3 rows
    assert summary.loc[F1, "adjusted_pct"] == pytest.approx(0.0)
    assert summary.loc[F2, "adjusted_pct"] == pytest.approx(100.0)
    assert summary.loc[F1, "last_utc"] == pd.Timestamp("2015-07-01 07:00", tz="UTC")


def test_level_shifts() -> None:
    # X: medians 100, then 160 (x1.60, flagged), then 150 (x0.94; the 0 and -5 are ignored).
    # Y: medians 100, then 60 (x0.60, flagged).
    x1 = [("X", f"2015-07-01 0{h}:00", 100, 1, NAN) for h in range(3)]
    y1 = [("Y", "2015-07-01 00:00", 100, 1, NAN)]
    x2 = [("X", "2016-01-01 00:00", 150, 1, NAN), ("X", "2016-01-01 01:00", 170, 1, NAN)]
    y2 = [("Y", "2016-01-01 00:00", 60, 1, NAN)]
    x3 = [
        ("X", "2016-07-01 00:00", 150, 1, NAN),
        ("X", "2016-07-01 01:00", 0, 1, NAN),
        ("X", "2016-07-01 02:00", -5, 1, NAN),
    ]
    hourly = combine({F1: hours(x1 + y1), F2: hours(x2 + y2), F3: hours(x3)}).hourly
    shifts = level_shifts(hourly)
    assert list(shifts["ba"]) == ["X", "Y"]
    assert list(shifts["half_year"]) == ["2016 H1", "2016 H1"]
    assert list(shifts["ratio"]) == pytest.approx([1.6, 0.6])
    assert shifts.loc[0, "previous_mw"] == 100 and shifts.loc[0, "median_mw"] == 160


def raw(name: str, header: list[str]) -> RawFile:
    url = "https://example.invalid/" + name
    return RawFile(name, url, 1, pd.Timestamp(0, tz="UTC"), "", header)


def test_header_section_groups_files_that_differ_the_same_way() -> None:
    reference = raw(F3, ["a", "b", "c"])
    files = [raw(F1, ["a", "b"]), raw(F2, ["a", "b"]), reference]
    text = header_section(files, reference, ["a"])
    assert 'All 3 files have the required columns ("a").' in text
    assert "### 2015 H2 to 2016 H1 (2 columns)" in text
    assert "- Missing compared with the reference (1): `c`" in text
    assert "### 2016 H2 (3 columns)" in text


def test_header_section_names_missing_required_columns() -> None:
    reference = raw(F2, ["a", "b"])
    text = header_section([raw(F1, ["b"]), reference], reference, ["a", "b"])
    assert "**Required columns missing (the combined table was not written):**" in text
    assert f"- `{F1}`: a" in text
