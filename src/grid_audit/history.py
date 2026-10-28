"""Combine six-month BALANCE files into one hourly table, with schema, duplicate and unit checks."""

import re
from dataclasses import dataclass

import pandas as pd

from grid_audit.check import fmt, markdown_table

FILE_PATTERN = re.compile(r"EIA930_BALANCE_(\d{4})_(Jan_Jun|Jul_Dec)\.csv")
# A BA half-year is flagged when its median demand is outside these multiples of the previous one.
LEVEL_SHIFT_LOW, LEVEL_SHIFT_HIGH = 2 / 3, 1.5


def half_year(file_name: str) -> str:
    """'EIA930_BALANCE_2015_Jul_Dec.csv' -> '2015 H2'."""
    match = FILE_PATTERN.fullmatch(file_name)
    if match is None:
        raise ValueError(f"not a BALANCE file name: {file_name}")
    return f"{match[1]} H{1 if match[2] == 'Jan_Jun' else 2}"


def header_differences(header: list[str], reference: list[str]) -> tuple[list[str], list[str]]:
    """Columns in `reference` but not in `header`, and in `header` but not in `reference`."""
    return [c for c in reference if c not in header], [c for c in header if c not in reference]


@dataclass(frozen=True)
class Combined:
    hourly: pd.DataFrame  # one row per BA and UTC hour, with source_file
    exact_duplicates: int  # rows dropped because an identical BA/hour row came earlier
    conflicts: pd.DataFrame  # rows whose BA/hour appears with different values; must be empty


def combine(frames: dict[str, pd.DataFrame]) -> Combined:
    """Stack per-file tables in the given order, tagging each row with its source file.

    BA/hour rows identical in every column are dropped (the first is kept). BA/hour rows that
    disagree are returned in `conflicts` rather than resolved.
    """
    stacked = pd.concat(
        [frame.assign(source_file=name) for name, frame in frames.items()], ignore_index=True
    )
    exact = stacked.drop(columns="source_file").duplicated()
    kept = stacked[~exact]
    clashing = kept.duplicated(["ba", "utc"], keep=False)
    hourly = kept[~clashing].sort_values(["ba", "utc"], ignore_index=True)
    hourly["source_file"] = pd.Categorical(hourly["source_file"], categories=list(frames))
    return Combined(hourly, int(exact.sum()), kept[clashing].reset_index(drop=True))


def file_summary(hourly: pd.DataFrame) -> pd.DataFrame:
    """Per source file: rows, BAs, BAs reporting demand, first and last hour, and the share of
    rows with demand and with adjusted demand reported."""
    by_file = hourly["source_file"]
    groups = hourly.groupby(by_file, observed=True)
    reported = hourly[["demand", "demand_adjusted"]].notna().groupby(by_file, observed=True)
    return pd.DataFrame(
        {
            "rows": groups.size(),
            "bas": groups["ba"].nunique(),
            "bas_with_demand": hourly["ba"]
            .where(hourly["demand"].notna())
            .groupby(by_file, observed=True)
            .nunique(),
            "first_utc": groups["utc"].min(),
            "last_utc": groups["utc"].max(),
            "demand_pct": 100 * reported["demand"].mean(),
            "adjusted_pct": 100 * reported["demand_adjusted"].mean(),
        }
    )


def level_shifts(hourly: pd.DataFrame) -> pd.DataFrame:
    """BA half-years whose median positive demand is below LEVEL_SHIFT_LOW or above
    LEVEL_SHIFT_HIGH times the BA's median in its previous half-year with demand.

    A shift can mean a footprint change or a unit change; it is reported, never corrected.
    """
    positive = hourly[hourly["demand"] > 0]
    medians = (
        positive.groupby(["ba", "source_file"], observed=True)["demand"]
        .median()
        .rename("median_mw")
        .reset_index()
    )
    medians["half_year"] = medians["source_file"].astype(str).map(half_year)
    medians = medians.sort_values(["ba", "half_year"])
    medians["previous_mw"] = medians.groupby("ba")["median_mw"].shift()
    medians["ratio"] = medians["median_mw"] / medians["previous_mw"]
    flagged = medians[(medians["ratio"] < LEVEL_SHIFT_LOW) | (medians["ratio"] > LEVEL_SHIFT_HIGH)]
    return flagged[["ba", "half_year", "previous_mw", "median_mw", "ratio"]].reset_index(drop=True)


@dataclass(frozen=True)
class RawFile:
    name: str
    url: str
    size: int
    downloaded: pd.Timestamp  # file modification time, UTC
    sha256: str
    header: list[str]


def header_section(files: list[RawFile], reference: RawFile, required: list[str]) -> str:
    """Column differences against the reference header, grouping neighbouring files that differ
    in the same way, and whether every file has the required columns."""
    lines = [
        "## Columns\n",
        f"Reference header: `{reference.name}` ({len(reference.header)} columns).\n",
    ]
    missing_required = {
        f.name: [c for c in required if c not in f.header]
        for f in files
        if any(c not in f.header for c in required)
    }
    if missing_required:
        lines.append("**Required columns missing (the combined table was not written):**\n")
        lines += [f"- `{name}`: {', '.join(cols)}" for name, cols in missing_required.items()]
        lines.append("")
    else:
        names = ", ".join(f'"{c}"' for c in required)
        lines.append(f"All {len(files)} files have the required columns ({names}).\n")
    groups: list[tuple[list[RawFile], tuple[list[str], list[str]]]] = []
    for f in files:
        diff = header_differences(f.header, reference.header)
        if groups and groups[-1][1] == diff:
            groups[-1][0].append(f)
        else:
            groups.append(([f], diff))
    for members, (missing, extra) in groups:
        first, last = half_year(members[0].name), half_year(members[-1].name)
        span = first if first == last else f"{first} to {last}"
        lines.append(f"### {span} ({len(members[0].header)} columns)\n")
        lines.append(f"- Missing compared with the reference ({len(missing)}): " + _names(missing))
        lines.append(f"- Not in the reference ({len(extra)}): " + _names(extra) + "\n")
    return "\n".join(lines)


def _names(columns: list[str]) -> str:
    return ", ".join(f"`{c}`" for c in columns) if columns else "none"


def render_schema_report(
    files: list[RawFile],
    reference: RawFile,
    required: list[str],
    combined: Combined | None,
) -> str:
    """results/schema_check.md. `combined` is None when the files could not be combined."""
    file_rows = [
        [f.name, fmt(f.size, 0), f"{f.downloaded:%Y-%m-%d %H:%M}", f"`{f.sha256}`"] for f in files
    ]
    parts = [
        "# Schema check: EIA-930 BALANCE files\n",
        f"{len(files)} six-month files, each from `{files[0].url.rsplit('/', 1)[0]}/` plus the "
        "file name. The download time is the file's modification time.\n",
        "## Files\n",
        markdown_table(["File", "Bytes", "Downloaded (UTC)", "SHA-256"], file_rows) + "\n",
        header_section(files, reference, required),
    ]
    if combined is None:
        return "\n".join(parts)
    summary = file_summary(combined.hourly)
    rows = [
        [
            half_year(str(row.Index)),
            fmt(row.rows, 0),
            fmt(row.bas, 0),
            fmt(row.bas_with_demand, 0),
            f"{row.first_utc:%Y-%m-%d %H:%M}",
            f"{row.last_utc:%Y-%m-%d %H:%M}",
            fmt(row.demand_pct, 1),
            fmt(row.adjusted_pct, 1),
        ]
        for row in summary.itertuples()
    ]
    header = [
        "Half-year",
        "Rows",
        "BAs",
        "BAs with demand",
        "First hour (UTC)",
        "Last hour (UTC)",
        "Demand reported (%)",
        "Adjusted demand reported (%)",
    ]
    shifts = level_shifts(combined.hourly)
    shift_rows = [
        [r.ba, r.half_year, fmt(r.previous_mw, 0), fmt(r.median_mw, 0), f"{r.ratio:.2f}"]
        for r in shifts.itertuples()
    ]
    conflict_text = (
        "none"
        if combined.conflicts.empty
        else f"**{len(combined.conflicts)} rows; the combined table was not written**"
    )
    parts += [
        "## Rows\n",
        markdown_table(header, rows) + "\n",
        "## Duplicates\n",
        f"- Identical BA/hour rows in more than one file, dropped: {combined.exact_duplicates:,}",
        f"- BA/hour rows that disagree between files: {conflict_text}\n",
        "## Units\n",
        "- The columns we use have the same names in every file, so every file states them in "
        "MW: " + ", ".join(f'"{c}"' for c in required if "(MW)" in c) + ".",
        f"- Magnitude check: BA half-years whose median positive demand is below "
        f"{LEVEL_SHIFT_LOW:.2f} or above {LEVEL_SHIFT_HIGH:.2f} times the BA's previous "
        f"half-year. A shift can mean a footprint change, a unit change or bad data; these are "
        f"reported, not corrected. {len(shifts)} flagged.\n",
        markdown_table(
            ["BA", "Half-year", "Previous median (MW)", "Median (MW)", "Ratio"], shift_rows
        )
        + "\n",
    ]
    return "\n".join(parts)
