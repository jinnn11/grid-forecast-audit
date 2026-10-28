"""Step 2 D. Run: uv run python -m grid_audit.data_quality

Applies the approved rules to data/processed/balance.parquet and writes
data/balance_exemptions.csv (the R5 exception rule's exemptions, with their evidence) and
results/data_quality.md (usable hours by BA and half-year).
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from grid_audit.check import fmt, markdown_table
from grid_audit.quality import (
    R3A_DAYS,
    R3A_EVENTS,
    R3B_MIN_USABLE_HOURS,
    both_present,
    near_events,
    nonpositive,
    removed_by_ba,
    repeats_in_runs,
    rule_impact,
    short_history,
    usable_share,
)
from grid_audit.quality_rules import EVENTS_PATH, PARQUET_PATH, RUN_HOURS, read_events
from grid_audit.truth import (
    BALANCE_TOLERANCE_MW,
    EPISODE_DAY_SHARE,
    EPISODE_GAP_DAYS,
    EXEMPTION_MIN_COVERAGE,
    EXEMPTION_MIN_DAYS,
    EXEMPTION_MONTHS,
    EXEMPTION_SHARE,
    R5_SHARE,
    eia_changed,
    exemption_checks,
    imbalanced,
    in_episodes,
    mismatch_episodes,
)
from grid_audit.truth_check import pct_cell

EXEMPTIONS_PATH = Path("data/balance_exemptions.csv")
REPORT_PATH = Path("results/data_quality.md")
GAP_SENSITIVITY = [0, 7, 14]  # episode gaps (days) to show the hours given back for
MARKERS = {
    "start": "†",
    "stop": "†",
    "footprint_change": "†",
    "demand_level_shift": "‡",
    "subregion_change": "§",
}


@dataclass(frozen=True)
class Applied:
    rules: dict[str, pd.Series]  # hours each approved rule drops, in order of application
    usable: pd.Series
    unbalanced: pd.Series  # R5 before its exception rule
    checks: pd.DataFrame  # every mismatch episode the exception rule checked
    given_back: pd.Series  # hours R5 would drop after R1-R4 that an exemption keeps


def exempted_hours(
    hourly: pd.DataFrame, unbalanced: pd.Series, gap_days: int = EPISODE_GAP_DAYS
) -> tuple[pd.DataFrame, pd.Series]:
    """The exception rule's checks (daily and hour-of-day episodes), and the hours inside
    exempted episodes."""
    checks = exemption_checks(hourly, mismatch_episodes(hourly, unbalanced, gap_days=gap_days))
    return checks, in_episodes(hourly, checks[checks["exempt"]])


def apply_rules(hourly: pd.DataFrame, events: pd.DataFrame) -> Applied:
    """The approved rules in order: R1, R2, R3a, R4, R5 with its exception rule, then R3b
    counted on the hours the others leave."""
    earlier = {
        "R1": nonpositive(hourly),
        f"R2 (N = {RUN_HOURS})": repeats_in_runs(hourly, "demand", RUN_HOURS),
        "R3a": near_events(hourly, events),
        "R4": eia_changed(hourly),
    }
    survivors = both_present(hourly)
    for flags in earlier.values():
        survivors &= ~flags
    unbalanced = imbalanced(hourly, R5_SHARE)
    checks, kept = exempted_hours(hourly, unbalanced)
    r5 = unbalanced & ~kept
    r3b = short_history(hourly, survivors & ~r5)
    rules = earlier | {"R5": r5, "R3b": r3b}
    return Applied(rules, survivors & ~r5 & ~r3b, unbalanced, checks, survivors & unbalanced & kept)


def survivors_of_r1_to_r4(hourly: pd.DataFrame, applied: Applied) -> pd.Series:
    survivors = both_present(hourly)
    for name, flags in applied.rules.items():
        if name not in ("R5", "R3b"):
            survivors &= ~flags
    return survivors


def hours_inside(hourly: pd.DataFrame, flags: pd.Series, episodes: pd.DataFrame) -> list[int]:
    """For each episode, the hours inside it where `flags` is true."""
    rows_of = hourly.groupby("ba").indices
    counts = []
    for episode in episodes.itertuples(index=False):
        rows = rows_of[episode.ba]
        inside = in_episodes(hourly.iloc[rows], pd.DataFrame([episode._asdict()]))
        counts.append(int(flags.iloc[rows][inside.to_numpy()].sum()))
    return counts


def exemptions_table(hourly: pd.DataFrame, applied: Applied) -> pd.DataFrame:
    """data/balance_exemptions.csv: one row per exempted episode with its evidence. `hour_utc`
    is blank for a daily episode and the UTC hour for an hour-of-day episode."""
    exempt = applied.checks[applied.checks["exempt"]]
    given_back = survivors_of_r1_to_r4(hourly, applied) & applied.unbalanced
    rows = []
    for episode, hours in zip(
        exempt.itertuples(index=False), hours_inside(hourly, given_back, exempt), strict=True
    ):
        after = episode.start + pd.DateOffset(months=EXEMPTION_MONTHS) - pd.Timedelta(days=1)
        year = pd.DateOffset(years=1)
        rows.append(
            {
                "ba": episode.ba,
                "hour_utc": "" if pd.isna(episode.hour) else int(episode.hour),
                "first_day": f"{episode.start:%Y-%m-%d}",
                "last_day": f"{episode.end:%Y-%m-%d}",
                "days": episode.days,
                "hours_given_back": hours,
                "compared": f"{episode.start:%Y-%m-%d} to {after:%Y-%m-%d} vs "
                f"{episode.start - year:%Y-%m-%d} to {after - year:%Y-%m-%d}",
                "demand_change_pct": round(100 * episode.demand_change, 1),
                "net_generation_shift_pct": round(100 * episode.generation_shift, 1),
                "interchange_shift_pct": round(100 * episode.interchange_shift, 1),
                "attributed_to": episode.attributed_to,
            }
        )
    columns = ["ba", "hour_utc", "first_day", "last_day", "days", "hours_given_back", "compared"]
    columns += ["demand_change_pct", "net_generation_shift_pct", "interchange_shift_pct"]
    return pd.DataFrame(rows, columns=[*columns, "attributed_to"])


def gap_sensitivity(hourly: pd.DataFrame, applied: Applied, gaps: list[int]) -> pd.DataFrame:
    """Episodes checked, exempted and hours given back for each episode gap (days)."""
    survivors = survivors_of_r1_to_r4(hourly, applied)
    rows = []
    for gap in gaps:
        checks, kept = exempted_hours(hourly, applied.unbalanced, gap)
        given_back = int((survivors & applied.unbalanced & kept).sum())
        rows.append({"gap": gap, "checked": len(checks), "exempted": int(checks["exempt"].sum())})
        rows[-1]["given_back"] = given_back
    return pd.DataFrame(rows)


def event_half_year(date: pd.Timestamp) -> str:
    return f"{date.year} H{1 if date.month <= 6 else 2}"


def render_data_quality(hourly: pd.DataFrame, events: pd.DataFrame, applied: Applied) -> str:
    """results/data_quality.md."""
    ba = hourly["ba"]
    base = both_present(hourly)
    usable = applied.usable
    order = list(hourly.groupby("ba")["demand"].mean().dropna().sort_values(ascending=False).index)
    no_demand = sorted(set(ba) - set(order))
    period = f"{hourly['utc'].min():%Y-%m-%d %H:%M} to {hourly['utc'].max():%Y-%m-%d %H:%M} UTC"
    pct = f"{R5_SHARE:.0%}"

    descriptions = {
        "R1": "Demand or forecast ≤ 0",
        f"R2 (N = {RUN_HOURS})": f"Hours repeating the previous hour's demand inside a run of at "
        f"least {RUN_HOURS} equal hours (the run's first hour is kept)",
        "R3a": f"A BA's hours within {R3A_DAYS} days of its {', '.join(R3A_EVENTS)} events",
        "R4": "Hours where EIA changed the reported demand (imputed demand set)",
        "R5": f"Demand more than {pct} and {fmt(BALANCE_TOLERANCE_MW, 0)} MW away from net "
        "generation minus interchange, except in exempted episodes",
        "R3b": f"Every hour of a BA with fewer than {fmt(R3B_MIN_USABLE_HOURS, 0)} usable hours "
        "after the other rules",
    }
    rule_rows = [
        [r.rule, descriptions[r.rule], fmt(r.alone, 0), fmt(r.after_earlier, 0), fmt(r.bas, 0)]
        for r in rule_impact(hourly, applied.rules).itertuples()
    ]

    # Exception rule
    checks = applied.checks
    exempt = checks[checks["exempt"]]
    is_daily = checks["hour"].isna()
    back_daily = applied.given_back & in_episodes(hourly, exempt[exempt["hour"].isna()])
    by_kind = pd.DataFrame(
        {
            "daily": back_daily.groupby(ba).sum(),
            "hour": (applied.given_back & ~back_daily).groupby(ba).sum(),
        }
    )
    back_rows = [
        [str(b), fmt(by_kind.loc[b, "daily"], 0), fmt(by_kind.loc[b, "hour"], 0)]
        + [fmt(r.hours, 0), fmt(r.pct, 1)]
        for b, r in removed_by_ba(hourly, applied.given_back).iterrows()
    ]
    left = survivors_of_r1_to_r4(hourly, applied) & applied.unbalanced
    check_rows = [
        [
            episode.ba,
            "all" if pd.isna(episode.hour) else f"{int(episode.hour):02d}",
            f"{episode.start:%Y-%m-%d}",
            f"{episode.end:%Y-%m-%d}",
            fmt(episode.days, 0),
            fmt(hours, 0),
            fmt(100 * episode.demand_change, 1),
            fmt(100 * episode.generation_shift, 1),
            fmt(100 * episode.interchange_shift, 1),
            f"exempt: {episode.attributed_to}"
            if episode.exempt
            else f"R5 applies: {episode.reason}",
        ]
        for episode, hours in zip(
            checks.itertuples(index=False), hours_inside(hourly, left, checks), strict=True
        )
    ]
    daily_rows = [
        row[:1] + row[2:] for row, daily in zip(check_rows, is_daily, strict=True) if daily
    ]
    hour_rows = [row for row, daily in zip(check_rows, is_daily, strict=True) if not daily]
    episode_header = [
        "First day",
        "Last day",
        "Days",
        "Hours",
        "Demand change (%)",
        "Net generation shift (%)",
        "Interchange shift (%)",
        "Decision",
    ]
    sensitivity_rows = [
        [
            str(r.gap) + (" (used)" if r.gap == EPISODE_GAP_DAYS else ""),
            fmt(r.checked, 0),
            fmt(r.exempted, 0),
            fmt(r.given_back, 0),
        ]
        for r in gap_sensitivity(hourly, applied, GAP_SENSITIVITY).itertuples()
    ]

    # Usable share by BA and half-year
    share = usable_share(hourly, usable).reindex(order)
    marks: dict[tuple[str, str], str] = {}
    for event in events.itertuples():
        key = (event.ba, event_half_year(event.date))
        marks[key] = marks.get(key, "") + MARKERS.get(event.event, "")
    repeated = repeats_in_runs(hourly, "forecast", RUN_HOURS)
    per_ba = pd.DataFrame(
        {
            "all": 100 * usable.groupby(ba).mean(),
            "hours": usable.groupby(ba).sum(),
            "repeated": 100 * (base & repeated).groupby(ba).sum() / base.groupby(ba).sum(),
        }
    ).reindex(order)
    halves = [str(h) for h in share.columns]
    share_rows = [
        [b]
        + [pct_cell(v) + marks.get((b, h), "") for h, v in zip(halves, share.loc[b], strict=True)]
        + [pct_cell(per_ba.loc[b, "all"]), fmt(per_ba.loc[b, "hours"], 0)]
        + [pct_cell(per_ba.loc[b, "repeated"])]
        for b in order
    ]
    share_rows.append(
        ["**Median across BAs**"]
        + [pct_cell(v) for v in share.median()]
        + [pct_cell(per_ba["all"].median()), fmt(per_ba["hours"].median(), 0)]
        + [pct_cell(per_ba["repeated"].median())]
    )
    shown = events[events["ba"].isin(order)]
    handling = {e: f"R3a drops {R3A_DAYS} days either side" for e in R3A_EVENTS}
    handling["demand_level_shift"] = "marked; the shift itself drops no hours"
    event_rows = [
        [
            f"{e.date:%Y-%m-%d}",
            e.ba,
            e.event,
            e.basis,
            MARKERS.get(e.event, ""),
            handling.get(e.event, "recorded; no rule acts on it"),
        ]
        for e in shown.itertuples()
    ]
    kept_rows = [
        [f"{e.date:%Y-%m-%d}", e.ba, e.evidence]
        for e in shown[shown["event"].eq("demand_level_shift")].itertuples()
    ]

    lines = [
        "# Data quality: usable hours by BA and half-year\n",
        "Rules approved by the user on 2026-10-28. An hour is usable when demand and forecast "
        "are both reported and no rule drops it.\n",
        f"- Data: {fmt(len(hourly), 0)} BA-hours from {hourly['ba'].nunique()} BAs, {period}.",
        '- Truth series: raw demand ("Demand (MW)"). Forecasts are judged as published, so the '
        "only forecast values dropped are impossible ones (R1).",
        f"- Usable: {fmt(usable.sum(), 0)} hours, {fmt(100 * usable.mean(), 1)}% of all BA-hours "
        f"and {fmt(100 * usable.sum() / base.sum(), 1)}% of the {fmt(base.sum(), 0)} hours with "
        "both values.",
        "- Robustness checks for the audit: EIA's adjusted demand as the truth; the audit without "
        f"R5; R2 with N = 3 and N = 12; repeated forecasts (R2 on the forecast, N = {RUN_HOURS}) "
        "dropped.\n",
        "## Rules, applied in this order\n",
        markdown_table(
            ["Rule", "Drops", "Hours removed on its own", "Removed after the rules above", "BAs"],
            rule_rows,
            left_columns=2,
        )
        + "\n",
        "## R5 exception rule\n",
        f"- Daily episodes: spans of UTC days on which at least {EPISODE_DAY_SHARE:.0%} of the "
        f"BA's checkable hours are out of balance by more than {pct}; such days at most "
        f"{EPISODE_GAP_DAYS} days apart join one episode.",
        "- Hour-of-day episodes (added 2026-10-28, before any forecast error was computed, because "
        "daily episodes cannot see a mismatch confined to the same hours of each day): for each "
        "UTC hour of the day, spans of days on which that hour is out of balance, joined the same "
        f"way, kept when the hour is out of balance on at least {EPISODE_DAY_SHARE:.0%} of the "
        "span's checkable days. They are searched only among hours outside the checked daily "
        "episodes, so each hour is judged by at most one checked episode.",
        f"- Episodes longer than {EXEMPTION_MIN_DAYS} days are checked. The check compares "
        f"medians over checkable hours with positive demand in the {EXEMPTION_MONTHS} calendar "
        "months from the episode's first day and in the same months a year earlier; an "
        "hour-of-day episode is measured on its own hour. Each window needs such hours for at "
        f"least {EXEMPTION_MIN_COVERAGE:.0%} of the hours it could hold.",
        f"- The episode is exempt when demand changed by at most {EXEMPTION_SHARE:.0%} while net "
        f"generation or interchange shifted by more than {EXEMPTION_SHARE:.0%} of the earlier "
        "demand. Its demand is kept: R5 drops none of its hours. Exemptions and their evidence "
        "are in `data/balance_exemptions.csv`.",
        f"- Medians, because single absurd values would swing means (SEC reports net generation "
        f"up to {fmt(hourly.loc[ba.eq('SEC'), 'net_generation'].max(), 0)} MW).\n"
        if "SEC" in order
        else "- Medians, because single absurd values would swing means.\n",
        f"{int(is_daily.sum())} daily and {int((~is_daily).sum())} hour-of-day episodes checked; "
        f"{int(exempt['hour'].isna().sum())} and {int(exempt['hour'].notna().sum())} exempt. The "
        f"exemptions give back {fmt(applied.given_back.sum(), 0)} hours that R5 would otherwise "
        "drop after R1-R4.\n",
        "### Hours given back, by BA\n",
        (
            markdown_table(
                [
                    "BA",
                    "Daily episodes",
                    "Hour-of-day episodes",
                    "Total",
                    "% of the BA's hours with both values",
                ],
                back_rows,
            )
            if back_rows
            else "None."
        )
        + "\n",
        "### Daily episodes checked\n",
        "Shifts are later minus earlier medians, as a percent of the earlier median demand. "
        '"Hours" counts out-of-balance hours left after R1-R4. Hour-of-day episodes are listed '
        "at the end of this page.\n",
        markdown_table(["BA", *episode_header], daily_rows) + "\n",
        "### How the episode gap affects the result\n",
        markdown_table(
            ["Gap (days)", "Episodes checked", "Exempt", "Hours given back"], sensitivity_rows
        )
        + "\n",
        "## Usable hours by BA and half-year\n",
        "Percent of the BA's rows that are usable. '–': no rows that half-year. BAs sorted by "
        "average demand. Markers: † start, stop or footprint change (R3a); ‡ demand level shift, "
        "marked (the shift itself drops no hours); § subregion change. "
        '"Repeated forecast" is the share of the BA\'s '
        f"hours with both values whose forecast repeats inside a run of {RUN_HOURS} or more "
        "equal hours; it is reported, not dropped. The last row gives medians across BAs, so a "
        "few broken series cannot drive it.\n",
        markdown_table(
            ["BA", *halves, "All (%)", "Usable hours", "Repeated forecast (%)"], share_rows
        )
        + "\n",
        f"BAs that never report demand ({len(no_demand)}, no usable hours): "
        f"{', '.join(no_demand) or 'none'}.\n",
        "## Marked half-years\n",
        "Events in `data/ba_events.csv` for BAs that report demand.\n",
        markdown_table(
            ["Date", "BA", "Event", "Basis", "Marker", "Handling"], event_rows, left_columns=6
        )
        + "\n",
        "### Demand level shifts\n",
        markdown_table(["Date", "BA", "Evidence"], kept_rows, left_columns=3) + "\n",
        "## Hour-of-day episodes checked\n",
        'As the daily table; "Hour" is the UTC hour of the hour-end time, and each episode is '
        "measured on that hour only.\n",
        (markdown_table(["BA", "Hour (UTC)", *episode_header], hour_rows) if hour_rows else "None.")
        + "\n",
    ]
    return "\n".join(lines)


def main() -> None:
    hourly = pd.read_parquet(PARQUET_PATH)
    events = read_events(EVENTS_PATH)
    applied = apply_rules(hourly, events)
    exemptions_table(hourly, applied).to_csv(EXEMPTIONS_PATH, index=False)
    REPORT_PATH.write_text(render_data_quality(hourly, events, applied), encoding="utf-8")
    print(f"wrote {EXEMPTIONS_PATH} and {REPORT_PATH}")


if __name__ == "__main__":
    main()
