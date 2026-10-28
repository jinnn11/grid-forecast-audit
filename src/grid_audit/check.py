"""Step 1 data check: per-BA quality stats, the go/no-go verdict and the Markdown report."""

from dataclasses import dataclass

import pandas as pd

# Go/no-go rule: at least MIN_PASSING of the TOP_N BAs by average demand must pass. A BA passes if
# both values are present for at least MIN_BOTH_PRESENT_PCT of its hours and its forecast MAPE is
# within [MIN_MAPE_PCT, MAX_MAPE_PCT]. Below the range suggests the forecast copies actual demand;
# above it suggests bad data or misaligned hours.
TOP_N = 10
MIN_PASSING = 8
MIN_BOTH_PRESENT_PCT = 95.0
MIN_MAPE_PCT = 0.5
MAX_MAPE_PCT = 10.0

SHARE_FLAGS = [
    "both_present",
    "demand_missing",
    "demand_zero",
    "demand_negative",
    "demand_unchanged",
    "forecast_missing",
    "forecast_zero",
    "forecast_negative",
    "forecast_unchanged",
]


def add_lags(hourly: pd.DataFrame) -> pd.DataFrame:
    """Add demand_1h, forecast_1h and demand_24h: each BA's values 1 and 24 hours earlier.

    Matched by timestamp, not row position, so a lag is NaN when that earlier hour is absent.
    """
    out = hourly
    for hours, columns in ((1, ["demand", "forecast"]), (24, ["demand"])):
        earlier = hourly[["ba", "utc", *columns]].copy()
        earlier["utc"] += pd.Timedelta(hours=hours)
        earlier.columns = ["ba", "utc", *(f"{column}_{hours}h" for column in columns)]
        out = out.merge(earlier, on=["ba", "utc"], how="left")
    return out


def hourly_flags(hourly: pd.DataFrame) -> pd.DataFrame:
    """Per-hour quality flags and errors.

    An hour is scored when demand and forecast are both present and demand > 0; errors are NaN
    for hours that are not scored, and the naive error is also NaN without demand 24 hours earlier.
    """
    lagged = add_lags(hourly)
    demand, forecast = lagged["demand"], lagged["forecast"]
    both_present = demand.notna() & forecast.notna()
    scored = both_present & (demand > 0)
    error = (forecast - demand).abs().where(scored)
    naive_error = (lagged["demand_24h"] - demand).abs().where(scored)
    return pd.DataFrame(
        {
            "ba": lagged["ba"],
            "demand": demand,
            "both_present": both_present,
            "demand_missing": demand.isna(),
            "demand_zero": demand.eq(0),
            "demand_negative": demand.lt(0),
            "demand_unchanged": demand.eq(lagged["demand_1h"]),
            "forecast_missing": forecast.isna(),
            "forecast_zero": forecast.eq(0),
            "forecast_negative": forecast.lt(0),
            "forecast_unchanged": forecast.eq(lagged["forecast_1h"]),
            "scored": scored,
            "scored_demand": demand.where(scored),
            "abs_error": error,
            "ape": error / demand,
            "naive_ape": naive_error / demand,
        }
    )


def ba_stats(hourly: pd.DataFrame) -> pd.DataFrame:
    """One row per BA, largest average reported demand first; BAs with no demand come last.

    Shares are percentages of the BA's hours in the file. MAPE, WAPE and naive MAPE are percent.
    """
    groups = hourly_flags(hourly).groupby("ba")
    stats = pd.DataFrame(
        {
            "avg_demand_mw": groups["demand"].mean(),
            "hours": groups.size(),
            **{f"{flag}_pct": 100 * groups[flag].mean() for flag in SHARE_FLAGS},
            "mape_pct": 100 * groups["ape"].mean(),
            "wape_pct": 100 * groups["abs_error"].sum() / groups["scored_demand"].sum(),
            "naive_mape_pct": 100 * groups["naive_ape"].mean(),
            "mape_hours": groups["scored"].sum(),
        }
    )
    return stats.sort_values("avg_demand_mw", ascending=False, kind="stable")


def top_ba_checks(stats: pd.DataFrame) -> pd.DataFrame:
    """The TOP_N BAs by average demand, with which go/no-go thresholds each one meets."""
    top = stats.dropna(subset=["avg_demand_mw"]).nlargest(TOP_N, "avg_demand_mw")
    coverage_ok = top["both_present_pct"] >= MIN_BOTH_PRESENT_PCT
    mape_ok = top["mape_pct"].between(MIN_MAPE_PCT, MAX_MAPE_PCT)
    return pd.DataFrame(
        {
            "avg_demand_mw": top["avg_demand_mw"],
            "both_present_pct": top["both_present_pct"],
            "mape_pct": top["mape_pct"],
            "coverage_ok": coverage_ok,
            "mape_ok": mape_ok,
            "passes": coverage_ok & mape_ok,
        }
    )


def is_go(checks: pd.DataFrame) -> bool:
    """Go if at least MIN_PASSING of the checked BAs pass."""
    return int(checks["passes"].sum()) >= MIN_PASSING


@dataclass(frozen=True)
class Source:
    file_name: str
    url: str
    sha256: str
    first_utc: pd.Timestamp
    last_utc: pd.Timestamp


def fmt(value: float, decimals: int) -> str:
    """Number with thousands separators, or an en dash when it is NaN."""
    return "–" if pd.isna(value) else f"{value:,.{decimals}f}"


def markdown_table(header: list[str], rows: list[list[str]], left_columns: int = 1) -> str:
    """Pipe table with the first `left_columns` columns left-aligned and the rest right-aligned."""
    align = [":--"] * left_columns + ["--:"] * (len(header) - left_columns)
    lines = [header, align, *rows]
    return "\n".join("| " + " | ".join(cells) + " |" for cells in lines)


def result_label(coverage_ok: bool, mape_ok: bool) -> str:
    """'pass', or which thresholds a BA fails."""
    failed = [name for name, ok in (("coverage", coverage_ok), ("MAPE", mape_ok)) if not ok]
    return "fails " + " and ".join(failed) if failed else "pass"


def verdict_section(checks: pd.DataFrame) -> str:
    verdict = "GO" if is_go(checks) else "NO-GO"
    rows = [
        [
            str(row.Index),
            fmt(row.avg_demand_mw, 0),
            fmt(row.both_present_pct, 1),
            fmt(row.mape_pct, 2),
            result_label(row.coverage_ok, row.mape_ok),
        ]
        for row in checks.itertuples()
    ]
    table = markdown_table(
        ["BA", "Avg demand (MW)", "Both present (%)", "MAPE (%)", "Result"], rows
    )
    return (
        f"## Verdict: {verdict}\n\n"
        f"{int(checks['passes'].sum())} of the {len(checks)} largest BAs by average demand pass; "
        f"at least {MIN_PASSING} of the {TOP_N} largest must pass. A BA passes if demand and the "
        f"day-ahead forecast are both present for at least {MIN_BOTH_PRESENT_PCT:g}% of its hours "
        f"and its forecast MAPE is between {MIN_MAPE_PCT:g}% and {MAX_MAPE_PCT:g}% (inclusive). "
        f"A MAPE below the range suggests the forecast copies actual demand; above it suggests "
        f"bad data or misaligned hours.\n\n{table}\n"
    )


def all_bas_section(stats: pd.DataFrame) -> str:
    header = [
        "BA",
        "Avg demand (MW)",
        "Hours",
        "Both present (%)",
        "Demand missing (%)",
        "Demand zero (%)",
        "Demand negative (%)",
        "Demand unchanged (%)",
        "Forecast missing (%)",
        "Forecast zero (%)",
        "Forecast negative (%)",
        "Forecast unchanged (%)",
        "MAPE (%)",
        "WAPE (%)",
        "Naive MAPE (%)",
        "MAPE hours",
    ]
    rows = [
        [
            str(row.Index),
            fmt(row.avg_demand_mw, 0),
            fmt(row.hours, 0),
            *(fmt(getattr(row, f"{flag}_pct"), 1) for flag in SHARE_FLAGS),
            fmt(row.mape_pct, 2),
            fmt(row.wape_pct, 2),
            fmt(row.naive_mape_pct, 2),
            fmt(row.mape_hours, 0),
        ]
        for row in stats.itertuples()
    ]
    return f"## All balancing authorities\n\n{markdown_table(header, rows)}\n"


DEFINITIONS = """## Definitions

- **Demand** is the raw reported "Demand (MW)", not EIA's imputed or adjusted series, so gaps
  stay visible. **Forecast** is "Demand Forecast (MW)", the BA's day-ahead demand forecast.
- **Hours** are the BA's rows in the file; every share is a percentage of them. "One hour
  earlier" and "24 hours earlier" are matched by UTC timestamp, not by row.
- **Missing** means blank. **Zero** means exactly 0. **Negative** means below 0. **Unchanged**
  means equal to the same BA's value one hour earlier, with both reported. A run of zeros counts
  as both zero and unchanged.
- **MAPE** is the mean of |forecast − demand| / demand over hours with both values present and
  demand > 0, so hours with negative demand are left out; negative forecasts are scored.
  **MAPE hours** counts those hours.
- **WAPE** is total |forecast − demand| / total demand over the same hours, so hours with tiny
  demand cannot inflate it.
- **Naive MAPE** is the MAPE of using demand 24 hours earlier as the forecast, over the same
  hours where that earlier demand was reported. A real forecast should beat it.
- **Avg demand** is the mean of reported demand. BAs that report no demand are listed last.
"""


def render_report(stats: pd.DataFrame, source: Source) -> str:
    """The full results/data_check.md text."""
    period = f"{source.first_utc:%Y-%m-%d %H:%M} to {source.last_utc:%Y-%m-%d %H:%M} UTC"
    intro = (
        "# EIA-930 data check\n\n"
        "Go/no-go check that EIA-930 day-ahead demand forecasts are usable for the audit.\n\n"
        f"- Source: [{source.file_name}]({source.url})\n"
        f"- SHA-256: `{source.sha256}`\n"
        f"- Hours (end of hour): {period}\n"
        f"- Balancing authorities: {len(stats)}\n"
    )
    sections = [intro, verdict_section(top_ba_checks(stats)), all_bas_section(stats), DEFINITIONS]
    return "\n".join(sections)
