"""Q5 step 2: CAISO's and SPP's own load and day-ahead forecast against EIA-930.

Run: uv run python -m grid_audit.operator_check (after grid_audit.download_operators)
Writes results/operator_check.md, and results/operator_files.csv with every cached operator file's
URL, size, download time and SHA-256. Reads only cached files.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from grid_audit.audit import MONTHS
from grid_audit.calendar import local_hours
from grid_audit.check import fmt, markdown_table
from grid_audit.data_check import sha256
from grid_audit.data_quality import apply_rules
from grid_audit.operators import (
    ALIGNED_GAP_PCT,
    CAISO_AREA,
    CAISO_MONTHS,
    CAISO_RUNS,
    EQUAL_MW,
    NAIVE_HOURS,
    OPERATORS_DIR,
    SPP_ISSUE_HOUR,
    alignment,
    caiso_series,
    monthly,
    moved,
    oasis_file,
    offset_runs,
    read_oasis,
    read_spp,
    score_table,
    source_url,
    spp_issues,
    spp_name,
    spp_series,
)
from grid_audit.quality_rules import EVENTS_PATH, PARQUET_PATH, read_events

REPORT_PATH = Path("results/operator_check.md")
MIN_RUN_DAYS = 3  # shorter runs of days are counted, not listed
MANIFEST_PATH = Path("results/operator_files.csv")


@dataclass(frozen=True)
class Period:
    operator: str
    ba: str
    label: str
    first: str  # local days, inclusive
    last: str


PERIODS = [
    Period("CAISO", "CISO", "2025", "2025-01-01", "2025-12-31"),
    Period("CAISO", "CISO", "Jan–Jun 2026", "2026-01-01", "2026-06-30"),
    Period("SPP", "SWPP", "2025", "2025-01-01", "2025-12-31"),
]


def manifest() -> pd.DataFrame:
    """Every cached operator file: path, URL, bytes, download time (file time, UTC), SHA-256."""
    rows = []
    for path in sorted(OPERATORS_DIR.glob("*/*")):
        stat = path.stat()
        downloaded = pd.Timestamp(stat.st_mtime, unit="s", tz="UTC")
        rows.append(
            {
                "file": path.as_posix(),
                "url": source_url(path),
                "bytes": stat.st_size,
                "downloaded_utc": f"{downloaded:%Y-%m-%d %H:%M:%S}",
                "sha256": sha256(path),
            }
        )
    return pd.DataFrame(rows)


def operator_series() -> tuple[dict[str, pd.DataFrame], int]:
    """Each operator's forecast and actual by UTC hour end, and SPP's revised-actual count."""
    months = {
        run: [read_oasis(oasis_file(run, m, OPERATORS_DIR / "caiso")[1]) for m in CAISO_MONTHS]
        for run in CAISO_RUNS
    }
    issues = {i: read_spp(OPERATORS_DIR / "spp" / spp_name(i)) for i in spp_issues()}
    spp, revised = spp_series(issues)
    return {"CAISO": caiso_series(months), "SPP": spp}, revised


def period_hours(
    hourly: pd.DataFrame,
    local: pd.DataFrame,
    usable: pd.Series,
    operator: pd.DataFrame,
    period: Period,
) -> pd.DataFrame:
    """The BA's hours in the period (local days), by UTC hour end: EIA's demand and forecast as
    published, the audit's usable flag, local month and day, and the operator's two series."""
    first, last = pd.Timestamp(period.first), pd.Timestamp(period.last)
    rows = hourly["ba"].eq(period.ba) & local["day"].between(first, last)
    eia = hourly[rows]
    frame = pd.DataFrame(
        {
            "eia_demand": eia["demand"].to_numpy(),
            "eia_forecast": eia["forecast"].to_numpy(),
            "usable": usable[rows].to_numpy(),
            "month": local.loc[rows, "month"].to_numpy(),
            "day": local.loc[rows, "day"].to_numpy(),
        },
        index=pd.DatetimeIndex(eia["utc"]),
    )
    frame["op_actual"] = operator["actual"].reindex(frame.index)
    frame["op_forecast"] = operator["forecast"].reindex(frame.index)
    return frame


@dataclass(frozen=True)
class Comparison:
    period: Period
    hours: pd.DataFrame
    demand_alignment: pd.DataFrame
    forecast_alignment: pd.DataFrame
    scores: pd.DataFrame  # over the audit's usable hours with both operator series
    months: pd.DataFrame
    demand_runs: pd.DataFrame  # days on which the same shift aligns demand best
    forecast_runs: pd.DataFrame


def compare(hours: pd.DataFrame, operator: pd.DataFrame, period: Period) -> Comparison:
    hours = hours.assign(
        eia_naive=moved(hours["eia_demand"], hours.index, NAIVE_HOURS),
        op_naive=moved(operator["actual"], hours.index, NAIVE_HOURS),
    )
    scored = hours[hours["usable"] & hours["op_actual"].notna() & hours["op_forecast"].notna()]
    return Comparison(
        period,
        hours,
        alignment(hours["eia_demand"], operator["actual"]),
        alignment(hours["eia_forecast"], operator["forecast"]),
        score_table(scored),
        monthly(scored, scored["month"]),
        offset_runs(hours["eia_demand"], operator["actual"], hours["day"]),
        offset_runs(hours["eia_forecast"], operator["forecast"], hours["day"]),
    )


def alignment_rows(c: Comparison) -> list[list[str]]:
    rows = []
    for k in c.demand_alignment.index:
        d, f = c.demand_alignment.loc[k], c.forecast_alignment.loc[k]
        rows.append(
            [
                f"{k:+d} h" if k else "0 (as published)",
                fmt(d["hours"], 0),
                fmt(d["equal_pct"], 1),
                fmt(d["mean_gap_pct"], 2),
                fmt(f["hours"], 0),
                fmt(f["equal_pct"], 1),
                fmt(f["mean_gap_pct"], 2),
            ]
        )
    return rows


def shift_label(shift: object) -> str:
    if pd.isna(shift):
        return f"none (gap above {fmt(ALIGNED_GAP_PCT, 0)}% at every shift)"
    return "as published" if shift == 0 else f"operator moved {int(shift):+d} h"


def run_rows(c: Comparison) -> tuple[list[list[str]], list[str]]:
    """Runs of at least MIN_RUN_DAYS days, and per series a note on the days in shorter runs."""
    rows, notes = [], []
    for name, runs in (("Demand", c.demand_runs), ("Forecast", c.forecast_runs)):
        long = runs[runs["days"] >= MIN_RUN_DAYS]
        rows += [
            [
                name,
                f"{r.first:%Y-%m-%d}",
                f"{r.last:%Y-%m-%d}",
                fmt(r.days, 0),
                shift_label(r.shift),
            ]
            for r in long.itertuples()
        ]
        short = runs[runs["days"] < MIN_RUN_DAYS]
        if len(short):
            notes.append(f"{name}: {short['days'].sum()} days in {len(short)} shorter runs.")
    return rows, notes


def comparison_section(c: Comparison) -> list[str]:
    p = c.period
    runs, run_notes = run_rows(c)
    score_rows = [
        [
            forecast,
            truth,
            fmt(s.hours, 0),
            fmt(s.mape, 2),
            fmt(s.bias, 2),
            fmt(s.mape_moved, 2),
            fmt(s.skill, 2),
        ]
        for (forecast, truth), s in c.scores.iterrows()
    ]
    month_rows = [
        [
            f"{month:02d}",
            fmt(m.demand_ratio, 4),
            fmt(m.forecast_ratio, 4),
            fmt(m.eia_bias, 2),
            fmt(m.op_bias, 2),
        ]
        for month, m in c.months.iterrows()
    ]
    return [
        f"## {p.operator} against EIA-930 {p.ba}, {p.label}\n",
        "### Hour alignment\n",
        "The operator's series moved k hours later (its value for hour t − k set against "
        f"EIA's at t), over all hours with both values. Equal: within {fmt(EQUAL_MW, 0)} MW. "
        "Gap: mean absolute difference as a percent of EIA's mean.\n",
        markdown_table(
            [
                "Operator moved by",
                "Demand hours",
                "Demand equal (%)",
                "Demand gap (%)",
                "Forecast hours",
                "Forecast equal (%)",
                "Forecast gap (%)",
            ],
            alignment_rows(c),
        )
        + "\n",
        "Day by day (local days), the shift of −1, 0 or +1 h with the smallest gap, as runs of "
        f"at least {MIN_RUN_DAYS} days. A day aligns at no shift when even the best gap is "
        f"above {fmt(ALIGNED_GAP_PCT, 0)}%.\n",
        markdown_table(
            ["Series", "First day", "Last day", "Days", "Best shift"], runs, left_columns=1
        )
        + "\n",
        " ".join(run_notes) + "\n" if run_notes else "",
        "### MAPE and bias\n",
        "Each forecast against each truth, over the audit's usable hours where the operator "
        'reports both series. "Moved +1 h": the forecast moved one hour later, as in the '
        "audit's Q5 check. Skill: 1 − MAPE / MAPE of that truth 24 hours earlier, on the hours "
        "that have it (below 0: loses to the naive forecast).\n",
        markdown_table(
            ["Forecast", "Truth", "Hours", "MAPE (%)", "Bias (%)", "MAPE moved +1 h (%)", "Skill"],
            score_rows,
            left_columns=2,
        )
        + "\n",
        "### By local month\n",
        "Medians of EIA / operator for demand and forecast; bias of each forecast against its "
        "own source's truth (Σe / Σ demand, %).\n",
        markdown_table(
            [
                "Month",
                "Demand EIA / operator",
                "Forecast EIA / operator",
                "EIA bias (%)",
                "Operator bias (%)",
            ],
            month_rows,
        )
        + "\n",
    ]


def files_section(files: pd.DataFrame, revised: int) -> list[str]:
    source = files["file"].str.split("/").str[-2]
    rows = [
        [
            name.upper(),
            fmt(len(group), 0),
            fmt(group["bytes"].sum(), 0),
            f"{group['downloaded_utc'].min()} to {group['downloaded_utc'].max()}",
        ]
        for name, group in files.groupby(source)
    ]
    return [
        "## Files\n",
        f"Cached under `{OPERATORS_DIR}/`, one at a time; each file's URL, size, download time "
        f"and SHA-256 are in `{MANIFEST_PATH}`.\n",
        markdown_table(["Source", "Files", "Bytes", "Downloaded (UTC)"], rows) + "\n",
        f"- CAISO OASIS, query `SLD_FCST`, area `{CAISO_AREA}` (the CAISO balancing authority "
        'area): `DAM` is "Demand Forecast Day Ahead", `ACTUAL` is "Total Actual Hourly '
        'Integrated Load". One query per month and run, Pacific midnight to Pacific midnight '
        "(OASIS counts its 31-day limit in Pacific days; the first five files used 08:00 UTC "
        "and are kept). OASIS names its files by request time, so they are cached as "
        "`CAISO_SLD_FCST_<run>_<month>_<UTC window>.zip`. No account, login or terms were "
        "needed. On 2026-10-30 a further 13 months were fetched to date CISO's one-hour lag "
        "(July 2016–2024, then Jan 2016, Sep 2016 and Jun 2022; `results/ciso_check.md`); "
        "they are listed here but not used below.",
        "- SPP Marketplace portal, folder `mtlf-vs-actual`: one file per issue hour with the "
        "mid-term load forecast (MTLF) and the averaged actual load. No account, login or terms "
        "were needed. To find which issue is SPP's day-ahead forecast, all 24 issues of "
        "2025-01-01 were fetched: EIA-930's SWPP forecast for 2025-01-02 equals the "
        f"{SPP_ISSUE_HOUR:02d}:00 issue in all 24 hours and no other issue in more than one. "
        f"SPP's day-ahead forecast for each day of 2025 is taken as the {SPP_ISSUE_HOUR:02d}:00 "
        "issue of the day before (04:00 on 2025-03-09, when clocks go forward and SPP has no "
        "03:00 file). Over the year EIA's forecast follows it closely but is rarely identical "
        "(see the findings), so EIA most often reports another issue. The actual load comes "
        f"from the same files (the latest issue wins; {revised} hours differ between issues).",
        "- SPP keeps 2024 only as a yearly archive (`2024.zip`), which holds a year of data "
        "outside the approval and was not fetched. Without its 2024-12-31 issue, SPP's "
        "forecast for 2025-01-01 is missing; that day's actual load is covered.\n",
    ]


def render(comparisons: list[Comparison], files: pd.DataFrame, revised: int, findings: list[str]):
    parts = [
        "# Operator check (Q5 step 2): CAISO and SPP against EIA-930\n",
        "Step 2 of the plan's Q5 checks, for the 10 largest BAs that lose to the naive forecast. "
        "Approved by the user on 2026-10-28, narrowly: CAISO's own day-ahead load forecast and "
        "actual load for 2025 and Jan–Jun 2026, and SPP's for 2025. FPL (losing in 2016–2017) "
        "has no public hourly forecast archive that we know of. Nothing here changes the "
        "audit's results.\n",
        "## Findings\n",
        *findings,
        "",
        *files_section(files, revised),
    ]
    for c in comparisons:
        parts += comparison_section(c)
    return "\n".join(parts)


def main() -> None:
    files = manifest()
    files.to_csv(MANIFEST_PATH, index=False)
    hourly = pd.read_parquet(PARQUET_PATH)
    applied = apply_rules(hourly, read_events(EVENTS_PATH))
    local = local_hours(hourly["local"])
    operators, revised = operator_series()
    comparisons = []
    for period in PERIODS:
        operator = operators[period.operator]
        hours = period_hours(hourly, local, applied.usable, operator, period)
        comparisons.append(compare(hours, operator, period))
    REPORT_PATH.write_text(render(comparisons, files, revised, findings(comparisons)), "utf-8")
    print(f"wrote {REPORT_PATH} and {MANIFEST_PATH}")


def runs_with(runs: pd.DataFrame, shift: int | None) -> pd.DataFrame:
    """Runs of at least MIN_RUN_DAYS days at `shift` (None: aligned at no shift)."""
    at = runs["shift"].isna() if shift is None else runs["shift"].eq(shift).fillna(False)
    return runs[at & runs["days"].ge(MIN_RUN_DAYS)]


def days_at(runs: pd.DataFrame, shift: int | None, first: pd.Timestamp, last: pd.Timestamp):
    """Days from `first` to `last` (runs of any length) at `shift` (None: no shift), and all
    days with data in that span."""
    inside = runs[runs["first"].ge(first) & runs["last"].le(last)]
    at = inside["shift"].isna() if shift is None else inside["shift"].eq(shift).fillna(False)
    return int(inside.loc[at, "days"].sum()), int(inside["days"].sum())


def signed(bias: float) -> str:
    """-6.91 -> '6.9% below'."""
    return f"{fmt(abs(bias), 1)}% {'below' if bias < 0 else 'above'}"


def caiso_conclusion(c25: Comparison, c26: Comparison) -> list[str]:
    """Whether CISO's one-hour lead comes from EIA-930's data or CAISO's forecast."""
    own = c25.scores.loc[("Operator", "Operator")]
    late = runs_with(c25.demand_runs, 1)
    equal = min(c.forecast_alignment.loc[0, "equal_pct"] for c in (c25, c26))
    d = c25.demand_alignment
    if not (equal >= 99 and len(late) and own.mape < own.mape_moved):
        return [
            "- **CISO:** the data do not settle where the one-hour lead comes from; see the "
            "tables below."
        ]
    first, last = late["first"].min(), late["last"].max()
    late_days, all_days = days_at(c25.demand_runs, 1, first, last)
    after = c25.demand_runs[c25.demand_runs["first"] > last]
    since = f"{after['first'].min():%Y-%m-%d}" if len(after) else "the end of 2025"
    own26 = c26.scores.loc[("Operator", "Operator")]
    loses = "would still lose" if own.skill < 0 else "would not lose"
    return [
        "- **CISO's one-hour lead comes from EIA-930's demand data, not from CAISO's forecast.**",
        f"  - EIA's CISO forecast is CAISO's own day-ahead forecast, unshifted, in "
        f"{fmt(equal, 1)}% of hours in both periods.",
        f"  - EIA's CISO demand is CAISO's actual load one hour late on {late_days} of the "
        f"{all_days} days with data from {first:%Y-%m-%d} to {last:%Y-%m-%d}: it lines up "
        "with CAISO's "
        f"load moved +1 h (mean gap {fmt(d.loc[1, 'mean_gap_pct'], 2)}%, "
        f"against {fmt(d.loc[0, 'mean_gap_pct'], 2)}% as published). From {since} it lines up "
        "as published, which is why the shift did not help in Jan–Jun 2026.",
        f"  - Against its own load, CAISO's forecast does best as published (MAPE "
        f"{fmt(own.mape, 2)}%, {fmt(own.mape_moved, 2)}% moved +1 h).",
        f"  - The rest of CISO's error is in CAISO's own published series: its day-ahead "
        f"forecast is {signed(own.bias)} its own actual load in 2025 and "
        f"{signed(own26.bias)} in Jan–Jun 2026 (MAPE {fmt(own.mape, 2)}% and "
        f"{fmt(own26.mape, 2)}%). With CAISO's own data, CISO {loses} to the naive forecast "
        f"in 2025 (skill {fmt(own.skill, 2)}). Most of that gap is battery charging, which "
        "CAISO's actual load counts and its day-ahead forecast leaves out "
        "(`results/ciso_check.md`).",
        "  - The same late demand covers 2016-01 to 2016-09-12 and 2022-06-14 to 2025-12-02, "
        "checked against CAISO's data back to 2016 (approved 2026-10-30; "
        "`results/ciso_check.md`).",
    ]


def spp_conclusion(c: Comparison) -> list[str]:
    """Whether SWPP's over-forecast comes from EIA-930's data or SPP's forecast."""
    own, eia = c.scores.loc[("Operator", "Operator")], c.scores.loc[("EIA-930", "EIA-930")]
    apart = runs_with(c.forecast_runs, None)
    high = c.months[c.months["forecast_ratio"] > 1 + ALIGNED_GAP_PCT / 100]
    demand = c.months["demand_ratio"]
    if not (len(apart) and len(high) and abs(own.bias) < 2 and demand.sub(1).abs().max() < 0.02):
        return [
            "- **SWPP:** the data do not settle where the over-forecast comes from; see the "
            "tables below."
        ]
    start, end = apart["first"].min(), c.forecast_runs["last"].max()
    before_apart, before = days_at(c.forecast_runs, None, c.forecast_runs["first"].min(), start)
    after_apart, after = days_at(c.forecast_runs, None, start, end)
    loses = "would lose" if own.skill < 0 else "would not lose"
    return [
        "- **SWPP's over-forecast comes from EIA-930's forecast data, not from SPP's forecast.**",
        f"  - Until {start - pd.Timedelta(days=1):%Y-%m-%d} EIA's SWPP forecast follows SPP's "
        f"own day-ahead forecast: within {fmt(ALIGNED_GAP_PCT, 0)}% on {before - before_apart} "
        f"of {before} days. From {start:%Y-%m-%d} to {end:%Y-%m-%d} it is more than "
        f"{fmt(ALIGNED_GAP_PCT, 0)}% away on {after_apart} of {after} days, at "
        f"{fmt(high['forecast_ratio'].min(), 2)}–"
        f"{fmt(high['forecast_ratio'].max(), 2)} times SPP's forecast by monthly median in "
        f"{MONTHS[high.index.min() - 1]}–{MONTHS[high.index.max() - 1]}.",
        f"  - EIA's SWPP demand matches SPP's actual load throughout (monthly medians "
        f"{fmt(demand.min(), 3)}–{fmt(demand.max(), 3)}).",
        f"  - SPP's own forecast is {signed(own.bias)} its own load (MAPE "
        f"{fmt(own.mape, 2)}%); with SPP's own data, SWPP {loses} to the naive forecast in 2025 "
        f"(skill {fmt(own.skill, 2)}). EIA's series gives MAPE {fmt(eia.mape, 2)}% and bias "
        f"{fmt(eia.bias, 2)}%.",
        "  - What changed in the forecast EIA-930 carries for SWPP is not visible in these files; "
        "EIA or SPP would have to say.",
    ]


def best_shift(table: pd.DataFrame) -> int:
    """The shift with the smallest mean gap."""
    return int(table["mean_gap_pct"].idxmin())


def facts(c: Comparison) -> list[str]:
    """What the comparison shows for one period, in numbers."""
    p, d, f, s = c.period, c.demand_alignment, c.forecast_alignment, c.scores
    eia, own = s.loc[("EIA-930", "EIA-930")], s.loc[("Operator", "Operator")]
    lines = [f"- **{p.operator} against {p.ba}, {p.label}.**"]
    for name, table in (("forecast", f), ("demand / actual load", d)):
        k = best_shift(table)
        lines.append(
            f"  - EIA's {name} equals the operator's (within {fmt(EQUAL_MW, 0)} MW) in "
            f"{fmt(table.loc[0, 'equal_pct'], 1)}% of hours as published (mean gap "
            f"{fmt(table.loc[0, 'mean_gap_pct'], 2)}%); the closest alignment is "
            + ("as published" if k == 0 else f"with the operator moved {k:+d} h")
            + f" ({fmt(table.loc[k, 'equal_pct'], 1)}% equal, gap "
            f"{fmt(table.loc[k, 'mean_gap_pct'], 2)}%)."
        )
    lines += [
        f"  - EIA forecast against EIA demand: MAPE {fmt(eia.mape, 2)}%, bias {fmt(eia.bias, 2)}%,"
        f" {fmt(eia.mape_moved, 2)}% moved +1 h.",
        f"  - {p.operator}'s forecast against its own actual load: MAPE {fmt(own.mape, 2)}%, bias "
        f"{fmt(own.bias, 2)}%, {fmt(own.mape_moved, 2)}% moved +1 h.",
    ]
    return lines


def findings(comparisons: list[Comparison]) -> list[str]:
    by_label = {(c.period.ba, c.period.label): c for c in comparisons}
    lines = caiso_conclusion(by_label[("CISO", "2025")], by_label[("CISO", "Jan–Jun 2026")])
    lines += spp_conclusion(by_label[("SWPP", "2025")])
    lines += ["", "In numbers:", ""]
    for c in comparisons:
        lines += facts(c)
    return lines


if __name__ == "__main__":
    main()
