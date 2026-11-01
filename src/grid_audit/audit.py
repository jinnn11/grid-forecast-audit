"""Step 3: the audit. Run: uv run python -m grid_audit.audit

Computes the pre-registered plan in docs/step3_audit_plan.md (committed in edd06df) from
data/processed/balance.parquet, and writes results/audit.md and results/figures/ (each figure a
PNG with the CSV it plots). Reads only cached files.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from grid_audit import figures
from grid_audit.calendar import (
    BASELINE_DAYS,
    EXTREME_PERCENTILE,
    HOLIDAYS,
    MIN_DAY_HOURS,
    SEASON_ORDER,
    baseline_days,
    comparison_days,
    extreme_days,
    holiday_days,
    local_hours,
    window_days,
)
from grid_audit.check import fmt, markdown_table
from grid_audit.data_quality import Applied, apply_rules
from grid_audit.metrics import lagged, metrics, naive_forecast, pooled_wape
from grid_audit.operators import (
    CISO_LATE_SPANS,
    OPERATORS_DIR,
    SWPP_REPLACED_DAYS,
    charging_removed,
    demand_moved_back,
    forecast_replaced,
    moved_back,
    read_spp,
    spp_issues,
    spp_name,
    spp_series,
)
from grid_audit.quality import both_present, largest_bas, repeats_in_runs, short_history
from grid_audit.quality_rules import EVENTS_PATH, PARQUET_PATH, RUN_HOURS, read_events
from grid_audit.stats import (
    PERMUTATION_SEED,
    PERMUTATIONS,
    mann_kendall,
    permutation_p,
    spearman,
    theil_sen_slope,
)
from grid_audit.storage import all_storage, charging

WEATHER_EVENTS_PATH = Path("data/weather_events.csv")
LOAD_SHEDDING_PATH = Path("data/load_shedding.csv")  # documented load shedding per event
REPORT_PATH = Path("results/audit.md")
YEARS = range(2016, 2026)  # 2015 and 2026 are half-years
YEAR, BASE_YEAR = 2025, 2019  # Q1; Q4 compares BASE_YEAR with YEAR
MIN_USABLE_SHARE = 0.5  # a BA-year is eligible when at least this share of its hours is usable
MIN_TREND_YEARS = 8
ALPHA = 0.05
Q4_LEFT_OUT = ("WACM", "SPA")  # footprint changes in 2022 and 2023
# Published forecast inconsistent with demand (user, 2026-10-28): first and last month, ratio.
MARKED = {"CHPD": ("2016-01", "2021-06", "about 2.4x"), "TEPC": ("2018-10", "2019-05", "1.2-2.2x")}
MARK = "‡"
OUTAGE_MARK = "†"  # outages and load shedding cut actual demand during the event
FORECAST_SHIFTS = (-24, -1, 1, 24)  # hours, for the Q5 checks
RANKED_YEARS = (2024, 2025)  # where they rank among the panel years (user, 2026-10-28)
VARIANTS = {
    "Main": "—",
    "EIA adjusted demand": "Adjusted demand is the truth; all rules re-applied to it, except R4",
    "Without R5": "No energy-balance rule",
    "R2 with N = 3": "Repeated-demand runs of 3 hours or more dropped",
    "R2 with N = 12": "Only runs of 12 hours or more dropped",
    "Repeated forecasts dropped": f"R2b (forecast runs of {RUN_HOURS} hours or more) applied",
    # User, 2026-10-30: the corrections the operator checks verified. The main run stays as
    # published.
    "Verified corrections": "CISO demand moved back 1 h where EIA-930 has it an hour late; "
    "SWPP forecast from 2025-05-07 replaced by SPP's own day-ahead forecast; all rules "
    "re-applied",
    # User, 2026-10-30, after CISO's other-fuel column was checked against CAISO's batteries.
    "CISO without charging": "CISO's battery charging (from its other-fuel net generation, "
    "July 2018 on) taken out of its demand; all rules re-applied",
    "All corrections": "Verified corrections, then CISO's charging taken out of its demand; "
    "all rules re-applied",
}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


# Rules and runs


def usable_after(hourly: pd.DataFrame, rules: dict[str, pd.Series]) -> pd.Series:
    """Hours with both values that no rule in `rules` drops, less R3b counted on what is left."""
    survivors = both_present(hourly)
    for flags in rules.values():
        survivors &= ~flags
    return survivors & ~short_history(hourly, survivors)


def naive_source(hourly: pd.DataFrame, rules: dict[str, pd.Series]) -> pd.Series:
    """Hours the naive forecast may come from: demand passes R1 (> 0) and whichever of R2, R4
    and R5 are in `rules`."""
    source = hourly["demand"].gt(0)
    for name, flags in rules.items():
        if name.split(" ")[0] in ("R2", "R4", "R5"):
            source &= ~flags
    return source


def variant_rules(hourly: pd.DataFrame, applied: Applied) -> dict[str, dict[str, pd.Series]]:
    """The rules before R3b for each variant that keeps raw demand as the truth. R5 does not
    depend on the other rules, so it is reused as applied."""
    main = {name: flags for name, flags in applied.rules.items() if name != "R3b"}

    def with_r2(n: int) -> dict[str, pd.Series]:
        r2 = repeats_in_runs(hourly, "demand", n)
        return {
            (f"R2 (N = {n})" if k.startswith("R2") else k): (r2 if k.startswith("R2") else v)
            for k, v in main.items()
        }

    return {
        "Main": main,
        "Without R5": {name: flags for name, flags in main.items() if name != "R5"},
        "R2 with N = 3": with_r2(3),
        "R2 with N = 12": with_r2(12),
        "Repeated forecasts dropped": main
        | {f"R2b (N = {RUN_HOURS})": repeats_in_runs(hourly, "forecast", RUN_HOURS)},
    }


def verified_corrections(
    hourly: pd.DataFrame, local: pd.DataFrame, spp_forecast: pd.Series
) -> tuple[pd.DataFrame, dict[str, int]]:
    """The hourly table with the corrections the operator checks verified, and counts of the
    hours changed: CISO's demand moved back an hour in CISO_LATE_SPANS, and SWPP's forecast on
    the local days SWPP_REPLACED_DAYS replaced by SPP's own day-ahead forecast."""
    corrected = demand_moved_back(hourly, "CISO", CISO_LATE_SPANS)
    first, last = (pd.Timestamp(day) for day in SWPP_REPLACED_DAYS)
    swpp = hourly["ba"].eq("SWPP") & local["day"].between(first, last)
    utc = hourly.loc[swpp, "utc"]
    corrected = forecast_replaced(corrected, "SWPP", spp_forecast, utc.min(), utc.max())
    ciso = hourly["ba"].eq("CISO")
    moved_rows = pd.Series(False, index=hourly.index)
    for a, b in CISO_LATE_SPANS:
        moved_rows |= ciso & hourly["utc"].between(a, b)
    counts = {
        "ciso_moved": int(moved_rows.sum()),
        "ciso_blanked": int((moved_rows & corrected["demand"].isna()).sum())
        - int((moved_rows & hourly["demand"].isna()).sum()),
        "swpp_replaced": int(swpp.sum()),
        "swpp_missing": int((swpp & corrected["forecast"].isna()).sum()),
    }
    return corrected, counts


def adjusted_truth(hourly: pd.DataFrame) -> pd.DataFrame:
    """EIA's adjusted demand as the truth. With no imputed values, R4 drops nothing."""
    return hourly.assign(demand=hourly["demand_adjusted"], demand_imputed=float("nan"))


@dataclass(frozen=True)
class Run:
    usable: pd.Series  # every row of the hourly table
    hours: pd.DataFrame  # usable hours of eligible BA-years in YEARS, with local fields and naive
    yearly: pd.DataFrame  # metrics per eligible (ba, year)


def audit_run(hourly: pd.DataFrame, local: pd.DataFrame, rules: dict[str, pd.Series]) -> Run:
    """One run of the audit: usable hours, eligible BA-years and their yearly metrics."""
    usable = usable_after(hourly, rules)
    in_years = local["year"].isin(YEARS)
    keys = [hourly.loc[in_years, "ba"], local.loc[in_years, "year"]]
    share = usable[in_years].groupby(keys).mean()
    eligible = share.index[share >= MIN_USABLE_SHARE]
    naive = naive_forecast(hourly, naive_source(hourly, rules))
    rows = usable & in_years
    hours = pd.concat(
        [hourly.loc[rows, ["ba", "utc", "demand", "forecast"]], local[rows]], axis=1
    ).assign(naive=naive[rows])
    hours = hours[pd.MultiIndex.from_arrays([hours["ba"], hours["year"]]).isin(eligible)]
    return Run(usable, hours, metrics(hours, ["ba", "year"]))


def marked(ba: str, first: pd.Timestamp, last: pd.Timestamp) -> bool:
    """Whether the days `first` to `last` overlap the BA's marked months."""
    if ba not in MARKED:
        return False
    start, end, _ = MARKED[ba]
    return first <= pd.Period(end, "M").end_time and last >= pd.Period(start, "M").start_time


def marked_year(ba: str, year: int) -> bool:
    return marked(ba, pd.Timestamp(year, 1, 1), pd.Timestamp(year, 12, 31))


# Q1, Q2, Q4, Q5 and robustness, from the yearly metrics


@dataclass(frozen=True)
class Trend:
    slope: float  # Theil-Sen, percentage points per year
    s: int
    p: float
    verdict: str  # "worse", "better" or "no clear trend"


def trend(years: pd.Index, values: pd.Series) -> Trend:
    test = mann_kendall(years, values)
    verdict = "no clear trend"
    if test.p < ALPHA:
        verdict = "worse" if test.s > 0 else "better"
    return Trend(theil_sen_slope(years, values), test.s, test.p, verdict)


def ba_trends(yearly: pd.DataFrame) -> pd.DataFrame:
    """Per BA with at least MIN_TREND_YEARS eligible years: the trend of its yearly MAPE."""
    rows = {}
    for ba, mape in yearly["mape"].groupby(level="ba"):
        years = mape.index.get_level_values("year")
        if len(mape) >= MIN_TREND_YEARS:
            rows[ba] = vars(trend(years, mape)) | {"years": len(mape)}
    return pd.DataFrame.from_dict(rows, orient="index")


def panel_bas(yearly: pd.DataFrame) -> list[str]:
    """BAs eligible in every year."""
    counts = yearly.groupby(level="ba").size()
    return sorted(counts.index[counts == len(YEARS)])


def panel_years(yearly: pd.DataFrame, bas: list[str]) -> pd.DataFrame:
    """Per year, over the panel: the median MAPE across BAs and the national figure."""
    panel = yearly[yearly.index.get_level_values("ba").isin(bas)]
    by_year = panel.groupby(level="year")
    return pd.DataFrame(
        {"median_mape": by_year["mape"].median(), "national": by_year.apply(pooled_wape)}
    )


def demand_growth(yearly: pd.DataFrame) -> pd.DataFrame:
    """Q4 points: BAs eligible in BASE_YEAR and YEAR, less Q4_LEFT_OUT. x is the change in mean
    demand over usable hours; y the change in MAPE, percentage points."""
    wide = yearly[["demand", "hours", "mape"]].unstack("year")
    both = wide.dropna(subset=[("mape", BASE_YEAR), ("mape", YEAR)])
    both = both[~both.index.isin(Q4_LEFT_OUT)]
    mean = both["demand"] / both["hours"]
    return pd.DataFrame(
        {
            "demand_base": mean[BASE_YEAR],
            "demand_year": mean[YEAR],
            "x": mean[YEAR] / mean[BASE_YEAR] - 1,
            "mape_base": both[("mape", BASE_YEAR)],
            "mape_year": both[("mape", YEAR)],
            "y": both[("mape", YEAR)] - both[("mape", BASE_YEAR)],
        }
    )


def year_ranks(values: pd.Series) -> dict[int, int]:
    """Rank of each of RANKED_YEARS among the years of `values` (1: the highest error)."""
    ranks = values.rank(ascending=False, method="min")
    return {year: int(ranks[year]) for year in RANKED_YEARS}


def robustness_row(run: Run) -> dict[str, object]:
    yearly = run.yearly
    final = yearly.xs(YEAR, level="year")
    panel = panel_bas(yearly)
    by_year = panel_years(yearly, panel)
    trends = ba_trends(yearly)
    verdicts = trends["verdict"].value_counts()
    points = demand_growth(yearly)
    national = trend(by_year.index, by_year["national"])
    return {
        "median": final["mape"].median(),
        "national": pooled_wape(final),
        "slope": theil_sen_slope(by_year.index, by_year["median_mape"]),
        "national_slope": national.slope,
        "national_p": national.p,
        "national_verdict": national.verdict,
        "national_by_year": by_year["national"],
        "median_ranks": year_ranks(by_year["median_mape"]),
        "national_ranks": year_ranks(by_year["national"]),
        "worse": int(verdicts.get("worse", 0)),
        "better": int(verdicts.get("better", 0)),
        "rho": spearman(points["x"], points["y"]),
        "losing": int((final["skill"] < 0).sum()),
        "losing_bas": sorted(final.index[final["skill"] < 0]),
        "skill": final["skill"],
        "yearly": yearly[["mape", "skill"]],
        "trends": trends,
        "eligible": len(final),
        "panel": len(panel),
        "tested": int(verdicts.sum()),
        "q4": len(points),
        "hours": len(run.hours),
    }


# Q3, from the scored hours


def season_hour(hours: pd.DataFrame) -> pd.DataFrame:
    """Median across BAs of each BA's MAPE per season (rows) and local hour ending (columns)."""
    mape = metrics(hours, ["season", "hour_ending", "ba"])["mape"]
    return mape.groupby(level=["season", "hour_ending"], observed=True).median().unstack()


def cut_demand(event_id: int, criterion: str, shed: set[int]) -> bool:
    """Events where outages or load shedding cut actual demand: the hurricanes (criterion (c);
    user, 2026-10-28) and the events in `shed`, with documented load shedding (user,
    2026-10-30)."""
    return criterion == "(c)" or event_id in shed


def read_load_shedding(path: Path) -> pd.DataFrame:
    shedding = pd.read_csv(path, dtype=str, keep_default_na=False)
    shedding["id"] = shedding["id"].astype(int)
    return shedding


def shed_ids(shedding: pd.DataFrame) -> set[int]:
    return set(shedding.loc[shedding["load_shed"].eq("yes"), "id"])


def event_days(weather: pd.DataFrame) -> pd.DataFrame:
    """One row per event, listed BA and day of the event's window."""
    rows = [
        (event.id, ba, day)
        for event in weather.itertuples()
        for ba in event.bas
        for day in window_days(event.first_day, event.last_day)
    ]
    return pd.DataFrame(rows, columns=["id", "ba", "day"])


def holiday_effects(
    hours: pd.DataFrame, holidays: pd.DataFrame, events: pd.DataFrame
) -> pd.DataFrame:
    """Per holiday and BA: MAPE on the holiday's days and on its comparison days (the same
    weekday one and two weeks before and after, without other holidays), both without the BA's
    event days; and their ratio. Only BAs with hours on both."""
    every = pd.DatetimeIndex(holidays["day"])
    roles = []
    for name, group in holidays.groupby("holiday", observed=True):
        days = pd.DatetimeIndex(group["day"])
        roles.append(pd.DataFrame({"holiday": name, "day": days, "role": "holiday"}))
        compare = comparison_days(days, every)
        roles.append(pd.DataFrame({"holiday": name, "day": compare, "role": "comparison"}))
    picked = hours.merge(pd.concat(roles, ignore_index=True), on="day")
    in_event = pd.MultiIndex.from_frame(picked[["ba", "day"]]).isin(
        pd.MultiIndex.from_frame(events[["ba", "day"]])
    )
    mape = metrics(picked[~in_event], ["holiday", "ba", "role"])["mape"].unstack("role").dropna()
    return mape.assign(ratio=mape["holiday"] / mape["comparison"])


def event_effects(
    hours: pd.DataFrame, weather: pd.DataFrame, holidays: pd.DataFrame, events: pd.DataFrame
) -> pd.DataFrame:
    """Per event and listed BA: MAPE and bias in the window and in the baseline (BASELINE_DAYS
    days before and after, without holidays and the BA's other events), and the MAPE ratio."""
    by_ba = {ba: group for ba, group in hours.groupby("ba")}
    holiday_index = pd.DatetimeIndex(holidays["day"])
    rows = []
    for event in weather.itertuples():
        window = window_days(event.first_day, event.last_day)
        for ba in event.bas:
            other = events.loc[events["ba"].eq(ba) & events["id"].ne(event.id), "day"]
            excluded = holiday_index.append(pd.DatetimeIndex(other))
            baseline = baseline_days(event.first_day, event.last_day, excluded)
            ba_hours = by_ba.get(ba, hours.iloc[:0])
            picked = pd.concat(
                [
                    ba_hours[ba_hours["day"].isin(window)].assign(role="window"),
                    ba_hours[ba_hours["day"].isin(baseline)].assign(role="baseline"),
                ]
            )
            result = metrics(picked, ["role"]).reindex(["window", "baseline"])
            rows.append(
                {
                    "id": event.id,
                    "ba": ba,
                    "window_hours": result.loc["window", "hours"],
                    "window_mape": result.loc["window", "mape"],
                    "window_bias": result.loc["window", "bias_pct"],
                    "baseline_hours": result.loc["baseline", "hours"],
                    "baseline_mape": result.loc["baseline", "mape"],
                    "baseline_bias": result.loc["baseline", "bias_pct"],
                    "ratio": result.loc["window", "mape"] / result.loc["baseline", "mape"],
                    "marked": marked(ba, event.first_day, event.last_day),
                }
            )
    return pd.DataFrame(rows)


def extreme_day_effects(hours: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Days whose peak is above the BA's EXTREME_PERCENTILE percentile within the season and
    season year (days with at least MIN_DAY_HOURS usable hours), and per season and BA the MAPE
    on those days and on the BA's other such days in the same seasons."""
    daily = (
        hours.groupby(["ba", "day"])
        .agg(
            peak=("demand", "max"),
            hours=("demand", "size"),
            season=("season", "first"),
            season_year=("season_year", "first"),
        )
        .reset_index()
    )
    daily = daily[daily["hours"] >= MIN_DAY_HOURS].reset_index(drop=True)
    daily["extreme"] = extreme_days(daily)
    picked = hours.merge(daily[["ba", "day", "extreme"]], on=["ba", "day"])
    picked["season"] = pd.Categorical(picked["season"], categories=SEASON_ORDER)
    mape = metrics(picked, ["season", "ba", "extreme"])["mape"].unstack("extreme")
    mape.columns = ["other", "extreme"]
    overall = metrics(picked, ["ba", "extreme"])["mape"].unstack("extreme")
    overall.columns = ["other", "extreme"]
    overall = pd.concat({"All": overall}, names=["season"])
    effects = pd.concat([mape, overall]).dropna()
    return daily, effects.assign(ratio=effects["extreme"] / effects["other"])


# Q5 checks inside EIA-930


def hour_ranges(values: list[int]) -> str:
    """[9, 10, 11, 15] -> '9-11, 15'."""
    spans: list[list[int]] = []
    for value in sorted(values):
        if spans and value == spans[-1][1] + 1:
            spans[-1][1] = value
        else:
            spans.append([value, value])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in spans) or "none"


def loss_checks(
    hourly: pd.DataFrame,
    local: pd.DataFrame,
    applied: Applied,
    run: Run,
    repeated_forecast: pd.Series,
    ba_events: pd.DataFrame,
    ba: str,
    year: int,
) -> dict[str, object]:
    """The plan's checks for a BA-year that loses to the naive forecast."""
    in_year = hourly["ba"].eq(ba) & local["year"].eq(year)
    rows = hourly[hourly["ba"].eq(ba)]
    hours = run.hours[run.hours["ba"].eq(ba) & run.hours["year"].eq(year)]
    positive = rows["forecast"].gt(0)
    shifted = {0: rows["forecast"].where(positive)}
    shifted |= {k: lagged(rows, "forecast", k, positive) for k in FORECAST_SHIFTS}
    common = pd.DataFrame({k: s.reindex(hours.index) for k, s in shifted.items()}).dropna()
    demand = hours.loc[common.index, "demand"]
    shift_mape = {k: 100 * ((common[k] - demand).abs() / demand).mean() for k in common}
    present = both_present(hourly) & in_year
    by_month = metrics(hours, ["month"])["skill"]
    by_hour = metrics(hours, ["hour_ending"])["skill"]
    events = ba_events[ba_events["ba"].eq(ba) & ba_events["date"].dt.year.eq(year)]
    return {
        "repeated_pct": 100 * repeated_forecast.reindex(hours.index).mean(),
        "shift_mape": shift_mape,
        "best_shift": min(shift_mape, key=shift_mape.get),
        "r5_hours": int((applied.rules["R5"] & present).sum()),
        "r5_pct": 100 * (applied.rules["R5"] & present).sum() / present.sum(),
        "given_back": int((applied.given_back & in_year).sum()),
        "events": "; ".join(f"{e.date:%Y-%m-%d} {e.event}" for e in events.itertuples()) or "none",
        "months": [MONTHS[m - 1] for m, s in by_month.items() if s < 0],
        "hours": [int(h) for h, s in by_hour.items() if s < 0],
    }


# Report


def pct(value: float, decimals: int = 2) -> str:
    return fmt(value, decimals)


def ba_label(ba: str, top: list[str], mark: bool = False) -> str:
    label = f"**{ba}**" if ba in top else ba
    return label + (MARK if mark else "")


def read_weather_events(path: Path) -> pd.DataFrame:
    weather = pd.read_csv(path, dtype=str, keep_default_na=False)
    weather["id"] = weather["id"].astype(int)
    for column in ("first_day", "last_day"):
        weather[column] = pd.to_datetime(weather[column], format="%Y-%m-%d")
    weather["bas"] = weather["bas"].str.split()
    return weather


@dataclass(frozen=True)
class Results:
    top: list[str]
    main: Run
    trends: pd.DataFrame
    panel: list[str]
    panel_by_year: pd.DataFrame
    panel_trend: Trend
    national_trend: Trend
    q4: pd.DataFrame
    rho: float
    rho_p: float
    season_hour: pd.DataFrame
    season_medians: pd.Series
    holidays: pd.DataFrame
    weather: pd.DataFrame
    events: pd.DataFrame
    extreme_days: pd.DataFrame
    extremes: pd.DataFrame
    checks: dict[tuple[str, int], dict[str, object]]
    robustness: dict[str, dict[str, object]]
    usable_total: int
    shedding: pd.DataFrame
    corrections: dict[str, int]
    charging: dict[str, float]


def q1_section(r: Results) -> list[str]:
    final = r.main.yearly.xs(YEAR, level="year").sort_values("mape")
    rows = [
        [
            ba_label(str(ba), r.top),
            pct(row.mape),
            pct(row.wape),
            pct(row.bias_pct),
            fmt(row.bias_mw, 0),
            pct(row.naive_mape),
            fmt(row.skill, 2),
            fmt(row.hours, 0),
        ]
        for ba, row in final.iterrows()
    ]
    rows.append(
        [
            "**Median across BAs**",
            pct(final["mape"].median()),
            pct(final["wape"].median()),
            pct(final["bias_pct"].median()),
            fmt(final["bias_mw"].median(), 0),
            pct(final["naive_mape"].median()),
            fmt(final["skill"].median(), 2),
            fmt(final["hours"].median(), 0),
        ]
    )
    rows.append(
        [
            "**National (demand-weighted)**",
            "",
            pct(pooled_wape(final)),
            pct(100 * final["error"].sum() / final["demand"].sum()),
            "",
            "",
            "",
            fmt(final["hours"].sum(), 0),
        ]
    )
    header = [
        "BA",
        "MAPE (%)",
        "WAPE (%)",
        "Bias (%)",
        "Bias (MW)",
        "Naive MAPE (%)",
        "Skill",
        "Usable hours",
    ]
    return [
        f"## Q1. How accurate is each BA's published day-ahead forecast in {YEAR}?\n",
        f"{len(final)} eligible BAs, sorted by MAPE; the 10 largest by average demand in bold. "
        "Bias is Σe / Σ demand (positive: over-forecast) and mean e in MW. Skill is "
        "1 − MAPE / naive MAPE on the hours with a naive value; below 0 the BA loses to the "
        "naive forecast. The national figure is Σ|e| / Σ demand over all these BAs' usable "
        f"hours. Figure 1: `results/figures/q1_mape_{YEAR}.png`.\n",
        markdown_table(header, rows) + "\n",
    ]


def q2_section(r: Results) -> list[str]:
    yearly = r.main.yearly
    trends = r.trends.sort_values("slope", ascending=False)
    counts = trends["verdict"].value_counts()
    tested = len(trends)
    rows = []
    for ba, t in trends.iterrows():
        cells = [
            ""
            if (ba, y) not in yearly.index
            else fmt(yearly.loc[(ba, y), "mape"], 1) + (MARK if marked_year(str(ba), y) else "")
            for y in YEARS
        ]
        rows.append([ba_label(str(ba), r.top), *cells, fmt(t.slope, 2), f"{t.p:.3f}", t.verdict])
    by_year = r.panel_by_year
    panel_rows = [
        [str(y), fmt(v.median_mape, 2), fmt(v.national, 2)] for y, v in by_year.iterrows()
    ]
    pt, nt = r.panel_trend, r.national_trend
    rank_text, national_rank_text = (
        " and ".join(f"{year} ranks {rank}" for year, rank in year_ranks(by_year[column]).items())
        for column in ("median_mape", "national")
    )
    return [
        "## Q2. Is accuracy getting worse?\n",
        f"Per BA: yearly MAPE over its eligible years, for the {tested} BAs with at least "
        f"{MIN_TREND_YEARS}. Slope: Theil–Sen, percentage points per year. Verdict: two-sided "
        f"Mann–Kendall p < {ALPHA}.\n",
        f"- **Worse: {counts.get('worse', 0)}. Better: {counts.get('better', 0)}. No clear "
        f"trend: {counts.get('no clear trend', 0)}.** By chance alone about "
        f"{fmt(ALPHA * tested, 1)} of {tested} would reach p < {ALPHA} ({ALPHA:.0%}).\n",
        f"Across BAs: the {len(r.panel)}-BA panel eligible in every year 2016–2025.\n",
        f"- Median MAPE across the panel: slope {fmt(pt.slope, 3)} points per year, "
        f"Mann–Kendall S = {pt.s}, p = {pt.p:.3f} ({pt.verdict}).",
        f"- National figure on the panel: slope {fmt(nt.slope, 3)} points per year, S = {nt.s}, "
        f"p = {nt.p:.3f} ({nt.verdict}). The verdict sits close to the {ALPHA} bar; the "
        "Robustness section shows it for every variant. With the two verified data corrections "
        "(CISO's late demand, SWPP's forecast) it is "
        f"{r.robustness['Verified corrections']['national_verdict']} (p = "
        f"{r.robustness['Verified corrections']['national_p']:.3f}); with CISO's battery "
        "charging also taken out of its demand, "
        f"{r.robustness['All corrections']['national_verdict']} (p = "
        f"{r.robustness['All corrections']['national_p']:.3f}).",
        f"- Among the ten panel years (1: the highest error), {rank_text} on the panel median, "
        f"and {national_rank_text} on the national figure.\n",
        markdown_table(["Year", "Panel median MAPE (%)", "Panel national WAPE (%)"], panel_rows)
        + "\n",
        "Figure 2: `results/figures/q2_mape_by_year.png`.\n",
        "### Per-BA yearly MAPE (%), sorted by slope\n",
        f"Blank: not eligible that year. {MARK}: published forecast inconsistent with demand "
        "(see Notes).\n",
        markdown_table(
            ["BA", *map(str, YEARS), "Slope (pp/yr)", "p", "Verdict"], rows, left_columns=1
        )
        + "\n",
    ]


def q3_section(r: Results) -> list[str]:
    grid = r.season_hour
    peaks = {s: (int(grid.loc[s].idxmax()), grid.loc[s].max()) for s in grid.index}
    lows = {s: (int(grid.loc[s].idxmin()), grid.loc[s].min()) for s in grid.index}
    season_rows = [
        [
            str(s),
            fmt(r.season_medians[s], 2),
            f"HE {lows[s][0]} ({fmt(lows[s][1], 2)})",
            f"HE {peaks[s][0]} ({fmt(peaks[s][1], 2)})",
        ]
        for s in grid.index
    ]
    hol = r.holidays
    hol_rows = []
    for name in HOLIDAYS:
        if name not in hol.index.get_level_values("holiday"):
            continue
        part = hol.xs(name, level="holiday")
        hol_rows.append(
            [
                name,
                fmt(len(part), 0),
                fmt(part["holiday"].median(), 2),
                fmt(part["comparison"].median(), 2),
                fmt(part["ratio"].median(), 2),
                fmt((part["ratio"] > 1).sum(), 0),
            ]
        )
    ev = r.events
    weather = r.weather.set_index("id")
    shed = shed_ids(r.shedding)

    def mark(event_id: int) -> str:
        return OUTAGE_MARK if cut_demand(event_id, weather.loc[event_id, "criterion"], shed) else ""

    event_rows = []
    for event_id, part in ev.groupby("id"):
        e = weather.loc[event_id]
        scored = part.dropna(subset=["ratio"])
        event_rows.append(
            [
                str(event_id),
                e.event + mark(event_id),
                f"{e.first_day:%Y-%m-%d} to {e.last_day:%m-%d}",
                f"{len(scored)} of {len(part)}",
                fmt(scored["window_mape"].median(), 2),
                fmt(scored["baseline_mape"].median(), 2),
                fmt(scored["ratio"].median(), 2),
                fmt((scored["ratio"] > 1).sum(), 0),
            ]
        )
    detail_rows = [
        [
            str(d.id) + mark(d.id),
            ba_label(d.ba, r.top, d.marked),
            fmt(d.window_hours, 0),
            fmt(d.window_mape, 2),
            fmt(d.window_bias, 2),
            fmt(d.baseline_hours, 0),
            fmt(d.baseline_mape, 2),
            fmt(d.baseline_bias, 2),
            fmt(d.ratio, 2),
        ]
        for d in ev.itertuples()
    ]
    ex = r.extremes
    ex_rows = []
    for season in ["All", *SEASON_ORDER]:
        part = ex.xs(season, level="season")
        ex_rows.append(
            [
                season,
                fmt(len(part), 0),
                fmt(part["extreme"].median(), 2),
                fmt(part["other"].median(), 2),
                fmt(part["ratio"].median(), 2),
                fmt((part["ratio"] > 1).sum(), 0),
            ]
        )
    shed_rows = [
        [
            str(row.id),
            row.event,
            " ".join(ba for ba in row.bas.split() if ba in weather.loc[row.id, "bas"]),
            row.detail,
            " ".join(f"<{url}>" for url in row.source.split()),
        ]
        for row in r.shedding[r.shedding["load_shed"].eq("yes")].itertuples()
    ]
    unshed = r.shedding[r.shedding["load_shed"].eq("no")]
    days = r.extreme_days
    return [
        "## Q3. When do forecasts miss most? (2016–2025)\n",
        "All Q3 results use the usable hours of eligible BA-years, by local time.\n",
        "### Season and hour of day\n",
        "Each BA's MAPE per season, then the median across BAs. HE: local hour ending; the "
        "lowest and highest cells of the season's row of Figure 3 "
        "(`results/figures/q3_season_hour.png`, values in its CSV).\n",
        markdown_table(["Season", "Median MAPE (%)", "Lowest hour", "Highest hour"], season_rows)
        + "\n",
        "### Holidays\n",
        "Each BA's MAPE over the holiday's days (all years, actual and observed dates) against "
        "the same weekday one and two weeks before and after, leaving out other holidays and "
        "the BA's event days. Ratio: holiday MAPE / comparison MAPE, median across BAs.\n",
        markdown_table(
            [
                "Holiday",
                "BAs",
                "Median holiday MAPE (%)",
                "Median comparison MAPE (%)",
                "Median ratio",
                "BAs with ratio > 1",
            ],
            hol_rows,
        )
        + "\n",
        "### Extreme-weather events\n",
        f"MAPE in the event window against the same BA's hours in the {BASELINE_DAYS} days "
        "before and after (leaving out holidays and the BA's other events). Ratio: window MAPE / "
        "baseline MAPE; medians across the event's BAs with hours in both. Events and sources: "
        "`data/weather_events.csv`; the hurricane landfalls were checked against the NHC "
        "reports.\n",
        markdown_table(
            [
                "#",
                "Event",
                "Window",
                "BAs scored",
                "Median window MAPE (%)",
                "Median baseline MAPE (%)",
                "Median ratio",
                "BAs with ratio > 1",
            ],
            event_rows,
            left_columns=3,
        )
        + "\n",
        f"{OUTAGE_MARK} Outages or load shedding cut actual demand in the marked windows, so "
        "reported demand fell below what customers would have used, while the forecast still "
        'assumed they would be served. **For Winter Storm Uri and the hurricanes, these "errors" '
        "mostly measure electricity that could not be delivered, not forecasting skill.** Their "
        "high ratios and positive window bias (for example ERCO during Uri) should not be read "
        "as forecast failures. The other marked events also had documented load shedding, but "
        "in fewer BAs and for hours rather than days (table below), so there the mark means "
        "part of the error may be undelivered electricity, mainly in the BAs named. Events "
        f"without documented firm load shedding ({', '.join(map(str, unshed['id']))}) are not "
        f"marked; `{LOAD_SHEDDING_PATH}` gives the source and quote for every non-hurricane "
        "event.\n",
        markdown_table(
            ["#", "Event", "Listed BAs that shed load", "What was shed", "Source"],
            shed_rows,
            left_columns=5,
        )
        + "\n",
        f"Per event and BA (bias: Σe / Σ demand, %, positive is over-forecast; {OUTAGE_MARK} as "
        "above):\n",
        markdown_table(
            [
                "#",
                "BA",
                "Window hours",
                "Window MAPE (%)",
                "Window bias (%)",
                "Baseline hours",
                "Baseline MAPE (%)",
                "Baseline bias (%)",
                "Ratio",
            ],
            detail_rows,
            left_columns=2,
        )
        + "\n",
        "### Extreme-demand days (second check, demand only)\n",
        f"Days whose daily peak (over usable hours; days with at least {MIN_DAY_HOURS}) is above "
        f"the BA's {EXTREME_PERCENTILE}th percentile of daily peaks within that season of that "
        "season year (December counts with the next January and February): "
        f"{fmt(days['extreme'].sum(), 0)} BA-days out of {fmt(len(days), 0)}. Each BA's MAPE on "
        "them against its other such days in the same seasons and years, then the median "
        "across BAs.\n",
        markdown_table(
            [
                "Season",
                "BAs",
                "Median extreme-day MAPE (%)",
                "Median other-day MAPE (%)",
                "Median ratio",
                "BAs with ratio > 1",
            ],
            ex_rows,
        )
        + "\n",
    ]


def q4_section(r: Results) -> list[str]:
    q4 = r.q4.sort_values("x", ascending=False)
    rows = [
        [
            ba_label(str(ba), r.top, marked_year(str(ba), BASE_YEAR) or marked_year(str(ba), YEAR)),
            fmt(p.demand_base, 0),
            fmt(p.demand_year, 0),
            fmt(100 * p.x, 1),
            fmt(p.mape_base, 2),
            fmt(p.mape_year, 2),
            fmt(p.y, 2),
        ]
        for ba, p in q4.iterrows()
    ]
    return [
        "## Q4. Did errors grow more where demand grew fastest?\n",
        f"{len(q4)} BAs eligible in {BASE_YEAR} and {YEAR} ({', '.join(Q4_LEFT_OUT)} left out for "
        f"their footprint changes). x: mean demand over usable hours, {YEAR} / {BASE_YEAR} − 1. "
        f"y: MAPE {YEAR} − MAPE {BASE_YEAR}, percentage points.\n",
        f"- **Spearman ρ = {r.rho:.3f}, two-sided permutation p = {r.rho_p:.3f}** "
        f"({fmt(PERMUTATIONS, 0)} permutations, seed {PERMUTATION_SEED}).\n",
        "Figure 4: `results/figures/q4_growth_vs_error.png`. "
        f"{MARK}: published forecast inconsistent with demand in {BASE_YEAR} (see Notes).\n",
        markdown_table(
            [
                "BA",
                f"Mean demand {BASE_YEAR} (MW)",
                f"Mean demand {YEAR} (MW)",
                "Demand change (%)",
                f"MAPE {BASE_YEAR} (%)",
                f"MAPE {YEAR} (%)",
                "MAPE change (pp)",
            ],
            rows,
        )
        + "\n",
    ]


def q5_section(r: Results) -> list[str]:
    yearly = r.main.yearly
    rows = []
    for year in YEARS:
        part = yearly.xs(year, level="year")
        losing = part[part["skill"] < 0].sort_values("skill")
        names = ", ".join(
            ba_label(str(ba), r.top, marked_year(str(ba), year)) for ba in losing.index
        )
        rows.append(
            [
                str(year),
                fmt(len(part), 0),
                fmt(len(losing), 0),
                fmt(100 * len(losing) / len(part), 1),
                names or "none",
            ]
        )
    check_rows = []
    for (ba, year), c in r.checks.items():
        s = c["shift_mape"]
        best = c["best_shift"]
        check_rows.append(
            [
                f"{ba} {year}",
                fmt(yearly.loc[(ba, year), "skill"], 2),
                fmt(c["repeated_pct"], 1),
                " / ".join(fmt(s[k], 2) for k in (-24, -1, 0, 1, 24)),
                "none" if best == 0 else f"{best:+d} h",
                f"{fmt(c['r5_hours'], 0)} ({fmt(c['r5_pct'], 1)}%)",
                fmt(c["given_back"], 0),
                c["events"],
                ", ".join(c["months"]) or "none",
                f"{len(c['hours'])} of 24: {hour_ranges(c['hours'])}",
            ]
        )
    return [
        "## Q5. How many BAs lose to the naive forecast each year?\n",
        "Skill below 0: the BA's forecast has a higher MAPE than demand 24 hours earlier, on the "
        f"same hours. Sorted from the worst skill; the 10 largest BAs in bold; {MARK}: marked "
        "(see Notes).\n",
        markdown_table(["Year", "Eligible BAs", "Losing", "Share (%)", "BAs"], rows, left_columns=1)
        + "\n",
        "### Checks inside EIA-930 for the 10 largest BAs that lose\n",
        "Step 1 of the plan's checks. Repeated forecast: share of the BA-year's usable hours "
        f"whose forecast repeats inside a run of {RUN_HOURS}+ equal hours. Shifted MAPE: the "
        "forecast moved by −24, −1, 0, +1, +24 hours (moved by +k: the value published for "
        "hour t − k is scored against demand at t), on the usable hours where all five exist; "
        '"best shift" is the lowest. R5: hours with both values R5 drops that year, and hours '
        "the exception rule gives back. Months and hours (local hour ending) where skill is "
        "below 0.\n",
        (
            markdown_table(
                [
                    "BA-year",
                    "Skill",
                    "Repeated forecast (%)",
                    "MAPE shifted −24/−1/0/+1/+24 h (%)",
                    "Best shift",
                    "R5 drops",
                    "R5 given back",
                    "BA events",
                    "Months losing",
                    "Hours losing",
                ],
                check_rows,
                left_columns=1,
            )
            if check_rows
            else "None."
        )
        + "\n",
        "Step 2 of the plan, the comparison with the operator's own published load and "
        "day-ahead forecast, was approved by the user on 2026-10-28 for CAISO (2025 and Jan–Jun "
        "2026) and SPP (2025): `results/operator_check.md`. FPL has no public hourly forecast "
        "archive that we know of. The follow-ups of 2026-10-30, when CISO's late demand began "
        "and how much of CAISO's forecast gap is battery charging, are in "
        "`results/ciso_check.md`; the Robustness section re-runs the audit with the verified "
        "corrections.\n",
    ]


def robustness_section(r: Results) -> list[str]:
    rows, count_rows = [], []
    for name, change in VARIANTS.items():
        v = r.robustness[name]
        rows.append(
            [
                name,
                change,
                fmt(v["median"], 2),
                fmt(v["national"], 2),
                fmt(v["slope"], 3),
                fmt(v["national_slope"], 3),
                f"{v['national_p']:.3f} ({v['national_verdict']})",
                f"{v['worse']} / {v['better']}",
                fmt(v["rho"], 3),
                fmt(v["losing"], 0),
            ]
        )
        count_rows.append(
            [
                name,
                fmt(v["eligible"], 0),
                fmt(v["panel"], 0),
                fmt(v["tested"], 0),
                fmt(v["q4"], 0),
                fmt(v["hours"], 0),
                " / ".join(str(v["median_ranks"][y]) for y in RANKED_YEARS),
                " / ".join(str(v["national_ranks"][y]) for y in RANKED_YEARS),
            ]
        )
    ranked = " / ".join(map(str, RANKED_YEARS))
    return [
        "## Robustness\n",
        "Each variant re-runs the whole audit with one change. Eligibility, the panel and the "
        "Q4 BAs are recomputed for each variant (counts in the second table). The national "
        "panel trend is the Theil–Sen slope and two-sided Mann–Kendall test of the panel's "
        'yearly Σ|e| / Σ demand; its "worse" verdict in the main run rests on p = '
        f"{r.robustness['Main']['national_p']:.3f}, so it is shown for every variant.\n",
        markdown_table(
            [
                "Variant",
                "Change from the main run",
                f"Median {YEAR} MAPE (%)",
                f"National {YEAR} WAPE (%)",
                "Panel-median slope 2016–2025 (pp/yr)",
                "National panel slope 2016–2025 (pp/yr)",
                "National panel trend p (verdict)",
                "BAs worse / better (Q2)",
                "Spearman ρ (Q4)",
                f"BAs losing to naive in {YEAR} (Q5)",
            ],
            rows,
            left_columns=2,
        )
        + "\n",
        f"Ranks: where {ranked} fall among the ten panel years, 1 being the highest error.\n",
        markdown_table(
            [
                "Variant",
                f"Eligible BAs {YEAR}",
                "Panel BAs",
                "BAs tested for trend",
                "Q4 BAs",
                "Scored hours 2016–2025",
                f"Rank of {ranked}, panel median",
                f"Rank of {ranked}, national",
            ],
            count_rows,
        )
        + "\n",
        *corrections_text(r),
    ]


CORRECTED_RUNS = ("Main", "Verified corrections", "CISO without charging", "All corrections")


def corrections_text(r: Results) -> list[str]:
    """What the verified corrections and the charging variants change, against the main run."""
    runs = {name: r.robustness[name] for name in CORRECTED_RUNS}
    main, c, g = runs["Main"], r.corrections, r.charging

    def ciso(row: dict[str, object], column: str) -> str:
        yearly = row["yearly"]
        value = yearly.loc[("CISO", YEAR), column] if ("CISO", YEAR) in yearly.index else None
        return fmt(value if value is not None else float("nan"), 2)

    def ciso_trend(row: dict[str, object]) -> str:
        if "CISO" not in row["trends"].index:
            return "–"
        t = row["trends"].loc["CISO"]
        return f"{fmt(t['slope'], 2)} ({t['verdict']})"

    lines = {
        f"{YEAR} rank among the panel years, median / national": lambda v: (
            f"{v['median_ranks'][YEAR]} / {v['national_ranks'][YEAR]}"
        ),
        "National panel slope (pp/yr)": lambda v: fmt(v["national_slope"], 3),
        "National panel trend p (verdict)": lambda v: (
            f"{v['national_p']:.3f} ({v['national_verdict']})"
        ),
        f"BAs losing to the naive forecast in {YEAR}": lambda v: str(v["losing"]),
        f"CISO MAPE {YEAR} (%)": lambda v: ciso(v, "mape"),
        f"CISO skill {YEAR}": lambda v: ciso(v, "skill"),
        "CISO MAPE trend 2016–2025, pp/yr (verdict)": ciso_trend,
    }
    rows = [[label, *(get(v) for v in runs.values())] for label, get in lines.items()]
    changes = []
    for name, v in list(runs.items())[1:]:
        stopped = sorted(set(main["losing_bas"]) - set(v["losing_bas"]))
        started = sorted(set(v["losing_bas"]) - set(main["losing_bas"]))
        changes.append(
            f"{name}: no longer losing {', '.join(stopped) or 'none'}; newly losing "
            f"{', '.join(started) or 'none'}"
        )
    spans = ", ".join(f"{a:%Y-%m-%d %H:%M} to {b:%Y-%m-%d %H:%M}" for a, b in CISO_LATE_SPANS)
    return [
        "### Verified corrections and battery charging\n",
        "Requested by the user on 2026-10-30: the audit re-run with the data errors the "
        "operator checks verified, and with CISO's battery charging taken out of its demand, "
        "every rule re-applied each time. The main run stays as published.\n",
        f"- CISO's late demand: moved back one hour in the late spans of `results/ciso_check.md` "
        f"(UTC hour ends {spans}): {fmt(c['ciso_moved'], 0)} hours. The last hour of each span "
        "needs a value the data do not have, so the move leaves "
        f"{fmt(c['ciso_blanked'], 0)} more hours blank.",
        f"- SWPP's forecast: for the local days {SWPP_REPLACED_DAYS[0]} to "
        f"{SWPP_REPLACED_DAYS[1]} replaced by SPP's own day-ahead forecast (the 03:00 issue of the "
        f"day before, as in `results/operator_check.md`): {fmt(c['swpp_replaced'], 0)} hours, of "
        f"which {fmt(c['swpp_missing'], 0)} lack SPP's value. Replacing is clean enough to use: "
        "SPP's files cover the hours, and before 7 May EIA's own SWPP forecast followed this "
        "series closely, though rarely exactly (it carries another issue). What changed on 7 May "
        "is not known.",
        "- CISO's charging: −(its other-fuel net generation) where that is below 0, which "
        "matches CAISO's own battery output (`results/ciso_check.md`), taken out of its demand "
        "in the same hour. In 2025 that column runs an hour late together with demand, so the "
        "same EIA hour holds both; this is taken to hold in every late span (see the CISO check "
        'for the evidence before 2025). "All corrections" moves both back. EIA-930 has fuel '
        "types from "
        f"July 2018: {fmt(g['with'], 0)} CISO hours in 2018–2025 have a value and "
        f"{fmt(g['without'], 0)} do not (kept as published): CISO left the column blank from "
        "October 2019 to August 2020, when batteries were small, and only "
        f"{fmt(g['without_recent'], 0)} hours lack it from 2021 on. Mean charging taken out in "
        f'{YEAR}: {fmt(g["mean_final"], 0)} MW. "CISO without charging" applies only this '
        'correction; "All corrections" applies all three.\n',
        markdown_table(["", *runs], rows) + "\n",
        f"Changes in who loses to the naive forecast in {YEAR}, against the main run: "
        + "; ".join(changes)
        + ".\n",
        "Exploratory, not in the pre-registered plan: whether any other BA that reports "
        "batteries has a forecast gap that tracks charging as CISO's does "
        "(`results/battery_check.md`; none does).\n",
    ]


def notes_section(r: Results) -> list[str]:
    marked_text = "; ".join(
        f"{ba} {start} to {end} ({ratio})" for ba, (start, end, ratio) in MARKED.items()
    )
    return [
        "## Notes\n",
        f"- {MARK} Published forecast inconsistent with demand, not a forecasting failure "
        f"(user, 2026-10-28): {marked_text}. Their results stay in; yearly cells and events that "
        "overlap these months carry the mark.",
        '- Local time is EIA\'s "Local Time at End of Hour". Some BAs report it in standard time '
        "all year (for example MISO, LGEE, EPE, PNM and WACM), so their hour of day does not "
        "follow daylight-saving time.",
        "- Choices where the plan is silent:",
        "  - MAPE, WAPE and bias use all usable hours; skill uses the usable hours that have a "
        "naive value, so the forecast and the naive forecast are scored on the same hours.",
        "  - Holidays are the plan's table (pandas' rules for the six federal ones); the other "
        "federal holidays (Martin Luther King Jr. Day, Washington's Birthday, Juneteenth, "
        "Columbus Day, Veterans Day) are not in it and are treated as ordinary days. A BA's "
        "event days are left out of both its holiday and its comparison days.",
        "  - Event windows are kept whole, holidays included (Winter Storm Elliott covers "
        "Christmas Eve and Day 2022). Bias is reported for the window and the baseline; the "
        "ratio is for MAPE only, because a bias near zero makes a ratio meaningless.",
        "  - Extreme-demand days are compared with the BA's other days that also have at least "
        f"{MIN_DAY_HOURS} usable hours, pooled over all its seasons and years.",
        "  - Mann–Kendall uses the normal approximation with the tie and continuity "
        "corrections. The permutation p-value counts the observed order: (b + 1) / "
        f"({fmt(PERMUTATIONS, 0)} + 1).",
        "  - In each robustness variant, eligibility, the panel and the Q4 BAs follow that "
        "variant's usable hours.",
        f"- Usable hours (R1, R2 with N = {RUN_HOURS}, R3a, R4, R5 with its exemptions, R3b): "
        f"{fmt(r.usable_total, 0)}, as in `results/data_quality.md`.",
        "- No result was used to change a rule, a threshold or the plan.\n",
    ]


def render_audit(r: Results, hourly: pd.DataFrame) -> str:
    final = r.main.yearly.xs(YEAR, level="year")
    period = f"{hourly['utc'].min():%Y-%m-%d} to {hourly['utc'].max():%Y-%m-%d} UTC"
    parts = [
        "# Step 3 audit: day-ahead demand forecasts in EIA-930, 2016–2025\n",
        "Computed as pre-registered in `docs/step3_audit_plan.md` (commit `edd06df`). "
        "**Stopped for the user's review.**\n",
        f"- Data: `data/processed/balance.parquet`, {fmt(len(hourly), 0)} BA-hours, {period}. "
        "Truth: raw demand. Forecast: the day-ahead forecast as published.",
        f"- Scored: the usable hours of eligible BA-years in local years 2016–2025, "
        f"{fmt(len(r.main.hours), 0)} hours. A BA-year is eligible when at least "
        f"{MIN_USABLE_SHARE:.0%} of its hours are usable: {len(final)} BAs in {YEAR}, a "
        f"{len(r.panel)}-BA panel eligible in every year, {len(r.q4)} BAs for Q4.",
        "- Error e = forecast − demand. Naive forecast: demand 24 hours earlier, matched by "
        "timestamp, from an hour whose demand passes R1, R2, R4 and R5. The naive value for late "
        "hours may not be known when the day-ahead forecast is issued, so it is a demanding "
        "benchmark.",
        "- Summaries across BAs are medians; the national figure is Σ|e| / Σ demand over every "
        "eligible BA's usable hours.\n",
    ]
    for section in (
        q1_section,
        q2_section,
        q3_section,
        q4_section,
        q5_section,
        robustness_section,
        notes_section,
    ):
        parts += section(r)
    return "\n".join(parts)


def national_lines(robustness: dict[str, dict[str, object]]) -> tuple[pd.DataFrame, str]:
    """The headline figure's data and caption: the panel's national figure per year as published
    (the main run) and with all corrections, and each line's trend as in the robustness table.
    The caption opens by saying that the corrections came after the pre-registered results."""
    rows = {"As published": robustness["Main"], "All corrections": robustness["All corrections"]}
    data = pd.DataFrame({label: row["national_by_year"] for label, row in rows.items()})
    trends = "; ".join(
        f"{label.lower()} {row['national_slope']:.3f} pp/yr (p = {row['national_p']:.3f}, "
        f"{row['national_verdict']})"
        for label, row in rows.items()
    )
    panels = {row["panel"] for row in rows.values()}
    if len(panels) != 1:
        raise RuntimeError(f"the two runs' panels differ in size: {sorted(panels)}")
    caption = (
        "The corrections were added after the pre-registered results.\n"
        f"The {panels.pop()}-BA panel (BAs eligible in every year {YEARS[0]}–{YEARS[-1]}); "
        f"error is Σ|e| / Σ demand over all of them.\nTrend: {trends}."
    )
    return data, caption


def write_figures(r: Results) -> None:
    final = r.main.yearly.xs(YEAR, level="year")
    figures.q1_dot_plot(final, final["mape"].median(), pooled_wape(final), r.top, YEAR)
    panel = r.main.yearly["mape"].unstack("year").loc[r.panel]
    figures.q2_lines(panel, r.panel_by_year)
    figures.q3_heatmap(r.season_hour)
    figures.q4_scatter(r.q4, r.top, r.rho, r.rho_p, BASE_YEAR, YEAR)
    figures.national_by_year(*national_lines(r.robustness))


def all_runs(
    hourly: pd.DataFrame,
    local: pd.DataFrame,
    applied: Applied,
    ba_events: pd.DataFrame,
    tables: dict[str, Callable[[], pd.DataFrame]],
) -> tuple[Run, dict[str, dict[str, object]]]:
    """The main run, and the robustness row of every variant; `tables` builds the hourly table
    of each variant that changes the data, which then has every rule re-applied. Only the main
    run's hours are kept, and each table is built when it is run, to save memory."""
    rows: dict[str, dict[str, object]] = {}
    for name, rules in variant_rules(hourly, applied).items():
        run = audit_run(hourly, local, rules)
        rows[name] = robustness_row(run)
        if name == "Main":
            main_run = run
    if not main_run.usable.equals(applied.usable):
        raise RuntimeError("the main run does not reproduce data_quality.apply_rules")
    for name, build in {"EIA adjusted demand": lambda: adjusted_truth(hourly), **tables}.items():
        table = build()
        rules = {k: v for k, v in apply_rules(table, ba_events).rules.items() if k != "R3b"}
        rows[name] = robustness_row(audit_run(table, local, rules))
    return main_run, rows


def ciso_charging() -> pd.Series:
    """CISO's battery charging (MW) by UTC hour end: its other-fuel net generation below 0 in
    the cached BALANCE files, where CISO reports its batteries (results/ciso_check.md)."""
    storage = all_storage()
    return charging(storage[storage["ba"].eq("CISO")].set_index("utc")["other"])


def charging_counts(hourly: pd.DataFrame, local: pd.DataFrame, charge: pd.Series) -> dict:
    """CISO's hours in YEARS from July 2018 with and without a charging value (and without one
    from 2021 on, when batteries grew), and the mean charging taken out in YEAR (MW)."""
    rows = hourly["ba"].eq("CISO") & local["year"].isin(YEARS)
    rows &= hourly["utc"] >= pd.Timestamp("2018-07-01 07:00", tz="UTC")
    values = charge.reindex(hourly.loc[rows, "utc"]).to_numpy()
    year = local.loc[rows, "year"].to_numpy()
    return {
        "with": int(pd.notna(values).sum()),
        "without": int(pd.isna(values).sum()),
        "without_recent": int((pd.isna(values) & (year >= 2021)).sum()),
        "mean_final": float(pd.Series(values[year == YEAR]).mean()),
    }


def spp_forecast() -> pd.Series:
    """SPP's own day-ahead forecast by UTC hour end, from the cached operator files."""
    issues = {issue: read_spp(OPERATORS_DIR / "spp" / spp_name(issue)) for issue in spp_issues()}
    return spp_series(issues)[0]["forecast"]


def main() -> None:
    hourly = pd.read_parquet(PARQUET_PATH)
    ba_events = read_events(EVENTS_PATH)
    weather = read_weather_events(WEATHER_EVENTS_PATH)
    local = local_hours(hourly["local"])
    applied = apply_rules(hourly, ba_events)
    spp, charge = spp_forecast(), ciso_charging()
    corrections: dict[str, int] = {}

    def corrected() -> pd.DataFrame:
        table, counts = verified_corrections(hourly, local, spp)
        corrections.update(counts)
        return table

    tables = {
        "Verified corrections": corrected,
        "CISO without charging": lambda: charging_removed(hourly, "CISO", charge),
        "All corrections": lambda: charging_removed(
            corrected(), "CISO", moved_back(charge, CISO_LATE_SPANS)
        ),
    }
    main_run, robustness = all_runs(hourly, local, applied, ba_events, tables)

    yearly = main_run.yearly
    top = largest_bas(hourly)
    panel = panel_bas(yearly)
    by_year = panel_years(yearly, panel)
    q4 = demand_growth(yearly)
    holidays = holiday_days(YEARS)
    events = event_days(weather)
    days, extremes = extreme_day_effects(main_run.hours)
    hours = main_run.hours
    season_medians = (
        metrics(hours, ["season", "ba"])["mape"].groupby(level="season", observed=True).median()
    )
    repeated = repeats_in_runs(hourly, "forecast", RUN_HOURS)
    losing = yearly[(yearly["skill"] < 0) & yearly.index.get_level_values("ba").isin(top)]
    checks = {
        (ba, year): loss_checks(hourly, local, applied, main_run, repeated, ba_events, ba, year)
        for ba, year in losing.index
    }
    results = Results(
        top=top,
        main=main_run,
        trends=ba_trends(yearly),
        panel=panel,
        panel_by_year=by_year,
        panel_trend=trend(by_year.index, by_year["median_mape"]),
        national_trend=trend(by_year.index, by_year["national"]),
        q4=q4,
        rho=spearman(q4["x"], q4["y"]),
        rho_p=permutation_p(q4["x"], q4["y"]),
        season_hour=season_hour(hours),
        season_medians=season_medians,
        holidays=holiday_effects(hours, holidays, events),
        weather=weather,
        events=event_effects(hours, weather, holidays, events),
        extreme_days=days,
        extremes=extremes,
        checks=checks,
        robustness=robustness,
        usable_total=int(applied.usable.sum()),
        shedding=read_load_shedding(LOAD_SHEDDING_PATH),
        corrections=corrections,
        charging=charging_counts(hourly, local, charge),
    )
    write_figures(results)
    REPORT_PATH.write_text(render_audit(results, hourly), encoding="utf-8")
    print(f"wrote {REPORT_PATH} and {figures.FIGURES_DIR}/")


if __name__ == "__main__":
    main()
