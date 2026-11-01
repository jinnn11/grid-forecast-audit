"""CISO follow-ups (user, 2026-10-30): when EIA-930's one-hour lag in CISO demand started, and
whether the gap between CAISO's own day-ahead forecast and actual load tracks battery charging.

Run: uv run python -m grid_audit.ciso_check (after grid_audit.download_operators)
Writes results/ciso_check.md. Reads only cached files; operator_check writes the file records.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from grid_audit.audit import MONTHS
from grid_audit.calendar import local_hours
from grid_audit.check import fmt, markdown_table
from grid_audit.operators import (
    CAISO_HISTORY_MONTHS,
    CAISO_MONTHS,
    CAISO_PINNED_MONTHS,
    CAISO_RUNS,
    CAISO_SAMPLE_MONTHS,
    CAISO_SPELL_MONTHS,
    CISO_LATE_SPANS,
    HOUR,
    NAIVE_HOURS,
    OPERATORS_DIR,
    OUTLOOK_DAYS,
    PACIFIC,
    alignment,
    caiso_series,
    charging_fit,
    day_runs,
    lead_by_month,
    moved,
    moved_back,
    oasis_file,
    outlook_name,
    ramp_match,
    ramp_runs,
    read_oasis,
    read_outlook,
    score,
    series_match,
)
from grid_audit.quality_rules import PARQUET_PATH
from grid_audit.storage import all_storage, charging

REPORT_PATH = Path("results/ciso_check.md")
AUDIT_LEAD_YEARS = (2023, 2024, 2025)  # CISO's losing years, where the audit's Q5 check ran
EDGE_HOURS = 2  # hours shown on each side of a switch


def ciso_hours(hourly: pd.DataFrame) -> pd.DataFrame:
    """CISO's EIA-930 hours by UTC hour end: local end, local day and month, demand, forecast."""
    rows = hourly[hourly["ba"].eq("CISO")]
    local = local_hours(rows["local"])
    return pd.DataFrame(
        {
            "local": rows["local"].to_numpy(),
            "day": local["day"].to_numpy(),
            "month": local["day"].dt.to_period("M").to_numpy(),
            "demand": rows["demand"].to_numpy(),
            "forecast": rows["forecast"].to_numpy(),
        },
        index=pd.DatetimeIndex(rows["utc"], name="utc"),
    ).sort_index()


# Part 1: the lag


def year_leads(eia: pd.DataFrame) -> pd.DataFrame:
    """Per local year: months whose EIA forecast fits EIA demand best moved +1, 0 and −1 h."""
    months = lead_by_month(eia["forecast"], eia["demand"], eia["month"])
    months = months[months.index.year.isin(range(2016, 2027))]
    counts = months.groupby(months.index.year)["best"].value_counts().unstack(fill_value=0)
    late = months.index[months["best"].eq(1)]
    spans = day_runs(pd.Series(1, index=late.to_timestamp()).reindex(months.index.to_timestamp()))
    return counts.reindex(columns=[1, 0, -1], fill_value=0), spans


@dataclass(frozen=True)
class MonthCheck:
    month: pd.Period
    fetched: str
    forecast_equal: float  # % of hours within 1 MW as published
    demand_gap: tuple[float, float]  # mean gap %, as published and CAISO moved +1 h
    ramps: tuple[float, float]  # change correlation, as published and moved +1 h
    days: dict[int, int]  # days whose changes match best at each shift


def check_month(eia: pd.DataFrame, caiso: pd.DataFrame, month: pd.Period, fetched: str):
    part = eia[eia["month"].eq(month)]
    demand = alignment(part["demand"], caiso["actual"])
    forecast = alignment(part["forecast"], caiso["forecast"])
    ramps = ramp_match(part["demand"], caiso["actual"])
    runs = ramp_runs(part["demand"], caiso["actual"], part["day"])
    days = runs.groupby("shift")["days"].sum().to_dict()
    return MonthCheck(
        month,
        fetched,
        forecast.loc[0, "equal_pct"],
        (demand.loc[0, "mean_gap_pct"], demand.loc[1, "mean_gap_pct"]),
        (ramps[0], ramps[1]),
        {k: int(days.get(k, 0)) for k in (1, 0, -1)},
    )


def fetched_as(month: pd.Period) -> str:
    if month in CAISO_SAMPLE_MONTHS:
        return "sample"
    if month in CAISO_PINNED_MONTHS:
        return "pin-down"
    if month in CAISO_SPELL_MONTHS:
        return "spell check"
    return "earlier check"


def day_verdicts(eia: pd.DataFrame, caiso: pd.DataFrame, months: pd.PeriodIndex) -> pd.DataFrame:
    """Every checked day: its best shift by hour-to-hour changes, its UTC hours and whether it
    lies inside a late span, outside all of them, or across an edge."""
    part = eia[eia["month"].isin(months)]
    rows = []
    for day, hours in part.groupby("day"):
        runs = ramp_runs(hours["demand"], caiso["actual"], hours["day"])
        if runs.empty:
            continue
        first, last = hours.index.min(), hours.index.max()
        inside = any(a <= first and last <= b for a, b in CISO_LATE_SPANS)
        touches = any(first <= b and a <= last for a, b in CISO_LATE_SPANS)
        place = "inside" if inside else ("edge" if touches else "outside")
        rows.append({"day": day, "shift": int(runs["shift"].iloc[0]), "place": place})
    return pd.DataFrame(rows)


def edge_rows(eia: pd.DataFrame, caiso: pd.DataFrame) -> list[list[str]]:
    """Hours either side of each switch: EIA demand against CAISO's load in the same hour and
    the hour before. The start of the first span is the start of 2016, not a switch."""
    rows = []
    edges = [(last, "last late hour") for _, last in CISO_LATE_SPANS]
    edges += [(first, "first late hour") for first, _ in CISO_LATE_SPANS[1:]]
    for edge, label in sorted(edges):
        for k in range(-EDGE_HOURS, EDGE_HOURS + 1):
            t = edge + k * HOUR
            if t not in eia.index:
                continue
            demand, now, before = (
                eia.at[t, "demand"],
                caiso["actual"].get(t),
                caiso["actual"].get(t - HOUR),
            )
            closer = "–"
            if pd.notna(demand) and pd.notna(now) and pd.notna(before):
                closer = (
                    "hour before (late)" if abs(demand - before) < abs(demand - now) else "same"
                )
            rows.append(
                [
                    f"{t:%Y-%m-%d %H:%M}" + (f" ({label})" if k == 0 else ""),
                    f"{eia.at[t, 'local']:%m-%d %H:%M}",
                    fmt(demand, 0),
                    fmt(now, 0) if now is not None else "–",
                    fmt(before, 0) if before is not None else "–",
                    closer,
                ]
            )
    return rows


def flagged_spells(eia: pd.DataFrame, min_days: int = 2) -> pd.DataFrame:
    """Runs of at least `min_days` days, outside every late span, on which EIA's forecast fits
    EIA's demand best moved +1 h: possible short lags, to check against CAISO's data."""
    days = lead_by_month(eia["forecast"], eia["demand"], eia["day"])["best"]
    days = days[days.index >= pd.Timestamp("2016-01-01")]
    runs = day_runs(days.astype("Int64"))
    runs = runs[runs["shift"].eq(1).fillna(False) & runs["days"].ge(min_days)]
    first_hour = eia.groupby("day").apply(lambda h: h.index.min())
    last_hour = eia.groupby("day").apply(lambda h: h.index.max())
    outside = [
        not any(first_hour[r.first] <= b and a <= last_hour[r.last] for a, b in CISO_LATE_SPANS)
        for r in runs.itertuples()
    ]
    return runs[outside]


# Part 2: CAISO's forecast gap and battery charging


@dataclass(frozen=True)
class GapPeriod:
    label: str
    hours: int
    bias: float  # CAISO's forecast against its actual load, Σe / Σ actual, %
    mape: float
    charging_pct: float  # mean charging / mean actual load, %
    fit: dict[str, float] | None
    bias_less: float  # against actual load less charging
    mape_less: float
    skill: float  # against its actual load (naive: the actual load 24 h earlier)
    skill_less: float


def gap_period(label: str, caiso: pd.DataFrame, storage: pd.DataFrame) -> GapPeriod:
    """CAISO's forecast against its own actual load, and against actual load less charging
    (charging: −other where CISO's other-fuel net generation is below 0)."""
    other = storage["other"].reindex(caiso.index)
    charging = (-other).clip(lower=0)
    less = caiso["actual"] - charging
    has = other.notna().any()
    plain = score(caiso["forecast"], caiso["actual"])
    minus = score(caiso["forecast"], less) if has else {"bias": float("nan"), "mape": float("nan")}

    def skill(truth: pd.Series) -> float:
        naive = moved(truth, truth.index, NAIVE_HOURS)
        both = naive.notna() & caiso["forecast"].notna() & truth.gt(0)
        return 1 - (
            score(caiso["forecast"][both], truth[both])["mape"]
            / score(naive[both], truth[both])["mape"]
        )

    return GapPeriod(
        label,
        plain["hours"],
        plain["bias"],
        plain["mape"],
        100 * charging.mean() / caiso["actual"][other.notna()].mean() if has else float("nan"),
        charging_fit(caiso["actual"] - caiso["forecast"], other) if has else None,
        minus["bias"],
        minus["mape"],
        skill(caiso["actual"]),
        skill(less) if has else float("nan"),
    )


def hour_profile(caiso: pd.DataFrame, storage: pd.DataFrame) -> pd.DataFrame:
    """Mean actual − forecast, charging and discharging (MW) by Pacific hour ending."""
    other = storage["other"].reindex(caiso.index)
    hour = (caiso.index - HOUR).tz_convert(PACIFIC).hour + 1
    table = pd.DataFrame(
        {
            "gap": caiso["actual"] - caiso["forecast"],
            "charging": (-other).clip(lower=0),
            "discharging": other.clip(lower=0),
        },
        index=caiso.index,
    )
    return table.groupby(hour).mean()


def storage_reporting(storage: pd.DataFrame) -> pd.DataFrame:
    """Per year: hours with a battery-storage value, and the 5th and 95th percentiles of the
    other-fuel net generation (MW)."""
    by_year = storage.groupby(storage.index.year)
    return pd.DataFrame(
        {
            "battery_hours": by_year["battery"].count(),
            "other_low": by_year["other"].quantile(0.05),
            "other_high": by_year["other"].quantile(0.95),
        }
    )


# Report


def lag_section(
    leads: pd.DataFrame,
    lead_spans: pd.DataFrame,
    checks: list[MonthCheck],
    verdicts: pd.DataFrame,
    edges: list[list[str]],
    spells: pd.DataFrame,
) -> list[str]:
    year_rows = [
        [str(year), fmt(row[1], 0), fmt(row[0], 0), fmt(row[-1], 0)]
        for year, row in leads.iterrows()
    ]
    late_months = lead_spans[lead_spans["shift"].eq(1).fillna(False)]
    month_spans = ", ".join(
        f"{r.first:%b %Y}" + ("" if r.first == r.last else f" to {r.last:%b %Y}")
        for r in late_months.itertuples()
    )
    check_rows = [
        [
            f"{c.month:%Y-%m}",
            c.fetched,
            fmt(c.forecast_equal, 1),
            f"{fmt(c.demand_gap[0], 2)} / {fmt(c.demand_gap[1], 2)}",
            f"{fmt(c.ramps[0], 3)} / {fmt(c.ramps[1], 3)}",
            f"{c.days[1]} / {c.days[0]} / {c.days[-1]}",
        ]
        for c in checks
    ]
    inside = verdicts[verdicts["place"].eq("inside")]
    outside = verdicts[verdicts["place"].eq("outside")]
    odd = pd.concat([inside[inside["shift"].ne(1)], outside[outside["shift"].ne(0)]])
    odd_text = (
        "; ".join(f"{r.day:%Y-%m-%d} ({r.place}, best {r.shift:+d} h)" for r in odd.itertuples())
        or "none"
    )
    by_day = verdicts.set_index("day")["shift"]
    spell_parts, spell_late, spell_checked = [], 0, 0
    for r in spells.itertuples():
        shifts = by_day[(by_day.index >= r.first) & (by_day.index <= r.last)]
        spell_late += int(shifts.eq(1).sum())
        spell_checked += len(shifts)
        span = f"{r.first:%Y-%m-%d}" + ("" if r.first == r.last else f" to {r.last:%Y-%m-%d}")
        spell_parts.append(f"{span} ({shifts.eq(1).sum()} of {r.days} days late in CAISO's data)")
    spell_text = ", ".join(spell_parts) or "none"
    spell_verdict = (
        "On every one of those days EIA's demand matches CAISO's load as published, so the "
        "spells are noise in EIA's forecast-against-demand check, not late demand; the spans "
        "above are the whole timeline."
        if spell_late == 0 and spell_checked == spells["days"].sum()
        else "Spells not wholly on time in CAISO's data are not in the spans above."
    )
    span_rows = [
        [
            f"{a:%Y-%m-%d %H:%M}",
            f"{a.tz_convert(PACIFIC):%Y-%m-%d %H:%M %Z}",
            f"{b:%Y-%m-%d %H:%M}",
            f"{b.tz_convert(PACIFIC):%Y-%m-%d %H:%M %Z}",
        ]
        for a, b in CISO_LATE_SPANS
    ]
    return [
        "## 1. When EIA-930's CISO demand runs an hour late\n",
        "### Audit years that show the one-hour lead\n",
        "The audit's Q5 check moves the forecast by −24, −1, 0, +1 and +24 hours, but only for "
        "large BAs in years they lose to the naive forecast: for CISO, "
        f"{', '.join(map(str, AUDIT_LEAD_YEARS))}, and +1 h was best in all three. The same "
        "check on every month (EIA-930 alone; the forecast moved −1, 0 and +1 h against demand, "
        "all hours with both values above 0) shows the lead in more years:\n",
        markdown_table(
            ["Year", "Months best at +1 h", "Months best at 0", "Months best at −1 h"], year_rows
        )
        + "\n",
        f"Months best at +1 h: {month_spans}. December 2019 is a month of broken forecast "
        "values (MAPE above 300% at every shift), not a lead.\n",
        "### Checked against CAISO's own data\n",
        "Per month: whether EIA's forecast equals CAISO's day-ahead forecast as published "
        "(within 1 MW), and how EIA's demand lines up with CAISO's actual load as published and "
        "with CAISO's load moved +1 h (EIA's value for hour t against CAISO's for t − 1). Gap: "
        "mean absolute difference, % of EIA's mean. Change correlation: correlation of the two "
        "series' hour-to-hour changes, which ignores a level difference; it is the deciding "
        "test, because in some months EIA's demand sits 1–2% from CAISO's at every shift "
        "(July 2019: 1.99% and 1.92%). Days: local days whose changes match best at +1 h / 0 / "
        "−1 h.\n",
        markdown_table(
            [
                "Month",
                "Fetched as",
                "Forecast equal as published (%)",
                "Demand gap as published / +1 h (%)",
                "Change correlation as published / +1 h",
                "Days late / on time / early",
            ],
            check_rows,
            left_columns=2,
        )
        + "\n",
        "### The late spans\n",
        "From the checks above, EIA-930's CISO demand is CAISO's actual load one hour late in "
        "these spans (UTC hour ends; the first span starts before EIA-930's 2016 data and is "
        "taken from the first hour of 2016):\n",
        markdown_table(
            ["First late hour (UTC)", "Pacific", "Last late hour (UTC)", "Pacific"],
            span_rows,
            left_columns=4,
        )
        + "\n",
        f"On the checked days wholly inside a span, {fmt((inside['shift'] == 1).sum(), 0)} of "
        f"{fmt(len(inside), 0)} match best at +1 h; on those wholly outside, "
        f"{fmt((outside['shift'] == 0).sum(), 0)} of {fmt(len(outside), 0)} match best as "
        f"published. Exceptions: {odd_text}. On 2018-07-01 to 04 CAISO's own actual load "
        "matches CAISO's own forecast best moved +1 h, while EIA's demand matches that forecast "
        "as published, so those days are an hour off in CAISO's OASIS series, not in EIA's.\n",
        "Hours either side of each switch (MW):\n",
        markdown_table(
            [
                "UTC hour end",
                "Local",
                "EIA demand",
                "CAISO, same hour",
                "CAISO, hour before",
                "EIA closer to",
            ],
            edges,
            left_columns=2,
        )
        + "\n",
        "EIA's demand is blank for the five hours after the 2016 switch. Just before the 2025 "
        "switch (2025-12-02 16:00–23:00 UTC) EIA's values match neither CAISO hour closely; they "
        "are counted as late, the nearer of the two.\n",
        "Outside the spans, EIA's own check finds short runs (two days or more) that fit best "
        f"at +1 h. Each was checked against CAISO's data for its month: {spell_text}. "
        f"{spell_verdict}\n",
    ]


def caiso_batteries() -> pd.Series:
    """CAISO's own net battery output (MW) by UTC hour end for OUTLOOK_DAYS, from the cached
    Today's Outlook files."""
    days = [
        read_outlook(OPERATORS_DIR / "caiso_outlook" / outlook_name(day), day)
        for day in OUTLOOK_DAYS
    ]
    hourly = pd.concat(days)
    return hourly[~hourly.index.duplicated()].sort_index()


def timing_sensitivity(eia: pd.DataFrame, other: pd.Series) -> pd.DataFrame:
    """CISO's MAPE per local year 2021–2025 (all hours with values) against demand moved back
    in the late spans and less charging, with the other-fuel series moved back too (as the
    audit's variants assume) or left as published (on time)."""
    demand = moved_back(eia["demand"], CISO_LATE_SPANS)
    year = eia["day"].dt.year
    rows = {}
    for name, series in (("moved", moved_back(other, CISO_LATE_SPANS)), ("published", other)):
        truth = demand - charging(series).reindex(eia.index).fillna(0)
        rows[name] = {
            y: score(eia["forecast"][year.eq(y)], truth[year.eq(y)])["mape"]
            for y in range(2021, 2026)
        }
    return pd.DataFrame(rows)


def battery_months(other: pd.Series, batteries: pd.Series) -> pd.DataFrame:
    """Per Pacific month, over hours with both: mean charging and discharging (MW) in CISO's
    other-fuel net generation and in CAISO's battery output."""
    both = other.notna() & batteries.reindex(other.index).notna()
    eia, caiso = other[both], batteries.reindex(other.index)[both]
    month = (eia.index - HOUR).tz_convert(PACIFIC).month
    table = pd.DataFrame(
        {
            "eia_charging": (-eia).clip(lower=0),
            "caiso_charging": (-caiso).clip(lower=0),
            "eia_discharging": eia.clip(lower=0),
            "caiso_discharging": caiso.clip(lower=0),
        }
    )
    return table.groupby(month).mean()


BATTERY_MATCH_CORR = 0.95  # the check counts as a match at or above this, at the best shift


def other_timing(other: pd.Series, batteries: pd.Series, caiso: pd.DataFrame) -> pd.DataFrame:
    """Per Pacific month from 2021: whether CISO's other-fuel series is on time or an hour late.
    Where CAISO's battery output exists (2025 on), the correlation with it as published and
    with it moved +1 h (EIA's value for t against CAISO's for t − 1); otherwise, indirectly, the
    R² of CAISO's own actual − forecast gap on charging taken from EIA's value for the same hour
    and for the hour after."""
    rows = {}
    month = pd.Series((other.index - HOUR).tz_convert(PACIFIC).strftime("%Y-%m"), other.index)
    gap = caiso["actual"] - caiso["forecast"]
    for label, part in other.groupby(month):
        if label < "2021-01":
            continue
        hours = part.index
        if batteries.reindex(hours).notna().sum() > 24 * 20:
            match = series_match(part, batteries, shifts=(0, 1))
            on_time, late, source = match.loc[0, "corr"], match.loc[1, "corr"], "batteries"
        elif gap.reindex(hours).notna().sum() > 24 * 20:
            g = gap.reindex(hours)
            on_time = charging_fit(g, part)["r2"]
            late = charging_fit(g, moved(other, hours, -1))["r2"]
            source = "forecast gap"
        else:
            continue
        rows[label] = {"source": source, "on_time": on_time, "late": late}
    table = pd.DataFrame.from_dict(rows, orient="index")
    return table.assign(
        verdict=table["late"].gt(table["on_time"]).map({True: "late", False: "on time"})
    )


def battery_section(
    match: pd.DataFrame,
    aligned: pd.DataFrame,
    months: pd.DataFrame,
    timing: pd.DataFrame,
    sensitivity: pd.DataFrame,
) -> list[str]:
    match_rows = [
        [
            "as published" if k == 0 else f"as published, CAISO moved {k:+d} h",
            fmt(m.hours, 0),
            fmt(m["corr"], 3),
            fmt(m.mean_abs_diff, 0),
            fmt(m.slope, 3),
        ]
        for k, m in match.iterrows()
    ]
    a = aligned.loc[0]
    match_rows.append(
        [
            "moved back an hour in the late spans",
            fmt(a.hours, 0),
            fmt(a["corr"], 3),
            fmt(a.mean_abs_diff, 0),
            fmt(a.slope, 3),
        ]
    )
    month_rows = [
        [
            MONTHS[month - 1],
            fmt(r.eia_charging, 0),
            fmt(r.caiso_charging, 0),
            fmt(r.eia_discharging, 0),
            fmt(r.caiso_discharging, 0),
        ]
        for month, r in months.iterrows()
    ]
    timing_rows = [
        [
            label,
            "CAISO's batteries (correlation)" if t.source == "batteries" else "CAISO's gap (R²)",
            fmt(t.on_time, 3),
            fmt(t.late, 3),
            t.verdict,
        ]
        for label, t in timing.iterrows()
    ]
    sensitivity_rows = [
        [str(year), fmt(r.moved, 2), fmt(r.published, 2), fmt(r.published - r.moved, 2)]
        for year, r in sensitivity.iterrows()
    ]
    holds = a["corr"] >= BATTERY_MATCH_CORR
    verdict = (
        "**It matches: CISO reports its batteries under `Other Fuel Sources`.**"
        if holds
        else "**It does not match closely enough to treat the column as CISO's batteries.**"
    )
    later = sensitivity["published"] - sensitivity["moved"]
    widest = later.loc[2022:2023].abs().max()
    return [
        "### Is CISO's `Other Fuel Sources` its batteries?\n",
        "EIA's documentation does not say. EIA-930's instructions define `OTH` as \"all other "
        'energy sources" and add: "In cases where there are three or fewer generators in an '
        "energy source category, and tariffs or other agreements require this information to be "
        'masked, use the “other” category (“OTH”) for this generation" '
        "(https://www.eia.gov/survey/form/eia_930/instructions.pdf). EIA's About page lists "
        '"Battery storage added as an energy source (beginning January 1, 2025)" '
        "(https://www.eia.gov/electricity/930-content/about.html). Neither, nor the reference "
        "tables, says what CISO reports under `OTH`.\n",
        "So the column was compared with CAISO's own battery output for 2025 (approved by the "
        "user on 2026-10-30): the `Batteries` column of CAISO's Today's Outlook daily fuel-mix "
        "files (https://www.caiso.com/outlook/history/YYYYMMDD/fuelsource.csv; public, no "
        "account, login or terms), MW every 5 minutes, averaged per hour. Both are net output, "
        "below 0 while charging. As published, EIA's values match CAISO's an hour earlier: the "
        "column runs an hour late, as CISO's demand does. Moved back in the same late spans as "
        f"demand, it matches CAISO's series as published. Match: correlation at least "
        f"{BATTERY_MATCH_CORR}. {verdict} EIA's values are about "
        f"{fmt(100 * a.slope, 0)}% of CAISO's (slope).\n",
        markdown_table(
            ["EIA's other-fuel series", "Hours", "Correlation", "Mean |difference| (MW)", "Slope"],
            match_rows,
        )
        + "\n",
        "By Pacific month, 2025, EIA's values moved back in the late spans (MW, means over all "
        "hours with both):\n",
        markdown_table(
            [
                "Month",
                "EIA charging",
                "CAISO charging",
                "EIA discharging",
                "CAISO discharging",
            ],
            month_rows,
        )
        + "\n",
        "### When the other-fuel column runs late\n",
        "Per month: on time or an hour late. From 2025 directly, against CAISO's batteries. "
        "Before, only indirectly and only for the months of CAISO's load data: how well "
        "charging from EIA's value for the same hour, or for the hour after, fits CAISO's own "
        "actual − forecast gap (R²). The indirect test is weak where charging is small.\n",
        markdown_table(
            ["Month", "Checked against", "On time", "An hour late", "Verdict"],
            timing_rows,
            left_columns=2,
        )
        + "\n",
        "The audit's charging variants take the column as late in every late span, as verified "
        "for 2025. Before 2025 that is not settled: the indirect test agrees for July 2024 but "
        "points the other way, weakly, for June–July 2022 and July 2023, and nothing covers "
        "August 2023 to June 2024. CISO's MAPE with demand moved back and charging taken out "
        "(all hours with values), with the column moved back too or left as published:\n",
        markdown_table(
            ["Year", "Moved back (%)", "As published (%)", "Difference (pp)"],
            sensitivity_rows,
        )
        + "\n",
        f"In 2022 and 2023 the choice changes CISO's MAPE by at most {fmt(widest, 2)} pp, so an "
        "hour's error in the charging there barely matters. In 2024 and 2025 leaving the column "
        f"as published adds {fmt(later.loc[2024], 2)} and {fmt(later.loc[2025], 2)} pp, as "
        "expected where it is late.\n",
    ]


def gap_section(
    periods: list[GapPeriod],
    profile: pd.DataFrame,
    reporting: pd.DataFrame,
    battery: list[str],
) -> list[str]:
    rows = []
    for p in periods:
        fit = p.fit or {}
        rows.append(
            [
                p.label,
                fmt(p.hours, 0),
                fmt(p.bias, 2),
                fmt(p.charging_pct, 2),
                fmt(fit.get("intercept", float("nan")), 0),
                fmt(fit.get("charging", float("nan")), 2),
                fmt(fit.get("discharging", float("nan")), 2),
                fmt(fit.get("r2", float("nan")), 2),
                fmt(p.bias_less, 2),
                f"{fmt(p.mape, 2)} / {fmt(p.mape_less, 2)}",
                f"{fmt(p.skill, 2)} / {fmt(p.skill_less, 2)}",
            ]
        )
    profile_rows = [
        [f"{hour}", fmt(r.gap, 0), fmt(r.charging, 0), fmt(r.discharging, 0)]
        for hour, r in profile.iterrows()
    ]
    report_rows = [
        [str(year), fmt(r.battery_hours, 0), fmt(r.other_low, 0), fmt(r.other_high, 0)]
        for year, r in reporting.iterrows()
    ]
    return [
        "## 2. CAISO's forecast gap and battery charging\n",
        "### What each series includes (CAISO's documentation)\n",
        *DOCUMENTATION,
        "",
        "### Storage in EIA-930 for CISO\n",
        "EIA-930's `Battery Storage` column (in the files from July 2024) is blank for CISO in "
        "every hour. CISO's `Other Fuel Sources` behaves like storage: below 0 in the middle "
        "of the day (charging) and above 0 in the evening (discharging), growing from tens of "
        "MW in 2019 to about ±10 GW in 2026. It is used here as CISO's storage (charging is "
        "−other where other is below 0); the next subsection checks it against CAISO's own "
        "battery output.\n",
        markdown_table(
            [
                "Year",
                "Hours with a battery value",
                "Other fuel, 5th percentile (MW)",
                "Other fuel, 95th percentile (MW)",
            ],
            report_rows,
        )
        + "\n",
        *battery,
        "### Does the gap track charging?\n",
        "CAISO's day-ahead forecast against its own actual load, per fetched month and for "
        "2025 and Jan–Jun 2026 (all hours with both), with charging from EIA's other-fuel "
        "column (moved back where it is verified late, in 2025) and, last, from CAISO's own "
        "battery output. Months before July 2018 have no fuel data, and CISO's other-fuel "
        "values are blank in July 2020. Fit: actual − forecast = "
        "a + b × charging + c × discharging (MW), least squares over the hours with storage "
        "data. Less charging: the actual load minus charging. Skill against each truth's value "
        "24 hours earlier.\n",
        markdown_table(
            [
                "Period",
                "Hours",
                "Bias (%)",
                "Charging (% of load)",
                "a (MW)",
                "b",
                "c",
                "R²",
                "Bias, less charging (%)",
                "MAPE / less charging (%)",
                "Skill / less charging",
            ],
            rows,
        )
        + "\n",
        "2025 by Pacific hour ending: mean actual − forecast, charging and discharging (MW).\n",
        markdown_table(["Hour", "Actual − forecast", "Charging", "Discharging"], profile_rows)
        + "\n",
    ]


# Quotes checked against the documents' text on 2026-10-30.
DOCUMENTATION = [
    "- **Day-ahead forecast (OASIS `DAM`).** CAISO's day-ahead forecast comes from its "
    "Automated Load Forecast System (BPM for Market Operations v107, §6.1.5, "
    "https://bpmcm.caiso.com/BPM%20Document%20Library/Market%20Operations/"
    "BPM_for_Market%20Operations_V107_Redline.pdf). CAISO removed battery charging from that "
    "system's inputs in June 2021: \"Currently battery charging is present in the load values "
    "feeding our Automated Load Forecast System (ALFS) … the ISO will be removing batteries when "
    'charging from the load values in ALFS" (Market Performance and Planning Forum, 22 June '
    "2021, slide 44, https://www.caiso.com/documents/"
    "presentation-marketperformance-planningforum-jun222021.pdf). CAISO's market monitor lists "
    'day-ahead demand as "the day-ahead load forecast, non-dispatchable pump load, '
    'self-scheduled exports, and upward ancillary service requirements", with "The day-ahead '
    'load forecast factors in losses" (DMM, 2025 Annual Report on Market Issues and '
    "Performance, section on day-ahead supply and demand, footnote 121, "
    "https://www.caiso.com/documents/2025-annual-report-on-market-issues-and-performance.pdf). "
    "So the forecast excludes battery charging, non-dispatchable pump load and exports, and "
    "includes losses.",
    '- **Actual load (OASIS `ACTUAL`).** CAISO describes it only as "The actual demand '
    'measurement by Hourly basis" (OASIS Interface Specification v5.1.2, field '
    "`SYS_FCST_ACT_MW`, https://www.caiso.com/Documents/"
    'OASIS-InterfaceSpecification_v5_1_2Clean_Fall2017Release.pdf) and "a total actual hourly '
    'integrated Demand" (BPM for Market Instruments v95, §13.3, https://bpmcm.caiso.com/'
    "BPM%20Document%20Library/Market%20Instruments/BPM_for_Market%20Instruments_V95_Redline.pdf"
    "). We found no CAISO document that says whether it includes battery charging or pump load.",
    "- **Elsewhere.** CAISO's Today's Outlook says its demand \"trend data do not include "
    'dispatchable pump loads or battery storage that is charging on the system" '
    "(https://www.caiso.com/todays-outlook; the change took effect on 22 June 2021, "
    "https://www.caiso.com/documents/todaysoutlookdemandgraphchanges.html). EIA-930's "
    'instructions say storage charging "should be excluded from the actual demand reported on '
    'Form EIA-930 and instead be included as a negative contribution to net generation" '
    "(https://www.eia.gov/survey/form/eia_930/instructions.pdf).",
    "- **What the documents leave open** is the actual-load side, so the test below asks the data.",
]


def findings(
    checks: list[MonthCheck],
    periods: list[GapPeriod],
    verdicts: pd.DataFrame,
    aligned: pd.DataFrame,
) -> list[str]:
    by_label = {p.label: p for p in periods}
    y25, y26 = by_label["2025"], by_label["Jan–Jun 2026"]
    own = by_label["2025, CAISO's battery data"]
    own_fit = own.fit or {}
    aligned = aligned.loc[0]
    first, second = CISO_LATE_SPANS[0], CISO_LATE_SPANS[-1]
    sample_late = [c for c in checks if c.fetched == "sample" and c.ramps[1] > c.ramps[0]]
    return [
        "- **EIA-930 reports CISO's demand an hour late in two spans: from before 2016 to "
        f"{second_day(first[1])}, and from {CISO_LATE_SPANS[1][0].tz_convert(PACIFIC):%Y-%m-%d} "
        f"(steadily from {second[0].tz_convert(PACIFIC):%Y-%m-%d}) to "
        f"{second_day(second[1])}.** In every checked month EIA's forecast equals CAISO's "
        "day-ahead forecast as published; the lead is in EIA's demand, as in 2025.",
        f"  - Audit years with the lead: 2016 (to {second_day(first[1])}), 2022 (from mid-June), "
        "2023, 2024 and 2025 (to 2 December). The audit's own Q5 table shows it only for "
        "2023–2025, the CISO years it checked.",
        f"  - Samples (July of 2016–2024): late in "
        f"{', '.join(f'{c.month:%Y}' for c in sample_late)}; on time in the others. The "
        "switches were pinned with Sep 2016 and Jun 2022, and the start of the audit years "
        "with Jan 2016. The short 2020–2021 spells that EIA's own check flags are on time in "
        "CAISO's data (May 2020, July 2020, May 2021).",
        "- **CISO reports its batteries under EIA-930's `Other Fuel Sources`.** EIA's "
        "documentation does not say so, but against CAISO's own 2025 battery output the "
        f"column matches at correlation {fmt(aligned['corr'], 3)} (EIA's values about "
        f"{fmt(100 * aligned['slope'], 0)}% of CAISO's) once moved back an hour: it runs an hour "
        "late together with CISO's demand through 2025-12-02, and on time after. Before 2025 "
        "its timing is checked only indirectly (see below).",
        f"- **Most of CAISO's own forecast gap is battery charging.** In 2025 CAISO's forecast "
        f"is {fmt(abs(own.bias), 1)}% below its actual load (all hours). With CAISO's own "
        "battery data, the hourly gap follows charging almost MW for MW (b = "
        f"{fmt(own_fit.get('charging', float('nan')), 2)}, R² = "
        f"{fmt(own_fit.get('r2', float('nan')), 2)}) and not discharging (c = "
        f"{fmt(own_fit.get('discharging', float('nan')), 2)}). Against actual load less "
        f"charging the bias is {fmt(own.bias_less, 1)}% (from {fmt(own.bias, 1)}%), MAPE "
        f"{fmt(own.mape_less, 2)}% (from {fmt(own.mape, 2)}%), and CAISO's forecast beats the "
        f"naive forecast (skill {fmt(own.skill_less, 2)}, from {fmt(own.skill, 2)}). With EIA's "
        f"column instead: bias {fmt(y25.bias_less, 1)}% in 2025 and {fmt(y26.bias_less, 1)}% in "
        f"Jan–Jun 2026 (from {fmt(y26.bias, 1)}%), MAPE {fmt(y25.mape_less, 2)}%. In the sampled "
        "months before 2021, with little storage, the bias was within ±1.1%.",
        f"  - The rest, about {fmt(own_fit.get('intercept', float('nan')), 0)} MW in every "
        "hour, is not explained here. One candidate is non-dispatchable pump load, which the "
        "forecast leaves out (see the documentation below); whether the actual load includes it "
        "is not documented, and EIA-930 has no CISO pumping series, so it is not tested.",
        "  - So the actual-load series counts charging as load and the day-ahead forecast does "
        "not (see the documentation below). EIA-930's CISO demand equals CAISO's actual load "
        "and its forecast equals CAISO's day-ahead forecast, so the audit's CISO error carries "
        "the same mismatch. The main run is unchanged; the audit's robustness section takes "
        "charging out in two variants.",
    ]


def second_day(t: pd.Timestamp) -> str:
    return f"{t.tz_convert(PACIFIC):%Y-%m-%d}"


def render(parts: list[str], top: list[str]) -> str:
    return "\n".join(
        [
            "# CISO check: the one-hour lag and CAISO's battery charging\n",
            "Follow-ups to `results/operator_check.md`, approved by the user on 2026-10-30: "
            "CAISO's actual load and day-ahead forecast from OASIS back to 2016 if needed, "
            "sampling one month per year first and then fetching only the months needed to pin "
            "the change down. No other download. Files and their SHA-256 are in "
            "`results/operator_files.csv`. Nothing here changes the audit's main results; the "
            "lag correction is used only in the audit's verified-corrections robustness "
            "variant.\n",
            "## Findings\n",
            *top,
            "",
            *parts,
        ]
    )


def main() -> None:
    hourly = pd.read_parquet(PARQUET_PATH, columns=["ba", "utc", "local", "demand", "forecast"])
    eia = ciso_hours(hourly)
    months = CAISO_HISTORY_MONTHS.union(CAISO_MONTHS)
    caiso = caiso_series(
        {
            run: [read_oasis(oasis_file(run, m, OPERATORS_DIR / "caiso")[1]) for m in months]
            for run in CAISO_RUNS
        }
    )
    storage = all_storage()
    storage = storage[storage["ba"].eq("CISO")].drop(columns="ba").set_index("utc").sort_index()
    batteries = caiso_batteries()
    match = series_match(storage["other"], batteries)
    aligned_other = moved_back(storage["other"], CISO_LATE_SPANS)
    aligned = series_match(aligned_other, batteries, shifts=(0,))
    # For CAISO's gap, EIA's column is moved back only where its timing is verified (2025).
    start = pd.Timestamp("2025-01-01 09:00", tz="UTC")
    late_2025 = tuple((max(a, start), b) for a, b in CISO_LATE_SPANS if b >= start)
    verified = storage.assign(other=moved_back(storage["other"], late_2025))

    leads, lead_spans = year_leads(eia)
    checks = [check_month(eia, caiso, m, fetched_as(m)) for m in months]
    verdicts = day_verdicts(eia, caiso, months)
    lag = lag_section(
        leads, lead_spans, checks, verdicts, edge_rows(eia, caiso), flagged_spells(eia)
    )

    def hours_of(first: str, last: str) -> pd.DataFrame:
        rows = eia.index[eia["day"].between(pd.Timestamp(first), pd.Timestamp(last))]
        return caiso.reindex(rows)

    periods = [
        gap_period(
            f"{MONTHS[m.month - 1]} {m.year}", hours_of(str(m.start_time), str(m.end_time)), storage
        )
        for m in CAISO_HISTORY_MONTHS
    ]
    periods += [
        gap_period("2025", hours_of("2025-01-01", "2025-12-31"), verified),
        gap_period("Jan–Jun 2026", hours_of("2026-01-01", "2026-06-30"), verified),
        gap_period(
            "2025, CAISO's battery data",
            hours_of("2025-01-01", "2025-12-31"),
            pd.DataFrame({"other": batteries}),
        ),
    ]
    profile = hour_profile(hours_of("2025-01-01", "2025-12-31"), verified)
    battery = battery_section(
        match,
        aligned,
        battery_months(aligned_other, batteries),
        other_timing(storage["other"], batteries, caiso),
        timing_sensitivity(eia, storage["other"]),
    )
    gap = gap_section(periods, profile, storage_reporting(storage), battery)
    top = findings(checks, periods, verdicts, aligned)
    REPORT_PATH.write_text(render(lag + gap, top), "utf-8")
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
