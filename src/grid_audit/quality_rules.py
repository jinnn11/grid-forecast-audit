"""Step 2 rule proposal. Run: uv run python -m grid_audit.quality_rules

Writes results/quality_rules_proposal.md from data/processed/balance.parquet and
data/ba_events.csv. Applies nothing: the rules are for the user to approve.
"""

from pathlib import Path

import pandas as pd

from grid_audit.check import fmt, markdown_table
from grid_audit.quality import (
    R3A_DAYS,
    R3A_EVENTS,
    R3B_MIN_USABLE_HOURS,
    both_present,
    largest_bas,
    near_events,
    nonpositive,
    removed_by_ba,
    repeats_in_runs,
    rule_impact,
    run_length_sensitivity,
    short_history,
)

PARQUET_PATH = Path("data/processed/balance.parquet")
EVENTS_PATH = Path("data/ba_events.csv")
REPORT_PATH = Path("results/quality_rules_proposal.md")
RUN_HOURS = 6  # recommended N for R2
RUN_LENGTHS = [2, 3, 4, 6, 12, 24]
TOP_ROWS = 15


def read_events(path: Path) -> pd.DataFrame:
    events = pd.read_csv(path, dtype=str, keep_default_na=False)
    events["date"] = pd.to_datetime(events["date"], format="%Y-%m-%d", utc=True)
    return events


def ba_table(removed: pd.DataFrame, limit: int = TOP_ROWS) -> str:
    rows = [[str(ba), fmt(r.hours, 0), fmt(r.pct, 2)] for ba, r in removed.head(limit).iterrows()]
    more = f"\n\n{len(removed) - limit} more BAs lose fewer hours." if len(removed) > limit else ""
    header = ["BA", "Hours removed", "% of the BA's hours with both values"]
    return (markdown_table(header, rows) if rows else "No BA loses hours.") + more


def render_proposal(hourly: pd.DataFrame, events: pd.DataFrame, run_hours: int) -> str:
    """The proposal page: rules, their impact, the run-length choice and the BAs affected."""
    base = both_present(hourly)
    r1, r3a = nonpositive(hourly), near_events(hourly, events)
    r2 = repeats_in_runs(hourly, "demand", run_hours)
    r2b = repeats_in_runs(hourly, "forecast", run_hours)
    r3b = short_history(hourly, base & ~r1 & ~r2 & ~r3a)
    rules = {"R1": r1, f"R2 (N = {run_hours})": r2, "R3a": r3a, "R3b": r3b}
    impact = rule_impact(hourly, rules)
    usable = base & ~r1 & ~r2 & ~r3a & ~r3b
    top = largest_bas(hourly)
    period = f"{hourly['utc'].min():%Y-%m-%d %H:%M} to {hourly['utc'].max():%Y-%m-%d %H:%M} UTC"

    impact_rows = [
        [r.rule, fmt(r.alone, 0), fmt(r.after_earlier, 0), fmt(r.bas, 0)]
        for r in impact.itertuples()
    ]
    sensitivity = run_length_sensitivity(hourly, RUN_LENGTHS, r1 | r3a, top)
    sensitivity_rows = [
        [
            str(r.n) + (" (proposed)" if r.n == run_hours else ""),
            fmt(r.removed, 0),
            fmt(r.bas_over_1pct, 0),
            f"{r.top_all_hours} of {len(top)}",
            f"{r.top_present_hours} of {len(top)}",
        ]
        for r in sensitivity.itertuples()
    ]
    applied = events[events["event"].isin(R3A_EVENTS)].reset_index(drop=True)
    event_rows = [
        [
            f"{event.date:%Y-%m-%d}",
            event.ba,
            event.event,
            event.basis,
            fmt((base & near_events(hourly, applied.iloc[[i]])).sum(), 0),
        ]
        for i, event in enumerate(applied.itertuples())
    ]
    others = events[~events["event"].isin(R3A_EVENTS)]
    other_rows = [
        [f"{e.date:%Y-%m-%d}", e.ba, e.event, e.basis, e.evidence] for e in others.itertuples()
    ]
    usable_before_r3b = (base & ~r1 & ~r2 & ~r3a).groupby(hourly["ba"]).sum()
    short = usable_before_r3b[usable_before_r3b < R3B_MIN_USABLE_HOURS].sort_values()
    short_rows = [[str(ba), fmt(n, 0)] for ba, n in short.items() if n > 0]
    never = sorted(ba for ba, n in short.items() if n == 0)
    present_by_ba = base.groupby(hourly["ba"]).sum()
    forecast_repeats = 100 * (base & r2b).groupby(hourly["ba"]).sum() / present_by_ba
    forecast_rows = [
        [str(ba), fmt(pct, 2)] for ba, pct in forecast_repeats.nlargest(10).items() if pct > 0
    ]

    return "\n".join(
        [
            "# Proposed data-quality rules\n",
            "**Status: proposal. No rule has been applied.** `results/data_quality.md` is written "
            "only after the rules are approved.\n",
            f"- Data: {fmt(len(hourly), 0)} BA-hours from {hourly['ba'].nunique()} BAs, {period}.",
            f"- Baseline: {fmt(base.sum(), 0)} hours ({fmt(100 * base.mean(), 1)}%) have both "
            "demand and forecast. Rules remove hours from this baseline.",
            "- No rule uses forecast error, because that is what the audit measures.\n",
            "## Rules\n",
            markdown_table(
                ["Rule", "Drops", "Status"],
                [
                    ["R1", "Hours with demand ≤ 0 or forecast ≤ 0", "Proposed"],
                    [
                        "R2",
                        "Hours repeating the previous hour's demand inside a run of at least "
                        "N consecutive hours with the same value; the first hour is kept",
                        f"Proposed, N = {run_hours}",
                    ],
                    [
                        "R3a",
                        f"A BA's hours within {R3A_DAYS} days of one of its events of type "
                        f"{', '.join(R3A_EVENTS)} in `data/ba_events.csv`",
                        "Proposed",
                    ],
                    [
                        "R3b",
                        f"Every hour of a BA with fewer than {fmt(R3B_MIN_USABLE_HOURS, 0)} "
                        "usable hours (one year) after R1-R3a",
                        "Proposed",
                    ],
                    [
                        "R2b",
                        "R2 applied to the forecast",
                        "Not applied (forecasts are judged as published); reported as a column",
                    ],
                ],
                left_columns=3,
            )
            + "\n",
            f"## Impact with N = {run_hours}, applied in this order\n",
            markdown_table(
                [
                    "Rule",
                    "Hours removed on its own",
                    "Removed after the rules above",
                    "BAs losing hours",
                ],
                impact_rows,
            )
            + "\n",
            f"Usable after all four rules: {fmt(usable.sum(), 0)} hours "
            f"({fmt(100 * usable.mean(), 1)}% of all BA-hours).\n",
            "## How many hours make a run (R2)\n",
            f"Hours removed are counted after R1 and R3a. The {len(top)} largest BAs by average "
            f'demand are {", ".join(top)}. "All hours" counts every row the BA has; "hours with '
            'both values" counts only rows with demand and forecast, so it isolates the rules.\n',
            markdown_table(
                [
                    "N (hours)",
                    "Hours removed",
                    "BAs losing more than 1%",
                    "Top-10 BAs with ≥ 95% of all hours usable",
                    "Top-10 BAs keeping ≥ 95% of hours with both values",
                ],
                sensitivity_rows,
            )
            + "\n",
            "## BAs each rule removes hours from\n",
            "### R1: non-positive values\n",
            ba_table(removed_by_ba(hourly, r1)) + "\n",
            f"### R2: repeated demand, N = {run_hours}\n",
            ba_table(removed_by_ba(hourly, r2)) + "\n",
            f"### R3a: {R3A_DAYS} days either side of BA events\n",
            markdown_table(
                ["Date", "BA", "Event", "Basis", "Hours removed"], event_rows, left_columns=4
            )
            + "\n",
            "Events with no hours removed are BAs without demand (generation-only) or hours that "
            "already lack a value.\n",
            "### R3b: short histories\n",
            (
                markdown_table(["BA", "Usable hours after R1-R3a"], short_rows)
                if short_rows
                else "No BA with usable hours falls short."
            )
            + "\n",
            f"BAs with no usable hours at all ({len(never)}): {', '.join(never) or 'none'}.\n",
            "## Events no rule acts on\n",
            "These events in `data/ba_events.csv` are recorded but trigger no rule.\n",
            markdown_table(["Date", "BA", "Event", "Basis", "Evidence"], other_rows, left_columns=5)
            + "\n",
            f"## Repeated forecasts (R2b, reported, not applied), N = {run_hours}\n",
            markdown_table(["BA", "% of hours with both values"], forecast_rows) + "\n",
        ]
    )


def main() -> None:
    hourly = pd.read_parquet(PARQUET_PATH)
    report = render_proposal(hourly, read_events(EVENTS_PATH), RUN_HOURS)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
